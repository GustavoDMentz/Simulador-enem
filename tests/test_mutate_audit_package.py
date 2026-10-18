import hashlib
import json

import pytest

from scripts.mutate_audit_package import mutate
from scripts.gemini_visual_audit import verify


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def test_mutation_isolated_and_requires_new_capture(tmp_path):
    src = tmp_path / "source"
    src.mkdir()
    question = {
        "id": "test-q", "blocks": [{"type": "text", "role": "enunciado",
            "value": "Este é um enunciado de teste com várias palavras para detectar uma omissão proposital no final da questão original"}],
        "alternatives": [{"label": label, "blocks": [{"type": "text", "value": label}]}
                         for label in "ABCDE"],
        "publication_authorized": False,
    }
    (src / "question.json").write_text(json.dumps(question))
    (src / "reconstructed.html").write_text("original html")
    (src / "reconstructed.png").write_bytes(b"old screenshot")
    (src / "original.png").write_bytes(b"official image")
    (src / "auditor_prompt.txt").write_text("Compare")
    manifest = {"question_id": "test-q", "publication_authorized": False,
                "files_sha256": {p.name: digest(p) for p in src.iterdir()}}
    (src / "manifest.json").write_text(json.dumps(manifest))
    target = tmp_path / "mutated"
    result = mutate(src, target)
    assert result["removed_words"] >= 3
    assert not (target / "reconstructed.png").exists()
    assert (src / "reconstructed.png").exists()
    assert json.loads((src / "question.json").read_text()) == question
    assert (tmp_path / "mutated.ground_truth.json").is_file()
    with pytest.raises(ValueError, match="reconstructed.png"):
        verify(target)
    with pytest.raises(ValueError, match="Destino já existe"):
        mutate(src, target)
