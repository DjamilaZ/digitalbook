import os
import json
import re
import fitz  # PyMuPDF
import pdfplumber
from PIL import Image
import io
import hashlib

def classify_line_by_pattern(line):
    """
    Classe une ligne en fonction de son motif (chapitre, section, sous-section ou paragraphe).
    Retourne un tuple (niveau, contenu, numéro) où niveau est 'h1', 'h2', 'h3' ou 'p'.
    """
    # Modèle pour les sous-sections (ex: "1.1.1 Objectifs") - Le plus spécifique en premier
    h3_pattern = re.compile(r'^(\d+\.\d+\.\d+)\s+(.+)$')
    h3_match = h3_pattern.match(line)
    if h3_match:
        return 'h3', h3_match.group(2).strip(), h3_match.group(1)

    # Modèle générique pour les chapitres et sections (ex: "1.0", "1.1", "7.0")
    hx_pattern = re.compile(r'^(\d+\.\d+)\s+(.+)$')
    hx_match = hx_pattern.match(line)
    if hx_match:
        number_part = hx_match.group(1)
        title_part = hx_match.group(2).strip()
        parts = number_part.split('.')

        # Si la partie après le point est "0", c'est un chapitre (h1)
        if len(parts) == 2 and parts[1] == '0':
            return 'h1', title_part, int(parts[0])
        # Sinon, c'est une section (h2)
        else:
            return 'h2', title_part, number_part
    
    # Modèle pour les chapitres simples (ex: "1. Introduction"), au cas où
    h1_simple_pattern = re.compile(r'^(\d+)\.\s+(.+)$')
    h1_simple_match = h1_simple_pattern.match(line)
    if h1_simple_match:
        return 'h1', h1_simple_match.group(2).strip(), int(h1_simple_match.group(1))

    # Si aucun motif ne correspond, c'est un paragraphe normal
    return 'p', line.strip(), None
def extract_number(s):
    """Extrait le numéro d'une section (ex: '1.1' -> 1.1, '1.10' -> 1.1, '1.01' -> 1.01)"""
    # Recherche le motif numérique au début du titre
    match = re.match(r'^(\d+(?:\.\d+)*)\s*', s)
    if not match:
        return (0, 0)  # Valeur par défaut si pas de numéro
    
    numbers = match.group(1).split('.')
    major = int(numbers[0])
    minor = int(numbers[1]) if len(numbers) > 1 else 0
    
    # Retourne un tuple pour un tri correct (1.2 < 1.10)
    return (major, minor)

