"""0.10.227 : jugement aveugle au taux de base."""
import unittest

import banc_a as ba
import banc_aveugle as bv

X = {"titre": "Will there be more 'Protests' in Chile…", "criteres": "c", "contexte": "ctx"}
VUE = {"frequence": 0.237, "classe_de_reference": "classe", "calcul": "calcul secret"}


class TestAveugle(unittest.TestCase):
    def test_consigne_sans_b(self):
        s = bv.consigne_aveugle(X, VUE, [{"date": "2026-09-01", "valeur": 12}], "recherche", "2026-09-27")
        self.assertNotIn("TAUX DE BASE", s)
        self.assertNotIn("0.237", s)
        self.assertNotIn("calcul secret", s)
        self.assertNotIn("Pars du taux de base", s)
        self.assertIn("2026-09-01 : 12", s)                 # la série brute reste
        self.assertIn("Juge d'après les données", s)
        v = ba.consigne_a(X, VUE, [], "recherche", "2026-09-27")
        self.assertIn("0.237", v)

    def test_resume(self):
        ls = [{"question_id": f"fb:2026-09-27:acled:q{i}:x", "jeu": "2026-09-27", "ordre": [i, "2026-09-27"],
               "issue": i % 2, "p_B": 0.3, "p_voit": 0.32, "p_aveugle": 0.6 if i % 2 else 0.2} for i in range(20)]
        r = bv.resumer(ls)
        self.assertEqual(r["n"], 20)
        self.assertLess(r["distance_a_B"]["A_voit"], r["distance_a_B"]["A_aveugle"])
        self.assertLess(r["C_aveugle"], r["A_voit"])
        self.assertTrue(r["critere"]["verdict"].startswith("en attente"))


if __name__ == "__main__":
    unittest.main()
