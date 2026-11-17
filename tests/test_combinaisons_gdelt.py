"""0.10.226 : questions fabriquées sur GDELT pour la grille de bon sens."""
import unittest
from datetime import date, timedelta

import combinaisons_gdelt as g


def jours(debut, n):
    return {(debut + timedelta(days=k)).isoformat() for k in range(n)}


class TestFabriquees(unittest.TestCase):
    def test_questions_issue_et_b_sans_fuite(self):
        couverts = jours(date(2024, 7, 1), 200)
        # 12 manifestations par jour jusqu'au 2024-10-01, puis 20 : hausse en octobre seulement
        serie = {j: (12 if j < "2024-10-01" else 20) for j in couverts}
        qs = g.questions({("manifestations", "XX"): serie}, couverts, set(), date(2024, 7, 1) + timedelta(days=199))
        par = {x["jeu"]: x for x in qs}
        self.assertEqual(par["2024-09-01"]["issue"], 0)
        self.assertEqual(par["2024-10-01"]["issue"], 1)
        self.assertEqual(par["2024-09-01"]["p_B"], 0.5)           # aucune histoire connue
        # au 2024-10-01, la question de septembre n'est pas encore résolue (fin le 2024-10-01) : elle compte
        self.assertEqual(par["2024-10-01"]["n_histoire"], 1)
        self.assertEqual(par["2024-11-01"]["n_histoire"], 2)
        self.assertAlmostEqual(par["2024-11-01"]["p_B"], (1 + 1) / (2 + 2))
        self.assertEqual(par["2024-10-01"]["famille"], "mobilisation")

    def test_jours_manquants_et_seuil(self):
        couverts = jours(date(2024, 7, 1), 200) - jours(date(2024, 9, 5), 5)
        serie = {j: 1 for j in couverts if int(j[-2:]) % 5 == 0}   # 6 par fenêtre : sous 10 (manifestations), pas sous 5 (force)
        qs = g.questions({("manifestations", "XX"): serie, ("force", "XX"): serie}, couverts, couverts,
                         date(2024, 7, 1) + timedelta(days=199))
        self.assertFalse([x for x in qs if x["type"] == "manifestations"])
        self.assertNotIn("2024-09-01", {x["jeu"] for x in qs})   # 5 jours manquants dans la fenêtre « après »
        self.assertTrue(all(x["famille"] == "strategique" for x in qs))


if __name__ == "__main__":
    unittest.main()
