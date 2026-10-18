#!/usr/bin/env python3
"""Renderiza uma questão estruturada como HTML branco, sem inferir conteúdo do PDF."""
from __future__ import annotations

import argparse
import html
import json
from pathlib import Path

LETTERS = "ABCDE"
ROLES = {"titulo", "texto", "enunciado", "imagem", "credito"}


def validate(question: dict) -> None:
    if not isinstance(question.get("id"), str) or not question["id"]:
        raise ValueError("ID obrigatório")
    blocks = question.get("blocks")
    if not isinstance(blocks, list) or not blocks:
        raise ValueError("Blocos de conteúdo obrigatórios")
    for block in blocks:
        if block.get("role") is not None and block["role"] not in ROLES:
            raise ValueError("Papel de bloco inválido")
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
            if block.get("role") is not None and block["role"] not in ROLES:
                raise ValueError("Papel de alternativa inválido")
            if block.get("type") not in {"text", "image"} or not isinstance(block.get("value"), str) or not block["value"].strip():
                raise ValueError("Bloco de alternativa inválido")


def render_blocks(blocks: list[dict]) -> str:
    parts = []
    for block in blocks:
        value = html.escape(block["value"], quote=True)
        role = block.get("role", "texto" if block["type"] == "text" else "imagem")
        if block["type"] == "text":
            tag = "h3" if role == "titulo" else "p"
            parts.append(f'<{tag} class="block-{role}">{value}</{tag}>')
        else:
            parts.append(f'<img class="block-{role}" loading="lazy" src="{value}" alt="Imagem da questão">')
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
        '.block-titulo{font-size:1.08rem;font-weight:750;letter-spacing:.02em;margin-top:22px}'
        '.block-credito{font-size:.78rem;color:#64748b;line-height:1.45}'
        '.block-enunciado{font-size:1.05rem;font-weight:550;line-height:1.7;margin:24px 0}'
        '.block-imagem{max-height:360px;width:auto}li .block-imagem{max-height:240px}'
        'li .block-texto{font-size:1rem;line-height:1.55}'
        '@media(max-width:600px){main{margin:0;padding:20px;border-radius:0}li{padding:12px}}'
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
