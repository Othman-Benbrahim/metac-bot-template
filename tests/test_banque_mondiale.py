"""0.10.463 : collecte Banque mondiale (WDI en bloc) et comptes GDELT des manifestations — tests rapides, sans réseau."""
import csv
import gzip
import tempfile
import unittest
from pathlib import Path

import collecte_banque_mondiale as bm
import gdelt_bq


PAYS = """﻿"Country Code","Short Name","Region"
"FRA","France","Europe & Central Asia"
"DEU","Germany","Europe & Central Asia"
"WLD","World",""
"""


def donnees():
    annees = list(range(2008, 2023))
    lignes = ['"Country Name","Country Code","Indicator Name","Indicator Code",' + ",".join(f'"{a}"' for a in annees)]
    for pays in ("FRA", "DEU", "WLD"):
        plein = ",".join(f'"{a - 2000}"' for a in annees)
        creux = ",".join('"1"' if a == 2015 else '""' for a in annees)
        lignes.append(f'"x","{pays}","Plein","A.PLEIN",{plein}')
        lignes.append(f'"x","{pays}","Creux","B.CREUX",{creux}')
    return "\n".join(lignes) + "\n"


class TestBanqueMondiale(unittest.TestCase):
    def test_agregats_ecartes_et_couverture(self):
        eco = bm.economies(PAYS)
        self.assertEqual(eco, {"FRA", "DEU"})
        vals, noms, annees = bm.lire(donnees(), eco)
        self.assertEqual(annees[0], 2010)
        self.assertNotIn(("WLD", 2015), vals)
        couv = bm.couverture(vals, noms, eco)
        self.assertEqual(couv["A.PLEIN"], 1.0)
        self.assertAlmostEqual(couv["B.CREUX"], 1 / 8)
        with tempfile.TemporaryDirectory() as d:
            gardes = bm.ecrire(vals, noms, annees, eco, couv, Path(d) / "w.csv.gz", Path(d) / "l.csv")
            self.assertEqual(gardes, ["A.PLEIN"])
            with gzip.open(Path(d) / "w.csv.gz", "rt") as f:
                r = list(csv.reader(f))
            self.assertEqual(r[0], ["pays", "annee", "A.PLEIN"])
            self.assertEqual(len(r) - 1, 2 * len(annees))


class TestManifestationsGdelt(unittest.TestCase):
    def test_requete_et_ecriture(self):
        s = gdelt_bq.sql_manifestations()
        self.assertIn("EventRootCode = '14'", s)
        self.assertIn("_PARTITIONTIME", s)
        self.assertIn("manifestations", gdelt_bq.PLAFOND_REQUETE_GO)
        with tempfile.TemporaryDirectory() as d:
            n = gdelt_bq.ecrire_manifestations(
                [{"pays": "FR", "semaine": "2016-01-04", "evenements": 10, "manifs": 2, "manifs_racine": 1,
                  "articles_manifs": None}], Path(d) / "m.csv")
            self.assertEqual(n, 1)
            r = list(csv.reader(open(Path(d) / "m.csv")))
            self.assertEqual(r[1], ["FR", "2016-01-04", "10", "2", "1", "0"])


if __name__ == "__main__":
    unittest.main()
