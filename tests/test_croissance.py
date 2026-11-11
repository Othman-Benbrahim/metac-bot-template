"""Bot 0.10.19 : taux de base d'un seuil de NIVEAU sur une série en croissance (cas FYONET du 2026-11-11)."""
from __future__ import annotations

import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import alphabet_compte as ac  # noqa: E402

FYONET = [1789, 1863, 2011, 2160, 2293, 2472, 2655, 2729, 2983, 3518, 3457, 3603, 3537, 3455, 3506, 3692, 3853, 3982,
          4109, 4447, 6554, 6822, 6273, 6135, 6752, 7010, 7396]


class Tests(unittest.TestCase):
    def test_fyonet(self):
        pts = [{"date": f"{2000 + i}-09-30", "valeur": x * 1000} for i, x in enumerate(FYONET)]
        r = ac.compter({"points": pts, "debut": "2000-01-01", "date_limite": "2026-11-10"}, 709, "atteint", 8050000, ">",
                       nature="niveau")
        self.assertEqual(r["methode"], "bootstrap_pas_relatifs")
        self.assertTrue(0.4 < r["frequence"] < 0.75)          # la tendance (≈ +4,5 %/an) atteint le seuil une fois sur deux

    def test_marche_aleatoire_inchangee(self):
        rnd = random.Random(3)
        v, x = [], 100.0
        for i in range(60):
            x += rnd.gauss(0, 1)
            v.append((None, x))
        self.assertFalse(ac.croissance(v))


if __name__ == "__main__":
    unittest.main()
