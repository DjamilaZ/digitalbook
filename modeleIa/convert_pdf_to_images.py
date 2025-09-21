# convert_pdf_to_images.py
from pdf2image import convert_from_path
import os

def pdf_to_images(pdf_path, out_dir="images", dpi=200):
    os.makedirs(out_dir, exist_ok=True)
    pages = convert_from_path(pdf_path, dpi=dpi)
    paths = []
    for i, p in enumerate(pages, 1):
        path = f"{out_dir}/page_{i:04d}.png"
        p.save(path)
        paths.append(path)
    return paths

if __name__ == "__main__":
    pdf_path = "NSL-Rigging-Lifting-Handbook.pdf"
    images = pdf_to_images(pdf_path, out_dir="images", dpi=200)
    print("Saved", len(images), "images")
