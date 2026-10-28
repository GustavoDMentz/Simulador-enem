"""Unit checks for external TRI staging; does not require network access."""
import unittest
from scripts.stage_lindemann_tri import stage

HEADER = "CO_ITEM;SG_AREA;TX_GABARITO;NU_PARAM_A;NU_PARAM_B;NU_PARAM_C;IN_ITEM_ABAN\n"


class TestExternalTriStaging(unittest.TestCase):
    def test_deduplicates_same_item_across_booklets(self):
        line = "153930;LC;A;2.28024;0.18554;0.19951;0\n"
        items, issues = stage(HEADER + line + line, 2025)
        self.assertEqual(len(items), 1)
        self.assertEqual(issues, [])
        self.assertEqual(items[0]["status"], "EXTERNAL_UNVERIFIED")

    def test_excludes_conflicting_item(self):
        items, issues = stage(HEADER + "11;MT;B;1;0;0.2;0\n11;MT;C;1;0;0.2;0\n", 2024)
        self.assertEqual(items, [])
        self.assertTrue(any("conflicting" in i["reason"] for i in issues))

    def test_rejects_bad_values_and_annulled(self):
        items, issues = stage(HEADER + "12;CN;D;nan;0;0.2;0\n13;CN;B;1;0;0.2;1\n", 2025)
        self.assertFalse(items)
        self.assertEqual(len(issues), 2)


if __name__ == "__main__":
    unittest.main()