def parse_pdf_to_structured_json(pdf_path):
    """
    Fonction principale pour parser le PDF et créer le JSON structuré
    avec chapitres, sections, sous-sections, images et tableaux.
    """
    document = {
        "chapters": [],
        "images": [],
        "tables": []
    }
    
    # Structures pour maintenir l'état de la hiérarchie
    chapters_dict = {}  # Pour suivre les chapitres par leur numéro
    chapter_order = []  # Pour maintenir l'ordre des chapitres
    
    # Variables pour suivre le contexte actuel
    current_chapter = None
    current_section = None
    current_subsection = None
    last_chapter_num = -1

    with pdfplumber.open(pdf_path) as pdf:
        full_text = ""
        for page in pdf.pages:
            page_text = page.extract_text(x_tolerance=2) # Améliore la jointure des mots
            if page_text:
                full_text += page_text + "\n"

    lines = full_text.split('\n')
    for line in lines:
        # Ignorer les lignes vides
        if not line.strip():
            continue
            
        # Classer la ligne
        level, text, number = classify_line_by_pattern(line.strip())
        
        if level == 'h1':
            # Nouveau chapitre (niveau 1)
            chapter_num = number
            chapter_key = f"{chapter_num:02d}"  # Format sur 2 chiffres pour le tri
            
            if chapter_key in chapters_dict:
                current_chapter = chapters_dict[chapter_key]
                # Mettre à jour le titre si c'était un chapitre temporaire
                if current_chapter["title"] == f"{chapter_num}.0 (Titre non trouvé)":
                    current_chapter["title"] = text
            else:
                current_chapter = {
                    "title": text,
                    "number": chapter_num,
                    "order": len(chapter_order),  # Ordre basé sur l'index avant ajout
                    "sections": [],  # Liste des sections du chapitre
                    "content": "",
                    "images": [],
                    "tables": []
                }
                chapters_dict[chapter_key] = current_chapter
                chapter_order.append(chapter_key)
                document["chapters"].append(current_chapter)
            
            # Réinitialiser les niveaux inférieurs
            current_section = None
            current_subsection = None
            
        elif level == 'h2':
            # Nouvelle section (niveau 2)
            section_num = number
            
            # Créer la section si elle n'existe pas déjà
            current_section = {
                "title": text,
                "number": section_num,
                "order": len(current_chapter["sections"]),  # Ordre basé sur l'index dans la liste
                "subsections": [],
                "content": "",
                "images": [],
                "tables": []
            }
            
            # Ajouter la section au chapitre actuel
            if current_chapter:
                current_chapter["sections"].append(current_section)
            else:
                # Si pas de chapitre parent, créer un chapitre temporaire
                chapter_num = int(section_num.split('.')[0])
                chapter_key = f"{chapter_num:02d}"
                if chapter_key not in chapters_dict:
                    current_chapter = {
                        "title": f"{chapter_num}.0 (Titre non trouvé)",
                        "number": chapter_num,
                        "order": len(chapter_order),  # Ordre basé sur l'index avant ajout
                        "sections": [current_section],
                        "content": "",
                        "images": [],
                        "tables": []
                    }
                    chapters_dict[chapter_key] = current_chapter
                    chapter_order.append(chapter_key)
                    document["chapters"].append(current_chapter)
            
            # Réinitialiser le niveau sous-section
            current_subsection = None
            
        elif level == 'h3':
            # Nouvelle sous-section (niveau 3)
            subsection_num = number
            
            # Créer la sous-section
            current_subsection = {
                "title": text,
                "number": subsection_num,
                "order": len(current_section["subsections"]),  # Ordre basé sur l'index dans la liste
                "content": "",
                "images": [],
                "tables": []
            }
            
            # Ajouter la sous-section à la section actuelle ou au chapitre si pas de section
            if current_section:
                current_section["subsections"].append(current_subsection)
            elif current_chapter:
                # Si pas de section parente, ajouter directement au chapitre
                existing_subsections = current_chapter.get("subsections", [])
                current_subsection["order"] = len(existing_subsections)  # Assigner l'ordre
                current_chapter["subsections"] = existing_subsections + [current_subsection]
            else:
                # Si ni chapitre ni section, créer une structure minimale
                chapter_num = int(subsection_num.split('.')[0])
                chapter_key = f"{chapter_num:02d}"
                if chapter_key not in chapters_dict:
                    current_chapter = {
                        "title": f"{chapter_num}.0 (Titre non trouvé)",
                        "number": chapter_num,
                        "order": len(chapter_order),  # Ordre basé sur l'index avant ajout
                        "sections": [],
                        "content": "",
                        "images": [],
                        "tables": []
                    }
                    chapters_dict[chapter_key] = current_chapter
                    chapter_order.append(chapter_key)
                    document["chapters"].append(current_chapter)
                
                existing_subsections = current_chapter.get("subsections", [])
                current_subsection["order"] = len(existing_subsections)  # Assigner l'ordre
                current_chapter["subsections"] = existing_subsections + [current_subsection]
            
        else:
            # Paragraphe normal
            if current_subsection:
                # Ajouter au contenu de la sous-section actuelle
                current_subsection["content"] += text + " "
            elif current_section:
                # Ajouter au contenu de la section actuelle
                current_section["content"] += text + " "
            elif current_chapter:
                # Ajouter au contenu du chapitre actuel
                current_chapter["content"] += text + " "

    # Nettoyer les contenus et trier les sections/sous-sections
    for chapter in document["chapters"]:
        # Nettoyer le contenu du chapitre
        chapter["content"] = " ".join(chapter["content"].split())
        
        # Trier les sections par numéro
        if "sections" in chapter and chapter["sections"]:
            chapter["sections"].sort(key=lambda x: [int(n) for n in x["number"].split('.')])
            
            # Pour chaque section, nettoyer et trier les sous-sections
            for section in chapter["sections"]:
                section["content"] = " ".join(section["content"].split())
                
                if "subsections" in section and section["subsections"]:
                    section["subsections"].sort(key=lambda x: [float(n) for n in x["number"].split('.')])
                    
                    # Nettoyer le contenu des sous-sections
                    for subsection in section["subsections"]:
                        subsection["content"] = " ".join(subsection["content"].split())
        
        # Gérer les sous-sections directes (sans section parente)
        if "subsections" in chapter and chapter["subsections"]:
            chapter["subsections"].sort(key=lambda x: [float(n) for n in x["number"].split('.')])
            for subsection in chapter["subsections"]:
                subsection["content"] = " ".join(subsection["content"].split())
    
    # Trier les chapitres selon l'ordre numérique
    document["chapters"] = [chapters_dict[key] for key in sorted(chapter_order, key=lambda x: int(x) if x.isdigit() else 0)]
    
    # Nettoyage final et tri des sections et sous-sections
    for chapter in document["chapters"]:
        # Initialiser les champs manquants
        if "content" not in chapter:
            chapter["content"] = ""
        else:
            chapter["content"] = chapter["content"].strip()
        
        # S'assurer que les listes de sections et sous-sections existent
        if "sections" not in chapter:  
            chapter["sections"] = []
        
        if "subsections" not in chapter:
            chapter["subsections"] = []
        
        # Nettoyer le contenu des sous-sections directes
        for subsection in chapter["subsections"]:
            if "content" in subsection:
                subsection["content"] = " ".join(str(subsection["content"]).split())
        
        # Trier les sous-sections directes
        if chapter["subsections"]:
            chapter["subsections"].sort(key=lambda x: extract_number(x.get("title", "0")))
        
        # Nettoyer et trier les sections et leurs sous-sections
        for section in chapter["sections"]:
            if "content" not in section:
                section["content"] = ""
            else:
                section["content"] = " ".join(str(section["content"]).split())
            
            if "subsections" not in section:
                section["subsections"] = []
            
            # Nettoyer le contenu des sous-sections de section
            for subsection in section["subsections"]:
                if "content" in subsection:
                    subsection["content"] = " ".join(str(subsection["content"]).split())
            
            # Trier les sous-sections de section
            if section["subsections"]:
                section["subsections"].sort(key=lambda x: extract_number(x.get("title", "0")))
    
    # Logs de fin de parsing
    total_chapters = len(document["chapters"])
    total_sections = sum(len(chapter["sections"]) for chapter in document["chapters"])
    total_subsections = sum(len(section["subsections"]) for chapter in document["chapters"] for section in chapter["sections"])
    
    print(f"\n=== FIN PARSING PDF ===")
    print(f"Chapitres extraits: {total_chapters}")
    print(f"Sections extraites: {total_sections}")
    print(f"Sous-sections extraites: {total_subsections}")
    
    # Afficher un aperçu de la structure
    for i, chapter in enumerate(document["chapters"][:3]):  # Limiter aux 3 premiers chapitres
        print(f"\nChapitre {i+1}: {chapter['title']}")
        print(f"  Sections: {len(chapter['sections'])}")
        for j, section in enumerate(chapter['sections'][:2]):  # Limiter aux 2 premières sections
            print(f"    - Section {j+1}: {section['title']}")
            print(f"      Sous-sections: {len(section['subsections'])}")
    
    if total_chapters > 3:
        print(f"  ... et {total_chapters - 3} autres chapitres")
    
    print(f"=== FIN PARSING PDF ===\n")
    
    return document

