"""Testes do cruzamento de gabaritos por identidade e proveniência."""
import importlib.util
import json
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "reconcile_answer_key.py"
spec = importlib.util.spec_from_file_location("reconcile_answer_key", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def key():
    return {
        "exam": {"year": 2024, "application": "regular", "day": 1, "color": "azul"},
        "source": {"url": "https://example.org/gabarito.pdf", "sha256": "a" * 64,
                   "verification_status": "verified"},
        "answers": [{"number": 1, "language_variant": "ingles", "answer": "B"},
                    {"number": 1, "language_variant": "espanhol", "answer": "C"},
                    {"number": 6, "language_variant": None, "answer": "D"}],
    }


def record(n=6, variant=None, correct=None):
    return {"id": f"q{n}-{variant}", "original_number": n,
            "language_variant": variant, "correct_option": correct,
            "exam": {"year": 2024, "application": "regular", "day": 1, "color": "azul"}}


def run(tmp_path, records, manifest=None):
    source = tmp_path / "review.json"
    source.write_text(json.dumps({"source_sha256": "b" * 64, "records": records}))
    gabarito = tmp_path / "key.json"
    gabarito.write_text(json.dumps(manifest or key()))
    return module.reconcile(source, gabarito, tmp_path / "result.json")


def test_distinct_languages_match_separately(tmp_path):
    result = run(tmp_path, [record(1, "ingles"), record(1, "espanhol")])
    assert [r["answer"] for r in result["results"]] == ["B", "C"]
    assert result["summary"] == {"matched": 2}
    assert result["publication_authorized"] is False


def test_language_missing_never_matches(tmp_path):
    result = run(tmp_path, [record(1)])
    assert result["results"][0]["status"] == "needs_review"


def test_existing_answer_conflict_blocks(tmp_path):
    result = run(tmp_path, [record(6, correct="A")])
    assert result["results"][0]["status"] == "blocked"
    assert result["results"][0]["answer"] is None


def test_unverified_source_never_matches(tmp_path):
    manifest = key()
    manifest["source"]["verification_status"] = "pending"
    result = run(tmp_path, [record(6)], manifest)
    assert result["results"][0]["status"] == "needs_review"


def test_duplicate_key_entries_rejected(tmp_path):
    manifest = key()
    manifest["answers"].append(manifest["answers"][0])
    with pytest.raises(ValueError, match="duplicada"):
        run(tmp_path, [record(1, "ingles")], manifest)


def test_wrong_booklet_blocks(tmp_path):
    item = record(6)
    item["exam"]["color"] = "amarelo"
    result = run(tmp_path, [item])
    assert result["results"][0]["status"] == "blocked"


def test_annulled_question_requires_review(tmp_path):
    manifest = key()
    manifest["answers"][2]["answer"] = "ANULADA"
    result = run(tmp_path, [record(6)], manifest)
    assert result["results"][0]["status"] == "needs_review"
