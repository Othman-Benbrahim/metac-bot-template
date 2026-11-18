import math
import unittest

import profil_erreurs as pe


class TProfil(unittest.TestCase):
    def test_deux_cotes_et_decomposition(self):
        paires = [(0.9, 1), (0.2, 1), (0.1, 0), (0.6, 0), (0.1, 0)]
        r = pe.profil(paires)
        self.assertAlmostEqual(r["perte_venue_des_oui"] + r["perte_venue_des_non"], r["perte_log"], places=3)
        self.assertEqual((r["rates_oui_sous_30"], r["fausses_alertes_non_sur_50"]), (1, 1))
        # Murphy : Brier = fiabilité − résolution + incertitude quand chaque classe est homogène en p
        self.assertAlmostEqual(r["brier"], r["fiabilite_plus_bas_mieux"] - r["resolution_plus_haut_mieux"]
                               + r["incertitude"], places=3)

    def test_le_piege_du_seul_cote_oui(self):
        toujours_oui = [(0.9, y) for y in [1] + [0] * 5]
        prudent = [(0.2, 1)] + [(0.1, 0)] * 5
        a, b = pe.profil(toujours_oui), pe.profil(prudent)
        self.assertLess(a["perte_venue_des_oui"], b["perte_venue_des_oui"])   # vu du seul côté « oui », il gagne
        self.assertGreater(a["perte_log"], b["perte_log"])                    # au total, il perd

    def test_memes_questions(self):
        ls = [{"issue": 1, "a": 0.5, "b": 0.6}, {"issue": 0, "a": 0.3, "b": None}]
        r = pe.profils(ls, {"A": "a", "B": "b"})
        self.assertEqual((r["A"]["n"], r["B"]["n"]), (1, 1))


if __name__ == "__main__":
    unittest.main()
