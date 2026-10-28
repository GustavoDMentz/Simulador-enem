#!/usr/bin/env python3
"""Stage TRI parameters from HenriqueLindemann/analise-enem without publishing them.

Upstream: https://github.com/HenriqueLindemann/analise-enem
License: PolyForm Noncommercial 1.0.0.
Required Notice: Copyright (c) 2026 Henrique Lindemann
https://github.com/HenriqueLindemann/analise-enem
"""
import argparse
import csv
import io
import json
import math
import urllib.request
from pathlib import Path

SOURCE = "https://github.com/HenriqueLindemann/analise-enem"
RAW = "https://raw.githubusercontent.com/HenriqueLindemann/analise-enem/{ref}/src/tri_enem/data/itens/{year}/ITENS_PROVA_{year}.csv"
AREAS = {"LC", "CH", "CN", "MT"}


def stage(text, year):
    """Return (distinct item parameters, issues); never assert independent verification."""
    rows = csv.DictReader(io.StringIO(text.lstrip("\ufeff")), delimiter=";")
    required = {"CO_ITEM", "SG_AREA", "TX_GABARITO", "NU_PARAM_A", "NU_PARAM_B", "NU_PARAM_C", "IN_ITEM_ABAN"}
    if not required.issubset(rows.fieldnames or ()):
        raise ValueError("Missing required INEP item columns")
    found, issues = {}, []
    for line, r in enumerate(rows, 2):
        try:
            area = r["SG_AREA"].strip()
            answer = r["TX_GABARITO"].strip().upper()
            if area not in AREAS or answer not in "ABCDE" or len(answer) != 1:
                raise ValueError("invalid area or answer")
            if r["IN_ITEM_ABAN"].strip() != "0":
                issues.append({"line": line, "reason": "abandoned or annulled item"})
                continue
            a, b, c = (float(r[k]) for k in ("NU_PARAM_A", "NU_PARAM_B", "NU_PARAM_C"))
            if not all(map(math.isfinite, (a, b, c))) or a <= 0 or not 0 <= c <= 1:
                raise ValueError("invalid TRI parameters")
            co_item = int(r["CO_ITEM"])
            if co_item <= 0:
                raise ValueError("invalid item identifier")
            item = {"ano": year, "co_item": co_item, "area_conhecimento": area,
                    "gabarito_oficial": answer, "a": a, "b": b, "c": c,
                    "fonte": f"{SOURCE}/blob/master/src/tri_enem/data/itens/{year}/ITENS_PROVA_{year}.csv",
                    "status": "EXTERNAL_UNVERIFIED"}
            key = (year, co_item)
            if key in found and found[key] != item:
                issues.append({"line": line, "reason": "conflicting repeated CO_ITEM", "co_item": co_item})
                found[key] = None
            elif key not in found:
                found[key] = item
        except (ValueError, TypeError, KeyError) as exc:
            issues.append({"line": line, "reason": str(exc)})
    return [x for x in found.values() if x is not None], issues


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--years", nargs="+", type=int, default=[2024, 2025])
    p.add_argument("--ref", default="master", help="upstream branch or pinned commit")
    p.add_argument("--input-dir", type=Path, help="read local ITENS_PROVA_YEAR.csv files instead of network")
    p.add_argument("--output-dir", type=Path, default=Path("data/tri/external-staging"))
    args = p.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    report = {"source": SOURCE, "ref": args.ref, "years": {}}
    for year in args.years:
        if not 2009 <= year <= 2025:
            p.error("year must be between 2009 and 2025")
        if args.input_dir:
            raw = (args.input_dir / f"ITENS_PROVA_{year}.csv").read_text(encoding="utf-8-sig")
        else:
            with urllib.request.urlopen(RAW.format(ref=args.ref, year=year), timeout=30) as response:
                raw = response.read().decode("utf-8-sig")
        items, issues = stage(raw, year)
        out = args.output_dir / f"tri-external-{year}.jsonl"
        out.write_text("".join(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n" for item in sorted(items, key=lambda i: i["co_item"])), encoding="utf-8")
        report["years"][str(year)] = {"unique_items": len(items), "issues": issues, "output": str(out)}
    (args.output_dir / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({y: {"unique_items": d["unique_items"], "issues": len(d["issues"])} for y, d in report["years"].items()}))


if __name__ == "__main__":
    main()
