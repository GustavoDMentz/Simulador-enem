#!/usr/bin/env python3
"""Gera candidatos de recortes por questão, sem modificar o banco.

Os recortes incluem texto, imagens e desenhos como aparecem no PDF.
Candidatos ambíguos devem ser revisados antes de uso no simulador.
"""
from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path

import fitz

HEADER = re.compile(r"^\\s*QUEST[ÃA]O\\s+(\\d{1,3})\\s*$", re.IGNORECASE)


def find_headers(page: fitz.Page) -> list[dict]:
    """Identifica cabeçalhos isolados nos blocos de texto do PDF."""
    found = []
    for block in page.get_text("dict")["blocks"]:
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            spans = line.get("spans", [])
            text = "".join(span.get("text", "") for span in spans).strip()
            match = HEADER.fullmatch(text)
            if match:
                box = fitz.Rect(line["bbox"])
                found.append({"number": int(match.group(1)), "bbox": list(box)})
    return sorted(found, key=lambda item: (item["bbox"][1], item["bbox"][0]))


def segment_page(page: fitz.Page, headers: list[dict], margin: float = 8) -> list[dict]:
    """Corta até o próximo cabeçalho na mesma coluna; não atravessa página."""
    width, height = page.rect.width, page.rect.height
    mid = width / 2
    results = []
    for header in headers:
        rect = fitz.Rect(header["bbox"])
        side = "left" if rect.x0 < mid else "right"
        left, right = (0.0, mid) if side == "left" else (mid, width)
        next_headers = [
            fitz.Rect(other["bbox"]).y0
            for other in headers
            if other is not header
            and ("left" if other["bbox"][0] < mid else "right") == side
            and fitz.Rect(other["bbox"]).y0 > rect.y0 + 1
        ]
        bottom = min(next_headers) if next_headers else height
        clip = fitz.Rect(left, max(0, rect.y0 - margin), right, min(height, bottom))
        if clip.is_empty or clip.height < 12:
            continue
        results.append({
            "number": header["number"],
            "column": side,
            "bbox": list(clip),
            "requires_review": True,
            "review_reason": "Limites heurísticos; pode conter conteúdo de outra questão ou continuação em outra página",
        })
    return results


def run(pdf: Path, output: Path, dpi: int = 160) -> dict:
    if not pdf.is_file():
        raise FileNotFoundError(pdf)
    if not 72 <= dpi <= 300:
        raise ValueError("DPI deve estar entre 72 e 300")
    output.mkdir(parents=True, exist_ok=True)
    candidates = []
    with fitz.open(pdf) as document:
        for index, page in enumerate(document):
            page_number = index + 1
            for candidate in segment_page(page, find_headers(page)):
                name = f"page_{page_number:03d}_q{candidate['number']:03d}_{candidate['column']}.png"
                page.get_pixmap(clip=fitz.Rect(candidate["bbox"]), dpi=dpi, alpha=False).save(str(output / name))
                candidates.append({"page": page_number, "image": name, **candidate})
    manifest = {"source_pdf": pdf.name, "dpi": dpi, "candidates": candidates}
    (output / "candidates.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    items = "".join(
        f'<article><h2>Questão {c["number"]} — página {c["page"]}</h2>'
        f'<p>{html.escape(c["review_reason"])}</p>'
        f'<img loading="lazy" src="{html.escape(c["image"], quote=True)}" alt="Candidato de recorte"></article>'
        for c in candidates
    )
    (output / "index.html").write_text(
        '<!doctype html><html lang="pt-BR"><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>Recortes candidatos ENEM</title>'
        '<style>body{font:16px system-ui;max-width:1000px;margin:2rem auto;padding:1rem}'
        'article{padding:1rem;border:1px solid #bbb;border-radius:10px;margin:1rem 0}'
        'img{max-width:100%;height:auto}</style>'
        '<h1>Recortes candidatos — revisão obrigatória</h1>' + items + '</html>',
        encoding="utf-8",
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--dpi", type=int, default=160)
    args = parser.parse_args()
    result = run(args.pdf, args.output, args.dpi)
    print(f'{len(result["candidates"])} candidatos. Revisar: {args.output / "index.html"}')


if __name__ == "__main__":
    main()
