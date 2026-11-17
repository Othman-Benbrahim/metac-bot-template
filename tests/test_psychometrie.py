import random
import unittest

import psychometrie_alphabet as pa


class T(unittest.TestCase):
    def test_statuts(self):
        rnd = random.Random(1)
        xs = []
        for i in range(200):
            y = int(rnd.random() < 0.3)
            notes = {c: {"note": rnd.randint(1, 4)} for c in pa.CARTES}
            t = 4 if y else rnd.choice([1, 2])
            notes["tendance"] = {"note": t}                                       # carte qui sait
            notes["freins"] = {"note": t}                                         # sens inversé : trompeuse
            xs.append({"issue": y, "forme": "echeance", "notes": notes})
        r = pa.examiner(xs, [{"notes1": {"tendance": 3}, "notes2": {"tendance": 3}}] * 6)
        self.assertEqual(r["statuts"]["tout"]["tendance"]["statut"], "démontrée")
        self.assertEqual(r["statuts"]["tout"]["freins"]["statut"], "trompeuse")
        self.assertTrue(r["statuts"]["tout"]["duree"]["statut"].startswith("non démontrée"))
        self.assertTrue(any(p["redondante"] for p in r["redondance"]))

    def test_kappa(self):
        self.assertAlmostEqual(pa.kappa_pondere([1, 2, 3, 4, 2, 3], [1, 2, 3, 4, 2, 3]), 1.0)


if __name__ == "__main__":
    unittest.main()
