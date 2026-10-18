#!/usr/bin/env python3
"""Auditoria Gemini multimodal, opt-in, com validação e contabilidade de tokens.

Nenhuma chamada é feita sem --execute. Nunca autoriza publicação.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

try:
    from scripts.audit_structured_question import validate_report
except ModuleNotFoundError:
    from audit_structured_question import validate_report

ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/"
DEFAULT_MODEL = "gemini-3.5-flash-lite"
SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "status": {"type": "STRING", "enum": ["conforme", "divergente", "inconclusivo"]},
        "issues": {"type": "ARRAY", "items": {
            "type": "OBJECT", "properties": {
                "type": {"type": "STRING", "enum": [
                    "omissao", "duplicacao", "imagem_incorreta", "alternativa_incorreta",
                    "texto_incorreto", "conteudo_vizinho", "outro"]},
                "location": {"type": "STRING"}, "description": {"type": "STRING"},
            }, "required": ["type", "location", "description"]}},
        "explanation": {"type": "STRING"},
    },
    "required": ["status", "issues", "explanation"],
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(folder: Path) -> dict:
    folder = folder.resolve()
    manifest_path = folder / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    files = manifest.get("files_sha256")
    if not isinstance(files, dict) or not files:
        raise ValueError("Manifesto sem arquivos")
    for name, expected in files.items():
        path = (folder / name).resolve()
        if not path.is_relative_to(folder) or not path.is_file() or sha(path) != expected:
            raise ValueError(f"Hash divergente: {name}")
    for required in ("original.png", "reconstructed.png", "question.json", "auditor_prompt.txt"):
        if required not in files:
            raise ValueError(f"Evidência ausente do manifesto: {required}")
    if manifest.get("publication_authorized") is not False:
        raise ValueError("Pacote não está bloqueado para publicação")
    manifest["manifest_sha256"] = sha(manifest_path)
    return manifest


def list_models(api_key: str) -> list[dict]:
    """Consulta modelos acessíveis à chave, com paginação e métodos suportados."""
    from urllib.parse import urlencode
    found = []
    token = None
    while True:
        query = urlencode({"pageSize": 100, **({"pageToken": token} if token else {})})
        request = Request(ENDPOINT + "?" + query, headers={"x-goog-api-key": api_key})
        with urlopen(request, timeout=30) as response:
            data = json.load(response)
        found.extend(data.get("models", []))
        token = data.get("nextPageToken")
        if not token:
            break
    return found


def ensure_model_available(model: str, api_key: str) -> dict:
    for entry in list_models(api_key):
        if entry.get("name") == "models/" + model:
            if "generateContent" not in entry.get("supportedGenerationMethods", []):
                raise ValueError(f"Modelo {model} não suporta generateContent")
            return entry
    raise ValueError(f"Modelo {model} não disponível para esta chave")


def payload(folder: Path, model: str, max_output_tokens: int) -> dict:
    question = json.loads((folder / "question.json").read_text(encoding="utf-8"))
    prompt = (folder / "auditor_prompt.txt").read_text(encoding="utf-8")
    prompt += "\nConteúdo estruturado para conferência textual:\n"
    prompt += json.dumps(question, ensure_ascii=False)
    parts = [{"text": prompt}]
    for filename in ("original.png", "reconstructed.png"):
        parts.append({"inline_data": {
            "mime_type": "image/png",
            "data": base64.b64encode((folder / filename).read_bytes()).decode("ascii"),
        }})
    return {
        "contents": [{"role": "user", "parts": parts}],
        "generationConfig": {
            "temperature": 0,
            "maxOutputTokens": max_output_tokens,
            "responseMimeType": "application/json",
            "responseSchema": SCHEMA,
        },
    }


def parse_response(data: dict, manifest: dict, model: str) -> dict:
    candidates = data.get("candidates") or []
    if not candidates or candidates[0].get("finishReason") != "STOP":
        raise ValueError("Resposta incompleta ou bloqueada pelo Gemini")
    parts = candidates[0].get("content", {}).get("parts", [])
    text = "".join(part.get("text", "") for part in parts)
    try:
        report = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError("Gemini não retornou JSON válido") from exc
    report["model"] = model
    return validate_report(report, manifest)


def audit(folder: Path, output: Path, *, model: str, execute: bool,
          max_output_tokens: int, input_rate: float | None,
          output_rate: float | None) -> dict:
    folder = folder.resolve()
    manifest = verify(folder)
    if output.exists():
        raise ValueError("Relatório já existe; não sobrescrever auditoria")
    if not model or not all(c.isalnum() or c in "-._" for c in model):
        raise ValueError("Nome de modelo inválido")
    if not 128 <= max_output_tokens <= 4096:
        raise ValueError("Limite de saída deve ficar entre 128 e 4096 tokens")
    if (input_rate is None) != (output_rate is None):
        raise ValueError("Informe ambas as tarifas ou nenhuma")
    if input_rate is not None and (input_rate < 0 or output_rate < 0):
        raise ValueError("Tarifas não podem ser negativas")
    request_body = payload(folder, model, max_output_tokens)
    if not execute:
        return {"dry_run": True, "question_id": manifest["question_id"],
                "model": model, "images": 2, "max_output_tokens": max_output_tokens,
                "publication_authorized": False}
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise ValueError("GEMINI_API_KEY não configurada")
    ensure_model_available(model, key)
    url = ENDPOINT + model + ":generateContent"
    request = Request(url, data=json.dumps(request_body).encode("utf-8"),
                      headers={"Content-Type": "application/json", "x-goog-api-key": key},
                      method="POST")
    try:
        with urlopen(request, timeout=120) as response:
            data = json.load(response)
    except HTTPError as exc:
        raise RuntimeError(f"Gemini HTTP {exc.code}; verifique modelo, cota e permissões") from exc
    except URLError as exc:
        raise RuntimeError("Falha de conexão com Gemini") from exc
    result = parse_response(data, manifest, model)
    usage = data.get("usageMetadata") or {}
    inp = usage.get("promptTokenCount")
    out = usage.get("candidatesTokenCount")
    cost = None
    if input_rate is not None and isinstance(inp, int) and isinstance(out, int):
        cost = round((inp * input_rate + out * output_rate) / 1_000_000, 8)
    result["usage"] = {
        "prompt_tokens": inp, "output_tokens": out,
        "total_tokens": usage.get("totalTokenCount"),
        "estimated_usd": cost,
        "rates_usd_per_million": (
            {"input": input_rate, "output": output_rate}
            if input_rate is not None else None),
        "note": "Estimativa informativa; não é teto de gasto nem cobrança oficial.",
    }
    result["evidence_files_sha256"] = manifest["files_sha256"]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"status": result["status"], "usage": result["usage"],
            "publication_authorized": False, "output": str(output)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--list-models", action="store_true", help="Consulta catálogo acessível à chave, sem gerar conteúdo")
    parser.add_argument("--max-output-tokens", type=int, default=1024)
    parser.add_argument("--input-usd-per-million", type=float)
    parser.add_argument("--output-usd-per-million", type=float)
    parser.add_argument("--execute", action="store_true", help="Autoriza UMA chamada real à API")
    args = parser.parse_args()
    if args.list_models:
        key = os.environ.get("GEMINI_API_KEY")
        if not key:
            parser.error("GEMINI_API_KEY não configurada")
        models = [{"id": m["name"].removeprefix("models/"),
                   "display_name": m.get("displayName")}
                  for m in list_models(key)
                  if "generateContent" in m.get("supportedGenerationMethods", [])]
        print(json.dumps(models, ensure_ascii=False, indent=2))
        return
    if args.package is None or args.output is None:
        parser.error("--package e --output são obrigatórios para auditoria")
    print(json.dumps(audit(args.package, args.output, model=args.model,
        execute=args.execute, max_output_tokens=args.max_output_tokens,
        input_rate=args.input_usd_per_million,
        output_rate=args.output_usd_per_million), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
