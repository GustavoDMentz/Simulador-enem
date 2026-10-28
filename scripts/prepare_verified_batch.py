#!/usr/bin/env python3
"""Prepare a bounded ENEM release batch from existing official-evidence queues.

Does not approve, publish, or modify the database. CANDIDATE is not approval.
"""
import argparse
import json
from collections import Counter
from pathlib import Path

from build_blue_release_candidates import read, decide

def prepare(root, year, day, positions):
    staging = read(root / "blue-candidates.jsonl")
    texts = read(root / "official-validation.jsonl")
    answers = read(root / "official-answer-evidence.jsonl")
    if set(staging) != set(texts) or set(staging) != set(answers):
        raise ValueError("Official evidence queues have different identities")
    selected = sorted(k for k in staging if k[0] == year and k[1] == day
                      and (positions is None or k[2] in positions))
    if positions is not None and {k[2] for k in selected} != positions:
        raise ValueError("Requested positions missing from evidence queues")
    rows = []
    for key in selected:
        status, reason = decide(staging[key], texts[key], answers[key])
        records = staging[key].get("existing_records") or []
        record = records[0].get("record") if len(records) == 1 else None
        rows.append({"ano": key[0], "dia": key[1], "posicao": key[2],
                     "status": status, "reason": reason,
                     "record": record if status == "CANDIDATE" else None,
                     "official_pdf_sha256": texts[key].get("source_pdf_sha256"),
                     "official_answer_pdf_sha256": answers[key].get("official_answer_pdf_sha256"),
                     "publication_authorized": False, "published": False})
    return rows

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output-dir", type=Path, default=Path("data/blue-staging"))
    p.add_argument("--year", type=int, required=True)
    p.add_argument("--day", type=int, choices=(1,2), required=True)
    p.add_argument("--positions", help="Comma-separated positions; default all in exam")
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    positions = None if args.positions is None else {int(n) for n in args.positions.split(",")}
    if positions is not None and not positions:
        p.error("Empty positions list")
    rows = prepare(args.output_dir, args.year, args.day, positions)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    counts = Counter(r["status"] for r in rows)
    print(json.dumps({"exam": f"{args.year}-D{args.day}", "count": len(rows),
                      "statuses": dict(counts), "output": str(args.output),
                      "published": 0, "note": "CANDIDATE requires independent approval and publication gate"},
                     ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
