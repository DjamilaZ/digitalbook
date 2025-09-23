from transformers import AutoProcessor, AutoModelForImageTextToText
from PIL import Image
import torch, os

# 👉 On redirige tout vers D:
os.environ["HF_HOME"] = "D:/HF_cache"
os.environ["TORCH_HOME"] = "D:/HF_cache/torch"
os.environ["HF_HUB_CACHE"] = "D:/HF_cache"  # important pour huggingface_hub
os.environ["TMP"] = "D:/HF_cache/tmp"
os.environ["TEMP"] = "D:/HF_cache/tmp"

# Créer les dossiers s’ils n’existent pas
os.makedirs("D:/HF_cache/tmp", exist_ok=True)
os.makedirs("D:/HF_cache/torch", exist_ok=True)

# 1️⃣ Charger le modèle multimodal
model_id = "ChatDOC/OCRFlux-3B"
device = "cuda" if torch.cuda.is_available() else "cpu"

print(f"🚀 Chargement du modèle {model_id} sur {device}...")

model = AutoModelForImageTextToText.from_pretrained(
    model_id,
    dtype=torch.float16 if device == "cuda" else torch.float32
).to(device)

processor = AutoProcessor.from_pretrained(model_id)

# 2️⃣ Charger une image de ton PDF
image_path = "dataset/train/page_10.png"
image = Image.open(image_path).convert("RGB")

# 3️⃣ Préparer l’entrée avec placeholder <image>
prompt = "<image>\nExtract the document structure with titles, sections and content in Markdown."

inputs = processor(
    text=prompt,
    images=[image],
    return_tensors="pt"
).to(device)

# 4️⃣ Générer
with torch.no_grad():
    generated_ids = model.generate(
        **inputs,
        max_new_tokens=2048,
    )

# 5️⃣ Décoder
output = processor.batch_decode(generated_ids, skip_special_tokens=True)[0]

print("\n📄 Résultat OCRFlux-3B :\n")
print(output)
