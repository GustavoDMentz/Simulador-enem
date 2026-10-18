#!/usr/bin/env python3
"""Cria inventário 2017–2025 a partir de PDFs locais, sem adivinhar metadados.

Nomes aceitos: 2024_PV_impresso_D1_CD1.pdf ou 2024-regular-d1-azul.pdf.
Arquivos ambíguos são relatados, nunca atribuídos silenciosamente.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

COLORS = {"1": "azul", "2": "amarelo", "3": "branco", "4": "rosa"}
STANDARD = re.compile(
    r"^(20(?:1[7-9]|2[0-5]))[-_]regular[-_]d([12])[-_](azul|amarelo|branco|rosa)\.pdf$",
    re.IGNORECASE,
)
INEP = re.compile(
    r"^(20(?:1[7-9]|2[0-5]))_PV_impresso_D([12])_CD([1-4])\.pdf$",
    re.IGNORECASE,
)


def classify(path: Path):
    name = path.name
    match = STANDARD.fullmatch(name)
    if match:
        year, day, color = match.groups()
        return int(year), int(day), color.lower()
    match = INEP.fullmatch(name)
    if match:
        year, day, code = match.groups()
        # CD1 etc. are booklet codes, not a guaranteed color mapping.
        return None
    return None


def generate(pdf_dir: Path, manifest: Path, *, include_existing: bool = True) -> dict:
    existing = {}
    if include_existing and manifest.exists():
        for entry in json.loads(manifest.read_text(encoding="utf-8")).get("exams", []):
            key = (int(entry["year"]), int(entry["day"]))
            if key in existing:
                raise ValueError(f"Duplicidade no manifesto: {key}")
            existing[key] = entry
    candidates = {}
    unclassified = []
    for path in sorted(pdf_dir.rglob("*.pdf")):
        key = classify(path)
        if key is None:
            unclassified.append(str(path))
        else:
            candidates.setdefault(key[:2], []).append((key[2], path))
    exams = []
    missing = []
    ambiguous = []
    for year in range(2017, 2026):
        for day in (1, 2):
            key = (year, day)
            if key in existing:
                exams.append(existing[key])
            elif len(candidates.get(key, [])) == 1:
                color, path = candidates[key][0]
                exams.append({
                    "year": year, "day": day, "color": color,
                    "application": "regular",
                    "pdf": str(path.resolve()),
                })
            elif candidates.get(key):
                ambiguous.append({"year": year, "day": day,
                                  "files": [str(p) for _, p in candidates[key]]})
            else:
                missing.append({"year": year, "day": day})
    result = {"schema_version": 1, "exams": exams,
              "missing": missing, "ambiguous": ambiguous,
              "unclassified_pdfs": unclassified}
    manifest.parent.mkdir(parents=True, exist_ok=True)
    # Batch runner reads only exams; keep diagnostics alongside.
    manifest.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf-dir", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--replace", action="store_true",
                        help="Ignorar entradas previamente cadastradas")
    args = parser.parse_args()
    result = generate(args.pdf_dir, args.manifest,
                      include_existing=not args.replace)
    print(json.dumps({"registered": len(result["exams"]),
                      "missing": len(result["missing"]),
                      "ambiguous": len(result["ambiguous"]),
                      "unclassified": len(result["unclassified_pdfs"])},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
