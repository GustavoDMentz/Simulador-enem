#!/usr/bin/env python3
"""Export review-ready evidence bundles for priority-01 questions.

Renders original official PDF pages alongside existing records and extracted
alternatives. Never approves or publishes automatically.
"""
import argparse
import html
import json
from collections import defaultdict
from pathlib import Path

try:
    import pymupdf
except ImportError as exc:
    raise SystemExit("Install PyMuPDF: python -m pip install pymupdf") from exc

def read_jsonl(path):
    with path.open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                yield json.loads(line)

def esc(value):
    return html.escape(str(value or ""))

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--output-dir",type=Path,default=Path("data/blue-staging"))
    ap.add_argument("--limit",type=int,default=0,help="0 exports all priority-01 positions")
    args=ap.parse_args()
    root=args.output_dir
    queue=list(read_jsonl(root/"release-review/review-queue.jsonl"))
    stage={(r["ano"],r["dia"],r["posicao"]):r for r in read_jsonl(root/"blue-candidates.jsonl")}
    chosen=[r for r in queue if r["priority"]=="01_REVIEW_CONTENT_VISUAL_ANSWER"]
    if args.limit>0:
        chosen=chosen[:args.limit]
    out=root/"release-review"/"visual"
    out.mkdir(parents=True,exist_ok=True)
    grouped=defaultdict(list)
    for row in chosen:
        grouped[(row["ano"],row["dia"])].append(row)
    count=0
    for (year,day),rows in sorted(grouped.items()):
        folder=out/f"{year}-d{day}"
        folder.mkdir(exist_ok=True)
        documents={}
        cards=[]
        try:
            for row in rows:
                key=(year,day,row["posicao"])
                item=stage[key]
                extraction=item.get("extraction") or {}
                page=extraction.get("pdf_page")
                pdf=item.get("official_pdf")
                if not pdf or not page:
                    continue
                if pdf not in documents:
                    documents[pdf]=pymupdf.open(pdf)
                doc=documents[pdf]
                if not 1<=int(page)<=len(doc):
                    continue
                image_name=f"page-{int(page):03d}.png"
                image_path=folder/image_name
                if not image_path.exists():
                    doc[int(page)-1].get_pixmap(matrix=pymupdf.Matrix(1.5,1.5),alpha=False).save(image_path)
                existing=item.get("existing_records") or []
                record=existing[0]["record"] if len(existing)==1 else {}
                content=record.get("conteudo") or {}
                options=content.get("alternativas") or {}
                extracted=(extraction.get("option_segmentation") or {}).get("options") or {}
                def opts(values):
                    return "".join(f"<li><b>{letter}</b> {esc(values.get(letter))}</li>" for letter in "ABCDE")
                cards.append(f"""<article><h2>Questão {row['posicao']} · página {page}</h2>
<p><b>Texto:</b> {esc(row['text_status'])} · <b>Gabarito:</b> {esc(row['answer_status'])}</p>
<div class="cols"><section><h3>PDF oficial — página completa</h3><img src="{image_name}" alt="Página {page} do PDF oficial"></section>
<section><h3>Registro existente</h3><p>{esc(content.get('texto_base'))}</p><p>{esc(content.get('enunciado'))}</p>
<ol class="options">{opts(options)}</ol><h3>Alternativas reextraídas</h3><ol class="options">{opts(extracted)}</ol>
<h3>Texto bruto reextraído</h3><p>{esc(extraction.get('raw_text'))}</p></section></div></article>""")
                count+=1
        finally:
            for doc in documents.values():
                doc.close()
        webpage="""<!doctype html><html lang="pt-BR"><meta charset="utf-8"><title>Revisão ENEM</title>
<style>body{font:15px system-ui,sans-serif;max-width:1500px;margin:auto;padding:20px;background:#fafafa;color:#222}
article{background:white;border:1px solid #ddd;padding:20px;margin:24px 0;break-inside:avoid}
.cols{display:grid;grid-template-columns:1fr 1fr;gap:20px}img{width:100%;height:auto}
section{min-width:0;overflow-wrap:anywhere}.options{list-style:none;padding:0}.options li{padding:6px}
@media(max-width:850px){.cols{grid-template-columns:1fr}}</style>
<h1>Revisão visual — ENEM """+str(year)+" D"+str(day)+"""</h1>
<p>Material para revisão humana. Nenhuma questão foi aprovada ou publicada.</p>"""+"".join(cards)+"</html>"
        (folder/"index.html").write_text(webpage,encoding="utf-8")
    print(json.dumps({"selected":len(chosen),"rendered":count,"booklets":len(grouped),
                      "directory":str(out),"approved":0},ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
