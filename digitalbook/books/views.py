# books/views.py
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from .models import Book, Chapter, Section, Subsection
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
            pdf_url=book_data['pdf_url']
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
                "created_at": book.created_at.isoformat()
            },
            "chapters": []
        }
        
        # Récupérer tous les chapitres du livre avec leurs sections et sous-sections
        for chapter in book.chapters.all().order_by('order'):
            chapter_data = {
                "id": chapter.id,
                "title": chapter.title,
                "content": chapter.content,
                "order": chapter.order,
                "sections": []
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