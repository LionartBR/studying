# Cache incremental por arquivo PDF
import shutil, time, uuid, os, json, stat
from typing import Dict, Any, Optional

from pdf_reader import extract_first_two_pages_hash

def _cache_dir(out_root: str) -> str:
    d = os.path.join(out_root, ".cache_distcolabs")
    os.makedirs(d, exist_ok=True)
    return d

def _cache_file(out_root: str) -> str:
    return os.path.join(_cache_dir(out_root), "index.json")

def load_cache(out_root: str) -> Dict[str, Any]:
    p = _cache_file(out_root)
    if not os.path.exists(p):
        return {}
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_cache(out_root: str, data: Dict[str, Any]) -> None:
    p = _cache_file(out_root)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, p)

def is_unchanged(path: str, cache: Dict[str, Any]) -> bool:
    try:
        st = os.stat(path)
    except OSError:
        return False
    key = os.path.abspath(path)
    info = cache.get(key)
    if not info:
        return False
    if info.get("mtime") != st.st_mtime or info.get("size") != st.st_size:
        return False

    cached_hash = info.get("first2_hash")
    if cached_hash is None:
        return False

    try:
        current_hash = extract_first_two_pages_hash(path)
    except Exception:
        return False
    return current_hash == cached_hash

def update_cache_entry(out_root: str, cache: Dict[str, Any], path: str, first2_hash: str, names: list):
    try:
        st = os.stat(path)
    except OSError:
        return
    key = os.path.abspath(path)
    cache[key] = {
        "mtime": st.st_mtime,
        "size": st.st_size,
        "first2_hash": first2_hash,
        "names": sorted(names),
    }

def get_cached_names(path: str, cache: Dict[str, Any]) -> Optional[list]:
    key = os.path.abspath(path)
    info = cache.get(key)
    if info:
        return list(info.get("names", []))
    return None

def _on_rm_error(func, path, exc_info):
    # Tenta remover atributo read-only e repetir a operação (Windows-friendly)
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except Exception:
        pass

def get_cache_dirs(out_root: str) -> list[str]:
    """Suporta variações antigas/novas do nome da pasta de cache."""
    names = [".cache_distcolabs", ".cache_distcolab", "cache.distcolabs", "cache.distcolab"]
    return [os.path.join(out_root, n) for n in names]

def purge_cache(out_root: str) -> None:
    """Remove recursivamente quaisquer pastas de cache conhecidas."""
    for d in get_cache_dirs(out_root):
        if os.path.exists(d):
            try:
                shutil.rmtree(d, onerror=_on_rm_error)
            except Exception:
                # tenta novamente ignorando erros
                shutil.rmtree(d, ignore_errors=True)
