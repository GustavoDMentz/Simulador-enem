#!/usr/bin/env python3
"""Triagem determinística das questões extraídas, sem aprovação por IA.

Classifica evidências e pendências. Não publica questões nem altera gabaritos.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

OPTION_RE = re.compile(r"(?m)^\s*([A-E])\s*[).]\s*(\S.*)$")
HEADER_RE = re.compile(r"(?im)^\s*QUEST[ÃA]O\s+(\d{1,3})\b")
SHA_RE = re.compile(r"^[a-f0-9]{64}$")


def inspect(record: dict, *, source_hash: str, duplicate_numbers: set[int],
            images_root: Path | None) -> dict:
    flags, checks = [], {}
    num = record.get("original_number")
    exam = record.get("exam") or {}
    text = record.get("extracted_text") or ""
    checks["source_hash_consistent"] = bool(
        SHA_RE.fullmatch(source_hash) and exam.get("source_sha256") == source_hash)
    if not checks["source_hash_consistent"]:
        flags.append("source_hash_mismatch")
    checks["question_header_found"] = bool(
        isinstance(num, int) and any(int(n) == num for n in HEADER_RE.findall(text)))
    if not checks["question_header_found"]:
        flags.append("header_missing_or_incomplete")
    matches = OPTION_RE.findall(text)
    letters = [letter for letter, _ in matches]
    checks["five_options_detected"] = letters == list("ABCDE")
    if not checks["five_options_detected"]:
        flags.append("options_missing_or_ambiguous")
    checks["duplicate_number"] = num in duplicate_numbers
    if checks["duplicate_number"]:
        flags.append("duplicate_number_or_language_variant")
    checks["answer_key_verified"] = False
    flags.append("official_answer_key_not_verified")
    checks["visual_integrity_verified"] = False
    flags.append("visual_integrity_not_verified")
    checks["image_hash_consistent"] = None
    if images_root is not None:
        # Only resolve a basename inside the explicitly selected folder.
        image_name = Path(str(record.get("image") or "")).name
        image = images_root / image_name
        if image.is_file() and image.suffix.lower() == ".png":
            actual = hashlib.sha256(image.read_bytes()).hexdigest()
            checks["image_hash_consistent"] = actual == record.get("image_sha256")
            if not checks["image_hash_consistent"]:
                flags.append("image_hash_mismatch")
        else:
            flags.append("image_missing")
    return {
        "id": record.get("id"), "number": num,
        "status": "blocked" if not checks["source_hash_consistent"] or
                  checks["image_hash_consistent"] is False else "needs_review",
        "checks": checks, "flags": flags,
        "automatic_approval": False,
    }


def triage(input_path: Path, output_path: Path, images_root: Path | None = None) -> dict:
    data = json.loads(input_path.read_text(encoding="utf-8"))
    records = data.get("records")
    if not isinstance(records, list):
        raise ValueError("Esperado question-review.json com lista records")
    counts = Counter(r.get("original_number") for r in records)
    duplicates = {n for n, count in counts.items() if count > 1}
    results = [inspect(r, source_hash=data.get("source_sha256", ""),
                       duplicate_numbers=duplicates, images_root=images_root)
               for r in records]
    summary = dict(Counter(r["status"] for r in results))
    result = {"schema_version": 1, "source_sha256": data.get("source_sha256"),
              "policy": "conservative-evidence-v1",
              "summary": summary, "results": results}
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--images", type=Path, default=None)
    args = parser.parse_args()
    report = triage(args.input, args.output, args.images)
    print(json.dumps(report["summary"], ensure_ascii=False))


if __name__ == "__main__":
    main()
