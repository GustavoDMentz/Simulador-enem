#!/usr/bin/env python3
"""Inventaria elementos visuais de um PDF e gera uma revisão HTML local.

Não altera o PDF, o banco de dados ou os JSONs de questões.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
from pathlib import Path

import fitz


def inspect_page(page: fitz.Page, page_number: int, out_dir: Path, dpi: int) -> dict:
    """Gera prévia da página e inventário de imagens/desenhos."""
    preview = out_dir / f"page_{page_number:03d}.png"
    page.get_pixmap(dpi=dpi, alpha=False).save(str(preview))
    images = []
    seen = set()
    for info in page.get_image_info(xrefs=True):
        bbox = fitz.Rect(info["bbox"])
        if bbox.is_empty or bbox.is_infinite:
            continue
        key = tuple(round(v, 2) for v in bbox)
        if key in seen:
            continue
        seen.add(key)
        images.append({
            "bbox": list(bbox),
            "width": info.get("width"),
            "height": info.get("height"),
            "xref": info.get("xref", 0),
        })
    drawings = [
        list(fitz.Rect(item["rect"]))
        for item in page.get_drawings()
        if not fitz.Rect(item["rect"]).is_empty
    ]
    return {
        "page": page_number,
        "preview": preview.name,
        "size": [page.rect.width, page.rect.height],
        "images": images,
        "drawing_count": len(drawings),
        "needs_review": bool(images or drawings),
    }


def build_report(manifest: dict, out_dir: Path) -> None:
    rows = []
    for page in manifest["pages"]:
        number = page["page"]
        summary = f'{len(page["images"])} imagens raster; {page["drawing_count"]} desenhos vetoriais'
        rows.append(
            '<article><h2>Página ' + str(number) + '</h2>'
            '<p>' + html.escape(summary) + '</p>'
            '<img loading="lazy" alt="Página ' + str(number) + '" src="'
            + html.escape(page["preview"], quote=True) + '"></article>'
        )
    document = (
        '<!doctype html><html lang="pt-BR"><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>Auditoria visual ENEM</title>'
        '<style>body{font:16px system-ui;max-width:1000px;margin:2rem auto;padding:0 1rem}'
        'article{border:1px solid #bbb;border-radius:12px;padding:1rem;margin:1rem 0}'
        'img{display:block;max-width:100%;height:auto}p{color:#555}</style>'
        '<h1>Auditoria visual do PDF</h1>'
        '<p>Prévia das páginas para inspeção humana; ainda não associa figuras a questões.</p>'
        + ''.join(rows) + '</html>'
    )
    (out_dir / "index.html").write_text(document, encoding="utf-8")


def audit(pdf: Path, output: Path, dpi: int) -> dict:
    if not pdf.is_file():
        raise FileNotFoundError(pdf)
    if dpi < 72 or dpi > 300:
        raise ValueError("DPI deve estar entre 72 e 300")
    output.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256()
    with pdf.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    with fitz.open(pdf) as doc:
        manifest = {
            "source_filename": pdf.name,
            "source_sha256": digest.hexdigest(),
            "page_count": len(doc),
            "dpi": dpi,
            "pages": [
                inspect_page(page, index + 1, output, dpi)
                for index, page in enumerate(doc)
            ],
        }
    (output / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    build_report(manifest, output)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", type=Path, required=True, help="Caminho do PDF original")
    parser.add_argument("--output", type=Path, required=True, help="Pasta de saída")
    parser.add_argument("--dpi", type=int, default=120)
    args = parser.parse_args()
    manifest = audit(args.pdf, args.output, args.dpi)
    print(f'{manifest["page_count"]} páginas auditadas. Relatório: {args.output / "index.html"}')


if __name__ == "__main__":
    main()
