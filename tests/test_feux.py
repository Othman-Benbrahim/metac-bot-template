"""0.10.208 : feux par pays (NASA FIRMS)."""
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest import mock

import collecte_feux as cf
import indicateurs_niche as ni

CSV = ("country_id,latitude,longitude,bright_ti4,scan,track,acq_date,acq_time,satellite,instrument,confidence,version,frp,daynight\n"
       "UKR,48.1,37.5,340,0.4,0.4,2026-11-10,0112,N,VIIRS,h,2.0NRT,12.3,N\n"
       "UKR,48.2,37.6,330,0.4,0.4,2026-11-10,0112,N,VIIRS,n,2.0NRT,5.1,N\n"
       "UKR,47.9,36.1,331,0.4,0.4,2026-11-11,1012,N,VIIRS,l,2.0NRT,2.0,D\n")


try:
    import shapely  # noqa: F401
    SHAPELY = True
except ImportError:
    SHAPELY = False

GEO = {"features": [
    {"properties": {"ADMIN": "Carré A", "ISO_A2": "-99", "ISO_A2_EH": "AA"},
     "geometry": {"type": "Polygon", "coordinates": [[[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]]]}},
    {"properties": {"ADMIN": "Somaliland", "ISO_A2": "-99", "ISO_A2_EH": "-99"},
     "geometry": {"type": "Polygon", "coordinates": [[[20, 0], [30, 0], [30, 10], [20, 10], [20, 0]]]}}]}
MONDE = ("latitude,longitude,bright_ti4,scan,track,acq_date,acq_time,satellite,instrument,confidence,version,bright_ti5,frp,daynight\n"
         "5,5,340,0.4,0.4,2026-11-10,0112,N,VIIRS,h,2.0NRT,290,12.3,N\n"
         "6,6,330,0.4,0.4,2026-11-11,0112,N,VIIRS,n,2.0NRT,290,5.1,N\n"
         "5,25,331,0.4,0.4,2026-11-10,1012,N,VIIRS,l,2.0NRT,290,2.0,D\n"
         "50,-30,331,0.4,0.4,2026-11-10,1012,N,VIIRS,l,2.0NRT,290,2.0,D\n")


class TestFeux(unittest.TestCase):
    @unittest.skipUnless(SHAPELY, "shapely absent (le workflow le charge avec uv run --with shapely)")
    def test_rattachement(self):
        g, codes = cf.frontieres(GEO)
        self.assertEqual(codes, ["AA", "SO"])
        self.assertEqual(cf.compter_par_pays(MONDE, g, codes),
                         {("AA", "2026-11-10"): [1, 1], ("AA", "2026-11-11"): [1, 0], ("SO", "2026-11-10"): [1, 0]})

    def test_compter(self):
        self.assertEqual(cf.compter(CSV), {"2026-11-10": [2, 1], "2026-11-11": [1, 0]})

    def test_source(self):
        d = cf.plages("data_id,min_date,max_date\nVIIRS_SNPP_SP,2012-01-20,2026-08-31\n"
                      "VIIRS_SNPP_NRT,2026-08-01,2026-11-15\nMODIS_NRT,2026-08-01,2026-11-15\n")
        self.assertEqual(cf.source_pour("2026-06-01", "2026-06-05", d), "VIIRS_SNPP_SP")       # NOAA-20 absent de ce jeu
        self.assertEqual(cf.source_pour("2026-11-01", "2026-11-05", d), "VIIRS_SNPP_NRT")
        d2 = cf.plages("data_id,min_date,max_date\nVIIRS_NOAA20_SP,2018-04-01,2026-07-31\nVIIRS_NOAA20_NRT,2026-08-01,2026-11-16\n"
                       "VIIRS_SNPP_NRT,2026-08-01,2026-11-02\n")
        self.assertEqual(cf.source_pour("2026-09-20", "2026-09-24", d2), "VIIRS_NOAA20_NRT")     # un seul capteur
        self.assertIsNone(cf.source_pour("2026-11-14", "2026-11-18", d))

    def test_indicateur(self):
        d0 = date(2026, 11, 1)
        with tempfile.TemporaryDirectory() as t:
            f, j = Path(t) / "f.csv", Path(t) / "j.txt"
            lignes = ["pays,jour,detections,forte_confiance"]
            for k in range(1, 29):
                lignes.append(f"UA,{(d0 - timedelta(days=k)).isoformat()},{30 if k <= 14 else 10},{3 if k <= 14 else 1}")
            f.write_text("\n".join(lignes) + "\n", encoding="utf-8")
            j.write_text("\n".join((d0 - timedelta(days=k)).isoformat() for k in range(1, 29)), encoding="utf-8")
            with mock.patch.multiple(ni, FEUX=f, FEUX_JOURS=j):
                r = ni.feux("UA", d0)
                self.assertEqual((r["detections_14j"], r["detections_14j_avant"]), (420, 140))
                self.assertGreater(r["valeur"], 0.4)
                self.assertEqual(r["part_forte_confiance"], 0.1)
                self.assertEqual(ni.feux("FR", d0)["valeur"], 0.0)
                j.write_text("", encoding="utf-8")
                self.assertFalse(ni.feux("UA", d0)["present"])


if __name__ == "__main__":
    unittest.main()
