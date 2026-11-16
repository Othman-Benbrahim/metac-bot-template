"""0.10.177 : coupures Cloudflare Radar et indicateur."""
import os
import tempfile
import unittest
from datetime import date
from pathlib import Path

os.environ["ALPHABET_REGISTRE"] = tempfile.mkdtemp(prefix="registre-")
import collecte_radar as cr
import indicateurs_niche as ni


class TestRadar(unittest.TestCase):
    def test_lignes(self):
        a = {"id": "x1", "startDate": "2026-09-20T10:00:00Z", "endDate": None, "locations": ["ir"],
             "locationsDetails": [{"code": "IR"}, {"code": "IQ"}],
             "outage": {"outageCause": "GOVERNMENT_DIRECTED", "outageType": "NATIONWIDE"}}
        l = cr.lignes(a)
        self.assertEqual(sorted(x["pays"] for x in l), ["IQ", "IR"])
        self.assertEqual((l[0]["debut"], l[0]["cause"], l[0]["fin"]), ("2026-09-20", "GOVERNMENT_DIRECTED", ""))

    def test_indicateur(self):
        d = Path(tempfile.mkdtemp())
        ancien = (ni.RADAR, ni.RADAR_COUVERTURE)
        ni.RADAR, ni.RADAR_COUVERTURE = d / "r.csv", d / "c.txt"
        try:
            ni.RADAR.write_text("id,pays,debut,fin,cause,type,portee\n"
                                "a,IR,2026-09-20,,GOVERNMENT_DIRECTED,NATIONWIDE,\n"
                                "b,IR,2026-09-25,,POWER_OUTAGE,REGIONAL,\n"
                                "c,IR,2026-08-01,,POWER_OUTAGE,REGIONAL,\n")
            ni.RADAR_COUVERTURE.write_text("2026-06-01\n")
            m = ni.radar("IR", date(2026, 10, 1))
            self.assertEqual((m["valeur"], m["etat_14j"], m["electricite_14j"]), (2, 1, 1))
            ni.RADAR_COUVERTURE.write_text("2026-09-25\n")
            self.assertFalse(ni.radar("IR", date(2026, 10, 1))["present"])
        finally:
            ni.RADAR, ni.RADAR_COUVERTURE = ancien


if __name__ == "__main__":
    unittest.main()
