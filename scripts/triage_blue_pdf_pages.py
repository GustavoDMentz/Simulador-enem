#!/usr/bin/env python3
"""Read-only triage for missing/ambiguous ENEM PDF headings.

Uses nearby *confirmed unique* heading positions as page-range anchors.
Ranges are candidates only and never establish actual question boundaries.
"""
import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", type=Path, default=Path("/tmp/enem-blue-page-candidates.json"))
    p.add_argument("--output", type=Path, default=Path("/tmp/enem-blue-page-triage.json"))
    args = p.parse_args()
    data = json.loads(args.input.read_text(encoding="utf-8"))
    by_pdf = defaultdict(list)
    for q in data["questions"]:
        if q["prova_pdf"]:
            by_pdf[q["prova_pdf"]].append(q)
    triage = []
    for pdf, rows in sorted(by_pdf.items()):
        anchors = sorted((q["posicao"], q["heading_pages"][0])
                         for q in rows if q["status"] == "CABECALHO_UNICO")
        maxpage = data["pdf_pages"][pdf]
        for q in rows:
            if q["status"] == "CABECALHO_UNICO":
                continue
            pos = q["posicao"]
            prev = [(n, pg) for n, pg in anchors if n < pos]
            nxt = [(n, pg) for n, pg in anchors if n > pos]
            lo = prev[-1][1] if prev else 1
            hi = nxt[0][1] if nxt else maxpage
            # Neighbor-based interval is invalid when PDF reading order contradicts
            # numbering. Never silently swap boundaries.
            valid = lo <= hi
            triage.append({
                "ano": q["ano"], "dia": q["dia"], "posicao": pos,
                "status_original": q["status"], "prova_pdf": pdf,
                "heading_pages": q["heading_pages"],
                "previous_anchor": list(prev[-1]) if prev else None,
                "next_anchor": list(nxt[0]) if nxt else None,
                "candidate_page_range": [lo, hi] if valid else None,
                "requires_manual_review": True,
                "reason": "ANCHOR_ORDER_CONFLICT" if not valid else
                          "NO_ANCHORS" if not prev and not nxt else
                          "BOUNDARY_ANCHOR_MISSING" if not prev or not nxt else
                          "NEIGHBOR_BOUNDED",
            })
    for q in data["questions"]:
        if q["status"] == "FONTE_OFICIAL_INCOMPLETA":
            triage.append({"ano": q["ano"], "dia": q["dia"], "posicao": q["posicao"],
                           "status_original": q["status"], "prova_pdf": "",
                           "candidate_page_range": None, "requires_manual_review": True,
                           "reason": "OFFICIAL_PDF_MISSING"})
    triage.sort(key=lambda q: (q["ano"], q["dia"], q["posicao"]))
    output = {"read_only": True,
              "warning": "Ranges are unverified candidates; column order, page continuation and content require visual inspection.",
              "total": len(triage), "summary": dict(Counter(x["reason"] for x in triage)),
              "questions": triage}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Revisao necessaria: {len(triage)}")
    print("Motivos:", output["summary"])
    print(f"Relatorio: {args.output}")

if __name__ == "__main__":
    main()
