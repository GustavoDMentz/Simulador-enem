#!/usr/bin/env python3
"""Executa o pipeline determinístico ENEM em lote, sem aprovar questões.

Manifesto JSON: {"exams":[{"year":2024,"day":1,"color":"azul",
"application":"regular","pdf":"caminho/arquivo.pdf"}]}
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def identity(item: dict) -> str:
    year, day = int(item["year"]), int(item["day"])
    color = str(item["color"]).lower()
    application = str(item.get("application", "regular")).lower()
    if not 2017 <= year <= 2025 or day not in (1, 2):
        raise ValueError("Ano ou dia fora do escopo 2017–2025")
    if not color.replace("-", "").isalnum() or not application.replace("-", "").isalnum():
        raise ValueError("Cor/aplicação inválida")
    return f"{year}-{application}-d{day}-{color}"


def execute(manifest: Path, output: Path, *, force: bool = False) -> dict:
    data = json.loads(manifest.read_text(encoding="utf-8"))
    exams = data.get("exams")
    if not isinstance(exams, list):
        raise ValueError("Manifesto precisa conter lista exams")
    output.mkdir(parents=True, exist_ok=True)
    root = Path(__file__).resolve().parents[1]
    summary = []
    seen = set()
    for item in exams:
        key = identity(item)
        if key in seen:
            raise ValueError(f"Identidade repetida: {key}")
        seen.add(key)
        pdf = Path(item["pdf"]).expanduser()
        if not pdf.is_absolute():
            pdf = (manifest.parent / pdf).resolve()
        target = output / key
        status_file = target / "status.json"
        if not pdf.is_file():
            summary.append({"id": key, "status": "missing_pdf", "pdf": str(pdf)})
            continue
        sha = digest(pdf)
        if status_file.exists() and not force:
            old = json.loads(status_file.read_text(encoding="utf-8"))
            if old.get("source_sha256") == sha and old.get("status") == "processed":
                summary.append({"id": key, "status": "skipped_unchanged"})
                continue
        questions = target / "questions"
        review = target / "review"
        queue_file = review / "question-review.json"
        if queue_file.exists():
            previous = json.loads(queue_file.read_text(encoding="utf-8"))
            if any(r.get("review_status") != "pending" for r in previous.get("records", [])):
                summary.append({"id": key, "status": "blocked_reviewed_queue",
                                "reason": "Fila contém decisões humanas; não sobrescrever"})
                continue
            if not force:
                summary.append({"id": key, "status": "blocked_existing_queue",
                                "reason": "Fila existente; use --force somente se for descartável"})
                continue
        try:
            subprocess.run([sys.executable, str(root / "scripts/segment_question_candidates.py"),
                            "--pdf", str(pdf), "--output", str(questions)], check=True)
            subprocess.run([sys.executable, str(root / "scripts/build_question_review.py"),
                            "--pdf", str(pdf), "--candidates", str(questions / "candidates.json"),
                            "--output", str(review), "--year", str(item["year"]),
                            "--day", str(item["day"]), "--color", str(item["color"]),
                            "--application", str(item.get("application", "regular"))], check=True)
            # Never overwrite a previously reviewed queue silently.
            status = "processed"
            count = len(json.loads((review / "question-review.json").read_text(encoding="utf-8"))["records"])
            result = {"id": key, "status": status, "source_sha256": sha,
                      "candidates": count, "publication_authorized": False}
            status_file.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
            summary.append(result)
        except (subprocess.CalledProcessError, OSError, ValueError) as exc:
            summary.append({"id": key, "status": "failed", "error": str(exc)})
    report = {"schema_version": 1, "exams": summary, "publication_authorized": False}
    (output / "batch-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    report = execute(args.manifest, args.output, force=args.force)
    print(json.dumps([{"id": x["id"], "status": x["status"],
                       "candidates": x.get("candidates")} for x in report["exams"]],
                     ensure_ascii=False, indent=2))
    if any(x["status"] == "failed" for x in report["exams"]):
        sys.exit(1)


if __name__ == "__main__":
    main()
