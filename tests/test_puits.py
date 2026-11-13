"""Tests hors ligne des puits de données (0.7.0)."""
import asyncio
import json
import math
import os
import sys
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

import os as _os  # noqa: E402
import tempfile as _tempfile  # noqa: E402
# 0.7.4 : JAMAIS le vrai registre dans les tests (des lignes fictives y avaient été écrites puis publiées).
_os.environ["ALPHABET_REGISTRE"] = _tempfile.mkdtemp(prefix="registre-test-")  # 0.8.0 : forcé, pas setdefault
_os.environ["ALPHABET_TESTS"] = "1"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import alphabet_pipeline as ap  # noqa: E402
import alphabet_puits as apz  # noqa: E402


def releve(points, debut=None, limite=None):
    return {"source": "S", "titre": "T", "url": "https://s", "debut": debut, "date_limite": limite, "points": points}


class TestsCompte(unittest.TestCase):
    def test_evenement_fenetres_disjointes(self):
        # un événement par an pendant 10 ans, fenêtres de 365 jours : chaque fenêtre en contient un → k = n
        pts = [{"date": f"{2015 + i}-06-01", "valeur": None} for i in range(10)]
        r = apz.compter(releve(pts, debut="2015-01-01"), 365, "evenement", fin=date(2025, 1, 1))
        # 0.9.5 (banc du compte) : taux de Poisson sur tout l'historique, P(au moins un en un an) = 1 − exp(−taux·365)
        self.assertEqual(r["methode"], "taux_poisson")
        self.assertEqual(r["k"], 10)
        self.assertAlmostEqual(r["frequence"], 1 - math.exp(-10.5 / 3653 * 365), places=4)   # ≈ 0,65 (vrai : 0,63)
        # niveaux : écart au seuil depuis la DERNIÈRE valeur, bootstrap des pas observés
        niv = [{"date": f"20{10 + i // 12:02d}-{i % 12 + 1:02d}-01", "valeur": float(i % 5)} for i in range(120)]
        r = apz.compter(releve(niv), 90, "atteint", 100.0, ">=", fin=date(2020, 1, 1), nature="niveau")
        self.assertIn(r["methode"], ("bootstrap_pas", "ar1", "ar1_melange"))   # 0.10.20 : dents de scie = retour à la moyenne
        self.assertLess(r["frequence"], 0.01)                            # seuil hors d'atteinte en 90 jours

    def test_atteint_et_franchit(self):
        pts = [{"date": f"20{a:02d}-01-01", "valeur": v} for a, v in zip(range(10, 22), [1, 1, 5, 5, 1, 1, 1, 5, 1, 1, 1, 1])]
        att = apz.compter(releve(pts), 365, "atteint", 4, ">=", fin=date(2021, 1, 2))
        fr = apz.compter(releve(pts), 365, "franchit", 4, ">=", fin=date(2021, 1, 2))
        self.assertEqual((att["k"], att["n"]), (3, 11))
        self.assertEqual(fr["k"], 2)                                   # 2013 était déjà au-dessus : pas un franchissement
        self.assertIsNone(apz.compter(releve(pts[:3]), 365, "atteint", 4)["frequence"])    # < 5 fenêtres

    def test_agregation_typee(self):
        pts = [{"date": f"20{a:02d}-01-01", "valeur": 5.0} for a in range(10, 22)]
        r = apz.compter(releve(pts), 365, "atteint", 50, ">=", "annee", fin=date(2021, 1, 2), nature="niveau")
        self.assertIsNone(r["frequence"])
        self.assertIn("niveaux", r["motif"])
        self.assertIn("sans seuil", apz.compter(releve(pts), 365, "franchit", None)["motif"])

    def test_agregation_mensuelle(self):
        pts = [{"date": "2024-01-03", "valeur": 30}, {"date": "2024-01-20", "valeur": 30}, {"date": "2024-02-10", "valeur": 10}]
        ag = apz._agreger(pts, "mois")
        self.assertEqual(ag, [{"date": "2024-01-01", "valeur": 60.0}, {"date": "2024-02-01", "valeur": 10.0}])

    def test_borne_a_la_date(self):
        r = apz._releve("S", "T", "u", [{"date": "2026-01-01"}, {"date": "2026-12-01"}], date(2026, 6, 1))
        self.assertEqual([p["date"] for p in r["points"]], ["2026-01-01"])


