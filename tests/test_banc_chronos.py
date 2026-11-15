"""0.10.132 : B Chronos, avec un faux modèle (le vrai est téléchargé au banc)."""
import os
import tempfile
import unittest
from datetime import date, timedelta

os.environ["ALPHABET_REGISTRE"] = tempfile.mkdtemp(prefix="registre-")
import alphabet_pipeline as _ap_regle_ab
_ap_regle_ab.POSTER_AB = False

try:
    import numpy  # noqa: F401
    TORCH = True
except Exception:
    TORCH = False

import banc_chronos as bc


class FauxTenseur:
    def __init__(self, q):
        self.q = q

    def __getitem__(self, idx):
        return self

    def tolist(self):
        return self.q


class FauxPipe:
    quantiles = [0.1, 0.5, 0.9]

    def __init__(self, q):
        self.q = q

    def predict_quantiles(self, inputs, prediction_length, quantile_levels):
        self.k = prediction_length
        return [FauxTenseur(self.q)], None


class TestChronos(unittest.TestCase):
    def test_repartition(self):
        self.assertAlmostEqual(bc.repartition(5.0, [0.1, 0.5, 0.9], [0.0, 5.0, 10.0]), 0.5)
        self.assertAlmostEqual(bc.repartition(7.5, [0.1, 0.5, 0.9], [0.0, 5.0, 10.0]), 0.7)
        self.assertEqual(bc.repartition(-3, [0.1, 0.5, 0.9], [0.0, 5.0, 10.0]), 0.1)

    def test_pas_horizon(self):
        d = [date(2026, 1, 1) + timedelta(days=i) for i in range(10)]
        self.assertEqual(bc.pas_horizon(d, 7), 7)
        m = [date(2026, 1, 1) + timedelta(days=30 * i) for i in range(10)]
        self.assertEqual(bc.pas_horizon(m, 7), 1)

    @unittest.skipUnless(TORCH, "numpy absent")
    def test_b_chronos(self):
        d0 = date(2026, 3, 1)
        pts = [{"date": (d0 - timedelta(days=40 - i)).isoformat(), "valeur": 5.0} for i in range(40)]
        r = bc.b_chronos(pts, 7, d0, 0.2, pipe=FauxPipe([0.0, 5.0, 10.0]))
        self.assertAlmostEqual(r["p"], 0.8 * 0.5)      # dernière valeur à la médiane, 20 % sans changement
        self.assertIsNone(bc.b_chronos(pts[:10], 7, d0, 0.0, pipe=FauxPipe([0, 1, 2])))


if __name__ == "__main__":
    unittest.main()
