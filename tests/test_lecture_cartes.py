"""0.10.470 : lecteur générique des cartes publiées (standard de lecture cartes/*.yaml) — tests rapides, sans réseau."""
import csv
import io
import tempfile
import unittest
import zipfile
from pathlib import Path

import lecture_cartes as lc


GED = ("id,date_start,country,country_id,type_of_violence,best\n"
       "1,2025-03-02 00:00:00.000,Russia (Soviet Union),365,1,10\n"
       "2,2025-03-20 00:00:00.000,DR Congo (Zaire),490,3,4\n"
       "3,2026-01-05 00:00:00.000,Russia (Soviet Union),365,1,7\n")
CAND = ("id,date_start,country,country_id,type_of_violence,best\n"
        "9,2026-01-07 00:00:00.000,Russia (Soviet Union),365,2,5\n"
        "10,2026-01-09 00:00:00.000,Atlantis,999,1,1\n")


class TestLectureCartes(unittest.TestCase):
    def test_spec_ucdp_et_liens(self):
        spec = next(s for s in lc.specs() if s["id"] == "ucdp")
        html = ('<a href="/downloads/ged/ged251-csv.zip">a</a><a href="/downloads/ged/ged261-csv.zip">b</a>'
                '<a href="/downloads/candidateged/GEDEvent_v26_0_9.csv">c</a>'
                '<a href="/downloads/candidateged/GEDEvent_v26_0_10.csv">d</a>'
                '<a href="/downloads/candidateged/GEDEvent_v26_01_26_09.csv">e</a>')
        l = lc.choisir_liens(html, spec, "https://ucdp.uu.se/downloads/")
        self.assertEqual(l["historique"], "https://ucdp.uu.se/downloads/ged/ged261-csv.zip")
        self.assertEqual(l["mois"], "https://ucdp.uu.se/downloads/candidateged/GEDEvent_v26_0_10.csv")
        self.assertEqual(l["cumul_annee"], "https://ucdp.uu.se/downloads/candidateged/GEDEvent_v26_01_26_09.csv")

    def test_agregats_et_priorite(self):
        spec = next(s for s in lc.specs() if s["id"] == "ucdp")
        b = io.BytesIO()
        with zipfile.ZipFile(b, "w") as z:
            z.writestr("GEDEvent_v26_1.csv", GED)
        agg, inc = {}, set()
        iso = lc.table_pays()
        self.assertEqual(lc.agreger(lc.lignes_csv(b.getvalue(), "csv_zip"), spec["lecture"], "historique", iso, agg, inc), 3)
        lc.agreger(lc.lignes_csv(CAND.encode(), "csv"), spec["lecture"], "mois", iso, agg, inc)
        self.assertEqual(inc, {"Atlantis"})
        with tempfile.TemporaryDirectory() as d:
            n = lc.ecrire_agregats(spec, agg, Path(d) / "o.csv")
            r = list(csv.DictReader(open(Path(d) / "o.csv")))
        self.assertEqual(n, 4)
        ru = {x["mois"]: x for x in r if x["iso3"] == "RUS"}
        self.assertEqual(ru["2025-03"]["somme"], "10.0")
        self.assertEqual(ru["2026-01"]["source"], "mois")          # le mois le plus récent l'emporte sur l'historique
        self.assertEqual(ru["2026-01"]["categorie_2"], "1")
        self.assertEqual({x["iso3"] for x in r if x["pays_source"].startswith("DR")}, {"COD"})


if __name__ == "__main__":
    unittest.main()
