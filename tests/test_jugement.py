import unittest

import banc_jugement as bj


class T(unittest.TestCase):
    def test_formes(self):
        self.assertEqual(bj.forme("Will Trump win the 2028 election?"), "election")
        self.assertEqual(bj.forme("Will the Supreme Court hear the case before July?"), "justice")
        self.assertEqual(bj.forme("Will Bitcoin exceed $150k by June?"), "seuil")
        self.assertEqual(bj.forme("Will Iran and the US sign a deal before 2027?"), "echeance")
        self.assertEqual(bj.forme("Will GPT-6 be released?"), "autre")
        self.assertEqual(bj.tranche(10), "<=30")
        self.assertEqual(bj.tranche(200), ">90")

    def test_sans_fuite(self):
        xs = []
        for i in range(40):
            xs.append({"source": "metaculus", "id": str(i), "jeu": "2025-%02d-01" % (1 + i % 12), "titre": f"Will the {['alpha', 'bravo', 'charlie'][i % 3]} treaty be signed before deadline?",
                       "horizon": 60, "resolue_le": "2025-%02d-15" % (1 + i % 12), "issue": int(i % 3 == 0)})
        xs.append({"source": "metaculus", "id": "x", "jeu": "2026-02-01", "titre": "Will the alpha treaty be signed before deadline?",
                   "horizon": 60, "resolue_le": "2026-03-01", "issue": 1})
        bj.calculer(xs)
        self.assertGreater(xs[-1]["p_S"], xs[-1]["p_R1"])
        premier = xs[0]                          # aucune voisine résolue avant son jeu
        self.assertAlmostEqual(premier["p_S"], premier["p_R1"])
        r = bj.resumer(xs)
        self.assertIn("perte", r)


if __name__ == "__main__":
    unittest.main()
