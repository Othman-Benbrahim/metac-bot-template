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


class TestAnalyseCartes(unittest.TestCase):
    def test_etats_transitions(self):
        import analyse_cartes as ac
        lignes = [{"iso3": "AAA", "pays_source": "A", "mois": m, "somme": v}
                  for m, v in [("2025-01", "0"), ("2025-02", "30"), ("2025-03", "30"), ("2025-04", "5"), ("2026-01", "2000")]]
        a = ac.analyser(lignes)
        self.assertEqual(a["dernier_mois"], "2026-01")
        self.assertEqual(a["transitions"]["comptes"][2][2], 1)         # moyen → moyen
        self.assertEqual(a["pays"][0]["etat"], "haut")
        self.assertEqual(a["episodes_moyen_ou_plus"]["nombre"], 1)
        # aucun mois « haut » dans l'historique 1989-2025 de l'exemple : pas de taux de départ pour cet état
        self.assertEqual(sum(a["pays"][0]["proba_mois_suivant"].values()), 0)
        self.assertAlmostEqual(sum(a["transitions"]["probabilites"][2]), 1.0, places=2)


class TestLectureEtendue(unittest.TestCase):
    """0.10.472 : matière déjà téléchargée (types, civils, régions, acteurs), VPP et Onset."""
    GED2 = ("date_start,country,country_id,type_of_violence,best,deaths_civilians,adm_1,side_a,side_b\n"
            "2026-10-02,Yemen (North Yemen),678,1,10,2,Taizz,Government of Yemen,Ansarallah\n"
            "2026-10-03,Yemen (North Yemen),678,3,5,5,Marib,Ansarallah,Civilians\n"
            "2026-10-04,Yemen (North Yemen),678,1,1,0,Taizz,Government of Yemen,AQAP\n")

    def test_detail_du_mois(self):
        spec = next(s for s in lc.specs() if s["id"] == "ucdp")
        agg, inc = {}, set()
        lc.agreger(lc.lignes_csv(self.GED2.encode(), "csv"), spec["lecture"], "mois", lc.table_pays(), agg, inc)
        with tempfile.TemporaryDirectory() as d:
            lc.ecrire_agregats(spec, agg, Path(d) / "o.csv")
            r = list(csv.DictReader(open(Path(d) / "o.csv")))[0]
        self.assertEqual((r["somme"], r["somme_categorie_1"], r["somme_categorie_3"]), ("16.0", "11.0", "5.0"))
        self.assertEqual((r["morts_civils"], r["distincts_regions"]), ("7.0", "2"))
        self.assertEqual(r["principaux"].split(" ; ")[0], "Ansarallah")        # 15 morts (10 + 5)
        import analyse_cartes as ac
        dm = ac.detail_mois(r)
        self.assertNotIn("Civilians", dm["acteurs"])
        self.assertEqual(dm["par_type"]["contre des civils"], 5.0)

    def test_onset_pays_annee_roles(self):
        spec = next(s for s in lc.specs() if s["id"] == "ucdp-onset")
        html = ('<a href="https://ucdp.uu.se/downloads/onset/ucdp-intrastate-country-onset-251.csv">a</a>'
                '<a href="https://ucdp.uu.se/downloads/onset/ucdp-intrastate-country-multiple-onset-251.csv">b</a>'
                '<a href="https://ucdp.uu.se/downloads/onset/ucdp-interstate-country-onset-251.csv">c</a>')
        l = lc.choisir_liens(html, spec, spec["page"])
        self.assertTrue(l["interne"].endswith("intrastate-country-onset-251.csv"))
        self.assertTrue(l["entre_etats"].endswith("interstate-country-onset-251.csv"))
        intra = "abc,name,year,gwno_a,newconf,onset1,onset2,onset3,onset5,onset10,onset20\nMLI,Mali,2012,432,0,1,1,1,1,1,0\nMLI,Mali,2013,432,0,0,0,0,0,0,0\n"
        inter = "abc,name,year,gwno_a,newconf,onset1,onset2,onset3,onset5,onset10,onset20\nMLI,Mali,2012,432,0,0,0,0,0,0,0\nMLI,Mali,2013,432,0,0,0,0,0,0,0\n"
        agg, inc = {}, set()
        lc.agreger(lc.lignes_csv(intra.encode(), "csv"), spec["lecture"], "interne", lc.table_pays(), agg, inc)
        lc.agreger(lc.lignes_csv(inter.encode(), "csv"), spec["lecture"], "entre_etats", lc.table_pays(), agg, inc)
        with tempfile.TemporaryDirectory() as d:
            lc.ecrire_agregats(spec, agg, Path(d) / "o.csv")
            r = list(csv.DictReader(open(Path(d) / "o.csv")))
        self.assertEqual(r[0]["annee"], "2012")
        self.assertEqual((r[0]["interne_reprise_1"], r[0]["entre_etats_reprise_1"]), ("1.0", "0.0"))
        import analyse_cartes as ac
        o = ac.analyser_onset(r)
        self.assertEqual(o["dernier_par_pays"]["MLI"], {"annee": "2012", "types": ["interne"], "nom": "Mali"})
        self.assertEqual(o["taux_annuel"], 0.5)

    def test_vpp(self):
        spec = next(s for s in lc.specs() if s["id"] == "ucdp-vpp")
        l = lc.choisir_liens('<a href="https://ucdp.uu.se/downloads/vpp/GEDEvent_v26_1_4_1101_2512.csv">x</a>'
                             '<a href="https://ucdp.uu.se/downloads/vpp/GEDEvent_v26_1_4_1101_2512.xlsx">y</a>',
                             spec, spec["page"])
        self.assertEqual(l, {"evenements": "https://ucdp.uu.se/downloads/vpp/GEDEvent_v26_1_4_1101_2512.csv"})
        import analyse_cartes as ac
        v = ac.analyser_vpp([{"iso3": "KEN", "pays_source": "Kenya", "mois": "2024-06", "evenements": "3", "somme": "20"},
                             {"iso3": "KEN", "pays_source": "Kenya", "mois": "2025-07", "evenements": "2", "somme": "8"}])
        self.assertEqual((v["derniere_annee"], v["pays"][0]["evenements"], v["pays"][0]["serie_evenements"]), ("2025", 2, [3, 2]))

    def test_empreinte_change_avec_la_lecture(self):
        spec = next(s for s in lc.specs() if s["id"] == "ucdp")
        e = lc.empreinte_lecture(spec)
        spec2 = dict(spec, lecture=dict(spec["lecture"], sommes={}))
        self.assertNotEqual(e, lc.empreinte_lecture(spec2))


