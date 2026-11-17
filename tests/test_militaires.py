"""0.10.229 : aéronefs militaires visibles par pays (adsb.fi)."""
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest import mock

import collecte_militaires as cm
import indicateurs_niche as ni

CARRE = {"features": [
    {"properties": {"ISO_A2": "-99", "ISO_A2_EH": "FR"},
     "geometry": {"type": "MultiPolygon", "coordinates": [[[[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]],
                                                            [[4, 4], [6, 4], [6, 6], [4, 6], [4, 4]]]]}},
    {"properties": {"ISO_A2": "-99", "ISO_A2_EH": "-99"},
     "geometry": {"type": "Polygon", "coordinates": [[[20, 20], [21, 20], [21, 21], [20, 21], [20, 20]]]}}]}


class TestMilitaires(unittest.TestCase):
    def test_pays_et_comptes(self):
        polys = cm.polygones(CARRE)
        self.assertEqual(len(polys), 1)                       # le territoire sans code est ignoré
        self.assertEqual(cm.pays_de(2, 2, polys), "FR")
        self.assertIsNone(cm.pays_de(5, 5, polys))            # dans le trou
        self.assertIsNone(cm.pays_de(15, 2, polys))
        d = {"ac": [{"hex": "a", "lat": 2, "lon": 2}, {"hex": "a", "lat": 2.1, "lon": 2},
                    {"hex": "b", "lat": 3, "lon": 3}, {"hex": "c", "lat": 30, "lon": 30}, {"hex": "d"}]}
        self.assertEqual(cm.compter(d, polys), {"FR": 2, "mer": 1})

    def test_indicateur(self):
        d0 = date(2026, 12, 20)
        with tempfile.TemporaryDirectory() as t:
            f, r = Path(t) / "m.csv", Path(t) / "r.txt"
            lignes, rel = ["releve,pays,appareils"], []
            for k in range(1, 29):
                for h in range(0, 24, 3):
                    rv = f"{(d0 - timedelta(days=k)).isoformat()}T{h:02d}:41Z"
                    rel.append(rv)
                    lignes.append(f"{rv},PL,{6 if k <= 7 else 2}")
            f.write_text("\n".join(lignes) + "\n", encoding="utf-8")
            r.write_text("\n".join(rel) + "\n", encoding="utf-8")
            with mock.patch.multiple(ni, MILITAIRES=f, MILITAIRES_RELEVES=r):
                v = ni.militaires("PL", d0)
                self.assertTrue(v["present"])
                self.assertAlmostEqual(v["moyenne_7j"], 6)
                self.assertGreater(v["valeur"], 0.4)
                self.assertEqual(ni.militaires("DE", d0)["valeur"], 0.0)
                self.assertFalse(ni.militaires("PL", d0 + timedelta(days=30))["present"])


if __name__ == "__main__":
    unittest.main()
