#!/usr/bin/env python3
"""Diagnóstico visual de continuidade: páginas inteiras e cabeçalhos próximos.

Somente leitura das fontes. Não corrige recortes nem aprova questões.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import fitz

from segment_question_candidates import find_headers


def inspect(pdf_path: Path, queue_path: Path, record_id: str, output: Path, dpi: int = 110) -> dict:
    if not 72 <= dpi <= 200:
        raise ValueError("DPI fora do intervalo permitido (72..200)")
    queue = json.loads(queue_path.read_text(encoding="utf-8"))
    record = next((r for r in queue["records"] if r["id"] == record_id), None)
    if record is None:
        raise ValueError(f"Registro não encontrado: {record_id}")
    digest = hashlib.sha256(pdf_path.read_bytes()).hexdigest()
    if digest != queue["source_sha256"]:
        raise ValueError("SHA-256 do PDF não coincide com a fila")
    output.mkdir(parents=True, exist_ok=True)
    with fitz.open(pdf_path) as doc:
        page_idx = record["page"] - 1
        if not 0 <= page_idx < len(doc):
            raise ValueError("Página inválida na fila")
        pages = []
        for idx in range(max(0, page_idx - 1), min(len(doc), page_idx + 2)):
            page = doc[idx]
            image = output / f"page_{idx+1:03d}.png"
            page.get_pixmap(dpi=dpi, alpha=False).save(str(image))
            pages.append({
                "page": idx + 1,
                "image": image.name,
                "headers": find_headers(page),
            })
    report = {
        "record_id": record_id,
        "source_pdf": str(pdf_path),
        "source_sha256": digest,
        "original_page": record["page"],
        "original_bbox": record["bbox"],
        "pages": pages,
        "diagnostic_only": True,
        "publication_authorized": False,
    }
    (output / "diagnostic.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", required=True, type=Path)
    parser.add_argument("--queue", required=True, type=Path)
    parser.add_argument("--id", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--dpi", type=int, default=110)
    args = parser.parse_args()
    report = inspect(args.pdf, args.queue, args.id, args.output, args.dpi)
    print(json.dumps({"record_id": report["record_id"],
                      "pages": [{"page": p["page"], "headers": [
                          h["number"] for h in p["headers"]]} for p in report["pages"]],
                      "output": str(args.output),
                      "publication_authorized": False}, ensure_ascii=False))


if __name__ == "__main__":
    main()
