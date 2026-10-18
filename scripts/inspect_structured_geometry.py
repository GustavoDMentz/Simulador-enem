#!/usr/bin/env python3
"""Inventaria blocos de texto e imagem do PDF para especificação estruturada.

Não decide quais blocos pertencem à questão ou às alternativas.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pymupdf


def inspect(pdf: Path, page_number: int) -> dict:
    if not pdf.is_file():
        raise ValueError("PDF deve ser arquivo existente")
    with pymupdf.open(pdf) as doc:
        if not 1 <= page_number <= len(doc):
            raise ValueError("Página inválida")
        page = doc[page_number - 1]
        items = []
        for i, block in enumerate(page.get_text("dict")["blocks"]):
            rect = pymupdf.Rect(block["bbox"])
            if block["type"] == 0:
                lines = [
                    "".join(s.get("text", "") for s in line.get("spans", []))
                    for line in block.get("lines", [])
                ]
                text = "\n".join(lines).strip()
                if not text:
                    continue
                items.append({"index": i, "type": "text", "bbox": list(rect),
                              "text": text[:600]})
            elif block["type"] == 1:
                items.append({"index": i, "type": "embedded_image",
                              "bbox": list(rect),
                              "width": block.get("width"), "height": block.get("height")})
        drawings = []
        for drawing in page.get_drawings():
            r = drawing.get("rect")
            if r and not r.is_empty:
                drawings.append(list(r))
        return {
            "source_sha256": hashlib.sha256(pdf.read_bytes()).hexdigest(),
            "page": page_number, "page_rect": list(page.rect),
            "blocks": items, "drawing_rects": drawings,
            "publication_authorized": False,
        }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", type=Path, required=True)
    parser.add_argument("--page", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = inspect(args.pdf, args.page)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")
    print(json.dumps({"page": result["page"], "blocks": len(result["blocks"]),
                      "drawings": len(result["drawing_rects"]),
                      "output": str(args.output)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
