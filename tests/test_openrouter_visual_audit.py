import json
import pytest

from scripts.openrouter_visual_audit import MODEL, parse_response, request_payload


def test_payload_contains_two_images(tmp_path):
    (tmp_path / "question.json").write_text('{"id":"q21"}')
    (tmp_path / "auditor_prompt.txt").write_text("Compare")
    for name in ("original.png", "reconstructed.png"):
        (tmp_path / name).write_bytes(b"png")
    payload = request_payload(tmp_path, 2048)
    assert payload["model"] == MODEL
    assert sum(part["type"] == "image_url"
               for part in payload["messages"][0]["content"]) == 2


def test_divergence_still_requires_human_review():
    data = {"choices": [{"finish_reason": "stop", "message": {"content": json.dumps({
        "status": "divergente",
        "issues": [{"type": "omissao", "location": "enunciado",
                    "description": "Trecho ausente"}],
        "explanation": "Texto final não corresponde"
    })}}]}
    result = parse_response(data, {"question_id": "q21", "manifest_sha256": "abc"})
    assert result["publication_authorized"] is False
    assert result["requires_human_review"] is True


def test_truncated_response_rejected():
    with pytest.raises(ValueError, match="incompleta"):
        parse_response({"choices": [{"finish_reason": "length"}]},
                       {"question_id": "q21", "manifest_sha256": "abc"})