def create_book_hierarchy_from_json(book, json_data):
    """
    Crée la hiérarchie complète (chapitres, sections, sous-sections) à partir des données JSON
    et les relie au livre.
    
    Args:
        book: Instance du modèle Book
        json_data: Données structurées du PDF
    
    Returns:
        Le livre avec sa hiérarchie complète
    """
    from .models import Chapter, Section, Subsection
    
    print(f"\n=== DÉBUT CRÉATION HIÉRARCHIE POUR LIVRE: {book.title} ===")
    print(f"Nombre de chapitres trouvés: {len(json_data.get('chapters', []))}")
    
    total_chapters = 0
    total_sections = 0
    total_subsections = 0
    
    for i, chapter_data in enumerate(json_data.get('chapters', [])):
        total_chapters += 1
        print(f"\n--- Création Chapitre {i+1}: {chapter_data.get('title', 'Sans titre')} ---")
        
        # Créer le chapitre
        try:
            chapter = Chapter.objects.create(
                book=book,
                title=chapter_data.get('title', ''),
                content=chapter_data.get('content', ''),
                order=chapter_data.get('order', 0)
            )
            print(f"✓ Chapitre créé avec ID: {chapter.id}")
        except Exception as e:
            print(f"✗ Erreur création chapitre: {e}")
            continue
        
        # Créer les sections du chapitre
        sections_count = len(chapter_data.get('sections', []))
        print(f"Nombre de sections dans ce chapitre: {sections_count}")
        
        for j, section_data in enumerate(chapter_data.get('sections', [])):
            total_sections += 1
            print(f"  - Création Section {j+1}: {section_data.get('title', 'Sans titre')}")
            
            try:
                section = Section.objects.create(
                    chapter=chapter,
                    title=section_data.get('title', ''),
                    content=section_data.get('content', ''),
                    order=section_data.get('order', 0)
                )
                print(f"    ✓ Section créée avec ID: {section.id}")
            except Exception as e:
                print(f"    ✗ Erreur création section: {e}")
                continue
            
            # Créer les sous-sections de la section
            subsections_count = len(section_data.get('subsections', []))
            print(f"    Nombre de sous-sections dans cette section: {subsections_count}")
            
            for k, subsection_data in enumerate(section_data.get('subsections', [])):
                total_subsections += 1
                print(f"      * Création Sous-section {k+1}: {subsection_data.get('title', 'Sans titre')}")
                
                try:
                    subsection = Subsection.objects.create(
                        section=section,
                        title=subsection_data.get('title', ''),
                        content=subsection_data.get('content', ''),
                        order=subsection_data.get('order', 0)
                    )
                    print(f"        ✓ Sous-section créée avec ID: {subsection.id}")
                except Exception as e:
                    print(f"        ✗ Erreur création sous-section: {e}")
                    continue
    
    print(f"\n=== RÉSUMÉ CRÉATION HIÉRARCHIE ===")
    print(f"Livre: {book.title}")
    print(f"Chapitres créés: {total_chapters}")
    print(f"Sections créées: {total_sections}")
    print(f"Sous-sections créées: {total_subsections}")
    print(f"=== FIN CRÉATION HIÉRARCHIE ===\n")
    
    return book


