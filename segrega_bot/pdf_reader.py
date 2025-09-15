# Extrai texto só das páginas 1–3, com pdfminer e fallback em pypdf.
from typing import Tuple
import logging

# silencia pdfminer verboso
for name in ("pdfminer", "pdfminer.pdfinterp", "pdfminer.pdfpage",
             "pdfminer.psparser", "pdfminer.pdftypes", "pdfminer.layout"):
    logging.getLogger(name).setLevel(logging.ERROR)

from pdfminer.high_level import extract_text
from util_normalize import strip_accents_lower
import hashlib

def _hash_text(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8", errors="ignore")).hexdigest()

def extract_first_pages_text(path: str, max_pages: int = 3) -> Tuple[str, str]:
    """
    Retorna (texto_p1a3, hash_p1a2) – ambos já como string (sem normalizar aqui).
    """
    txt = ""
    try:
        # page_numbers é 0-based; pegamos até 0,1,2
        pages = [i for i in range(max_pages)]
        txt = extract_text(path, page_numbers=pages) or ""
    except Exception:
        txt = ""

    if len(txt.strip()) < 20:
        # fallback: pypdf
        try:
            from pypdf import PdfReader
            reader = PdfReader(path, strict=False)
            parts = []
            for i, page in enumerate(reader.pages[:max_pages]):
                parts.append(page.extract_text() or "")
            txt2 = "\n".join(parts)
            if len(txt2.strip()) > len(txt.strip()):
                txt = txt2
        except Exception:
            pass

    # Para hash p1–p2, re-extrai só 2 páginas (ou recorta o txt quando possível).
    txt12 = ""
    try:
        txt12 = extract_text(path, page_numbers=[0, 1]) or ""
    except Exception:
        # fallback pypdf p/ p1–p2
        try:
            from pypdf import PdfReader
            reader = PdfReader(path, strict=False)
            parts = []
            for page in reader.pages[:2]:
                parts.append(page.extract_text() or "")
            txt12 = "\n".join(parts)
        except Exception:
            txt12 = ""

    h12 = _hash_text(txt12)
    return txt, h12
