import PyPDF2
import ocrmypdf
import json
import os
from tempfile import NamedTemporaryFile
import pytesseract
import fitz  # pymupdf for font and heading extraction

# Configure Tesseract path
pytesseract.pytesseract.tesseract_cmd = r'E:\Tesseract-OCR\tesseract.exe'
os.environ['TESSDATA_PREFIX'] = r'E:\Tesseract-OCR\tessdata'

# Configure PATH for Tesseract and Ghostscript
os.environ['PATH'] = os.environ['PATH'] + os.pathsep + r'E:\Tesseract-OCR' + os.pathsep + r'C:\Program Files\gs\gs10.03.1\bin'

def detect_scanned_pages(file_path):
    try:
        # Ouvre le fichier PDF en mode binaire
        with open(file_path, 'rb') as file:
            # Crée un objet PDF reader
            pdf_reader = PyPDF2.PdfReader(file)
            
            # Liste pour stocker les numéros des pages scannées
            scanned_pages = []
            non_scanned_pages = []
            
            # Parcourt chaque page du PDF
            for page_num, page in enumerate(pdf_reader.pages, start=1):
                # Extrait le texte de la page
                text = page.extract_text() or ""
                
                # Vérifie si la page contient des images
                has_images = False
                if '/XObject' in page['/Resources']:
                    xobjects = page['/Resources']['/XObject'].get_object()
                    if xobjects:
                        for obj in xobjects:
                            if xobjects[obj]['/Subtype'] == '/Image':
                                has_images = True
                                break
                
                # Si la page a des images mais peu ou pas de texte, elle est probablement scannée
                if has_images and len(text.strip()) < 50:  # Seuil arbitraire pour le texte
                    scanned_pages.append(page_num)
                else:
                    non_scanned_pages.append(page_num)
            
            return scanned_pages, non_scanned_pages, None  # Retourne None pour l'erreur en cas de succès
    except FileNotFoundError:
        return [], [], "Erreur : Le fichier PDF n'a pas été trouvé."
    except Exception as e:
        return [], [], f"Erreur lors de la lecture du PDF : {str(e)}"

def extract_non_scanned_pages(file_path, non_scanned_pages):
    try:
        # Ouvre le fichier PDF en mode binaire
        with open(file_path, 'rb') as file:
            # Crée un objet PDF reader
            pdf_reader = PyPDF2.PdfReader(file)
            
            # Dictionnaire pour stocker le contenu des pages non scannées
            non_scanned_content = {}
            
            # Extrait le texte des pages non scannées
            for page_num in non_scanned_pages:
                page = pdf_reader.pages[page_num - 1]  # Les pages sont indexées à partir de 0
                text = page.extract_text() or ""
                if text.strip():
                    non_scanned_content[f"Page_{page_num}"] = text.strip()
            
            # Enregistre dans un fichier JSON
            with open("non_scanned_pages.json", "w", encoding="utf-8") as f:
                json.dump(non_scanned_content, f, ensure_ascii=False, indent=4)
            
            return f"Contenu des pages non scannées enregistré dans 'non_scanned_pages.json'"
    except FileNotFoundError:
        return "Erreur : Le fichier PDF n'a pas été trouvé."
    except Exception as e:
        return f"Erreur lors de l'extraction des pages non scannées : {str(e)}"

