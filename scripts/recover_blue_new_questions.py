#!/usr/bin/env python3
"""Recover missing blue positions into a separate, unapproved JSONL.

Never writes fused files or database. Uses geometric options only when all A-E
are detected; raw PDF text is retained as evidence, not invented as a stem.
"""
import argparse
import json
from pathlib import Path

def rows(path):
    with path.open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                yield json.loads(line)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output-dir",type=Path,default=Path("data/blue-staging"))
    args=p.parse_args()
    root=args.output_dir
    out=root/"release-review"
    out.mkdir(parents=True,exist_ok=True)
    complete=partial=missing=0
    with (out/"new-question-recovery.jsonl").open("w",encoding="utf-8") as f:
        for row in rows(root/"blue-candidates.jsonl"):
            if row.get("existing_records"):
                continue
            ext=row.get("extraction") or {}
            seg=ext.get("option_segmentation") or {}
            opts=seg.get("options") or {}
            all_options=all(isinstance(opts.get(k),str) and opts[k].strip() for k in "ABCDE")
            status="OPTIONS_RECOVERED_STEM_PENDING" if all_options else "RECOVERY_INCOMPLETE"
            if all_options:complete+=1
            else:partial+=1
            if not ext:missing+=1
            f.write(json.dumps({"ano":row["ano"],"dia":row["dia"],
                "posicao_prova":row["posicao"],"cor_prova":"AZUL",
                "status":status,"conteudo":{"texto_base":None,"enunciado":None,
                    "alternativas":{k:opts.get(k) for k in "ABCDE"}},
                "source":{"pdf":row.get("official_pdf"),"pdf_page":ext.get("pdf_page"),
                    "raw_text":ext.get("raw_text"),"layout_lines":ext.get("layout_lines"),
                    "segmentation_status":seg.get("status")},
                "gabarito_oficial":None,"publishable":False},
                ensure_ascii=False)+"\n")
    print(json.dumps({"new_positions_options_recovered":complete,
        "new_positions_incomplete":partial,"without_extraction":missing,
        "output":str(out/"new-question-recovery.jsonl"),
        "published":0},ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