def save_image(image, prefix, page_num, index, output_dir):
    """
    Sauvegarde une image et retourne le chemin relatif
    """
    # Créer un nom de fichier unique
    image_filename = f"{prefix}_p{page_num}_{index}.png"
    image_path = os.path.join(output_dir, image_filename)
    
    # Sauvegarder l'image
    image.save(image_path, 'PNG')
    
    return image_filename


def extract_assets(pdf_path, output_dir, structured_data=None):
    """
    Extrait toutes les images et tableaux du PDF, les enregistre dans des dossiers spécifiques
    et les associe aux chapitres et sous-sections correspondants.
    
    Args:
        pdf_path: Chemin vers le fichier PDF
        output_dir: Dossier de sortie pour les assets
        structured_data: Données structurées du PDF (chapitres/sous-sections)
        
    Returns:
        Tuple (assets, structured_data) avec les assets extraits et les données structurées mises à jour
    """
    # Créer les dossiers de sortie s'ils n'existent pas
    images_dir = os.path.join(output_dir, 'images')
    tables_dir = os.path.join(output_dir, 'tables')
    os.makedirs(images_dir, exist_ok=True)
    os.makedirs(tables_dir, exist_ok=True)
    
    assets = {
        'images': [],
        'tables': [],
        'metadata': {
            'pdf_path': os.path.abspath(pdf_path),
            'images_dir': images_dir,
            'tables_dir': tables_dir
        }
    }
    
    # Préparer la structure pour la recherche de contexte
    chapter_contexts = []
    if structured_data and 'chapters' in structured_data:
        for chapter in structured_data['chapters']:
            chapter_num = extract_number(chapter['title'])[0] if 'title' in chapter else 0
            chapter_contexts.append({
                'type': 'chapter',
                'number': chapter_num,
                'title': chapter.get('title', ''),
                'start_page': 0,
                'end_page': 9999,  # Valeur par défaut élevée
            })
    
    # Ouvrir le PDF avec PyMuPDF pour l'extraction des images
    doc = fitz.open(pdf_path)
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        
        # Extraction des images désactivée pour le moment
    # image_list = page.get_images(full=True)
    # for img_index, img in enumerate(image_list):
    #     xref = img[0]
    #     pix = fitz.Pixmap(doc, xref)
    #     
    #     if pix.n - pix.alpha < 4:  # Vérifier si l'image est en RVB ou en niveaux de gris
    #         # Convertir en PIL Image
    #         img_data = pix.tobytes("png")
    #         pil_image = Image.open(io.BytesIO(img_data))
    #         
    #         # Trouver le contexte pour cette page
    #         context = find_context_for_page(chapter_contexts, page_num + 1)
    #         
    #         # Sauvegarder l'image
    #         image_filename = save_image(
    #             pil_image, 
    #             "img", 
    #             page_num + 1, 
    #             img_index, 
    #             images_dir
    #         )
    #         
    #         # Ajouter aux assets
    #         asset_info = {
    #             'filename': image_filename,
    #             'page': page_num + 1,
    #             'context': context
    #         }
    #         assets['images'].append(asset_info)
    #         
    #         # Associer l'image au contexte approprié
    #         if context and structured_data:
    #             associate_asset_to_context(structured_data, asset_info, context)
    #     
    #     pix = None
    
    # Extraire les tableaux avec pdfplumber
    with pdfplumber.open(pdf_path) as pdf:
        for page_num in range(len(pdf.pages)):
            page = pdf.pages[page_num]
            
            # Extraire les tableaux
            tables = page.extract_tables()
            for table_index, table in enumerate(tables):
                if table and len(table) > 0:
                    # Créer un nom de fichier pour le tableau
                    table_filename = f"table_p{page_num + 1}_{table_index}.txt"
                    table_path = os.path.join(tables_dir, table_filename)
                    
                    # Sauvegarder le tableau
                    with open(table_path, 'w', encoding='utf-8') as f:
                        for row in table:
                            if row:  # Ignorer les lignes vides
                                f.write('|'.join(str(cell) if cell else '' for cell in row) + '\n')
                    
                    # Trouver le contexte pour cette page
                    context = find_context_for_page(chapter_contexts, page_num + 1)
                    
                    # Ajouter aux assets
                    asset_info = {
                        'filename': table_filename,
                        'page': page_num + 1,
                        'context': context
                    }
                    assets['tables'].append(asset_info)
                    
                    # Associer le tableau au contexte approprié
                    if context and structured_data:
                        associate_asset_to_context(structured_data, asset_info, context)
    
    doc.close()
    
    return assets, structured_data


