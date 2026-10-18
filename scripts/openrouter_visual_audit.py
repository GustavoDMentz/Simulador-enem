#!/usr/bin/env python3
"""Teste isolado do Nemotron VL via OpenRouter; não altera pacote nem aprova publicação."""
from __future__ import annotations

import argparse
import base64
import json
import os
import re
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

try:
    from scripts.gemini_visual_audit import verify
    from scripts.audit_structured_question import validate_report
except ModuleNotFoundError:
    from gemini_visual_audit import verify
    from audit_structured_question import validate_report

MODEL = "nvidia/nemotron-3.5-super-vl:free"
ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"
SCHEMA = {
    "type": "object",
    "properties": {
        "status": {"type": "string", "enum": ["conforme", "divergente", "inconclusivo"]},
        "issues": {"type": "array", "items": {"type": "object", "properties": {
            "type": {"type": "string", "enum": ["omissao", "duplicacao", "imagem_incorreta",
                "alternativa_incorreta", "texto_incorreto", "conteudo_vizinho", "outro"]},
            "location": {"type": "string"}, "description": {"type": "string"}},
            "required": ["type", "location", "description"], "additionalProperties": False}},
        "explanation": {"type": "string"},
    },
    "required": ["status", "issues", "explanation"], "additionalProperties": False,
}


def request_payload(folder: Path, max_tokens: int) -> dict:
    prompt = (folder / "auditor_prompt.txt").read_text(encoding="utf-8")
    prompt += ("\nATENÇÃO: a página original contém outras questões, o que NÃO é erro. "
               "Compare somente a questão identificada no JSON. Confira palavra por "
               "palavra o FIM do enunciado, especialmente omissões. Conteúdo vizinho "
               "é defeito apenas se aparecer na RECONSTRUÇÃO.\n")
    prompt += json.dumps(json.loads((folder / "question.json").read_text(encoding="utf-8")),
                         ensure_ascii=False)
    content = [{"type": "text", "text": prompt}]
    for name in ("original.png", "reconstructed.png"):
        encoded = base64.b64encode((folder / name).read_bytes()).decode("ascii")
        content.append({"type": "image_url", "image_url": {
            "url": "data:image/png;base64," + encoded}})
    return {
        "model": MODEL,
        "messages": [{"role": "user", "content": content}],
        "temperature": 0,
        "max_tokens": max_tokens,
        "response_format": {"type": "json_schema", "json_schema": {
            "name": "enem_visual_audit", "strict": True, "schema": SCHEMA}},
    }


def parse_response(data: dict, manifest: dict) -> dict:
    choices = data.get("choices") or []
    if not choices or choices[0].get("finish_reason") != "stop":
        raise ValueError("Resposta incompleta ou bloqueada")
    raw = choices[0].get("message", {}).get("content")
    if not isinstance(raw, str):
        raise ValueError("Resposta textual ausente")
    try:
        report = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("JSON inválido na resposta do Nemotron") from exc
    report["model"] = MODEL
    result = validate_report(report, manifest)
    result["provider"] = "openrouter"
    result["usage"] = data.get("usage", {})
    result["publication_authorized"] = False
    return result


def audit(folder: Path, output: Path, execute: bool, max_tokens: int) -> dict:
    folder = folder.resolve()
    manifest = verify(folder)
    if output.exists():
        raise ValueError("Relatório existente: não sobrescrever")
    if not 256 <= max_tokens <= 4096:
        raise ValueError("max_tokens fora do intervalo 256–4096")
    body = request_payload(folder, max_tokens)
    if not execute:
        return {"dry_run": True, "model": MODEL, "images": 2,
                "question_id": manifest["question_id"], "publication_authorized": False}
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        raise ValueError("OPENROUTER_API_KEY não configurada")
    request = Request(ENDPOINT, data=json.dumps(body).encode("utf-8"),
                      headers={"Authorization": "Bearer " + key,
                               "Content-Type": "application/json"}, method="POST")
    try:
        with urlopen(request, timeout=180) as response:
            data = json.load(response)
    except HTTPError as exc:
        raise RuntimeError(f"OpenRouter HTTP {exc.code}; confira cota e compatibilidade do endpoint") from exc
    except URLError as exc:
        raise RuntimeError("Falha de conexão com OpenRouter") from exc
    result = parse_response(data, manifest)
    result["evidence_files_sha256"] = manifest["files_sha256"]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"status": result["status"], "usage": result["usage"],
            "publication_authorized": False, "output": str(output)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--max-tokens", type=int, default=2048)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    print(json.dumps(audit(args.package, args.output, args.execute, args.max_tokens),
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
