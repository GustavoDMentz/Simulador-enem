#!/usr/bin/env python3
"""Batch audit existing blue records and geometric candidates against PDF text.

Heuristic checks only. No official validation, database writes, or publishing.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import re
import unicodedata

def norm(value):
    value = unicodedata.normalize("NFKD", str(value or "")).casefold()
    return re.sub(r"[^a-z0-9]+", " ", "".join(c for c in value if not unicodedata.combining(c))).strip()

def tokens(value):
    return [w for w in norm(value).split() if len(w) > 2]

def check_record(q):
    problems = []
    content = q.get("conteudo") or {}
    options = content.get("alternativas") or {}
    if not str(content.get("enunciado") or "").strip():
        problems.append("EMPTY_STATEMENT")
    if set(options) != set("ABCDE") or any(not str(options.get(k) or "").strip() for k in "ABCDE"):
        problems.append("INCOMPLETE_OPTIONS")
    if not q.get("gabarito_oficial") in "ABCDE":
        problems.append("INVALID_ANSWER")
    if not q.get("co_item"):
        problems.append("MISSING_ITEM_ID")
    return problems

def compare_pdf(q, text):
    # Token recall is diagnostic, not proof: official text may be multi-column,
    # contain graphics, or differ in extraction order.
    content = q.get("conteudo") or {}
    options = content.get("alternativas") or {}
    fragments = [content.get("texto_base"), content.get("enunciado")]
    fragments.extend(options.get(letter) for letter in "ABCDE")
    haystack = set(tokens(text))
    reference = [token for fragment in fragments for token in tokens(fragment)]
    if not reference:
        return None
    return round(sum(token in haystack for token in reference) / len(reference), 4)

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", type=Path, default=Path("data/blue-staging/blue-candidates.jsonl"))
    p.add_argument("--output-dir", type=Path, default=Path("data/blue-staging"))
    args = p.parse_args()
    if args.output_dir.resolve() == args.input.resolve():
        p.error("Output must not replace input")
    report = []
    for line in args.input.open(encoding="utf-8"):
        row = json.loads(line)
        item = {"ano":row["ano"],"dia":row["dia"],"posicao":row["posicao"],
                "status":row["status"],"automatically_verified":False,
                "content_verified":False,"answer_verified":False,"tri_verified":False}
        records = row.get("existing_records") or []
        if records:
            q = records[0]["record"]
            problems = check_record(q)
            item["schema_problems"] = problems
            item["category"] = "EXISTING_STRUCTURALLY_PLAUSIBLE" if not problems else "EXISTING_NEEDS_REPAIR"
            item["source"] = records[0]["source"]
            item["pdf_comparison"] = "NOT_AVAILABLE_FOR_EXISTING"
        elif row.get("extraction"):
            extraction = row["extraction"]
            seg = extraction.get("option_segmentation") or {}
            item["category"] = ("NEW_OPTIONS_HYPOTHESIS" if seg.get("status") ==
                                "GEOMETRIC_HYPOTHESIS_UNVERIFIED" else "NEW_NEEDS_RECOVERY")
            item["option_status"] = seg.get("status")
            item["reason"] = seg.get("reason")
        else:
            item["category"] = "SOURCE_OR_HEADING_BLOCKED"
        report.append(item)
    summary = dict(Counter(r["category"] for r in report))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    dest = args.output_dir / "audit-priorities.json"
    dest.write_text(json.dumps({
        "total":len(report),"summary":summary,
        "disclaimer":"Structural triage only. No official PDF fidelity, key, or TRI verified.",
        "records":report},ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"total":len(report),"summary":summary,
                      "output":str(dest)},ensure_ascii=False,indent=2))

if __name__ == "__main__":
    main()
