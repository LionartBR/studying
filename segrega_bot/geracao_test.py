# gerar_pdfs_nomes.py
# -----------------------------------------------------------
# Gera 100 PDFs. Cada PDF contém 1, 2 ou 3 nomes escolhidos
# aleatoriamente a partir de uma lista com 200 rótulos.
# Cria também um manifest.csv mapeando arquivo -> nomes.
# -----------------------------------------------------------

from pathlib import Path
from fpdf import FPDF  # pip install fpdf2
import random
import csv

# --- Lista de nomes (como você pediu) ---
NAMES = [f"NOME_{i:03d}" for i in range(1, 201)]

# --- Parâmetros ajustáveis ---
NUM_PDFS = 100
OUTPUT_DIR = Path("pdfs_out")   # pasta de saída
RANDOM_SEED = 42                # troque para None se quiser aleatoriedade diferente a cada execução
NAMES_PER_PDF_CHOICES = [1, 2, 3]

def _shuffled_pool():
    pool = NAMES[:]
    random.shuffle(pool)
    return pool

def _take_names(pool, k):
    """Retira k nomes do 'pool'. Se acabar, reembaralha e continua."""
    taken = []
    while k > 0:
        if not pool:
            pool = _shuffled_pool()
        taken.append(pool.pop())
        k -= 1
    return taken, pool

def _make_pdf(filepath: Path, names):
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_margins(20, 20, 20)
    pdf.add_page()

    # Título
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 10, "Lista de Nomes", ln=1)

    # Conteúdo
    pdf.set_font("Helvetica", "", 14)
    pdf.ln(4)
    for idx, name in enumerate(names, start=1):
        pdf.cell(0, 10, f"{idx}. {name}", ln=1)

    # Rodapé simples
    pdf.set_y(-20)
    pdf.set_font("Helvetica", "I", 9)
    pdf.cell(0, 8, "Gerado automaticamente", align="R")

    pdf.output(str(filepath))

def main():
    if RANDOM_SEED is not None:
        random.seed(RANDOM_SEED)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # manifesto com o mapeamento arquivo -> nomes
    manifest_path = OUTPUT_DIR / "manifest.csv"
    with open(manifest_path, "w", newline="", encoding="utf-8") as mf:
        writer = csv.writer(mf, delimiter=";")
        writer.writerow(["filename", "count", "names"])

        pool = _shuffled_pool()

        for i in range(1, NUM_PDFS + 1):
            k = random.choice(NAMES_PER_PDF_CHOICES)   # 1, 2 ou 3
            chosen, pool = _take_names(pool, k)
            pdf_path = OUTPUT_DIR / f"doc_{i:03d}.pdf"
            _make_pdf(pdf_path, chosen)
            writer.writerow([pdf_path.name, len(chosen), " | ".join(chosen)])

    print(f"OK! {NUM_PDFS} PDFs gerados em: {OUTPUT_DIR.resolve()}")
    print(f"Manifesto: {manifest_path.resolve()}")

if __name__ == "__main__":
    main()
