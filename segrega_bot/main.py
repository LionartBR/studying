# main.py
import os, csv, threading
from pathlib import Path
from typing import List, Dict

from ui import App
from util_normalize import normalize_name_for_key, normalize_text_for_search
from search_ac import build_automaton, find_keys_in_text, map_keys_to_displays
from pdf_reader import extract_first_pages_text
from report_writer import write_distribution_report
from copy_engine import copy_plan
from cache_db import load_cache, save_cache, is_unchanged, update_cache_entry, get_cached_names, purge_cache

# -------- util --------
def load_names(txt_path: str) -> List[str]:
    with open(txt_path, "r", encoding="utf-8-sig") as f:
        raw = [ln.strip() for ln in f]
    seen, out = set(), []
    for n in raw:
        if n and n not in seen:
            out.append(n); seen.add(n)
    return out

def scan_pdfs(src_dir: str) -> List[str]:
    pdfs = []
    for root, _, files in os.walk(src_dir):
        for f in files:
            if f.lower().endswith(".pdf"):
                pdfs.append(os.path.join(root, f))
    return pdfs

# -------- controller --------
class Controller:
    def __init__(self, ui: App):
        self.ui = ui
        self.thread = None
        self._cancel = threading.Event()
        self._pause = threading.Event()
        self._pause.clear()

    def bind(self):
        self.ui.bind_handlers(on_start=self.on_start, on_pause=self.on_pause, on_cancel=self.on_cancel)

    def on_start(self, _ui):
        if self.thread and self.thread.is_alive():
            return
        self._cancel.clear()
        self._pause.clear()
        self.thread = threading.Thread(target=self._worker, daemon=True)
        self.thread.start()

    def on_pause(self, _ui):
        if self._pause.is_set():
            self.ui.ui_log("Retomando…")
            self._pause.clear()
        else:
            self.ui.ui_log("Pausado.")
            self._pause.set()

    def on_cancel(self, _ui):
        self._cancel.set()
        self.ui.ui_log("Cancelando…")

    def _wait_if_paused(self):
        while self._pause.is_set() and not self._cancel.is_set():
            self._pause.wait(timeout=0.2)

    def _worker(self):
        try:
            txt_path, src_dir, dst_dir = self.ui.get_paths()
            report_path = self.ui.get_report_path()

            names = load_names(txt_path)
            canon_by_disp = {disp: normalize_name_for_key(disp) for disp in names}
            A, key_to_display = build_automaton(canon_by_disp)

            pdf_paths = scan_pdfs(src_dir)
            cache = load_cache(dst_dir)

            self.ui.ui_set_counts(total=len(pdf_paths), colabs=len(names), found=0, nomatch=0, conflicts=0)
            self.ui.ui_set_progress_total(max(1, len(pdf_paths)))

            files_by_collab: Dict[str, List[str]] = {n: [] for n in names}
            files_no_match: List[str] = []
            plan: Dict[str, List[str]] = {}

            # -------- Fase 1: varredura/matching --------
            for idx, p in enumerate(pdf_paths, 1):
                if self._cancel.is_set(): break
                self._wait_if_paused()
                self.ui.ui_log(f"[{idx}/{len(pdf_paths)}] Lendo: {os.path.basename(p)}")

                if is_unchanged(p, cache):
                    matched_displays = get_cached_names(p, cache) or []
                else:
                    txt, h12 = extract_first_pages_text(p, max_pages=3)
                    base_norm = normalize_text_for_search(Path(p).stem)
                    t_norm = normalize_text_for_search(txt)

                    keys = set()
                    keys |= find_keys_in_text(A, t_norm)
                    keys |= find_keys_in_text(A, base_norm)
                    matched_displays = sorted(map_keys_to_displays(keys, key_to_display))
                    update_cache_entry(dst_dir, cache, p, h12, matched_displays)

                if matched_displays:
                    for d in matched_displays:
                        files_by_collab.setdefault(d, []).append(p)
                    plan[p] = matched_displays[:]
                else:
                    files_no_match.append(p)

                self.ui.ui_step()

            save_cache(dst_dir, cache)

            if self._cancel.is_set():
                self.ui.ui_log("Cancelado antes das cópias.")
                # Purga cache mesmo assim, conforme pedido
                purge_cache(dst_dir)
                self.ui.ui_on_finish(None)
                return

            # -------- Fase 2: cópias/links --------
            total_copy_ops = sum(len(v) for v in plan.values())
            self.ui.ui_log(f"Iniciando cópias/links ({total_copy_ops} destinos)…")
            self.ui.ui_set_progress_total(max(1, total_copy_ops))

            result = copy_plan(plan, dst_dir, max_workers=2)
            conflicts = 0
            created_map = {}
            reason_map = {}
            progress = 0

            # Também montamos o manifest (linhas planas)
            manifest_rows: List[Dict[str, str]] = []

            for pdf_path, res in result.items():
                src_name = os.path.basename(pdf_path)
                for collab, created_path in res.get("created", []):
                    created_map[(collab, pdf_path)] = created_path
                    manifest_rows.append({
                        "source_path": pdf_path,
                        "source_name": src_name,
                        "collaborator": collab,
                        "created_path": created_path,
                        "created_name": os.path.basename(created_path),
                        "status": "created",
                    })
                    progress += 1
                    self.ui.ui_step()
                for collab, reason in res.get("skipped", []):
                    conflicts += 1
                    reason_map[(collab, pdf_path)] = reason
                    manifest_rows.append({
                        "source_path": pdf_path,
                        "source_name": src_name,
                        "collaborator": collab,
                        "created_path": "",
                        "created_name": "",
                        "status": f"skipped:{reason}",
                    })
                    progress += 1
                    self.ui.ui_step()

            # -------- Monta linhas do relatório --------
            rows = []
            not_found_collabs = []
            for collab in names:
                pdfs = files_by_collab.get(collab, [])
                if not pdfs:
                    not_found_collabs.append(collab)
                else:
                    for pdf_path in pdfs:
                        rows.append({
                            "collaborator": collab,
                            "source_path": pdf_path,
                            "created_path": created_map.get((collab, pdf_path), ""),
                            "status": reason_map.get((collab, pdf_path), "created"),
                        })

            # -------- Atualiza contadores --------
            found = sum(1 for collab in names if files_by_collab.get(collab))
            self.ui.ui_set_counts(total=len(pdf_paths), colabs=len(names),
                                  found=found, nomatch=len(files_no_match), conflicts=conflicts)

            # -------- Relatório --------
            final_report = None

            if report_path:
                try:
                    final_report = write_distribution_report(
                        report_path=report_path,
                        collaborators=names,
                        rows=rows,
                        not_found_collabs=not_found_collabs,
                        files_no_match=files_no_match,
                        manifest_rows=manifest_rows,
                    )
                    self.ui.ui_log(f"Relatório salvo em: {final_report}")
                except Exception as e:
                    self.ui.ui_log(f"[ERRO] Falha ao salvar relatório: {e}")

            # -------- Purga cache ao final --------
            try:
                purge_cache(dst_dir)
                self.ui.ui_log("Cache (.cache_distcolab) removido.")
            except Exception:
                pass

            self.ui.ui_on_finish(final_report)

        except Exception as e:
            self.ui.ui_log(f"[ERRO FATAL] {e}")
            # tentativa de purgar cache mesmo em falha
            try:
                _, _, dst_dir = self.ui.get_paths()
                purge_cache(dst_dir)
            except Exception:
                pass
            self.ui.ui_on_finish(None)

# --------- bootstrap ---------
if __name__ == "__main__":
    app = App()
    Controller(app).bind()
    app.mainloop()
