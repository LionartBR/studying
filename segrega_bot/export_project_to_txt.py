# export_project_to_txt.py
# -*- coding: utf-8 -*-
r"""
Converte cada arquivo texto/código do projeto em um .txt com o mesmo conteúdo,
espelhando a árvore de diretórios. Ignora .venv e __pycache__.

Uso (exemplos):
  python export_project_to_txt.py --root "C:\meu\projeto" --out "C:\saida_txt"
  python export_project_to_txt.py --root "C:\meu\projeto"

Opções:
  --include-binaries        Processa tudo, inclusive binários (NÃO recomendado)
  --extra-skip-dirs ".git,.idea,node_modules"   (lista separada por vírgula)
  --ext-allow ".py,.md,.txt,.json"             (se usar, só exporta essas extensões)
  --dry-run                 Mostra o que faria, sem escrever arquivos
"""

import argparse
import os
from pathlib import Path
from typing import Iterable, Tuple

# Diretórios a ignorar SEMPRE (prefix match por nome exato)
DEFAULT_SKIP_DIRS = {
    ".venv", "__pycache__", ".git", ".hg", ".svn", ".tox", "node_modules", "venv", ".idea", "text_export",
    "export_project_to_txt.py", "geracao_test.py"
    }

# Extensões de binários comuns a ignorar por padrão
DEFAULT_SKIP_BIN_EXTS = {
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".ico", ".webp",
    ".pdf",
    ".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz",
    ".exe", ".dll", ".so", ".dylib",
    ".ttf", ".otf", ".woff", ".woff2",
    ".mp3", ".wav", ".flac", ".ogg",
    ".mp4", ".avi", ".mov", ".mkv", ".webm",
    ".sqlite", ".db",
    ".xls", ".xlsx", ".doc", ".docx", ".ppt", ".pptx",
    ".pyc"
}

def looks_binary(sample: bytes) -> bool:
    """Heurística leve para binário (nulos ou muitos bytes não-imprimíveis)."""
    if b"\x00" in sample:
        return True
    # considera 'não imprimível' fora de \t\r\n e ASCII 32..126
    textish = sum(1 for b in sample if b in (9,10,13) or 32 <= b <= 126)
    if len(sample) == 0:
        return False
    return (textish / len(sample)) < 0.6  # muito “ruim” para ser texto

def is_text_file(path: Path) -> bool:
    """Rápida verificação de binário vs texto."""
    try:
        with path.open("rb") as f:
            chunk = f.read(4096)
        ext = path.suffix.lower()
        # pulo por lista (rápido) e heurística (robusta)
        if ext in DEFAULT_SKIP_BIN_EXTS:
            return False
        return not looks_binary(chunk)
    except Exception:
        # se não consigo ler, não considero texto
        return False

def decode_bytes(data: bytes) -> str:
    """
    Decodifica bytes em string de modo tolerante:
    tenta utf-8, depois utf-16, por fim latin-1 (sem erros).
    """
    for enc in ("utf-8", "utf-16"):
        try:
            return data.decode(enc)
        except Exception:
            pass
    # latin-1 nunca falha
    return data.decode("latin-1", errors="replace")

def export_file(src: Path, out_root: Path, dry_run: bool = False) -> Tuple[bool, Path]:
    """
    Converte um arquivo para .txt no espelho de out_root.
    Retorna (sucesso, caminho_destino).
    """
    rel = src.relative_to(ROOT_DIR)  # ROOT_DIR global setado no main()
    dst = out_root / rel
    dst = dst.with_name(dst.name + ".txt")  # ex.: app.py -> app.py.txt
    if dry_run:
        print(f"[DRY] {src} -> {dst}")
        return True, dst
    dst.parent.mkdir(parents=True, exist_ok=True)
    try:
        with src.open("rb") as f:
            data = f.read()
        text = decode_bytes(data)
        with dst.open("w", encoding="utf-8", newline="") as g:
            g.write(text)
        return True, dst
    except Exception as e:
        print(f"[ERRO] Falha ao processar {src}: {e}")
        return False, dst

