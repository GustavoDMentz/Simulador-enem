#!/usr/bin/env python3
"""Publish only automatically matched ENEM blue candidates into an isolated release.

Usage: python scripts/publish_blue_candidates.py
Creates data/blue-published/questions.jsonl; never modifies fused or ArangoDB.
No review-only or incomplete records are included.
"""
import json
from pathlib import Path
from collections import Counter

ROOT=Path("data/blue-staging/release-review")
DEST=Path("data/blue-published/questions.jsonl")
def main():
    source=ROOT/"release-candidates.jsonl"
    if not source.exists():
        raise SystemExit("Missing release candidates: run build_blue_release_candidates.py first")
    accepted={}
    counts=Counter()
    for line in source.open(encoding="utf-8"):
        row=json.loads(line)
        status=row.get("status")
        counts[status]+=1
        if status!="CANDIDATE": continue
        record=row["record"]
        content=record.get("conteudo") or {}
        opts=content.get("alternativas") or {}
        if not str(content.get("enunciado") or "").strip() or any(not str(opts.get(k) or "").strip() for k in "ABCDE"):
            raise SystemExit("Invalid CANDIDATE: incomplete stem/options")
        key=(row["ano"],row["dia"],row["posicao"])
        if key in accepted:raise SystemExit(f"Duplicate: {key}")
        accepted[key]=record
    if not accepted:raise SystemExit("No eligible candidates: refusing empty publication")
    DEST.parent.mkdir(parents=True,exist_ok=True)
    temp=DEST.with_suffix(".jsonl.tmp")
    with temp.open("w",encoding="utf-8") as f:
        for key in sorted(accepted):
            f.write(json.dumps(accepted[key],ensure_ascii=False)+"\n")
    temp.replace(DEST)
    print(json.dumps({"published_to_file":len(accepted),"path":str(DEST),
        "other_statuses_excluded":{k:v for k,v in counts.items() if k!="CANDIDATE"},
        "database_changed":False},ensure_ascii=False,indent=2))
if __name__=="__main__":main()
