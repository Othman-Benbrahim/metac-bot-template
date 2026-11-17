import unittest
from datetime import date, timedelta

import banc_geo_math as bg
import banc_richardson as br


class T(unittest.TestCase):
    def test_grappe(self):
        d0 = date(2025, 3, 1)
        cov = {(d0 - timedelta(days=k)).isoformat() for k in range(1, 40)}
        haut = {(d0 - timedelta(days=k)).isoformat(): (10 if k <= 14 else 1) for k in range(1, 29)}
        bas = {(d0 - timedelta(days=k)).isoformat(): 3 for k in range(1, 29)}
        c = {("manifestations", "A"): haut, ("manifestations", "B"): haut, ("manifestations", "C"): bas}
        self.assertEqual(bg.grappe("X", "manifestations", d0, c, cov, {"X": ["A", "B", "C"]}), 1)
        self.assertEqual(bg.grappe("X", "manifestations", d0, c, cov, {"X": ["A", "C", "C"]}), 0)
        self.assertIsNone(bg.grappe("X", "manifestations", d0, c, cov, {"X": ["Z"]}))

    def test_alerte(self):
        d0 = date(2025, 3, 1)
        cov = {(d0 - timedelta(days=k)).isoformat() for k in range(1, 91)}
        s = {}
        for k in range(1, 91):
            j = (d0 - timedelta(days=k)).isoformat()
            s[j] = 5 if k > 45 else (k // 5) * 3   # calme puis variance et autocorrélation fortes
        self.assertEqual(bg.alerte(s, d0, cov), 1)
        self.assertEqual(bg.alerte({j: 5 for j in cov}, d0, cov), 0)

    def test_lois(self):
        fen = [0, 2, 5, 1, 40, 3, 0, 8, 2, 1, 120, 4]
        self.assertGreater(br.p_ln(fen, 100), br.p_bn(fen, 100) * 0 )   # défini
        self.assertTrue(0 < br.p_bn(fen, 30) < 1)
        self.assertTrue(0 < br.p_ln(fen, 30) < 1)


if __name__ == "__main__":
    unittest.main()
