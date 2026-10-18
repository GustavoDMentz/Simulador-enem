import hashlib
import json

import pymupdf
import pytest

from scripts.audit_structured_question import package, validate_report


def test_packaging_and_manifest(tmp_path):
    pdf = tmp_path / "official.pdf"
    doc = pymupdf.open()
    doc.new_page()
    doc.save(pdf)
    doc.close()
    source_hash = hashlib.sha256(pdf.read_bytes()).hexdigest()
    assets = tmp_path / "source_assets"
    assets.mkdir()
    (assets / "a.png").write_bytes(b"image")
    img_hash = hashlib.sha256(b"image").hexdigest()
    question = {
        "id": "test-q1", "source_pdf_sha256": source_hash, "source_page": 1,
        "blocks": [{"type": "text", "value": "Texto"}],
        "alternatives": [{"label": c, "blocks": [
            {"type": "image", "value": "source_assets/a.png", "sha256": img_hash}
        ]} for c in "ABCDE"],
        "publication_authorized": False,
    }
    src = tmp_path / "question.json"
    src.write_text(json.dumps(question))
    out = tmp_path / "package"
    manifest = package(src, pdf, out)
    assert manifest["audit_status"] == "pending"
    assert len(manifest["files_sha256"]) == 5
    assert (out / "original.png").is_file()
    assert (out / "reconstructed.html").is_file()
    assert (out / "assets/image_000.png").is_file()


def test_wrong_pdf_hash_rejected(tmp_path):
    pdf = tmp_path / "official.pdf"
    pdf.write_bytes(b"not the official PDF")
    q = tmp_path / "q.json"
    q.write_text(json.dumps({
        "id": "x", "blocks": [{"type": "text", "value": "x"}],
        "alternatives": [{"label": c, "blocks": [{"type": "text", "value": c}]}
                         for c in "ABCDE"],
        "source_pdf_sha256": "wrong", "source_page": 1,
    }))
    with pytest.raises(ValueError, match="Hash"):
        package(q, pdf, tmp_path / "out")


def test_llm_report_never_approves():
    manifest = {"question_id": "q21", "manifest_sha256": "abc"}
    result = validate_report({"status": "conforme", "issues": [],
                              "explanation": "Comparação visual realizada"}, manifest)
    assert result["publication_authorized"] is False
    assert result["requires_human_review"] is True


def test_divergence_requires_issue():
    with pytest.raises(ValueError):
        validate_report({"status": "divergente", "issues": [],
                         "explanation": "Falha"}, {"question_id": "x", "manifest_sha256": "a"})
