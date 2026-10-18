"""Testa a barreira de publicação, sem banco nem rede."""
import importlib.util
import json
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "export_reviewed_questions.py"
spec = importlib.util.spec_from_file_location("export_reviewed_questions", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def example_record():
    return {
        "id": "2024-regular-d1-azul-q006-p004",
        "exam": {"year": 2024, "application": "regular", "day": 1,
                 "color": "azul", "source_sha256": "a" * 64},
        "original_number": 6, "page": 4, "bbox": [0, 0, 200, 200],
        "image": "page_004_q006_left.png", "image_sha256": "b" * 64,
        "stem": "Qual é a resposta?",
        "alternatives": dict(zip("ABCDE", ["Um", "Dois", "Três", "Quatro", "Cinco"])),
        "correct_option": "B", "answer_key_source": "Gabarito oficial INEP",
        "reviewer": "Revisor", "reviewed_at": "2026-10-17",
        "language_variant": None, "review_status": "approved",
    }


def test_pending_never_exports(tmp_path):
    item = example_record()
    item["review_status"] = "pending"
    source = tmp_path / "review.json"
    source.write_text(json.dumps({"source_sha256": "a" * 64, "records": [item]}))
    target = tmp_path / "published.json"
    summary = module.export_approved(source, target)
    assert summary["approved"] == 0
    assert json.loads(target.read_text())["questions"] == []


def test_approved_exports_with_no_invented_tri(tmp_path):
    source = tmp_path / "review.json"
    source.write_text(json.dumps({"source_sha256": "a" * 64, "records": [example_record()]}))
    target = tmp_path / "published.json"
    summary = module.export_approved(source, target)
    assert summary["approved"] == 1
    assert json.loads(target.read_text())["questions"][0]["calibration"] is None


def test_incomplete_answer_key_rejected(tmp_path):
    item = example_record()
    item["answer_key_source"] = ""
    source = tmp_path / "review.json"
    source.write_text(json.dumps({"source_sha256": "a" * 64, "records": [item]}))
    summary = module.export_approved(source, tmp_path / "published.json")
    assert summary["approved"] == 0
    assert "fonte do gabarito ausente" in summary["rejections"][0]["reasons"]


def test_language_variant_required_for_first_five():
    item = example_record()
    item["original_number"] = 1
    _, errors = module.validate(item, source_sha256="a" * 64)
    assert "língua obrigatória nas questões 1–5 do primeiro dia" in errors


def test_duplicate_approved_item_is_error(tmp_path):
    item = example_record()
    source = tmp_path / "review.json"
    source.write_text(json.dumps({"source_sha256": "a" * 64, "records": [item, item]}))
    with pytest.raises(ValueError, match="duplicado"):
        module.export_approved(source, tmp_path / "published.json")
