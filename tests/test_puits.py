"""Tests hors ligne des puits de données (0.7.0)."""
import asyncio
import json
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
        self.assertEqual(r["n"], 10)
        self.assertEqual(r["k"], 10)
        self.assertAlmostEqual(r["frequence"], 1 - 1 / 20)             # jamais 1 : le moteur exige ]0, 1[

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
            choisie, suivi = asyncio.run(ap.vues_exterieures(q, {}, [], [], llm_vue, "2026-01-01", 120, None, vue))
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
            choisie, suivi = asyncio.run(ap.vues_exterieures(q, {}, [], [], llm_vue, "2026-01-01", 120, None, None, ancrage))
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

    def test_extraire_json_robuste(self):
        self.assertEqual(ap.extraire_json('voici {"a": 1} puis {"b": 2}'), {"a": 1})
        self.assertEqual(ap.extraire_json('{"a": 1,}'), {"a": 1})

    def test_score_compte_en_ombre(self):
        import score_registre as sr
        paires = [({"compte": 0.8, "B": 0.5, "_corr": "proche"}, 1) for _ in range(6)]
        r = sr.comparer(paires, "compte", "B")
        self.assertGreater(r["gain_log_moyen"], 0)

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
