import os
import json
import re
import fitz  # PyMuPDF
import pdfplumber
from PIL import Image
import io
import hashlib

# --- Fonction pour classer les lignes ---
def classify_line_by_pattern(line):
    h1_pattern = re.compile(r'^(\d+)\.\s+(.+)$')
    h2_pattern = re.compile(r'^(\d+\.\d+)\s+(.+)$')
    h3_pattern = re.compile(r'^(\d+\.\d+\.\d+)\s+(.+)$')

    h3_match = h3_pattern.match(line)
    if h3_match:
        return 'h3', h3_match.group(2).strip(), h3_match.group(1)
    h2_match = h2_pattern.match(line)
    if h2_match:
        return 'h2', h2_match.group(2).strip(), h2_match.group(1)
    h1_match = h1_pattern.match(line)
    if h1_match:
        return 'h1', h1_match.group(2).strip(), int(h1_match.group(1))
    return 'p', line.strip(), None

def extract_number(s):
    match = re.match(r'^(\d+(?:\.\d+)*)\s*', s)
    if not match:
        return (0, 0)
    numbers = match.group(1).split('.')
    major = int(numbers[0])
    minor = int(numbers[1]) if len(numbers) > 1 else 0
    return (major, minor)

# --- Parsing PDF vers structure JSON ---
def parse_pdf_to_structured_json(pdf_path):
    document = {"chapters": [], "images": [], "tables": []}
    chapters_dict = {}
    chapter_order = []

    current_chapter = None
    current_section = None
    current_subsection = None

    with pdfplumber.open(pdf_path) as pdf:
        full_text = ""
        for page in pdf.pages:
            page_text = page.extract_text(x_tolerance=2)
            if page_text:
                full_text += page_text + "\n"

    lines = full_text.split('\n')
    for line in lines:
        if not line.strip():
            continue
        level, text, number = classify_line_by_pattern(line.strip())
        if level == 'h1':
            chapter_num = number
            chapter_key = f"{chapter_num:02d}"
            current_chapter = {"title": text, "number": chapter_num, "sections": [], "subsections": [], "content": "", "images": [], "tables": []}
            chapters_dict[chapter_key] = current_chapter
            chapter_order.append(chapter_key)
            document["chapters"].append(current_chapter)
            current_section = None
            current_subsection = None
        elif level == 'h2':
            section_num = number
            current_section = {"title": text, "number": section_num, "subsections": [], "content": "", "images": [], "tables": []}
            if current_chapter:
                current_chapter["sections"].append(current_section)
            current_subsection = None
        elif level == 'h3':
            subsection_num = number
            current_subsection = {"title": text, "number": subsection_num, "content": "", "images": [], "tables": []}
            if current_section:
                current_section["subsections"].append(current_subsection)
            elif current_chapter:
                current_chapter["subsections"].append(current_subsection)
        elif level == 'p':
            if current_subsection:
                current_subsection["content"] += text + " "
            elif current_section:
                current_section["content"] += text + " "
            elif current_chapter:
                current_chapter["content"] += text + " "

    # Nettoyage des contenus
    for chapter in document["chapters"]:
        chapter["content"] = " ".join(chapter["content"].split())
        for section in chapter["sections"]:
            section["content"] = " ".join(section["content"].split())
            for subsection in section["subsections"]:
                subsection["content"] = " ".join(subsection["content"].split())
        for subsection in chapter["subsections"]:
            subsection["content"] = " ".join(subsection["content"].split())

    return document

