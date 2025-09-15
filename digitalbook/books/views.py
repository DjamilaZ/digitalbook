# books/views.py
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from django.conf import settings
from .models import Book, Chapter, Section, Subsection
from qcm.models import QCM, Question, Reponse
from .serializers import BookSerializer, BookListSerializer, ChapterSerializer, SectionSerializer, SubsectionSerializer

class BookPagination(PageNumberPagination):
    """Pagination personnalisée pour les livres - 12 livres par page"""
    page_size = 12
    page_size_query_param = 'page_size'
    max_page_size = 100

class BookViewSet(viewsets.ModelViewSet):
    queryset = Book.objects.all()
    serializer_class = BookSerializer
    # permission_classes = [IsAuthenticated]
    lookup_field = 'id'
    lookup_url_kwarg = 'id'
    pagination_class = BookPagination
    
    def get_serializer_class(self):
        """Retourne le serializer approprié selon l'action"""
        if self.action == 'list':
            return BookListSerializer
        return BookSerializer

    def get_queryset(self):
        queryset = Book.objects.all()
        # Temporairement désactivé pour le débogage
        # if self.request.user.is_authenticated:
        #     queryset = queryset.filter(created_by=self.request.user)
        return queryset

    def perform_create(self, serializer):
        # Temporairement désactivé pour le débogage
        # serializer.save(created_by=self.request.user)
        pass  # La sauvegarde est déjà faite dans la méthode create

    def create(self, request, *args, **kwargs):
        """Gère l'upload de fichiers PDF et sauvegarde l'URL dans la BDD"""
        if 'pdf_file' not in request.FILES:
            return Response(
                {'error': 'Aucun fichier PDF fourni'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        pdf_file = request.FILES['pdf_file']
        
        # Vérifier que c'est bien un fichier PDF
        if not pdf_file.name.lower().endswith('.pdf'):
            return Response(
                {'error': 'Le fichier doit être au format PDF'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Sauvegarder le fichier dans le système de fichiers
        from django.conf import settings
        import os
        import uuid
        
        # Créer le répertoire de stockage s'il n'existe pas
        upload_dir = os.path.join(settings.MEDIA_ROOT, 'books/pdfs')
        os.makedirs(upload_dir, exist_ok=True)
        
        # Générer un nom de fichier unique
        file_extension = os.path.splitext(pdf_file.name)[1]
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = os.path.join(upload_dir, unique_filename)
        
        # Sauvegarder le fichier
        with open(file_path, 'wb+') as destination:
            for chunk in pdf_file.chunks():
                destination.write(chunk)
        
        # Extraire la première page comme couverture
        from .pdf_parser import extract_cover_from_pdf
        cover_path = extract_cover_from_pdf(file_path, settings.MEDIA_ROOT)
        
        # Construire l'URL complète du fichier
        pdf_url = f"{settings.MEDIA_URL}books/pdfs/{unique_filename}"
        
        # Générer une URL unique à partir du titre
        import re
        from django.utils.text import slugify
        
        title = request.data.get('title', pdf_file.name.replace('.pdf', ''))
        base_url = slugify(title)
        url = base_url
        counter = 1
        
        # Vérifier que l'URL est unique
        while Book.objects.filter(url=url).exists():
            url = f"{base_url}-{counter}"
            counter += 1
        
        # Créer le livre avec l'URL du PDF
        book_data = {
            'title': title,
            'url': url,
            'pdf_url': pdf_url
        }
        
        # Créer directement le livre avec toutes les données
        book = Book.objects.create(
            title=book_data['title'],
            url=book_data['url'],
            pdf_url=book_data['pdf_url'],
            cover_image=cover_path
        )
        
        # Parser le PDF et créer la hiérarchie
        try:
            print(f"\n=== DÉBUT TRAITEMENT PDF POUR LIVRE: {book.title} ===")
            print(f"PDF URL: {book.pdf_url}")
            
            from .pdf_parser import parse_pdf_to_structured_json, create_book_hierarchy_from_json
            
            # Obtenir le chemin absolu du fichier PDF
            import os
            from django.conf import settings
            pdf_file_path = os.path.join(settings.MEDIA_ROOT, book.pdf_url.replace(settings.MEDIA_URL, ''))
            print(f"Chemin PDF absolu: {pdf_file_path}")
            
            # Vérifier que le fichier existe
            if not os.path.exists(pdf_file_path):
                print(f"✗ ERREUR: Le fichier PDF n'existe pas: {pdf_file_path}")
            else:
                print(f"✓ Fichier PDF trouvé, taille: {os.path.getsize(pdf_file_path)} octets")
                
                # Parser le PDF pour obtenir la structure
                print("\n--- DÉBUT PARSING PDF ---")
                structured_data = parse_pdf_to_structured_json(pdf_file_path)
                print("--- FIN PARSING PDF ---")
                
                # Écrire le JSON structuré dans un fichier data.json
                print("\n--- ÉCRITURE FICHIER data.json ---")
                import json
                data_json_path = os.path.join(settings.BASE_DIR, 'data.json')
                try:
                    with open(data_json_path, 'w', encoding='utf-8') as f:
                        json.dump(structured_data, f, ensure_ascii=False, indent=2)
                    print(f"✓ Fichier data.json écrit avec succès: {data_json_path}")
                except Exception as e:
                    print(f"✗ Erreur écriture fichier data.json: {e}")
                
                # Créer la hiérarchie dans la BDD
                print("\n--- DÉBUT CRÉATION HIÉRARCHIE ---")
                book = create_book_hierarchy_from_json(book, structured_data)
                print("--- FIN CRÉATION HIÉRARCHIE ---")
                
                # Générer automatiquement des QCM pour chaque chapitre
                generate_qcm = request.data.get('generate_qcm', 'true').lower() == 'true'
                
                if generate_qcm and getattr(settings, 'OPENAI_API_KEY', ''):
                    print("\n--- DÉBUT GÉNÉRATION AUTOMATIQUE DES QCM ---")
                    try:
                        from qcm.utils import generate_qcms_for_book
                        nb_questions = int(request.data.get('nb_questions_per_chapter', getattr(settings, 'QCM_DEFAULT_QUESTIONS', 5)))
                        qcm_results = generate_qcms_for_book(
                            book=book,
                            nb_questions_per_chapter=nb_questions,
                            generate_for_all_chapters=True
                        )
                        print(f"✓ QCM générés: {len(qcm_results['success'])} succès, {len(qcm_results['failed'])} échecs")
                        if qcm_results['failed']:
                            print(f"✗ Échecs de génération QCM: {[f['chapter'].title for f in qcm_results['failed']]}")
                    except Exception as e:
                        print(f"✗ Erreur lors de la génération des QCM: {e}")
                        import traceback
                        print(f"Traceback: {traceback.format_exc()}")
                    print("--- FIN GÉNÉRATION AUTOMATIQUE DES QCM ---")
                elif generate_qcm:
                    print("\n⚠ OPENAI_API_KEY non configurée, génération des QCM ignorée")
                else:
                    print("\n⚠ Génération des QCM désactivée par l'utilisateur")
            
            print(f"=== FIN TRAITEMENT PDF POUR LIVRE: {book.title} ===\n")
            
        except Exception as e:
            # En cas d'erreur de parsing, on continue quand même
            # mais on log l'erreur pour le débogage
            print(f"\n✗ ERREUR LORS DU PARSING PDF: {e}")
            import traceback
            print(f"Traceback complet: {traceback.format_exc()}")
            print(f"=== FIN TRAITEMENT AVEC ERREUR ===\n")
        
        # Sérialiser le livre créé pour la réponse
        serializer = self.get_serializer(book)
        
        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data, 
            status=status.HTTP_201_CREATED, 
            headers=headers
        )
    
    @action(detail=True, methods=['post'])
    def generate_qcms(self, request, id=None):
        """
        Génère automatiquement des QCM pour tous les chapitres d'un livre existant
        
        Paramètres optionnels:
        - nb_questions_per_chapter: Nombre de questions par chapitre (défaut: 5)
        - generate_for_all_chapters: Si false, ne génère que pour les chapitres sans QCM (défaut: true)
        """
        book = self.get_object()
        
        # Vérifier que l'API key OpenAI est configurée
        if not getattr(settings, 'OPENAI_API_KEY', ''):
            return Response(
                {'error': 'OPENAI_API_KEY non configurée'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from qcm.utils import generate_qcms_for_book
            
            nb_questions = int(request.data.get('nb_questions_per_chapter', getattr(settings, 'QCM_DEFAULT_QUESTIONS', 5)))
            generate_for_all = request.data.get('generate_for_all_chapters', 'true').lower() == 'true'
            
            print(f"\n=== DÉBUT GÉNÉRATION MANUELLE DES QCM POUR LIVRE: {book.title} ===")
            
            qcm_results = generate_qcms_for_book(
                book=book,
                nb_questions_per_chapter=nb_questions,
                generate_for_all_chapters=generate_for_all
            )
            
            response_data = {
                'book_id': book.id,
                'book_title': book.title,
                'qcm_generated': len(qcm_results['success']),
                'qcm_failed': len(qcm_results['failed']),
                'qcm_skipped': len(qcm_results['skipped']),
                'details': {
                    'success': [{'qcm_id': qcm.id, 'chapter_title': qcm.chapter.title} for qcm in qcm_results['success']],
                    'failed': [{'chapter_title': f['chapter'].title, 'error': f['error']} for f in qcm_results['failed']],
                    'skipped': [{'chapter_title': chapter.title} for chapter in qcm_results['skipped']]
                }
            }
            
            print(f"✓ QCM générés manuellement: {len(qcm_results['success'])} succès, {len(qcm_results['failed'])} échecs")
            print(f"=== FIN GÉNÉRATION MANUELLE DES QCM POUR LIVRE: {book.title} ===\n")
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            print(f"✗ Erreur lors de la génération manuelle des QCM: {e}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            return Response(
                {'error': f'Erreur lors de la génération des QCM: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'])
    def export_structure(self, request, id=None):
        """Exporter la structure complète d'un livre en JSON"""
        book = self.get_object()
        
        # Construire la structure JSON
        structure = {
            "book": {
                "id": book.id,
                "title": book.title,
                "url": book.url,
                "pdf_url": book.pdf_url,
                "cover_image": book.cover_image.url if book.cover_image else None,
                "created_at": book.created_at.isoformat()
            },
            "chapters": []
        }
        
        # Récupérer tous les chapitres du livre avec leurs sections et sous-sections
        for chapter in book.chapters.all().order_by('order'):
            # Récupérer les QCMs associés à ce chapitre
            qcms = chapter.qcms.all()
            qcm_data = []
            
            for qcm in qcms:
                qcm_info = {
                    "id": qcm.id,
                    "title": qcm.title,
                    "description": qcm.description,
                    "created_at": qcm.created_at.isoformat(),
                    "updated_at": qcm.updated_at.isoformat(),
                    "question_count": qcm.questions.count(),
                    "questions": []
                }
                
                # Ajouter les questions et réponses pour chaque QCM
                for question in qcm.questions.all().order_by('order'):
                    question_info = {
                        "id": question.id,
                        "text": question.text,
                        "order": question.order,
                        "responses": []
                    }
                    
                    # Ajouter les réponses pour chaque question
                    for response in question.reponses.all().order_by('order'):
                        response_info = {
                            "id": response.id,
                            "text": response.text,
                            "is_correct": response.is_correct,
                            "order": response.order
                        }
                        question_info["responses"].append(response_info)
                    
                    qcm_info["questions"].append(question_info)
                
                qcm_data.append(qcm_info)
            
            chapter_data = {
                "id": chapter.id,
                "title": chapter.title,
                "content": chapter.content,
                "order": chapter.order,
                "sections": [],
                "qcm": qcm_data  # Ajouter les QCMs au chapitre
            }
            
            # Récupérer toutes les sections du chapitre
            for section in chapter.sections.all().order_by('order'):
                section_data = {
                    "id": section.id,
                    "title": section.title,
                    "content": section.content,
                    "order": section.order,
                    "images": section.images,
                    "tables": section.tables,
                    "subsections": []
                }
                
                # Récupérer toutes les sous-sections de la section
                for subsection in section.subsections.all().order_by('order'):
                    subsection_data = {
                        "id": subsection.id,
                        "title": subsection.title,
                        "content": subsection.content,
                        "order": subsection.order,
                        "images": subsection.images,
                        "tables": subsection.tables
                    }
                    section_data["subsections"].append(subsection_data)
                
                chapter_data["sections"].append(section_data)
            
            structure["chapters"].append(chapter_data)
        
        return Response(structure, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['get'])
    def recent(self, request):
        """Retourner les 5 derniers livres créés récemment (derniers 7 jours)"""
        from django.utils import timezone
        from datetime import timedelta
        
        # Calculer la date d'il y a 7 jours
        seven_days_ago = timezone.now() - timedelta(days=7)
        
        # Récupérer les 5 derniers livres créés dans les 7 derniers jours, ordonnés par date de création
        recent_books = Book.objects.filter(
            created_at__gte=seven_days_ago
        ).order_by('-created_at')[:5]  # Limiter aux 5 derniers livres
        
        # Utiliser le BookListSerializer pour une réponse optimisée
        serializer = self.get_serializer(recent_books, many=True)
        
        return Response({
            'count': len(serializer.data),
            'period': 'last_7_days',
            'max_results': 5,
            'results': serializer.data
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def search(self, request):
        """Rechercher des livres par titre"""
        query = request.query_params.get('q', '').strip()
        
        if not query:
            return Response({
                'error': 'Le paramètre de recherche "q" est requis',
                'count': 0,
                'results': []
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Rechercher dans le titre
        books = Book.objects.filter(
            title__icontains=query
        )
        
        # Ordonner par pertinence (les livres dont le titre correspond exactement en premier)
        books = books.order_by('-created_at')
        
        # Paginer les résultats
        page = self.paginate_queryset(books)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        # Si pas de pagination, retourner tous les résultats
        serializer = self.get_serializer(books, many=True)
        return Response({
            'count': len(serializer.data),
            'results': serializer.data
        }, status=status.HTTP_200_OK)

class ChapterViewSet(viewsets.ModelViewSet):
    serializer_class = ChapterSerializer
    # permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Chapter.objects.filter(book__created_by=self.request.user)

    def perform_create(self, serializer):
        book = get_object_or_404(Book, url=self.kwargs['book_url'], created_by=self.request.user)
        serializer.save(book=book)

class SectionViewSet(viewsets.ModelViewSet):
    serializer_class = SectionSerializer
    # permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Section.objects.filter(chapter__book__created_by=self.request.user)

    def perform_create(self, serializer):
        chapter = get_object_or_404(
            Chapter, 
            id=self.kwargs['chapter_id'],
            book__created_by=self.request.user
        )
        serializer.save(chapter=chapter)

class SubsectionViewSet(viewsets.ModelViewSet):
    serializer_class = SubsectionSerializer
    # permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Subsection.objects.filter(section__chapter__book__created_by=self.request.user)

    def perform_create(self, serializer):
        section = get_object_or_404(
            Section, 
            id=self.kwargs['section_id'],
            chapter__book__created_by=self.request.user
        )
        serializer.save(section=section)