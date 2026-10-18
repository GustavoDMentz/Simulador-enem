#!/usr/bin/env python3
"""Cria fila de revisão de questões a partir dos recortes candidatos.

Não identifica automaticamente o gabarito nem aprova questões.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
from collections import Counter
from pathlib import Path

import fitz


def build_review(pdf: Path, candidates_json: Path, output: Path, *,
                 year: int, day: int, color: str, application: str = "regular") -> dict:
    manifest = json.loads(candidates_json.read_text(encoding="utf-8"))
    if manifest.get("source_pdf") != pdf.name:
        raise ValueError("Nome do PDF diverge do manifesto de recortes")
    sha = hashlib.sha256(pdf.read_bytes()).hexdigest()
    output.mkdir(parents=True, exist_ok=True)
    counts = Counter(item["number"] for item in manifest["candidates"])
    records = []
    with fitz.open(pdf) as document:
        for item in manifest["candidates"]:
            page_num = int(item["page"])
            number = int(item["number"])
            if not 1 <= page_num <= len(document):
                raise ValueError(f"Página inválida: {page_num}")
            bbox = fitz.Rect(item["bbox"])
            if bbox.is_empty or not document[page_num - 1].rect.contains(bbox):
                raise ValueError(f"Recorte fora da página: {page_num}")
            raw_text = document[page_num - 1].get_text("text", clip=bbox, sort=True).strip()
            image_path = (candidates_json.parent / item["image"]).resolve()
            if not image_path.is_file():
                raise FileNotFoundError(image_path)
            asset_sha = hashlib.sha256(image_path.read_bytes()).hexdigest()
            uid = f"{year}-{application}-d{day}-{color.lower()}-q{number:03d}-p{page_num:03d}"
            reasons = ["Recorte e conteúdo não conferidos", "Alternativas e gabarito não validados"]
            if counts[number] > 1:
                reasons.append("Número repetido: identificar variante de língua/edição")
            records.append({
                "id": uid, "exam": {"year": year, "application": application, "day": day,
                                    "color": color.lower(), "source_sha256": sha},
                "original_number": number, "page": page_num, "bbox": list(bbox),
                "image": os.path.relpath(image_path, output.resolve()),
                "image_sha256": asset_sha,
                "extracted_text": raw_text,
                "language_variant": None,
                "alternatives": None,
                "correct_option": None,
                "review_status": "pending",
                "review_reasons": reasons,
            })
    ids = [r["id"] for r in records]
    if len(ids) != len(set(ids)):
        raise ValueError("IDs colidiram: há mais de um candidato para mesma questão/página")
    result = {"schema_version": 1, "source_pdf": pdf.name, "source_sha256": sha,
              "records": records, "all_require_review": True}
    (output / "question-review.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    entries = []
    for r in records:
        rel_image = Path(r["image"])
        uri = rel_image.as_posix()
        entries.append(
            '<article><h2>' + html.escape(r["id"]) + '</h2>'
            '<p>Status: PENDENTE — ' + html.escape("; ".join(r["review_reasons"])) + '</p>'
            '<img loading="lazy" src="' + html.escape(uri, quote=True) + '" alt="Recorte da questão">'
            '<details><summary>Texto extraído (não validado)</summary><pre>'
            + html.escape(r["extracted_text"]) + '</pre></details></article>'
        )
    (output / "review.html").write_text(
        '<!doctype html><html lang="pt-BR"><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>Revisão de questões ENEM</title>'
        '<style>body{font:16px system-ui;max-width:1100px;margin:2rem auto;padding:1rem}'
        'article{border:1px solid #ccc;border-radius:10px;padding:1rem;margin:1rem 0}'
        'img{max-width:100%}pre{white-space:pre-wrap;overflow-wrap:anywhere}</style>'
        '<h1>Fila de revisão — nenhuma questão aprovada automaticamente</h1>'
        + "".join(entries) + '</html>', encoding="utf-8"
    )
    return {"candidates": len(records), "duplicate_numbers": sorted(
        n for n, count in counts.items() if count > 1),
        "pending_review": len(records), "output": str(output / "question-review.json")}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", type=Path, required=True)
    parser.add_argument("--candidates", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--day", type=int, choices=[1, 2], required=True)
    parser.add_argument("--color", required=True)
    parser.add_argument("--application", default="regular")
    args = parser.parse_args()
    print(json.dumps(build_review(args.pdf, args.candidates, args.output,
        year=args.year, day=args.day, color=args.color, application=args.application),
        ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
