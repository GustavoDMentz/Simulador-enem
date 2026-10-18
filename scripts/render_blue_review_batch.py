#!/usr/bin/env python3
"""Render official PDF page candidates for visual review, without changing sources.

Select one exam/day and a small number of missing positions. Generates PNGs
and an HTML index; pages are FULL pages to preserve column and continuation context.
Requires pdftoppm (poppler-utils).
"""
import argparse
import csv
import html
import subprocess
from pathlib import Path

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--manifest", type=Path, default=Path("/tmp/enem-blue-visual-review.csv"))
    p.add_argument("--year", type=int, required=True)
    p.add_argument("--day", type=int, choices=(1,2), required=True)
    p.add_argument("--limit", type=int, default=5)
    p.add_argument("--max-pages", type=int, default=15)
    p.add_argument("--dpi", type=int, default=135)
    p.add_argument("--out", type=Path, default=Path("/tmp/enem-blue-review-images"))
    args = p.parse_args()
    if not 1 <= args.limit <= 20 or not 1 <= args.max_pages <= 40 or not 72 <= args.dpi <= 240:
        p.error("limit 1-20; max-pages 1-40; dpi 72-240")
    with args.manifest.open(encoding="utf-8", newline="") as f:
        rows = [r for r in csv.DictReader(f)
                if int(r["ano"]) == args.year and int(r["dia"]) == args.day
                and r["localizacao_status"] != "BLOCKED"]
    selected = rows[:args.limit]
    if not selected:
        p.error("No available positions for this year/day")
    pages = sorted({int(n) for r in selected
                    for n in r["paginas_candidatas"].split(",") if n.strip()})
    if len(pages) > args.max_pages:
        p.error(f"Selection spans {len(pages)} pages; reduce --limit or explicitly raise --max-pages")
    pdfs = {r["prova_pdf"] for r in selected}
    if len(pdfs) != 1:
        p.error("Multiple PDF sources in selection")
    pdf = Path(next(iter(pdfs)))
    if not pdf.is_file():
        p.error(f"PDF not found: {pdf}")
    out = args.out / f"{args.year}-d{args.day}"
    out.mkdir(parents=True, exist_ok=True)
    for page in pages:
        target = out / f"page-{page:03d}"
        subprocess.run(["pdftoppm", "-f", str(page), "-l", str(page),
                        "-r", str(args.dpi), "-singlefile", "-png",
                        str(pdf), str(target)], check=True,
                       stdout=subprocess.DEVNULL)
    lines = ["<!doctype html><html lang='pt-BR'><meta charset='utf-8'>",
             "<title>ENEM - revisão visual</title>",
             "<style>body{font:16px sans-serif;max-width:1200px;margin:auto;padding:20px}img{width:100%;border:1px solid #aaa}section{margin:2em 0}</style>",
             f"<h1>ENEM {args.year} D{args.day} - revisão visual (não validada)</h1>",
             "<p>Imagens de páginas completas. Conferir colunas, alternativas, créditos, figuras e continuidade.</p>",
             "<h2>Posições selecionadas</h2><ul>"]
    for r in selected:
        lines.append(f"<li>Questão {html.escape(r['posicao'])}: {html.escape(r['localizacao_status'])}; páginas candidatas {html.escape(r['paginas_candidatas'])}</li>")
    lines.append("</ul>")
    for page in pages:
        lines.append(f"<section><h2>Página PDF {page}</h2><img alt='Página {page}' src='page-{page:03d}.png'></section>")
    lines.append("</html>")
    index = out / "index.html"
    index.write_text("\n".join(lines), encoding="utf-8")
    print(f"Questoes selecionadas: {len(selected)}; paginas renderizadas: {len(pages)}")
    print(f"Revisao visual: {index}")
    print("Nenhuma questao foi considerada validada e nenhuma fonte foi modificada.")

if __name__ == "__main__":
    main()
