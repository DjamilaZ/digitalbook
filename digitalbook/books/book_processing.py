import os
import json
import traceback
from datetime import datetime
from typing import Optional

from django.conf import settings
from django.utils import timezone

from .models import Book


def _save_book_fields(book: Book, **kwargs):
    for k, v in kwargs.items():
        setattr(book, k, v)
    book.save(update_fields=list(kwargs.keys()))


def process_book_sync(
    book_id: int,
    json_structure_file_rel: Optional[str] = None,
    generate_qcm: bool = True,
    nb_questions_per_chapter: Optional[int] = None,
) -> None:
    """Traite un livre de manière synchrone dans un thread background.
    - Parse le PDF (ou importe un JSON fourni) pour créer la hiérarchie
    - Génère les QCMs si demandé
    - Met à jour les champs de progression/statut sur le modèle Book
    """
    book = Book.objects.get(id=book_id)

    # Marquer comme en cours
    _save_book_fields(
        book,
        processing_status='processing',
        processing_progress=5,
        processing_error=None,
        processing_started_at=timezone.now(),
        processing_finished_at=None,
    )

    try:
        # Résoudre le chemin absolu du PDF à partir de book.pdf_url
        pdf_rel_path = book.pdf_url.replace(settings.MEDIA_URL, '') if book.pdf_url else None
        pdf_file_path = os.path.join(settings.MEDIA_ROOT, pdf_rel_path) if pdf_rel_path else None

        # Étape 1: Charger les données (JSON fourni ou parsing PDF)
        _save_book_fields(book, processing_progress=15)

        structured_data = None
        json_file_path = None
        if json_structure_file_rel:
            json_file_path = os.path.join(settings.MEDIA_ROOT, json_structure_file_rel)

        if json_file_path and os.path.exists(json_file_path):
            # Utiliser le JSON fourni par l'utilisateur
            with open(json_file_path, 'r', encoding='utf-8') as f:
                structured_data = json.load(f)
            # Option: mettre à jour le titre depuis le JSON
            if structured_data.get('title'):
                _save_book_fields(book, title=structured_data['title'])

            # Créer la hiérarchie depuis le JSON fourni
            _save_book_fields(book, processing_progress=40)

            from .views import create_book_hierarchy_from_provided_json
            create_book_hierarchy_from_provided_json(book, structured_data)
        else:
            # Parser le PDF
            if not pdf_file_path or not os.path.exists(pdf_file_path):
                raise FileNotFoundError(f"Fichier PDF introuvable: {pdf_file_path}")

            from .pdf_parser import parse_pdf_to_structured_json, create_book_hierarchy_from_json, extract_cover_from_pdf

            _save_book_fields(book, processing_progress=35)

            # Extraire la couverture si possible
            try:
                cover_path = extract_cover_from_pdf(pdf_file_path, settings.MEDIA_ROOT)
                if cover_path:
                    _save_book_fields(book, cover_image=cover_path)
            except Exception:
                pass

            structured_data = parse_pdf_to_structured_json(pdf_file_path)

            # Optionnel: écrire le JSON structuré sur disque (debug/dev)
            try:
                data_json_path = os.path.join(settings.BASE_DIR, 'data.json')
                with open(data_json_path, 'w', encoding='utf-8') as f:
                    json.dump(structured_data, f, ensure_ascii=False, indent=2)
            except Exception:
                pass

            # Créer la hiérarchie
            _save_book_fields(book, processing_progress=60)
            create_book_hierarchy_from_json(book, structured_data)

        # Étape 2: Génération QCM (si demandée et API key configurée)
        if generate_qcm and getattr(settings, 'OPENAI_API_KEY', ''):
            _save_book_fields(book, processing_progress=80)

            from qcm.utils import generate_qcms_for_book
            nbq = int(nb_questions_per_chapter) if nb_questions_per_chapter else int(
                os.environ.get('QCM_DEFAULT_QUESTIONS', getattr(settings, 'QCM_DEFAULT_QUESTIONS', 5))
            )
            generate_qcms_for_book(
                book=book,
                nb_questions_per_chapter=nbq,
                generate_for_all_chapters=True
            )

        # Finalisation
        _save_book_fields(
            book,
            processing_status='completed',
            processing_progress=100,
            processing_finished_at=timezone.now(),
        )

    except Exception as e:
        tb = traceback.format_exc()
        _save_book_fields(
            book,
            processing_status='failed',
            processing_error=f"{str(e)}\n{tb}",
            processing_finished_at=timezone.now(),
        )
        # Ne pas relancer: on est en background thread
