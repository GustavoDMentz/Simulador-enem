#!/usr/bin/env python3
"""Diagnostica questões que podem continuar na próxima página/coluna.

Usa a geometria do caderno e informa evidências; não altera recortes nem aprova questões.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

import pymupdf

try:
    from diagnose_pdf_geometry import analyze
except ImportError:
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "diagnose_pdf_geometry", Path(__file__).with_name("diagnose_pdf_geometry.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    analyze = mod.analyze


def inspect_continuation(pdf: pymupdf.Document, record: dict) -> dict:
    p = int(record["page"]) - 1
    current = analyze(pdf[p], record["bbox"])
    if current["ABCDE_detected"]:
        return {"id": record["id"], "status": "already_detected",
                "original_sequence": current["sequence"], "candidates": []}
    rect = pymupdf.Rect(record["bbox"])
    midpoint = pdf[p].rect.width / 2
    side = "left" if rect.x0 < midpoint else "right"
    probes = []
    # Probe only, never merge automatically: columns can change reading order.
    if p + 1 < len(pdf):
        next_page = pdf[p + 1]
        mid = next_page.rect.width / 2
        for candidate_side, left, right in (
            ("left", 0, mid), ("right", mid, next_page.rect.width)
        ):
            clip = [left, 0, right, next_page.rect.height]
            found = analyze(next_page, clip)
            probes.append({
                "page": p + 2, "column": candidate_side,
                "sequence": found["sequence"],
                "combined_sequence": current["sequence"] + found["sequence"],
                "ABCDE_combined": "ABCDE" in current["sequence"] + found["sequence"],
                "note": "Hipótese apenas; a coluna pode conter outras questões.",
            })
    return {"id": record["id"], "number": record.get("original_number"),
            "page": p + 1, "column": side,
            "status": "continuation_requires_boundary_check",
            "original_sequence": current["sequence"], "candidates": probes,
            "publication_authorized": False}


def run(pdf_path: Path, review_path: Path, output_path: Path) -> dict:
    payload = json.loads(review_path.read_text(encoding="utf-8"))
    records = payload.get("records")
    if not isinstance(records, list):
        raise ValueError("Manifesto sem records")
    with pymupdf.open(pdf_path) as pdf:
        results = [inspect_continuation(pdf, record) for record in records]
    report = {"schema_version": 1, "policy": "continuation-probes-v1",
              "summary": dict(Counter(r["status"] for r in results)),
              "results": results, "publication_authorized": False}
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", type=Path, required=True)
    parser.add_argument("--review", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = run(args.pdf, args.review, args.output)
    print(json.dumps(report["summary"], ensure_ascii=False))


if __name__ == "__main__":
    main()
