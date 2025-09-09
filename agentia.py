import fitz  # PyMuPDF
import os
import json
import logging
from openai import OpenAI

# --- Configuration logging ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def parse_pdf_to_json(file_path: str, api_key: str = None, extract_dir: str = "extracted"):
    """
    Lit un PDF, extrait texte + images,
    et demande à OpenAI de le structurer en JSON hiérarchisé.
    Retourne un dict Python.
    """
    os.makedirs(extract_dir, exist_ok=True)
    logging.info(f"Extraction PDF : {file_path}")
    
    client = OpenAI(api_key=api_key)

    # --- Extraction texte et images ---
    doc = fitz.open(file_path)
    full_text = []
    image_refs = []
    for page_num, page in enumerate(doc, start=1):
        text = page.get_text("text")
        full_text.append(f"[PAGE {page_num}]\n{text}")
        logging.info(f"Page {page_num} : {len(text)} caractères extraits")

        # Extraire images
        images_on_page = page.get_images(full=True)
        logging.info(f"Page {page_num} : {len(images_on_page)} images détectées")
        for img_index, img in enumerate(images_on_page, start=1):
            xref = img[0]
            base_image = doc.extract_image(xref)
            img_bytes = base_image["image"]
            img_ext = base_image["ext"]
            img_name = f"page{page_num}_img{img_index}.{img_ext}"
            img_path = os.path.join(extract_dir, img_name)
            with open(img_path, "wb") as f:
                f.write(img_bytes)
            image_refs.append(img_path)

    logging.info(f"Total images extraites : {len(image_refs)}")

    document_content = "\n".join(full_text)
    logging.info(f"Texte total extrait : {len(document_content)} caractères")

    # --- Prompt pour structurer en JSON ---
    prompt = f"""
    Tu es un expert en structuration de documents.
    J'ai un document PDF dont voici le contenu brut.
    J'ai aussi extrait les images (fichiers listés ci-dessous).
    Associe-les intelligemment aux chapitres/sections correspondants.

    Retourne-moi un JSON respectant STRICTEMENT ce schéma :

    {{
      "chapters": [
        {{
          "title": "string",
          "number": "int",
          "sections": [
            {{
              "title": "string",
              "number": "string",
              "content": "string",
              "images": ["string"],   # chemins vers fichiers extraits
              "tables": [],           # vide car extraction table désactivée
              "subsections": []
            }}
          ]
        }}
      ]
    }}

    Texte extrait :
    {document_content}

    Images extraites :
    {image_refs}
    """

    logging.info("Envoi du prompt à OpenAI...")
    response = client.chat.completions.create(
        model="gpt-4.1",
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        response_format={"type": "json_object"}
    )


    logging.info("Réponse reçue d'OpenAI, parsing JSON...")
    result_json = json.loads(response.choices[0].message.content)
    logging.info(f"JSON généré : {len(result_json['chapters'])} chapitres détectés")

    return result_json



if __name__ == "__main__":
    data = parse_pdf_to_json("Livretdigital.pdf", api_key="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")
    print(type(data))  # <class 'dict'>
    print(data["chapters"][0]["title"])  # accès direct au JSON
