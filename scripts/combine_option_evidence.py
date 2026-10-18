#!/usr/bin/env python3
"""Combina evidências de dois extratores sem modificar ou aprovar questões."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


def classify(old: str, new: str) -> str:
    if old == new == "exact_ABCDE":
        return "consensus_exact"
    if "exact_ABCDE" in (old, new):
        return "single_method_exact"
    if "ABCDE_with_extra_markers" in (old, new) or "multiple_ABCDE_sequences" in (old, new):
        return "complete_sequence_with_noise"
    return "inconclusive"


def combine(payload: dict) -> dict:
    records = []
    for record in payload["records"]:
        if "old_category" not in record or "new_category" not in record:
            records.append({**record, "evidence_class": "unavailable",
                            "publication_authorized": False})
            continue
        old, new = record["old_category"], record["new_category"]
        records.append({
            **record,
            "evidence_class": classify(old, new),
            "methods_disagree": old != new,
            "requires_visual_review": True,
            "publication_authorized": False,
        })
    return {
        "schema_version": 1,
        "summary": dict(sorted(Counter(r["evidence_class"] for r in records).items())),
        "disagreements": sum(r.get("methods_disagree", False) for r in records),
        "records": records,
        "publication_authorized": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    data = json.loads(args.input.read_text(encoding="utf-8"))
    result = combine(data)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"summary": result["summary"],
                      "disagreements": result["disagreements"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
