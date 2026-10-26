import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "link_audit_to_fused.py"
spec = importlib.util.spec_from_file_location("audit_linker", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class LinkAuditTests(unittest.TestCase):
    def test_match_is_never_publication(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "pdf"
            source.write_bytes(b"official-test-pdf")
            import hashlib
            sha = hashlib.sha256(source.read_bytes()).hexdigest()
            report = {"results": [{"year": 2018, "sha256": sha,
                "selected_questions": [{"number": 95}]}]}
            data = [("2018.jsonl", 1, {"ano": 2018, "dia": 2,
                     "cor_prova": "AZUL", "posicao_prova": 95,
                     "id_unico_sistema": "test"})]
            result = module.match(report, data, {2018: source})
            self.assertEqual(result[0]["status"], "MATCHED_UNVERIFIED")
            self.assertFalse(result[0]["publication_authorized"])

    def test_duplicate_match_is_ambiguous(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "pdf"
            source.write_bytes(b"source")
            import hashlib
            sha = hashlib.sha256(source.read_bytes()).hexdigest()
            report = {"results": [{"year": 2024, "sha256": sha,
                "selected_questions": [{"number": 7}]}]}
            item = {"ano": 2024, "dia": 1, "cor_prova": "AZUL",
                    "posicao_prova": 7}
            result = module.match(report, [("a", 1, item), ("b", 1, item)],
                                  {2024: source})
            self.assertEqual(result[0]["status"], "AMBIGUOUS")

    def test_wrong_source_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "pdf"
            source.write_bytes(b"other")
            report = {"results": [{"year": 2019, "sha256": "a"*64,
                "selected_questions": [{"number": 117}]}]}
            with self.assertRaises(ValueError):
                module.match(report, [], {2019: source})

if __name__ == "__main__":
    unittest.main()
