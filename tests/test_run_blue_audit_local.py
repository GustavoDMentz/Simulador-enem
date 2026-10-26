"""Local official source inventory tests (no network or database)."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from run_blue_audit_local import inspect_sources

class LocalInventoryTests(unittest.TestCase):
    def test_missing_sources_are_counted(self):
        with tempfile.TemporaryDirectory() as d:
            rows=inspect_sources(Path(d))
            self.assertEqual(len(rows),18)
            self.assertEqual(sum(x[k]["status"]=="MISSING" for x in rows
                                 for k in ("prova","gabarito")),36)

    def test_magic_bytes_not_equivalent_to_verified_provenance(self):
        with tempfile.TemporaryDirectory() as d:
            folder=Path(d)
            (folder/"2018-regular-d2-azul.pdf").write_bytes(b"%PDF-1.7\nsynthetic")
            rows=inspect_sources(folder)
            item=next(x for x in rows if x["ano"]==2018 and x["dia"]==2)
            self.assertEqual(item["prova"]["status"],"PRESENT_UNVERIFIED_ORIGIN")
            self.assertEqual(len(item["prova"]["sha256"]),64)
            self.assertEqual(item["gabarito"]["status"],"MISSING")

    def test_invalid_header_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            folder=Path(d)
            (folder/"2017-regular-d1-azul.pdf").write_bytes(b"not a pdf")
            rows=inspect_sources(folder)
            self.assertEqual(rows[0]["prova"]["status"],"INVALID_HEADER")

if __name__=="__main__":
    unittest.main()
