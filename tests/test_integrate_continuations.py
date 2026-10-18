"""A integração não altera a fila original e mantém proveniência."""
import importlib.util
import json
from pathlib import Path
import sys
import pymupdf

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location("integrate_continuations", SCRIPTS / "integrate_continuations.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_integrates_without_mutating_original(tmp_path):
    pdf_path = tmp_path / "exam.pdf"
    with pymupdf.open() as pdf:
        page = pdf.new_page(width=600, height=800)
        page.insert_text((35, 650), "QUESTÃO 7")
        page.insert_text((35, 680), "Enunciado")
        for index, letter in enumerate("ABCDE"):
            page.insert_text((335, 80 + index * 24), f"{letter} alternativa")
        page.insert_text((335, 300), "QUESTÃO 8")
        pdf.save(pdf_path)
    import hashlib
    sha = hashlib.sha256(pdf_path.read_bytes()).hexdigest()
    review = tmp_path / "question-review.json"
    data = {"source_sha256": sha, "records": [{
        "id": "q007", "original_number": 7, "page": 1,
        "bbox": [0, 640, 300, 800], "image": "old.png",
        "image_sha256": "old-sha", "extracted_text": "old",
        "review_status": "pending", "review_reasons": [],
    }]}
    review.write_text(json.dumps(data), encoding="utf-8")
    before = review.read_bytes()
    result = module.integrate(pdf_path, review, tmp_path / "enriched")
    assert result["repaired"] == 1
    assert review.read_bytes() == before
    enriched = json.loads(Path(result["output"]).read_text())
    item = enriched["records"][0]
    assert item["original_crop"]["image"] == "old.png"
    assert item["review_status"] == "pending"
    assert len(item["source_segments"]) == 2
    assert (tmp_path / "enriched" / item["image"]).is_file()
    assert enriched["continuation_integration"]["publication_authorized"] is False
