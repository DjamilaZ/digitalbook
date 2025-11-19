# books/views.py
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.views import APIView
from rest_framework.exceptions import PermissionDenied
from django.conf import settings
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from django.db.models import F, Max
import json
from .models import (
    Book, Chapter, Section, Subsection, Thematique, ReadingProgress,
    ThematiqueTranslation, ChapterTranslation, SectionTranslation, SubsectionTranslation,
)
from .background import submit_process_book
from qcm.models import QCM, Question, Reponse
from .serializers import BookSerializer, BookListSerializer, BookUpdateSerializer, ChapterSerializer, SectionSerializer, SubsectionSerializer, ReadingProgressSerializer
from authentication.custom_auth import CsrfExemptSessionAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication

class BookPagination(PageNumberPagination):
    """Pagination personnalisée pour les livres - 12 livres par page"""
    page_size = 12
    page_size_query_param = 'page_size'
    max_page_size = 100

@method_decorator(csrf_exempt, name='dispatch')
class BookViewSet(viewsets.ModelViewSet):
    queryset = Book.objects.all()
    serializer_class = BookSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication, CsrfExemptSessionAuthentication]
    lookup_field = 'id'
    lookup_url_kwarg = 'id'
    pagination_class = BookPagination
    
    def get_serializer_class(self):
        """Retourne le serializer approprié selon l'action"""
        if self.action in ['list', 'search', 'recent']:
            return BookListSerializer
        return BookSerializer

    def get_queryset(self):
        """Retourne les livres en fonction du rôle de l'utilisateur.

        - admin : voit tous les livres
        - manager / employe : voit uniquement les livres publiés
        """
        user = self.request.user
        role = getattr(getattr(user, 'profile', user), 'role_name', None) or getattr(user, 'role_name', None)
        qs = Book.objects.all()
        if role == 'admin':
            return qs
        return qs.filter(published=True)

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        """Empêche les non-admin de modifier le champ published."""
        user = self.request.user
        role = getattr(getattr(user, 'profile', user), 'role_name', None) or getattr(user, 'role_name', None)
        if role != 'admin':
            # Forcer published à l'ancienne valeur pour les non-admin
            instance = self.get_object()
            serializer.save(published=instance.published)
        else:
            serializer.save()

    def destroy(self, request, *args, **kwargs):
        """Seul un admin peut supprimer un livre."""
        user = request.user
        role = getattr(getattr(user, 'profile', user), 'role_name', None) or getattr(user, 'role_name', None)
        if role != 'admin':
            raise PermissionDenied("Seul un admin peut supprimer un livre.")
        return super().destroy(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        """Upload le PDF, crée l'objet Book, et délègue le traitement à un pool de threads.
        - 2 threads dédiés au traitement (création hiérarchie + QCM)
        - Retourne immédiatement une réponse avec un statut de traitement = queued
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
        
        # Extraire la première page comme couverture (meilleur UX sans attendre tout le parsing)
        try:
            from .pdf_parser import extract_cover_from_pdf
            cover_path = extract_cover_from_pdf(file_path, settings.MEDIA_ROOT)
        except Exception:
            cover_path = None
        
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
        # Paramètres de traitement
        generate_qcm = str(request.data.get('generate_qcm', 'true')).lower() == 'true'
        try:
            nb_questions = int(request.data.get('nb_questions_per_chapter', getattr(settings, 'QCM_DEFAULT_QUESTIONS', 5)))
        except Exception:
            nb_questions = getattr(settings, 'QCM_DEFAULT_QUESTIONS', 5)

        # Si un JSON de structure est fourni, le sauvegarder pour le thread
        json_rel_path = None
        json_file = request.FILES.get('json_structure_file')
        if json_file:
            import uuid, os
            json_dir = os.path.join(settings.MEDIA_ROOT, 'books/json')
            os.makedirs(json_dir, exist_ok=True)
            json_name = f"{uuid.uuid4()}.json"
            json_abs = os.path.join(json_dir, json_name)
            with open(json_abs, 'wb') as out:
                for chunk in json_file.chunks():
                    out.write(chunk)
            json_rel_path = os.path.join('books/json', json_name).replace('\\', '/')

        # Marquer le livre comme en file d'attente et soumettre au pool 2 threads
        book.processing_status = 'queued'
        book.processing_progress = 0
        book.processing_error = None
        book.processing_started_at = None
        book.processing_finished_at = None
        book.save(update_fields=[
            'processing_status', 'processing_progress', 'processing_error',
            'processing_started_at', 'processing_finished_at'
        ])

        submit_process_book(
            book_id=book.id,
            json_structure_file_rel=json_rel_path,
            generate_qcm=generate_qcm,
            nb_questions_per_chapter=nb_questions,
        )

        # Retour immédiat
        serializer = self.get_serializer(book)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
    
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
                "is_intro": getattr(chapter, 'is_intro', False),
                "images": getattr(chapter, 'images', []),
                "tables": getattr(chapter, 'tables', []),
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

    @action(detail=True, methods=['get'], url_path='processing-status')
    def processing_status(self, request, id=None):
        """Récupérer le statut/progression du traitement background pour un livre."""
        book = self.get_object()
        data = {
            'id': book.id,
            'status': book.processing_status,
            'progress': book.processing_progress,
            'error': book.processing_error,
            'started_at': book.processing_started_at,
            'finished_at': book.processing_finished_at,
        }
        return Response(data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='finalize')
    def finalize(self, request, id=None):
        """Déclenche le job de traduction du livre (asynchrone).

        Fonctionnalité de traduction désactivée temporairement.
        """
        # from .background import submit_translate_book
        # book = self.get_object()
        # # Optionnel: liste de cibles fournie
        # targets = request.data.get('target_langs') or request.data.get('targets') or None
        # if isinstance(targets, str):
        #     targets = [t.strip() for t in targets.split(',') if t.strip()]
        # submit_translate_book(book.id, targets)
        # return Response({'status': 'accepted', 'book_id': book.id}, status=status.HTTP_202_ACCEPTED)

        return Response(
            {'error': 'La traduction automatique est désactivée pour le moment.'},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    @action(detail=True, methods=['get'], url_path='content')
    def content(self, request, id=None):
        """Retourner la structure du livre avec traductions selon ?lang=fr|en|pt (fallback sur source)."""
        book = self.get_object()
        req_lang = (request.query_params.get('lang') or '').strip().lower()
        if req_lang not in ('fr', 'en', 'pt'):
            req_lang = None

        def pick_thematique(thematique: Thematique):
            data = {
                'id': thematique.id,
                'title': thematique.title,
                'description': thematique.description,
                'translation_status': None,
            }
            if req_lang:
                tr = ThematiqueTranslation.objects.filter(thematique=thematique, lang=req_lang).first()
                if tr and (tr.title or tr.description):
                    data['title'] = tr.title or data['title']
                    data['description'] = tr.description or data['description']
                    data['translation_status'] = tr.status
            return data

        structure = {
            'book': {
                'id': book.id,
                'title': book.title,
                'url': book.url,
                'pdf_url': book.pdf_url,
                'cover_image': book.cover_image.url if book.cover_image else None,
                'created_at': book.created_at.isoformat(),
                'language': book.language,
            },
            'chapters': []
        }

        for chapter in book.chapters.all().order_by('order'):
            ch_title = chapter.title
            ch_content = chapter.content
            ch_status = None
            if req_lang:
                trc = ChapterTranslation.objects.filter(chapter=chapter, lang=req_lang).first()
                if trc and (trc.title or trc.content):
                    ch_title = trc.title or ch_title
                    ch_content = trc.content or ch_content
                    ch_status = trc.status

            chapter_data = {
                'id': chapter.id,
                'title': ch_title,
                'content': ch_content,
                'order': chapter.order,
                'images': getattr(chapter, 'images', []),
                'tables': getattr(chapter, 'tables', []),
                'translation_status': ch_status,
                'thematique': pick_thematique(chapter.thematique) if chapter.thematique else None,
                'sections': [],
            }

            for section in chapter.sections.all().order_by('order'):
                se_title = section.title
                se_content = section.content
                se_images = section.images
                se_tables = section.tables
                se_status = None
                if req_lang:
                    trs = SectionTranslation.objects.filter(section=section, lang=req_lang).first()
                    if trs and (trs.title or trs.content or trs.images or trs.tables):
                        se_title = trs.title or se_title
                        se_content = trs.content or se_content
                        se_images = trs.images if isinstance(trs.images, list) else se_images
                        se_tables = trs.tables if isinstance(trs.tables, list) else se_tables
                        se_status = trs.status

                section_data = {
                    'id': section.id,
                    'title': se_title,
                    'content': se_content,
                    'order': section.order,
                    'images': se_images,
                    'tables': se_tables,
                    'translation_status': se_status,
                    'subsections': [],
                }

                for subsection in section.subsections.all().order_by('order'):
                    su_title = subsection.title
                    su_content = subsection.content
                    su_images = subsection.images
                    su_tables = subsection.tables
                    su_status = None
                    if req_lang:
                        trs = SubsectionTranslation.objects.filter(subsection=subsection, lang=req_lang).first()
                        if trs and (trs.title or trs.content or trs.images or trs.tables):
                            su_title = trs.title or su_title
                            su_content = trs.content or su_content
                            su_images = trs.images if isinstance(trs.images, list) else su_images
                            su_tables = trs.tables if isinstance(trs.tables, list) else su_tables
                            su_status = trs.status

                    subsection_data = {
                        'id': subsection.id,
                        'title': su_title,
                        'content': su_content,
                        'order': subsection.order,
                        'images': su_images,
                        'tables': su_tables,
                        'translation_status': su_status,
                    }
                    section_data['subsections'].append(subsection_data)

                chapter_data['sections'].append(section_data)

            structure['chapters'].append(chapter_data)

        return Response(structure, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get', 'put', 'patch'], url_path='reading-progress')
    def reading_progress(self, request, id=None):
        """Récupérer ou mettre à jour la progression de lecture de l'utilisateur pour ce livre."""
        book = self.get_object()
        rp, _ = ReadingProgress.objects.get_or_create(user=request.user, book=book)

        if request.method in ['PUT', 'PATCH']:
            serializer = ReadingProgressSerializer(rp, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save(book=book)
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        serializer = ReadingProgressSerializer(rp)
        return Response(serializer.data, status=status.HTTP_200_OK)

class ChapterViewSet(viewsets.ModelViewSet):
    """ViewSet pour la gestion des chapitres"""
    queryset = Chapter.objects.all()
    serializer_class = ChapterSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        qs = Chapter.objects.none()
        user = self.request.user
        if user.is_authenticated:
            role = getattr(getattr(user, 'profile', user), 'role_name', None) or getattr(user, 'role_name', None)
            if role in ('admin', 'manager'):
                qs = Chapter.objects.all()
            else:
                qs = Chapter.objects.filter(book__created_by=user)
            # Filtrer par livre parent si présent (nested router)
            book_id = self.kwargs.get('book_id') or self.kwargs.get('book_pk') or None
            if book_id:
                qs = qs.filter(book_id=book_id)
        return qs
    
    def perform_create(self, serializer):
        book_id = self.kwargs.get('book_id') or self.kwargs.get('book_pk')
        user = self.request.user
        role = getattr(getattr(user, 'profile', user), 'role_name', None) or getattr(user, 'role_name', None)
        if role in ('admin', 'manager'):
            book = get_object_or_404(Book, id=book_id)
        else:
            book = get_object_or_404(Book, id=book_id, created_by=user)
        # Gestion de la position/ordre lors de la création du chapitre
        position = (self.request.data.get('position') or 'first').lower()
        after_id = self.request.data.get('after_id')
        qs = Chapter.objects.filter(book=book)
        new_order = 0

        if position == 'last':
            max_order = qs.aggregate(max_o=Max('order'))['max_o']
            new_order = (max_order or 0) + 1
        elif position == 'after' and after_id:
            try:
                ref = qs.get(id=after_id)
                ref_order = ref.order
            except Chapter.DoesNotExist:
                ref_order = None
            if ref_order is None:
                max_order = qs.aggregate(max_o=Max('order'))['max_o']
                new_order = (max_order or 0) + 1
            else:
                qs.filter(order__gt=ref_order).update(order=F('order') + 1)
                new_order = ref_order + 1
        else:
            # Par défaut, insérer au début
            qs.update(order=F('order') + 1)
            new_order = 0

        serializer.save(book=book, order=new_order)


class SectionViewSet(viewsets.ModelViewSet):
    """ViewSet pour la gestion des sections"""
    queryset = Section.objects.all()
    serializer_class = SectionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        qs = Section.objects.none()
        user = self.request.user
        if user.is_authenticated:
            role = getattr(getattr(user, 'profile', user), 'role_name', None) or getattr(user, 'role_name', None)
            if role in ('admin', 'manager'):
                qs = Section.objects.all()
            else:
                qs = Section.objects.filter(chapter__book__created_by=user)
            # Filtrer par parents si présents
            book_id = self.kwargs.get('book_id') or self.kwargs.get('book_pk')
            chapter_id = self.kwargs.get('chapter_id') or self.kwargs.get('chapter_pk')
            if book_id:
                qs = qs.filter(chapter__book_id=book_id)
            if chapter_id:
                qs = qs.filter(chapter_id=chapter_id)
        return qs
    
    def perform_create(self, serializer):
        chapter_id = self.kwargs.get('chapter_id') or self.kwargs.get('chapter_pk')
        user = self.request.user
        role = getattr(getattr(user, 'profile', user), 'role_name', None) or getattr(user, 'role_name', None)
        if role in ('admin', 'manager'):
            chapter = get_object_or_404(Chapter, id=chapter_id)
        else:
            chapter = get_object_or_404(Chapter, id=chapter_id, book__created_by=user)
        # Gestion de la position/ordre lors de la création de la section
        position = (self.request.data.get('position') or 'first').lower()
        after_id = self.request.data.get('after_id')
        qs = Section.objects.filter(chapter=chapter)
        new_order = 0

        if position == 'last':
            max_order = qs.aggregate(max_o=Max('order'))['max_o']
            new_order = (max_order or 0) + 1
        elif position == 'after' and after_id:
            try:
                ref = qs.get(id=after_id)
                ref_order = ref.order
            except Section.DoesNotExist:
                ref_order = None
            if ref_order is None:
                max_order = qs.aggregate(max_o=Max('order'))['max_o']
                new_order = (max_order or 0) + 1
            else:
                qs.filter(order__gt=ref_order).update(order=F('order') + 1)
                new_order = ref_order + 1
        else:
            # Par défaut, insérer au début
            qs.update(order=F('order') + 1)
            new_order = 0

        serializer.save(chapter=chapter, order=new_order)


class SubsectionViewSet(viewsets.ModelViewSet):
    """ViewSet pour la gestion des sous-sections"""
    queryset = Subsection.objects.all()
    serializer_class = SubsectionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        qs = Subsection.objects.none()
        user = self.request.user
        if user.is_authenticated:
            role = getattr(getattr(user, 'profile', user), 'role_name', None) or getattr(user, 'role_name', None)
            if role in ('admin', 'manager'):
                qs = Subsection.objects.all()
            else:
                qs = Subsection.objects.filter(section__chapter__book__created_by=user)
            # Filtrer par parents si présents
            book_id = self.kwargs.get('book_id') or self.kwargs.get('book_pk')
            chapter_id = self.kwargs.get('chapter_id') or self.kwargs.get('chapter_pk')
            section_id = self.kwargs.get('section_id') or self.kwargs.get('section_pk')
            if book_id:
                qs = qs.filter(section__chapter__book_id=book_id)
            if chapter_id:
                qs = qs.filter(section__chapter_id=chapter_id)
            if section_id:
                qs = qs.filter(section_id=section_id)
        return qs
    
    def perform_create(self, serializer):
        section_id = self.kwargs.get('section_id') or self.kwargs.get('section_pk')
        user = self.request.user
        role = getattr(getattr(user, 'profile', user), 'role_name', None) or getattr(user, 'role_name', None)
        if role in ('admin', 'manager'):
            section = get_object_or_404(Section, id=section_id)
        else:
            section = get_object_or_404(Section, id=section_id, chapter__book__created_by=user)
        # Gestion de la position/ordre lors de la création de la sous-section
        position = (self.request.data.get('position') or 'first').lower()
        after_id = self.request.data.get('after_id')
        qs = Subsection.objects.filter(section=section)
        new_order = 0

        if position == 'last':
            max_order = qs.aggregate(max_o=Max('order'))['max_o']
            new_order = (max_order or 0) + 1
        elif position == 'after' and after_id:
            try:
                ref = qs.get(id=after_id)
                ref_order = ref.order
            except Subsection.DoesNotExist:
                ref_order = None
            if ref_order is None:
                max_order = qs.aggregate(max_o=Max('order'))['max_o']
                new_order = (max_order or 0) + 1
            else:
                qs.filter(order__gt=ref_order).update(order=F('order') + 1)
                new_order = ref_order + 1
        else:
            # Par défaut, insérer au début
            qs.update(order=F('order') + 1)
            new_order = 0

        serializer.save(section=section, order=new_order)


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


class ImageUploadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        """Uploader une image et retourner son URL publique."""
        img = request.FILES.get('file') or request.FILES.get('image')
        if not img:
            return Response({'error': 'Aucun fichier fourni (clé attendue: file)'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            import os, uuid
            upload_dir = os.path.join(settings.MEDIA_ROOT, 'books/images')
            os.makedirs(upload_dir, exist_ok=True)

            ext = os.path.splitext(img.name)[1] or '.png'
            filename = f"{uuid.uuid4()}{ext}"
            abs_path = os.path.join(upload_dir, filename)
            with open(abs_path, 'wb+') as destination:
                for chunk in img.chunks():
                    destination.write(chunk)

            url = f"{settings.MEDIA_URL}books/images/{filename}"
            caption = request.data.get('caption')
            payload = {'url': url}
            if caption:
                payload['caption'] = caption
            return Response(payload, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)