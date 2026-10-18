"""Diagnóstico de alternativas: não confundir sequência com aprovação."""
import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "diagnose_options.py"
spec = importlib.util.spec_from_file_location("diagnose_options", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def item(text):
    return {"id": "q6", "original_number": 6, "page": 5, "extracted_text": text}


def test_exact_five_options():
    text = "QUESTÃO 06\n" + "\n".join(f"{k} resposta {k}" for k in "ABCDE")
    result = module.diagnose(item(text))
    assert result["category"] == "exact_ABCDE"
    assert result["safe_to_publish"] is False


def test_extra_marker_before_options_is_not_auto_approved():
    text = "A legenda\n" + "\n".join(f"{k} resposta {k}" for k in "ABCDE")
    result = module.diagnose(item(text))
    assert result["category"] == "ABCDE_with_extra_markers"
    assert result["flags"] == ["extra_option_like_lines"]


def test_missing_e_is_reported():
    result = module.diagnose(item("\n".join(f"{k} resposta" for k in "ABCD")))
    assert result["category"] == "ABCD_without_E"


def test_disordered_options_reported():
    result = module.diagnose(item("A primeiro\nC terceiro\nB segundo"))
    assert result["category"] == "missing_or_disordered_options"


def test_watermark_does_not_generate_options():
    result = module.diagnose(item("ENEM2024" * 20 + "\nQUESTÃO 06"))
    assert result["detected_sequence"] == ""
