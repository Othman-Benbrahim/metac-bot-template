"""0.10.175 : censure OONI, comptes et indicateur."""
import os
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

os.environ["ALPHABET_REGISTRE"] = tempfile.mkdtemp(prefix="registre-")
import collecte_ooni as co
import indicateurs_niche as ni
import induction as ind


class TestOoni(unittest.TestCase):
    def test_lignes_api(self):
        corps = {"result": [{"measurement_start_day": "2026-10-01", "measurement_count": 10, "anomaly_count": 3,
                             "confirmed_count": 1}, {"measurement_count": 4}]}
        self.assertEqual(co.lignes_api(corps), [("2026-10-01", 10, 3, 1)])

    def test_indicateur(self):
        d = Path(tempfile.mkdtemp())
        ancien = (ni.OONI_COMPTES, ni.OONI_JOURS, ni._OONI)
        ni.OONI_COMPTES, ni.OONI_JOURS, ni._OONI = d / "c.csv", d / "j.txt", None
        try:
            d0 = date(2026, 10, 1)
            jours = [(d0 - timedelta(days=k)).isoformat() for k in range(1, 29)]
            ni.OONI_JOURS.write_text("\n".join(jours))
            ni.OONI_COMPTES.write_text("pays,jour,test,mesures,anomalies,confirmees\n"
                                       f"IR,{jours[0]},web_connectivity,100,40,5\nIR,{jours[20]},web_connectivity,100,10,0\n"
                                       f"IR,{jours[0]},telegram,10,9,0\n")
            m = ni.ooni("IR", d0)
            self.assertTrue(m["present"])
            self.assertAlmostEqual(m["valeur"], 0.30)
            self.assertNotIn("valeur_messageries", m)          # 10 mesures de messageries : sous le minimum
            self.assertFalse(ni.ooni("FR", d0)["present"])     # aucune mesure
        finally:
            ni.OONI_COMPTES, ni.OONI_JOURS, ni._OONI = ancien

    def test_etats(self):
        self.assertIn("ooni", ind.ETATS)
        self.assertIn("ooni_messageries", ind.ETATS)


if __name__ == "__main__":
    unittest.main()
