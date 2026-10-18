import pytest
from scripts.render_structured_question import render

def sample():
    return {"id":"2017-q21", "blocks":[{"type":"text","value":"Enunciado"}],
            "alternatives":[{"label":c,"blocks":[{"type":"text","value":"Opção "+c}]} for c in "ABCDE"]}

def test_render_clean_layout():
    result=render(sample())
    assert "<main>" in result
    assert "background:white" in result
    assert result.count('class="letter"') == 5

def test_rejects_missing_alternative():
    q=sample()
    q["alternatives"].pop()
    with pytest.raises(ValueError):
        render(q)

def test_escapes_untrusted_content():
    q=sample()
    q["blocks"][0]["value"]="<script>alert(1)</script>"
    result=render(q)
    assert "<script>" not in result
    assert "&lt;script&gt;" in result
