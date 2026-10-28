#!/usr/bin/env python3
"""Compare published ENEM questions with staged TRI item parameters, read-only.

Usage: python scripts/match_published_tri.py
"""
import argparse
import collections
import json
from pathlib import Path


def compare(questions, params):
    by_key = {(p["ano"], p["co_item"]): p for p in params}
    stats = collections.defaultdict(lambda: {"total": 0, "matched": 0, "missing": 0, "conflict": 0})
    results = []
    for q in questions:
        year = q["ano"]
        if not 2018 <= year <= 2025:
            continue
        s = stats[str(year)]
        s["total"] += 1
        p = by_key.get((year, q.get("co_item")))
        if p is None:
            status = "MISSING"
            s["missing"] += 1
        elif p["area_conhecimento"] != q["area_conhecimento"] or p["gabarito_oficial"] != q["gabarito_oficial"]:
            status = "CONFLICT"
            s["conflict"] += 1
        else:
            status = "MATCH"
            s["matched"] += 1
        results.append({"id": q["id_unico_sistema"], "ano": year, "co_item": q.get("co_item"),
                        "status": status, "gabarito_local": q["gabarito_oficial"],
                        "gabarito_externo": p["gabarito_oficial"] if p else None,
                        "area_local": q["area_conhecimento"],
                        "area_externa": p["area_conhecimento"] if p else None})
    return dict(stats), results


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--questions", type=Path, default=Path("data/blue-published/questions.jsonl"))
    ap.add_argument("--tri-dir", type=Path, default=Path("data/tri/external-staging"))
    ap.add_argument("--output", type=Path, default=Path("data/tri/external-staging/match-report.json"))
    args = ap.parse_args()
    params = [p for year in range(2018, 2026) for p in read_jsonl(args.tri_dir / f"tri-external-{year}.jsonl")]
    stats, results = compare(read_jsonl(args.questions), params)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({"stats": stats, "results": results}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(stats, ensure_ascii=False))
    if any(s["conflict"] or s["missing"] for s in stats.values()):
        print("WARNING: unresolved mismatches; do not activate these parameters automatically")


if __name__ == "__main__":
    main()
