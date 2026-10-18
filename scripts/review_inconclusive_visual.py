#!/usr/bin/env python3
"""Gera painel visual dos inconclusivos, sem alterar filas ou aprovar questões."""
from __future__ import annotations

import argparse
import html
import json
from collections import Counter
from pathlib import Path


def build(report: Path, batch: Path, output: Path) -> dict:
    data = json.loads(report.read_text(encoding="utf-8"))
    selected = [r for r in data["records"] if r.get("evidence_class") == "inconclusive"]
    cards = []
    counts = Counter()
    for row in selected:
        exam, rid = row["exam"], row["id"]
        counts[exam[:4]] += 1
        queue = batch / exam / "enriched" / "question-review-enriched.json"
        if not queue.is_file():
            raise FileNotFoundError(queue)
        payload = json.loads(queue.read_text(encoding="utf-8"))
        match = next((r for r in payload["records"] if r["id"] == rid), None)
        if match is None:
            raise ValueError(f"ID ausente na fila: {rid}")
        repaired = rid in payload.get("continuation_integration", {}).get("repaired_ids", [])
        image_root = queue.parent if repaired else queue.parent.parent / "review"
        image = (image_root / match["image"]).resolve()
        if not image.is_file():
            raise FileNotFoundError(image)
        # Only embed a relative path to a verified local PNG.
        if image.suffix.lower() != ".png":
            raise ValueError(f"Imagem não PNG: {image}")
        relative = image.relative_to(output.parent.resolve()) if image.is_relative_to(output.parent.resolve()) else None
        if relative is None:
            import os
            src = Path(os.path.relpath(image, output.parent.resolve())).as_posix()
        else:
            src = relative.as_posix()
        cards.append(
            '<article><h2>' + html.escape(rid) + '</h2>'
            '<p>Original: ' + html.escape(str(row.get("old_sequence", ""))) +
            ' | Blocos: ' + html.escape(str(row.get("new_sequence", ""))) + '</p>'
            '<img loading="lazy" src="' + html.escape(src, quote=True) +
            '" alt="Recorte original do ENEM">'
            '<details><summary>Texto extraído</summary><pre>' +
            html.escape(str(match.get("extracted_text", ""))[:6000]) +
            '</pre></details></article>'
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    page = (
        '<!doctype html><html lang="pt-BR"><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>ENEM — inconclusivos</title>'
        '<style>body{font:16px system-ui;max-width:1100px;margin:auto;padding:1rem}'
        'article{border:1px solid #aaa;border-radius:8px;padding:1rem;margin:1rem 0}'
        'img{display:block;max-width:100%;height:auto}pre{white-space:pre-wrap;overflow-wrap:anywhere}</style>'
        '<h1>Questões inconclusivas — revisão visual necessária</h1>'
        '<p>O painel não aprova questões nem verifica gabaritos.</p>' +
        "".join(cards) + '</html>'
    )
    output.write_text(page, encoding="utf-8")
    return {"total": len(selected), "by_year": dict(sorted(counts.items())),
            "output": str(output), "publication_authorized": False}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--batch", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.input, args.batch, args.output), ensure_ascii=False))


if __name__ == "__main__":
    main()
