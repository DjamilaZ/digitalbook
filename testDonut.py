from transformers import VisionEncoderDecoderModel, DonutProcessor
from pdf2image import convert_from_path
from PIL import Image
import torch, json

MODEL_NAME = "naver-clova-ix/donut-base"  # modèle générique

processor = DonutProcessor.from_pretrained(MODEL_NAME)
model = VisionEncoderDecoderModel.from_pretrained(MODEL_NAME)
device = "cuda" if torch.cuda.is_available() else "cpu"
model.to(device)

pdf_path = "NSL-Rigging-Lifting-Handbook.pdf"
pages = convert_from_path(pdf_path, dpi=150)

document_structure = {"title": "Rigging Handbook", "chapters": []}

for page_num, page in enumerate(pages[:3], start=1):  # limiter pour test
    image = page.convert("RGB")
    pixel_values = processor(image, return_tensors="pt").pixel_values.to(device)

    task_prompt = "<s_docvqa><s_question>Extract JSON structure with title, chapters, sections, subsections, and content</s_question><s_answer>"
    decoder_input_ids = processor.tokenizer(task_prompt, add_special_tokens=False, return_tensors="pt").input_ids.to(device)

    outputs = model.generate(
        pixel_values,
        decoder_input_ids=decoder_input_ids,
        max_length=model.config.decoder.max_position_embeddings,
        pad_token_id=processor.tokenizer.pad_token_id,
        eos_token_id=processor.tokenizer.eos_token_id,
        num_beams=1,
        bad_words_ids=[[processor.tokenizer.unk_token_id]],
        return_dict_in_generate=True,
    )

    sequence = processor.batch_decode(outputs.sequences)[0]
    sequence = sequence.replace(processor.tokenizer.eos_token, "").replace(processor.tokenizer.pad_token, "")
    sequence = sequence.replace(task_prompt, "").strip()

    print(f"\n📄 Page {page_num} ===")
    print(sequence)

    # essayer d’ajouter au JSON global
    try:
        page_json = json.loads(sequence)
        document_structure["chapters"].append(page_json)
    except:
        print("⚠️ sortie non JSON pour cette page")

with open("document_structure.json", "w", encoding="utf-8") as f:
    json.dump(document_structure, f, indent=2, ensure_ascii=False)

print("\n✅ Résultat sauvegardé dans document_structure.json")
