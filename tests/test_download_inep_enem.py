"""Teste offline do parser do portal Inep."""
import importlib.util
from pathlib import Path

script = Path(__file__).resolve().parents[1] / "scripts" / "download_inep_enem.py"
spec = importlib.util.spec_from_file_location("download_inep_enem", script)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def test_discovers_regular_blue_and_skips_reapplication():
    html = """
    <h3>Aplicação regular</h3>
    <p>1º Dia – Caderno 1 – Azul – Aplicação Regular</p>
    <ul><li><a href="https://download.inep.gov.br/a.pdf">Prova</a></li>
    <li><a href="https://download.inep.gov.br/a-gb.pdf">Gabarito</a></li></ul>
    <p>2º Dia – Caderno 7 – Azul – Aplicação Regular</p>
    <ul><li><a href="https://download.inep.gov.br/b.pdf">Prova</a></li></ul>
    <h3>Reaplicação/PPL</h3>
    <p>1º Dia – Caderno 1 – Azul – Reaplicação/PPL</p>
    <li><a href="https://download.inep.gov.br/other.pdf">Prova</a></li>
    """
    found = mod.discover(html, mod.BASE + "2024")
    assert found[(1, "azul")]["prova"].endswith("/a.pdf")
    assert found[(1, "azul")]["gabarito"].endswith("/a-gb.pdf")
    assert found[(2, "azul")]["code"] == 7
    assert len(found) == 2


def test_rejects_untrusted_url():
    import pytest
    with pytest.raises(ValueError):
        mod.request("https://example.com/a.pdf")
