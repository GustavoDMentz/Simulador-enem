#!/usr/bin/env python3
"""Triagem automatizada e conservadora das filas enriquecidas ENEM.

Não altera as filas nem autoriza publicação. Verifica texto, arquivos e
pendências de continuação; não substitui inspeção visual do PDF original.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

from diagnose_options import diagnose


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit_batch(root: Path) -> dict:
    exams, records = [], []
    for queue in sorted(root.glob("*/enriched/question-review-enriched.json")):
        exam_id = queue.parent.parent.name
        payload = json.loads(queue.read_text(encoding="utf-8"))
        repairs = set(payload.get("continuation_integration", {}).get("repaired_ids", []))
        report_path = queue.parent / "images" / "continuation-report.json"
        report = json.loads(report_path.read_text(encoding="utf-8")) if report_path.exists() else {}
        manual = {x["id"]: x.get("sequence", "") for x in report.get("results", [])
                  if x.get("status") == "manual_review"}
        counts = Counter(x.get("original_number") for x in payload["records"])
        for item in payload["records"]:
            flags = []
            rid = item["id"]
            is_repaired = rid in repairs
            # Repaired images are relative to enriched/; untouched ones retain
            # their original relative paths from review/.
            image_root = queue.parent if is_repaired else queue.parent.parent / "review"
            image = (image_root / item["image"]).resolve()
            image_ok = image.is_file() and digest(image) == item.get("image_sha256")
            if not image_ok:
                flags.append("image_missing_or_hash_mismatch")
            options = diagnose(item)
            if options["category"] != "exact_ABCDE":
                flags.append("options_not_exactly_ABCDE")
            if is_repaired:
                flags.append("composite_requires_visual_check")
            if rid in manual:
                flags.append("unresolved_column_continuation")
            if counts[item["original_number"]] > 1:
                flags.append("duplicate_number_language_variant_check")
            if not str(item.get("extracted_text") or "").strip():
                flags.append("empty_extracted_text")
            if item.get("review_status") != "pending":
                flags.append("unexpected_review_status")
            records.append({
                "exam": exam_id, "id": rid, "number": item["original_number"],
                "option_category": options["category"],
                "option_sequence": options["detected_sequence"],
                "image_hash_verified": image_ok,
                "repaired": is_repaired,
                "continuation_sequence": manual.get(rid),
                "flags": flags,
                "needs_human_review": bool(flags),
                "publication_authorized": False,
            })
        exams.append({"exam": exam_id, "candidates": len(payload["records"]),
                      "repaired": len(repairs), "manual_continuations": len(manual)})
    summary = Counter(flag for item in records for flag in item["flags"])
    return {"schema_version": 1, "policy": "evidence-only-no-auto-approval",
            "exams": exams, "total_exams": len(exams),
            "total_candidates": len(records),
            "flag_counts": dict(sorted(summary.items())),
            "needs_human_review": sum(x["needs_human_review"] for x in records),
            "records": records, "publication_authorized": False}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    report = audit_batch(args.input)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"exams": report["total_exams"],
                      "candidates": report["total_candidates"],
                      "needs_human_review": report["needs_human_review"],
                      "flags": report["flag_counts"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
