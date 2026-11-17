import unittest

import banc_conflictforecast as bc


class T(unittest.TestCase):
    def test_fuite(self):
        self.assertEqual(bc.utilisable_le(202610), "2026-11-25")
        self.assertEqual(bc.utilisable_le(202512), "2026-01-25")
        serie = [("2026-10-25", {"ESC": 0}), ("2026-11-25", {"ESC": 1})]
        self.assertEqual(bc.etat_au(serie, "2026-11-24"), {"ESC": 0})
        self.assertEqual(bc.etat_au(serie, "2026-11-25"), {"ESC": 1})
        self.assertEqual(bc.etat_au(serie, "2026-01-01"), {})

    def test_charger(self):
        t = ("version,isocode,periode,cible,horizon,p_all,p_text,p_hist,actuel\n"
             "2026-10,UKR,202610,lnbest,3,7.5,,,6.8\n2026-10,UKR,202610,anyviolence,3,0.99,,,1\n"
             "2021-07,AFG,202107,anyviolence,3,81.4,,,1\n2026-10,UKR,202610,lnbest,12,9,,,6.8\n")
        cf = bc.charger_cf(t, {"UKR": "UA", "AFG": "AF"})
        self.assertEqual(cf["UA"], [("2026-11-25", {"ESC": 1, "AV": 1})])
        self.assertEqual(cf["AF"][0][1], {"AV": 1})

    def test_resumer(self):
        ls = []
        for j, jeu in enumerate(["2025-0%d-01" % m for m in range(1, 7)] + ["2026-0%d-01" % m for m in range(1, 7)]):
            for i in range(4):
                ls.append({"jeu": jeu, "famille": "violence", "issue": int(i < 3), "p_B": 0.3, "cf": {"ESC": 1}})
        r = bc.resumer(ls)
        c = next(c for c in r["cellules"] if c["indicateur"] == "ESC" and c["etat"] == 1)
        self.assertGreater(c["delta"], 0)
        self.assertEqual(c["verdict"], "confirmé")


if __name__ == "__main__":
    unittest.main()
