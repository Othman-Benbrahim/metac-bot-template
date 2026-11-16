"""0.10.196 : ACAPS, risques et INFORM."""
import os
import tempfile
import unittest
from datetime import date
from pathlib import Path

os.environ["ALPHABET_REGISTRE"] = tempfile.mkdtemp(prefix="registre-")
import collecte_acaps as ca
import indicateurs_niche as ni


class TestAcaps(unittest.TestCase):
    def test_lignes(self):
        r = ca.lignes_risques([{"risk_id": "R1", "iso3": ["SYR", "TUR"], "date_entered": "2026-09-01", "status": "Active"}],
                              {"SYR": "SY", "TUR": "TR"})
        self.assertEqual([x["pays"] for x in r], ["SY", "TR"])
        i = ca.lignes_inform([{"crisis_id": "AFG001", "iso3": [], "INFORM Severity Index": 9.2}], {"AFG": "AF"}, "2026-11-16")
        self.assertEqual((i[0]["pays"], i[0]["indice"]), ("AF", 9.2))

    def test_indicateur(self):
        d = Path(tempfile.mkdtemp()) / "r.csv"
        ancien = ni.ACAPS_RISQUES
        ni.ACAPS_RISQUES = d
        try:
            d.write_text("risk_id,pays,date_entered,last_risk_update,probability,impact,risk_level,status,risk_type,"
                         "geographic_level,risk_title\nR1,SY,2026-09-01,,,,,,,,a\nR2,SY,2025-01-01,,,,,,,,b\n")
            self.assertEqual(ni.acaps("SY", date(2026, 10, 1))["valeur"], 1)
            self.assertEqual(ni.acaps("FR", date(2026, 10, 1))["valeur"], 0)
        finally:
            ni.ACAPS_RISQUES = ancien


if __name__ == "__main__":
    unittest.main()
