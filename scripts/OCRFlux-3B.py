from transformers import AutoProcessor, AutoModelForVision2Seq
from PIL import Image
import torch

# 1️⃣ Charger le modèle multimodal
model_id = "ChatDOC/OCRFlux-3B"
device = "cuda" if torch.cuda.is_available() else "cpu"

print(f"🚀 Chargement du modèle {model_id} sur {device}...")

model = AutoModelForVision2Seq.from_pretrained(
    model_id,
    torch_dtype=torch.float16 if device == "cuda" else torch.float32
).to(device)

processor = AutoProcessor.from_pretrained(model_id)

# 2️⃣ Charger une image de ton PDF
image_path = "dataset/train/page_10.png"  # modifie selon ton chemin
image = Image.open(image_path).convert("RGB")

# 3️⃣ Préparer l’entrée
prompt = "Extract the document structure with titles, sections and content in Markdown."

inputs = processor(
    images=image,
    text=prompt,
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
