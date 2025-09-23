import pdfplumber
import json
import re
import unicodedata
import os
import io
import hashlib
import fitz  # PyMuPDF
from PIL import Image

def is_page_number_line(s: str) -> bool:
    """Return True if the line is just a small number (likely a page number)."""
    return bool(re.fullmatch(r"\d{1,3}", s))

def normalize_heading_title(title: str) -> str:
    """Remove stray leading '#' and trim spaces from a heading title."""
    t = re.sub(r"^#+", "", title)
    t = normalize_ws(t)
    # Collapse multiple spaces only
    t = re.sub(r"\s+", " ", t).strip()
    # Fix internal single-letter splits within words (titles only)
    t = cleanup_title_internal_splits(t)
    return t

def is_numeric_heading(title: str) -> bool:
    """Return True if a heading title is only a numeric code like '1' or '1.2' or '2.10.3'."""
    return bool(re.fullmatch(r"\d+(?:\.\d+)*", title))

def get_heading_code(title: str):
    """Extract leading numeric code (e.g. '2.0', '2.18') from a title, else None."""
    m = re.match(r"^(\d+(?:\.\d+)*)\b", title.strip())
    return m.group(1) if m else None

def split_heading_title_and_content(s: str):
    """Split heading at the first colon. Returns (title, remainder_or_None)."""
    if ":" in s:
        left, right = s.split(":", 1)
        left = left.strip()
        right = right.strip()
        return left, (right if right else None)
    return s.strip(), None

def normalize_ws(s: str) -> str:
    """Normalize unicode spaces (NBSP, narrow NBSP, thin space, etc.) to regular spaces."""
    return (
        s.replace("\u00A0", " ")  # NBSP
         .replace("\u202F", " ")  # NARROW NBSP
         .replace("\u2009", " ")  # THIN SPACE
         .replace("\u200A", " ")  # HAIR SPACE
         .replace("\u2007", " ")  # FIGURE SPACE
         .replace("\u2002", " ")  # EN SPACE
         .replace("\u2003", " ")  # EM SPACE
         .replace("\u2004", " ")  # THREE-PER-EM SPACE
         .replace("\u2005", " ")  # FOUR-PER-EM SPACE
         .replace("\u2006", " ")  # SIX-PER-EM SPACE
         .replace("\u2008", " ")  # PUNCTUATION SPACE
         .replace("\u205F", " ")  # MEDIUM MATHEMATICAL SPACE
         .replace("\u200B", "")   # ZERO WIDTH SPACE
         .replace("\ufeff", "")   # BOM
    )

def cleanup_title_internal_splits(t: str) -> str:
    """Merge isolated single-letter tokens back into previous word inside titles.
    Example: 'fonctionnemen t' -> 'fonctionnement', 'Schma du' unaffected.
    """
    tokens = t.split()
    merged = []
    for tok in tokens:
        if (
            merged
            and len(tok) == 1
            and re.fullmatch(r"[A-Za-zÀ-ÿ]", tok)
            and re.fullmatch(r"[A-Za-zÀ-ÿ]+", merged[-1])
            and len(merged[-1]) >= 3
        ):
            merged[-1] = merged[-1] + tok
        else:
            merged.append(tok)
    return " ".join(merged)

def is_fragment_line(line: str) -> bool:
    """Return True if line is 1-3 letters possibly separated by spaces (e.g., 'g', 'r e')."""
    s = normalize_ws(line)
    s = re.sub(r"\s+", "", s)
    # Remove any non-letter residuals (punctuation/invisibles)
    letters = re.sub(r"[^A-Za-zÀ-ÿ]", "", s)
    return 1 <= len(letters) <= 3 and bool(re.fullmatch(r"[A-Za-zÀ-ÿ]+", letters))

def merge_fragment_into_title(title: str, fragment: str) -> str:
    """Append compacted fragment letters to the end of the last word in title."""
    tit = normalize_ws(title)
    frag = normalize_ws(fragment)
    frag = re.sub(r"\s+", "", frag)
    if not frag:
        return tit
    return (tit + frag) if re.search(r"[A-Za-zÀ-ÿ]$", tit) else (tit + " " + frag)

def is_toc_misc_line(s: str) -> bool:
    """Heuristic to skip TOC-like lines that aren't actual content (Tableau/x, Annexe/s)."""
    return bool(re.match(r"^(?:Tableau|Tableaux|Annexe|Annexes)\b", s, flags=re.IGNORECASE))

