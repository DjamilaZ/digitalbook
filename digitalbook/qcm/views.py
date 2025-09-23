from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from django.conf import settings
from django.db import transaction
from .models import QCM, Question, Reponse
from .serializers import (
    QCMSerializer, QCMListSerializer, QCMCreateSerializer,
    QuestionSerializer, QuestionCreateSerializer,
    ReponseSerializer, ReponseCreateSerializer
)
from books.models import Book, Chapter
from .ai_generator import QCMGenerator


class QCMPagination(PageNumberPagination):
    """Pagination personnalisée pour les QCM - 10 QCM par page"""
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


class QCMViewSet(viewsets.ModelViewSet):
    queryset = QCM.objects.all()
    serializer_class = QCMSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'
    lookup_url_kwarg = 'id'
    pagination_class = QCMPagination
    
    def get_serializer_class(self):
        """Retourne le serializer approprié selon l'action"""
        if self.action == 'list':
            return QCMListSerializer
        elif self.action == 'create':
            return QCMCreateSerializer
        return QCMSerializer

    def get_queryset(self):
        queryset = QCM.objects.all()
        
        # Filtrer par utilisateur connecté
        if self.request.user.is_authenticated:
            queryset = queryset.filter(book__created_by=self.request.user)
        else:
            return QCM.objects.none()
        
        # Filtrer par livre si spécifié
        book_id = self.request.query_params.get('book_id')
        if book_id:
            queryset = queryset.filter(book_id=book_id)
        
        # Filtrer par chapitre si spécifié
        chapter_id = self.request.query_params.get('chapter_id')
        if chapter_id:
            queryset = queryset.filter(chapter_id=chapter_id)
            
        return queryset

    @action(detail=False, methods=['post'], url_path='regenerate-chapter')
    def regenerate_chapter(self, request):
        """
        Regénère le QCM pour un chapitre donné en recréant exactement 5 nouvelles questions.
        - Supprime les QCM existants liés à ce chapitre (pour ne plus afficher les anciennes questions)
        - Génère un nouveau QCM avec 5 questions
        - Crée un QCM s'il n'existait pas

        Body attendu:
        { "chapter_id": <int>, "title": <optionnel>, "description": <optionnel> }
        """
        try:
            chapter_id = request.data.get('chapter_id')
            title = request.data.get('title')
            description = request.data.get('description', '')

            if not chapter_id:
                return Response(
                    {'error': 'chapter_id est requis'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Récupérer le chapitre appartenant à un livre de l'utilisateur
            chapter = get_object_or_404(Chapter, id=chapter_id, book__created_by=request.user)

            # Vérifier que le chapitre a des sections
            if not chapter.sections.exists():
                return Response(
                    {'error': 'Le chapitre ne contient aucune section'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Titre par défaut
            if not title:
                title = f"QCM auto-généré - {chapter.title}"

            # Toujours 5 questions, borné par le max autorisé
            nb_questions = min(5, getattr(settings, 'QCM_MAX_QUESTIONS', 10))

            with transaction.atomic():
                # Récupérer les anciennes questions AVANT suppression pour les éviter
                existing_questions_texts = list(
                    Question.objects.filter(qcm__chapter=chapter, qcm__book=chapter.book)
                    .values_list('text', flat=True)
                )

                # Supprimer les anciens QCM du chapitre (et leurs questions/réponses)
                QCM.objects.filter(chapter=chapter, book=chapter.book).delete()

                # Générer les données via l'IA en évitant les anciennes questions
                generator = QCMGenerator()
                qcm_data = generator.generate_qcm_from_chapter(
                    chapter=chapter,
                    nb_questions=nb_questions,
                    avoid_questions_texts=existing_questions_texts
                )

                # Créer le QCM
                qcm = QCM.objects.create(
                    book=chapter.book,
                    chapter=chapter,
                    title=title,
                    description=description
                )

                # Créer questions et réponses
                for i, question_data in enumerate(qcm_data):
                    question = Question.objects.create(
                        qcm=qcm,
                        text=question_data['question'],
                        order=i + 1
                    )

                    for j, option in enumerate(question_data['options']):
                        is_correct = (option == question_data['reponse_correcte'])
                        Reponse.objects.create(
                            question=question,
                            text=option,
                            is_correct=is_correct,
                            order=j + 1
                        )

            serializer = QCMSerializer(qcm)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except ValueError as e:
            return Response(
                {'error': f'Erreur de génération du QCM: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': f'Erreur serveur: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'])
    def questions(self, request, id=None):
        """Récupérer toutes les questions d'un QCM"""
        qcm = self.get_object()
        questions = qcm.questions.all().order_by('order')
        serializer = QuestionSerializer(questions, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def add_question(self, request, id=None):
        """Ajouter une question à un QCM"""
        qcm = self.get_object()
        serializer = QuestionCreateSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(qcm=qcm)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def add_reponse(self, request, id=None):
        """Ajouter une réponse à une question spécifique"""
        question_id = request.data.get('question_id')
        if not question_id:
            return Response(
                {'error': 'question_id est requis'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        question = get_object_or_404(Question, id=question_id, qcm=self.get_object())
        serializer = ReponseCreateSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(question=question)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def generate(self, request):
        """
        Génère automatiquement un QCM à partir d'un chapitre en utilisant l'IA
        
        Paramètres attendus:
        - book_id: ID du livre
        - chapter_id: ID du chapitre
        - title: Titre du QCM (optionnel)
        - description: Description du QCM (optionnel)
        - nb_questions: Nombre de questions à générer (optionnel, défaut: 5)
        """
        try:
            book_id = request.data.get('book_id')
            chapter_id = request.data.get('chapter_id')
            title = request.data.get('title')
            description = request.data.get('description', '')
            nb_questions = int(request.data.get('nb_questions', settings.QCM_DEFAULT_QUESTIONS))
            
            # Validation des paramètres
            if not book_id or not chapter_id:
                return Response(
                    {'error': 'book_id et chapter_id sont requis'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Limiter le nombre de questions
            nb_questions = min(nb_questions, settings.QCM_MAX_QUESTIONS)
            
            # Récupérer le livre et le chapitre
            book = get_object_or_404(Book, id=book_id)
            chapter = get_object_or_404(Chapter, id=chapter_id, book=book)
            
            # Vérifier que le chapitre a des sections
            if not chapter.sections.exists():
                return Response(
                    {'error': 'Le chapitre ne contient aucune section'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Générer le titre si non fourni
            if not title:
                title = f"QCM auto-généré - {chapter.title}"
            
            # Initialiser le générateur IA
            generator = QCMGenerator()

            # Récupérer les questions existantes pour éviter les doublons
            existing_questions_texts = list(
                Question.objects.filter(qcm__chapter=chapter, qcm__book=book)
                .values_list('text', flat=True)
            )
            
            # Générer les questions en évitant les anciennes
            qcm_data = generator.generate_qcm_from_chapter(
                chapter=chapter,
                nb_questions=nb_questions,
                avoid_questions_texts=existing_questions_texts
            )
            
            # Filtrer tout doublon exact qui aurait pu passer
            existing_set = set(existing_questions_texts)
            qcm_data = [q for q in qcm_data if q.get('question') not in existing_set]
            
            # Créer le QCM
            qcm = QCM.objects.create(
                book=book,
                chapter=chapter,
                title=title,
                description=description
            )
            
            # Créer les questions et réponses
            for i, question_data in enumerate(qcm_data):
                question = Question.objects.create(
                    qcm=qcm,
                    text=question_data['question'],
                    order=i + 1
                )
                
                # Créer les réponses
                for j, option in enumerate(question_data['options']):
                    is_correct = (option == question_data['reponse_correcte'])
                    Reponse.objects.create(
                        question=question,
                        text=option,
                        is_correct=is_correct,
                        order=j + 1
                    )
            
            # Retourner le QCM créé
            serializer = QCMSerializer(qcm)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        except ValueError as e:
            return Response(
                {'error': f'Erreur de génération du QCM: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': f'Erreur serveur: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class QuestionViewSet(viewsets.ModelViewSet):
    """ViewSet pour la gestion des questions"""
    queryset = Question.objects.all()
    serializer_class = QuestionSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'
    lookup_url_kwarg = 'id'
    
    def get_serializer_class(self):
        if self.action == 'create':
            return QuestionCreateSerializer
        return QuestionSerializer
    
    def get_queryset(self):
        if self.request.user.is_authenticated:
            return Question.objects.filter(qcm__book__created_by=self.request.user)
        return Question.objects.none()
        
        # Filtrer par QCM si spécifié
        qcm_id = self.request.query_params.get('qcm_id')
        if qcm_id:
            queryset = queryset.filter(qcm_id=qcm_id)
        return queryset

    @action(detail=True, methods=['get'])
    def reponses(self, request, id=None):
        """Récupérer toutes les réponses d'une question"""
        question = self.get_object()
        reponses = question.reponses.all().order_by('order')
        serializer = ReponseSerializer(reponses, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def add_reponse(self, request, id=None):
        """Ajouter une réponse à cette question"""
        question = self.get_object()
        serializer = ReponseCreateSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(question=question)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ReponseViewSet(viewsets.ModelViewSet):
    """ViewSet pour la gestion des réponses"""
    queryset = Reponse.objects.all()
    serializer_class = ReponseSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'
    lookup_url_kwarg = 'id'
    
    def get_serializer_class(self):
        if self.action == 'create':
            return ReponseCreateSerializer
        return ReponseSerializer
    
    def get_queryset(self):
        if self.request.user.is_authenticated:
            queryset = Reponse.objects.filter(question__qcm__book__created_by=self.request.user)
        else:
            return Reponse.objects.none()
        
        # Filtrer par question si spécifié
        question_id = self.request.query_params.get('question_id')
        if question_id:
            queryset = queryset.filter(question_id=question_id)
        return queryset
