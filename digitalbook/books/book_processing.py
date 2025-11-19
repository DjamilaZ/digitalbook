import os
import sys
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


def _load_marked_pdf_parser():
    """Charge dynamiquement le parseur balisé depuis scripts/algo_balise.py.

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
            print(f"[process_book_sync] algo_balise import failed: {inner_e}")
            return None, None
    except Exception as e:
        print(f"[process_book_sync] Unexpected error loading algo_balise: {e}")
        return None, None


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
    print(f"[process_book_sync] Start for book_id={book_id}")
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
        print(f"[process_book_sync] json_structure_file_rel={json_structure_file_rel}")
        print(f"[process_book_sync] Resolved json_file_path={json_file_path}")

        if json_file_path and os.path.exists(json_file_path):
            # Utiliser le JSON fourni par l'utilisateur
            print(f"[process_book_sync] Loading JSON from {json_file_path}")
            # Supporte les fichiers JSON avec BOM UTF-8 via 'utf-8-sig'
            with open(json_file_path, 'r', encoding='utf-8-sig') as f:
                structured_data = json.load(f)
            # Normaliser la racine si c'est une liste (chapitres sans thématique)
            if isinstance(structured_data, list):
                print("[process_book_sync] JSON loaded. Root is a list; wrapping into 'chapters_sans_thematique'")
                structured_data = {'chapters_sans_thematique': structured_data}
            else:
                try:
                    print(f"[process_book_sync] JSON loaded. Root keys: {list(structured_data.keys())}")
                except Exception:
                    print("[process_book_sync] JSON loaded.")
            # Option: mettre à jour le titre depuis le JSON
            if isinstance(structured_data, dict) and structured_data.get('title'):
                _save_book_fields(book, title=structured_data['title'])

            # Créer la hiérarchie depuis le JSON fourni
            _save_book_fields(book, processing_progress=40)

            # Import depuis un module dédié pour éviter les dépendances aux vues
            from .hierarchy import create_book_hierarchy_from_provided_json
            print("[process_book_sync] Creating hierarchy from provided JSON...")
            create_book_hierarchy_from_provided_json(book, structured_data)
            print("[process_book_sync] Hierarchy creation done.")
        else:
            # Parser le PDF (aucun JSON fourni)
            if not pdf_file_path or not os.path.exists(pdf_file_path):
                raise FileNotFoundError(f"Fichier PDF introuvable: {pdf_file_path}")

            from .pdf_parser import parse_pdf_to_structured_json, create_book_hierarchy_from_json, extract_cover_from_pdf
            from .hierarchy import create_book_hierarchy_from_provided_json
            from .algo_balise import parse_marked_pdf, extract_assets

            _save_book_fields(book, processing_progress=35)

            # Extraire la couverture si possible (inchangé)
            try:
                cover_path = extract_cover_from_pdf(pdf_file_path, settings.MEDIA_ROOT)
                if cover_path:
                    _save_book_fields(book, cover_image=cover_path)
            except Exception:
                pass

            # Tenter d'utiliser le nouveau parseur basé sur les balises (scripts/algo_balise.py)
            try:
                print("[process_book_sync] Parsing PDF with algo_balise.parse_marked_pdf ...")
                structured_data = parse_marked_pdf(pdf_file_path)

                # Extraire les assets (images, tableaux) dans un répertoire partagé 'extracted_assets'
                try:
                    # Un niveau au-dessus de BASE_DIR pour matcher le dossier racine 'extracted_assets'
                    assets_root = os.path.join(getattr(settings, "BASE_DIR", os.getcwd()), "..", "extracted_assets")
                    assets_root = os.path.abspath(assets_root)
                    os.makedirs(assets_root, exist_ok=True)
                    print(f"[process_book_sync] Extracting assets to {assets_root} ...")
                    assets, structured_data = extract_assets(pdf_file_path, assets_root, structured_data)
                    try:
                        print(
                            f"[process_book_sync] Assets extracted: images={len(assets.get('images', []))}, "
                            f"tables={len(assets.get('tables', []))}"
                        )
                    except Exception:
                        pass
                except Exception as assets_err:
                    print(f"[process_book_sync] Asset extraction failed, continuing without assets: {assets_err}")

                # Optionnel: écrire le JSON structuré sur disque (debug/dev)
                try:
                    data_json_path = os.path.join(settings.BASE_DIR, 'data.json')
                    with open(data_json_path, 'w', encoding='utf-8') as f:
                        json.dump(structured_data, f, ensure_ascii=False, indent=2)
                except Exception:
                    pass

                # Créer la hiérarchie avec la nouvelle structure (thematiques / chapters_sans_thematique)
                _save_book_fields(book, processing_progress=60)
                print("[process_book_sync] Creating hierarchy from marked PDF JSON (algo_balise)...")
                create_book_hierarchy_from_provided_json(book, structured_data)
            except Exception as balise_err:
                # Fallback: utiliser l'ancien parseur basé sur pdf_parser.parse_pdf_to_structured_json
                print("[process_book_sync] algo_balise indisponible, fallback sur parse_pdf_to_structured_json ...")
                print(f"[process_book_sync] Reason: {balise_err}")
                print("[process_book_sync] Parsing PDF to structured JSON...")
                structured_data = parse_pdf_to_structured_json(pdf_file_path)

                # Optionnel: écrire le JSON structuré sur disque (debug/dev)
                try:
                    data_json_path = os.path.join(settings.BASE_DIR, 'data.json')
                    with open(data_json_path, 'w', encoding='utf-8') as f:
                        json.dump(structured_data, f, ensure_ascii=False, indent=2)
                except Exception:
                    pass

                # Créer la hiérarchie avec l'ancien format (chapters)
                _save_book_fields(book, processing_progress=60)
                print("[process_book_sync] Creating hierarchy from parsed PDF JSON (fallback)...")
                create_book_hierarchy_from_json(book, structured_data)

        # Étape: Détection de langue (après création de la hiérarchie)
        try:
            detected_lang = _detect_language_for_book(book)
            if detected_lang and detected_lang in ('fr', 'en', 'pt'):
                _save_book_fields(book, language=detected_lang)
        except Exception:
            pass

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
        print("[process_book_sync] Finalizing: status=completed")
        _save_book_fields(
            book,
            processing_status='completed',
            processing_progress=100,
            processing_finished_at=timezone.now(),
        )

    except Exception as e:
        tb = traceback.format_exc()
        print(f"[process_book_sync] ERROR: {e}\n{tb}")
        _save_book_fields(
            book,
            processing_status='failed',
            processing_error=f"{str(e)}\n{tb}",
            processing_finished_at=timezone.now(),
        )
        # Ne pas relancer: on est en background thread


def _detect_language_for_book(book: Book) -> str:
    """Détecte une langue globale en échantillonnant le contenu du livre.
    Utilise fastText si disponible; sinon retourne 'fr' par défaut.
    """
    # Collecter un texte représentatif
    parts = [book.title or ""]
    try:
        # Priorité: chapitres puis sections
        for ch in book.chapters.all().order_by('order')[:5]:
            parts.append(ch.title or "")
            if ch.content:
                parts.append(ch.content[:2000])
            for sec in ch.sections.all().order_by('order')[:3]:
                parts.append(sec.title or "")
                if sec.content:
                    parts.append(sec.content[:1000])
    except Exception:
        pass

    text = "\n".join([p for p in parts if p])[:10000]  # limite 10k
    text = _clean_text(text)
    if not text:
        return 'fr'

    try:
        import fasttext  # type: ignore
        import os
        model_path = os.getenv('FASTTEXT_LANG_MODEL', 'lid.176.bin')
        if not hasattr(_detect_language_for_book, '_model'):
            _detect_language_for_book._model = fasttext.load_model(model_path)
        model = _detect_language_for_book._model
        labels, probs = model.predict(text, k=1)
        lang = labels[0].replace('__label__', '')
        conf = float(probs[0])
        if lang.startswith('fr'):
            return 'fr'
        if lang.startswith('en'):
            return 'en'
        if lang.startswith('pt'):
            return 'pt'
        # fallback simple
        return 'fr'
    except Exception:
        return 'fr'


def _clean_text(s: str) -> str:
    try:
        import re
        s = re.sub(r"<[^>]+>", " ", s or "")
        s = re.sub(r"\s+", " ", s).strip()
        return s
    except Exception:
        return s or ""
