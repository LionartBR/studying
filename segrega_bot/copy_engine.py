# copy_engine.py
from typing import Dict, List, Tuple
import threading
import os
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed

def _same_drive(a: str, b: str) -> bool:
    da = os.path.splitdrive(os.path.abspath(a))[0].upper()
    db = os.path.splitdrive(os.path.abspath(b))[0].upper()
    return da == db and da != ""

def _ensure_dir(p: str):
    os.makedirs(p, exist_ok=True)

def _scan_dir_sizes(dest_dir: str) -> Dict[str, int]:
    sizes = {}
    try:
        with os.scandir(dest_dir) as it:
            for e in it:
                if e.is_file():
                    sizes[e.name] = e.stat().st_size
    except FileNotFoundError:
        pass
    return sizes

def _resolve_conflict(dest_dir: str, fname: str, fsize: int, cache_sizes: Dict[str, int]) -> Tuple[str, str]:
    name, ext = os.path.splitext(fname)
    cand = os.path.join(dest_dir, fname)

    s = cache_sizes.get(fname)
    if s is None and os.path.exists(cand):
        s = os.path.getsize(cand)
        cache_sizes[fname] = s

    if s is not None:
        if s == fsize and fsize >= 0:
            return "skip_same", cand
        k = 2
        while True:
            nf = f"{name}-{k}{ext}"
            cand = os.path.join(dest_dir, nf)
            s2 = cache_sizes.get(nf)
            if s2 is None and os.path.exists(cand):
                s2 = os.path.getsize(cand)
                cache_sizes[nf] = s2
            if s2 is None:
                return "ok", cand
            if s2 == fsize and fsize >= 0:
                return "skip_same", cand
            k += 1
    else:
        return "ok", cand

def _hardlink_or_copy(src: str, dst: str):
    try:
        os.link(src, dst)  # hardlink
    except Exception:
        shutil.copy2(src, dst)

def _sanitize_folder(name: str) -> str:
    invalid = '<>:"/\\|?*'
    out = "".join("_" if ch in invalid else ch for ch in name).strip()
    return out or "_sem_nome_"

def copy_plan(
    plan: Dict[str, List[str]],
    out_root: str,
    max_workers: int = 2
) -> Dict[str, Dict[str, List[Tuple[str, str]]]]:
    """
    plan: { pdf_path: [ 'Colab A', 'Colab B', ... ] }
    Retorna:
      { pdf_path: { "created": [(collab, created_path), ...],
                    "skipped": [(collab, reason), ...] } }
    """
    results: Dict[str, Dict[str, List[Tuple[str, str]]]] = {}
    dest_cache: Dict[str, Dict[str, int]] = {}  # dest_dir -> {fname: size}
    locks: Dict[str, threading.Lock] = {}

    def task_for_pdf(pdf_path: str, collabs: List[str]):
        created, skipped = [], []
        try:
            fsize = os.path.getsize(pdf_path)
        except OSError:
            fsize = -1
        fname = os.path.basename(pdf_path)

        for collab in collabs:   # sequência por PDF
            dest_dir = os.path.join(out_root, _sanitize_folder(collab))
            _ensure_dir(dest_dir)

            lock = locks.setdefault(dest_dir, threading.Lock())
            with lock:
                if dest_dir not in dest_cache:
                    dest_cache[dest_dir] = _scan_dir_sizes(dest_dir)
                cache_sizes = dest_cache[dest_dir]

                status, final_path = _resolve_conflict(dest_dir, fname, fsize, cache_sizes)
                if status == "skip_same":
                    skipped.append((collab, "same name & size"))
                    continue

                try:
                    if _same_drive(pdf_path, dest_dir):
                        _hardlink_or_copy(pdf_path, final_path)
                    else:
                        shutil.copy2(pdf_path, final_path)
                    created.append((collab, final_path))
                    cache_sizes[os.path.basename(final_path)] = fsize
                except Exception as e:
                    skipped.append((collab, f"copy_failed: {e}"))

        return (pdf_path, {"created": created, "skipped": skipped})

    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futs = [ex.submit(task_for_pdf, p, cols) for p, cols in plan.items()]
        for fut in as_completed(futs):
            pdf, res = fut.result()
            results[pdf] = res

    return results