def extract_scanned_pages(file_path, scanned_pages):
    try:
        # Crée un fichier temporaire pour le PDF traité par OCR
        with NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
            temp_output = temp_file.name
        
        # Applique l'OCR au PDF avec ocrmypdf
        ocrmypdf.ocr(file_path, temp_output, force_ocr=True)
        
        # Ouvre le PDF traité pour extraire le texte
        with open(temp_output, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            
            # Dictionnaire pour stocker le contenu des pages scannées
            scanned_content = {}
            
            # Extrait le texte des pages scannées
            for page_num in scanned_pages:
                page = pdf_reader.pages[page_num - 1]  # Les pages sont indexées à partir de 0
                text = page.extract_text() or ""
                if text.strip():
                    scanned_content[f"Page_{page_num}"] = text.strip()
            
            # Enregistre dans un fichier JSON
            with open("scanned_pages.json", "w", encoding="utf-8") as f:
                json.dump(scanned_content, f, ensure_ascii=False, indent=4)
            
            return temp_output, f"Contenu des pages scannées enregistré dans 'scanned_pages.json'"
    except FileNotFoundError:
        return None, "Erreur : Le fichier PDF n'a pas été trouvé."
    except Exception as e:
        return None, f"Erreur lors de l'extraction des pages scannées : {str(e)}"

def extract_fonts_and_sizes(file_path):
    try:
        # Ouvre le PDF avec pymupdf
        doc = fitz.open(file_path)
        
        # Dictionnaire pour stocker les fonts uniques et leurs tailles (liste de tailles par font)
        fonts_info = {}
        
        # Parcourt chaque page
        for page_num in range(doc.page_count):
            page = doc.load_page(page_num)
            
            # Extrait les fonts de la page
            fonts = page.get_fonts(full=True)
            
            for font in fonts:
                font_id, font_name, font_type, font_file, embedded = font  # Décompose les infos
                
                # Utilise font_name comme clé (souvent le nom de la font)
                if font_name not in fonts_info:
                    fonts_info[font_name] = set()  # Utilise un set pour éviter les doublons de tailles
                
                # Extrait les tailles de font (utilise get_text('dict') pour obtenir les spans avec tailles)
                blocks = page.get_text("dict")["blocks"]
                for block in blocks:
                    if "lines" in block:
                        for line in block["lines"]:
                            for span in line["spans"]:
                                if span["font"] == font_name:  # Associe à la font
                                    size = span["size"]  # Taille en points
                                    fonts_info[font_name].add(size)
        
        # Convertit les sets en listes triées pour le JSON
        for font in fonts_info:
            fonts_info[font] = sorted(list(fonts_info[font]))
        
        # Enregistre dans un fichier JSON
        with open("fonts_info.json", "w", encoding="utf-8") as f:
            json.dump(fonts_info, f, ensure_ascii=False, indent=4)
        
        doc.close()
        return f"Informations sur les fonts et tailles enregistrées dans 'fonts_info.json'"
    except FileNotFoundError:
        return "Erreur : Le fichier PDF n'a pas été trouvé."
    except Exception as e:
        return f"Erreur lors de l'extraction des fonts : {str(e)}"

def extract_headings(file_path, scanned_pages, ocr_file_path=None):
    try:
        # Ouvre le PDF original pour les pages non scannées et le PDF OCR pour les pages scannées
        doc = fitz.open(file_path)
        if ocr_file_path and os.path.exists(ocr_file_path):
            doc_ocr = fitz.open(ocr_file_path)
        else:
            doc_ocr = doc  # Fallback si OCR non disponible
        
        # Liste pour stocker les titres sous forme de tableau
        headings = []
        
        # Calcule un seuil de taille pour les titres (moyenne des tailles + 1.5x écart-type)
        all_sizes = []
        for page_num in range(doc.page_count):
            page = doc.load_page(page_num)
            blocks = page.get_text("dict")["blocks"]
            for block in blocks:
                if "lines" in block:
                    for line in block["lines"]:
                        for span in line["spans"]:
                            all_sizes.append(span["size"])
        
        if all_sizes:
            avg_size = sum(all_sizes) / len(all_sizes)
            std_size = (sum((x - avg_size) ** 2 for x in all_sizes) / len(all_sizes)) ** 0.5
            title_size_threshold = avg_size + 1.5 * std_size  # Seuil dynamique pour les titres
        else:
            title_size_threshold = 12.0  # Seuil par défaut si aucune taille trouvée
        
        # Parcourt chaque page
        for page_num in range(doc.page_count):
            # Utilise le doc OCR pour les pages scannées, sinon le doc original
            if page_num + 1 in scanned_pages and doc_ocr != doc:
                page = doc_ocr.load_page(page_num)
            else:
                page = doc.load_page(page_num)
            
            # Extrait les blocs de texte
            blocks = page.get_text("dict")["blocks"]
            for block in blocks:
                if "lines" in block:
                    for line in block["lines"]:
                        for span in line["spans"]:
                            # Considère comme titre si la taille est supérieure au seuil
                            if span["size"] > title_size_threshold:
                                text = span["text"].strip()
                                if text:  # Ignore les chaînes vides
                                    headings.append({
                                        "page": page_num + 1,
                                        "title": text,
                                        "font": span["font"],
                                        "size": span["size"]
                                    })
        
        # Enregistre dans un fichier JSON
        with open("headings.json", "w", encoding="utf-8") as f:
            json.dump(headings, f, ensure_ascii=False, indent=4)
        
        # Affiche le tableau dans la console
        print("\n📋 Tableau des titres détectés :")
        print("Page | Titre | Police | Taille")
        print("-" * 50)
        for h in headings:
            print(f"{h['page']} | {h['title'][:50]}... | {h['font']} | {h['size']}")
        
        doc.close()
        if doc_ocr != doc:
            doc_ocr.close()
        return f"Tableau des titres enregistré dans 'headings.json'"
    except FileNotFoundError:
        return "Erreur : Le fichier PDF n'a pas été trouvé."
    except Exception as e:
        return f"Erreur lors de l'extraction des titres : {str(e)}"

# Exemple d'utilisation
if __name__ == "__main__":
    file_path = "livretdigital.pdf"
    
    # Détecte les pages scannées et non scannées
    scanned_pages, non_scanned_pages, error = detect_scanned_pages(file_path)
    print(f"📊 Pages détectées - Scannées : {scanned_pages}, Non scannées : {non_scanned_pages}")
    
    if error:
        print(error)
    else:
        # Extrait le contenu des pages non scannées
        if non_scanned_pages:
            print(extract_non_scanned_pages(file_path, non_scanned_pages))
        else:
            print("Aucune page non scannée détectée.")
        
        # Extrait le contenu des pages scannées avec OCR
        ocr_file_path = None
        if scanned_pages:
            ocr_file_path, result = extract_scanned_pages(file_path, scanned_pages)
            print(result)
        else:
            print("Aucune page scannée détectée.")
        
        # Extrait les fonts et tailles du document entier
        print(extract_fonts_and_sizes(file_path))
        
        # Extrait les titres et les organise dans un tableau
        print(extract_headings(file_path, scanned_pages, ocr_file_path))