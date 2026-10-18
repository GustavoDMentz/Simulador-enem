#!/usr/bin/env python3
"""Gera candidato composto para questão que continua na coluna direita.

Não altera a fila nem aprova o candidato. Requer limites explícitos de página.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pymupdf


def generate(pdf_path: Path, queue_path: Path, record_id: str, output: Path,
             right_top: float, right_bottom: float | None = None, dpi: int = 160) -> dict:
    if not pdf_path.is_file():
        raise ValueError("PDF deve ser um arquivo existente")
    queue = json.loads(queue_path.read_text(encoding="utf-8"))
    if hashlib.sha256(pdf_path.read_bytes()).hexdigest() != queue["source_sha256"]:
        raise ValueError("PDF não corresponde ao SHA-256 da fila")
    record = next((r for r in queue["records"] if r["id"] == record_id), None)
    if record is None:
        raise ValueError("Registro não encontrado")
    if not 72 <= dpi <= 300:
        raise ValueError("DPI fora do intervalo permitido")
    with pymupdf.open(pdf_path) as doc:
        page = doc[record["page"] - 1]
        mid = page.rect.width / 2
        left = pymupdf.Rect(record["bbox"])
        if left.x1 > mid + 2:
            raise ValueError("O recorte original não está limitado à coluna esquerda")
        bottom = page.rect.height if right_bottom is None else right_bottom
        if not 0 <= right_top < bottom <= page.rect.height:
            raise ValueError("Limites da coluna direita inválidos")
        right = pymupdf.Rect(mid, right_top, page.rect.width, bottom)
        if right.is_empty or left.is_empty:
            raise ValueError("Segmentos vazios")
        output.mkdir(parents=True, exist_ok=True)
        segments = []
        for name, rect in (("left", left), ("right", right)):
            path = output / f"{name}.png"
            page.get_pixmap(clip=rect, dpi=dpi, alpha=False).save(str(path))
            segments.append({
                "page": record["page"], "bbox": list(rect),
                "image": path.name,
                "image_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "text": page.get_text("text", clip=rect, sort=True),
            })
    report = {
        "id": record_id,
        "source_sha256": queue["source_sha256"],
        "segments": segments,
        "requires_visual_review": True,
        "publication_authorized": False,
    }
    (output / "candidate.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", required=True, type=Path)
    parser.add_argument("--queue", required=True, type=Path)
    parser.add_argument("--id", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--right-top", required=True, type=float)
    parser.add_argument("--right-bottom", type=float)
    parser.add_argument("--dpi", type=int, default=160)
    args = parser.parse_args()
    result = generate(args.pdf, args.queue, args.id, args.output,
                      args.right_top, args.right_bottom, args.dpi)
    print(json.dumps({"id": result["id"], "segments": len(result["segments"]),
                      "output": str(args.output),
                      "publication_authorized": False}, ensure_ascii=False))


if __name__ == "__main__":
    main()
