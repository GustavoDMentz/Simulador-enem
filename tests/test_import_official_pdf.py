"""Testes locais do importador de PDFs oficiais."""
import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "import_official_pdf.py"
spec = importlib.util.spec_from_file_location("import_official_pdf", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_import_and_manifest(tmp_path):
    source = tmp_path / "original.pdf"
    source.write_bytes(b"%PDF-1.7\nexample")
    result = module.import_pdf(year=2025, day=1, color="Azul",
                               output=tmp_path / "sources", source_path=source)
    assert result["size_bytes"] == len(source.read_bytes())
    target = tmp_path / "sources/2025/dia1/azul/prova.pdf"
    assert target.read_bytes() == source.read_bytes()
    assert (target.parent / "source.json").is_file()


def test_refuses_overwrite(tmp_path):
    source = tmp_path / "original.pdf"
    source.write_bytes(b"%PDF-1.7\nexample")
    kwargs = dict(year=2025, day=1, color="azul",
                  output=tmp_path / "sources", source_path=source)
    module.import_pdf(**kwargs)
    with pytest.raises(FileExistsError):
        module.import_pdf(**kwargs)


def test_invalid_pdf_is_not_persisted(tmp_path):
    source = tmp_path / "invalid.pdf"
    source.write_bytes(b"not a PDF")
    with pytest.raises(ValueError, match="cabeçalho PDF"):
        module.import_pdf(year=2025, day=1, color="azul",
                          output=tmp_path / "sources", source_path=source)
    assert not (tmp_path / "sources/2025/dia1/azul/prova.pdf").exists()


def test_only_official_https_domains():
    assert module.official_url("https://download.inep.gov.br/educacao_basica/enem/provas.pdf")
    assert not module.official_url("http://download.inep.gov.br/teste.pdf")
    assert not module.official_url("https://gov.br.example.com/teste.pdf")
