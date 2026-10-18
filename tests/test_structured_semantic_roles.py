import pytest
from scripts.render_structured_question import render


def sample():
    return {
        "id": "q21",
        "blocks": [
            {"type": "text", "role": "titulo", "value": "TEXTO I"},
            {"type": "image", "role": "imagem", "value": "assets/goeldi.png"},
            {"type": "text", "role": "credito", "value": "Fonte da imagem"},
            {"type": "text", "role": "enunciado", "value": "Qual obra?"},
        ],
        "alternatives": [
            {"label": c, "blocks": [
                {"type": "image", "role": "imagem", "value": f"assets/{c}.png"},
                {"type": "text", "role": "texto", "value": f"Artista {c}"},
            ]} for c in "ABCDE"
        ],
    }


def test_semantic_blocks_have_distinct_markup():
    html = render(sample())
    assert '<h3 class="block-titulo">TEXTO I</h3>' in html
    assert '<p class="block-credito">Fonte da imagem</p>' in html
    assert '<p class="block-enunciado">Qual obra?</p>' in html
    assert 'class="block-imagem"' in html
    assert html.count('class="letter"') == 5


def test_rejects_unknown_role():
    question = sample()
    question["blocks"][0]["role"] = "javascript"
    with pytest.raises(ValueError, match="Papel"):
        render(question)


def test_semantic_text_escaped():
    question = sample()
    question["blocks"][0]["value"] = "<script>alert(1)</script>"
    result = render(question)
    assert "<script>" not in result
    assert "&lt;script&gt;" in result
