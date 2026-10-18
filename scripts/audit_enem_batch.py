#!/usr/bin/env python3
"""Auditoria somente-leitura das filas enriquecidas do ENEM."""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def audit(root: Path) -> dict:
    exams = []
    findings = []
    for queue in sorted(root.glob("*/enriched/question-review-enriched.json")):
        exam_id = queue.parent.parent.name
        data = json.loads(queue.read_text(encoding="utf-8"))
        records = data["records"]
        expected = 95 if "-d1-" in exam_id else 90
        counts = Counter(r["original_number"] for r in records)
        repaired = set(data.get("continuation_integration", {}).get("repaired_ids", []))
        flags = Counter()
        report_path = queue.parent / "images" / "continuation-report.json"
        manual_ids = set()
        if report_path.is_file():
            report = json.loads(report_path.read_text(encoding="utf-8"))
            manual_ids = {x["id"] for x in report.get("results", [])
                          if x.get("status") == "manual_review"}
        if len(records) != expected:
            findings.append({"exam": exam_id, "issue": "unexpected_count", "actual": len(records), "expected": expected})
        for record in records:
            issues = []
            if record["original_number"] < 1 or record["original_number"] > 180:
                issues.append("invalid_number")
            if counts[record["original_number"]] > 1:
                issues.append("duplicate_number_language_check")
            if record["id"] in repaired:
                issues.append("composite_crop_visual_check")
            if record["id"] in manual_ids:
                issues.append("continuation_manual_review")
            if record.get("review_status") != "pending":
                issues.append("non_pending_review_status")
            if record.get("alternatives") is None:
                flags["alternatives_unvalidated"] += 1
            if record.get("correct_option") is None:
                flags["answer_unvalidated"] += 1
            image = (queue.parent / record["image"]).resolve()
            if not image.is_file():
                issues.append("missing_image")
            elif sha256(image) != record["image_sha256"]:
                issues.append("image_hash_mismatch")
            if not record.get("extracted_text", "").strip():
                issues.append("empty_extracted_text")
            if issues:
                findings.append({"exam": exam_id, "id": record["id"], "number": record["original_number"], "issues": issues})
        exams.append({"exam": exam_id, "candidates": len(records), "expected": expected,
                      "repaired": len(repaired), "continuation_manual_review": len(manual_ids), "duplicate_numbers": sorted(n for n, c in counts.items() if c > 1),
                      **flags})
    return {"schema_version": 1, "exams": exams, "total_exams": len(exams),
            "total_candidates": sum(e["candidates"] for e in exams),
            "findings": findings, "publication_authorized": False}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.input)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"exams": result["total_exams"], "candidates": result["total_candidates"],
                      "findings": len(result["findings"]), "output": str(args.output)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
