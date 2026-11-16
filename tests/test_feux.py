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


class TestFeux(unittest.TestCase):
    def test_compter(self):
        self.assertEqual(cf.compter(CSV), {"2026-11-10": [2, 1], "2026-11-11": [1, 0]})

    def test_source(self):
        a = date(2026, 11, 16)
        self.assertEqual(cf.source_pour(date(2026, 11, 1), a), "VIIRS_SNPP_NRT")
        self.assertEqual(cf.source_pour(date(2026, 6, 1), a), "VIIRS_SNPP_SP")

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
