"""Bot 0.10.29 : puissance du test C contre B selon le lecteur (sans appel de modèle)."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import puissance_lecteur as pl  # noqa: E402


class Tests(unittest.TestCase):
    def test_monde_et_lecteurs(self):
        qs = pl.monde(12, graine=3)
        self.assertEqual(len(qs), 12)
        self.assertTrue(all(0 < q["p_vrai"] < 1 and q["cible"] not in q["vraies"] for q in qs))
        nul = pl.simuler({"sens_F": 0, "sens_f": 0, "fp_F": 0, "fp_f": 0}, qs)
        self.assertTrue(all(abs(g) < 1e-9 for g in nul))           # lecteur aveugle : C = B, gain nul
        self.assertEqual(len(pl.simuler(pl.SCENARIOS["parfait"], qs)), 12)


if __name__ == "__main__":
    unittest.main()
