"""0.10.230 : collecte ConflictForecast (prévision publiée = dernière période de chaque version)."""
import unittest

import collecte_conflictforecast as cf

NOUVEAU = """isocode,period,ons_armedconf_03_target,ons_armedconf_03_text,ons_armedconf_03_hist,ons_armedconf_03_all,ons_armedconf_03_naive
UKR,202609,1,0.1,0.9,0.95,1
UKR,202610,,0.13,1.0,0.99,1
SEN,202610,,0.02,0.01,0.03,0
"""
ANCIEN = """isocode,year,month,text_model,best_model,topic0
UKR,2021,7,0.2,0.8,0.1
UKR,2021,8,0.25,0.85,0.1
"""


class TestCF(unittest.TestCase):
    def test_tri(self):
        self.assertTrue(cf.garder("conflictforecast_ons_armedconf_03.csv"))
        self.assertFalse(cf.garder("grid_risk_2026-10.csv"))
        self.assertEqual(cf.version_iso("10-2026"), "2026-10")
        self.assertIsNone(cf.version_iso("latest"))
        self.assertEqual(cf.cible_horizon("conflictforecast_ons_armedconf_03.csv"), ("armedconf", 3))
        self.assertEqual(cf.cible_horizon("conflictforecast_int_lnbest_12.csv"), ("lnbest", 12))
        self.assertEqual(cf.cible_horizon("conflictforecast_anyviolence_3.csv"), ("anyviolence", 3))

    def test_extraire_derniere_periode(self):
        r = cf.extraire(NOUVEAU, "2026-10", "conflictforecast_ons_armedconf_03.csv")
        self.assertEqual([(x["isocode"], x["periode"], x["p_all"]) for x in r], [("UKR", 202610, "0.99"), ("SEN", 202610, "0.03")])
        INT = "isocode,period,int_lnbest_03_text,int_lnbest_03_hist,int_lnbest_03_all,fatalities_UCDP,lnbest\nUKR,202610,5,6,7.5,900,6.8\n"
        self.assertEqual(cf.extraire(INT, "2026-10", "conflictforecast_int_lnbest_03.csv")[0]["actuel"], "6.8")
        r = cf.extraire(ANCIEN, "2021-09", "conflictforecast_armedconf_3.csv")
        self.assertEqual([(x["periode"], x["p_all"], x["p_text"]) for x in r], [(202108, "0.85", "0.25")])


if __name__ == "__main__":
    unittest.main()
