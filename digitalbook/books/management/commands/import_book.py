import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.utils.text import slugify

from books.models import Book, Chapter, Section, Subsection


class Command(BaseCommand):
    help = "Importe un livre, ses chapitres, sections, sous-sections et images depuis un fichier JSON."

    def add_arguments(self, parser):
        parser.add_argument(
            "--json-path",
            type=str,
            default=str(Path("d:/GitHub/digitalbook/livre_digital_structured_v2.json")),
            help="Chemin absolu du fichier JSON structuré à importer",
        )
        parser.add_argument(
            "--title",
            type=str,
            default="LIVRET DIGITAL LEVAGE",
            help="Titre du livre à créer",
        )
        parser.add_argument(
            "--url",
            type=str,
            default=None,
            help="Slug/URL du livre (si non fourni, sera généré depuis le titre)",
        )
        parser.add_argument(
            "--created-by",
            type=str,
            default=None,
            help="Nom d'utilisateur à associer comme créateur (optionnel)",
        )
        parser.add_argument(
            "--replace",
            action="store_true",
            help="Remplacer (supprimer) un livre existant avec le même slug/titre avant import",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Ne pas écrire en base, simuler l'import et afficher un récapitulatif",
        )

    def handle(self, *args, **options):
        json_path = Path(options["json_path"]).expanduser()
        if not json_path.exists():
            raise CommandError(f"Fichier JSON introuvable: {json_path}")

        # Lecture JSON
        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))
        except Exception as e:
            raise CommandError(f"Erreur de lecture JSON: {e}")

        title = options["title"].strip()
        slug = options["url"].strip() if options["url"] else slugify(title)
        replace = options["replace"]
        dry_run = options["dry_run"]

        # Résolution du créateur (optionnel)
        created_by = None
        username = options.get("created_by")
        if username:
            User = get_user_model()
            try:
                created_by = User.objects.get(username=username)
            except User.DoesNotExist:
                self.stdout.write(self.style.WARNING(f"Utilisateur '{username}' introuvable, 'created_by' sera NULL"))

        # Stratégie de remplacement
        existing_qs = Book.objects.filter(title=title) | Book.objects.filter(url=slug)
        if existing_qs.exists():
            if replace:
                if dry_run:
                    self.stdout.write(self.style.WARNING(f"[Dry-run] Suppression de {existing_qs.count()} livre(s) existant(s)"))
                else:
                    existing_qs.delete()
                    self.stdout.write(self.style.SUCCESS("Livre(s) existant(s) supprimé(s)"))
            else:
                raise CommandError(
                    "Un livre avec ce titre/url existe déjà. Utilisez --replace pour le remplacer, ou --url pour un slug différent."
                )

        # Création du Book
        if dry_run:
            self.stdout.write(f"[Dry-run] Création du livre: title='{title}', url='{slug}'")
            book = None  # placeholder
        else:
            book = Book.objects.create(title=title, url=slug, created_by=created_by)
            self.stdout.write(self.style.SUCCESS(f"Livre créé: {book.title} ({book.url})"))

        # L'arbre dans le fichier JSON: { chapters: [ { title, number, sections: [...] } , ... ] }
        total_chapters = 0
        total_sections = 0
        total_subsections = 0

        chapters = data.get("chapters", [])

        def create_section(chapter_obj, section_payload, order_idx):
            nonlocal total_sections, total_subsections
            sec_title = section_payload.get("title", "").strip() or f"Section {order_idx+1}"
            sec_content = section_payload.get("content", "") or ""
            sec_images = section_payload.get("images", []) or []
            sec_tables = section_payload.get("tables", []) or []

            if dry_run:
                self.stdout.write(f"[Dry-run]  - Section[{order_idx}] '{sec_title}' (images={len(sec_images)}, tables={len(sec_tables)})")
                section = None
            else:
                section = Section.objects.create(
                    chapter=chapter_obj,
                    title=sec_title,
                    content=sec_content,
                    order=order_idx,
                    images=sec_images,
                    tables=sec_tables,
                )
            total_sections += 1

            # Sous-sections
            for sub_idx, sub_payload in enumerate(section_payload.get("subsections", []) or []):
                sub_title = sub_payload.get("title", "").strip() or f"Sous-section {sub_idx+1}"
                sub_content = sub_payload.get("content", "") or ""
                sub_images = sub_payload.get("images", []) or []
                sub_tables = sub_payload.get("tables", []) or []

                if dry_run:
                    self.stdout.write(f"[Dry-run]     * Subsection[{sub_idx}] '{sub_title}' (images={len(sub_images)}, tables={len(sub_tables)})")
                else:
                    Subsection.objects.create(
                        section=section,
                        title=sub_title,
                        content=sub_content,
                        order=sub_idx,
                        images=sub_images,
                        tables=sub_tables,
                    )
                total_subsections += 1

        # Création des chapitres
        for chap_idx, chap in enumerate(chapters):
            chap_title = chap.get("title", f"Chapitre {chap_idx+1}")
            chap_content = chap.get("content", "") or ""
            if dry_run:
                self.stdout.write(f"[Dry-run] Chapitre[{chap_idx}] '{chap_title}'")
                chapter_obj = None
            else:
                chapter_obj = Chapter.objects.create(
                    book=book,
                    title=chap_title,
                    content=chap_content,
                    order=chap_idx,
                )
            total_chapters += 1

            # Sections de chapitre
            for sec_idx, section_payload in enumerate(chap.get("sections", []) or []):
                create_section(chapter_obj, section_payload, sec_idx)

            # Certains fichiers peuvent placer des sections directement au même niveau (au cas où)
            # Si chap contient des clés de type section (rare), on peut les traiter ici si nécessaire.

        self.stdout.write(self.style.SUCCESS(
            f"Import terminé: {total_chapters} chapitre(s), {total_sections} section(s), {total_subsections} sous-section(s)."
        ))
