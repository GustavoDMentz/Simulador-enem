#!/usr/bin/env python3
"""Build a conservative, practical ENEM release candidate file.

No DB writes, no fused mutation. A source PDF text match alone is insufficient.
Only existing records with complete options, positive source token evidence,
and matching parsed official key are eligible. Essential images require review.
"""
import argparse
import json
from pathlib import Path

def read(path):
    with path.open(encoding="utf-8") as f:
        return {(x["ano"],x["dia"],x["posicao"]):x for line in f
                if (x:=json.loads(line))}

def decide(s,t,a):
    existing=s.get("existing_records") or []
    if len(existing)!=1:
        return "HOLD","NO_SINGLE_RECORD"
    if a.get("status")=="ANSWER_DIVERGENCE":
        return "HOLD","ANSWER_DIVERGENCE"
    if t.get("status")=="SUSPECTED_TEXT_DIVERGENCE":
        return "HOLD","TEXT_DIVERGENCE"
    record=existing[0]["record"]
    content=record.get("conteudo") or {}
    options=content.get("alternativas") or {}
    if not str(content.get("enunciado") or "").strip():
        return "HOLD","MISSING_STEM"
    if any(not str(options.get(k) or "").strip() for k in "ABCDE"):
        return "HOLD","MISSING_OPTION"
    checks=t.get("text_evidence") or []
    required={"enunciado",*(f"alternativa_{k}" for k in "ABCDE")}
    exact={c["field"] for c in checks if c.get("status")=="EXACT_TOKEN_SEQUENCE"}
    if not required<=exact:
        return "REVIEW_TEXT","REQUIRED_FIELD_NOT_MATCHED"
    if a.get("status")!="ANSWER_TEXT_MATCH_UNVERIFIED":
        return "REVIEW_ANSWER","ANSWER_NOT_CONFIRMED"
    visual=content.get("metadados_visual") or {}
    if visual.get("contem_imagem"):
        return "REVIEW_IMAGE","IMAGE_DEPENDENCY"
    return "CANDIDATE","TEXT_AND_ANSWER_MATCHED"

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output-dir",type=Path,default=Path("data/blue-staging"))
    args=p.parse_args()
    root=args.output_dir
    s=read(root/"blue-candidates.jsonl")
    t=read(root/"official-validation.jsonl")
    a=read(root/"official-answer-evidence.jsonl")
    if set(s)!=set(t) or set(s)!=set(a):
        raise SystemExit("Evidence keys do not match")
    out=root/"release-review"
    out.mkdir(parents=True,exist_ok=True)
    counts={}
    with (out/"release-candidates.jsonl").open("w",encoding="utf-8") as f:
        for key in sorted(s):
            status,reason=decide(s[key],t[key],a[key])
            counts[status]=counts.get(status,0)+1
            if status=="HOLD":continue
            original=s[key]["existing_records"][0]["record"]
            f.write(json.dumps({"ano":key[0],"dia":key[1],"posicao":key[2],
                "status":status,"reason":reason,"record":original,
                "official_pdf_sha256":t[key].get("source_pdf_sha256"),
                "official_answer_pdf_sha256":a[key].get("official_answer_pdf_sha256"),
                "published":False},ensure_ascii=False)+"\n")
    print(json.dumps({"counts":counts,"output":str(out/"release-candidates.jsonl"),
        "published":0,"note":"REVIEW statuses are NOT approved. Candidates are NOT imported."},
        ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