# --- Extraction des assets et rattachement ---
def extract_assets(pdf_path, output_dir, structured_data=None):
    images_dir = os.path.join(output_dir, 'images')
    tables_dir = os.path.join(output_dir, 'tables')
    os.makedirs(images_dir, exist_ok=True)
    os.makedirs(tables_dir, exist_ok=True)

    assets = {'images': [], 'tables': [], 'metadata': {'pdf_path': os.path.abspath(pdf_path), 'images_dir': images_dir, 'tables_dir': tables_dir}}

    # --- Images avec PyMuPDF ---
    doc = fitz.open(pdf_path)
    image_hashes = set()
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        for img_index, img in enumerate(page.get_images(full=True)):
            xref = img[0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            img_hash = hashlib.md5(image_bytes).hexdigest()
            if img_hash in image_hashes:
                continue
            image_hashes.add(img_hash)

            image = Image.open(io.BytesIO(image_bytes))
            if image.mode != 'RGB':
                image = image.convert('RGB')
            filename = f"img_p{page_num+1}_{img_index}_{img_hash[:8]}.png"
            filepath = os.path.join(images_dir, filename)
            image.save(filepath, 'PNG')

            image_data = {'id': f"img_{page_num+1}_{img_index}", 'page': page_num + 1, 'filename': filename, 'filepath': filepath, 'url': f"/assets/images/{filename}", 'width': image.width, 'height': image.height}
            assets['images'].append(image_data)

            # Rattachement à la structure
            if structured_data:
                placed = False
                for chapter in structured_data['chapters']:
                    if page_num + 1 >= 1:  # approximation simple
                        for section in chapter.get('sections', []):
                            for subsection in section.get('subsections', []):
                                if page_num + 1 >= 1:
                                    subsection.setdefault('images', []).append(image_data)
                                    placed = True
                                    break
                            if placed:
                                break
                            section.setdefault('images', []).append(image_data)
                            placed = True
                            break
                        if not placed:
                            chapter.setdefault('images', []).append(image_data)
                        break

    doc.close()

    # --- Tableaux avec pdfplumber ---
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                tables = page.extract_tables()
                for table_index, table in enumerate(tables):
                    table_text = [" | ".join(str(cell or "").strip() for cell in row) for row in table]
                    filename = f"table_p{page_num+1}_{table_index+1}.txt"
                    filepath = os.path.join(tables_dir, filename)
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write("\n".join(table_text))
                    table_data = {'id': f"table_{page_num+1}_{table_index}", 'page': page_num + 1, 'filename': filename, 'filepath': filepath, 'url': f"/assets/tables/{filename}", 'rows': len(table), 'columns': len(table[0]) if table else 0, 'content': table_text}
                    assets['tables'].append(table_data)

                    # Rattachement aux chapitres
                    if structured_data:
                        placed = False
                        for chapter in structured_data['chapters']:
                            if page_num + 1 >= 1:
                                for section in chapter.get('sections', []):
                                    for subsection in section.get('subsections', []):
                                        if page_num + 1 >= 1:
                                            subsection.setdefault('tables', []).append(table_data)
                                            placed = True
                                            break
                                    if placed:
                                        break
                                    section.setdefault('tables', []).append(table_data)
                                    placed = True
                                    break
                                if not placed:
                                    chapter.setdefault('tables', []).append(table_data)
                                break
    except Exception as e:
        print(f"Erreur extraction tableaux: {e}")

    # Enregistrer metadata
    metadata_file = os.path.join(output_dir, 'assets_metadata.json')
    with open(metadata_file, 'w', encoding='utf-8') as f:
        json.dump(assets, f, ensure_ascii=False, indent=2)

    return assets, structured_data

# --- Main ---
def main():
    pdf_file = "Livretdigital.pdf"
    output_file = "ebook_structure_detailed.json"
    assets_dir = "extracted_assets"
    os.makedirs(assets_dir, exist_ok=True)

    structured_data = parse_pdf_to_structured_json(pdf_file)
    assets, structured_data = extract_assets(pdf_file, assets_dir, structured_data)

    # Sauvegarde finale
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(structured_data, f, ensure_ascii=False, indent=4)

    print(f"[SUCCES] Structure et assets extraits.")
    print(f"- {len(assets['images'])} images extraites")
    print(f"- {len(assets['tables'])} tableaux extraits")
    print(f"- Métadonnées enregistrées dans {os.path.join(assets_dir, 'assets_metadata.json')}")

if __name__ == "__main__":
    main()
