"""Testes básicos do segmentador usando um PDF sintético em memória."""
import importlib.util
from pathlib import Path

import fitz

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "segment_question_candidates.py"
spec = importlib.util.spec_from_file_location("segment_question_candidates", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_two_questions_same_column():
    doc = fitz.open()
    page = doc.new_page(width=600, height=800)
    page.insert_text((35, 80), "QUESTÃO 12", fontsize=12)
    page.insert_text((35, 280), "QUESTÃO 13", fontsize=12)
    headers = module.find_headers(page)
    assert [h["number"] for h in headers] == [12, 13]
    clips = module.segment_page(page, headers)
    assert len(clips) == 2
    assert clips[0]["bbox"][3] <= headers[1]["bbox"][1]
    assert all(c["column"] == "left" for c in clips)
    doc.close()


def test_right_column_does_not_cut_left_column():
    doc = fitz.open()
    page = doc.new_page(width=600, height=800)
    page.insert_text((35, 80), "QUESTÃO 1", fontsize=12)
    page.insert_text((335, 130), "QUESTÃO 2", fontsize=12)
    clips = module.segment_page(page, module.find_headers(page))
    assert len(clips) == 2
    assert clips[0]["bbox"][3] == 800
    assert clips[1]["column"] == "right"
    doc.close()


def test_non_header_is_ignored():
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((35, 80), "Na questão 15, considere...", fontsize=12)
    assert module.find_headers(page) == []
    doc.close()
