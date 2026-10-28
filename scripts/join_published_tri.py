#!/usr/bin/env python3
"""Join external TRI parameters to published questions without changing answer keys.

Identity: (ano, co_item, area_conhecimento). Answer-key differences are
reported separately and never used to overwrite local answers.
"""
import argparse
import collections
import json
from pathlib import Path


def read_jsonl(path):
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


def join(questions, parameters):
    lookup = {(p["ano"], p["co_item"]): p for p in parameters}
    report = collections.defaultdict(lambda: {"total": 0, "linked": 0, "missing": 0, "area_conflict": 0, "answer_disagreement": 0})
    linked = []
    for q in questions:
        if not 2018 <= q["ano"] <= 2025:
            continue
        s = report[str(q["ano"])]
        s["total"] += 1
        p = lookup.get((q["ano"], q.get("co_item")))
        if p is None:
            s["missing"] += 1
            continue
        if p["area_conhecimento"] != q["area_conhecimento"]:
            s["area_conflict"] += 1
            continue
        s["linked"] += 1
        if q["gabarito_oficial"] != p["gabarito_oficial"]:
            s["answer_disagreement"] += 1
        linked.append({"ano": q["ano"], "id_unico_sistema": q["id_unico_sistema"],
                       "co_item": q["co_item"], "area_conhecimento": q["area_conhecimento"],
                       "a": p["a"], "b": p["b"], "c": p["c"], "fonte": p["fonte"],
                       "status": "IDENTITY_MATCHED_EXTERNAL",
                       "answer_disagreement": q["gabarito_oficial"] != p["gabarito_oficial"]})
    return dict(report), linked


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--questions", type=Path, default=Path("data/blue-published/questions.jsonl"))
    ap.add_argument("--tri-dir", type=Path, default=Path("data/tri/external-staging"))
    ap.add_argument("--output", type=Path, default=Path("data/tri/external-staging/tri-joined-2018-2025.jsonl"))
    ap.add_argument("--report", type=Path, default=Path("data/tri/external-staging/tri-join-report.json"))
    args = ap.parse_args()
    params = [p for y in range(2018, 2026) for p in read_jsonl(args.tri_dir / f"tri-external-{y}.jsonl")]
    stats, rows = join(read_jsonl(args.questions), params)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    args.report.write_text(json.dumps(stats, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(stats, ensure_ascii=False))


if __name__ == "__main__":
    main()
