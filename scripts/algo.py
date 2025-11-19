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

def clean_line(text):
    text = text.strip()
    text = re.sub(r'\s+\d{1,3}$', '', text)
    return text

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
        total_pages = len(pdf.pages)
        for page_num, page in enumerate(pdf.pages):
            page_text = page.extract_text(x_tolerance=2)
            if not page_text:
                continue
            for raw_line in page_text.split('\n'):
                line = clean_line(raw_line)
                if not line:
                    continue
                level, text, number = classify_line_by_pattern(line)
                if level == 'h1':
                    chapter_num = number
                    chapter_key = f"{chapter_num:02d}"
                    if chapter_key in chapters_dict:
                        prev_chapter = current_chapter
                        current_chapter = chapters_dict[chapter_key]
                        if current_chapter.get("title", "").startswith(f"{chapter_num}.0 (Titre non trouvé)") and text:
                            current_chapter["title"] = text
                        if prev_chapter and prev_chapter is not current_chapter and 'end_page' not in prev_chapter:
                            prev_chapter['end_page'] = page_num
                    else:
                        current_chapter = {
                            "title": text,
                            "number": chapter_num,
                            "sections": [],
                            "content": "",
                            "images": [],
                            "tables": [],
                            "start_page": page_num + 1
                        }
                        chapters_dict[chapter_key] = current_chapter
                        chapter_order.append(chapter_key)
                        document["chapters"].append(current_chapter)
                    current_section = None
                    current_subsection = None
                elif level == 'h2':
                    section_num = number
                    if current_chapter is None:
                        chapter_num = int(section_num.split('.')[0])
                        chapter_key = f"{chapter_num:02d}"
                        if chapter_key not in chapters_dict:
                            current_chapter = {
                                "title": f"{chapter_num}.0 (Titre non trouvé)",
                                "number": chapter_num,
                                "sections": [],
                                "content": "",
                                "images": [],
                                "tables": [],
                                "start_page": page_num + 1
                            }
                            chapters_dict[chapter_key] = current_chapter
                            chapter_order.append(chapter_key)
                            document["chapters"].append(current_chapter)
                    existing = None
                    for sec in current_chapter.get("sections", []):
                        if sec.get("number") == section_num:
                            existing = sec
                            break
                    if existing:
                        existing["title"] = text or existing.get("title", "")
                        if 'start_page' not in existing:
                            existing['start_page'] = page_num + 1
                        current_section = existing
                    else:
                        current_section = {
                            "title": text,
                            "number": section_num,
                            "subsections": [],
                            "content": "",
                            "images": [],
                            "tables": [],
                            "start_page": page_num + 1
                        }
                        current_chapter["sections"].append(current_section)
                    if current_subsection and 'end_page' not in current_subsection:
                        current_subsection['end_page'] = page_num
                    current_subsection = None
                elif level == 'h3':
                    subsection_num = number
                    parent_for_sub = current_section
                    if parent_for_sub is None and current_chapter is not None:
                        parent_for_sub = current_chapter
                        if "subsections" not in parent_for_sub:
                            parent_for_sub["subsections"] = []
                    existing_sub = None
                    if parent_for_sub is not None:
                        for sub in parent_for_sub.get("subsections", []):
                            if sub.get("number") == subsection_num:
                                existing_sub = sub
                                break
                    if existing_sub:
                        existing_sub["title"] = text or existing_sub.get("title", "")
                        if 'start_page' not in existing_sub:
                            existing_sub['start_page'] = page_num + 1
                        current_subsection = existing_sub
                    else:
                        current_subsection = {
                            "title": text,
                            "number": subsection_num,
                            "content": "",
                            "images": [],
                            "tables": [],
                            "start_page": page_num + 1
                        }
                        if parent_for_sub is not None:
                            parent_for_sub.setdefault("subsections", []).append(current_subsection)
                    
                elif level == 'p':
                    if current_subsection:
                        current_subsection["content"] += text + " "
                    elif current_section:
                        current_section["content"] += text + " "
                    elif current_chapter:
                        current_chapter["content"] += text + " "

        if current_subsection and 'end_page' not in current_subsection:
            current_subsection['end_page'] = total_pages
        if current_section and 'end_page' not in current_section:
            current_section['end_page'] = total_pages
        if current_chapter and 'end_page' not in current_chapter:
            current_chapter['end_page'] = total_pages

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

def find_node_for_page(structured_data, page_num):
    ch_obj = None
    sec_obj = None
    sub_obj = None
    for ch in structured_data.get('chapters', []):
        cs = ch.get('start_page', 0)
        ce = ch.get('end_page', 0)
        if cs and ce and cs <= page_num <= ce:
            ch_obj = ch
            for sec in ch.get('sections', []):
                ss = sec.get('start_page', 0)
                se = sec.get('end_page', 0)
                if ss and se and ss <= page_num <= se:
                    sec_obj = sec
                    for sub in sec.get('subsections', []):
                        sss = sub.get('start_page', 0)
                        sse = sub.get('end_page', 0)
                        if sss and sse and sss <= page_num <= sse:
                            sub_obj = sub
                            return ch_obj, sec_obj, sub_obj
                    return ch_obj, sec_obj, sub_obj
            for sub in ch.get('subsections', []):
                sss = sub.get('start_page', 0)
                sse = sub.get('end_page', 0)
                if sss and sse and sss <= page_num <= sse:
                    sub_obj = sub
                    return ch_obj, sec_obj, sub_obj
            return ch_obj, sec_obj, sub_obj
    return ch_obj, sec_obj, sub_obj

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
    
    chapter_contexts = []
    
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
                
                ch_obj, sec_obj, sub_obj = find_node_for_page(structured_data or {}, page_num + 1)
                context = {
                    'chapter': {'number': ch_obj.get('number'), 'title': ch_obj.get('title')} if ch_obj else None,
                    'section': {'number': sec_obj.get('number'), 'title': sec_obj.get('title')} if sec_obj else None,
                    'subsection': {'number': sub_obj.get('number'), 'title': sub_obj.get('title')} if sub_obj else None
                }
                
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
                
                if structured_data is not None:
                    structured_data['images'].append({
                        'id': image_data['id'],
                        'url': image_data['url'],
                        'title': image_data['title'],
                        'description': image_data['description'],
                        'page': image_data['page']
                    })
                    if sub_obj is not None:
                        sub_obj.setdefault('images', []).append(image_data)
                    elif sec_obj is not None:
                        sec_obj.setdefault('images', []).append(image_data)
                    elif ch_obj is not None:
                        ch_obj.setdefault('images', []).append(image_data)
    
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
                    
                    if structured_data is not None:
                        structured_data['tables'].append({
                            'id': table_data['id'],
                            'url': table_data['url'],
                            'title': table_data['title'],
                            'page': table_data['page'],
                            'rows': table_data['rows'],
                            'columns': table_data['columns']
                        })
                        ch_obj, sec_obj, sub_obj = find_node_for_page(structured_data or {}, page_num + 1)
                        if sub_obj is not None:
                            sub_obj.setdefault('tables', []).append(table_data)
                        elif sec_obj is not None:
                            sec_obj.setdefault('tables', []).append(table_data)
                        elif ch_obj is not None:
                            ch_obj.setdefault('tables', []).append(table_data)
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
    pdf_file = "IOGP best pratique.pdf"
    
    # 1. Extraire la structure du texte
    structured_data = parse_pdf_to_structured_json(pdf_file)
    
    # Enregistrer la structure du texte
    output_file = "ebook_structure_detailed2.json"
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