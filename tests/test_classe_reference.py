import unittest

import banc_classe_reference as bcr


class T(unittest.TestCase):
    def test_noyau_poids_egaux_rend_B(self):
        xs = [{"jeu": "2025-0%d-01" % m, "fin": "2025-0%d-28" % m, "type": "t", "issue": m % 2, "z": 0.0, "m": 0.0,
               "p_B": 0.5} for m in range(1, 9)]
        bcr.noyau(xs, 1.0, 1.0)
        # le dernier voit les 7 premiers, tous de même z, m : poids 1 → (k + 1) / (n + 2)
        self.assertAlmostEqual(xs[-1]["p_K"], (4 + 1) / (7 + 2))
        self.assertNotIn("p_K", xs[0])

    def test_ressemblance(self):
        xs = [{"jeu": "2025-01-01", "fin": "2025-01-31", "type": "t", "issue": 1, "z": 2.0, "m": 0.0},
              {"jeu": "2025-01-01", "fin": "2025-01-31", "type": "t", "issue": 0, "z": -2.0, "m": 0.0},
              {"jeu": "2025-03-01", "fin": "2025-03-31", "type": "t", "issue": 0, "z": 2.0, "m": 0.0}]
        bcr.noyau(xs, 1.0, 1.0)
        self.assertGreater(xs[2]["p_K"], 0.5)


class TNoyauSeries(unittest.TestCase):
    def test_retour_moyenne(self):
        from datetime import date, timedelta
        import banc_forecastbench as fb
        # série qui oscille : haut une semaine, bas la suivante ; à D on est en haut → la hausse est rare
        d0 = date(2026, 1, 1)
        pts = [{"date": (d0 - timedelta(days=k)).isoformat(), "valeur": 10.0 if (k // 7) % 2 == 0 else 0.0}
               for k in range(1, 2400)]
        pts.append({"date": (d0 - timedelta(days=1)).isoformat(), "valeur": 10.0})
        r = fb.b_noyau(pts, 7, d0)
        self.assertIsNotNone(r)
        self.assertLess(r["p"], 0.3)


if __name__ == "__main__":
    unittest.main()
