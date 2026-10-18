"""Testes da triagem de evidências; nenhuma questão é aprovada."""
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from audit_enem_evidence import audit_batch


class AuditEvidenceTests(unittest.TestCase):
    def test_repaired_and_original_image_roots_and_manual_flag(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            exam = root / "2022-regular-d2-azul"
            review = exam / "review"
            enriched = exam / "enriched"
            images = enriched / "images"
            review.mkdir(parents=True)
            images.mkdir(parents=True)
            raw = b"original"
            composite = b"composite"
            (review / "q1.png").write_bytes(raw)
            (images / "q2.png").write_bytes(composite)
            def item(number, image, contents):
                return {
                    "id": f"q{number}", "original_number": number,
                    "image": image, "image_sha256": hashlib.sha256(contents).hexdigest(),
                    "extracted_text": f"QUESTÃO {number}\nA primeira\nB segunda\nC terceira\nD quarta\nE quinta",
                    "review_status": "pending",
                }
            payload = {
                "records": [item(1, "q1.png", raw), item(2, "images/q2.png", composite)],
                "continuation_integration": {"repaired_ids": ["q2"]},
            }
            (enriched / "question-review-enriched.json").write_text(json.dumps(payload))
            (images / "continuation-report.json").write_text(json.dumps({
                "results": [{"id": "q1", "status": "manual_review", "sequence": "A"}]
            }))
            result = audit_batch(root)
            self.assertEqual(result["total_candidates"], 2)
            self.assertEqual(result["flag_counts"]["unresolved_column_continuation"], 1)
            self.assertEqual(result["flag_counts"]["composite_requires_visual_check"], 1)
            self.assertTrue(all(r["image_hash_verified"] for r in result["records"]))
            self.assertTrue(all(not r["publication_authorized"] for r in result["records"]))

    def test_missing_image_is_flagged(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            enriched = root / "2017-regular-d2-azul" / "enriched"
            enriched.mkdir(parents=True)
            (enriched / "question-review-enriched.json").write_text(json.dumps({
                "records": [{
                    "id": "q1", "original_number": 91, "image": "missing.png",
                    "image_sha256": "0" * 64, "extracted_text": "",
                    "review_status": "pending",
                }]
            }))
            result = audit_batch(root)
            self.assertIn("image_missing_or_hash_mismatch", result["records"][0]["flags"])
            self.assertFalse(result["publication_authorized"])


if __name__ == "__main__":
    unittest.main()
