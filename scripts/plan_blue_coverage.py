#!/usr/bin/env python3
"""Read-only coverage plan for official ENEM blue booklets (2017-2025).

The manifest identifies missing blue positions and potential source material.
Other colors are NEVER automatically assigned to blue positions.
"""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path

YEARS = range(2017, 2026)
DAYS = (1, 2)
def positions_for_day(day):
    return range(1, 91) if day == 1 else range(91, 181)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--provenance", type=Path, default=Path("/tmp/enem-provenance-report.json"))
    parser.add_argument("--output", type=Path, default=Path("/tmp/enem-blue-coverage.json"))
    args = parser.parse_args()
    report = json.loads(args.provenance.read_text(encoding="utf-8"))
    records = report["records"]
    blue = defaultdict(list)
    other = defaultdict(list)
    invalid = []
    for r in records:
        year, day, pos = r["ano"], r["dia"], r["posicao"]
        if year not in YEARS or day not in DAYS or not isinstance(pos, int) or pos not in positions_for_day(day):
            invalid.append(r["id"])
            continue
        if str(r["cor"]).upper() == "AZUL":
            blue[(year, day, pos)].append(r)
        else:
            other[(year, day)].append(r)
    positions = []
    summary = []
    for year in YEARS:
        for day in DAYS:
            counts = Counter()
            for pos in positions_for_day(day):
                matches = blue[(year, day, pos)]
                # Reuse other-color text only after independently proving
                # correspondence with the official blue PDF.
                status = "AUSENTE" if not matches else "UNICO" if len(matches) == 1 else "MULTIPLO"
                counts[status] += 1
                positions.append({
                    "ano": year, "dia": day, "posicao": pos,
                    "status": status,
                    "registros_azuis": [r["id"] for r in matches],
                    "gabarito_status": [r["gabarito_status"] for r in matches],
                    "tri_status": [r["tri_status"] for r in matches],
                    "observacao": "Variantes de idioma exigem conferencia separada" if day == 1 and pos <= 5 else None,
                })
            summary.append({
                "ano": year, "dia": day, "posicoes": 90,
                "unicas": counts["UNICO"], "ausentes": counts["AUSENTE"],
                "multiplas": counts["MULTIPLO"],
                "registros_outras_cores_disponiveis_para_consulta": len(other[(year, day)]),
            })
    result = {
        "read_only": True, "target": "ENEM regular, caderno azul, 2017-2025",
        "expected_positions": 1620,
        "warning": "Cobertura por posicao nao comprova fidelidade textual, gabarito ou TRI. Nao inferir posicoes azuis a partir de outras cores.",
        "invalid_records": invalid, "summary": summary, "positions": positions,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Cobertura azul (sem modificar dados):")
    for row in summary:
        print(f"{row['ano']} D{row['dia']}: unicas={row['unicas']:2} ausentes={row['ausentes']:2} multiplas={row['multiplas']:2}")
    print(f"Total de posicoes: {len(positions)}; registros invalidos: {len(invalid)}")
    print(f"Relatorio: {args.output}")

if __name__ == "__main__":
    main()