def find_context_for_page(chapter_contexts, page_num):
    """
    Trouve le contexte (chapitre et sous-section) pour un numéro de page donné.
    
    Args:
        chapter_contexts: Liste des contextes de chapitres
        page_num: Numéro de la page à rechercher
        
    Returns:
        Dictionnaire avec les informations de contexte
    """
    # Trouver le chapitre qui contient cette page
    for context in chapter_contexts:
        if context['start_page'] <= page_num <= context['end_page']:
            return context
    
    # Si aucun contexte n'est trouvé, retourner None
    return None


def associate_asset_to_context(structured_data, asset_info, context):
    """
    Associe un asset (image ou tableau) au contexte approprié dans les données structurées.
    
    Args:
        structured_data: Données structurées du PDF
        asset_info: Information sur l'asset
        context: Contexte trouvé pour l'asset
    """
    if not context or 'chapters' not in structured_data:
        return
    
    # Trouver le chapitre correspondant
    for chapter in structured_data['chapters']:
        if (extract_number(chapter['title'])[0] == context['number'] and 
            context['type'] == 'chapter'):
            
            # Ajouter l'asset au chapitre
            if 'images' not in chapter:
                chapter['images'] = []
            if 'tables' not in chapter:
                chapter['tables'] = []
            
            if asset_info['filename'].endswith('.png'):
                chapter['images'].append(asset_info['filename'])
            elif asset_info['filename'].endswith('.txt'):
                chapter['tables'].append(asset_info['filename'])
            
            break
