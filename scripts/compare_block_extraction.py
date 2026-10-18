#!/usr/bin/env python3
"""Compara extração textual existente com blocos nativos do PDF, sem sobrescrever filas."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

import pymupdf

from diagnose_options import diagnose


def extract_blocks(page, segments):
    chunks = []
    for box in segments:
        blocks = page.get_text("blocks", clip=pymupdf.Rect(box), sort=True)
        # Watermarks are typically isolated text blocks (including vertical
        # ENEM/year repetition). Do not filter by keyword in question content.
        text = "\n".join(
            str(b[4]).strip()
            for b in blocks
            if len(b) >= 7 and b[6] == 0
            and not _watermark_block(str(b[4]))
        )
        chunks.append(text)
    return "\n\n".join(chunks).strip()


def _watermark_block(text: str) -> bool:
    tokens = text.split()
    return bool(tokens) and all(token in {"ENEM", "2022", "2023", "2022ENEM", "2023ENEM"}
                                for token in tokens)


def compare(root: Path, manifest: Path) -> dict:
    catalog = json.loads(manifest.read_text(encoding="utf-8"))
    paths = {}
    for item in catalog["exams"]:
        key = f'{item["year"]}-{item.get("application", "regular")}-d{item["day"]}-{item["color"]}'.lower()
        pdf = Path(item["pdf"])
        if not pdf.is_absolute():
            pdf = (manifest.parent / pdf).resolve()
        paths[key] = pdf
    results = []
    for queue in sorted(root.glob("*/enriched/question-review-enriched.json")):
        exam = queue.parent.parent.name
        pdf_path = paths.get(exam)
        if pdf_path is None or not pdf_path.is_file():
            results.append({"exam": exam, "error": "pdf_missing"})
            continue
        data = json.loads(queue.read_text(encoding="utf-8"))
        with pymupdf.open(pdf_path) as pdf:
            for record in data["records"]:
                page = pdf[record["page"] - 1]
                segments = [s["bbox"] for s in record.get("source_segments", [])]
                if not segments:
                    segments = [record["bbox"]]
                clean = extract_blocks(page, segments)
                old = diagnose(record)
                new = diagnose({"extracted_text": clean})
                results.append({
                    "exam": exam, "id": record["id"],
                    "old_category": old["category"], "new_category": new["category"],
                    "old_sequence": old["detected_sequence"],
                    "new_sequence": new["detected_sequence"],
                    "changed": old["category"] != new["category"],
                    "publication_authorized": False,
                })
    return {"schema_version": 1, "summary_old": dict(Counter(
                r["old_category"] for r in results if "old_category" in r)),
            "summary_new": dict(Counter(
                r["new_category"] for r in results if "new_category" in r)),
            "records": results, "publication_authorized": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = compare(args.input, args.manifest)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"old": result["summary_old"], "new": result["summary_new"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