def extract_images_for_page(doc, page_num: int, images_dir: str, image_hashes: set, image_by_hash: dict):
    """Extract images from a given page using PyMuPDF. Returns list of image metadata dicts."""
    os.makedirs(images_dir, exist_ok=True)
    page = doc.load_page(page_num)
    out = []
    for img_index, img in enumerate(page.get_images(full=True)):
        xref = img[0]
        base_image = doc.extract_image(xref)
        image_bytes = base_image.get("image")
        if not image_bytes:
            continue
        img_hash = hashlib.md5(image_bytes).hexdigest()
        if img_hash in image_by_hash:
            # Reuse previously saved metadata to avoid creating duplicate files
            out.append(image_by_hash[img_hash])
            continue
        image_hashes.add(img_hash)
        pil_img = Image.open(io.BytesIO(image_bytes))
        if pil_img.mode != 'RGB':
            pil_img = pil_img.convert('RGB')
        filename = f"img_p{page_num+1}_{img_index}_{img_hash[:8]}.png"
        filepath = os.path.join(images_dir, filename)
        pil_img.save(filepath, 'PNG')
        meta = {
            'page': page_num + 1,
            'index': img_index,
            'filename': filename,
            'filepath': filepath,
            'url': f"/assets/images/{filename}",
            'hash': img_hash
        }
        image_by_hash[img_hash] = meta
        out.append(meta)
    return out