def iter_files(root: Path, skip_dirs: Iterable[str]) -> Iterable[Path]:
    """
    Itera arquivos sob 'root', pulando diretórios cujo nome esteja em skip_dirs.
    """
    skip_set = {s.strip() for s in skip_dirs if s.strip()}
    for base, dirs, files in os.walk(root):
        # filtra pastas in-place (para o os.walk não descer nelas)
        dirs[:] = [d for d in dirs if d not in skip_set]
        for name in files:
            yield Path(base, name)

def parse_args():
    ap = argparse.ArgumentParser(description="Exporta arquivos do projeto para .txt (espelhando diretórios).")
    ap.add_argument("--root", required=True, help="Pasta raiz do projeto.")
    ap.add_argument("--out", help="Pasta de saída para o espelho .txt. Padrão: <raiz>_txt_export")
    ap.add_argument("--include-binaries", action="store_true", help="Processa também arquivos binários (NÃO recomendado).")
    ap.add_argument("--extra-skip-dirs", default="", help="Pastas adicionais a ignorar (ex.: .git,.idea,node_modules)")
    ap.add_argument("--ext-allow", default="", help="Se informado, só exporta essas extensões (ex.: .py,.md,.txt)")
    ap.add_argument("--dry-run", action="store_true", help="Apenas mostra o que faria, sem escrever nada.")
    return ap.parse_args()

# Usada em export_file() para montar caminho relativo
ROOT_DIR: Path

def main():
    global ROOT_DIR
    args = parse_args()
    ROOT_DIR = Path(args.root).resolve()
    if not ROOT_DIR.is_dir():
        raise SystemExit(f"Raiz inválida: {ROOT_DIR}")

    out_root = Path(args.out).resolve() if args.out else Path(str(ROOT_DIR) + "_txt_export").resolve()
    out_root.mkdir(parents=True, exist_ok=True)

    extra_skips = {s.strip() for s in args.extra_skip_dirs.split(",") if s.strip()}
    skip_dirs = set(DEFAULT_SKIP_DIRS) | extra_skips

    allow_exts = {s.strip().lower() for s in args.ext_allow.split(",") if s.strip()}
    if allow_exts:
        # normalize para começar com ponto
        allow_exts = {e if e.startswith(".") else f".{e}" for e in allow_exts}

    print(f"[INFO] Raiz: {ROOT_DIR}")
    print(f"[INFO] Saída: {out_root}")
    print(f"[INFO] Pastas ignoradas: {', '.join(sorted(skip_dirs)) or '(nenhuma)'}")
    if allow_exts:
        print(f"[INFO] Extensões permitidas: {', '.join(sorted(allow_exts))}")
    print(f"[INFO] Incluir binários: {'SIM' if args.include_binaries else 'NÃO'}")
    print(f"[INFO] Dry-run: {'SIM' if args.dry_run else 'NÃO'}")

    total = 0
    ok = 0
    skipped = 0

    for path in iter_files(ROOT_DIR, skip_dirs):
        # aplica filtro por extensão, se houver
        if allow_exts and path.suffix.lower() not in allow_exts:
            skipped += 1
            continue

        if not args.include_binaries:
            # pular binários comuns/óbvios
            if path.suffix.lower() in DEFAULT_SKIP_BIN_EXTS:
                skipped += 1
                continue
            # pular o que parecer binário pela heurística
            try:
                with path.open("rb") as f:
                    sample = f.read(4096)
                if looks_binary(sample):
                    skipped += 1
                    continue
            except Exception:
                skipped += 1
                continue

        total += 1
        ok_flag, dst = export_file(path, out_root, dry_run=args.dry_run)
        ok += int(ok_flag)

    print(f"\n[RESUMO] Exportados: {ok}  |  Pulados: {skipped}  |  Total considerados: {total}")
    if not args.dry_run:
        print(f"[OK] Arquivos .txt criados em: {out_root}")

if __name__ == "__main__":
    main()
