"""Fail-closed regression checks for the independent PDF validator."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
try:
    import fitz
except ImportError:
    fitz = None

@unittest.skipUnless(fitz, "PyMuPDF must be installed for PDF validation")
class OfficialPDFAuditTests(unittest.TestCase):
    def test_independent_pdf_region_and_single_word_corruption(self):
        from validate_blue_official import PDFSource, compare_text, compare_candidate
        with tempfile.TemporaryDirectory() as tmp:
            pdf = Path(tmp) / "official.pdf"
            doc = fitz.open()
            page = doc.new_page(width=580, height=780)
            page.insert_text((38, 96), "QUESTÃO 101")
            page.insert_text((38, 125), "O deserto ocupa regioes muito secas")
            for i, label in enumerate("ABCDE"):
                page.insert_text((38, 160 + 27*i), f"{label} alternativa texto {label}")
            page.insert_text((299, 96), "QUESTÃO 102")
            page.insert_text((299, 125), "Outra questao diferente")
            doc.save(str(pdf))
            doc.close()
            source = PDFSource(pdf)
            try:
                official, err = source.get(101)
                self.assertIsNone(err)
                self.assertIn("deserto", official["tokens"])
                self.assertNotIn("outra", official["tokens"])
                self.assertEqual(source.get(103)[1], "HEADER_ABSENT")
                q = {"conteudo": {
                    "texto_base": "O deserto ocupa regioes muito secas",
                    "enunciado": "O deserto ocupa regioes muito secas",
                    "alternativas": {k: f"alternativa texto {k}" for k in "ABCDE"},
                    "metadados_visual": {"contem_imagem": False}}}
                status, checks, visuals = compare_text(q, official)
                self.assertEqual(status, "TEXT_MATCH_VISUAL_UNVERIFIED")
                self.assertTrue(visuals)
                q["conteudo"]["texto_base"] = "O dolar ocupa regioes muito secas"
                status, checks, _ = compare_text(q, official)
                self.assertEqual(status, "SUSPECTED_TEXT_DIVERGENCE")
                diff = checks[0]["evidence"]["token_differences"][0]
                self.assertEqual(diff["record"], "dolar")
                self.assertEqual(diff["pdf"], "deserto")
                q["conteudo"]["metadados_visual"] = {
                    "contem_imagem": True, "caminho_local_imagem": None}
                self.assertIn("DECLARED_IMAGE_WITHOUT_LOCAL_ASSET",
                              compare_text(q, official)[2])
                seg = {"option_segmentation": {
                    "options": {k: f"alternativa texto {k}" for k in "ABCDE"}}}
                self.assertEqual(compare_candidate(seg, official)[0],
                                 "CANDIDATE_OPTIONS_TEXT_MATCH_ONLY")
                seg["option_segmentation"]["options"]["E"] = "alternativa falsa E"
                self.assertEqual(compare_candidate(seg, official)[0],
                                 "CANDIDATE_OPTIONS_NEED_RECOVERY")
            finally:
                source.close()

if __name__ == "__main__":
    unittest.main()
