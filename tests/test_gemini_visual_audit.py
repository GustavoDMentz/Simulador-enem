import json
import pytest

from scripts.gemini_visual_audit import parse_response, payload, verify


def test_verify_rejects_missing_screenshot(tmp_path):
    (tmp_path / "manifest.json").write_text(json.dumps({
        "files_sha256": {"original.png": "x"}, "publication_authorized": False}))
    (tmp_path / "original.png").write_bytes(b"wrong")
    with pytest.raises(ValueError, match="Hash"):
        verify(tmp_path)


def test_valid_report_remains_pending():
    manifest = {"question_id": "q21", "manifest_sha256": "abc"}
    data = {"candidates": [{"finishReason": "STOP", "content": {"parts": [{
        "text": json.dumps({"status": "conforme", "issues": [],
                            "explanation": "Comparação visual sem divergências"})
    }]}}]}
    result = parse_response(data, manifest, "gemini-test")
    assert result["publication_authorized"] is False
    assert result["requires_human_review"] is True


def test_truncated_response_rejected():
    with pytest.raises(ValueError, match="incompleta"):
        parse_response({"candidates": [{"finishReason": "MAX_TOKENS"}]},
                       {"question_id": "x", "manifest_sha256": "abc"}, "test")


def test_payload_contains_two_images(tmp_path):
    (tmp_path / "question.json").write_text('{"id":"q21"}')
    (tmp_path / "auditor_prompt.txt").write_text("Audite")
    for name in ("original.png", "reconstructed.png"):
        (tmp_path / name).write_bytes(b"png")
    data = payload(tmp_path, "gemini-test", 1024)
    parts = data["contents"][0]["parts"]
    assert len([p for p in parts if "inline_data" in p]) == 2
    assert data["generationConfig"]["responseMimeType"] == "application/json"
