from django.db import transaction
from .models import Book, Chapter, Section, Subsection, Thematique


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

    # Prioriser l'ordre fourni dans le JSON; sinon utiliser un ordre auto-incrémenté (index, 1-based)
    json_order = chapter_data.get('order')
    order = json_order if json_order is not None else (chapter_index if chapter_index is not None else 0)

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
    for section_index, section_data in enumerate(sections_data, start=1):
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

    # Prioriser l'ordre fourni dans le JSON; sinon utiliser un ordre auto-incrémenté (index, 1-based)
    json_order = section_data.get('order')
    order = json_order if json_order is not None else (section_index if section_index is not None else 0)

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
    for subsection_index, subsection_data in enumerate(subsections_data, start=1):
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

    # Prioriser l'ordre fourni dans le JSON; sinon utiliser un ordre auto-incrémenté (index, 1-based)
    json_order = subsection_data.get('order')
    order = json_order if json_order is not None else (subsection_index if subsection_index is not None else 0)

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
    print(f"\n=== CRÉATION HIÉRARCHIE (hierarchy.py) ===")
    print(f"Livre: {book.title}")
    print(f"Clés racines reçues: {list(structured_data.keys())}")

    try:
        with transaction.atomic():
            # Nouvelle structure avec thematiques et/ou chapitres sans thématique
            if 'thematiques' in structured_data or 'chapters_sans_thematique' in structured_data:
                print("Utilisation de la structure 'thematiques' / 'chapters_sans_thematique'")

                # Mettre à jour le titre du livre si présent
                if 'titre_livre' in structured_data:
                    book.title = structured_data['titre_livre']
                    book.save(update_fields=['title'])
                    print(f"Titre du livre mis à jour: {book.title}")

                # Thématiques
                for thematique_data in structured_data.get('thematiques', []):
                    print(f"\n--- Création thématique: {thematique_data.get('title', 'Sans titre')} ---")
                    thematique = Thematique.objects.create(
                        book=book,
                        title=thematique_data.get('title', 'Thématique sans titre'),
                        description=thematique_data.get('description', '')
                    )
                    print(f"✓ Thématique créée: {thematique.title}")

                    # Chapitres de la thématique
                    for chapter_index, chapter_data in enumerate(thematique_data.get('chapters', []), start=1):
                        create_chapter_from_data(chapter_data, book, thematique, chapter_index)

                # Chapitres sans thématique
                chapters_sans_thematique = structured_data.get('chapters_sans_thematique', [])
                if chapters_sans_thematique:
                    print(f"\n--- Création chapitres sans thématique ---")
                    for chapter_index, chapter_data in enumerate(chapters_sans_thematique, start=1):
                        chapter_data_adapted = {
                            'title': chapter_data.get('titre', chapter_data.get('title', 'Chapitre sans titre')),
                            'content': chapter_data.get('contenu', chapter_data.get('content', '')),
                            'sections': chapter_data.get('sections', []),
                            'order': chapter_data.get('order')
                        }
                        create_chapter_from_data(chapter_data_adapted, book, None, chapter_index)

            # Ancienne structure (chapitres directs)
            elif 'chapitres' in structured_data or 'titre_livre' in structured_data:
                print("Utilisation de la structure 'chapitres' / 'titre_livre'")

                if 'titre_livre' in structured_data:
                    book.title = structured_data['titre_livre']
                    book.save(update_fields=['title'])
                    print(f"Titre du livre mis à jour: {book.title}")

                chapitres_data = structured_data.get('chapitres', [])
                print(f"Nombre de chapitres à créer: {len(chapitres_data)}")
                for chapter_index, chapitre_data in enumerate(chapitres_data, start=1):
                    chapter_data_adapted = {
                        'title': chapitre_data.get('titre', 'Chapitre sans titre'),
                        'content': chapitre_data.get('contenu', ''),
                        'sections': chapitre_data.get('sections', []),
                        'order': chapitre_data.get('order')
                    }
                    create_chapter_from_data(chapter_data_adapted, book, None, chapter_index)

            else:
                print("Structure JSON non reconnue")
                raise ValueError("Structure JSON non reconnue. Les clés attendues sont: 'thematiques'/'chapters_sans_thematique' ou 'chapitres'/'titre_livre'")

            print(f"\n✓ HIÉRARCHIE CRÉÉE AVEC SUCCÈS (hierarchy.py) POUR LE LIVRE: {book.title}")
            return book

    except Exception as e:
        import traceback
        print(f"✗ ERREUR LORS DE LA CRÉATION DE LA HIÉRARCHIE (hierarchy.py): {e}")
        print(f"Traceback: {traceback.format_exc()}")
        raise
