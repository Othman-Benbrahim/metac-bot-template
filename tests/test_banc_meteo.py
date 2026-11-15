"""0.10.135 : contexte météo."""
import os
import tempfile
import unittest
from datetime import date

os.environ["ALPHABET_REGISTRE"] = tempfile.mkdtemp(prefix="registre-")
import alphabet_pipeline as _ap_regle_ab
_ap_regle_ab.POSTER_AB = False

import banc_meteo as bm


class TestMeteo(unittest.TestCase):
    def test_station(self):
        t = "What is the probability that the daily average temperature at the French weather station at Reims – Prunay Aerodrome will be higher on 2026-07-12 than on 2026-07-05?"
        self.assertEqual(bm.station(t), "Reims – Prunay Aerodrome")
        self.assertEqual(bm.nom_a_geocoder("Reims – Prunay Aerodrome"), "Reims")
        self.assertEqual(bm.nom_a_geocoder("Brest Bretagne Airport"), "Brest Bretagne")
        self.assertEqual(bm.nom_a_geocoder("Toulouse–Blagnac Airport"), "Toulouse")

    def test_probabilite(self):
        self.assertAlmostEqual(bm.p_meteo(20.0, 20.0), 0.5)
        self.assertGreater(bm.p_meteo(18.0, 22.0), 0.9)
        self.assertEqual(bm.p_meteo(10.0, 30.0), 0.99)

    def test_moyenne_jour(self):
        h = [f"2026-07-05T{i:02d}:00" for i in range(24)] + [f"2026-07-06T{i:02d}:00" for i in range(24)]
        v = [10.0] * 24 + [20.0] * 24
        self.assertEqual(bm.moyenne_jour(h, v, date(2026, 7, 5)), 10.0)
        self.assertIsNone(bm.moyenne_jour(h[:10], v[:10], date(2026, 7, 5)))


if __name__ == "__main__":
    unittest.main()
