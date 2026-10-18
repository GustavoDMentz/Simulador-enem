#!/usr/bin/env python3
"""Read-only audit of ENEM fused JSONL against official blue-booklet answer PDFs.

Requires pdftotext (poppler-utils). Never modifies sources or databases.
"""
import argparse
import collections
import json
import re
import subprocess
from pathlib import Path

PDF_RE = re.compile(r"^(20\d{2})-regular-d([12])-azul-gabarito\.pdf$", re.I)
ROW_RE = re.compile(r"^\s*(\d{1,3})\s+([A-E*X-])(?:\s+([A-E*X-]))?(?:\s+(\d{1,3})\s+([A-E*X-]))?\s*$")
LANG = {"INGLES": "ingles", "ESPANHOL": "espanhol", "INGLÊS": "ingles"}
def extract_pdf(pdf):
    result = subprocess.run(["pdftotext", "-layout", str(pdf), "-"], capture_output=True, text=True, check=True)
    answers, ambiguous = {}, []
    for line in result.stdout.splitlines():
        m = ROW_RE.fullmatch(line)
        if not m:
            continue
        pos, first, second, pos2, last = m.groups()
        pos = int(pos)
        # Only numbered ENEM questions; ignore tables, legends and PDF debris.
        if not 1 <= pos <= 180:
            continue
        if pos in answers:
            ambiguous.append(pos)
        if pos <= 5 and second and second in "ABCDE":
            answers[pos] = {"ingles": first, "espanhol": second}
        elif pos <= 5:
            # Two languages are required: never assume the single extracted letter.
            ambiguous.append(pos)
        else:
            answers[pos] = {"comum": first}
        if pos2:
            p2 = int(pos2)
            if not 1 <= p2 <= 180:
                continue
            if p2 in answers:
                ambiguous.append(p2)
            answers[p2] = {"comum": last}
    return answers, sorted(set(ambiguous)), len(result.stdout)

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--fused", type=Path, default=Path("data/fused"))
    p.add_argument("--pdf-dir", type=Path, default=Path("data/enem-pdfs/oficiais"))
    p.add_argument("--output", type=Path, default=Path("/tmp/enem-official-answer-audit.json"))
    args = p.parse_args()
    sources = sorted(args.fused.glob("*.jsonl"))
    records = []
    for f in sources:
        for n, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            if line.strip():
                q = json.loads(line)
                records.append((q, str(f), n))
    pdfs = {}
    for pdf in sorted(args.pdf_dir.glob("*-gabarito.pdf")):
        m = PDF_RE.fullmatch(pdf.name)
        if m:
            pdfs[(int(m.group(1)), int(m.group(2)))] = pdf
    parsed = {key: extract_pdf(pdf) for key, pdf in pdfs.items()}
    outcomes = []
    for q, source, line in records:
        year, day = q["ano"], q["dia"]
        position = q["posicao_prova"]
        result = {"id": q["id_unico_sistema"], "year": year, "day": day,
                  "color": q["cor_prova"], "position": position,
                  "db_answer": q["gabarito_oficial"], "source": source, "line": line}
        if q["cor_prova"].upper() != "AZUL":
            result.update(status="INCONCLUSIVA", reason="caderno_nao_azul_sem_mapeamento_validado")
        elif (year, day) not in parsed:
            result.update(status="INCONCLUSIVA", reason="pdf_oficial_ausente")
        else:
            answers, ambiguous, _ = parsed[(year, day)]
            expected = answers.get(position)
            if position in ambiguous or expected is None:
                result.update(status="INCONCLUSIVA", reason="linha_pdf_ausente_ou_ambigua")
            elif position <= 5 and day == 1:
                # Do not infer language from question wording.
                result.update(status="INCONCLUSIVA", reason="idioma_nao_identificado",
                              official_answers=expected)
            elif "comum" not in expected or expected["comum"] not in "ABCDE":
                result.update(status="INCONCLUSIVA", reason="gabarito_nao_canonico",
                              official_answers=expected)
            else:
                official = expected["comum"]
                result.update(status="CONFORME" if official == q["gabarito_oficial"] else "DIVERGENTE",
                              official_answer=official)
        outcomes.append(result)
    summary = dict(collections.Counter(x["status"] for x in outcomes))
    pdf_status = [{"year": y, "day": d, "file": str(pdfs[(y,d)]),
                   "parsed_positions": len(parsed[(y,d)][0]),
                   "ambiguous_positions": parsed[(y,d)][1],
                   "extracted_chars": parsed[(y,d)][2]}
                  for y,d in sorted(pdfs)]
    output = {"read_only": True, "total": len(outcomes), "summary": summary,
              "pdfs": pdf_status, "results": outcomes}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"total": len(outcomes), "summary": summary,
                      "pdfs": len(pdfs), "report": str(args.output)}, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
