"""Regressões do reparador de continuações entre colunas."""
import importlib.util
from pathlib import Path

import pymupdf

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "repair_column_continuations.py"
spec = importlib.util.spec_from_file_location("repair_column_continuations", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def make_page(pdf):
    page = pdf.new_page(width=600, height=800)
    page.insert_text((35, 650), "QUESTÃO 7", fontsize=12)
    page.insert_text((35, 680), "Texto da questão 7")
    for i, letter in enumerate("ABCDE"):
        page.insert_text((335, 80 + i * 24), f"{letter} alternativa {letter}")
    page.insert_text((335, 300), "QUESTÃO 8", fontsize=12)
    page.insert_text((335, 330), "Texto da questão 8")
    return page


def test_repair_skips_own_header_and_generates_image(tmp_path):
    with pymupdf.open() as pdf:
        make_page(pdf)
        record = {
            "id": "q007", "original_number": 7, "page": 1,
            "bbox": [0, 640, 300, 800],
        }
        result = module.repair(pdf, record, tmp_path)
        assert result is not None
        assert result["status"] == "candidate_for_review"
        assert result["sequence_in_right_segment"] == "ABCDE"
        assert (tmp_path / "q007-continuation.png").is_file()
        assert result["publication_authorized"] is False


def test_repair_rejects_later_left_header(tmp_path):
    with pymupdf.open() as pdf:
        page = make_page(pdf)
        page.insert_text((35, 735), "QUESTÃO 9", fontsize=12)
        record = {
            "id": "q007", "original_number": 7, "page": 1,
            "bbox": [0, 640, 300, 800],
        }
        assert module.repair(pdf, record, tmp_path) is None


def test_repair_rejects_right_column_question(tmp_path):
    with pymupdf.open() as pdf:
        make_page(pdf)
        record = {
            "id": "q008", "original_number": 8, "page": 1,
            "bbox": [300, 290, 600, 800],
        }
        assert module.repair(pdf, record, tmp_path) is None