class Rep:
    def __init__(self, corps):
        self.corps = corps

    def raise_for_status(self):
        pass

    def json(self):
        return self.corps

    @property
    def text(self):
        return self.corps if isinstance(self.corps, str) else json.dumps(self.corps)


def client(corps, vu):
    class Client:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            pass

        async def get(self, url, params=None):
            vu.append((url, params))
            return Rep(corps)
    return Client


class TestsConnecteurs(unittest.TestCase):
    def test_fred_millesime_et_cle(self):
        vu = []
        corps = {"observations": [{"date": "2026-01-01", "value": "4.1"}, {"date": "2026-02-01", "value": "."}]}
        with mock.patch.dict(os.environ, {"FRED_API_KEY": "k"}), mock.patch.object(apz.httpx, "AsyncClient", client(corps, vu)):
            r = asyncio.run(apz.fred("UNRATE", date(2026, 3, 1)))
        self.assertEqual(vu[0][1]["realtime_end"], "2026-03-01")     # ALFRED : la série telle qu'elle était publiée
        self.assertEqual(len(r["points"]), 1)                          # « . » (valeur manquante) écarté
        with mock.patch.dict(os.environ, {"FRED_API_KEY": ""}):
            with self.assertRaises(apz.SansCle):
                asyncio.run(apz.fred("UNRATE"))

    def test_wikipedia_revision_anterieure(self):
        vu = []
        corps = {"query": {"pages": [{"title": "X", "revisions": [{"revid": 7, "timestamp": "2026-05-01T10:00:00Z",
                                                                    "slots": {"main": {"content": "'''X''' est [[Y|un pays]]."}}}]}]}}
        with mock.patch.object(apz.httpx, "AsyncClient", client(corps, vu)):
            r = asyncio.run(apz.wikipedia("X", "en", date(2026, 6, 1)))
        self.assertEqual(vu[0][1]["rvstart"], "2026-06-01T23:59:59Z")
        self.assertEqual(vu[0][1]["rvdir"], "older")
        self.assertIn("X est un pays", r["points"][0]["extrait"])
        self.assertIn("oldid=7", r["url"])

    def test_wikitexte_imbrique(self):
        t = apz._texte_wiki("{{Infobox conflict\n| date = {{start date|2023|4|15}}\n| place = [[Sudan]]}}\nThe war began.")
        self.assertEqual(t, "The war began.")

    def test_retard_de_publication(self):
        # 0.8.0 (audit M-05) : un point n'est connu qu'après sa publication, pas à la date de sa période
        pts = [{"date": "2025-12-31", "valeur": 1.0}, {"date": "2024-12-31", "valeur": 2.0}]
        r = apz._releve("S", "T", "u", pts, date(2026, 6, 1), retard=200)
        self.assertEqual([p["date"] for p in r["points"]], ["2024-12-31"])     # 2025 paraît vers juillet 2026
        vu = []
        csv_ = "TIME_PERIOD,OBS_VALUE\n2026-04,1.1\n2026-05,1.2\n2026-05-29,1.3\n"
        with mock.patch.object(apz.httpx, "AsyncClient", client(csv_, vu)):
            r = asyncio.run(apz.bce("EXR/M.USD.EUR.SP00.A", date(2026, 6, 1)))
        self.assertEqual([p["date"] for p in r["points"]], ["2026-04-01", "2026-05-29"])   # mai (mensuel) pas encore

    def test_gaza_borne_et_retard(self):                          # 0.10.0
        vu = []
        corps = [{"report_date": "2026-05-30", "killed_cum": 100}, {"report_date": "2026-05-31", "killed_cum": 110},
                 {"report_date": "2026-06-01", "killed_cum": 120}]
        with mock.patch.object(apz.httpx, "AsyncClient", client(corps, vu)):
            r = asyncio.run(apz.gaza("killed_cum", "gaza", date(2026, 6, 1)))
        self.assertEqual([p["valeur"] for p in r["points"]], [100, 110])      # le rapport du jour paraît le lendemain
        self.assertIn("ministère de la Santé de Gaza", r["source"])
        self.assertTrue(vu[0][0].endswith("casualties_daily.json"))

    def test_sanctions_ue_une_entree_par_entite(self):
        vu = []
        csv_ = ("\ufefffileGenerationDate;Entity_LogicalId;Entity_DesignationDate;Entity_SubjectType;"
                "Entity_Regulation_PublicationDate;Entity_Regulation_Programme;NameAlias_WholeName\n"
                "2026-11-01;1;2022-03-15;person;2022-03-16;RUS;Ivan Petrov\n"
                "2026-11-01;1;2022-03-15;person;2022-03-16;RUS;Ivan PETROV\n"
                "2026-11-01;2;2026-07-01;enterprise;2026-07-02;RUS;Acme LLC\n"
                "2026-11-01;4;;person;2023-05-01;RUS;Sans Date\n"
                "2026-11-01;3;2023-01-10;person;2023-01-11;IRN;Ali X\n")
        with mock.patch.object(apz.httpx, "AsyncClient", client(csv_, vu)):
            r = asyncio.run(apz.sanctions_ue(programme="RUS", avant=date(2026, 6, 1)))
        self.assertEqual(len(r["points"]), 2)                                   # Acme désignée après la borne ; IRN exclu
        self.assertEqual(r["points"][0]["date"], "2022-03-15")
        self.assertEqual(r["points"][1]["date"], "2023-05-01")                  # 0.10.1 : repli sur la publication
        self.assertIn("biais", r)

    def test_oms_annuel_retarde(self):
        vu = []
        corps = {"value": [{"TimeDim": 2024, "NumericValue": 82.5, "Dim1": "SEX_BTSX"},
                           {"TimeDim": 2025, "NumericValue": 82.7, "Dim1": "SEX_BTSX"}]}
        with mock.patch.object(apz.httpx, "AsyncClient", client(corps, vu)):
            r = asyncio.run(apz.oms("WHOSIS_000001", "FRA", "SEX_BTSX", date(2026, 6, 1)))
        self.assertEqual([p["date"] for p in r["points"]], ["2024-12-31"])     # 2025 pas encore publiée
        self.assertIn("Dim1 eq 'SEX_BTSX'", vu[0][1]["$filter"])

    def test_ecosystemes_versions(self):
        vu = []
        corps = [{"number": "2.0.0", "published_at": "2026-01-10T00:00:00Z"},
                 {"number": "2.1.0", "published_at": "2026-07-01T00:00:00Z"}]
        with mock.patch.object(apz.httpx, "AsyncClient", client(corps, vu)):
            r = asyncio.run(apz.ecosystemes("pypi.org", "numpy", date(2026, 6, 1)))
        self.assertEqual([p["titre"] for p in r["points"]], ["version 2.0.0"])
        self.assertIn("pypi.org/packages/numpy/versions", vu[0][0])

    def test_epoch_modeles(self):                                  # 0.10.10
        csv_ = ("Model,Organization,Publication date,Domain,Country (of organization),Training compute (FLOP),"
                "Frontier model,Last modified\n"
                "A1,OpenAI,2025-03-01,Language,United States,3e25,True,2025-03-05\n"
                "B1,Google,2026-02-01,Language,United States,5e25,True,2026-02-02\n"
                "C1,OpenAI,2025-09-01,Language,United States,1e24,False,2026-08-01\n"
                "D1,OpenAI,2026-08-01,Language,United States,9e25,True,2026-08-01\n")
        with mock.patch.object(apz, "_get", mock.AsyncMock(return_value=csv_)):
            r = asyncio.run(apz.epoch_modeles(organisation="openai", avant=date(2026, 6, 1)))
            self.assertEqual([p["titre"] for p in r["points"]], ["A1 (OpenAI)", "C1 (OpenAI)"])   # D1 après la date
            self.assertIn("1 ligne(s) antérieure(s) modifiée(s)", r["revisions"])
            self.assertIn("CC BY 4.0", r["licence"])
            f = asyncio.run(apz.epoch_modeles(frontiere=True, mesure="calcul", avant=date(2026, 6, 1)))
            self.assertEqual([p["valeur"] for p in f["points"]], [3e25, 5e25])

    def test_epoch_benchmarks(self):                               # 0.10.10
        import io as _io
        import zipfile as _zf
        b = _io.BytesIO()
        with _zf.ZipFile(b, "w") as z:
            z.writestr("benchmarks/gpqa_diamond.csv", "Model version,Best score (across scorers),Release date\n"
                                                      "m1,0.61,2025-01-10\nm2,72%,2026-03-01\nm3,0.9,2026-09-01\n")
            z.writestr("benchmarks/other.csv", "Model version,Best score (across scorers),Release date\nx,0.1,2025-01-01\n")
        with mock.patch.object(apz, "_get_octets", mock.AsyncMock(return_value=b.getvalue())):
            r = asyncio.run(apz.epoch_benchmarks("GPQA Diamond", avant=date(2026, 6, 1)))
        self.assertEqual([(p["titre"], p["valeur"]) for p in r["points"]], [("m1", 0.61), ("m2", 0.72)])
        self.assertEqual(r["fichier"], "benchmarks/gpqa_diamond.csv")

    def test_fts_refuse_le_passe(self):
        with self.assertRaises(RuntimeError):
            asyncio.run(apz.fts("SDN", None, date(2025, 1, 1)))

    def test_catalogue_sans_cle_cache_la_source(self):
        t = apz.catalogue_texte({"FRED_API_KEY": "k"})
        self.assertIn("- fred", t)
        self.assertNotIn("- ucdp", t)                                  # UCDP_TOKEN absent : non proposé
        self.assertNotIn("- firms", t)


