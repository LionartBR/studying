# Aho–Corasick para busca de "palavra inteira" com verificação de fronteiras.
from typing import Dict, List, Set, Tuple
import ahocorasick  # pacote: pyahocorasick
from util_normalize import is_word_char

def build_automaton(canon_by_display: Dict[str, str]):
    """
    canon_by_display: {"Nome Original": "nome canonico sem stopwords"}
    Retorna automaton e também um mapa key->display para atribuição.
    """
    A = ahocorasick.Automaton()
    key_to_display: Dict[str, List[str]] = {}
    for display, key in canon_by_display.items():
        if not key:
            continue
        # Evita duplicar chaves iguais (mesmo nome canônico para pessoas diferentes é raro, mas tratamos)
        if key not in key_to_display:
            A.add_word(key, key)
        key_to_display.setdefault(key, []).append(display)
    A.make_automaton()
    return A, key_to_display

def boundary_ok(text: str, start: int, end: int) -> bool:
    """Garante 'palavra inteira' verificando caracteres vizinhos."""
    left_ok = start == 0 or not is_word_char(text[start - 1])
    right_ok = end == len(text) - 1 or not is_word_char(text[end + 1])
    return left_ok and right_ok

def find_keys_in_text(A, text: str) -> Set[str]:
    """Retorna conjunto de chaves canônicas encontradas no 'text' (com fronteira de palavra)."""
    hits: Set[str] = set()
    for end, key in A.iter(text):
        start = end - len(key) + 1
        if start >= 0 and boundary_ok(text, start, end):
            hits.add(key)
    return hits

def map_keys_to_displays(keys: Set[str], key_to_display: Dict[str, List[str]]) -> Set[str]:
    return {disp for k in keys for disp in key_to_display.get(k, [])}
