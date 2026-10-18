#!/usr/bin/env python3
"""Aplica anotações visuais explícitas a evidências; nunca altera a fila original."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

CROP = {"complete", "incomplete", "uncertain"}
OPTIONS = {"text", "visual", "mixed", "missing", "uncertain"}


def annotate(evidence: dict, annotations: dict) -> dict:
    records = evidence["records"]
    index = {r["id"]: r for r in records}
    if len(index) != len(records):
        raise ValueError("IDs duplicados nas evidências")
    supplied = annotations["annotations"]
    if not isinstance(supplied, list):
        raise ValueError("annotations deve ser lista")
    seen = set()
    notes = {}
    for item in supplied:
        rid = item["id"]
        if rid in seen:
            raise ValueError(f"Anotação duplicada: {rid}")
        seen.add(rid)
        if rid not in index:
            raise ValueError(f"ID desconhecido: {rid}")
        if item["crop_integrity"] not in CROP or item["options_format"] not in OPTIONS:
            raise ValueError(f"Classificação inválida: {rid}")
        if not isinstance(item.get("reviewer_note"), str) or not item["reviewer_note"].strip():
            raise ValueError(f"Justificativa obrigatória: {rid}")
        notes[rid] = item
    result = []
    for row in records:
        note = notes.get(row["id"])
        result.append({
            **row,
            "visual_review": (
                {"crop_integrity": note["crop_integrity"],
                 "options_format": note["options_format"],
                 "reviewer_note": note["reviewer_note"]}
                if note else None
            ),
            "requires_visual_review": note is None or
                note["crop_integrity"] != "complete" or note["options_format"] == "uncertain",
            "publication_authorized": False,
        })
    return {
        "schema_version": 1,
        "summary": dict(sorted(Counter(
            r["visual_review"]["crop_integrity"] if r["visual_review"] else "unreviewed"
            for r in result
        ).items())),
        "records": result,
        "publication_authorized": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--annotations", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    evidence = json.loads(args.input.read_text(encoding="utf-8"))
    notes = json.loads(args.annotations.read_text(encoding="utf-8"))
    result = annotate(evidence, notes)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"summary": result["summary"], "publication_authorized": False},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
