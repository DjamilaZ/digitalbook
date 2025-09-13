from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from .models import QCM, Question, Reponse
from .serializers import (
    QCMSerializer, QCMListSerializer, QCMCreateSerializer,
    QuestionSerializer, QuestionCreateSerializer,
    ReponseSerializer, ReponseCreateSerializer
)
from books.models import Book, Chapter


class QCMPagination(PageNumberPagination):
    """Pagination personnalisée pour les QCM - 10 QCM par page"""
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


class QCMViewSet(viewsets.ModelViewSet):
    queryset = QCM.objects.all()
    serializer_class = QCMSerializer
    # permission_classes = [IsAuthenticated]
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
        # Filtrer par livre si spécifié
        book_id = self.request.query_params.get('book_id')
        if book_id:
            queryset = queryset.filter(book_id=book_id)
        
        # Filtrer par chapitre si spécifié
        chapter_id = self.request.query_params.get('chapter_id')
        if chapter_id:
            queryset = queryset.filter(chapter_id=chapter_id)
            
        return queryset

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


class QuestionViewSet(viewsets.ModelViewSet):
    queryset = Question.objects.all()
    serializer_class = QuestionSerializer
    # permission_classes = [IsAuthenticated]
    lookup_field = 'id'
    lookup_url_kwarg = 'id'
    
    def get_serializer_class(self):
        if self.action == 'create':
            return QuestionCreateSerializer
        return QuestionSerializer
    
    def get_queryset(self):
        queryset = Question.objects.all()
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
    queryset = Reponse.objects.all()
    serializer_class = ReponseSerializer
    # permission_classes = [IsAuthenticated]
    lookup_field = 'id'
    lookup_url_kwarg = 'id'
    
    def get_serializer_class(self):
        if self.action == 'create':
            return ReponseCreateSerializer
        return ReponseSerializer
    
    def get_queryset(self):
        queryset = Reponse.objects.all()
        # Filtrer par question si spécifié
        question_id = self.request.query_params.get('question_id')
        if question_id:
            queryset = queryset.filter(question_id=question_id)
        return queryset
