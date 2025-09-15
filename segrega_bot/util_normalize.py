import re
import unicodedata

# palavras brasileiras a remover dos NOMES (e também do texto normalizado p/ matching)
STOPWORDS = {"de", "da", "do", "dos", "das", "e"}

_WORD_RE = re.compile(r"[a-z0-9]", re.IGNORECASE)

def strip_accents_lower(s: str) -> str:
    if not s:
        return ""
    # Normaliza e remove acentos
    s = unicodedata.normalize("NFD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    # Ç explícito para C por segurança (após NFD, "ç" vira "c")
    s = s.replace("Ç", "C").replace("ç", "c")
    s = s.lower()
    # colapsa espaços e pontuação redundante em 1 espaço
    s = re.sub(r"\s+", " ", s)
    return s.strip()

def remove_stopwords_tokens(text: str) -> str:
    tokens = text.split()
    tokens = [t for t in tokens if t not in STOPWORDS]
    return " ".join(tokens)

def normalize_name_for_key(name: str) -> str:
    """Nome canônico: sem acentos/Ç, minúsculo, sem stopwords."""
    base = strip_accents_lower(name)
    return remove_stopwords_tokens(base)

def normalize_text_for_search(text: str) -> str:
    """Texto do PDF/filename pronto p/ busca: sem acentos/Ç, minúsculo, sem stopwords."""
    base = strip_accents_lower(text)
    return remove_stopwords_tokens(base)

def is_word_char(ch: str) -> bool:
    return bool(ch) and bool(_WORD_RE.match(ch))
