"""Bot 0.10.30 : apprentissage des λ en ombre (skill §47)."""
from __future__ import annotations

import math
import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import apprentissage_lambda as al  # noqa: E402


def donnees(n, vrai, graine=1):
    rnd = random.Random(graine)
    rows = []
    for _ in range(n):
        f = rnd.uniform(0.05, 0.5)
        x = {c: rnd.choice([0, 0, 1, 1, 2]) for c in al.CLASSES}
        z = math.log(f / (1 - f)) + sum(x[c] * math.log(vrai[c]) for c in al.CLASSES)
        rows.append({"source": "test", "question_id": "q", "f": f, "n": x,
                     "y": 1 if rnd.random() < 1 / (1 + math.exp(-z)) else 0})
    return rows


class Tests(unittest.TestCase):
    def test_retrouve_les_vrais_lambda(self):
        vrai = {"F": 6.0, "M": 1.8, "f": 1.0, "I": 0.4}
        r = al.apprendre(donnees(4000, vrai))
        for c in al.CLASSES:
            lo, hi = r["intervalle_95"][c]
            self.assertTrue(lo <= vrai[c] <= hi or abs(r["lambda_appris"][c] - vrai[c]) / vrai[c] < 0.15, (c, r))
        self.assertLess(r["perte_log_hors_echantillon"]["appris"], r["perte_log_hors_echantillon"]["stipules"])

    def test_peu_de_donnees_reste_pres_de_l_a_priori(self):
        r = al.apprendre(donnees(8, {"F": 20.0, "M": 1.8, "f": 1.2, "I": 0.556}))
        self.assertLess(abs(math.log(r["lambda_appris"]["F"] / r["lambda_stipules"]["F"])), 1.0)
        self.assertTrue(r["statut"].startswith("indicatif"))
        self.assertEqual(al.apprendre([])["statut"], "aucune question résolue avec lecture")


if __name__ == "__main__":
    unittest.main()
