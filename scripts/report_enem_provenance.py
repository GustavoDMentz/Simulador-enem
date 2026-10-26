#!/usr/bin/env python3
"""Read-only provenance inventory for ENEM fused questions.

Combines the existing official-answer audit with fused records. Does not assert
TRI correctness from answer-key agreement. No database access or writes.
"""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--audit", type=Path, default=Path("/tmp/enem-official-answer-audit.json"))
    ap.add_argument("--output", type=Path, default=Path("/tmp/enem-provenance-report.json"))
    args = ap.parse_args()
    audit = json.loads(args.audit.read_text(encoding="utf-8"))
    if not audit.get("read_only") or audit.get("total") != len(audit.get("results", [])):
        raise ValueError("Auditoria de entrada incompleta ou sem garantia read_only")
    pdfs = {(p["year"], p["day"]): p for p in audit["pdfs"]}
    records = []
    per_proof = defaultdict(Counter)
    item_occurrences = defaultdict(list)
    for entry in audit["results"]:
        status = entry["status"]
        if status not in ("CONFORME", "DIVERGENTE", "INCONCLUSIVA"):
            raise ValueError(f"Status inesperado: {status}")
        # PDF extraction is not automatically trusted. 90 expected positions,
        # with 1-5 bilingual on day 1. Flag any incomplete extraction.
        pdf = pdfs.get((entry["year"], entry["day"]))
        extraction_complete = bool(pdf and pdf["parsed_positions"] == 90
                                   and not pdf["ambiguous_positions"])
        source = Path(entry["source"])
        lines = source.read_text(encoding="utf-8").splitlines()
        q = json.loads(lines[entry["line"] - 1])
        if q.get("id_unico_sistema") != entry["id"]:
            raise ValueError(f"Fonte mudou desde a auditoria: {entry['id']}")
        item = q.get("co_item")
        key = (entry["year"], entry["day"], entry["color"])
        item_occurrences[(entry["year"], item)].append(entry["id"])
        answer_state = (
            "PENDENTE_VALIDACAO_PDF" if status != "INCONCLUSIVA" and not extraction_complete
            else "VALIDADO_OFICIAL" if status == "CONFORME"
            else "DIVERGENTE" if status == "DIVERGENTE"
            else "INCONCLUSIVO"
        )
        record = {
            "id": entry["id"], "ano": entry["year"], "dia": entry["day"],
            "cor": entry["color"], "posicao": entry["position"],
            "co_item": item, "gabarito_fused": entry["db_answer"],
            "gabarito_pdf": entry.get("official_answer"),
            "gabaritos_idiomas": entry.get("official_answers"),
            "gabarito_status": answer_state,
            "motivo": entry.get("reason"),
            "pdf_extracao_completa": extraction_complete,
            "tri_status": "TRI_NAO_VERIFICADO",
            "tri_valores_presentes": bool(q.get("parametros_tri")),
            "fonte": entry["source"], "linha": entry["line"],
        }
        records.append(record)
        per_proof[key][answer_state] += 1
    duplicates = [
        {"ano": year, "co_item": item, "ids": ids}
        for (year, item), ids in item_occurrences.items()
        if item is not None and len(ids) > 1
    ]
    summary = Counter(r["gabarito_status"] for r in records)
    result = {
        "schema_version": 1, "read_only": True,
        "caveat": "PDF extraction must be independently validated; answer agreement does not validate CO_ITEM or TRI.",
        "total": len(records), "summary": dict(summary),
        "tri_unverified": len(records),
        "repeated_items_same_year": duplicates,
        "per_proof": [
            {"ano": y, "dia": d, "cor": c, "status": dict(v)}
            for (y,d,c),v in sorted(per_proof.items())
        ],
        "records": records,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "total": len(records), "summary": dict(summary),
        "tri_unverified": len(records),
        "repeated_items_same_year": len(duplicates),
        "report": str(args.output),
    }, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
