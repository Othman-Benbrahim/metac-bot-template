"""0.10.43 : banc ForecastBench (appariement, construction, garde-fous ; sans réseau)."""
from __future__ import annotations

import asyncio
import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import alphabet_pipeline as ap  # noqa: E402
import banc_forecastbench as fb  # noqa: E402

Q = {"questions": [
    {"id": "SOFR", "source": "fred", "question": "Will X have increased by {resolution_date} vs {forecast_due_date}?",
     "background": "b", "resolution_criteria": "r", "url": "u", "freeze_datetime": "2026-10-15T00:00:00+00:00",
     "freeze_datetime_value": "4.1", "freeze_datetime_value_explanation": "taux"},
    {"id": "11045", "source": "metaculus", "question": "Will a Democrat win?", "freeze_datetime_value": "0.6"},
    {"id": ["A", "B"], "source": "fred", "question": "combo"}]}
R = {"resolutions": [
    {"id": "SOFR", "source": "fred", "resolution_date": "2026-11-24", "resolved_to": 0.0, "resolved": True},
    {"id": "SOFR", "source": "fred", "resolution_date": "2026-11-01", "resolved_to": 1.0, "resolved": True},
    {"id": "11045", "source": "metaculus", "resolution_date": "2026-11-01", "resolved_to": 0.6, "resolved": False},
    {"id": ["A", "B"], "source": "fred", "resolution_date": "2026-11-01", "resolved_to": 1.0, "resolved": True}]}


