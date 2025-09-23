# train_donut_fixed.py
import os
import json
from PIL import Image
from pathlib import Path

import torch
from torch.nn.utils.rnn import pad_sequence
from torch.utils.data import Dataset, DataLoader

from transformers import (
    DonutProcessor,
    VisionEncoderDecoderModel,
    Seq2SeqTrainer,
    Seq2SeqTrainingArguments
    ,
)

# -------------------------
#  CONFIG
# -------------------------
MODEL_NAME = "naver-clova-ix/donut-base"
DATA_DIR = Path("dataset")  # doit contenir train/ et validation/
TRAIN_DIR = DATA_DIR / "train"
VAL_DIR = DATA_DIR / "validation"
OUTPUT_DIR = Path("./donut-finetuned")
TASK_PROMPT = "<s_docvqa><s_question>Extract structure as JSON:</s_question><s_answer>"

# -------------------------
#  Debug / versions
# -------------------------
import transformers, datasets
print("🚀 Transformers version:", transformers.__version__)
print("📚 Datasets version:", datasets.__version__)
print("Python executable:", Path(os.sys.executable))
print("Working dir:", Path.cwd())

# -------------------------
#  Charger processor & modèle
# -------------------------
print("🔁 Loading Donut processor & model:", MODEL_NAME)
processor = DonutProcessor.from_pretrained(MODEL_NAME)
model = VisionEncoderDecoderModel.from_pretrained(MODEL_NAME)

# ensure decoder/pad tokens set
model.config.decoder_start_token_id = processor.tokenizer.cls_token_id or processor.tokenizer.bos_token_id
model.config.eos_token_id = processor.tokenizer.eos_token_id
model.config.pad_token_id = processor.tokenizer.pad_token_id

# -------------------------
#  Helpers: build samples list (image path absolute, ground_truth string)
# -------------------------
def build_samples_from_folder(folder: Path):
    samples = []
    if not folder.exists():
        return samples
    for j in folder.glob("*.json"):
        try:
            with open(j, "r", encoding="utf-8") as f:
                content = json.load(f)
        except Exception as e:
            print("⚠️ Failed to read", j, e)
            continue

        # If JSON is a list with one element, take the first
        if isinstance(content, list) and len(content) > 0:
            content = content[0]

        # Compose ground-truth string: either it's already a string OR a dict
        if isinstance(content, dict):
            gt_text = json.dumps(content, ensure_ascii=False)
        elif isinstance(content, str):
            gt_text = content
        else:
            gt_text = str(content)

        # Determine image path: prefer absolute path in JSON, else same base name .png
        img_path = None
        if isinstance(content, dict):
            # try common keys
            for key in ("image", "image_path", "img"):
                if key in content and content[key]:
                    img_path = Path(content[key])
                    break
        if not img_path:
            img_path = j.with_suffix(".png")

        # Make absolute if not already
        if not img_path.is_absolute():
            img_path = folder / img_path.name

        if not img_path.exists():
            print(f"⚠️ Image not found, skipping: {img_path}")
            continue

        samples.append({"image": str(img_path), "ground_truth": gt_text})
    return samples

print("📥 Building train/val sample lists...")
train_samples = build_samples_from_folder(TRAIN_DIR)
val_samples = build_samples_from_folder(VAL_DIR)
print(f"Train samples: {len(train_samples)}  Val samples: {len(val_samples)}")
if len(train_samples) == 0:
    raise SystemExit("❗ Aucun sample d'entraînement trouvé. Vérifie dataset/train/*.json + .png")

# -------------------------
#  PyTorch Dataset
# -------------------------
class DonutTorchDataset(Dataset):
    def __init__(self, samples, processor, task_prompt, max_target_length=512):
        self.samples = samples
        self.processor = processor
        self.task_prompt = task_prompt
        self.max_target_length = max_target_length

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        s = self.samples[idx]
        img = Image.open(s["image"]).convert("RGB")
        pv = self.processor(img, return_tensors="pt").pixel_values.squeeze(0)  # (C, H, W)

        # prepare labels (prompt + ground truth + eos)
        gt = (self.task_prompt + s["ground_truth"] + processor.tokenizer.eos_token)
        # tokenize WITHOUT adding special tokens (we add the prompt ourselves)
        labels_ids = self.processor.tokenizer(gt, add_special_tokens=False, return_tensors="pt").input_ids.squeeze(0)
        if labels_ids.shape[0] > self.max_target_length:
            labels_ids = labels_ids[: self.max_target_length]

        return {"pixel_values": pv, "labels": labels_ids}


# Data collator: pad pixel_values (stack) and pad labels to same length -> replace pad id with -100
class DonutCollator:
    def __init__(self, pad_token_id):
        self.pad_token_id = pad_token_id

    def __call__(self, batch):
        pixel_values = torch.stack([b["pixel_values"] for b in batch])  # (B,C,H,W)
        labels = [b["labels"] for b in batch]  # list tensors len L_i
        labels_padded = pad_sequence(labels, batch_first=True, padding_value=self.pad_token_id)
        # replace pad token id with -100 for loss ignore
        labels_padded = labels_padded.masked_fill(labels_padded == self.pad_token_id, -100)
        return {"pixel_values": pixel_values, "labels": labels_padded}


train_dataset_torch = DonutTorchDataset(train_samples, processor, TASK_PROMPT, max_target_length=512)
eval_dataset_torch = DonutTorchDataset(val_samples, processor, TASK_PROMPT, max_target_length=512)
collator = DonutCollator(processor.tokenizer.pad_token_id)

# -------------------------
#  Trainer args (use TrainingArguments to avoid the Seq2Seq args conflict)
# -------------------------
training_args = Seq2SeqTrainingArguments(
    output_dir="./donut-output",
    per_device_train_batch_size=2,
    per_device_eval_batch_size=2,
    num_train_epochs=5,
    save_steps=500,
    save_total_limit=2,
    logging_steps=100,
    predict_with_generate=True,
    do_eval=True,
    eval_strategy="steps",   # ✅ remplace evaluation_strategy
    eval_steps=500,
)

# -------------------------
#  Trainer
# -------------------------
trainer = Seq2SeqTrainer(
    model=model,
    args=training_args,
    train_dataset=train_dataset_torch,
    eval_dataset=eval_dataset_torch if len(eval_dataset_torch) > 0 else None,
    data_collator=collator,
    tokenizer=processor.tokenizer,
)

# -------------------------
#  Start training
# -------------------------
print("▶️ Démarrage de l'entraînement...")
trainer.train()
print("✅ Entraînement terminé. Sauvegarde du modèle...")
trainer.save_model(OUTPUT_DIR)
processor.save_pretrained(OUTPUT_DIR)
print("✅ Modèle sauvegardé dans", OUTPUT_DIR)
