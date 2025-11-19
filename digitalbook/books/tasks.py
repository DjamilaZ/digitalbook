import os
import sys
import json
import traceback
from datetime import datetime

from celery import shared_task
from django.conf import settings
from django.utils import timezone

from .models import Book


def _load_marked_pdf_parser_for_task():
  """Charge dynamiquement le parseur balisé depuis scripts/algo_balise.py pour la tâche Celery.

  Retourne (parse_marked_pdf, extract_assets) ou (None, None) si l'import échoue.
  """
  try:
      scripts_paths = []
      try:
          base_dir = settings.BASE_DIR
      except Exception:
          base_dir = None
      if base_dir:
          scripts_paths.append(os.path.join(base_dir, "scripts"))
          scripts_paths.append(os.path.join(os.path.dirname(base_dir), "scripts"))
      else:
          scripts_paths.append(os.path.join(os.getcwd(), "scripts"))

      for p in scripts_paths:
          if os.path.isdir(p) and p not in sys.path:
              sys.path.append(p)

      try:
          from algo_balise import parse_marked_pdf, extract_assets  # type: ignore
          return parse_marked_pdf, extract_assets
      except Exception as inner_e:
          print(f"[process_book_task] algo_balise import failed: {inner_e}")
          return None, None
  except Exception as e:
      print(f"[process_book_task] Unexpected error loading algo_balise: {e}")
      return None, None


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 2})
def process_book_task(self, book_id: int, json_structure_file_rel: str = None,
                      generate_qcm: bool = True, nb_questions_per_chapter: int = None):
    """
    Traite un livre en arrière-plan:
    - Parse le PDF (ou importe un JSON fourni) pour créer la hiérarchie du livre
    - Génère les QCMs si demandé
    - Met à jour les champs de progression/statut sur le modèle Book
    """
    book = Book.objects.get(id=book_id)

    # Initialiser le statut de traitement
    book.processing_status = 'processing'
    book.processing_progress = 5
    book.processing_error = None
    book.processing_started_at = timezone.now()
    book.save(update_fields=[
        'processing_status', 'processing_progress', 'processing_error', 'processing_started_at'
    ])

    try:
        # Résoudre le chemin absolu du PDF à partir de book.pdf_url
        pdf_rel_path = book.pdf_url.replace(settings.MEDIA_URL, '') if book.pdf_url else None
        pdf_file_path = os.path.join(settings.MEDIA_ROOT, pdf_rel_path) if pdf_rel_path else None

        # Étape 1: Charger les données (JSON fourni ou parsing PDF)
        book.processing_progress = 15
        book.save(update_fields=['processing_progress'])

        structured_data = None
        json_file_path = None
        if json_structure_file_rel:
            json_file_path = os.path.join(settings.MEDIA_ROOT, json_structure_file_rel)

        if json_file_path and os.path.exists(json_file_path):
            # Utiliser le JSON fourni par l'utilisateur
            print(f"[process_book_task] Loading JSON from {json_file_path}")
            # Supporte les fichiers JSON avec BOM UTF-8 via 'utf-8-sig'
            with open(json_file_path, 'r', encoding='utf-8-sig') as f:
                structured_data = json.load(f)
            # Option: mettre à jour le titre depuis le JSON
            if structured_data.get('title'):
                book.title = structured_data['title']
                book.save(update_fields=['title'])

            # Créer la hiérarchie depuis le JSON fourni
            book.processing_progress = 40
            book.save(update_fields=['processing_progress'])

            from .hierarchy import create_book_hierarchy_from_provided_json
            print("[process_book_task] Creating hierarchy from provided JSON...")
            create_book_hierarchy_from_provided_json(book, structured_data)
        else:
            # Parser le PDF (aucun JSON fourni)
            if not pdf_file_path or not os.path.exists(pdf_file_path):
                raise FileNotFoundError(f"Fichier PDF introuvable: {pdf_file_path}")

            from .pdf_parser import parse_pdf_to_structured_json, create_book_hierarchy_from_json
            from .hierarchy import create_book_hierarchy_from_provided_json
            from .algo_balise import parse_marked_pdf, extract_assets

            book.processing_progress = 35
            book.save(update_fields=['processing_progress'])

            # Tenter d'utiliser le nouveau parseur basé sur les balises (scripts/algo_balise.py)
            try:
                print("[process_book_task] Parsing PDF with algo_balise.parse_marked_pdf ...")
                structured_data = parse_marked_pdf(pdf_file_path)

                # Extraire les assets (images, tableaux) dans un répertoire partagé 'extracted_assets'
                try:
                    assets_root = os.path.join(getattr(settings, "BASE_DIR", os.getcwd()), "..", "extracted_assets")
                    assets_root = os.path.abspath(assets_root)
                    os.makedirs(assets_root, exist_ok=True)
                    print(f"[process_book_task] Extracting assets to {assets_root} ...")
                    assets, structured_data = extract_assets(pdf_file_path, assets_root, structured_data)
                    try:
                        print(
                            f"[process_book_task] Assets extracted: images={len(assets.get('images', []))}, "
                            f"tables={len(assets.get('tables', []))}"
                        )
                    except Exception:
                        pass
                except Exception as assets_err:
                    print(f"[process_book_task] Asset extraction failed, continuing without assets: {assets_err}")

                # Écrire le JSON structuré dans un fichier data.json (debug/dev)
                try:
                    data_json_path = os.path.join(settings.BASE_DIR, 'data.json')
                    with open(data_json_path, 'w', encoding='utf-8') as f:
                        json.dump(structured_data, f, ensure_ascii=False, indent=2)
                except Exception:
                    # On ignore les erreurs d'écriture de ce fichier de debug
                    pass

                # Créer la hiérarchie avec la nouvelle structure (thematiques / chapters_sans_thematique)
                book.processing_progress = 60
                book.save(update_fields=['processing_progress'])

                print("[process_book_task] Creating hierarchy from marked PDF JSON (algo_balise)...")
                create_book_hierarchy_from_provided_json(book, structured_data)
            except Exception as balise_err:
                # Fallback: utiliser l'ancien parseur basé sur pdf_parser.parse_pdf_to_structured_json
                print("[process_book_task] algo_balise indisponible, fallback sur parse_pdf_to_structured_json ...")
                print(f"[process_book_task] Reason: {balise_err}")
                structured_data = parse_pdf_to_structured_json(pdf_file_path)

                # Écrire le JSON structuré dans un fichier data.json (debug/dev)
                try:
                    data_json_path = os.path.join(settings.BASE_DIR, 'data.json')
                    with open(data_json_path, 'w', encoding='utf-8') as f:
                        json.dump(structured_data, f, ensure_ascii=False, indent=2)
                except Exception:
                    # On ignore les erreurs d'écriture de ce fichier de debug
                    pass

                # Créer la hiérarchie avec l'ancien format (chapters)
                book.processing_progress = 60
                book.save(update_fields=['processing_progress'])

                create_book_hierarchy_from_json(book, structured_data)

        # Étape 2: Génération QCM (si demandée et API key configurée)
        if generate_qcm and getattr(settings, 'OPENAI_API_KEY', ''):
            book.processing_progress = 80
            book.save(update_fields=['processing_progress'])

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
        book.processing_status = 'completed'
        book.processing_progress = 100
        book.processing_finished_at = timezone.now()
        book.save(update_fields=['processing_status', 'processing_progress', 'processing_finished_at'])
        return {
            'book_id': book.id,
            'status': book.processing_status,
            'progress': book.processing_progress
        }

    except Exception as e:
        book.processing_status = 'failed'
        book.processing_finished_at = timezone.now()
        # On conserve l'exception pour debug
        tb = traceback.format_exc()
        book.processing_error = f"{str(e)}\n{tb}"
        book.save(update_fields=['processing_status', 'processing_error', 'processing_finished_at'])
        # Relancer l'exception pour permettre le retry Celery s'il est configuré
        raise
