

import fitz 
import logging
from pypdf import PdfReader
import docx
from unicodedata import normalize

logger = logging.getLogger(__name__)


def pdf_has_image(file_path, image_threshold=0.9):
    doc = fitz.open(file_path)
    image_pages = 0

    for page in doc:
        images = page.get_images(full=True)
        if images:
            image_pages += 1

    return image_pages > 0



def extract_text_from_pdf_with_PyPDF(file_path):
    extracted_text = []
    try:
        reader = PdfReader(file_path)
        for page in reader.pages:
            text = page.extract_text()
            if text and text.strip():
                extracted_text.append(text.strip())
    except Exception as e:
        logger.error(f"Failed to extract text via PyPDF: {e}")
    
    return extracted_text

def extract_text_from_doc(file_path):
    doc = docx.Document(file_path)
    paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    if paragraphs:
        return [" ".join(paragraphs)]
    return []


def extract_text_from_txt(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read().strip()
    return [content] if content else []

def normalize_text_list(text_list):
    def clean(t):
        try:
            return normalize('NFKC', t.encode('utf-8').decode('utf-8'))
        except Exception as e:
            print(f"ERRO AO FAZER NORMALIZE {e}")
            return t

    return [clean(t) for t in text_list if isinstance(t, str)]
