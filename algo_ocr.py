import re
import json
import fitz  # PyMuPDF
import pytesseract
from pytesseract import Output
from PIL import Image
import io
import os

# ============================
# OCR Fallback
# ============================
pytesseract.pytesseract.tesseract_cmd = r"E:\Tesseract-OCR\tesseract.exe"
def extract_text_with_ocr(pdf_path):
    """Extrait texte du PDF, OCR fallback si page sans texte natif"""
    doc = fitz.open(pdf_path)
    texte_total = ""

    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text("text")

        if text and text.strip():
            # Texte natif trouvé
            texte_total += text + "\n"
        else:
            # OCR fallback
            print(f"⚠️ OCR utilisé pour la page {page_num+1}")
            pix = page.get_pixmap(dpi=300)
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            ocr_text = pytesseract.image_to_string(img, lang="eng")  # "fra" si document FR
            texte_total += ocr_text + "\n"

    doc.close()
    return texte_total


# ============================
# Classification hiérarchique
# ============================
def classify_line_by_pattern(line):
    """
    Détermine si une ligne est un chapitre, section, sous-section par regex numérotation.
    """
    line = line.strip()

    # CHAPITRE : 1, 2, 3
    if re.match(r"^\d+(\s+.+)?$", line):
        return "chapitre"

    # SECTION : 1.1, 2.3
    if re.match(r"^\d+\.\d+(\s+.+)?$", line):
        return "section"

    # SOUS-SECTION : 1.1.1, 2.3.4
    if re.match(r"^\d+\.\d+\.\d+(\s+.+)?$", line):
        return "sous-section"

    return "texte"


def build_structure(text):
    """
    Construit la hiérarchie JSON à partir du texte OCR/natif.
    """
    lines = text.splitlines()
    structure = {"chapitres": []}
    current_chapitre = None
    current_section = None
    current_sous_section = None

    for line in lines:
        if not line.strip():
            continue

        t = classify_line_by_pattern(line)

        if t == "chapitre":
            current_chapitre = {"titre": line, "contenu": "", "sections": []}
            structure["chapitres"].append(current_chapitre)
            current_section = None
            current_sous_section = None

        elif t == "section":
            if current_chapitre is None:
                current_chapitre = {"titre": "Sans titre", "contenu": "", "sections": []}
                structure["chapitres"].append(current_chapitre)
            current_section = {"titre": line, "contenu": "", "sous_sections": []}
            current_chapitre["sections"].append(current_section)
            current_sous_section = None

        elif t == "sous-section":
            if current_section is None:
                if current_chapitre is None:
                    current_chapitre = {"titre": "Sans titre", "contenu": "", "sections": []}
                    structure["chapitres"].append(current_chapitre)
                current_section = {"titre": "Sans titre", "contenu": "", "sous_sections": []}
                current_chapitre["sections"].append(current_section)
            current_sous_section = {"titre": line, "contenu": ""}
            current_section["sous_sections"].append(current_sous_section)

        else:  # contenu
            if current_sous_section:
                current_sous_section["contenu"] += line + " "
            elif current_section:
                current_section["contenu"] += line + " "
            elif current_chapitre:
                current_chapitre["contenu"] += line + " "
            else:
                # Cas isolé
                if "chapitres" not in structure:
                    structure["chapitres"] = []
                if not structure["chapitres"]:
                    structure["chapitres"].append({"titre": "Intro", "contenu": line, "sections": []})
                else:
                    structure["chapitres"][0]["contenu"] += line + " "

    return structure


# ============================
# Extraction des assets (images / tableaux)
# ============================
def extract_assets(pdf_path, output_dir="assets"):
    """
    Extrait les images du PDF pour les rattacher plus tard à la structure.
    """
    os.makedirs(output_dir, exist_ok=True)
    doc = fitz.open(pdf_path)
    assets = []

    for page_index in range(len(doc)):
        page = doc[page_index]
        for img_index, img in enumerate(page.get_images(full=True)):
            xref = img[0]
            base_image = doc.extract_image(xref)
            img_bytes = base_image["image"]
            ext = base_image["ext"]
            img_path = os.path.join(output_dir, f"page{page_index+1}_img{img_index+1}.{ext}")
            with open(img_path, "wb") as f:
                f.write(img_bytes)
            assets.append({"page": page_index+1, "path": img_path})

    return assets


# ============================
# Main
# ============================
def process_pdf(pdf_path, out_json="output.json"):
    print("📄 Lecture du PDF + OCR fallback...")
    text = extract_text_with_ocr(pdf_path)

    print("🧩 Construction de la structure hiérarchique...")
    structure = build_structure(text)

    print("🖼️ Extraction des assets...")
    assets = extract_assets(pdf_path)

    structure["assets"] = assets

    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(structure, f, indent=2, ensure_ascii=False)

    print(f"✅ JSON sauvegardé : {out_json}")
    return structure


if __name__ == "__main__":
    PDF_PATH = "Livretdigital.pdf"
    OUT_JSON = "document_structure_final.json"
    process_pdf(PDF_PATH, OUT_JSON)
