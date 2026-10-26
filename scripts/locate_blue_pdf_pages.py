#!/usr/bin/env python3
"""Read-only candidate PDF page locator for missing blue ENEM questions.

Finds printed QUESTÃO headings in per-page pdftotext output. These are
candidates, not validated question boundaries or extracted content.
"""
import argparse
import csv
import json
import re
import subprocess
from collections import defaultdict
from pathlib import Path

HEADING = re.compile(r"(?im)^\s*QUEST[ÃA]O\s*(\d{1,3})\b")

def run(*args):
    return subprocess.run(args, check=True, capture_output=True, text=True).stdout

def pages_for(pdf):
    info = run("pdfinfo", str(pdf))
    m = re.search(r"(?m)^Pages:\s*(\d+)\s*$", info)
    if not m:
        raise ValueError(f"Unable to determine PDF page count: {pdf}")
    return int(m.group(1))

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--queue", type=Path, default=Path("/tmp/enem-blue-recovery-queue.csv"))
    p.add_argument("--output", type=Path, default=Path("/tmp/enem-blue-page-candidates.json"))
    args = p.parse_args()
    with args.queue.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    groups = defaultdict(list)
    for r in rows:
        if r["status"] == "PRONTO_PARA_MAPEAR_PAGINA":
            groups[r["prova_pdf"]].append(r)
    matches = {}
    page_counts = {}
    for path in sorted(groups):
        pdf = Path(path)
        if not pdf.is_file():
            raise FileNotFoundError(pdf)
        count = pages_for(pdf)
        page_counts[path] = count
        found = defaultdict(set)
        for page in range(1, count + 1):
            text = run("pdftotext", "-f", str(page), "-l", str(page), "-layout", str(pdf), "-")
            for match in HEADING.finditer(text):
                found[int(match.group(1))].add(page)
        matches[path] = {k: sorted(v) for k, v in found.items()}
    output = []
    for r in rows:
        year, day, position = int(r["ano"]), int(r["dia"]), int(r["posicao"])
        if r["status"] != "PRONTO_PARA_MAPEAR_PAGINA":
            output.append({"ano":year,"dia":day,"posicao":position,
                           "status":"FONTE_OFICIAL_INCOMPLETA","heading_pages":[],
                           "candidate_pages":[],"prova_pdf":r["prova_pdf"]})
            continue
        path = r["prova_pdf"]
        headings = matches[path].get(position, [])
        # Adjacent page is included for visual continuity review only.
        candidates = sorted({p for h in headings for p in (h, h+1) if p <= page_counts[path]})
        status = "CABECALHO_UNICO" if len(headings) == 1 else "CABECALHO_AUSENTE" if not headings else "CABECALHO_MULTIPLO"
        output.append({"ano":year,"dia":day,"posicao":position,
                       "status":status,"heading_pages":headings,
                       "candidate_pages":candidates,"prova_pdf":path})
    result = {"read_only":True,
              "warning":"Candidate pages only. Verify columns, continuations, diagrams, options and credits visually.",
              "total":len(output),"pdf_pages":page_counts,"questions":output}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    from collections import Counter
    print(f"Posicoes analisadas: {len(output)}")
    print("Status:",dict(Counter(x["status"] for x in output)))
    print(f"Relatorio: {args.output}")
    print("Nenhum PDF, JSONL ou banco de dados foi modificado.")

if __name__ == "__main__":
    main()
