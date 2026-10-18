"""Consolidated ENEM audit must be complete, conservative and non-publishing."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from consolidate_blue_audit import consolidate, POSITIONS

class MatrixTests(unittest.TestCase):
    def test_missing_evidence_never_publishes(self):
        records, summary=consolidate([],[],[])
        self.assertEqual(len(records),1620)
        self.assertEqual(summary["problem_counts"]["STAGING_MISSING"],1620)
        self.assertEqual(summary["publishable"],0)

    def test_mismatch_and_premature_flags(self):
        row={"ano":2018,"dia":2,"posicao":91,"status":"REUSE_EXISTING_UNVERIFIED",
             "publishable":True}
        text={"ano":2018,"dia":2,"posicao":91,"status":"SUSPECTED_TEXT_DIVERGENCE",
              "text_evidence":[{"status":"NOT_EXACT"}]}
        answer={"ano":2018,"dia":2,"posicao":91,"status":"ANSWER_DIVERGENCE"}
        records,_=consolidate([row],[text],[answer])
        item=next(x for x in records if (x["ano"],x["dia"],x["posicao"])==(2018,2,91))
        self.assertIn("ANSWER_DIVERGENCE",item["problems"])
        self.assertIn("UNEXPECTED_VERIFIED_FLAG",item["problems"])
        self.assertFalse(item["publishable"])

    def test_duplicate_is_detected(self):
        row={"ano":2018,"dia":2,"posicao":91}
        records,_=consolidate([row,row],[],[])
        item=next(x for x in records if x["ano"]==2018 and x["posicao"]==91)
        self.assertIn("DUPLICATE_POSITION_IN_EVIDENCE",item["problems"])

if __name__=="__main__":
    unittest.main()
