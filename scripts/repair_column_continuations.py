#!/usr/bin/env python3
"""Recupera continuações da coluna esquerda no topo da coluna direita.

Produz imagens compostas e relatório, sem alterar a fila de revisão original.
A junção só é sugerida quando a sequência A–E aparece na região de continuação.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import pymupdf

HEADER = re.compile(r"^QUESTÃO\s+\d+\s*$")
OPTION = re.compile(r"^\s*([A-E])(?:[).]|\s+)\s*\S")
WATERMARK = "ENEM2024"


def lines_in(page, clip):
    for block in page.get_text("dict", clip=clip)["blocks"]:
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            value = "".join(span.get("text", "") for span in line.get("spans", [])).strip()
            yield value, line["bbox"]


def right_header_y(page):
    mid = page.rect.width / 2
    found = [(bbox[1], value) for value, bbox in lines_in(
        page, pymupdf.Rect(mid, 0, page.rect.width, page.rect.height)
    ) if HEADER.fullmatch(value) and bbox[0] >= mid]
    return min(found) if found else None


def option_sequence(page, clip):
    letters = []
    for value, _ in lines_in(page, clip):
        if WATERMARK in value:
            continue
        m = OPTION.match(value)
        if m:
            letters.append(m.group(1))
    return "".join(letters)


def repair(pdf, record, output_dir):
    if not isinstance(record.get("page"), int):
        raise ValueError("Número de página inválido")
    page = pdf[record["page"] - 1]
    left = pymupdf.Rect(record["bbox"])
    mid = page.rect.width / 2
    if left.x0 >= mid:
        return None
    # Não exigir que o recorte chegue ao rodapé físico: o PDF possui margens.
    if "ABCDE" in option_sequence(page, left):
        return None
    # A questão deve ser a última da coluna esquerda: sem cabeçalho posterior.
    for value, bbox in lines_in(page, pymupdf.Rect(0, left.y0 + 1, mid, page.rect.height)):
        if HEADER.fullmatch(value) and bbox[1] > left.y0 + 5:
            # O recorte começa 8 pt antes do próprio cabeçalho: não o trate
            # como uma questão posterior.
            number = int(re.search(r"[0-9]+", value).group())
            if number != record["original_number"]:
                return None
    next_header = right_header_y(page)
    if next_header is None:
        return None
    top = 50.0
    bottom = max(top, next_header[0] - 1)
    right = pymupdf.Rect(mid, top, page.rect.width, bottom)
    seq = option_sequence(page, right)
    if "ABCDE" not in seq:
        return {"id": record["id"], "status": "manual_review", "sequence": seq}
    zoom = pymupdf.Matrix(1.5, 1.5)
    left_pix = page.get_pixmap(matrix=zoom, clip=left, alpha=False)
    right_pix = page.get_pixmap(matrix=zoom, clip=right, alpha=False)
    # Place both segments vertically; each retains its original PDF provenance.
    combined = pymupdf.Pixmap(
        pymupdf.csRGB,
        pymupdf.IRect(0, 0, max(left_pix.width, right_pix.width),
                      left_pix.height + right_pix.height),
        False,
    )
    combined.clear_with(255)
    combined.copy(left_pix, pymupdf.IRect(0, 0, left_pix.width, left_pix.height))
    combined.copy(right_pix, pymupdf.IRect(
        0, left_pix.height, right_pix.width, left_pix.height + right_pix.height))
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / (record["id"] + "-continuation.png")
    combined.save(path)
    return {"id": record["id"], "number": record["original_number"],
            "page": record["page"], "status": "candidate_for_review",
            "segments": [list(left), list(right)],
            "sequence_in_right_segment": seq, "image": str(path),
            "review_status": "pending", "publication_authorized": False}


def run(pdf_path, review_path, output_dir):
    payload = json.loads(Path(review_path).read_text(encoding="utf-8"))
    with pymupdf.open(pdf_path) as pdf:
        results = []
        for record in payload["records"]:
            result = repair(pdf, record, output_dir)
            if result:
                results.append(result)
    report = {"schema_version": 1, "source_sha256": payload.get("source_sha256"),
              "results": results, "publication_authorized": False}
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "continuation-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", required=True, type=Path)
    parser.add_argument("--review", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    report = run(args.pdf, args.review, args.output)
    print(json.dumps({"candidates": len(report["results"]),
                      "ready_for_review": sum(r["status"] == "candidate_for_review"
                                              for r in report["results"])},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
