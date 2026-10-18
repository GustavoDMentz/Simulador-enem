#!/usr/bin/env python3
"""Cruza candidatos com um gabarito transcrito e identificado por caderno.

A fonte do gabarito precisa ser fornecida e verificada separadamente.
Não confunde 'gabarito informado' com 'gabarito oficialmente autenticado'.
Não aprova nem publica questões.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

SHA256 = re.compile(r"^[a-f0-9]{64}$")
LETTERS = set("ABCDE")
VARIANTS = {"ingles", "espanhol"}


def load_key(path: Path) -> dict:
    raw = path.read_bytes()
    data = json.loads(raw)
    exam = data.get("exam")
    source = data.get("source")
    entries = data.get("answers")
    if not isinstance(exam, dict) or not isinstance(source, dict) or not isinstance(entries, list):
        raise ValueError("Gabarito precisa de exam, source e answers")
    for field in ("year", "application", "day", "color"):
        if exam.get(field) in (None, ""):
            raise ValueError(f"Identificação incompleta do caderno: {field}")
    if not isinstance(source.get("url"), str) or not source["url"].strip():
        raise ValueError("Informe URL verificável da fonte do gabarito")
    if not isinstance(source.get("sha256"), str) or not SHA256.fullmatch(source["sha256"]):
        raise ValueError("Informe SHA-256 do documento de gabarito original")
    if source.get("verification_status") not in ("pending", "verified"):
        raise ValueError("verification_status deve ser pending ou verified")
    indexed = {}
    for row in entries:
        n, letter, variant = row.get("number"), row.get("answer"), row.get("language_variant")
        if not isinstance(n, int) or isinstance(n, bool) or not 1 <= n <= 180:
            raise ValueError(f"Número de questão inválido: {n}")
        if letter not in LETTERS and letter != "ANULADA":
            raise ValueError(f"Resposta inválida na questão {n}: {letter}")
        if exam["day"] == 1 and 1 <= n <= 5:
            if variant not in VARIANTS:
                raise ValueError(f"Questão {n}: variante de língua obrigatória")
        elif variant is not None:
            raise ValueError(f"Questão {n}: variante de língua inesperada")
        key = (n, variant)
        if key in indexed:
            raise ValueError(f"Entrada duplicada no gabarito: {key}")
        indexed[key] = letter
    return {"exam": exam, "source": source, "answers": indexed,
            "manifest_sha256": hashlib.sha256(raw).hexdigest()}


def reconcile(review_path: Path, key_path: Path, output_path: Path) -> dict:
    review = json.loads(review_path.read_text(encoding="utf-8"))
    key = load_key(key_path)
    records = review.get("records")
    if not isinstance(records, list):
        raise ValueError("Arquivo de revisão sem records")
    results = []
    seen = Counter((r.get("original_number"), r.get("language_variant")) for r in records)
    for r in records:
        exam = r.get("exam") or {}
        identity_matches = all(exam.get(field) == key["exam"][field]
                               for field in ("year", "application", "day", "color"))
        n = r.get("original_number")
        variant = r.get("language_variant")
        identity = (n, variant)
        flags = []
        answer = None
        if not identity_matches:
            flags.append("exam_identity_mismatch")
        elif key["exam"]["day"] == 1 and isinstance(n, int) and 1 <= n <= 5 and variant not in VARIANTS:
            flags.append("language_variant_missing")
        elif seen[identity] > 1:
            flags.append("duplicate_candidate_identity")
        elif identity not in key["answers"]:
            flags.append("answer_not_found")
        else:
            answer = key["answers"][identity]
            if answer == "ANULADA":
                flags.append("annulled_question")
            if r.get("correct_option") and r["correct_option"] != answer:
                flags.append("existing_answer_conflict")
        if key["source"]["verification_status"] != "verified":
            flags.append("key_source_not_verified")
        status = ("matched" if not flags else
                  "blocked" if "existing_answer_conflict" in flags or
                  "exam_identity_mismatch" in flags or
                  "duplicate_candidate_identity" in flags else "needs_review")
        results.append({"id": r.get("id"), "number": n, "language_variant": variant,
                        "status": status, "answer": answer if status == "matched" else None,
                        "flags": flags})
    result = {
        "schema_version": 1, "policy": "answer-key-reconciliation-v1",
        "source_pdf_sha256": review.get("source_sha256"),
        "key_manifest_sha256": key["manifest_sha256"],
        "key_source": key["source"],
        "exam": key["exam"],
        "summary": dict(Counter(item["status"] for item in results)),
        "results": results,
        "publication_authorized": False,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review", required=True, type=Path)
    parser.add_argument("--key", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(reconcile(args.review, args.key, args.output)["summary"],
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
