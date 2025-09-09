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
    # Modèle pour les titres de chapitre (ex: "1. Introduction")
    h1_pattern = re.compile(r'^(\d+)\.\s+(.+)$')
    # Modèle pour les sections (ex: "1.1 Présentation")
    h2_pattern = re.compile(r'^(\d+\.\d+)\s+(.+)$')
    # Modèle pour les sous-sections (ex: "1.1.1 Objectifs")
    h3_pattern = re.compile(r'^(\d+\.\d+\.\d+)\s+(.+)$')

    # Vérifier les motifs dans l'ordre de spécificité (du plus précis au moins précis)
    h3_match = h3_pattern.match(line)
    if h3_match:
        return 'h3', h3_match.group(2).strip(), h3_match.group(1)
    
    h2_match = h2_pattern.match(line)
    if h2_match:
        return 'h2', h2_match.group(2).strip(), h2_match.group(1)
    
    h1_match = h1_pattern.match(line)
    if h1_match:
        return 'h1', h1_match.group(2).strip(), int(h1_match.group(1))
    
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

def save_image(image, prefix, page_num, index, output_dir):
    """Sauvegarde une image et retourne le chemin relatif"""
    # Créer un nom de fichier unique pour l'image
    img_hash = hashlib.md5(image.tobytes()).hexdigest()[:8]
    filename = f"{prefix}_p{page_num+1}_{index}_{img_hash}.png"
    filepath = os.path.join(output_dir, filename)
    
    # Créer le dossier s'il n'existe pas
    os.makedirs(output_dir, exist_ok=True)
    
    # Sauvegarder l'image
    if image.mode != 'RGB':
        image = image.convert('RGB')
    image.save(filepath, 'PNG')
    
    return {
        'path': filepath,
        'url': f"/assets/{os.path.basename(output_dir)}/{filename}",
        'alt': f"Image {index+1} de la page {page_num+1}"
    }