class TestsPipeline(unittest.TestCase):
    def test_compte_devient_une_vue_controlee(self):
        q = ap.Question(id=1, url="u", titre="Le chômage dépassera-t-il 5 % ?", contexte="", criteres="UNRATE ≥ 5",
                        precisions="", resolution=date(2027, 1, 1))
        demande = {"appels": [{"source": "fred", "params": {"serie": "UNRATE"}}],
                   "compte": {"appel": 0, "mode": "atteint", "seuil": 5, "sens": ">=", "agregation": None,
                              "classe_de_reference": "fenêtres de 120 jours où le chômage américain a atteint 5 %",
                              "ecart_critere": "identique : même série", "resolution": "UNRATE ≥ 5",
                              "source_resolution": {"emetteur": "BLS"}}}

        async def llm(c):
            return json.dumps(demande)
        pts = [{"date": f"{2000 + i // 12}-{i % 12 + 1:02d}-01", "valeur": 6.0 if (i // 12) % 4 == 0 else 4.0}
               for i in range(26 * 12)]

        async def appeler(src, params, avant):
            return releve(pts, limite=avant.isoformat())
        with mock.patch.object(apz, "appeler", appeler):
            tr, donnees, vue = asyncio.run(ap.puits(q, {"evenement": None}, llm, "2026-01-01", 120, 3))
        self.assertEqual(tr["appels"][0]["statut"], "ok")
        self.assertTrue(vue["compte_calcule"])
        self.assertIn("[R3]", vue["fondement"])
        self.assertTrue(0 < vue["frequence"] < 1)
        self.assertIsNone(ap.controle_vue(vue, "2026-01-01"))
        self.assertEqual(donnees[0]["moteur"], "puits-fred")

        async def llm_vue(c):
            return json.dumps({"frequence": 0.9, "classe_de_reference": "c", "source": "s", "fondement": "[R1]",
                               "periode": "2000-2025", "disponible_le": "2025-12-01", "expression": "9/10"})
        anciens = ap.NB_VUES
        ap.NB_VUES = 1
        try:
            choisie, suivi = asyncio.run(ap.vues_exterieures(q, {}, [{"requete": "r", "resultat": "x"}] * 2, [], llm_vue, "2026-01-01", 120, None, vue))
        finally:
            ap.NB_VUES = anciens
        self.assertEqual(suivi["valides"], 1)                        # 0.8.0 (audit M-02) : le compte n'est plus une vue
        self.assertIsNone(suivi["vue_calculee"]["refus"])
        self.assertTrue(choisie.get("compte_calcule"))               # compte exact : il EST le taux de base
        self.assertAlmostEqual(suivi["p_modele"], 0.9)               # la médiane du modèle reste en ombre

    def test_compte_proche_ancre_les_vues(self):
        q = ap.Question(id=1, url="u", titre="t", contexte="", criteres="c", precisions="", resolution=date(2027, 1, 1))
        ancrage = {"frequence": 0.25, "fondement": "[R2] compte calculé par le code (puits de données)",
                   "source": "FRED — UNRATE", "calcul": "3 fenêtre(s) sur 12", "periode": "2000-2025",
                   "ecart_critere": "série nationale, la question vise un État", "correspondance": "proche"}
        t = ap.consigne_vue(q, {}, [], "2026-01-01", 120, None, None, ancrage)
        self.assertIn("PARS DE CE COMPTE", t)
        self.assertIn("usage_compte", t)
        self.assertNotIn("usage_compte", ap.consigne_vue(q, {}, [], "2026-01-01", 120))
        vus = []

        async def llm_vue(c):
            vus.append("PARS DE CE COMPTE" in c)
            f = 0.3 if len(vus) == 1 else 0.4
            return json.dumps({"frequence": f, "classe_de_reference": "c", "source": f"s{len(vus)}", "fondement": "[R2]",
                               "periode": "2000-2025", "disponible_le": "2025-12-01", "usage_compte": "ajuste",
                               "expression": repr(f)})
        anciens = ap.NB_VUES
        ap.NB_VUES = 2
        try:
            choisie, suivi = asyncio.run(ap.vues_exterieures(q, {}, [{"requete": "r", "resultat": "x"}] * 2, [], llm_vue, "2026-01-01", 120, None, None, ancrage))
        finally:
            ap.NB_VUES = anciens
        self.assertEqual(vus, [True, False])                         # 0.8.0 (audit M-03) : seule la 1re vue est ancrée
        self.assertEqual(suivi["valides"], 2)                        # le compte proche n'entre pas dans les vues
        self.assertEqual(suivi["usages_compte"], ["ajuste"])
        self.assertAlmostEqual(suivi["p_sans_ancre"], 0.4)           # la mesure aveugle, pour juger le compte
        self.assertEqual(suivi["sources"], ["s1", "s2"])
        self.assertFalse(choisie.get("compte_calcule"))

    def test_expression_recalculee(self):
        v = {"frequence": 0.025, "expression": "1 - (1 - 3/40) ** (120/365)"}
        self.assertIsNone(ap.controle_calcul(v))
        self.assertAlmostEqual(v["frequence"], 1 - (1 - 3 / 40) ** (120 / 365))
        # registre, question 43329 : déclaré 0,00037 pour un calcul qui donne 0,0016
        v = {"frequence": 0.00037, "expression": "0.0435 * 54/1461"}       # 43329 : 0,00037 pour un calcul à 0,0016
        self.assertIsNone(ap.controle_calcul(v))                            # 0.8.1 : la formule l'emporte
        self.assertAlmostEqual(v["frequence"], 0.0435 * 54 / 1461)
        self.assertTrue(v["calcul_corrige"])
        self.assertIn("déjà utilisée", ap.source_reprise({"source": "Registre des notifications de l'article 50 (Commission)"},
                                                         ["Registre des notifications de l'article 50 du TUE"]))
        self.assertIsNone(ap.source_reprise({"source": "Forbes 400"}, ["Bloomberg Billionaires Index"]))
        self.assertIn("sans expression", ap.controle_calcul({"frequence": 0.2}))
        self.assertIn("illisible", ap.controle_calcul({"frequence": 0.2, "expression": "__import__('os')"}))

    def test_references_inexistantes(self):
        self.assertIn("[R7] inexistante", ap.controle_references({"fondement": "recherche [R7]"}, 4, 0))
        self.assertIn("[M2]", ap.controle_references({"calcul": "2 OUI sur [M1] [M2]"}, 4, 1))
        self.assertIsNone(ap.controle_references({"fondement": "[R2] et [M1]"}, 4, 1))
        d = {"mots": [{"carte": "SEU", "strate": 7, "fait": "Exercice militaire annoncé.", "source_url":
                       "https://www.reuters.com/world/x/?utm=1", "passage": [{"extrait": "exercice militaire annonce"}]}]}
        a_ = ap.controle_attribution(d, "[R1] exercice militaire annoncé — https://www.reuters.com/world/x")
        self.assertTrue(a_["detail"]["SEU@7"]["url_retrouvee"])
        d["mots"][0]["source_url"] = "https://exemple.org/invente"
        self.assertFalse(ap.controle_attribution(d, "[R1] exercice militaire annoncé")["detail"]["SEU@7"]["url_retrouvee"])

    def test_extraire_json_robuste(self):
        self.assertEqual(ap.extraire_json('voici {"a": 1} puis {"b": 2}'), {"a": 1})
        self.assertEqual(ap.extraire_json('{"a": 1,}'), {"a": 1})

    def test_score_compte_en_ombre(self):
        import score_registre as sr
        paires = [({"compte": 0.8, "B": 0.5, "_corr": "proche"}, 1) for _ in range(6)]
        r = sr.comparer(paires, "compte", "B")
        self.assertGreater(r["gain_log_moyen"], 0)

    def test_ucdp_candidates_66(self):
        import alphabet_puits as pu
        # un mois n'est pris que s'il était publié à la date limite (fin du mois suivant)
        self.assertEqual(pu.versions_candidates("2015-01-01", date(2026, 4, 15), "26.1"), ["26.0.1", "26.0.2"])
        self.assertEqual(pu.versions_candidates("2026-03-01", date(2026, 11, 13), "26.1"),
                         ["26.0.3", "26.0.4", "26.0.5", "26.0.6", "26.0.7", "26.0.8", "26.0.9"])
        self.assertEqual(pu.versions_candidates("2015-01-01", date(2026, 1, 20), "26.1"), [])
        vus = []

        async def faux_get(url, params=None, headers=None, json_=True):
            vus.append(url.rsplit("/", 1)[1])
            if url.endswith("26.0.3"):
                raise RuntimeError("pas encore publiée")
            return {"Result": [{"date_start": "2026-02-10", "best": 3, "conflict_name": "c"}], "NextPageUrl": None}
        with mock.patch.object(pu, "_get", faux_get), mock.patch.dict(os.environ, {"UCDP_TOKEN": "x"}):
            r = asyncio.run(pu.ucdp(avant=date(2026, 11, 13)))
        self.assertEqual(vus[:4], ["26.1", "26.0.1", "26.0.2", "26.0.3"])
        self.assertIn("candidates 26.0.1, 26.0.2", r.get("serie") or json.dumps(r, ensure_ascii=False))

    def test_sans_cle_ne_bloque_pas(self):
        q = ap.Question(id=1, url="u", titre="t", contexte="", criteres="c", precisions="", resolution=date(2027, 1, 1))

        async def llm(c):
            return json.dumps({"appels": [{"source": "ucdp", "params": {}}], "compte": None})
        with mock.patch.dict(os.environ, {"UCDP_TOKEN": ""}):
            tr, donnees, vue = asyncio.run(ap.puits(q, {}, llm, "2026-01-01", 30, 1))
        self.assertEqual(tr["appels"][0]["statut"], "sans_cle")
        self.assertEqual((donnees, vue), ([], None))



class TestsIsolement(unittest.TestCase):
    def test_le_vrai_registre_est_hors_de_portee(self):
        vrai = (Path(__file__).resolve().parents[1] / "registre").resolve()
        self.assertNotEqual(ap.REGISTRE.resolve(), vrai)

    def test_garde_refuse_le_vrai_registre(self):
        ancien, ap.REGISTRE = ap.REGISTRE, ap.VRAI_REGISTRE
        try:
            with self.assertRaises(ap.RegistreInterdit):
                ap.ecrire_registre({"question_id": "x", "bras": {"A": {"horodatage": "t"}}}, None)
        finally:
            ap.REGISTRE = ancien

    def test_sceau_du_dossier_relu(self):
        import score_registre as sr
        import tempfile as tf
        reg = Path(tf.mkdtemp(prefix="registre-dossier-"))
        (reg / "dossiers").mkdir()
        d = {"mots": [1]}
        (reg / "dossiers" / "q.json").write_text(json.dumps(d), encoding="utf-8")
        x = {"dossier_fichier": "dossiers/q.json", "dossier_sha256": ap.sceau(d)}
        self.assertEqual(sr.etat_dossier(reg, x), "conforme")
        (reg / "dossiers" / "q.json").write_text(json.dumps({"mots": [2]}), encoding="utf-8")
        self.assertEqual(sr.etat_dossier(reg, x), "different")
        self.assertEqual(sr.etat_dossier(reg, {"dossier_fichier": "dossiers/r.json"}), "absent")


if __name__ == "__main__":
    unittest.main()
