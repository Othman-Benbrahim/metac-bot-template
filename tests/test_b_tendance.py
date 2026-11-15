"""0.10.131 : taux de base récent."""
import os
import tempfile
import unittest
from datetime import date, timedelta

os.environ["ALPHABET_REGISTRE"] = tempfile.mkdtemp(prefix="registre-")
import alphabet_pipeline as _ap_regle_ab
_ap_regle_ab.POSTER_AB = False

import banc_forecastbench as fb


def serie(jours, pente_recente):
    d0 = date(2026, 9, 1)
    pts, v = [], 100.0
    for i in range(jours, 0, -1):
        t = d0 - timedelta(days=i)
        v += (pente_recente if i < 120 else (-0.1 if i % 2 else 0.1))
        pts.append({"date": t.isoformat(), "valeur": v})
    return pts, d0


class TestTendance(unittest.TestCase):
    def test_hausse_recente_vue(self):
        pts, d0 = serie(1500, 0.5)
        b = fb.b_hausse(pts, 7, d0)[0]
        t = fb.b_tendance(pts, 7, d0)
        self.assertGreater(t["p"], b + 0.2)          # la tendance des derniers mois pèse

    def test_serie_peu_frequente_ignoree(self):
        d0 = date(2026, 9, 1)
        pts = [{"date": (d0 - timedelta(days=30 * i)).isoformat(), "valeur": float(i % 3)} for i in range(1, 61)]
        self.assertIsNone(fb.b_tendance(pts, 30, d0))  # mensuelle : poids < 20, B reste


if __name__ == "__main__":
    unittest.main()