class Tests(unittest.TestCase):
    def test_banc(self):
        items = fb.apparier(Q, R)
        self.assertEqual(len(items), 1)                                   # marché et combinée écartés
        self.assertEqual((items[0]["resolution_date"], items[0]["issue"]), ("2026-11-01", 1))   # premier horizon
        x = fb.construire(items[0], "2026-10-25")
        self.assertEqual(x["titre"], "Will X have increased by 2026-11-01 vs 2026-10-25?")
        self.assertIn("4.1", x["contexte"])
        self.assertTrue(x["qid"].startswith("fb:2026-10-25:fred:SOFR:"))
        self.assertNotIn("metaculus", fb.SOURCES_SERIES)
        self.assertEqual(fb.apparier(Q, R, ("metaculus",)), [])             # jamais de cote de foule : non résolue
        j = fb.jeux_candidats(date(2026, 11, 11), date(2026, 9, 1))
        self.assertEqual(j[:3], ["2026-10-25", "2026-10-11", "2026-09-27"])
        self.assertTrue(all(d > "2026-09-01" for d in j))


    def test_b_calcule(self):
        self.assertLess(fb.b_acled(0.0), 0.06)                      # aucun événement en 360 jours : rare
        self.assertAlmostEqual(fb.b_acled(160.0), 0.5, delta=0.03)   # gros comptes : environ une chance sur deux
        pts = [{"date": f"2026-{1 + i // 28:02d}-{1 + i % 28:02d}", "valeur": float(i)} for i in range(200)]
        f, k, n = fb.b_hausse(pts, 7, date(2026, 10, 25))
        self.assertGreater(f, 0.9)                                   # série toujours croissante
        self.assertIsNone(fb.b_hausse(pts[:5], 7, date(2026, 10, 25)))
        x = {"resolution": "2026-11-01"}
        q = {"source": "yfinance", "question": "Will A have a higher rate of return than B between ...?", "id": "A_B"}
        v = asyncio.run(fb.vue_calculee(x, q, "2026-10-25"))
        self.assertEqual(v["frequence"], 0.5)
        self.assertIsNone(ap.controle_vue(v, "2026-10-25"))          # la vue passe les contrôles du bot
        q2 = {"source": "acled", "freeze_datetime_value": "0.25", "freeze_datetime": "2026-10-15T00:00:00+00:00"}
        v2 = asyncio.run(fb.vue_calculee(x, q2, "2026-10-25"))
        self.assertIsNone(ap.controle_vue(v2, "2026-10-25"))
        x3 = dict(x, criteres="Résolu OUI si …", url="https://acleddata.com", source="acled", titre="t")
        v3 = asyncio.run(fb.vue_calculee(x3, q2, "2026-10-25"))
        self.assertTrue(v3["resolution"] and v3["source_resolution"]["emetteur"] == "ACLED")   # 0.10.46
        # 0.10.47 : la vue calculée passe la validation du MOTEUR (dossier complet), pas seulement celle du bot
        import json as _j
        m = ap._moteur()
        plan = {"evenement": {"carte": "SEU", "strate": 7, "type": "apparait"}, "semantique": "au-moins-une-fois"}
        v4 = asyncio.run(fb.vue_calculee(x3, q, "2026-10-25"))
        for vv in (v3, v4):
            evt, _ = ap.evenement_depuis(plan, vv)
            d = _j.loads(ap.lire_ref("assets/dossier.exemple.json"))
            d["evenements"] = [evt]
            m.dossier_valider(d)

    def test_reparations(self):
        d = {"mots": [{"carte": "POL", "strate": 6, "intensite": "f", "portee": "aucune"}], "candidats": ["POL@6"],
             "rejets": {"POL@6": "x"}, "_categories_rejet": {"POL@6": "aucun_fait"},
             "liaisons": [{"de": "POL@6", "type": "renforcement", "vers": "CTR@6", "preuve": "fait daté"}, {"bizarre": 1},
                          "trop court", "POL@6 renforcement CTR@6"]}
        notes = ap.reparer_dossier(d, {"candidats": ["CTR@6", "SEU@7"]})
        self.assertNotIn("POL@6", d["rejets"])                       # ancrée : plus rejetée
        self.assertEqual(d["candidats"], ["POL@6", "CTR@6"])          # complétée par le plan, même strate
        self.assertIn("non_cherchee", d["rejets"]["CTR@6"])
        self.assertEqual(d["liaisons"], [])          # 0.10.52 : CTR@6 n'est pas un mot de l'état (le moteur refusait)
        self.assertTrue(any("mot absent" in n for n in notes))
        d3 = {"mots": [{"carte": c_, "strate": 6, "intensite": "f", "portee": "aucune"} for c_ in ("POL", "CTR")],
              "candidats": [], "rejets": {},
              "liaisons": [{"de": "POL@6", "type": "renforcement", "vers": "CTR@6", "preuve": "fait daté"},
                           "POL@6 tension CTR@6"]}
        ap.reparer_dossier(d3, {"candidats": []})
        self.assertEqual(d3["liaisons"], ["POL@6 renforcement CTR@6"])   # la seconde, sans preuve, est retirée
        self.assertEqual(d3["preuves_liaisons"], ["fait daté"])
        self.assertGreaterEqual(len(notes), 4)
        self.assertEqual(ap.cle_normale("POLARITÉ@13_portee"), "POL@13")
        self.assertEqual(ap.code_carte("POL@6"), "POL")
        # 0.10.46 : clé sans strate, rejet hors des candidates, contre-candidate manquante
        d2 = {"mots": [{"carte": "INC", "strate": 6, "intensite": "f", "portee": "aucune"}], "candidats": ["INC", "CTR@6"],
              "rejets": {"CTR@6": "a", "SEU@6": "b"}, "_categories_rejet": {}, "liaisons": [], "contre_candidate": None}
        ap.reparer_dossier(d2, {"evenement": {"carte": "SEU", "strate": 6}, "candidats": []})
        self.assertEqual(d2["candidats"], ["INC@6", "CTR@6", "SEU@6"])
        self.assertEqual(d2["contre_candidate"], ["CTR@6"])

    def test_reparations_regles(self):
        # 0.10.48 : A7, A6/test/garantie, questions — la conséquence écrite de chaque règle, jamais un renforcement
        m = ap._moteur()
        d = {"mots": [{"carte": "TRC", "strate": 6, "intensite": "f", "portee": "substantielle"},
                      {"carte": "CTR", "strate": 6, "intensite": "F", "portee": "substantielle"},
                      {"carte": "HIE", "strate": 6, "intensite": "f"},
                      {"carte": "INC", "strate": 6, "intensite": "F", "portee": "aucune", "a6": ""},
                      {"carte": "POL", "strate": 6, "intensite": "f", "portee": "marginale", "test": "marteau"}],
             "candidats": [], "rejets": {}, "liaisons": [],
             "questions": [{"question": "A ?", "si_oui": "POLARITÉ@6", "si_non": "POLARITÉ@6"},
                           {"question": "B ?", "si_oui": "Les deux", "si_non": "x"}]}
        ap.reparer_dossier(d, {"evenement": {"carte": "SEU", "strate": 6}})
        mots = {f"{x['carte']}@{x['strate']}": x for x in d["mots"]}
        self.assertNotIn("TRC@6", mots)                                      # substantielle sur f : rejet
        self.assertNotIn("HIE@6", mots)                                      # portée absente : non retenu
        self.assertEqual((mots["CTR@6"]["intensite"], mots["CTR@6"]["force_initiale"]), ("f", "F"))
        self.assertEqual(mots["INC@6"]["intensite"], "f")                    # A6 vide : au plus f
        self.assertNotIn("test", mots["POL@6"])
        self.assertIn("TRC@6", d["rejets"])
        fm = set(mots)
        self.assertEqual(m.controle_questions(d["questions"], fm, True, True), [])
        self.assertEqual(d["questions"][0]["si_non"], "indetermine")

    def test_averti_52(self):
        # 0.10.52 (skill 0.7.75, §51) : averti admis et peut viser l'événement ; source absente → retiré ;
        # liaison hors liste gardée à part ; seules les « averti » partent au moteur en --liaison
        d = {"mots": [{"carte": "POL", "strate": 13, "intensite": "f", "portee": "aucune"}],
             "candidats": ["POL@13", "INC@13"], "rejets": {"INC@13": "[non_cherchee] x"},
             "liaisons": ["POL@13 averti SEU@13", "CTR@13 averti SEU@13", "POL@13 informe SEU@13"],
             "preuves_liaisons": ["hausse datée, précédent nommé", "x", "y"], "questions": []}
        ap.reparer_dossier(d, {"evenement": {"carte": "SEU", "strate": 13}, "candidats": []}, "2026-10-25")
        self.assertEqual(d["liaisons"], ["POL@13 averti SEU@13"])
        self.assertEqual(d["preuves_liaisons"], ["hausse datée, précédent nommé"])
        self.assertEqual(d["_liaisons_hors_liste"], ["POL@13 informe SEU@13"])
        from unittest import mock
        vu = {}
        def faux_run(cmd, **kw):
            vu["cmd"] = cmd
            return mock.Mock(returncode=0, stdout="{}", stderr="")
        with mock.patch.object(ap.subprocess, "run", faux_run):
            ap.appeler_moteur({"liaisons": ["POL@13 averti SEU@13", "POL@13 tension CTR@13"]}, "[x]", "SEUIL@13 apparait",
                              "presence", "2026-10-25", {"frequence": 0.1})
        i = [k for k, x in enumerate(vu["cmd"]) if x == "--liaison"]
        self.assertEqual([vu["cmd"][k + 1] for k in i], ["POL@13 averti SEU@13"])

    def test_reparations_51(self):
        # 0.10.51 : liaison inconnue, corroboration à une source, extrait trop long, garantie postérieure (B1),
        # strate sans seconde candidate, candidate sans motif de rejet
        bon = {"mecanisme": "m", "attendu": "a", "contredirait": "c",
               "support": {"type": "donnee", "reference": "r", "disponible_le": "2026-11-10"}}
        d = {"mots": [{"carte": "POL", "strate": 13, "intensite": "f", "portee": "aucune", "source": "Reuters",
                       "corroboration": "independantes", "independance": {"critere": "origine", "motif": "x"},
                       "passage": {"localisation": "p1", "relation": "soutient", "extrait": "x" * 400},
                       "garantie": bon}],
             "candidats": ["POL@13", "INC@13"], "rejets": {}, "liaisons": ["POL@13 informe SEU@13", "POL@13 tension CTR@13"],
             "questions": []}
        ap.reparer_dossier(d, {"evenement": {"carte": "SEU", "strate": 13}, "candidats": []}, "2026-10-25")
        m0 = d["mots"][0]
        self.assertEqual(m0["corroboration"], "unique")
        self.assertNotIn("independance", m0)
        self.assertLessEqual(len(m0["passage"]["extrait"]), 300)
        self.assertNotIn("garantie", m0)                                   # support postérieur : retiré (B1)
        self.assertEqual(d["liaisons"], [])          # CTR@13 n'est pas un mot de l'état : le moteur aurait refusé
        self.assertNotIn("preuves_liaisons", d)
        self.assertIn("INC@13", d["rejets"])                               # candidate sans motif : « non cherchée »
        d2 = {"mots": [{"carte": "POL", "strate": 13, "intensite": "f", "portee": "aucune"}], "candidats": [],
              "rejets": {}, "liaisons": [], "questions": []}
        ap.reparer_dossier(d2, {"evenement": {"carte": "SEU", "strate": 13}, "candidats": []}, "2026-10-25")
        self.assertGreaterEqual(len([c for c in d2["candidats"] if c.endswith("@13")]), 2)   # voisine ajoutée


if __name__ == "__main__":
    unittest.main()
