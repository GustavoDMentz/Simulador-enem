#!/usr/bin/env python3
"""Build a read-only visual-review manifest for missing blue ENEM questions.

No PDF extraction, no answer inference, no database or fused-data mutation.
"""
import argparse
import csv
import json
from collections import Counter
from pathlib import Path

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--candidates", type=Path, default=Path("/tmp/enem-blue-page-candidates.json"))
    p.add_argument("--triage", type=Path, default=Path("/tmp/enem-blue-page-triage.json"))
    p.add_argument("--output", type=Path, default=Path("/tmp/enem-blue-visual-review.csv"))
    args = p.parse_args()
    source = json.loads(args.candidates.read_text(encoding="utf-8"))
    triage = json.loads(args.triage.read_text(encoding="utf-8"))
    if not source.get("read_only") or not triage.get("read_only"):
        raise ValueError("Input reports must be read-only")
    indexed = {(q["ano"], q["dia"], q["posicao"]): q for q in triage["questions"]}
    rows = []
    for q in source["questions"]:
        key = (q["ano"], q["dia"], q["posicao"])
        t = indexed.get(key)
        if q["status"] == "CABECALHO_UNICO":
            pages = q["candidate_pages"]
            confidence = "HEADING_FOUND_NOT_VALIDATED"
            reason = "CHECK_FULL_QUESTION_AND_CONTINUATION"
        elif q["status"] == "FONTE_OFICIAL_INCOMPLETA":
            pages = []
            confidence = "BLOCKED"
            reason = "OFFICIAL_PDF_MISSING"
        else:
            if t is None:
                raise ValueError(f"Missing triage for {key}")
            interval = t.get("candidate_page_range")
            pages = list(range(interval[0], interval[1] + 1)) if interval else []
            confidence = "NEIGHBOR_RANGE_UNVERIFIED" if interval else "UNRESOLVED"
            reason = t["reason"]
        rows.append({
            "ano": q["ano"], "dia": q["dia"], "posicao": q["posicao"],
            "prova_pdf": q["prova_pdf"],
            "pagina_inicio_candidata": min(pages) if pages else "",
            "pagina_fim_candidata": max(pages) if pages else "",
            "paginas_candidatas": ",".join(map(str, pages)),
            "localizacao_status": confidence,
            "motivo": reason,
            "revisao_visual": "PENDENTE",
            "texto_alternativas_creditos": "NAO_AUDITADOS",
            "imagens_formulas": "NAO_AUDITADOS",
            "gabarito": "NAO_VALIDADO",
            "tri": "NAO_VERIFICADO",
        })
    if len(rows) != 483 or len(set((r["ano"],r["dia"],r["posicao"]) for r in rows)) != len(rows):
        raise ValueError("Unexpected coverage or duplicate keys")
    rows.sort(key=lambda r:(r["ano"],r["dia"],r["posicao"]))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Linhas para revisao: {len(rows)}")
    print("Localizacao:", dict(Counter(r["localizacao_status"] for r in rows)))
    print(f"Manifesto: {args.output}")
    print("Somente o manifesto foi criado; nenhuma questao foi validada automaticamente.")

if __name__ == "__main__":
    main()
