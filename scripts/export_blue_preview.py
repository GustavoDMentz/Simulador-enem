#!/usr/bin/env python3
"""Export usable blue questions for a clearly labelled preview, not certified release.

Preserves all 513 non-HOLD candidates where available. Never writes fused or DB.
Unverified answers are removed from preview records to avoid false scoring.
"""
import argparse
import json
from pathlib import Path
from collections import Counter

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--input",type=Path,default=Path("data/blue-staging/release-review/release-candidates.jsonl"))
 p.add_argument("--output",type=Path,default=Path("data/blue-published/preview-questions.jsonl"))
 args=p.parse_args()
 counts=Counter()
 seen=set()
 args.output.parent.mkdir(parents=True,exist_ok=True)
 tmp=args.output.with_suffix(".tmp")
 with args.input.open(encoding="utf-8") as inp,tmp.open("w",encoding="utf-8") as out:
  for line in inp:
   row=json.loads(line)
   status=row["status"]
   if status not in {"CANDIDATE","REVIEW_TEXT","REVIEW_ANSWER","REVIEW_IMAGE"}:continue
   q=row["record"].copy()
   key=(row["ano"],row["dia"],row["posicao"])
   if key in seen:raise SystemExit(f"Duplicate {key}")
   seen.add(key)
   if status!="CANDIDATE":
    q["gabarito_oficial"]=None
    q["parametros_tri"]=None
   q["preview_status"]=status
   q["preview_unverified"]=status!="CANDIDATE"
   q["scoring_enabled"]=status=="CANDIDATE"
   q["preview_warning"]=("Questão em revisão: texto, imagem ou resposta podem estar incorretos. Sem pontuação."
       if status!="CANDIDATE" else None)
   out.write(json.dumps(q,ensure_ascii=False)+"\n")
   counts[status]+=1
 tmp.replace(args.output)
 print(json.dumps({"preview_total":sum(counts.values()),"by_status":dict(counts),
   "scoring_enabled":counts["CANDIDATE"],"output":str(args.output),
   "certified":False,"database_changed":False},ensure_ascii=False,indent=2))
if __name__=="__main__":main()
