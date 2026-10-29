#!/usr/bin/env python3
"""Fail closed if 2024 regular blue D2 fused answers differ from Inep's official key."""
import json
from pathlib import Path

# INEP regular 2024 D2 CD7: https://download.inep.gov.br/enem/provas_e_gabaritos/2024_GB_impresso_D2_CD7.pdf
OFFICIAL = {
93:"E",97:"D",99:"D",102:"A",105:"D",106:"D",107:"E",108:"B",
109:"B",116:"A",117:"E",120:"B",126:"A",129:"ANULADO",135:"D",
140:"B",143:"D",149:"E",151:"E",156:"B",157:"C",159:"C",
160:"D",162:"A",165:"B",171:"A",179:"C",180:"E"
}
def check(path):
    rows = [json.loads(s) for s in Path(path).read_text(encoding="utf-8").splitlines() if s.strip()]
    index = {x["posicao_prova"]: x for x in rows}
    if any(n not in index for n in OFFICIAL):
        raise ValueError("Missing selected positions in fused file")
    mismatches = [{"position":n,"recorded":index[n].get("gabarito_oficial"),"official_regular":key}
                  for n,key in OFFICIAL.items() if index[n].get("gabarito_oficial") != key]
    return mismatches

if __name__ == "__main__":
    mismatches=check(Path("data/fused/questoes_enem_2024_AZUL_D2.jsonl"))
    print(json.dumps({"exam":"2024 regular blue D2","checked":len(OFFICIAL),
                      "mismatches":len(mismatches),"details":mismatches,
                      "publication_authorized":False},ensure_ascii=False,indent=2))
    if mismatches:
        raise SystemExit("BLOCKED: official regular answer-key mismatch")
