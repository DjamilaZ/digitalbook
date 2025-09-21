# books/views.py
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from django.conf import settings
from django.db import transaction
import json
from .models import Book, Chapter, Section, Subsection, Thematique
from qcm.models import QCM, Question, Reponse
from .serializers import BookSerializer, BookListSerializer, BookUpdateSerializer, ChapterSerializer, SectionSerializer, SubsectionSerializer

class BookPagination(PageNumberPagination):
    """Pagination personnalisée pour les livres - 12 livres par page"""
    page_size = 12
    page_size_query_param = 'page_size'
    max_page_size = 100

class BookViewSet(viewsets.ModelViewSet):
    queryset = Book.objects.all()
    serializer_class = BookSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'
    lookup_url_kwarg = 'id'
    pagination_class = BookPagination
    
    def get_serializer_class(self):
        """Retourne le serializer approprié selon l'action"""
        if self.action in ['list', 'search', 'recent']:
            return BookListSerializer
        return BookSerializer

    def get_queryset(self):
        """Retourne tous les livres pour les utilisateurs authentifiés"""
        return Book.objects.all()

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def create(self, request, *args, **kwargs):
        """Gère l'upload de fichiers PDF et sauvegarde l'URL dans la BDD
        Si un fichier JSON est fourni, utilise sa structure pour créer la hiérarchie
        Sinon, utilise le parsing PDF automatique
        """
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
            cover_image=cover_path,
            created_by=request.user
        )
        
        # Parser le PDF et créer la hiérarchie
        try:
            print(f"\n=== DÉBUT TRAITEMENT POUR LIVRE: {book.title} ===")
            print(f"PDF URL: {book.pdf_url}")
            
            # Vérifier si un fichier JSON de structure est fourni
            json_file = request.FILES.get('json_structure_file')
            
            if json_file:
                print("\n--- UTILISATION DU FICHIER JSON FOURNI ---")
                
                # Lire et parser le fichier JSON
                try:
                    json_content = json_file.read().decode('utf-8')
                    structured_data = json.loads(json_content)
                    print(f"✓ Fichier JSON chargé avec succès")
                    
                    # Utiliser le titre du JSON si fourni, sinon garder celui du formulaire
                    if structured_data.get('title'):
                        book.title = structured_data['title']
                        book.save()
                        print(f"✓ Titre mis à jour depuis le JSON: {book.title}")
                    
                except Exception as e:
                    print(f"✗ Erreur lecture du fichier JSON: {e}")
                    # Fallback sur le parsing PDF automatique
                    structured_data = None
            else:
                print("\n--- AUCUN FICHIER JSON FOURNI, UTILISATION DU PARSING PDF AUTOMATIQUE ---")
                structured_data = None
            
            # Si pas de JSON ou erreur de lecture, utiliser le parsing PDF automatique
            if not structured_data:
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
                    data_json_path = os.path.join(settings.BASE_DIR, 'data.json')
                    try:
                        with open(data_json_path, 'w', encoding='utf-8') as f:
                            json.dump(structured_data, f, ensure_ascii=False, indent=2)
                        print(f"✓ Fichier data.json écrit avec succès: {data_json_path}")
                    except Exception as e:
                        print(f"✗ Erreur écriture fichier data.json: {e}")
            
            # Créer la hiérarchie dans la BDD
            if structured_data:
                print("\n--- DÉBUT CRÉATION HIÉRARCHIE ---")
                if json_file:
                    # Utiliser la nouvelle fonction pour créer la hiérarchie depuis le JSON fourni
                    book = create_book_hierarchy_from_provided_json(book, structured_data)
                else:
                    # Utiliser la fonction existante pour le parsing PDF automatique
                    from .pdf_parser import create_book_hierarchy_from_json
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
                "thematique": {
                    "id": chapter.thematique.id,
                    "title": chapter.thematique.title,
                    "description": chapter.thematique.description
                } if chapter.thematique else None,
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

    def update(self, request, *args, **kwargs):
        """Mettre à jour le titre d'un livre"""
        instance = self.get_object()
        
        # Utiliser le serializer de mise à jour
        serializer = BookUpdateSerializer(instance, data=request.data, partial=True)
        
        if serializer.is_valid():
            serializer.save()
            return Response({
                'message': 'Titre mis à jour avec succès',
                'book': {
                    'id': instance.id,
                    'title': serializer.validated_data['title'],
                    'url': instance.url
                }
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ChapterViewSet(viewsets.ModelViewSet):
    """ViewSet pour la gestion des chapitres"""
    queryset = Chapter.objects.all()
    serializer_class = ChapterSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        if self.request.user.is_authenticated:
            return Chapter.objects.filter(book__created_by=self.request.user)
        return Chapter.objects.none()
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def create(self, request, *args, **kwargs):
        """Gère l'upload de fichiers PDF et sauvegarde l'URL dans la BDD
        Si un fichier JSON est fourni, utilise sa structure pour créer la hiérarchie
        Sinon, utilise le parsing PDF automatique
        """
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
            print(f"\n=== DÉBUT TRAITEMENT POUR LIVRE: {book.title} ===")
            print(f"PDF URL: {book.pdf_url}")
            
            # Vérifier si un fichier JSON de structure est fourni
            json_file = request.FILES.get('json_structure_file')
            
            if json_file:
                print("\n--- UTILISATION DU FICHIER JSON FOURNI ---")
                
                # Lire et parser le fichier JSON
                try:
                    json_content = json_file.read().decode('utf-8')
                    structured_data = json.loads(json_content)
                    print(f"✓ Fichier JSON chargé avec succès")
                    
                    # Utiliser le titre du JSON si fourni, sinon garder celui du formulaire
                    if structured_data.get('title'):
                        book.title = structured_data['title']
                        book.save()
                        print(f"✓ Titre mis à jour depuis le JSON: {book.title}")
                    
                except Exception as e:
                    print(f"✗ Erreur lecture du fichier JSON: {e}")
                    # Fallback sur le parsing PDF automatique
                    structured_data = None
            else:
                print("\n--- AUCUN FICHIER JSON FOURNI, UTILISATION DU PARSING PDF AUTOMATIQUE ---")
                structured_data = None
            
            # Si pas de JSON ou erreur de lecture, utiliser le parsing PDF automatique
            if not structured_data:
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
                    data_json_path = os.path.join(settings.BASE_DIR, 'data.json')
                    try:
                        with open(data_json_path, 'w', encoding='utf-8') as f:
                            json.dump(structured_data, f, ensure_ascii=False, indent=2)
                        print(f"✓ Fichier data.json écrit avec succès: {data_json_path}")
                    except Exception as e:
                        print(f"✗ Erreur écriture fichier data.json: {e}")
            
            # Créer la hiérarchie dans la BDD
            if structured_data:
                print("\n--- DÉBUT CRÉATION HIÉRARCHIE ---")
                if json_file:
                    # Utiliser la nouvelle fonction pour créer la hiérarchie depuis le JSON fourni
                    book = create_book_hierarchy_from_provided_json(book, structured_data)
                else:
                    # Utiliser la fonction existante pour le parsing PDF automatique
                    from .pdf_parser import create_book_hierarchy_from_json
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

class SectionViewSet(viewsets.ModelViewSet):
    """ViewSet pour la gestion des sections"""
    queryset = Section.objects.all()
    serializer_class = SectionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        if self.request.user.is_authenticated:
            return Section.objects.filter(chapter__book__created_by=self.request.user)
        return Section.objects.none()
    
    def perform_create(self, serializer):
        chapter = get_object_or_404(
            Chapter, 
            id=self.kwargs['chapter_id'],
            book__created_by=self.request.user
        )
        serializer.save(chapter=chapter)

class SubsectionViewSet(viewsets.ModelViewSet):
    """ViewSet pour la gestion des sous-sections"""
    queryset = Subsection.objects.all()
    serializer_class = SubsectionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        if self.request.user.is_authenticated:
            return Subsection.objects.filter(section__chapter__book__created_by=self.request.user)
        return Subsection.objects.none()
    
    def perform_create(self, serializer):
        section = get_object_or_404(
            Section, 
            id=self.kwargs['section_id'],
            chapter__book__created_by=self.request.user
        )
        serializer.save(section=section)


def create_book_hierarchy_from_provided_json(book, structured_data):
    """
    Crée la hiérarchie complète d'un livre (thématiques, chapitres, sections, sous-sections)
    à partir d'un JSON structuré fourni par l'utilisateur
    
    Args:
        book: Instance du modèle Book
        structured_data: Dictionnaire contenant la structure du livre
    
    Returns:
        Book: L'instance du livre mise à jour avec sa hiérarchie
    """
    print(f"\n=== CRÉATION HIÉRARCHIE DEPUIS JSON FOURNI ===")
    print(f"Livre: {book.title}")
    print(f"Structure reçue: {list(structured_data.keys())}")
    
    try:
        with transaction.atomic():
            # Vérifier si c'est la nouvelle structure (avec thematiques) ou l'ancienne (avec chapitres directement)
            if 'thematiques' in structured_data or 'chapters_sans_thematique' in structured_data:
                # Nouvelle structure
                print("Utilisation de la nouvelle structure (avec thematiques)")
                
                # Mettre à jour le titre du livre si présent (pour les fichiers mixtes)
                if 'titre_livre' in structured_data:
                    book.title = structured_data['titre_livre']
                    book.save()
                    print(f"Titre du livre mis à jour: {book.title}")
                
                # Créer les thématiques
                thematiques_data = structured_data.get('thematiques', [])
                for thematique_data in thematiques_data:
                    print(f"\n--- Création thématique: {thematique_data.get('title', 'Sans titre')} ---")
                    
                    thematique = Thematique.objects.create(
                        book=book,
                        title=thematique_data.get('title', 'Thématique sans titre'),
                        description=thematique_data.get('description', '')
                    )
                    print(f"✓ Thématique créée: {thematique.title}")
                    
                    # Créer les chapitres de cette thématique
                    chapters_data = thematique_data.get('chapters', [])
                    for chapter_index, chapter_data in enumerate(chapters_data):
                        chapter = create_chapter_from_data(chapter_data, book, thematique, chapter_index)
                
                # Créer les chapitres sans thématique
                chapters_sans_thematique = structured_data.get('chapters_sans_thematique', [])
                if chapters_sans_thematique:
                    print(f"\n--- Création chapitres sans thématique ---")
                    for chapter_index, chapter_data in enumerate(chapters_sans_thematique):
                        # Adapter les noms de champs pour l'ancienne structure
                        chapter_data_adapted = {
                            'title': chapter_data.get('titre', 'Chapitre sans titre'),
                            'content': chapter_data.get('contenu', ''),
                            'sections': chapter_data.get('sections', [])
                        }
                        chapter = create_chapter_from_data(chapter_data_adapted, book, None, chapter_index)
            
            elif 'chapitres' in structured_data or 'titre_livre' in structured_data:
                # Ancienne structure (comme test_structure.json)
                print("Utilisation de l'ancienne structure (chapitres directs)")
                
                # Mettre à jour le titre du livre si présent
                if 'titre_livre' in structured_data:
                    book.title = structured_data['titre_livre']
                    book.save()
                    print(f"Titre du livre mis à jour: {book.title}")
                
                # Créer les chapitres directement (sans thématique)
                chapitres_data = structured_data.get('chapitres', [])
                print(f"Nombre de chapitres à créer: {len(chapitres_data)}")
                
                for chapter_index, chapitre_data in enumerate(chapitres_data):
                    print(f"\n--- Création chapitre: {chapitre_data.get('titre', 'Sans titre')} ---")
                    
                    # Adapter les noms de champs
                    chapter_data_adapted = {
                        'title': chapitre_data.get('titre', 'Chapitre sans titre'),
                        'content': chapitre_data.get('contenu', ''),
                        'sections': chapitre_data.get('sections', [])
                    }
                    
                    chapter = create_chapter_from_data(chapter_data_adapted, book, None, chapter_index)
            
            else:
                print("Structure JSON non reconnue")
                raise ValueError("Structure JSON non reconnue. Les clés attendues sont: 'thematiques'/'chapters_sans_thematique' ou 'chapitres'/'titre_livre'")
            
            print(f"\n✓ HIÉRARCHIE CRÉÉE AVEC SUCCÈS POUR LE LIVRE: {book.title}")
            return book
            
    except Exception as e:
        print(f"✗ ERREUR LORS DE LA CRÉATION DE LA HIÉRARCHIE: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        raise


def create_chapter_from_data(chapter_data, book, thematique, chapter_index=None):
    """
    Crée un chapitre et sa hiérarchie (sections, sous-sections) à partir des données
    
    Args:
        chapter_data: Dictionnaire contenant les données du chapitre
        book: Instance du livre parent
        thematique: Instance de la thématique parent (peut être None)
        chapter_index: Index du chapitre dans le tableau (pour l'ordre)
    
    Returns:
        Chapter: L'instance du chapitre créée
    """
    print(f"  Création chapitre: {chapter_data.get('title', 'Sans titre')}")
    
    # Utiliser l'index comme ordre si fourni, sinon utiliser la valeur du JSON ou 0
    order = chapter_index if chapter_index is not None else chapter_data.get('order', 0)
    
    chapter = Chapter.objects.create(
        book=book,
        thematique=thematique,
        title=chapter_data.get('title', 'Chapitre sans titre'),
        content=chapter_data.get('content', ''),
        order=order
    )
    print(f"    ✓ Chapitre créé: {chapter.title} (ID: {chapter.id})")
    
    # Créer les sections du chapitre
    sections_data = chapter_data.get('sections', [])
    print(f"    Nombre de sections à créer: {len(sections_data)}")
    for section_index, section_data in enumerate(sections_data):
        create_section_from_data(section_data, chapter, section_index)
    
    return chapter


def create_section_from_data(section_data, chapter, section_index=None):
    """
    Crée une section et ses sous-sections à partir des données
    
    Args:
        section_data: Dictionnaire contenant les données de la section
        chapter: Instance du chapitre parent
        section_index: Index de la section dans le tableau (pour l'ordre)
    
    Returns:
        Section: L'instance de la section créée
    """
    # Adapter les noms de champs pour l'ancienne structure
    section_title = section_data.get('title') or section_data.get('titre', 'Section sans titre')
    section_content = section_data.get('content') or section_data.get('contenu', '')
    
    print(f"    Création section: {section_title}")
    
    # Utiliser l'index comme ordre si fourni, sinon utiliser la valeur du JSON ou 0
    order = section_index if section_index is not None else section_data.get('order', 0)
    
    section = Section.objects.create(
        chapter=chapter,
        title=section_title,
        content=section_content,
        order=order,
        images=section_data.get('images', []),
        tables=section_data.get('tables', [])
    )
    print(f"      ✓ Section créée: {section.title} (ID: {section.id})")
    
    # Créer les sous-sections de la section
    subsections_data = section_data.get('subsections') or section_data.get('sous_sections', [])
    print(f"      Nombre de sous-sections à créer: {len(subsections_data)}")
    for subsection_index, subsection_data in enumerate(subsections_data):
        create_subsection_from_data(subsection_data, section, subsection_index)
    
    return section


def create_subsection_from_data(subsection_data, section, subsection_index=None):
    """
    Crée une sous-section à partir des données
    
    Args:
        subsection_data: Dictionnaire contenant les données de la sous-section
        section: Instance de la section parent
        subsection_index: Index de la sous-section dans le tableau (pour l'ordre)
    
    Returns:
        Subsection: L'instance de la sous-section créée
    """
    # Adapter les noms de champs pour l'ancienne structure
    subsection_title = subsection_data.get('title') or subsection_data.get('titre', 'Sous-section sans titre')
    subsection_content = subsection_data.get('content') or subsection_data.get('contenu', '')
    
    print(f"      Création sous-section: {subsection_title}")
    
    # Utiliser l'index comme ordre si fourni, sinon utiliser la valeur du JSON ou 0
    order = subsection_index if subsection_index is not None else subsection_data.get('order', 0)
    
    subsection = Subsection.objects.create(
        section=section,
        title=subsection_title,
        content=subsection_content,
        order=order,
        images=subsection_data.get('images', []),
        tables=subsection_data.get('tables', [])
    )
    print(f"        ✓ Sous-section créée: {subsection.title} (ID: {subsection.id})")
    
    return subsection