def test_dyades_ucdp(tmp_path):
    import lecture_cartes as lc
    import adaptateurs as ad
    lec = {"date": "date_start", "pays": "country", "somme": "best", "dyades": {"colonnes": ["side_a", "side_b"]}}
    lignes = [{"date_start": "2025-06-13", "country": "Iran", "best": "10", "side_a": "Government of Israel",
               "side_b": "Government of Iran"},
              {"date_start": "2025-06-20", "country": "Israel", "best": "3", "side_a": "Government of Iran",
               "side_b": "Government of Israel"},
              {"date_start": "2025-08-02", "country": "Gaza", "best": "1", "side_a": "Government of Israel",
               "side_b": "Hamas"}]
    agg, dy = {}, {}
    lc.agreger(lignes, lec, "historique", lc.table_pays(), agg, set(), dy)
    spec = {"lecture": lec, "fichiers": [{"role": "historique"}]}
    (tmp_path / "cartes").mkdir()
    lc.ecrire_dyades(spec, dy, tmp_path / "cartes" / "ucdp-dyades-mois.csv")
    s = dict(ad.ucdp_dyade(tmp_path, "ISR", "IRN"))
    assert s["2025-06-01"] == 2 and s["2025-07-01"] == 0 and s["2025-08-01"] == 0
    assert dict(ad.ucdp_dyade(tmp_path, "IRN", "ISR", "somme"))["2025-06-01"] == 13
