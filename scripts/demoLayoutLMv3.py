import os
import json
from pdf2image import convert_from_path
from PIL import Image
import pytesseract
from pytesseract import Output
from transformers import LayoutLMv3Processor, LayoutLMv3ForTokenClassification
import torch
import os
os.environ["HF_HOME"] = "D:/huggingface"
# ⚠️ adapte ce chemin si nécessaire
pytesseract.pytesseract.tesseract_cmd = r"E:\Tesseract-OCR\tesseract.exe"
# ================================
# 1. CONFIG
# ================================
PDF_PATH = "NSL-Rigging-Lifting-Handbook.pdf"
OUTPUT_JSON = "document_structure.json"
MODEL_NAME = "microsoft/layoutlmv3-base"  # modèle pré-entrainé

# ================================
# 2. CONVERTIR PDF EN IMAGES
# ================================
print("📄 Conversion du PDF en images...")
pages = convert_from_path(PDF_PATH, dpi=200)
os.makedirs("pages", exist_ok=True)
page_images = []
for i, page in enumerate(pages):
    path = f"pages/page_{i+1}.png"
    page.save(path, "PNG")
    page_images.append(path)

# ================================
# 3. OCR POUR EXTRAIRE TEXTE + BBOX
# ================================
def normalize_box(bbox, width, height):
    """Convertit une bounding box en pixels vers l’échelle 0-1000."""
    return [
        int(1000 * bbox[0] / width),   # x0
        int(1000 * bbox[1] / height),  # y0
        int(1000 * bbox[2] / width),   # x1
        int(1000 * bbox[3] / height)   # y1
    ]

def extract_words_and_boxes(img_path):
    img = Image.open(img_path).convert("RGB")
    width, height = img.size

    data = pytesseract.image_to_data(img, output_type=Output.DICT)

    words, boxes = [], []
    for i in range(len(data["text"])):
        if int(data["conf"][i]) > 0:  # garder que les détections valides
            word = data["text"][i].strip()
            if word:
                x, y, w, h = data["left"][i], data["top"][i], data["width"][i], data["height"][i]
                # normalisation dans l’intervalle [0, 1000]
                box = normalize_box([x, y, x + w, y + h], width, height)
                words.append(word)
                boxes.append(box)

    return words, boxes, img


# ================================
# 4. INITIALISER LE MODELE
# ================================
print("🤖 Chargement du modèle LayoutLMv3...")
processor = LayoutLMv3Processor.from_pretrained(MODEL_NAME, apply_ocr=False)
model = LayoutLMv3ForTokenClassification.from_pretrained(MODEL_NAME)

# ================================
# 5. ANALYSE PAGE PAR PAGE
# ================================
document_structure = {"pages": []}

for page_id, img_path in enumerate(page_images, 1):
    print(f"🔎 Analyse de la page {page_id}...")
    words, boxes, image = extract_words_and_boxes(img_path)

    if not words:
        continue

    encoding = processor(image, words, boxes=boxes,
                         return_tensors="pt",
                         truncation=True, padding="max_length")

    with torch.no_grad():
        outputs = model(**encoding)

    predictions = outputs.logits.argmax(-1).squeeze().tolist()
    tokens = encoding.tokens()

    page_data = {"page": page_id, "blocks": []}
    for word, box, pred in zip(words, boxes, predictions[:len(words)]):
        label = model.config.id2label[pred]
        page_data["blocks"].append({
            "text": word,
            "bbox": box,
            "label": label
        })

    document_structure["pages"].append(page_data)

# ================================
# 6. RECONSTRUCTION SIMPLE EN JSON
# ================================
# Ici on regroupe par type : TITLE, PARA, TABLE, etc.
chapters = []
current_chapter = {"titre": "", "contenu": "", "sections": []}
current_section = None

for page in document_structure["pages"]:
    for block in page["blocks"]:
        label = block["label"]
        text = block["text"]

        if label in ["TITLE", "HEADER"]:  # Nouveau chapitre/section
            if "chapitre" not in current_chapter["titre"].lower():
                if current_chapter["titre"] or current_chapter["contenu"]:
                    chapters.append(current_chapter)
                current_chapter = {"titre": text, "contenu": "", "sections": []}
            else:
                if current_section:
                    current_chapter["sections"].append(current_section)
                current_section = {"titre": text, "contenu": ""}
        else:
            if current_section:
                current_section["contenu"] += text + " "
            else:
                current_chapter["contenu"] += text + " "

if current_section:
    current_chapter["sections"].append(current_section)
if current_chapter["titre"] or current_chapter["contenu"]:
    chapters.append(current_chapter)

output = {"chapitres": chapters}

with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
    json.dump(output, f, indent=2, ensure_ascii=False)

print(f"✅ Structure extraite et sauvegardée dans {OUTPUT_JSON}")
