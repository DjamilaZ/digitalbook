import json
import re
from pathlib import Path

def is_chapter(text):
    return bool(re.match(r"^#\s*", text.strip())) or text.isupper()

def is_section(text):
    return bool(re.match(r"^##\s*", text.strip()))

def is_subsection(text):
    return bool(re.match(r"^###\s*", text.strip()))

def clean_text(txt):
    txt = re.sub(r"\${.*?}", "", txt)  # remove math formulas
    txt = re.sub(r"\s+", " ", txt).strip()
    return txt

def structure_json(data):
    result = {"titre_livre": None, "chapitres": []}
    current_chapter = None
    current_section = None
    current_subsection = None

    for block in data:
        if block["type"] == "text":
            text = clean_text(block["text"])

            # Détection du titre du livre
            if not result["titre_livre"] and "livre" in text.lower():
                result["titre_livre"] = text
                continue

            level = block.get("text_level")

            # Déterminer le niveau du texte
            if level == 1 or is_chapter(text):
                current_chapter = {
                    "titre": text.lstrip("# ").strip(),
                    "contenu": "",
                    "images": [],
                    "sections": []
                }
                result["chapitres"].append(current_chapter)
                current_section = None
                current_subsection = None

            elif level == 2 or is_section(text):
                if not current_chapter:
                    # créer un chapitre par défaut
                    current_chapter = {
                        "titre": "Chapitre sans titre",
                        "contenu": "",
                        "images": [],
                        "sections": []
                    }
                    result["chapitres"].append(current_chapter)
                current_section = {
                    "titre": text.lstrip("# ").strip(),
                    "contenu": "",
                    "images": [],
                    "sous_sections": []
                }
                current_chapter["sections"].append(current_section)
                current_subsection = None

            elif level == 3 or is_subsection(text):
                if not current_section:
                    if not current_chapter:
                        current_chapter = {"titre": "Chapitre sans titre", "contenu": "", "images": [], "sections": []}
                        result["chapitres"].append(current_chapter)
                    current_section = {"titre": "Section sans titre", "contenu": "", "images": [], "sous_sections": []}
                    current_chapter["sections"].append(current_section)
                current_subsection = {
                    "titre": text.lstrip("# ").strip(),
                    "contenu": "",
                    "images": []
                }
                current_section["sous_sections"].append(current_subsection)

            else:
                # C’est un paragraphe, on l’attache au bon niveau
                target = None
                if current_subsection:
                    target = current_subsection
                elif current_section:
                    target = current_section
                elif current_chapter:
                    target = current_chapter

                if target:
                    target["contenu"] += (" " + text)

        elif block["type"] == "image":
            # Attacher image au bon bloc (le plus précis possible)
            target = current_subsection or current_section or current_chapter
            if target is not None:
                target["images"].append(block["img_path"])

    return result


if __name__ == "__main__":
    input_path = Path("output_md/book_raw.json")
    output_path = Path("output_md/book_structured.json")

    if not input_path.exists():
        raise FileNotFoundError(f"Fichier JSON introuvable: {input_path}")

    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    structured = structure_json(data)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(structured, f, ensure_ascii=False, indent=4)

    print(f"✅ JSON structuré enregistré dans {output_path}")
