import pytest

from scripts.apply_visual_review import annotate


def evidence():
    return {"records": [
        {"id": "q21", "evidence_class": "inconclusive"},
        {"id": "q108", "evidence_class": "inconclusive"},
    ]}


def test_separates_crop_from_options_and_never_approves():
    result = annotate(evidence(), {"annotations": [
        {"id": "q21", "crop_integrity": "incomplete",
         "options_format": "missing", "reviewer_note": "Recorte termina no Texto I"},
        {"id": "q108", "crop_integrity": "complete",
         "options_format": "visual", "reviewer_note": "Cinco gráficos A-E visíveis"},
    ]})
    assert result["publication_authorized"] is False
    assert result["summary"] == {"complete": 1, "incomplete": 1}
    assert result["records"][0]["requires_visual_review"] is True
    assert result["records"][1]["requires_visual_review"] is False
    assert all(r["publication_authorized"] is False for r in result["records"])


def test_unreviewed_is_not_approved():
    result = annotate(evidence(), {"annotations": []})
    assert result["summary"] == {"unreviewed": 2}
    assert all(r["requires_visual_review"] for r in result["records"])


@pytest.mark.parametrize("items", [
    [{"id": "missing", "crop_integrity": "complete", "options_format": "visual",
      "reviewer_note": "x"}],
    [{"id": "q21", "crop_integrity": "complete", "options_format": "wrong",
      "reviewer_note": "x"}],
    [{"id": "q21", "crop_integrity": "complete", "options_format": "visual",
      "reviewer_note": "x"}] * 2,
])
def test_rejects_invalid_annotations(items):
    with pytest.raises(ValueError):
        annotate(evidence(), {"annotations": items})
