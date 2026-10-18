#!/usr/bin/env python3
"""Export missing blue-booklet positions from the read-only coverage manifest."""
import argparse
import csv
import json
from pathlib import Path

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--coverage", type=Path, default=Path("/tmp/enem-blue-coverage.json"))
    p.add_argument("--output", type=Path, default=Path("/tmp/enem-blue-missing.csv"))
    args = p.parse_args()
    data = json.loads(args.coverage.read_text(encoding="utf-8"))
    if not data.get("read_only") or len(data.get("positions", [])) != 1620:
        raise ValueError("Manifesto de cobertura incompleto")
    missing = [q for q in data["positions"] if q["status"] == "AUSENTE"]
    if len(data.get("invalid_records", [])):
        raise ValueError("Existem registros invalidos; revise antes de exportar")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["ano", "dia", "posicao", "idioma_requer_verificacao"])
        for q in missing:
            w.writerow([q["ano"], q["dia"], q["posicao"],
                        "SIM" if q["dia"] == 1 and q["posicao"] <= 5 else "NAO"])
    print(f"Lacunas exportadas: {len(missing)}")
    print(f"Arquivo: {args.output}")
    print("Nenhum JSONL, PDF ou banco de dados foi modificado.")

if __name__ == "__main__":
    main()
