#!/usr/bin/env python3
"""Create an actionable, non-publishing review queue from refreshed blue staging.

Read-only with respect to fused data and databases. This is a review queue,
NOT an automatic fidelity certificate or publication authorization.
"""
import argparse
import csv
import json
from collections import Counter
from pathlib import Path

def load(path):
    with path.open(encoding="utf-8") as stream:
        return {(r["ano"], r["dia"], r["posicao"]): r
                for line in stream if (r := json.loads(line))}

def build(staging, texts, answers):
    if not (set(staging) == set(texts) == set(answers)):
        raise ValueError("Evidence sets do not cover identical positions")
    for key in sorted(staging):
        s, t, a = staging[key], texts[key], answers[key]
        extraction = s.get("extraction") or {}
        segment = extraction.get("option_segmentation") or {}
        status = t.get("refresh_candidate_status") or t.get("status")
        existing = s.get("existing_records") or []
        if status in ("CANDIDATE_OPTIONS_TEXT_MATCH_ONLY", "TEXT_MATCH_VISUAL_UNVERIFIED"):
            priority = "01_REVIEW_CONTENT_VISUAL_ANSWER"
        elif status in ("CANDIDATE_OPTIONS_INCOMPLETE", "CANDIDATE_OPTIONS_NEED_RECOVERY"):
            priority = "02_RECOVER_OPTIONS"
        elif t.get("status") == "SOURCE_MISSING":
            priority = "04_MISSING_SOURCE"
        else:
            priority = "03_INVESTIGATE"
        blockers = []
        if a.get("status") != "ANSWER_TEXT_MATCH_UNVERIFIED":
            blockers.append("ANSWER_" + str(a.get("status", "UNKNOWN")))
        if t.get("region_warnings"):
            blockers.append("REGION_CONTINUATION")
        if segment.get("status") != "GEOMETRIC_HYPOTHESIS_UNVERIFIED":
            blockers.append("OPTION_SEGMENTATION")
        blockers.extend(("VISUAL_REVIEW", "STEM_SUPPORT_CREDITS_REVIEW"))
        yield {
            "ano": key[0], "dia": key[1], "posicao": key[2],
            "priority": priority, "existing": bool(existing),
            "text_status": t.get("status"), "refresh_status": status,
            "answer_status": a.get("status"),
            "pdf_page": extraction.get("pdf_page"),
            "official_pdf": s.get("official_pdf"),
            "source_pdf_sha256": t.get("source_pdf_sha256"),
            "record_id": existing[0]["record"].get("id_unico_sistema") if len(existing) == 1 else None,
            "candidate_options": segment.get("options") or {},
            "candidate_raw_text": extraction.get("raw_text"),
            "blockers": blockers,
            "approved": False, "publishable": False
        }

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output-dir", type=Path, default=Path("data/blue-staging"))
    args = p.parse_args()
    root = args.output_dir
    rows = list(build(load(root/"blue-candidates.jsonl"),
                      load(root/"official-validation.jsonl"),
                      load(root/"official-answer-evidence.jsonl")))
    out = root/"release-review"
    out.mkdir(parents=True, exist_ok=True)
    with (out/"review-queue.jsonl").open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False)+"\n")
    fields = ["ano","dia","posicao","priority","existing","text_status",
              "refresh_status","answer_status","pdf_page","official_pdf",
              "record_id","blockers"]
    with (out/"review-queue.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for row in rows:
            w.writerow({k: "|".join(row[k]) if k == "blockers" else row[k] for k in fields})
    print(json.dumps({"total":len(rows),"priorities":dict(Counter(r["priority"] for r in rows)),
                      "queue":str(out/"review-queue.csv"),"published":0},ensure_ascii=False,indent=2))

if __name__ == "__main__":
    main()
