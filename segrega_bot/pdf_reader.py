# Extrai texto só das páginas 1–3, com pdfminer e fallback em pypdf.
from typing import Tuple, Iterable
import logging

# silencia pdfminer verboso
for name in ("pdfminer", "pdfminer.pdfinterp", "pdfminer.pdfpage",
             "pdfminer.psparser", "pdfminer.pdftypes", "pdfminer.layout"):
    logging.getLogger(name).setLevel(logging.ERROR)

from pdfminer.high_level import extract_text
import hashlib

def _hash_text(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8", errors="ignore")).hexdigest()

def _extract_text_for_pages(path: str, page_numbers: Iterable[int]) -> str:
    pages = list(page_numbers)
    if not pages:
        return ""
    try:
        txt = extract_text(path, page_numbers=pages) or ""
    except Exception:
        txt = ""

    if len(txt.strip()) < 20:
        try:
            from pypdf import PdfReader

            reader = PdfReader(path, strict=False)
            total = len(reader.pages)
            parts = []
            for idx in pages:
                if 0 <= idx < total:
                    parts.append(reader.pages[idx].extract_text() or "")
            txt2 = "\n".join(parts)
            if len(txt2.strip()) > len(txt.strip()):
                txt = txt2
        except Exception:
            pass

    return txt

def extract_first_pages_text(path: str, max_pages: int = 3) -> Tuple[str, str]:
    """
    Retorna (texto_p1a3, hash_p1a2) – ambos já como string (sem normalizar aqui).
    """
    pages = [i for i in range(max_pages)]
    txt = _extract_text_for_pages(path, pages)
    txt12 = _extract_text_for_pages(path, [0, 1])
    h12 = _hash_text(txt12)
    return txt, h12

def extract_first_two_pages_hash(path: str) -> str:
    """Retorna hash (SHA-1) do texto das duas primeiras páginas."""
    txt12 = _extract_text_for_pages(path, [0, 1])
    return _hash_text(txt12)
