"""Regression tests for the 2024 D2 official-key quarantine."""
import json
import tempfile
import unittest
from pathlib import Path
from scripts.check_2024_d2_regular_key import OFFICIAL, check

class OfficialKeyGateTest(unittest.TestCase):
    def write(self, directory, values):
        path=Path(directory)/"fused.jsonl"
        path.write_text("".join(json.dumps({"posicao_prova":n,"gabarito_oficial":value})+"\n"
                                for n,value in values.items()),encoding="utf-8")
        return path

    def test_correct_regular_key_passes(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(check(self.write(directory,OFFICIAL)),[])

    def test_reapplication_answer_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            values=dict(OFFICIAL)
            values[93]="D"
            values[129]="B"
            errors=check(self.write(directory,values))
            self.assertEqual({e["position"] for e in errors},{93,129})

    def test_missing_position_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            values=dict(OFFICIAL)
            del values[93]
            with self.assertRaises(ValueError):
                check(self.write(directory,values))

if __name__=="__main__":
    unittest.main()
