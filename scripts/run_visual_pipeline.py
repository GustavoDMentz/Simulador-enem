#!/usr/bin/env python3
"""Executa auditoria e segmentação visual e consolida indicadores por caderno."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from audit_pdf_visuals import audit
from segment_question_candidates import run as segment


def pipeline(pdf: Path, output: Path, *, audit_dpi: int = 100,
             crop_dpi: int = 160, expected: int | None = None) -> dict:
    if expected is not None and expected <= 0:
        raise ValueError("expected deve ser positivo")
    if not pdf.is_file():
        raise FileNotFoundError(pdf)
    output.mkdir(parents=True, exist_ok=True)
    page_data = audit(pdf, output / "pages", audit_dpi)
    crop_data = segment(pdf, output / "questions", crop_dpi)
    counts = Counter(c["number"] for c in crop_data["candidates"])
    duplicated = sorted(n for n, count in counts.items() if count > 1)
    found = sorted(counts)
    missing = sorted(set(range(1, expected + 1)) - set(found)) if expected else []
    invalid = sorted(n for n in found if expected and not 1 <= n <= expected)
    visual_pages = sum(p["needs_review"] for p in page_data["pages"])
    report = {
        "source_pdf": pdf.name,
        "source_sha256": page_data["source_sha256"],
        "pages": page_data["page_count"],
        "pages_with_visual_elements": visual_pages,
        "candidate_count": len(crop_data["candidates"]),
        "unique_question_numbers": len(found),
        "question_numbers": found,
        "duplicate_question_numbers": duplicated,
        "missing_question_numbers": missing,
        "out_of_range_question_numbers": invalid,
        "expected_question_count": expected,
        "requires_human_review": True,
        "quality_note": (
            "Contagens heurísticas; não demonstram correção visual nem "
            "correspondência com o gabarito ou microdados."
        ),
        "page_review": "pages/index.html",
        "candidate_review": "questions/index.html",
    }
    (output / "quality-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--audit-dpi", type=int, default=100)
    parser.add_argument("--crop-dpi", type=int, default=160)
    parser.add_argument("--expected", type=int, help="Número esperado de questões, se conhecido")
    args = parser.parse_args()
    result = pipeline(args.pdf, args.output, audit_dpi=args.audit_dpi,
                      crop_dpi=args.crop_dpi, expected=args.expected)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
