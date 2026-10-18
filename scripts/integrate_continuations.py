#!/usr/bin/env python3
"""Cria fila enriquecida por continuações, sem alterar question-review.json original."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import pymupdf

from repair_column_continuations import run as repair_run


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def integrate(pdf_path: Path, review_path: Path, output_dir: Path) -> dict:
    original = json.loads(review_path.read_text(encoding="utf-8"))
    if sha256(pdf_path) != original["source_sha256"]:
        raise ValueError("PDF não corresponde ao SHA-256 da fila de revisão")
    if any(r.get("review_status") != "pending" for r in original["records"]):
        raise ValueError("Há decisões humanas: integração bloqueada")
    output_dir.mkdir(parents=True, exist_ok=True)
    repairs = repair_run(pdf_path, review_path, output_dir / "images")
    by_id = {r["id"]: r for r in repairs["results"] if r["status"] == "candidate_for_review"}
    records = []
    with pymupdf.open(pdf_path) as pdf:
        for record in original["records"]:
            item = dict(record)
            correction = by_id.get(item["id"])
            if correction:
                image_path = Path(correction["image"]).resolve()
                page = pdf[item["page"] - 1]
                chunks = [
                    page.get_text("text", clip=pymupdf.Rect(box), sort=True).strip()
                    for box in correction["segments"]
                ]
                item["original_crop"] = {
                    "image": item["image"],
                    "image_sha256": item["image_sha256"],
                    "bbox": item["bbox"],
                    "extracted_text": item["extracted_text"],
                }
                item["image"] = os.path.relpath(image_path, output_dir.resolve())
                item["image_sha256"] = sha256(image_path)
                item["extracted_text"] = "\n\n".join(chunks)
                item["source_segments"] = [
                    {"page": item["page"], "bbox": box}
                    for box in correction["segments"]
                ]
                item["review_reasons"] = list(item["review_reasons"]) + [
                    "Continuação de coluna composta automaticamente; conferir limites e texto"
                ]
            records.append(item)
    enriched = {
        **original, "records": records,
        "continuation_integration": {
            "method": "same-page-left-to-right-v1",
            "repaired_ids": sorted(by_id),
            "count": len(by_id),
            "publication_authorized": False,
        },
        "all_require_review": True,
    }
    dest = output_dir / "question-review-enriched.json"
    tmp = dest.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(enriched, ensure_ascii=False, indent=2) + "\n",
                   encoding="utf-8")
    tmp.replace(dest)
    return {"total": len(records), "repaired": len(by_id),
            "manual_review": sum(r["status"] == "manual_review" for r in repairs["results"]),
            "output": str(dest)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", required=True, type=Path)
    parser.add_argument("--review", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(integrate(args.pdf, args.review, args.output), ensure_ascii=False))


if __name__ == "__main__":
    main()
