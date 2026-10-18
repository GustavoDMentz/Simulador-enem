#!/usr/bin/env python3
"""Cria pacote experimental com omissão conhecida, sem alterar evidência original."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

try:
    from scripts.gemini_visual_audit import verify
    from scripts.render_structured_question import render
except ModuleNotFoundError:
    from gemini_visual_audit import verify
    from render_structured_question import render


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def mutate(source: Path, target: Path) -> dict:
    source, target = source.resolve(), target.resolve()
    verify(source)
    if source == target or source in target.parents or target in source.parents:
        raise ValueError("Origem e destino devem ser diretórios separados")
    if target.exists():
        raise ValueError("Destino já existe; não sobrescrever experimentos")
    question = json.loads((source / "question.json").read_text(encoding="utf-8"))
    candidates = [(i, b) for i, b in enumerate(question["blocks"])
                  if b.get("type") == "text" and b.get("role") == "enunciado"
                  and len(b.get("value", "").split()) >= 12]
    if len(candidates) != 1:
        raise ValueError("Exige exatamente um enunciado longo e identificado")
    index, block = candidates[0]
    original = block["value"]
    words = original.split()
    removed = words[-min(8, max(3, len(words) // 4)):]
    changed = " ".join(words[:-len(removed)])
    if not changed.strip() or changed == original:
        raise ValueError("Mutação sem efeito")
    shutil.copytree(source, target)
    question["blocks"][index]["value"] = changed
    question["publication_authorized"] = False
    (target / "question.json").write_text(
        json.dumps(question, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (target / "reconstructed.html").write_text(render(question), encoding="utf-8")
    # Screenshot antigo não pode acompanhar HTML modificado.
    (target / "reconstructed.png").unlink()
    record = {
        "experiment": "deliberate_omission",
        "source_manifest_sha256": sha(source / "manifest.json"),
        "question_id": question["id"],
        "block_index": index,
        "removed_text": " ".join(removed),
        "expected_status": "divergente",
        "publication_authorized": False,
    }
    # Ground truth fora do pacote enviado ao modelo.
    truth = target.parent / (target.name + ".ground_truth.json")
    if truth.exists():
        shutil.rmtree(target)
        raise ValueError("Arquivo de referência já existe")
    truth.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n",
                     encoding="utf-8")
    manifest = json.loads((target / "manifest.json").read_text(encoding="utf-8"))
    manifest["files_sha256"] = {
        p.relative_to(target).as_posix(): sha(p)
        for p in sorted(target.rglob("*"))
        if p.is_file() and p.name != "manifest.json"
    }
    manifest["audit_status"] = "pending"
    manifest["publication_authorized"] = False
    (target / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"target": str(target), "ground_truth": str(truth),
            "removed_words": len(removed), "publication_authorized": False}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(mutate(args.source, args.output), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