def parse_pdf_to_json(pdf_path, output_json):
    structure = []
    current_chapter = None
    current_section = None
    current_subsection = None
    # Index des sections par code numérique (réinitialisé à chaque chapitre)
    sections_index = {}
    # Gestion des images
    images_dir = os.path.join('extracted_assets', 'images')
    image_hashes = set()
    image_by_hash = {}
    page_images_cache = {}
    page_images_ptr = {}

    with pdfplumber.open(pdf_path) as pdf, fitz.open(pdf_path) as doc:
        for page_num, page in enumerate(pdf.pages):
            text = page.extract_text()
            if not text:
                continue
            for line in text.split("\n"):
                line = line.strip()
                if not line:
                    continue
                # Skip page numbers (standalone digits)
                if is_page_number_line(line):
                    continue
                # Skip any line containing the ignore marker "!!"
                if "!!" in line:
                    continue

                # Détection des balises (accepte #, ##, ### avec ou sans espace)
                m_sub = re.match(r'^\s*#{3,}\s*(.+)$', line)
                m_sec = re.match(r'^\s*##(?!#)\s*(.+)$', line)
                m_ch = re.match(r'^\s*#(?!#)\s*(.+)$', line)

                if m_sub:  # Sous-section
                    raw = m_sub.group(1).strip()
                    left, right = split_heading_title_and_content(raw)
                    current_subsection = {
                        "title": normalize_heading_title(left),
                        "content": [],
                        "images": []
                    }
                    if current_section is None:
                        # Créer une section par défaut si une sous-section apparaît avant une section
                        current_section = {
                            "title": "Section",
                            "content": [],
                            "subsections": [],
                            "images": []
                        }
                        if current_chapter is None:
                            # Créer un chapitre par défaut si nécessaire
                            current_chapter = {
                                "title": "Chapitre",
                                "content": [],
                                "sections": []
                            }
                            structure.append(current_chapter)
                        current_chapter["sections"].append(current_section)
                    if right:
                        current_subsection["content"].append(right)
                    current_section["subsections"].append(current_subsection)

                elif m_sec:  # Section
                    raw = m_sec.group(1).strip()
                    left, right = split_heading_title_and_content(raw)
                    sec_title = normalize_heading_title(left)
                    code = get_heading_code(sec_title)

                    # Find if this section already exists anywhere in the structure
                    existing_section = None
                    for chapter in structure:
                        for section in chapter.get("sections", []):
                            # Match by title, or by code if the title is just a number
                            if section.get("title") == sec_title or (code and get_heading_code(section.get("title")) == code):
                                existing_section = section
                                break
                        if existing_section:
                            break

                    if existing_section:
                        # A section with this title/code already exists, so we'll merge into it.
                        current_section = existing_section
                        # If the new title is more descriptive, update it.
                        if len(sec_title) > len(current_section.get("title", "")):
                            current_section["title"] = sec_title
                        if right:
                            current_section.setdefault("content", [])
                            current_section["content"].append(right)
                    else:
                        # This is a new section, create it.
                        if current_chapter is None:
                            # If we are not in a chapter, create a default one.
                            current_chapter = {"title": "Chapitre", "content": [], "sections": []}
                            structure.append(current_chapter)
                        
                        current_section = {
                            "title": sec_title,
                            "content": [],
                            "subsections": [],
                            "images": []
                        }
                        current_chapter["sections"].append(current_section)
                        if code:
                            sections_index[code] = current_section
                        if right:
                            current_section["content"].append(right)
                    current_subsection = None

                elif m_ch:  # Chapitre
                    raw = m_ch.group(1).strip()
                    left, right = split_heading_title_and_content(raw)
                    ch_title = normalize_heading_title(left)
                    existing_chapter = next((ch for ch in structure if ch.get("title") == ch_title), None)

                    if existing_chapter:
                        current_chapter = existing_chapter
                    else:
                        current_chapter = {
                            "title": ch_title,
                            "content": [],
                            "sections": []
                        }
                        structure.append(current_chapter)

                    if right:
                        current_chapter.setdefault("content", [])
                        current_chapter["content"].append(right)
                    current_section = None
                    current_subsection = None
                    # Rebuild sections_index for the current chapter to handle section merging correctly
                    sections_index = {get_heading_code(sec['title']): sec for sec in current_chapter['sections'] if get_heading_code(sec['title'])}

                else:  # Contenu normal
                    # Image caption detection: text wrapped in asterisks like *My image title*
                    m_imgcap = re.search(r'\*(.+?)\*', line)
                    if m_imgcap:
                        img_title = m_imgcap.group(1).strip()
                        # Ensure images for this page are extracted and cached
                        if page_num not in page_images_cache:
                            page_images_cache[page_num] = extract_images_for_page(doc, page_num, images_dir, image_hashes, image_by_hash)
                            page_images_ptr[page_num] = 0
                        # Pick the next available image on this page
                        img_list = page_images_cache.get(page_num, [])
                        ptr = page_images_ptr.get(page_num, 0)
                        if ptr < len(img_list):
                            img_meta = img_list[ptr]
                            page_images_ptr[page_num] = ptr + 1
                            # Attach image to the deepest level (subsection > section)
                            target = current_subsection if current_subsection is not None else current_section
                            if target is not None:
                                target.setdefault("images", [])
                                target["images"].append({
                                    "title": img_title,
                                    "url": img_meta["url"],
                                    "filename": img_meta["filename"],
                                    "page": img_meta["page"],
                                    "index": img_meta["index"]
                                })
                            # Do not add this caption line to textual content
                            continue

                    # Si le dernier titre est uniquement numérique (ex: "1.0"),
                    # et que la ligne courante ressemble au libellé du titre (ex: "Glossaire"),
                    # fusionner pour former un titre complet (ex: "1.0 Glossaire").
                    if current_subsection is not None and is_numeric_heading(current_subsection["title"]):
                        if not is_page_number_line(line) and not re.match(r'^\s*#', line):
                            new_title = normalize_heading_title(f"{current_subsection['title']} {line}")
                            # Déduplication: fusionner si une sous-section du même titre existe déjà
                            if current_section is not None:
                                for ss in list(current_section["subsections"]):
                                    if ss is current_subsection:
                                        continue
                                    if ss["title"] == new_title:
                                        # Fusionner contenu et supprimer l'ancien doublon
                                        ss["content"].extend(current_subsection.get("content", []))
                                        current_section["subsections"].remove(current_subsection)
                                        current_subsection = ss
                                        break
                            current_subsection["title"] = new_title
                            continue  # ne pas ajouter cette ligne au contenu

                    if current_section is not None and is_numeric_heading(current_section["title"]):
                        if not is_page_number_line(line) and not re.match(r'^\s*#', line):
                            new_title = normalize_heading_title(f"{current_section['title']} {line}")
                            # Déduplication: fusionner si une section du même titre existe déjà
                            if current_chapter is not None:
                                for sec in list(current_chapter["sections"]):
                                    if sec is current_section:
                                        continue
                                    if sec["title"] == new_title:
                                        # Fusionner contenu et sous-sections
                                        sec["content"].extend(current_section.get("content", []))
                                        sec["subsections"].extend(current_section.get("subsections", []))
                                        current_chapter["sections"].remove(current_section)
                                        current_section = sec
                                        break
                            current_section["title"] = new_title
                            continue  # ne pas ajouter cette ligne au contenu

                    # Filtrer les lignes parasites du sommaire sous la section 6.0
                    if current_section is not None:
                        sec_code = get_heading_code(current_section.get("title", "") or "")
                        if sec_code == "6.0":
                            if is_toc_misc_line(line) or re.match(r'^\d+(?:\.\d+)*\b', line):
                                continue

                    # Merge tiny letter fragments into the current title instead of content
                    if current_subsection is not None and is_fragment_line(line):
                        current_subsection["title"] = merge_fragment_into_title(current_subsection["title"], line)
                        continue
                    if current_section is not None and is_fragment_line(line):
                        current_section["title"] = merge_fragment_into_title(current_section["title"], line)
                        continue
                    if current_chapter is not None and is_fragment_line(line):
                        current_chapter["title"] = merge_fragment_into_title(current_chapter["title"], line)
                        continue

                    if current_subsection is not None:
                        current_subsection["content"].append(line)
                    elif current_section is not None:
                        current_section["content"].append(line)
                    elif current_chapter is not None:
                        current_chapter["content"].append(line)

    # Sauvegarde JSON
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(structure, f, indent=4, ensure_ascii=False)

    return structure


# Exemple d'utilisation
if __name__ == "__main__":
    pdf_path = "LivretDigitalbalise-1-24.pdf"
    output_json = "structure.json"
    data = parse_pdf_to_json(pdf_path, output_json)
    print(json.dumps(data, indent=4, ensure_ascii=False))


   
