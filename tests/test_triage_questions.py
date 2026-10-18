"""Testes da triagem automática conservadora."""
import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "triage_questions.py"
spec = importlib.util.spec_from_file_location("triage_questions", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def record():
    return {
        "id": "q006", "original_number": 6,
        "exam": {"source_sha256": "a" * 64},
        "extracted_text": "QUESTÃO 06\nEnunciado\nA) Um\nB) Dois\nC) Três\nD) Quatro\nE) Cinco",
        "image": "q006.png", "image_sha256": "b" * 64,
    }


def test_complete_text_is_not_automatically_approved():
    result = module.inspect(record(), source_hash="a" * 64,
                            duplicate_numbers=set(), images_root=None)
    assert result["checks"]["five_options_detected"]
    assert result["checks"]["question_header_found"]
    assert result["status"] == "needs_review"
    assert not result["automatic_approval"]


def test_missing_options_are_flagged():
    item = record()
    item["extracted_text"] = "QUESTÃO 06\nA) Um\nB) Dois"
    result = module.inspect(item, source_hash="a" * 64,
                            duplicate_numbers=set(), images_root=None)
    assert "options_missing_or_ambiguous" in result["flags"]


def test_source_hash_mismatch_blocks():
    result = module.inspect(record(), source_hash="c" * 64,
                            duplicate_numbers=set(), images_root=None)
    assert result["status"] == "blocked"


def test_image_hash_mismatch_blocks(tmp_path):
    (tmp_path / "q006.png").write_bytes(b"fake")
    result = module.inspect(record(), source_hash="a" * 64,
                            duplicate_numbers=set(), images_root=tmp_path)
    assert result["status"] == "blocked"
    assert "image_hash_mismatch" in result["flags"]


def test_duplicate_number_flagged():
    result = module.inspect(record(), source_hash="a" * 64,
                            duplicate_numbers={6}, images_root=None)
    assert "duplicate_number_or_language_variant" in result["flags"]
