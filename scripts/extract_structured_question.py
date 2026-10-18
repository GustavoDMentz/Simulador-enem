#!/usr/bin/env python3
"""Extrai blocos estruturados de regiões explicitamente delimitadas de um PDF.

Etapa conservadora: geometria declarada por especificação; nenhuma aprovação
ou identificação automática de alternativas é presumida.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pymupdf

LETTERS = "ABCDE"


def _block(page, definition: dict, assets: Path, name: str, dpi: int) -> dict:
    kind = definition.get("type")
    if kind not in {"text", "image"}:
        raise ValueError(f"Tipo de bloco inválido: {kind}")
    if "bbox" not in definition or len(definition["bbox"]) != 4:
        raise ValueError(f"BBox obrigatório: {name}")
    rect = pymupdf.Rect(definition["bbox"])
    if rect.is_empty or not page.rect.contains(rect):
        raise ValueError(f"BBox fora da página: {name}")
    if kind == "text":
        value = page.get_text("text", clip=rect, sort=True).strip()
        if not value:
            raise ValueError(f"Região textual vazia: {name}")
        return {"type": "text", "value": value, "source_bbox": list(rect)}
    path = assets / f"{name}.png"
    page.get_pixmap(clip=rect, dpi=dpi, alpha=False).save(str(path))
    return {"type": "image", "value": path.name,
            "source_bbox": list(rect),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def extract(pdf_path: Path, spec: dict, output: Path, dpi: int = 160) -> dict:
    if not pdf_path.is_file():
        raise ValueError("PDF deve ser um arquivo")
    if not 72 <= dpi <= 300:
        raise ValueError("DPI inválido")
    digest = hashlib.sha256(pdf_path.read_bytes()).hexdigest()
    if digest != spec.get("source_sha256"):
        raise ValueError("SHA-256 do PDF não corresponde à especificação")
    if not isinstance(spec.get("id"), str) or not spec["id"]:
        raise ValueError("ID obrigatório")
    options = spec.get("alternatives")
    if not isinstance(options, list) or [o.get("label") for o in options] != list(LETTERS):
        raise ValueError("São necessárias cinco alternativas A–E ordenadas")
    if not isinstance(spec.get("blocks"), list) or not spec["blocks"]:
        raise ValueError("Enunciado obrigatório")
    for o in options:
        if not isinstance(o.get("blocks"), list) or not o["blocks"]:
            raise ValueError(f"Alternativa vazia: {o['label']}")
    assets = output.parent / (output.stem + "_assets")
    # Valida as regiões antes de criar arquivos.
    with pymupdf.open(pdf_path) as doc:
        page_number = spec.get("page")
        if not isinstance(page_number, int) or not 1 <= page_number <= len(doc):
            raise ValueError("Página inválida")
        page = doc[page_number - 1]
        for b in spec["blocks"] + [b for o in options for b in o["blocks"]]:
            if b.get("type") not in {"text", "image"} or not isinstance(b.get("bbox"), list) or len(b["bbox"]) != 4:
                raise ValueError("Definição de bloco inválida")
            rect = pymupdf.Rect(b["bbox"])
            if rect.is_empty or not page.rect.contains(rect):
                raise ValueError("Região fora da página")
        assets.mkdir(parents=True, exist_ok=True)
        blocks = [_block(page, b, assets, f"stem_{i:03d}", dpi)
                  for i, b in enumerate(spec["blocks"])]
        rendered_options = []
        for option in options:
            letter = option["label"]
            rendered_options.append({
                "label": letter,
                "blocks": [_block(page, b, assets, f"option_{letter}_{i:03d}", dpi)
                           for i, b in enumerate(option["blocks"])],
            })
    # Referências relativas ao HTML produzido no mesmo diretório do JSON.
    for block in blocks + [b for o in rendered_options for b in o["blocks"]]:
        if block["type"] == "image":
            block["value"] = f"{assets.name}/{block['value']}"
    result = {
        "id": spec["id"], "blocks": blocks, "alternatives": rendered_options,
        "source_pdf_sha256": digest, "source_page": page_number,
        "review_status": "pending", "publication_authorized": False,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                      encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", required=True, type=Path)
    parser.add_argument("--spec", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--dpi", type=int, default=160)
    args = parser.parse_args()
    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    result = extract(args.pdf, spec, args.output, args.dpi)
    print(json.dumps({"id": result["id"], "blocks": len(result["blocks"]),
                      "alternatives": len(result["alternatives"]),
                      "publication_authorized": False}, ensure_ascii=False))


if __name__ == "__main__":
    main()
