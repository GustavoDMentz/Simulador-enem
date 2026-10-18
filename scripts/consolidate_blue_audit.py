#!/usr/bin/env python3
"""Consolidate independent staging evidence without approving any question.

Read-only: never modifies fused JSONL, official sources or a database.
"""
import argparse
from collections import Counter
import json
from pathlib import Path

POSITIONS = {(year, day, pos)
             for year in range(2017, 2026)
             for day in (1, 2)
             for pos in (range(1, 91) if day == 1 else range(91, 181))}

def load_jsonl(path):
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]

def consolidate(staging, text_evidence, answer_evidence):
    def index(items, source):
        indexed = {}
        duplicates = set()
        for item in items:
            key = (int(item["ano"]), int(item["dia"]),
                   int(item.get("posicao", item.get("posicao_prova", -1))))
            if key in indexed:
                duplicates.add(key)
            indexed[key] = item
        return indexed, duplicates

    staged, sd = index(staging, "staging")
    texts, td = index(text_evidence, "text")
    answers, ad = index(answer_evidence, "answer")
    results = []
    for key in sorted(POSITIONS):
        row, txt, ans = staged.get(key), texts.get(key), answers.get(key)
        problems = []
        if key in sd or key in td or key in ad:
            problems.append("DUPLICATE_POSITION_IN_EVIDENCE")
        if row is None:
            problems.append("STAGING_MISSING")
        if txt is None:
            problems.append("TEXT_EVIDENCE_MISSING")
        if ans is None:
            problems.append("ANSWER_EVIDENCE_MISSING")
        if txt is not None:
            if txt.get("status") in ("SUSPECTED_TEXT_DIVERGENCE",):
                problems.append("SUSPECTED_TEXT_DIVERGENCE")
            if txt.get("status") in ("SOURCE_MISSING", "INCONCLUSIVE",
                                      "INCONCLUSIVE_REGION_BOUNDARY", "TEXT_INCONCLUSIVE",
                                      "CANDIDATE_OPTIONS_INCOMPLETE",
                                      "CANDIDATE_OPTIONS_NEED_RECOVERY"):
                problems.append("TEXT_REVIEW_REQUIRED")
            if any(x.get("status") in ("NOT_EXACT", "EMPTY_FIELD")
                   for x in txt.get("text_evidence", [])):
                problems.append("TEXT_FIELD_MISMATCH_OR_EMPTY")
            if txt.get("visual_warnings"):
                problems.append("VISUAL_UNVERIFIED")
            if txt.get("region_warnings"):
                problems.append("CONTINUATION_UNVERIFIED")
        if ans is not None:
            if ans.get("status") == "ANSWER_DIVERGENCE":
                problems.append("ANSWER_DIVERGENCE")
            elif ans.get("status") != "ANSWER_TEXT_MATCH_UNVERIFIED":
                problems.append("ANSWER_REVIEW_REQUIRED")
        if row and (row.get("publishable") or row.get("content_verified")
                    or row.get("answer_verified") or row.get("tri_verified")):
            problems.append("UNEXPECTED_VERIFIED_FLAG")
        if txt and (txt.get("publishable") or txt.get("full_fidelity_verified")
                    or txt.get("answer_verified") or txt.get("tri_verified")):
            problems.append("UNEXPECTED_VERIFIED_FLAG")
        if ans and (ans.get("publishable") or ans.get("answer_verified")):
            problems.append("UNEXPECTED_VERIFIED_FLAG")
        results.append({"ano":key[0], "dia":key[1], "posicao":key[2],
                        "staging_status":row.get("status") if row else None,
                        "text_status":txt.get("status") if txt else None,
                        "answer_status":ans.get("status") if ans else None,
                        "tri_status":"UNVERIFIED", "problems":sorted(set(problems)),
                        "publishable":False, "full_fidelity_verified":False})
    extras = {"staging": sorted([list(k) for k in staged.keys()-POSITIONS]),
              "text": sorted([list(k) for k in texts.keys()-POSITIONS]),
              "answer": sorted([list(k) for k in answers.keys()-POSITIONS])}
    counts = Counter(problem for item in results for problem in item["problems"])
    summary = {"safe_staging_only":True, "expected_positions":len(POSITIONS),
               "positions_reported":len(results), "publishable":0,
               "fully_verified":0, "problem_counts":dict(sorted(counts.items())),
               "text_statuses":dict(Counter(x["text_status"] for x in results)),
               "answer_statuses":dict(Counter(x["answer_status"] for x in results)),
               "unexpected_positions":extras,
               "warning":"Evidence consolidation is not certification. All positions remain blocked."}
    return results, summary

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output-dir",type=Path,default=Path("data/blue-staging"))
    args = ap.parse_args()
    folder = args.output_dir
    inputs = [folder/"blue-candidates.jsonl",folder/"official-validation.jsonl",
              folder/"official-answer-evidence.jsonl"]
    for path in inputs:
        if not path.is_file():
            ap.error(f"Missing required evidence: {path}")
    results, summary = consolidate(*(load_jsonl(path) for path in inputs))
    with (folder/"audit-matrix.jsonl").open("w",encoding="utf-8") as f:
        for item in results:
            f.write(json.dumps(item,ensure_ascii=False)+"\n")
    (folder/"audit-matrix-summary.json").write_text(
        json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(summary,ensure_ascii=False,indent=2))
    if any(summary["unexpected_positions"].values()) or summary["problem_counts"].get("UNEXPECTED_VERIFIED_FLAG"):
        raise SystemExit("FAIL CLOSED: invalid positions or premature verification flags")

if __name__=="__main__":
    main()
