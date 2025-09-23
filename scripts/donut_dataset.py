# donut_dataset.py
import json
from PIL import Image
import torch
from torch.utils.data import Dataset
from transformers import DonutProcessor

class DonutDataset(Dataset):
    def __init__(self, jsonl_path, processor: DonutProcessor, task_prompt: str, max_target_length=512):
        self.samples = []
        with open(jsonl_path, "r", encoding="utf-8") as f:
            for line in f:
                obj = json.loads(line)
                # image path and label string (JSON)
                img = obj["image"]
                label_json = obj["label"] if isinstance(obj["label"], str) else json.dumps(obj["label"], ensure_ascii=False)
                self.samples.append({"image": img, "label": label_json})
        self.processor = processor
        self.task_prompt = task_prompt
        self.max_target_length = max_target_length

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        sample = self.samples[idx]
        image = Image.open(sample["image"]).convert("RGB")
        # processor handles image resizing/cropping etc
        pixel_values = self.processor(image, return_tensors="pt").pixel_values.squeeze()  # tensor HWC->CHW inside
        # prepare label tokens (task_prompt + ground truth)
        # note: no special tokens added by add_special_tokens=False
        tokenized = self.processor.tokenizer(self.task_prompt + sample["label"] + self.processor.tokenizer.eos_token,
                                             add_special_tokens=False,
                                             return_tensors="pt")
        labels = tokenized["input_ids"].squeeze()
        # clamp length
        if labels.size(0) > self.max_target_length:
            labels = labels[:self.max_target_length]
        return {"pixel_values": pixel_values, "labels": labels}
