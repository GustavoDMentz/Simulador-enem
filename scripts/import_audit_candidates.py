#!/usr/bin/env python3
"""Import audit v3 results as QUARANTINED provenance, without overwriting fused/TRI data."""
import argparse
import hashlib
import json
from pathlib import Path

def convert(report):
    if not isinstance(report.get("results"), list):
        raise ValueError("Missing audit results")
    rows = []
    seen = set()
    for exam in report["results"]:
        year = int(exam["year"])
        digest = exam.get("sha256", "")
        if len(digest) != 64 or any(c not in "0123456789abcdefABCDEF" for c in digest):
            raise ValueError(f"Invalid source SHA256: {year}")
        for q in exam.get("selected_questions", []):
            number = int(q["number"])
            key = f"{year}-{number}"
            if key in seen:
                raise ValueError(f"Duplicate candidate: {key}")
            seen.add(key)
            rows.append({
                "id": key, "year": year, "number": number,
                "source_sha256": digest.lower(),
                "status": "INCONCLUSIVA",
                "publication_authorized": False,
                "audit": {"text": False, "options": False, "graphics": False,
                          "credits": False, "continuity": False},
                "provenance": {
                    "extractor_status": q.get("status", "unknown"),
                    "all_five_labels": q.get("all_five_labels") is True,
                    "pixel_verified": False,
                    "source_report": "independent-audit-v3"
                }
            })
    return {"schema_version": 1, "questions": sorted(rows, key=lambda x:(x["year"], x["number"]))}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("data/audit/manifest.json"))
    args = parser.parse_args()
    if args.output.exists():
        old = json.loads(args.output.read_text(encoding="utf-8"))
        if any(x.get("publication_authorized") is True for x in old.get("questions", [])):
            raise SystemExit("Refusing to overwrite an approved manifest")
    converted = convert(json.loads(args.report.read_text(encoding="utf-8")))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(converted, ensure_ascii=False, indent=2)+"\n",encoding="utf-8")
    print(f"Imported {len(converted['questions'])} quarantined candidates; 0 approved.")

if __name__ == "__main__":
    main()
