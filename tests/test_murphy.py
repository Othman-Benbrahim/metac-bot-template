"""0.10.197 : diagramme de Murphy et valeur captée (lecture descriptive du Banc B)."""
import unittest

import numpy as np

import murphy as m


def lignes(n=200, graine=0):
    rng = np.random.default_rng(graine)
    out = []
    for i in range(n):
        y = int(rng.random() < 0.3)
        out.append({"question_id": f"q{i}", "source_question": "fred" if i % 2 else "dbnomics", "issue": y,
                    "p_B": 0.3, "parfait": float(y), "bruit": float(rng.random())})
    return out


class TestMurphy(unittest.TestCase):
    def test_brier_egale_integrale_des_regrets(self):
        p = np.array([0.1, 0.37, 0.8, 0.5]); y = np.array([0.0, 1.0, 1.0, 0.0])
        r = m.regret(p, y, m.GRILLE)
        integrale = 2 * r.mean(1)                       # grille régulière sur ]0, 1[
        np.testing.assert_allclose(integrale, (p - y) ** 2, atol=2e-3)

    def test_demi_action_au_seuil(self):
        r = m.regret(np.array([0.5]), np.array([1.0]), np.array([0.5]))
        self.assertAlmostEqual(float(r[0, 0]), 0.25)

    def test_ancres_prescience_et_taux_de_base(self):
        r = m.comparer(lignes(), {"B": lambda x: x["p_B"], "parfait": lambda x: x["parfait"]})
        c = r["comparaisons"]["parfait"]
        self.assertEqual(c["par_profil"]["uniforme (= Brier)"]["parfait"]["V"], 1.0)
        self.assertEqual(c["par_seuil"]["0.50"]["parfait"]["V"], 1.0)

    def test_bruit_pire_que_taux_de_base(self):
        r = m.comparer(lignes(400), {"B": lambda x: x["p_B"], "bruit": lambda x: x["bruit"]})
        v = r["comparaisons"]["bruit"]["par_profil"]["uniforme (= Brier)"]["bruit"]
        self.assertLess(v["V"], 0)
        self.assertLessEqual(v["ic95"][0], v["V"]); self.assertGreaterEqual(v["ic95"][1], v["V"])

    def test_bras_absent_ou_trop_peu(self):
        r = m.comparer(lignes(20), {"B": lambda x: x["p_B"], "x": lambda x: None})
        self.assertEqual(r["comparaisons"]["x"]["n"], 0)

    def test_tableau_et_banc_b(self):
        l = [dict(x, ombre_b_ar={"p": 0.4}, ombre_b_saison={"p": 0.2}) for x in lignes()]
        r = m.pour_banc_b(l)
        self.assertIn("B_AR", r["comparaisons"])
        self.assertIn("| précaution (θ moyen 0,1) |", m.tableau(r))

    def test_deterministe(self):
        a = m.comparer(lignes(), {"B": lambda x: x["p_B"], "bruit": lambda x: x["bruit"]})
        b = m.comparer(lignes(), {"B": lambda x: x["p_B"], "bruit": lambda x: x["bruit"]})
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()
