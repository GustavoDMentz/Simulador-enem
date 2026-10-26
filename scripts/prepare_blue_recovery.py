#!/usr/bin/env python3
"""Read-only preflight: missing blue positions and official PDF availability."""
import argparse
import csv
from collections import Counter
from pathlib import Path

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--missing", type=Path, default=Path("/tmp/enem-blue-missing.csv"))
    p.add_argument("--pdf-dir", type=Path, default=Path("data/enem-pdfs/oficiais"))
    p.add_argument("--output", type=Path, default=Path("/tmp/enem-blue-recovery-queue.csv"))
    args = p.parse_args()
    with args.missing.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    expected = {(y, d) for y in range(2017, 2026) for d in (1, 2)}
    documents = {}
    for y, d in sorted(expected):
        stem = f"{y}-regular-d{d}-azul"
        documents[(y, d)] = (
            args.pdf_dir / (stem + ".pdf"),
            args.pdf_dir / (stem + "-gabarito.pdf"),
        )
    queue = []
    for row in rows:
        y, d, pos = int(row["ano"]), int(row["dia"]), int(row["posicao"])
        if (y, d) not in expected or pos not in (range(1, 91) if d == 1 else range(91, 181)):
            raise ValueError(f"Invalid missing position: {row}")
        pdf, key = documents[(y, d)]
        queue.append({
            "ano": y, "dia": d, "posicao": pos,
            "prova_pdf": str(pdf) if pdf.is_file() else "",
            "gabarito_pdf": str(key) if key.is_file() else "",
            "status": "PRONTO_PARA_MAPEAR_PAGINA" if pdf.is_file() and key.is_file() else "FONTE_OFICIAL_INCOMPLETA",
            "idioma_requer_verificacao": row["idioma_requer_verificacao"],
        })
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(queue[0]) if queue else [
            "ano","dia","posicao","prova_pdf","gabarito_pdf","status","idioma_requer_verificacao"
        ])
        w.writeheader()
        w.writerows(queue)
    counts = Counter(r["status"] for r in queue)
    print(f"Lacunas: {len(queue)}; fontes completas: {counts['PRONTO_PARA_MAPEAR_PAGINA']}; fontes incompletas: {counts['FONTE_OFICIAL_INCOMPLETA']}")
    for (y,d),(pdf,key) in sorted(documents.items()):
        if not pdf.is_file() or not key.is_file():
            print(f"Documentos faltantes {y} D{d}: prova={pdf.is_file()} gabarito={key.is_file()}")
    print(f"Fila: {args.output}")
    print("Nenhum arquivo de dados ou banco de dados foi modificado.")

if __name__ == "__main__":
    main()
