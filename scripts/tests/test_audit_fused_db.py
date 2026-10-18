import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / "audit_fused_db.py"
spec = importlib.util.spec_from_file_location("audit_fused_db", SOURCE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class DBTests(unittest.TestCase):
    def run_case(self, rows):
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / "sample.jsonl").write_text(
                "\n".join(json.dumps(x) for x in rows), encoding="utf-8")
            return module.audit(folder)

    def example(self):
        return {"id_unico_sistema": "2019_AZUL_D2_Q117", "ano": 2019,
            "dia": 2, "cor_prova": "AZUL", "posicao_prova": 117,
            "co_item": 1234, "area_conhecimento": "CN", "gabarito_oficial": "A",
            "in_item_aban": 0, "parametros_tri": {
                "a_discriminacao": 1.2, "b_dificuldade": -0.1, "c_chute": 0.2},
            "conteudo": {"alternativas": dict.fromkeys("ABCDE", "Texto")}}

    def test_valid(self):
        self.assertTrue(self.run_case([self.example()])["ok"])

    def test_duplicate(self):
        result = self.run_case([self.example(), self.example()])
        codes = [x["code"] for x in result["issues"]]
        self.assertIn("DUPLICATE_ID", codes)
        self.assertIn("DUPLICATE_PROOF_POSITION", codes)

    def test_missing_tri(self):
        record = self.example()
        record["parametros_tri"] = None
        self.assertIn("MISSING_TRI", [i["code"] for i in self.run_case([record])["issues"]])

    def test_missing_gabarito(self):
        record = self.example()
        record["gabarito_oficial"] = None
        self.assertIn("MISSING_OR_INVALID_KEY", [i["code"] for i in self.run_case([record])["issues"]])

    def test_empty_fails(self):
        self.assertFalse(self.run_case([])["ok"])

if __name__ == "__main__":
    unittest.main()
