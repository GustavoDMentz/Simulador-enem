"""Regression checks for the conservative official TRI importer."""
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / 'scripts/import_official_tri.py'

class TriImportTests(unittest.TestCase):
    def run_case(self, records):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            (root/'scripts').mkdir()
            (root/'data/blue-published').mkdir(parents=True)
            (root/'scripts/import_official_tri.py').write_text(SCRIPT.read_text())
            question = {'ano':2023,'id_unico_sistema':'2023_AZUL_D1_Q01','co_item':123,'area_conhecimento':'LC','gabarito_oficial':'B','scoring_enabled':True}
            (root/'data/blue-published/questions.jsonl').write_text(json.dumps(question)+'\n')
            header='CO_ITEM;SG_AREA;TX_GABARITO;IN_ITEM_ABAN;NU_PARAM_A;NU_PARAM_B;NU_PARAM_C\n'
            (root/'items.csv').write_text(header+''.join(records),encoding='latin-1')
            result=subprocess.run([sys.executable,str(root/'scripts/import_official_tri.py'),str(root/'items.csv'),'--year','2023','--output',str(root/'report.json')],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            return json.loads((root/'report.json').read_text())

    def test_valid_official_candidate(self):
        r=self.run_case(['123;LC;B;0;1,5;-0,2;0,2\n'])
        self.assertEqual(r['counts'],{'matched':1,'blocked':0})
        self.assertTrue(r['matched'][0]['review_required'])

    def test_conflicting_duplicate_is_blocked(self):
        r=self.run_case(['123;LC;B;0;1,5;-0,2;0,2\n','123;LC;B;0;1,7;-0,2;0,2\n'])
        self.assertEqual(r['counts']['matched'],0)

    def test_wrong_answer_is_blocked(self):
        r=self.run_case(['123;LC;C;0;1,5;-0,2;0,2\n'])
        self.assertEqual(r['counts']['blocked'],1)

    def test_abandoned_item_is_blocked(self):
        r=self.run_case(['123;LC;B;1;1,5;-0,2;0,2\n'])
        self.assertEqual(r['counts']['matched'],0)

if __name__=='__main__': unittest.main()
