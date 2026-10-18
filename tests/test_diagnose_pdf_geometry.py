"""Testes sintéticos da leitura geométrica de alternativas."""
import importlib.util
from pathlib import Path
import fitz

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'diagnose_pdf_geometry.py'
spec = importlib.util.spec_from_file_location('diagnose_pdf_geometry', SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_five_options_from_pdf_lines():
    with fitz.open() as pdf:
        page = pdf.new_page()
        for i, letter in enumerate('ABCDE'):
            page.insert_text((35, 80 + i * 22), f'{letter} alternativa {letter}')
        result = module.analyze(page, list(page.rect))
        assert result['exact_ABCDE']
        assert len(result['candidate_lines']) == 5
        assert result['publication_authorized'] is False


def test_watermark_line_ignored():
    with fitz.open() as pdf:
        page = pdf.new_page()
        page.insert_text((35, 50), 'ENEM2024ENEM2024ENEM2024')
        page.insert_text((35, 80), 'A resposta')
        result = module.analyze(page, list(page.rect))
        assert result['sequence'] == 'A'


def test_incomplete_options_not_published():
    with fitz.open() as pdf:
        page = pdf.new_page()
        for i, letter in enumerate('ABCD'):
            page.insert_text((35, 80 + i * 22), f'{letter} alternativa')
        result = module.analyze(page, list(page.rect))
        assert not result['ABCDE_detected']
        assert result['publication_authorized'] is False
