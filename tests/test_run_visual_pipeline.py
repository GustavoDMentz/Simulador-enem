"""Integração local com PDF sintético, sem rede ou banco."""
import importlib.util
import sys
from pathlib import Path

import fitz

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location("run_visual_pipeline", SCRIPTS / "run_visual_pipeline.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_pipeline_generates_report(tmp_path):
    pdf = tmp_path / "test.pdf"
    doc = fitz.open()
    page = doc.new_page(width=600, height=800)
    page.insert_text((30, 80), "QUESTÃO 1", fontsize=12)
    page.insert_text((30, 280), "QUESTÃO 3", fontsize=12)
    doc.save(pdf)
    doc.close()
    report = module.pipeline(pdf, tmp_path / "output", expected=3)
    assert report["question_numbers"] == [1, 3]
    assert report["missing_question_numbers"] == [2]
    assert report["candidate_count"] == 2
    assert report["requires_human_review"] is True
    assert (tmp_path / "output/quality-report.json").is_file()
    assert (tmp_path / "output/pages/index.html").is_file()
    assert (tmp_path / "output/questions/index.html").is_file()
