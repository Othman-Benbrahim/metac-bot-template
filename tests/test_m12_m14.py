"""0.10.202 : M12 (récit russe), M13 (actes hostiles russes dans GDELT), M14 (dates de mémoire)."""
import csv
import os
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest import mock

import collecte_gdelt as cg
import collecte_recit_russe as cr
import indicateurs_niche as ni


def ligne_gdelt(acteur, racine, pays_action):
    col = [""] * 58
    col[7], col[28], col[27], col[51] = acteur, racine, racine + "0", pays_action
    return "\t".join(col)


class TestM13(unittest.TestCase):
    def test_hostilites(self):
        texte = "\n".join([ligne_gdelt("RUS", "18", "EN"), ligne_gdelt("RUS", "19", "EN"), ligne_gdelt("RUS", "20", "UP"),
                           ligne_gdelt("RUS", "14", "EN"), ligne_gdelt("USA", "18", "EN"), ligne_gdelt("RUS", "18", "RS")])
        h = cg.hostilites(texte, {"EN": "EE", "UP": "UA", "RS": "RU"})
        self.assertEqual(h, {"EE": [1, 1, 0], "UA": [0, 0, 1]})


class TestM12(unittest.TestCase):
    def test_requete(self):
        self.assertEqual(cr.requete("Estonia"), 'sourcecountry:russia "Estonia"')
        self.assertIn("false flag", cr.requete("Estonia", alibi=True))

    def test_indicateur(self):
        d0 = date(2026, 11, 1)
        with tempfile.TemporaryDirectory() as t:
            f = Path(t) / "r.csv"
            with f.open("w", newline="") as h:
                w = csv.writer(h)
                w.writerow(cr.CHAMPS)
                for k in range(1, 29):
                    j = d0 - timedelta(days=k)
                    w.writerow(["EE", j.isoformat(), 10 if k <= 14 else 4, 2 if k <= 14 else "", 1000])
            with mock.patch.object(ni, "RECIT_RUSSE", f):
                r = ni.recit_russe("EE", d0)
                self.assertTrue(r["present"])
                self.assertEqual((r["articles_14j"], r["articles_14j_avant"]), (140, 56))
                self.assertGreater(r["valeur"], 0.4)
                self.assertEqual(r["part_alibi_14j"], 0.2)
                self.assertFalse(ni.recit_russe("LV", d0)["present"])


class TestM14(unittest.TestCase):
    def test_dates(self):
        self.assertEqual(ni.dates_memoire("EE", date(2026, 5, 1))["valeur"], 1)        # 9 mai dans la fenêtre
        self.assertEqual(ni.dates_memoire("EE", date(2026, 7, 1))["valeur"], 0)
        self.assertEqual(ni.dates_memoire("LV", date(2026, 3, 10))["valeur"], 1)       # 16 mars
        self.assertFalse(ni.dates_memoire("BR", date(2026, 5, 1))["present"])


if __name__ == "__main__":
    unittest.main()
