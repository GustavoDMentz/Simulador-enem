"""Inventário não deve inventar cor nem substituir cadastro existente."""
import importlib.util
import json
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "inventory_enem_pdfs.py"
spec = importlib.util.spec_from_file_location("inventory_enem_pdfs", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def test_inventory_preserves_existing_and_reports_missing(tmp_path):
    pdfs = tmp_path / "pdfs"
    pdfs.mkdir()
    (pdfs / "2023-regular-d2-azul.pdf").write_bytes(b"%PDF")
    (pdfs / "2022_PV_impresso_D1_CD1.pdf").write_bytes(b"%PDF")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"exams": [{
        "year": 2024, "day": 1, "color": "azul",
        "application": "regular", "pdf": "original.pdf"
    }]}))
    result = mod.generate(pdfs, manifest)
    assert len(result["exams"]) == 2
    assert len(result["missing"]) == 16
    assert len(result["unclassified_pdfs"]) == 1
    assert next(x for x in result["exams"] if x["year"] == 2024)["pdf"] == "original.pdf"


def test_ambiguous_same_day_not_auto_selected(tmp_path):
    (tmp_path / "2021-regular-d1-azul.pdf").touch()
    (tmp_path / "2021-regular-d1-rosa.pdf").touch()
    result = mod.generate(tmp_path, tmp_path / "manifest.json", include_existing=False)
    assert len(result["ambiguous"]) == 1
    assert not result["exams"]
