"""0.10.39 : gain de C sur B selon la marge de B, et partition de Murphy."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import score_registre as sr  # noqa: E402


class Tests(unittest.TestCase):
    def test_marge(self):
        app = [({"A": 0.5, "B": 0.5, "C": 0.8}, 1), ({"A": 0.5, "B": 0.1, "C": 0.1}, 0),
               ({"A": 0.5, "B": 0.3, "C": 0.2}, 0), ({"A": 0.5, "B": 0.6, "C": 0.9}, 1),
               ({"A": 0.5, "B": 0.2, "C": 0.2}, 0), ({"A": 0.5, "B": 0.7, "C": 0.6}, 1)]
        m = sr.marge_B(app)
        self.assertEqual(m["n"], 6)
        self.assertEqual(sum(v["n"] for v in m["par_tiers_de_marge"].values()), 6)
        self.assertGreater(m["gain_normalise_hake_agrege"], 0)
        self.assertGreater(m["par_tiers_de_marge"]["marge_forte"]["gain_log_C_sur_B"], 0)
        pm = sr.partition_murphy([(p["C"], y) for p, y in app])
        self.assertAlmostEqual(pm["fiabilite"] - pm["resolution"] + pm["incertitude"], pm["brier"], delta=0.02)
        self.assertIsNone(sr.partition_murphy([(0.5, 1)]))
        self.assertIsNone(sr.marge_B(app[:2]))


if __name__ == "__main__":
    unittest.main()
