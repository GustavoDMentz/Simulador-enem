#!/usr/bin/env python3
"""Valida revisões humanas e exporta somente questões aprovadas.

Entrada: question-review.json editado por um revisor.
Saída: JSON de publicação; nenhuma questão é aprovada por este script.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

OPTIONS = ("A", "B", "C", "D", "E")
LANGUAGES = ("ingles", "espanhol")


def validate(record: dict, *, source_sha256: str) -> tuple[dict | None, list[str]]:
    problems = []
    if record.get("review_status") != "approved":
        return None, ["revisão pendente"]
    exam = record.get("exam") or {}
    if exam.get("source_sha256") != source_sha256:
        problems.append("hash de origem divergente")
    for field in ("year", "application", "day", "color"):
        if not exam.get(field):
            problems.append(f"campo obrigatório ausente: exam.{field}")
    if not isinstance(record.get("original_number"), int) or not 1 <= record["original_number"] <= 180:
        problems.append("número da questão inválido")
    if not isinstance(record.get("page"), int) or record["page"] < 1:
        problems.append("página inválida")
    if not isinstance(record.get("bbox"), list) or len(record["bbox"]) != 4:
        problems.append("coordenadas ausentes")
    if not record.get("image_sha256") or len(record["image_sha256"]) != 64:
        problems.append("hash de imagem ausente")
    if not isinstance(record.get("stem"), str) or not record["stem"].strip():
        problems.append("enunciado revisado ausente")
    alternatives = record.get("alternatives")
    if not isinstance(alternatives, dict) or set(alternatives) != set(OPTIONS) or any(
        not isinstance(alternatives[k], str) or not alternatives[k].strip() for k in OPTIONS if k in alternatives
    ):
        problems.append("alternativas A–E incompletas")
    if record.get("correct_option") not in OPTIONS:
        problems.append("gabarito A–E ausente")
    if not isinstance(record.get("answer_key_source"), str) or not record["answer_key_source"].strip():
        problems.append("fonte do gabarito ausente")
    if not isinstance(record.get("reviewer"), str) or not record["reviewer"].strip():
        problems.append("identificação do revisor ausente")
    if not isinstance(record.get("reviewed_at"), str) or not record["reviewed_at"].strip():
        problems.append("data de revisão ausente")
    if record.get("original_number") in range(1, 6) and exam.get("day") == 1:
        if record.get("language_variant") not in LANGUAGES:
            problems.append("língua obrigatória nas questões 1–5 do primeiro dia")
    elif record.get("language_variant") not in (None, ""):
        problems.append("variante de língua inesperada")
    if problems:
        return None, problems
    return {
        "id": record["id"], "exam": exam,
        "original_number": record["original_number"],
        "language_variant": record.get("language_variant"),
        "stem": record["stem"].strip(),
        "alternatives": {k: alternatives[k].strip() for k in OPTIONS},
        "correct_option": record["correct_option"],
        "answer_key_source": record["answer_key_source"],
        "asset": {"page": record["page"], "bbox": record["bbox"],
                  "image": record["image"], "sha256": record["image_sha256"]},
        "review": {"reviewer": record["reviewer"], "reviewed_at": record["reviewed_at"]},
        "calibration": None,
    }, []


def export_approved(input_path: Path, output_path: Path) -> dict:
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    source_hash = payload.get("source_sha256")
    if not isinstance(source_hash, str) or len(source_hash) != 64:
        raise ValueError("Manifesto sem SHA-256 de origem")
    records = payload.get("records")
    if not isinstance(records, list):
        raise ValueError("Manifesto sem lista de registros")
    approved, rejected = [], []
    ids = set()
    keys = set()
    for index, record in enumerate(records):
        item, issues = validate(record, source_sha256=source_hash)
        if issues:
            rejected.append({"index": index, "id": record.get("id"), "reasons": issues})
            continue
        if item["id"] in ids:
            raise ValueError(f"ID aprovado duplicado: {item['id']}")
        ids.add(item["id"])
        key = (item["exam"]["year"], item["exam"]["application"],
               item["exam"]["day"], item["exam"]["color"],
               item["original_number"], item["language_variant"])
        if key in keys:
            raise ValueError(f"Questão aprovada duplicada: {key}")
        keys.add(key)
        approved.append(item)
    result = {
        "schema_version": 1, "source_sha256": source_hash,
        "questions": approved,
        "export_summary": {"approved": len(approved), "not_exported": len(rejected),
                           "rejections": rejected},
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result["export_summary"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(export_approved(args.input, args.output), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
