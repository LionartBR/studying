# ui.py
import os
import subprocess
import sys
import webbrowser
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinter.scrolledtext import ScrolledText

APP_TITLE = "CEFGD - BOT DE DISTRIBUIÇÃO"
DEFAULT_REPORT_NAME = "relatorio_distribuicao.xlsx"


def open_path(path):
    """Abre um arquivo ou diretório de acordo com o sistema operacional."""
    target = str(path)
    if not target:
        raise ValueError("Caminho vazio.")

    if sys.platform.startswith('win'):
        os.startfile(target)
        return True

    try:
        subprocess.Popen(['xdg-open', target])
        return True
    except (FileNotFoundError, OSError):
        pass

    if webbrowser.open(target):
        return True

    raise RuntimeError(f"Não foi possível abrir o caminho: {target}")


# ---------- Widgets compostos ----------
class PathField(ttk.Frame):
    """Entrada de caminho com botões de selecionar e limpar.
    mode: "file" | "dir" | "savefile"
    """

    def __init__(self, master, *, mode: str = "file", placeholder: str = "", width: int = 60,
                 filetypes=(('Text files', '*.txt'), ('All files', '*.*')),
                 defaultextension: str | None = None, initialfile: str | None = None):
        super().__init__(master)
        self.mode = mode
        self.filetypes = filetypes
        self.defaultextension = defaultextension
        self.initialfile = initialfile
        self.var = tk.StringVar(value="")

        self.entry = ttk.Entry(self, textvariable=self.var, width=width)
        self.btn_pick = ttk.Button(self, text="Selecionar", command=self._pick)
        self.btn_clear = ttk.Button(self, text="Limpar", command=lambda: self.var.set(""))

        self.entry.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        self.btn_pick.grid(row=0, column=1, padx=(0, 6))
        self.btn_clear.grid(row=0, column=2)
        self.columnconfigure(0, weight=1)

        if placeholder:
            self.entry.insert(0, placeholder)

    def _pick(self):
        path = None
        if self.mode == "file":
            path = filedialog.askopenfilename(title="Selecione o arquivo",
                                              filetypes=self.filetypes)
        elif self.mode == "savefile":
            path = filedialog.asksaveasfilename(
                title="Salvar relatório como…",
                defaultextension=self.defaultextension,
                filetypes=self.filetypes,
                initialfile=self.initialfile
            )
        else:
            path = filedialog.askdirectory(title="Selecione a pasta")
        if path:
            self.var.set(path)

    def get(self) -> str:
        return self.var.get().strip()

    def set(self, value: str):
        self.var.set(value)

    def open(self):
        path = self.get()
        if not path:
            return
        p = Path(path)
        try:
            if p.is_dir():
                open_path(p)
            elif p.exists():
                open_path(p.parent)
        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível abrir: {e}")


