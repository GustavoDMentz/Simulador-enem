#!/usr/bin/env python3
"""Export batch review dossiers from existing read-only ENEM audit evidence."""
import argparse
from collections import Counter, defaultdict
import csv
import json
from pathlib import Path

def load(path):
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]

def key(row):
    return (int(row["ano"]), int(row["dia"]), int(row["posicao"]))

def export(folder, out, priority="P0_DIVERGENCE"):
    files = {"matrix": "audit-matrix.jsonl", "text": "official-validation.jsonl",
             "answer": "official-answer-evidence.jsonl", "staging": "blue-candidates.jsonl"}
    indexed = {}
    for name, filename in files.items():
        records = load(folder / filename)
        if len({key(x) for x in records}) != len(records):
            raise ValueError(f"Duplicate keys in {filename}; refusing ambiguous batch")
        indexed[name] = {key(x): x for x in records}
    if any(set(indexed["matrix"]) != set(indexed[name]) for name in ("text", "answer", "staging")):
        raise ValueError("Audit evidence positions do not agree")
    out.mkdir(parents=True, exist_ok=True)
    groups = defaultdict(list)
    for k, row in sorted(indexed["matrix"].items()):
        if priority != "ALL" and row["priority"] != priority:
            continue
        t, a, s = (indexed[n][k] for n in ("text", "answer", "staging"))
        checks = []
        for field in t.get("text_evidence", []):
            if field.get("status") in ("NOT_EXACT", "EMPTY_FIELD"):
                checks.append(field)
        records = s.get("existing_records") or []
        item = {
            "ano": k[0], "dia": k[1], "posicao": k[2],
            "priority": row["priority"], "problems": row["problems"],
            "staging_status": s.get("status"),
            "text_status": t.get("status"), "text_reason": t.get("reason"),
            "source_regions": t.get("source_regions", []),
            "region_warnings": t.get("region_warnings", []),
            "pdf_sha256": t.get("source_pdf_sha256"),
            "text_field_findings": checks,
            "answer_status": a.get("status"), "answer_reason": a.get("reason"),
            "official_answer": a.get("official_answer"),
            "recorded_answer": a.get("recorded_answer"),
            "answer_pdf_sha256": a.get("official_answer_pdf_sha256"),
            "existing_record_count": len(records),
            "record_ids": [r.get("record", {}).get("id_unico_sistema") for r in records],
            "classification": "REVIEW_REQUIRED",
            "publishable": False,
        }
        groups[(k[0], k[1])].append(item)
    summary = []
    for (year, day), items in sorted(groups.items()):
        name = f"batch-{year}-d{day}.jsonl"
        with (out / name).open("w", encoding="utf-8") as f:
            for item in items:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
        counts = Counter(i["answer_status"] for i in items)
        summary.append({"ano": year, "dia": day, "count": len(items),
                        "answer_divergences": counts["ANSWER_DIVERGENCE"],
                        "text_suspicions": sum(i["text_status"] == "SUSPECTED_TEXT_DIVERGENCE" for i in items),
                        "file": name})
    with (out / "batch-index.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["ano", "dia", "count", "answer_divergences", "text_suspicions", "file"])
        w.writeheader()
        w.writerows(summary)
    result = {"priority": priority, "total": sum(x["count"] for x in summary),
              "batches": summary, "publication_blocked": True,
              "note": "Machine evidence only; PDF visual fidelity and official provenance not certified."}
    (out / "batch-summary.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input-dir", type=Path, default=Path("data/blue-staging"))
    p.add_argument("--output-dir", type=Path, default=Path("data/blue-staging/review-batches"))
    p.add_argument("--priority", choices=("P0_DIVERGENCE", "ALL"), default="P0_DIVERGENCE")
    args = p.parse_args()
    if args.input_dir.resolve() == args.output_dir.resolve():
        p.error("Output must not overwrite input evidence")
    print(json.dumps(export(args.input_dir, args.output_dir, args.priority), ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
