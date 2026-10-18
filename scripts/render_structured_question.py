#!/usr/bin/env python3
"""Renderiza uma questão estruturada como HTML branco, sem inferir conteúdo do PDF."""
from __future__ import annotations

import argparse
import html
import json
from pathlib import Path

LETTERS = "ABCDE"


def validate(question: dict) -> None:
    if not isinstance(question.get("id"), str) or not question["id"]:
        raise ValueError("ID obrigatório")
    blocks = question.get("blocks")
    if not isinstance(blocks, list) or not blocks:
        raise ValueError("Blocos de conteúdo obrigatórios")
    for block in blocks:
        if block.get("type") not in {"text", "image"}:
            raise ValueError("Tipo de bloco inválido")
        if not isinstance(block.get("value"), str) or not block["value"].strip():
            raise ValueError("Conteúdo de bloco obrigatório")
    options = question.get("alternatives")
    if not isinstance(options, list) or len(options) != 5:
        raise ValueError("Exatamente cinco alternativas são obrigatórias")
    if [o.get("label") for o in options] != list(LETTERS):
        raise ValueError("Alternativas devem estar ordenadas de A até E")
    for option in options:
        if not isinstance(option.get("blocks"), list) or not option["blocks"]:
            raise ValueError("Cada alternativa precisa de conteúdo")
        for block in option["blocks"]:
            if block.get("type") not in {"text", "image"} or not isinstance(block.get("value"), str) or not block["value"].strip():
                raise ValueError("Bloco de alternativa inválido")


def render_blocks(blocks: list[dict]) -> str:
    parts = []
    for block in blocks:
        value = html.escape(block["value"], quote=True)
        if block["type"] == "text":
            parts.append(f"<p>{value}</p>")
        else:
            parts.append(f'<img loading="lazy" src="{value}" alt="Imagem da questão">')
    return "".join(parts)


def render(question: dict) -> str:
    validate(question)
    options = "".join(
        '<li><span class="letter">' + o["label"] + '</span><div>' +
        render_blocks(o["blocks"]) + '</div></li>'
        for o in question["alternatives"]
    )
    return (
        '<!doctype html><html lang="pt-BR"><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>Questão ENEM — prévia</title>'
        '<style>body{margin:0;background:#f3f4f6;color:#17212b;font:16px/1.6 system-ui}'
        'main{max-width:800px;margin:28px auto;padding:32px;background:white;border-radius:12px}'
        'img{max-width:100%;height:auto;object-fit:contain;display:block;margin:12px auto}'
        'ol{padding:0;list-style:none}li{display:flex;gap:16px;align-items:flex-start;'
        'padding:12px 16px;border:1px solid #e1e4e8;border-radius:10px;margin:10px 0}'
        'li>div{min-width:0;flex:1}p{white-space:pre-wrap;margin:8px 0}'
        '.letter{border:1px solid #94a3b8;border-radius:50%;width:32px;height:32px;'
        'flex:none;display:grid;place-items:center;font-weight:700}'
        '.note{color:#64748b;font-size:13px}</style>'
        '<main><p class="note">Prévia estruturada — não publicada</p><h1>' +
        html.escape(question["id"]) + '</h1>' + render_blocks(question["blocks"]) +
        '<h2>Alternativas</h2><ol>' + options + '</ol>'
        '<p class="note">Conteúdo sujeito à revisão visual e ao gabarito oficial.</p></main></html>'
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    question = json.loads(args.input.read_text(encoding="utf-8"))
    result = render(question)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(result, encoding="utf-8")
    print(json.dumps({"id": question["id"], "output": str(args.output),
                      "publication_authorized": False}, ensure_ascii=False))


if __name__ == "__main__":
    main()
