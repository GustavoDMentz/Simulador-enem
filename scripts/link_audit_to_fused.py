#!/usr/bin/env python3
"""Read-only bridge: match a v2/v3 PDF audit report to existing fused JSONL.
No database writes and no automatic publication authorization.
"""
import argparse
import hashlib
import json
from pathlib import Path

def read_jsonl(folder):
    for path in sorted(Path(folder).glob("*.jsonl")):
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if line.strip():
                yield path.name, line_no, json.loads(line)

def match(report, records, pdfs):
    index = {}
    for filename, line_no, item in records:
        key = (item.get("ano"), item.get("dia"), item.get("cor_prova"), item.get("posicao_prova"))
        index.setdefault(key, []).append((filename, line_no, item))
    findings = []
    for exam in report["results"]:
        year = int(exam["year"])
        pdf = Path(pdfs[year])
        digest = hashlib.sha256(pdf.read_bytes()).hexdigest()
        if digest != exam["sha256"]:
            raise ValueError(f"SHA256 mismatch for {year}")
        day = 1 if year == 2024 else 2
        for q in exam["selected_questions"]:
            number = int(q["number"])
            key = (year, day, "AZUL", number)
            candidates = index.get(key, [])
            # Do not guess when language variants, duplicate records or positions differ.
            findings.append({
                "year": year, "day": day, "color": "AZUL", "number": number,
                "source_sha256": digest, "match_count": len(candidates),
                "matches": [{"file": file, "line": line,
                             "id": item.get("id_unico_sistema"),
                             "co_item": item.get("co_item")}
                            for file, line, item in candidates],
                "status": "MATCHED_UNVERIFIED" if len(candidates) == 1 else
                          "AMBIGUOUS" if len(candidates) > 1 else "NOT_FOUND",
                "publication_authorized": False
            })
    return findings

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", type=Path, required=True)
    ap.add_argument("--fused", type=Path, required=True)
    for year in (2018, 2019, 2024):
        ap.add_argument(f"--pdf-{year}", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    pdfs = {year: getattr(args, f"pdf_{year}") for year in (2018, 2019, 2024)}
    result = match(json.loads(args.report.read_text(encoding="utf-8")),
                   read_jsonl(args.fused), pdfs)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({
        "schema_version": 1, "publication_authorized": False,
        "matches": result
    }, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    counts = {state: sum(x["status"] == state for x in result)
              for state in ("MATCHED_UNVERIFIED", "AMBIGUOUS", "NOT_FOUND")}
    print(json.dumps(counts))

if __name__ == "__main__":
    main()
