#!/usr/bin/env python3
"""Diagnóstico reproduzível de alternativas em recortes reais do ENEM.

Detectar A–E em ordem é uma evidência parcial, nunca aprovação editorial.
Não edita nem publica questões.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

# INEP costuma usar "A texto", mas também pode usar "A)" ou "A.".
# Não usar \s aqui: ele pode consumir quebras de linha.
OPTION = re.compile(r"(?m)^[ \t]*([A-E])(?:[).]|[ \t]+)[ \t]*(\S[^\r\n]*)$")
WATERMARK = re.compile(r"(?:ENEM2024){3,}")


def diagnose(record: dict) -> dict:
    text = str(record.get("extracted_text") or "")
    clean = WATERMARK.sub("", text)
    candidates = OPTION.findall(clean)
    sequence = "".join(letter for letter, _ in candidates)
    starts = [i for i in range(max(0, len(sequence) - 4))
              if sequence[i:i + 5] == "ABCDE"]
    if sequence == "ABCDE":
        category = "exact_ABCDE"
    elif len(starts) == 1:
        category = "ABCDE_with_extra_markers"
    elif len(starts) > 1:
        category = "multiple_ABCDE_sequences"
    elif "ABCD" in sequence:
        category = "ABCD_without_E"
    else:
        category = "missing_or_disordered_options"
    return {
        "id": record.get("id"),
        "number": record.get("original_number"),
        "page": record.get("page"),
        "category": category,
        "detected_sequence": sequence,
        "candidate_lines": [{"letter": letter, "preview": value[:100]}
                            for letter, value in candidates],
        "flags": (["extra_option_like_lines"] if category == "ABCDE_with_extra_markers"
                  else []),
        "safe_to_publish": False,
    }


def run(input_path: Path, output_path: Path) -> dict:
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    records = payload.get("records")
    if not isinstance(records, list):
        raise ValueError("Manifesto precisa de records")
    items = [diagnose(r) for r in records]
    report = {
        "schema_version": 1,
        "source_sha256": payload.get("source_sha256"),
        "summary": dict(Counter(item["category"] for item in items)),
        "total": len(items),
        "records": items,
        "publication_authorized": False,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = run(args.input, args.output)
    print(json.dumps({"total": report["total"], "summary": report["summary"]},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