def extract_tables(pdf_path, page_num, output_dir, total_pages):
    """Extrait les tableaux d'une page et les sauvegarde"""
    tables = []
    
    try:
        # Ouvrir le PDF avec pdfplumber
        with pdfplumber.open(pdf_path) as pdf:
            # Vérifier que le numéro de page est valide
            if page_num < len(pdf.pages):
                pdf_page = pdf.pages[page_num]
                
                # Extraire les tableaux
                for i, table in enumerate(pdf_page.extract_tables()):
                    # Créer une représentation texte du tableau
                    table_text = []
                    for row in table:
                        table_text.append(" | ".join(str(cell or "").strip() for cell in row))
                    
                    # Créer un nom de fichier pour le tableau
                    filename = f"table_p{page_num+1}_{i+1}.txt"
                    filepath = os.path.join(output_dir, filename)
                    
                    # Sauvegarder le tableau
                    os.makedirs(output_dir, exist_ok=True)
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write("\n".join(table_text))
                    
                    tables.append({
                        'path': filepath,
                        'url': f"/assets/{os.path.basename(output_dir)}/{filename}",
                        'content': table_text,
                        'page': page_num + 1
                    })
    except Exception as e:
        print(f"Erreur lors de l'extraction des tableaux de la page {page_num + 1}: {str(e)}")
    
    return tables

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
                "content": "",
                "images": [],
                "tables": []
            }
            
            # Ajouter la sous-section à la section actuelle ou au chapitre si pas de section
            if current_section:
                current_section["subsections"].append(current_subsection)
            elif current_chapter:
                # Si pas de section parente, ajouter directement au chapitre
                current_chapter["subsections"] = current_chapter.get("subsections", []) + [current_subsection]
            else:
                # Si ni chapitre ni section, créer une structure minimale
                chapter_num = int(subsection_num.split('.')[0])
                chapter_key = f"{chapter_num:02d}"
                if chapter_key not in chapters_dict:
                    current_chapter = {
                        "title": f"{chapter_num}.0 (Titre non trouvé)",
                        "number": chapter_num,
                        "sections": [],
                        "content": "",
                        "images": [],
                        "tables": []
                    }
                    chapters_dict[chapter_key] = current_chapter
                    chapter_order.append(chapter_key)
                    document["chapters"].append(current_chapter)
                
                # Ajouter la sous-section directement au chapitre
                current_chapter["subsections"] = current_chapter.get("subsections", []) + [current_subsection]
        
        elif level == 'p':
            # Ajoute le contenu à l'élément le plus récent
            if current_subsection:
                current_subsection["content"] += text + " "
            elif current_section:
                current_section["content"] += text + " "
            elif current_chapter:
                # Ce contenu est l'introduction du chapitre, avant la première sous-section
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

    return document

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
                'subsections': [{
                    'type': 'subsection',
                    'number': extract_number(sub.get('title', '0.0')),
                    'title': sub.get('title', ''),
                    'start_page': 0,
                    'end_page': 9999
                } for sub in chapter.get('subsections', [])]
            })
    
    # Dictionnaire pour suivre les images déjà enregistrées (éviter les doublons)
    image_hashes = set()
    
    # Initialiser les listes d'images et tableaux dans la structure
    if structured_data is not None:
        if 'images' not in structured_data:
            structured_data['images'] = []
        if 'tables' not in structured_data:
            structured_data['tables'] = []
    
    # 1. Extraire les images avec PyMuPDF
    try:
        doc = fitz.open(pdf_path)
        
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            
            # Extraire les images
            for img_index, img in enumerate(page.get_images(full=True)):
                xref = img[0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                
                # Vérifier si l'image a déjà été traitée (éviter les doublons)
                img_hash = hashlib.md5(image_bytes).hexdigest()
                if img_hash in image_hashes:
                    continue
                image_hashes.add(img_hash)
                
                # Enregistrer l'image
                image = Image.open(io.BytesIO(image_bytes))
                if image.mode != 'RGB':
                    image = image.convert('RGB')
                    
                # Créer un nom de fichier unique
                filename = f"img_p{page_num+1}_{img_index}_{img_hash[:8]}.png"
                filepath = os.path.join(images_dir, filename)
                image.save(filepath, 'PNG')
                
                # Trouver le contexte (chapitre et sous-section) de l'image
                context = find_context_for_page(chapter_contexts, page_num + 1)
                
                # Créer l'objet image avec métadonnées
                image_data = {
                    'id': f"img_{page_num+1}_{img_index}",
                    'page': page_num + 1,
                    'index': img_index,
                    'filename': filename,
                    'filepath': filepath,
                    'url': f"/assets/images/{filename}",
                    'width': image.width,
                    'height': image.height,
                    'hash': img_hash,
                    'context': context,
                    'title': f"Figure {len(assets['images']) + 1}",
                    'description': f"Image {len(assets['images']) + 1} de la page {page_num + 1}"
                }
                
                # Ajouter aux assets globaux
                assets['images'].append(image_data)
                
                # Ajouter aux images globales de la structure
                if structured_data is not None:
                    structured_data['images'].append({
                        'id': image_data['id'],
                        'url': image_data['url'],
                        'title': image_data['title'],
                        'description': image_data['description'],
                        'page': image_data['page']
                    })
    
    finally:
        if 'doc' in locals():
            doc.close()
    
    # 2. Extraire les tableaux avec pdfplumber
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                # Extraire les tableaux de la page
                tables = page.extract_tables()
                
                for table_index, table in enumerate(tables):
                    # Créer une représentation texte du tableau
                    table_text = []
                    for row in table:
                        table_text.append(" | ".join(str(cell or "").strip() for cell in row))
                    
                    # Créer un nom de fichier pour le tableau
                    filename = f"table_p{page_num+1}_{table_index+1}.txt"
                    filepath = os.path.join(tables_dir, filename)
                    
                    # Sauvegarder le tableau
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write("\n".join(table_text))
                    
                    # Créer l'objet tableau avec métadonnées
                    table_data = {
                        'id': f"table_{page_num+1}_{table_index}",
                        'page': page_num + 1,
                        'index': table_index,
                        'filename': filename,
                        'filepath': filepath,
                        'url': f"/assets/tables/{filename}",
                        'rows': len(table),
                        'columns': len(table[0]) if table else 0,
                        'title': f"Tableau {len(assets['tables']) + 1}",
                        'content': table_text
                    }
                    
                    # Ajouter aux assets globaux
                    assets['tables'].append(table_data)
                    
                    # Ajouter aux tableaux globaux de la structure
                    if structured_data is not None:
                        structured_data['tables'].append({
                            'id': table_data['id'],
                            'url': table_data['url'],
                            'title': table_data['title'],
                            'page': table_data['page'],
                            'rows': table_data['rows'],
                            'columns': table_data['columns']
                        })
    except Exception as e:
        print(f"Erreur lors de l'extraction des tableaux : {str(e)}")
    
    # Enregistrer les métadonnées dans un fichier JSON
    metadata_file = os.path.join(output_dir, 'assets_metadata.json')
    with open(metadata_file, 'w', encoding='utf-8') as f:
        json.dump(assets, f, ensure_ascii=False, indent=2)
    
    print(f"[SUCCES] Extraction des assets terminée. Métadonnées enregistrées dans {metadata_file}")
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
    context = {
        'chapter': None,
        'subsection': None
    }
    
    if not chapter_contexts:
        return context
    
    # Trouver le chapitre correspondant
    current_chapter = None
    for chapter in chapter_contexts:
        if page_num >= chapter.get('start_page', 0) and page_num <= chapter.get('end_page', 9999):
            current_chapter = {
                'number': chapter.get('number', 0),
                'title': chapter.get('title', '')
            }
            context['chapter'] = current_chapter
            
            # Essayer de trouver la sous-section correspondante
            for sub in chapter.get('subsections', []):
                if page_num >= sub.get('start_page', 0) and page_num <= sub.get('end_page', 9999):
                    context['subsection'] = {
                        'number': sub.get('number', (0, 0)),
                        'title': sub.get('title', '')
                    }
                    break
            break
    
    return context

def main():
    pdf_file = "Livretdigital.pdf"
    
    # 1. Extraire la structure du texte
    structured_data = parse_pdf_to_structured_json(pdf_file)
    
    # Enregistrer la structure du texte
    output_file = "ebook_structure_detailed.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(structured_data, f, ensure_ascii=False, indent=4)
    print(f"[SUCCES] La structure détaillée du PDF a été extraite dans '{output_file}'")
    
    # 2. Extraire les images et tableaux avec le contexte
    assets_dir = "extracted_assets"
    os.makedirs(assets_dir, exist_ok=True)
    assets, structured_data = extract_assets(pdf_file, assets_dir, structured_data)
    
    # Mettre à jour le fichier de structure avec les images et tableaux
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(structured_data, f, ensure_ascii=False, indent=4)
    
    # Afficher un résumé
    print(f"\nRésumé de l'extraction :")
    print(f"- {len(assets['images'])} images extraites dans {assets['metadata']['images_dir']}")
    print(f"- {len(assets['tables'])} tableaux extraits dans {assets['metadata']['tables_dir']}")
    print(f"- Métadonnées complètes enregistrées dans {os.path.join(assets_dir, 'assets_metadata.json')}")

if __name__ == "__main__":
    main()