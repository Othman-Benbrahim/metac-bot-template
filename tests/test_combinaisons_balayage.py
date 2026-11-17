"""0.10.228 : balayage exhaustif des combinaisons comparé au hasard."""
import unittest
from datetime import date

import numpy as np

import combinaisons_balayage as bal


class TestBalayage(unittest.TestCase):
    def test_hostilites(self):
        par = {"EE": {"2026-03-01": 2, "2026-02-20": 1}}
        jours = {f"2026-{m:02d}-{d:02d}" for m in (1, 2, 3) for d in range(1, 29)}
        self.assertEqual(bal.hostilites(par, jours, "EE", date(2026, 3, 10)), 1)
        self.assertEqual(bal.hostilites(par, jours, "LV", date(2026, 3, 10)), 0)
        self.assertIsNone(bal.hostilites(par, set(), "EE", date(2026, 3, 10)))

    def test_evaluer(self):
        n = 80
        etat = np.zeros((n, len(bal.INDICATEURS)), dtype=np.int8)
        etat[:40, 0] = 1                                   # M10 présent sur la moitié
        typ = np.zeros(n, dtype=int)                       # manifestations
        explo = np.array([i % 2 == 0 for i in range(n)])
        pb = np.full(n, 0.3)
        y = np.array([1 if i < 40 else 0 for i in range(n)], dtype=float)   # M10 → toujours oui
        res = bal.evaluer(etat, typ, explo, pb, y, [(0,), (0, 1)])
        r = next(x for x in res if x["combi"] == (0,) and x["type"] == "manifestations")
        self.assertEqual((r["n_exploration"], r["n_confirmation"]), (20, 20))
        self.assertGreater(r["delta"], 0)
        self.assertLess(r["gain"], 0)
        r2 = next(x for x in res if x["combi"] == (0, 1) and x["type"] == "manifestations")
        self.assertNotIn("gain", r2)                       # M11 jamais présent : cellule vide


if __name__ == "__main__":
    unittest.main()
