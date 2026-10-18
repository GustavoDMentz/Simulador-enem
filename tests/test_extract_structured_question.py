import json

import pymupdf
import pytest

from scripts.extract_structured_question import extract


def test_extract_native_text_and_image(tmp_path):
    pdf = tmp_path / "exam.pdf"
    doc = pymupdf.open()
    page = doc.new_page(width=400, height=500)
    page.insert_text((30, 50), "QUESTAO EXEMPLO")
    for i, letter in enumerate("ABCDE"):
        page.insert_text((30, 100 + i * 45), f"{letter} alternativa")
    doc.save(pdf)
    doc.close()
    import hashlib
    digest = hashlib.sha256(pdf.read_bytes()).hexdigest()
    spec = {"id": "sample", "source_sha256": digest, "page": 1,
            "blocks": [{"type": "text", "bbox": [20, 30, 200, 60]}],
            "alternatives": [
                {"label": letter, "blocks": [{"type": "image" if i == 0 else "text",
                    "bbox": [20, 80 + i * 45, 220, 115 + i * 45]}]}
                for i, letter in enumerate("ABCDE")
            ]}
    out = tmp_path / "question.json"
    result = extract(pdf, spec, out)
    assert result["publication_authorized"] is False
    assert result["blocks"][0]["value"] == "QUESTAO EXEMPLO"
    assert len(result["alternatives"]) == 5
    assert (tmp_path / result["alternatives"][0]["blocks"][0]["value"]).is_file()
    assert json.loads(out.read_text())["review_status"] == "pending"


def test_rejects_wrong_pdf_hash(tmp_path):
    pdf = tmp_path / "exam.pdf"
    doc = pymupdf.open()
    doc.new_page()
    doc.save(pdf)
    doc.close()
    with pytest.raises(ValueError, match="SHA-256"):
        extract(pdf, {"id": "x", "source_sha256": "wrong"}, tmp_path / "out.json")
