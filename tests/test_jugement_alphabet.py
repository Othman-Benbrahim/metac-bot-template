import unittest

import banc_jugement_alphabet as b


class T(unittest.TestCase):
    def test_consignes_sans_foule(self):
        q = {"titre": "Will X happen?", "cloture": "2026-05-01", "criteres": "Yes if X.", "contexte": "Background."}
        for s in (b.consigne_a(q, 0.2, "r", "2026-03-01"), b.consigne_notes(q, 0.2, "r", "2026-03-01"),
                  b.consigne_finale(q, 0.2, {"tendance": {"note": 3, "pourquoi": "p"}}, "r", "2026-03-01")):
            self.assertNotIn("community", s.lower())
            self.assertNotIn("market", s.lower())
            self.assertIn("0.200", s)

    def test_notes(self):
        r = b.lire_notes({"notes": {"tendance": {"note": 3, "pourquoi": "x"}, "freins": 5, "duree": "2"}})
        self.assertEqual(set(r), {"tendance", "duree"})


if __name__ == "__main__":
    unittest.main()
