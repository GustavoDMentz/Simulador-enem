#!/usr/bin/env python3
"""Diagnostica padrões de alternativas sem alterar ou aprovar questões."""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

from diagnose_options import diagnose


def analyze(root: Path, sample_limit: int = 3) -> dict:
    by_exam = {}
    examples = defaultdict(list)
    categories = Counter()
    for queue in sorted(root.glob("*/enriched/question-review-enriched.json")):
        exam = queue.parent.parent.name
        payload = json.loads(queue.read_text(encoding="utf-8"))
        counts = Counter()
        for record in payload["records"]:
            result = diagnose(record)
            seq = result["detected_sequence"]
            category = result["category"]
            counts[category] += 1
            categories[category] += 1
            # Separate likely leading markers from ambiguous sequences;
            # never interpret this as proof of complete question content.
            pattern = (
                "leading_A_then_ABCDE" if seq == "AABCDE"
                else "exact_ABCDE" if seq == "ABCDE"
                else "other"
            )
            key = (exam, category, pattern)
            if len(examples[key]) < sample_limit:
                examples[key].append({
                    "id": record["id"], "sequence": seq,
                    "option_lines": result["candidate_lines"],
                })
        by_exam[exam] = dict(sorted(counts.items()))
    return {
        "schema_version": 1, "category_totals": dict(sorted(categories.items())),
        "by_exam": by_exam,
        "examples": [
            {"exam": exam, "category": category, "pattern": pattern, "records": items}
            for (exam, category, pattern), items in sorted(examples.items())
        ],
        "publication_authorized": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--sample-limit", type=int, default=3)
    args = parser.parse_args()
    if args.sample_limit < 1:
        parser.error("--sample-limit precisa ser positivo")
    result = analyze(args.input, args.sample_limit)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result["category_totals"], ensure_ascii=False))


if __name__ == "__main__":
    main()
