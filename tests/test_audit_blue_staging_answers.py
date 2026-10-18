"""Synthetic tests: answer evidence must never certify or publish."""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from audit_blue_staging_answers import audit

class AnswerAuditTests(unittest.TestCase):
    def row(self, day=2, position=91, recorded="A", source=True):
        return {"ano": 2018, "dia": day, "posicao": position,
                "official_answer_pdf": self.pdf if source else None,
                "existing_records": [{"record": {"gabarito_oficial": recorded,
                                                   "id_unico_sistema": "synthetic"}}]}

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.pdf = str(Path(self.temp.name) / "official-gabarito.pdf")
        Path(self.pdf).write_bytes(b"synthetic PDF fixture bytes")

    def tearDown(self):
        self.temp.cleanup()

    @patch("audit_blue_staging_answers.extract_pdf")
    def test_match_is_not_certified(self, parser):
        parser.return_value = ({91: {"comum": "A"}}, [], 100)
        r = audit([self.row()])[0]
        self.assertEqual(r["status"], "ANSWER_TEXT_MATCH_UNVERIFIED")
        self.assertFalse(r["answer_verified"])
        self.assertFalse(r["publishable"])

    @patch("audit_blue_staging_answers.extract_pdf")
    def test_real_mismatch_is_reported(self, parser):
        parser.return_value = ({91: {"comum": "B"}}, [], 100)
        r = audit([self.row()])[0]
        self.assertEqual(r["status"], "ANSWER_DIVERGENCE")
        self.assertEqual(r["official_answer"], "B")
        self.assertEqual(r["recorded_answer"], "A")

    @patch("audit_blue_staging_answers.extract_pdf")
    def test_language_variants_not_guessed(self, parser):
        parser.return_value = ({1: {"ingles": "A", "espanhol": "B"}}, [], 100)
        r = audit([self.row(day=1, position=1)])[0]
        self.assertEqual(r["status"], "INCONCLUSIVE_LANGUAGE")
        self.assertFalse(r["answer_verified"])

    def test_missing_source_is_blocked(self):
        r = audit([self.row(source=False)])[0]
        self.assertEqual(r["status"], "SOURCE_MISSING")

if __name__ == "__main__":
    unittest.main()
