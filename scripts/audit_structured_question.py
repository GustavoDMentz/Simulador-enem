#!/usr/bin/env python3
"""Prepara pacote local e valida parecer de auditor multimodal; sem chamadas de API."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path

import pymupdf

from scripts.render_structured_question import render, validate

STATUSES = {"conforme", "divergente", "inconclusivo"}
ISSUES = {"omissao", "duplicacao", "imagem_incorreta", "alternativa_incorreta",
          "texto_incorreto", "conteudo_vizinho", "outro"}
PROMPT = """Você é auditor visual de extração de questões ENEM.
Compare a página oficial (original.png) com a questão reconstruída (reconstructed.html,
ou captura de tela dessa página) e o conteúdo de question.json.
A página oficial pode conter outras questões: avalie APENAS a questão identificada.
Verifique texto integral, ordem dos blocos, créditos, imagens, associação das
alternativas A–E e contaminação por questões vizinhas.
Não deduza gabarito. Não corrija conteúdo silenciosamente. Não aprove publicação.
Retorne SOMENTE JSON:
{"status":"conforme|divergente|inconclusivo",
 "issues":[{"type":"omissao|duplicacao|imagem_incorreta|alternativa_incorreta|texto_incorreto|conteudo_vizinho|outro",
            "location":"identificação objetiva","description":"problema observável"}],
 "explanation":"justificativa fundamentada"}
Use inconclusivo quando não puder verificar visualmente um elemento.
"""


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def package(question_path: Path, pdf: Path, output: Path) -> dict:
    question = json.loads(question_path.read_text(encoding="utf-8"))
    validate(question)
    if question.get("publication_authorized") is True:
        raise ValueError("Pacote de auditoria não aceita publicação autorizada")
    if sha(pdf) != question.get("source_pdf_sha256"):
        raise ValueError("Hash do PDF oficial diverge")
    page_num = question.get("source_page")
    if not isinstance(page_num, int) or isinstance(page_num, bool):
        raise ValueError("Página oficial inválida")
    with pymupdf.open(pdf) as doc:
        if not 1 <= page_num <= len(doc):
            raise ValueError("Página oficial inválida")
        # Renderiza página inteira: não perder continuações entre colunas.
        page_png = doc[page_num - 1].get_pixmap(dpi=160, alpha=False).tobytes("png")
    if output.exists() and any(output.iterdir()):
        raise ValueError("Diretório de saída precisa estar vazio")
    output.mkdir(parents=True, exist_ok=True)
    (output / "original.png").write_bytes(page_png)
    assets = output / "assets"
    assets.mkdir()
    copied = {}
    all_blocks = question["blocks"] + [
        b for opt in question["alternatives"] for b in opt["blocks"]
    ]
    for block in all_blocks:
        if block["type"] != "image":
            continue
        value = block["value"]
        if not isinstance(value, str):
            raise ValueError("Caminho de imagem inválido")
        src = (question_path.parent / value).resolve()
        base = question_path.parent.resolve()
        if not src.is_relative_to(base) or not src.is_file():
            raise ValueError("Imagem fora do diretório da questão ou ausente")
        if block.get("sha256") != sha(src):
            raise ValueError(f"Hash de imagem diverge: {value}")
        if src not in copied:
            name = f"image_{len(copied):03d}.png"
            shutil.copyfile(src, assets / name)
            copied[src] = name
        block["value"] = "assets/" + copied[src]
    question["publication_authorized"] = False
    (output / "question.json").write_text(
        json.dumps(question, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output / "reconstructed.html").write_text(render(question), encoding="utf-8")
    (output / "auditor_prompt.txt").write_text(PROMPT, encoding="utf-8")
    manifest = {
        "schema_version": 1,
        "question_id": question["id"],
        "source_pdf_sha256": sha(pdf),
        "source_page": page_num,
        "files_sha256": {
            p.relative_to(output).as_posix(): sha(p)
            for p in sorted(output.rglob("*")) if p.is_file()
        },
        "audit_status": "pending",
        "publication_authorized": False,
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def validate_report(report: dict, manifest: dict) -> dict:
    if not isinstance(report, dict) or report.get("status") not in STATUSES:
        raise ValueError("Status de auditoria inválido")
    issues = report.get("issues")
    if not isinstance(issues, list):
        raise ValueError("issues deve ser lista")
    if report["status"] == "conforme" and issues:
        raise ValueError("Parecer conforme não pode listar divergências")
    if report["status"] == "divergente" and not issues:
        raise ValueError("Divergência exige evidências")
    for issue in issues:
        if not isinstance(issue, dict) or issue.get("type") not in ISSUES:
            raise ValueError("Tipo de problema inválido")
        if not all(isinstance(issue.get(k), str) and issue[k].strip()
                   for k in ("location", "description")):
            raise ValueError("Problema exige localização e descrição")
    if not isinstance(report.get("explanation"), str) or not report["explanation"].strip():
        raise ValueError("Justificativa obrigatória")
    return {
        "schema_version": 1, "question_id": manifest["question_id"],
        "evidence_manifest_sha256": manifest["manifest_sha256"],
        "model": report.get("model") if isinstance(report.get("model"), str) else None,
        "status": report["status"], "issues": issues,
        "explanation": report["explanation"],
        "requires_human_review": True, "publication_authorized": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    pack = sub.add_parser("package")
    pack.add_argument("--question", required=True, type=Path)
    pack.add_argument("--pdf", required=True, type=Path)
    pack.add_argument("--output", required=True, type=Path)
    review = sub.add_parser("review")
    review.add_argument("--manifest", required=True, type=Path)
    review.add_argument("--report", required=True, type=Path)
    review.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.command == "package":
        result = package(args.question, args.pdf, args.output)
        print(json.dumps({"question_id": result["question_id"],
                          "audit_status": "pending", "publication_authorized": False}))
    else:
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        for name, expected in manifest["files_sha256"].items():
            path = (args.manifest.parent / name).resolve()
            if not path.is_relative_to(args.manifest.parent.resolve()) or sha(path) != expected:
                raise ValueError("Pacote de evidências alterado")
        manifest["manifest_sha256"] = sha(args.manifest)
        report = json.loads(args.report.read_text(encoding="utf-8"))
        result = validate_report(report, manifest)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                               encoding="utf-8")
        print(json.dumps({"status": result["status"], "publication_authorized": False}))


if __name__ == "__main__":
    main()