# ---------- App ----------
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("900x520")
        self.minsize(820, 480)
        self._setup_style()
        self._build_ui()
        self._bind_shortcuts()
        # callbacks externos
        self._on_start = None
        self._on_pause = None
        self._on_cancel = None

    # ---- Estilo ----
    def _setup_style(self):
        style = ttk.Style(self)
        try:
            style.theme_use('vista')
        except tk.TclError:
            style.theme_use('clam')
        style.configure('TButton', padding=(10, 6))
        style.configure('Danger.TButton', foreground='#b00020')
        style.configure('Muted.TLabel', foreground='#666')

    # ---- Layout principal ----
    def _build_ui(self):
        pad = dict(padx=12, pady=8)

        # Entradas
        frm_inputs = ttk.LabelFrame(self, text="Entradas")
        frm_inputs.grid(row=0, column=0, sticky="ew", **pad)
        frm_inputs.columnconfigure(1, weight=1)

        ttk.Label(frm_inputs, text="Lista colaboradores (.txt):").grid(row=0, column=0, sticky="w")
        self.f_txt = PathField(frm_inputs, mode="file", filetypes=(("TXT", "*.txt"), ("Todos", "*.*")))
        self.f_txt.grid(row=0, column=1, sticky="ew")

        ttk.Label(frm_inputs, text="Pasta origem (PDFs):").grid(row=1, column=0, sticky="w")
        self.f_src = PathField(frm_inputs, mode="dir")
        self.f_src.grid(row=1, column=1, sticky="ew")
        ttk.Button(frm_inputs, text="Abrir", command=self.f_src.open).grid(row=1, column=2)

        ttk.Label(frm_inputs, text="Pasta destino:").grid(row=2, column=0, sticky="w")
        self.f_dst = PathField(frm_inputs, mode="dir")
        self.f_dst.grid(row=2, column=1, sticky="ew")
        ttk.Button(frm_inputs, text="Abrir", command=self.f_dst.open).grid(row=2, column=2)

        # Relatório
        frm_rep = ttk.LabelFrame(self, text="Relatório")
        frm_rep.grid(row=1, column=0, sticky="ew", **pad)
        frm_rep.columnconfigure(1, weight=1)

        self.var_report = tk.BooleanVar(value=True)
        self.var_open_rep = tk.BooleanVar(value=False)

        ttk.Checkbutton(frm_rep, text="Gerar Excel", variable=self.var_report).grid(row=0, column=0, sticky="w")
        self.f_report = PathField(
            frm_rep,
            mode="savefile",
            filetypes=(("Excel", "*.xlsx"), ("Todos", "*.*")),
            defaultextension=".xlsx",
            initialfile=DEFAULT_REPORT_NAME
        )
        self.f_report.grid(row=0, column=1, sticky="ew")
        ttk.Checkbutton(frm_rep, text="Abrir ao finalizar", variable=self.var_open_rep).grid(row=0, column=2, sticky="w")

        # Execução / Status
        frm_run = ttk.LabelFrame(self, text="Execução")
        frm_run.grid(row=2, column=0, sticky="nsew", **pad)
        self.columnconfigure(0, weight=1)
        frm_run.columnconfigure(0, weight=1)
        frm_run.rowconfigure(3, weight=1)

        self.prog = ttk.Progressbar(frm_run, mode='determinate')
        self.prog.grid(row=0, column=0, sticky="ew", pady=(2, 6))

        grid_ind = ttk.Frame(frm_run)
        grid_ind.grid(row=1, column=0, sticky="ew")
        for i in range(8):
            grid_ind.columnconfigure(i, weight=1)
        self.lbl_total = ttk.Label(grid_ind, text="PDFs: 0", style='Muted.TLabel')
        self.lbl_colabs = ttk.Label(grid_ind, text="Colaboradores: 0", style='Muted.TLabel')
        self.lbl_found = ttk.Label(grid_ind, text="Encontrados: 0", style='Muted.TLabel')
        self.lbl_nomatch = ttk.Label(grid_ind, text="Sem match: 0", style='Muted.TLabel')
        self.lbl_conflicts = ttk.Label(grid_ind, text="Conflitos: 0", style='Muted.TLabel')
        for i, w in enumerate([self.lbl_total, self.lbl_colabs, self.lbl_found, self.lbl_nomatch, self.lbl_conflicts]):
            w.grid(row=0, column=i, sticky="w")

        self.log = ScrolledText(frm_run, height=9, state='normal')
        self.log.grid(row=3, column=0, sticky="nsew", pady=(6, 6))
        self.ui_log("Pronto.")

        btns = ttk.Frame(frm_run)
        btns.grid(row=4, column=0, sticky="ew")
        btns.columnconfigure(0, weight=1)
        left = ttk.Frame(btns); right = ttk.Frame(btns)
        left.grid(row=0, column=0, sticky="w"); right.grid(row=0, column=1, sticky="e")

        self.btn_start = ttk.Button(left, text="Iniciar", command=self.start)
        self.btn_pause = ttk.Button(left, text="Pausar", state='disabled', command=self.pause)
        self.btn_cancel = ttk.Button(left, text="Cancelar", style='Danger.TButton', state='disabled', command=self.cancel)
        self.btn_new = ttk.Button(left, text="Novo", state='disabled', command=self.new)
        self.btn_new.grid(row=0, column=3, padx=(6, 0))
        self.btn_start.grid(row=0, column=0, padx=(0, 6))
        self.btn_pause.grid(row=0, column=1, padx=(0, 6))
        self.btn_cancel.grid(row=0, column=2)

        self.btn_open_report = ttk.Button(right, text="Abrir relatório", state='disabled', command=self._open_report)
        self.btn_open_dst = ttk.Button(right, text="Abrir pasta destino", state='disabled', command=self.f_dst.open)
        self.btn_open_report.grid(row=0, column=0, padx=(0, 6))
        self.btn_open_dst.grid(row=0, column=1)

    # ---- binding externo ----
    def bind_handlers(self, *, on_start, on_pause, on_cancel):
        self._on_start = on_start
        self._on_pause = on_pause
        self._on_cancel = on_cancel

    # ---- atalhos e validação ----
    def _bind_shortcuts(self):
        self.bind('<Return>', lambda e: self.start())
        self.bind('<Escape>', lambda e: self._on_exit())
        self.protocol("WM_DELETE_WINDOW", self._on_exit)

    def _validate_inputs(self) -> bool:
        txt, src, dst = self.f_txt.get(), self.f_src.get(), self.f_dst.get()
        if not txt or not Path(txt).is_file():
            messagebox.showwarning("Entrada inválida", "Selecione o arquivo TXT de colaboradores.")
            return False
        if not src or not Path(src).is_dir():
            messagebox.showwarning("Entrada inválida", "Selecione a pasta de origem dos PDFs.")
            return False
        if not dst or not Path(dst).is_dir():
            messagebox.showwarning("Entrada inválida", "Selecione a pasta destino.")
            return False
        if self.var_report.get() and not self.f_report.get():
            # default: salva o relatório dentro da pasta destino
            self.f_report.set(str(Path(dst) / DEFAULT_REPORT_NAME))
        return True

    # ---- ações dos botões (chamam callbacks externos) ----
    def start(self):
        if not self._validate_inputs():
            return
        self.ui_log("Processamento iniciado…")
        self._toggle_buttons(running=True)
        if self._on_start:
            self._on_start(self)

    def pause(self):
        self.ui_log("Pausa solicitada…")
        if self._on_pause:
            self._on_pause(self)

    def cancel(self):
        self.ui_log("Cancelamento solicitado…")
        if self._on_cancel:
            self._on_cancel(self)

    def _toggle_buttons(self, running: bool):
        self.btn_start.configure(state='disabled' if running else 'normal')
        self.btn_pause.configure(state='normal' if running else 'disabled')
        self.btn_cancel.configure(state='normal' if running else 'disabled')
        self.btn_new.configure(state='disabled')  # só habilita ao finalizar
        self.btn_open_dst.configure(state='disabled' if running else 'normal')
        self.btn_open_report.configure(state='disabled')

    # ---- helpers thread-safe para o main usar ----
    def ui_log(self, msg: str):
        self.after(0, lambda: (self.log.insert('end', msg + "\n"), self.log.see('end')))

    def ui_set_counts(self, *, total=0, colabs=0, found=0, nomatch=0, conflicts=0):
        def _apply():
            self.lbl_total.config(text=f"PDFs: {total}")
            self.lbl_colabs.config(text=f"Colaboradores: {colabs}")
            self.lbl_found.config(text=f"Encontrados: {found}")
            self.lbl_nomatch.config(text=f"Sem match: {nomatch}")
            self.lbl_conflicts.config(text=f"Conflitos: {conflicts}")
        self.after(0, _apply)

    def ui_set_progress_total(self, total: int):
        self.after(0, lambda: (self.prog.config(maximum=max(1, total)), self.prog.config(value=0)))

    def ui_set_progress(self, value: int):
        self.after(0, lambda: self.prog.config(value=min(value, int(self.prog['maximum']))))

    def ui_step(self, inc: int = 1):
        def _apply():
            self.prog.config(value=min(self.prog['value'] + inc, self.prog['maximum']))
        self.after(0, _apply)

    def ui_on_finish(self, report_path: str | None):
        def _apply():
            self.ui_log("Concluído!")

            # Mantém INICIAR desabilitado para evitar duplicidade
            self.btn_start.configure(state='disabled')
            self.btn_pause.configure(state='disabled')
            self.btn_cancel.configure(state='disabled')

            # Habilita 'Novo' e botões de abrir
            self.btn_new.configure(state='normal')
            self.btn_open_dst.configure(state='normal')
            if report_path and Path(report_path).exists():
                if self.var_open_rep.get():
                    try:
                        open_path(report_path)
                    except Exception:
                        pass
                self.btn_open_report.configure(state='normal')
        self.after(0, _apply)

    def new(self):
        """Limpa campos/estado e reabilita o botão Iniciar."""
        self._reset_form()

    def _reset_form(self):
        # Limpa caminhos
        self.f_txt.set("")
        self.f_src.set("")
        self.f_dst.set("")
        # Reseta caminho do relatório para o nome padrão (sem pasta)
        self.f_report.set(DEFAULT_REPORT_NAME)

        # Zera progresso e contadores
        self.prog.config(value=0, maximum=100)
        self.ui_set_counts(total=0, colabs=0, found=0, nomatch=0, conflicts=0)

        # Limpa log
        self.log.delete('1.0', 'end')
        self.ui_log("Pronto.")

        # Desabilita botões de abrir
        self.btn_open_dst.configure(state='disabled')
        self.btn_open_report.configure(state='disabled')

        # Reabilita Iniciar e desabilita 'Novo' até a próxima conclusão
        self.btn_start.configure(state='normal')
        self.btn_new.configure(state='disabled')

    # acessos aos caminhos
    def get_paths(self):
        return self.f_txt.get(), self.f_src.get(), self.f_dst.get()

    def get_report_path(self) -> str | None:
        if not self.var_report.get():
            return None
        raw = self.f_report.get().strip()
        if not raw:
            return None
        p = Path(raw)
        if not p.suffix:
            p = p.with_suffix(".xlsx")
        if not p.is_absolute():
            dst = Path(self.f_dst.get()) if self.f_dst.get() else Path.cwd()
            p = dst / p
        return str(p)

    def _open_report(self):
        p = self.get_report_path()
        if not p:
            messagebox.showinfo("Relatório", "Nenhum caminho de relatório definido.")
            return
        P = Path(p)
        if P.exists():
            try:
                open_path(P)
            except Exception as e:
                messagebox.showerror("Erro", f"Não foi possível abrir o relatório:\n{e}")
        else:
            messagebox.showinfo("Relatório", f"Arquivo não encontrado:\n{P}")

    def _on_exit(self):
        self.destroy()
