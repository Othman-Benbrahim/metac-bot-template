"""0.10.230 : collecte ConflictForecast."""
import unittest

import collecte_conflictforecast as cf


class TestCF(unittest.TestCase):
    def test_tri(self):
        self.assertTrue(cf.garder("armed_conflict_3_2026-10.csv"))
        self.assertFalse(cf.garder("grid_risk_2026-10.csv"))
        self.assertFalse(cf.garder("readme.pdf"))
        self.assertEqual(cf.propre("Armed Conflict - 3.csv"), "Armed_Conflict_-_3.csv")


if __name__ == "__main__":
    unittest.main()
