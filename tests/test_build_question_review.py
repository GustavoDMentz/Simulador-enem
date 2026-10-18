"""Teste da fila de revisão, sem acesso a rede ou banco."""
import importlib.util
from pathlib import Path

import fitz

SCRIPT = Path(__file__).resolve().parents[1] / "scripts"


def load(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPT / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_review_queue_never_approves_or_invents_answers(tmp_path):
    segment = load("segment_question_candidates")
    review = load("build_question_review")
    pdf = tmp_path / "prova.pdf"
    doc = fitz.open()
    page = doc.new_page(width=600, height=800)
    page.insert_text((35, 80), "QUESTÃO 01")
    page.insert_text((35, 100), "Texto de teste")
    doc.save(pdf)
    doc.close()
    candidates = tmp_path / "candidates"
    segment.run(pdf, candidates, dpi=72)
    result = review.build_review(pdf, candidates / "candidates.json",
                                 tmp_path / "review", year=2024, day=1, color="azul")
    assert result["candidates"] == 1
    assert result["pending_review"] == 1
    import json
    record = json.loads((tmp_path / "review/question-review.json").read_text())["records"][0]
    assert record["review_status"] == "pending"
    assert record["correct_option"] is None
    assert record["alternatives"] is None
    assert record["exam"]["source_sha256"]
    assert (tmp_path / "review/review.html").exists()
