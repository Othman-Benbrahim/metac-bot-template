"""0.10.43 : banc ForecastBench (appariement, construction, garde-fous ; sans réseau)."""
from __future__ import annotations

import asyncio
import json
import os
import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import alphabet_pipeline as ap  # noqa: E402
import alphabet_pipeline as _ap_regle_ab
_ap_regle_ab.POSTER_AB = False   # 0.10.122 : tests écrits avant la règle AB ; la CI lance unittest, sans conftest
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

    def test_triplets_67(self):
        # 0.10.67 : triplets durs du monde synthétique (consigne du leurre, mesure)
        import monde_synthetique as ms
        c = ms.consigne_narrateur(["SEU@7", "CTR@7"], ["POL@7"], 7, "2026-11-13", 3, leurre="SEU@7")
        self.assertIn("SANS le remplir", c)
        c13 = ms.consigne_narrateur(["SEU@13", "CTR@13"], ["POL@13"], 13, "2026-11-13", 3)
        self.assertIn("partis politiques", c13)
        self.assertNotIn("SANS le remplir", c13)
        rows = [{"statut": "lue", "ancrees": {"SEU@7": "f", "CTR@7": "f"},
                 "triplet": {"carte_leurre": "SEU@7", "ancrees_accord": {"SEU@13": "f", "CTR@13": "f"},
                             "ancrees_leurre": {"CTR@7": "f"}}},                     # structure : réussi, discrimine
                {"statut": "lue", "ancrees": {"SEU@7": "f", "CTR@7": "f"},
                 "triplet": {"carte_leurre": "SEU@7", "ancrees_accord": {"POL@13": "f"},
                             "ancrees_leurre": {"SEU@7": "f", "CTR@7": "f"}}}]        # surface : échoue, suit
        r = ms.mesurer_triplets(rows)
        self.assertEqual((r["n"], r["triplets_reussis"], r["leurre_discrimine"], r["leurre_suit_la_surface"]),
                         (2, 1.0, 1, 1))

    def test_tiers_polarite_64(self):
        # 0.10.64 (skill 0.7.76, §52) : tiers gardé sur POL ; retiré ailleurs ou mal formé ; troisième pôle → POL retiré
        base = {"intensite": "f", "portee": "aucune"}
        d = {"mots": [dict(base, carte="POL", strate=7, tiers={"type": "mediateur", "qui": "Qatar", "fait": "médiation du 2026-10-02"}),
                      dict(base, carte="CTR", strate=7, tiers={"type": "aucun"}),
                      dict(base, carte="INC", strate=7, tiers={"type": "arbitre"})],
             "candidats": [], "rejets": {}, "liaisons": [], "questions": []}
        notes = ap.reparer_dossier(d, {"evenement": {"carte": "SEU", "strate": 7}, "candidats": []}, "2026-10-25")
        mots = {m["carte"]: m for m in d["mots"]}
        self.assertEqual(mots["POL"]["tiers"]["type"], "mediateur")
        self.assertNotIn("tiers", mots["CTR"])
        self.assertNotIn("tiers", mots["INC"])
        d2 = {"mots": [dict(base, carte="POL", strate=7, tiers={"type": "troisieme_pole", "qui": "x", "fait": "y"}),
                       dict(base, carte="CTR", strate=7)], "candidats": [], "rejets": {}, "liaisons": [], "questions": []}
        notes = ap.reparer_dossier(d2, {"evenement": {"carte": "SEU", "strate": 7}, "candidats": []}, "2026-10-25")
        self.assertEqual([m["carte"] for m in d2["mots"]], ["CTR"])
        self.assertTrue(any("troisième pôle" in n for n in notes))

    def test_recherches_candidates_68(self):
        # 0.10.68 : une carte visée par une recherche hors des candidates sort de la recherche ; une recherche sans
        # carte sort du dossier ; les candidates ne changent pas pour autant
        base = {"intensite": "f", "portee": "aucune"}
        d = {"mots": [dict(base, carte="CTR", strate=6)], "candidats": ["CTR@6", "HIE@6"],
             "rejets": {"HIE@6": "[aucun_fait] rien"}, "liaisons": [], "questions": [],
             "recherches": [{"famille": "contradiction", "cartes": ["RES@6"], "requete": "a", "executee": True},
                            {"famille": "discrimination", "cartes": ["HIE@6", "INC@6"], "requete": "b", "executee": True},
                            {"famille": "observation", "cartes": ["CTR@6"], "requete": "c", "executee": True}]}
        ap.reparer_dossier(d, {"evenement": {"carte": "SEU", "strate": 6}, "candidats": []}, "2026-10-25")
        self.assertEqual(d["candidats"], ["CTR@6", "HIE@6"])
        self.assertEqual([(r["requete"], r["cartes"]) for r in d["recherches"]], [("b", ["HIE@6"]), ("c", ["CTR@6"])])

    def test_ombre_absence_70(self):
        # 0.10.70 : B à cote × 0,5 pour les seuls états nuls d'absence ; jugée sur les lignes ≥ 0.10.70 seulement
        import score_registre as sr
        self.assertAlmostEqual(ap.ombre_absence(0.5, "structure_absente"), 1 / 3)
        self.assertAlmostEqual(ap.ombre_absence(0.2, "carte_visee_absente"), 0.25 * 0.5 / (1 + 0.25 * 0.5))
        self.assertIsNone(ap.ombre_absence(0.5, "angle_mort"))
        self.assertIsNone(ap.ombre_absence(0.5, "indetermine"))
        self.assertIsNone(ap.ombre_absence(None, "structure_absente"))
        s = sr.ombre_absence_suivi([(1 / 3, 0.5, 0, "0.10.70"), (1 / 3, 0.5, 0, "0.10.71"), (1 / 3, 0.5, 1, "0.10.55")])
        self.assertEqual(s["n_comptees"], 2)
        self.assertGreater(s["ombre_sur_B"]["gain_log_moyen"], 0)
        self.assertEqual(s["avant_enregistrement"]["n"], 1)
        self.assertIsNone(sr.ombre_absence_suivi([]))

    def test_auc_krippendorff_71(self):
        import score_registre as sr
        self.assertEqual(sr.auc([(0.9, 1), (0.1, 0)]), 1.0)
        self.assertEqual(sr.auc([(0.5, 1), (0.5, 0)]), 0.5)
        self.assertIsNone(sr.auc([(0.5, 1)]))
        self.assertAlmostEqual(sr.alpha_krippendorff({"a": [1, 1], "b": [2, 2], "c": [1, 1]})["alpha"], 1.0)
        # exemple de Krippendorff (2004) réduit : désaccord total sur deux valeurs → alpha négatif
        self.assertLess(sr.alpha_krippendorff({"a": [1, 2], "b": [2, 1]})["alpha"], 0)
        # questions incomplètes ignorées
        self.assertEqual(sr.alpha_krippendorff({"a": [1, None], "b": [1, 1], "c": [2, 2]})["unites"], 2)

    def test_ombres_auto_73(self):
        import ombres_auto as oa
        ex = [{"executee": True, "resultat": "La Fed relève le taux SOFR à 4,3 %.\n\nLa Fed relève le taux SOFR à 4,3 %.\n\n"
                                            "Match de football hier soir à Lyon."},
              {"executee": True, "moteur": "puits-fred", "resultat": "Relevé sans rapport apparent"}]
        f = oa.filtrer(ex, "Le taux SOFR sera-t-il plus haut ?")
        self.assertEqual([m for _, m in f["retires"]], ["doublon", "hors_question"])
        self.assertIn("Relevé sans rapport apparent", f["gardes"])          # les puits ne sont jamais filtrés
        m = oa.mesurer_filtrage(ex, "taux SOFR", [{"carte": "CTR", "strate": 6, "fait": "Match de football hier soir à Lyon"}])
        self.assertEqual(m["faits_perdus"], ["CTR@6"])
        self.assertTrue(oa.croissance([1, 1.1, 1.2, 1.3, 1.5, 1.8, 2.3]))
        self.assertFalse(oa.croissance([1, 2, 3, 4, 5, 6, 7]))             # hausse sans accélération
        saw = [0, 1, 2, 3, 0, 1, 2, 3, 0, 1, 2, 3, 0, 1, 2, 3, 0, 1, 2, 3]
        self.assertTrue(oa.periodicite(saw))
        self.assertFalse(oa.periodicite(list(range(20))))
        self.assertTrue(oa.seuil([1, 2, 3], 2.5))
        self.assertFalse(oa.seuil([1, 2, 3], None))
        calme = [i % 2 * 0.1 for i in range(30)]
        self.assertTrue(oa.incertitude(calme + [0, 3, -2, 4, -3, 5, -4, 3, -2, 4]))
        c = oa.comparer_series([{"points": [{"valeur": x} for x in [1, 1.1, 1.2, 1.3, 1.5, 1.8, 2.3]]}], None,
                               [{"carte": "CROISSANCE", "strate": 6}])
        self.assertTrue(c["accord"]["CRO"])

    def test_calibration_par_groupe_75(self):
        import score_registre as sr
        its = [{"B": 0.5, "C": 0.9, "y": 0, "groupes": {"source": "fred"}},
               {"B": 0.5, "C": None, "y": 1, "groupes": {"source": "fred"}},
               {"B": 0.2, "C": 0.3, "y": 1, "groupes": {"source": "acled"}}]
        g = sr.calibration_par_groupe(its, ("source", "absente"))
        self.assertEqual(g["source"]["fred"]["n"], 2)
        self.assertEqual(g["source"]["fred"]["C"]["n"], 1)
        self.assertTrue(g["source"]["fred"]["C"]["petit"])
        self.assertEqual(g["source"]["fred"]["B"]["frequence_observee"], 0.5)
        self.assertEqual(g["absente"], {})
        self.assertIsNone(sr.calibration_par_groupe([], ("source",)))

    def test_trois_corrections_78(self):
        import ombres_auto as oa
        # plus de 4 candidates dans une strate : ancrée et contre-candidate gardées, la dernière du lecteur écartée
        base = {"intensite": "f", "portee": "aucune"}
        d = {"mots": [dict(base, carte="CTR", strate=6)],
             "candidats": ["CTR@6", "HIE@6", "INC@6", "EME@6", "RES@6"], "contre_candidate": ["RES@6"],
             "rejets": {"EME@6": "[aucun_fait] rien"}, "liaisons": [], "questions": [], "recherches": []}
        notes = ap.reparer_dossier(d, {"evenement": {"carte": "SEU", "strate": 6}, "candidats": []}, "2026-10-25")
        self.assertEqual(len([c for c in d["candidats"] if c.endswith("@6")]), 4)
        self.assertIn("CTR@6", d["candidats"])
        self.assertIn("RES@6", d["candidats"])
        self.assertTrue(any("candidate écartée" in n for n in notes))
        # faits perdus comptés par règle
        ex = [{"executee": True, "resultat": "Match de football hier soir à Lyon."}]
        m = oa.mesurer_filtrage(ex, "taux SOFR", [{"carte": "CTR", "strate": 6, "fait": "Match de football hier soir"}])
        self.assertEqual(m["faits_perdus_par_motif"], {"hors_question": 1})

    def test_surnombre_ancrees_84(self):
        # banc du 2026-11-14 : cinq cartes ancrées en strate 7 (événement CRO persiste) → refus sur trois lectures.
        # 0.10.84 : la carte de l'événement est gardée, puis contre-candidate, plan ; la dernière du lecteur sort.
        base = {"intensite": "f", "portee": "aucune", "fait": "x", "source": "s"}
        d = {"mots": [dict(base, carte=c, strate=7) for c in ("CRO", "POL", "CTR", "HIE", "RES")],
             "candidats": ["POL@7", "CTR@7", "HIE@7", "RES@7"], "contre_candidate": ["POL@7"],
             "rejets": {}, "liaisons": ["CTR@7 tension RES@7"], "preuves_liaisons": ["p"], "questions": [],
             "recherches": []}
        plan = {"evenement": {"carte": "CRO", "strate": 7, "type": "persiste"},
                "candidats": ["POL@7", "CTR@7", "HIE@7", "RES@7"]}
        notes = ap.reparer_dossier(d, plan, "2026-10-25")
        cartes = [m["carte"] for m in d["mots"]]
        self.assertEqual(cartes, ["CRO", "POL", "CTR", "HIE"])
        self.assertNotIn("RES@7", d["candidats"])
        self.assertEqual(len([c for c in d["candidats"] if c.endswith("@7")]), 4)
        self.assertEqual(d["liaisons"], [])
        self.assertTrue(any("plus de 4 cartes ancrées" in n for n in notes))
        self.assertIn("Au plus 4 cartes ancrées par strate", open(ap.__file__, encoding="utf-8").read())

    def test_plafond_et_bascules_85(self):
        import comparer_bascules as cb
        self.assertFalse(fb.depasse(0.0, 0.0, 15))
        self.assertFalse(fb.depasse(14.0, 0.9, 15))
        self.assertTrue(fb.depasse(14.5, 0.9, 15))
        self.assertFalse(fb.depasse(1e6, 1e6, 0))                  # 0 = sans plafond
        base = {"lignes": 3, "table": [{"question_id": "q1", "avant": "refuse", "apres": "refuse", "p_avant": None,
                                        "p_apres": None}]}
        branche = {"lignes": 3, "version_rejouee": "x",
                   "table": [{"question_id": "q1", "avant": "refuse", "apres": "estime", "p_avant": None, "p_apres": 0.5},
                             {"question_id": "q2", "avant": "estime", "apres": "estime", "p_avant": 0.3, "p_apres": 0.31}]}
        d = cb.comparer(base, branche)
        self.assertEqual([x["question_id"] for x in d], ["q1", "q2"])
        self.assertEqual(d[1]["base"], ("estime", 0.3))
        self.assertIn("2 verdict(s) changé(s)", cb.markdown(base, branche))
        self.assertIn("rien à comparer", cb.markdown({"indisponible": True}, branche))
        self.assertEqual(cb.comparer(branche, branche), [])

    def test_sources_sans_b_86(self):
        import asyncio
        os.environ.pop("ALPHABET_FB_SANS_B", None)

        async def llm(_):
            raise AssertionError("aucun appel de modèle pour une source sans B par le code")
        for src, q in (("yfinance", "Will GD's market close price on 2026-10-04 be higher than …?"),
                       ("wikipedia", "According to Wikipedia, will a vaccine have been developed for X by …?")):
            x = {"qid": f"fb:2026-09-27:{src}:X:2026-10-04", "source": src, "issue": 0, "url": "", "titre": "t",
                 "resolution": "2026-10-04", "contexte": "", "criteres": "", "_q": {"question": q}}
            self.assertTrue(fb.sans_b_code(x))
            self.assertIsNone(asyncio.run(fb.un_test(x, "2026-09-27", llm, set())))
        self.assertFalse(fb.sans_b_code({"source": "fred", "_q": {}}))
        self.assertFalse(fb.sans_b_code({"source": "yfinance", "_q": {"question": "Will A have a higher rate of return than B?"}}))

    def test_stabilite_et_substituts_86b(self):
        import random
        import apprentissage_liens as al
        import controle_regles_series as crs
        rnd = random.Random(3)
        A = []
        for _ in range(150):
            fort, faible = rnd.random() < 0.4, rnd.random() < 0.3
            p = 0.3 * (4 if fort else 1) / (1 + 0.3 * ((4 if fort else 1) - 1))
            A.append({"B": 0.3, "y": int(rnd.random() < p), "x": [n for n, b in (("fort", fort), ("faible", faible)) if b]})
        s = al.stabilite(A, {"fort": "pousse", "faible": "retient"})
        self.assertGreaterEqual(s["fort"], 0.8)
        self.assertLess(s["faible"], 0.5)
        self.assertEqual(al.stabilite(A, {}), {})
        t = crs.taux_substituts(graine=0, n_series=200)
        self.assertEqual(len(t), len(crs.CAS) * len(crs.LONGUEURS))
        self.assertGreater(t["marche_avec_derive:60"]["CRO"], t["bruit_blanc:60"]["CRO"])
        self.assertEqual(crs.taux_reels([{"ombre_series": {"code": {"CRO": True, "PER": False, "INC": False}}}])["CRO"], 1.0)

    def test_bootstrap_blocs_88(self):
        import random
        import apprentissage_liens as al
        D = [{"q": f"q{i}", "bloc": "b1" if i < 3 else "b2", "y": 0, "B": 0.5, "x": []} for i in range(5)]
        for g in range(20):
            S = al.tirer_blocs(D, random.Random(g))
            blocs = {}
            for d in S:
                blocs.setdefault(d["bloc"], []).append(d["q"])
            for b, qs in blocs.items():                      # un bloc tiré l'est en entier (une ou deux fois)
                self.assertEqual(len(qs) % (3 if b == "b1" else 2), 0)
        self.assertEqual(len(al.tirer_blocs([{"q": "a"}, {"q": "b"}], random.Random(0))), 2)  # sans bloc : par lecture

    def test_decoupage_jeux_entiers_89(self):
        import apprentissage_liens as al
        D = ([{"jeu": "2026-09-13", "q": f"a{i}"} for i in range(50)] + [{"jeu": "2026-09-27", "q": f"b{i}"} for i in range(30)]
             + [{"jeu": "2026-10-11", "q": f"c{i}"} for i in range(20)])
        A, J = al.decouper(D)
        self.assertEqual({d["jeu"] for d in J}, {"2026-10-11", "2026-09-27"})   # 20 < 33 : on ajoute le jeu précédent
        self.assertEqual({d["jeu"] for d in A}, {"2026-09-13"})
        self.assertEqual(len(A) + len(J), len(D))
        A, J = al.decouper([d for d in D if d["jeu"] != "2026-09-13"])
        self.assertEqual({d["jeu"] for d in J}, {"2026-10-11"})                 # le plus ancien reste à l'apprentissage
        self.assertEqual(al.decouper([{"jeu": "x", "q": "1"}]), ([{"jeu": "x", "q": "1"}], []))

    def test_frontiere_vue_exterieure_90(self):
        # skill 0.7.77 : un a priori exactement au plafond (rapport 10, arrondi 10,000000000000002) n'est plus refusé
        M = ap._moteur()
        R = M.P["vue_exterieure_rapport_max"]
        b = 0.443
        p0 = (R * b / (1 - b)) / (1 + R * b / (1 - b)) + 1e-15
        r = M.controle_vue_exterieure({"p": p0, "a_priori": {"p0": p0}, "p_sans_cartes": b},
                                      {"frequence": b, "classe_de_reference": "x", "source": "s"})
        self.assertFalse(r["vue_exterieure"]["a_priori_absurde"])
        self.assertIsNotNone(r["p"])
        p_loin = (11 * b / (1 - b)) / (1 + 11 * b / (1 - b))
        r = M.controle_vue_exterieure({"p": p_loin, "a_priori": {"p0": p_loin}, "p_sans_cartes": b},
                                      {"frequence": b, "classe_de_reference": "x", "source": "s"})
        self.assertTrue(r["vue_exterieure"]["a_priori_absurde"])

    def test_sans_matrice_91(self):
        import asyncio
        from datetime import date
        import score_registre as sr
        q = ap.Question(id="fb:x", url="u", titre="Will WTI rise?", contexte="", criteres="c", precisions="",
                        resolution=date(2026, 10, 18))
        plan = {"strates": [6], "candidats": ["POL@6", "EME@6"], "contre_candidate": ["POL@6"],
                "evenement": {"carte": "CRO", "strate": 6, "type": "apparait"}, "semantique": "presence"}
        c = ap.consigne_plan_sans_matrice(q, "recherche", "2026-10-11", plan)
        self.assertNotIn("MATRICE DES DYNAMIQUES", c)
        self.assertNotIn("d'après la matrice", c)
        self.assertIn("CRO@6 apparait", c)
        self.assertIn("D'APRÈS LES FAITS", c)
        reponses = iter(['{"candidats": ["CTR@6", "INC@6", "SEU@9"], "contre_candidate": ["INC@6"]}',
                         '{"mots": [], "rejets": {"CTR@6": "[aucun_fait] rien", "INC@6": "[aucun_fait] rien"}, '
                         '"candidats": ["CTR@6", "INC@6"], "liaisons": [], "questions": [], "recherches": []}'])

        async def llm(_):
            return next(reponses)
        trace = {"_rejeu": {}, "_textes": ""}
        evt = {"vue_exterieure": None, "temporalite": "generique"}
        o = asyncio.run(ap.sans_matrice_ombre(q, plan, [], "2026-10-11", 7, evt, "CROISSANCE@6 apparait", False, llm,
                                              "r", trace))
        self.assertEqual(trace["_rejeu"]["plan_sans_matrice"]["candidats"], ["CTR@6", "INC@6"])   # SEU@9 hors strate
        self.assertEqual(o["statut"], "etat_nul")
        self.assertEqual(o["part_parents_matrice_candidates"], 0.0)
        # suivi : part des parents de la matrice, officielle contre sans matrice
        ligne = {"statut": "estime", "version_bot": "0.10.99", "ombre_sans_matrice": {"statut": "estime"},
                 "modeles": {"principal": "mistral/mistral-medium-latest"},
                 "rejeu": {"plan": plan, "lectures": [{"mots": [{"carte": "POL", "strate": 6}, {"carte": "EME", "strate": 6}]}],
                           "lecture_sans_matrice": {"mots": [{"carte": "CTR", "strate": 6}, {"carte": "POL", "strate": 6}]}}}
        sv = sr.sans_matrice_suivi([ligne])
        self.assertEqual(sv["part_parents_matrice_officielle"], 1.0)
        self.assertEqual(sv["part_parents_matrice_sans_matrice"], 0.5)
        self.assertTrue(sv["verdict"].startswith("en attente"))
        self.assertFalse(ap.tirage_sans_matrice("x"))                       # taux 0 par défaut
        self.assertEqual(sr.sans_matrice_suivi([dict(ligne, version_bot="0.10.97")])["avant_ecart_de_protocole"], 1)
        # 0.10.99 : l'ombre a droit aux corrections, comme l'officiel
        mot_ev = {"carte": "CRO", "strate": 6, "intensite": "f", "portee": "aucune", "fait": "x", "source": "s"}
        reponses = iter(['{"candidats": ["CTR@6", "INC@6"], "contre_candidate": ["INC@6"]}',
                         json.dumps({"mots": [mot_ev], "rejets": {}, "candidats": ["CTR@6", "INC@6"], "liaisons": [],
                                     "questions": [], "recherches": []}),
                         '{"mots": [], "rejets": {"CTR@6": "[aucun_fait] rien", "INC@6": "[aucun_fait] rien"}, '
                         '"candidats": ["CTR@6", "INC@6"], "liaisons": [], "questions": [], "recherches": []}'])
        appels = []

        async def llm2(c):
            appels.append(c[:60])
            return next(reponses)
        trace = {"_rejeu": {}, "_textes": ""}
        o = asyncio.run(ap.sans_matrice_ombre(q, plan, [], "2026-10-11", 7, evt, "CROISSANCE@6 apparait", False, llm2,
                                              "r", trace))
        self.assertEqual(len(appels), 3)
        self.assertEqual((o["statut"], o["corrections"]), ("etat_nul", 1))

    def test_b_ar_92(self):
        import random
        from datetime import date, timedelta
        d0 = date(2026, 10, 11)
        for derive, sens in ((0.3, 1), (-0.3, -1)):
            rnd, v, pts = random.Random(1), 100.0, []
            for i in range(800):
                v += derive + rnd.gauss(0, 1)
                pts.append({"date": (d0 - timedelta(days=800 - i)).isoformat(), "valeur": v})
            pts.append({"date": d0.isoformat(), "valeur": 1e9})              # le jour même : ignoré (strictement avant)
            o = fb.b_ar(pts, 7, d0)
            self.assertTrue((o["p"] - 0.5) * sens > 0.15, o)
            self.assertLess(abs(o["p"] - fb.b_hausse(pts, 7, d0)[0]), 0.1)
        plat = [{"date": (d0 - timedelta(days=200 - i)).isoformat(), "valeur": 5.0 if i % 10 else 5.25} for i in range(200)]
        o = fb.b_ar(plat, 7, d0)
        self.assertGreater(o["part_sans_changement"], 0.2)
        self.assertLessEqual(o["p"], 0.999)
        self.assertIsNone(fb.b_ar(plat[:10], 7, d0))

    def test_doubles_permutes_96(self):
        import random
        import apprentissage_liens as al
        rnd = random.Random(5)
        A = []
        for _ in range(200):
            fort, bruit = rnd.random() < 0.4, rnd.random() < 0.3
            p = 0.3 * (5 if fort else 1) / (1 + 0.3 * ((5 if fort else 1) - 1))
            A.append({"B": 0.3, "y": int(rnd.random() < p), "x": [n for n, b in (("fort", fort), ("bruit", bruit)) if b]})
        nuls = al.doubles_permutes(A, ["fort", "bruit"], tirages=40)
        beta, et = al.ajuster(A, ["fort", "bruit"])
        z_fort = abs(beta["fort"] / et["fort"])
        self.assertGreater(z_fort, max(nuls["fort"]))              # le vrai lien bat tous ses doubles
        self.assertEqual(len(nuls["bruit"]), 40)

    def test_critere_b_ar_97(self):
        import score_registre as sr
        L = [{"question_id": f"fb:2026-09-13:fred:S{i}:x", "issue": i % 2, "p_B": 0.5,
              "ombre_b_ar": {"p": 0.6 if i % 2 else 0.4}} for i in range(120)]
        c = sr.critere_b_ar(L)
        self.assertEqual(c["n_nouveaux"], 120)
        self.assertTrue(c["verdict"].startswith("critère atteint"))
        vus = [dict(x, question_id=x["question_id"].replace("2026-09-13", "2026-10-25")) for x in L]
        self.assertEqual(sr.critere_b_ar(vus)["n_nouveaux"], 0)
        self.assertTrue(sr.critere_b_ar(L[:50])["verdict"].startswith("en attente"))

    def test_essais_98(self):
        import essais as es
        import score_registre as sr
        k = es.k_intervalle()
        self.assertEqual(k, 12)                    # 0.10.135 : + contexte_meteo
        self.assertAlmostEqual(es.risque_corrige(1), 0.05 / 12)
        self.assertAlmostEqual(es.risque_corrige(2), 0.05 / 24)
        self.assertEqual([es.regard(n, 100) for n in (50, 100, 199, 200, 500)], [0, 1, 1, 2, 2])
        t = sorted(range(1000))
        self.assertEqual(es.bornes(t, 0.05), (50, 949))
        # B_AR : un gain net passe au niveau corrigé ; le verdict ne regarde que les 100 premières questions
        L = [{"question_id": f"fb:2026-09-13:fred:S{i}:x", "issue": i % 2, "p_B": 0.5,
              "ombre_b_ar": {"p": 0.6 if i % 2 else 0.4}} for i in range(150)]
        c = sr.critere_b_ar(L)
        self.assertEqual((c["regard"], c["n_juge"]), (1, 100))
        self.assertTrue(c["verdict"].startswith("critère atteint"))
        self.assertEqual(es.resume()["ouverts"], 13)             # 0.10.135 : + contexte_meteo
        import pathlib
        racine = pathlib.Path(__file__).resolve().parents[1]
        for k, e in es.ESSAIS.items():                            # chaque essai a son pré-enregistrement commité
            self.assertTrue((racine / e["doc"]).is_file(), k)

    def test_fournisseurs_100(self):
        import asyncio
        import alphabet_modeles as am
        import litellm
        self.assertTrue(am.famille_mistral("azure_ai/mistral-medium-2505"))
        self.assertTrue(am.famille_mistral("mistral/mistral-medium-latest"))
        self.assertFalse(am.famille_mistral("bedrock/global.anthropic.claude-haiku-4-5"))
        am.installer_traceur()
        am.installer_traceur()                                    # une seule fois
        self.assertEqual(len(am._TRACEUR), 1)
        am.servis_et_vider()

        async def appel():
            await litellm.acompletion(model="mistral/mistral-medium-latest", mock_response="ok",
                                      messages=[{"role": "user", "content": "x"}])
            await asyncio.sleep(0.5)
        asyncio.run(appel())
        s = am.servis_et_vider()
        self.assertEqual(s, {"mistral/mistral-medium-latest": {"mistral-medium-latest": 1}})
        self.assertEqual(am.servis_et_vider(), {})

    def test_fond_et_duels_79(self):
        import asyncio
        import ombres_auto as oa
        self.assertTrue(oa.est_fond({"fait": "Au 8 octobre 2026, le taux de dépôt est à 2,50 % depuis septembre"},
                                    "2026-10-11", 7))
        self.assertFalse(oa.est_fond({"fait": "Le 5 octobre 2026, la BCE annonce une hausse de 25 points"},
                                     "2026-10-11", 7))
        self.assertTrue(oa.est_fond({"fait": "En janvier 2025, la BCE annonce une hausse"}, "2026-10-11", 7))
        x = {"qid": "fb:2026-10-11:yfinance:A_B:2026-10-18", "source": "yfinance", "issue": 1, "url": "", "titre": "t",
             "resolution": "2026-10-18", "contexte": "", "criteres": "",
             "_q": {"question": "Will A have a higher rate of return than B between …?"}}
        os.environ.pop("ALPHABET_FB_DUELS", None)

        async def llm(_):
            raise AssertionError("aucun appel de modèle pour un duel")
        self.assertIsNone(asyncio.run(fb.un_test(x, "2026-10-11", llm, set())))

    def test_apprentissage_liens_80(self):
        import math
        import random
        import apprentissage_liens as al
        rnd = random.Random(1)
        D = []
        for _ in range(600):
            x = [n for n in ("A→S", "B→S", "C→S") if rnd.random() < 0.4]
            B = rnd.uniform(0.2, 0.8)
            z = math.log(B / (1 - B)) + (1.0 if "A→S" in x else 0) - (1.0 if "B→S" in x else 0)
            D.append({"B": B, "x": x, "y": int(rnd.random() < 1 / (1 + math.exp(-z)))})
        b, e = al.ajuster(D, ["A→S", "B→S", "C→S"])
        self.assertGreater(b["A→S"] - 1.645 * e["A→S"], 0)          # pousse
        self.assertLess(b["B→S"] + 1.645 * e["B→S"], 0)             # retient
        self.assertLess(abs(b["C→S"]), 1.645 * e["C→S"])            # ne dit rien
        x = {"rejeu": {"plan": {"evenement": {"carte": "SEU", "strate": 6, "type": "apparait"}},
                       "lectures": [{"mots": [{"carte": "CTR", "strate": 6}, {"carte": "POL", "strate": 7}]}]}}
        self.assertEqual(al.variables(x), ["CTR→SEU"])                # une carte d'une autre strate n'entre pas
        x["rejeu"]["plan"]["evenement"]["type"] = "persiste"
        self.assertEqual(al.variables(x), ["persiste:SEU"])

    def test_source_url_liste_81(self):
        base = {"intensite": "f", "portee": "aucune"}
        d = {"mots": [dict(base, carte="RCS", strate=6, source_url=["https://a.org/x "]),
                      dict(base, carte="CTR", strate=6, source_url="  https://b.org/y")],
             "candidats": ["RCS@6", "CTR@6"], "rejets": {}, "liaisons": [], "questions": [], "recherches": []}
        ap.reparer_dossier(d, {"evenement": {"carte": "SEU", "strate": 6}, "candidats": []}, "2026-10-25")
        self.assertEqual([m["source_url"] for m in d["mots"]], ["https://a.org/x", "https://b.org/y"])

    def test_poster_b_82(self):
        # règle par défaut (décision du 2026-11-14) : C estimé → B posté, C en ombre
        self.assertFalse(ap.POSTER_C)
        self.assertEqual(ap.choisir_bras({"statut": "estime", "p_C": 0.8, "p_B": 0.3}, 0.5), ("B", 0.3))
        self.assertEqual(ap.choisir_bras({"statut": "estime", "p_C": 0.8, "p_B": None}, 0.5), ("A", 0.5))
        self.assertEqual(ap.choisir_bras({"statut": "etat_nul", "p_B": 0.2}, 0.5), ("B", 0.2))
        q = ap.Question(id="q", url="u", titre="t", contexte="", criteres="", precisions="", resolution=None)
        c = {"statut": "estime", "p_C": 0.8, "p_B": 0.3, "dossier": {"disponible_le": "2026-11-14"}, "etat": "x",
             "evenement": "SEU@7 apparait", "semantique": "au-moins-une-fois", "vue": {}}
        t = ap.commentaire(q, 0.5, "", c, "B")
        self.assertIn("NOT posted", t)
        self.assertIn("0.800", t)

    def test_foret_64(self):
        import foret_strates as fs
        lec = {"mots": [{"carte": "POL", "strate": 13}, {"carte": "CRO", "strate": 6}, {"carte": "INC", "strate": 7}],
               "liaisons": ["CRO@6 transfert POL@13", "INC@7 tension INC@7"]}
        c = fs.compter(lec, {"evenement": {"carte": "SEU", "strate": 13}})
        self.assertEqual((c["hors_strate"], c["relies"]), (2, 1))

    def test_etat_suit_reparation_57(self):
        # 0.10.57 : un mot affaibli par le réparateur (F → f) doit l'être aussi dans l'état
        from unittest import mock

        def affaiblir(d_, p_, a_=None):
            d_["mots"][0]["intensite"] = "f"
            return ["F → f"]
        with mock.patch.object(ap, "reparer_dossier", affaiblir):
            dd = ap.assembler({"mots": [{"carte": "POL", "strate": 7, "intensite": "F", "portee": "aucune"}],
                               "candidats": [], "liaisons": [], "questions": []},
                              {"evenement": {"carte": "SEU", "strate": 7}, "candidats": []}, [],
                              {"evenement": "SEUIL@7 apparait"}, "2026-10-25", 7)
        self.assertIn("POLARITÉ@7[f]", dd["etat"])

    def test_empreintes_56(self):
        # 0.10.56 : empreinte de chaque résultat (texte hors registre) ; chaque passage cité est lié à sa source
        ex = [{"famille": "observation", "cartes": [], "requete": "q", "executee": True,
               "resultat": "Le 3 octobre, le Parlement a adopté la loi de finances après un vote serré."},
              {"famille": "observation", "cartes": [], "requete": "q2", "executee": False, "resultat": ""}]
        r0 = ap.sans_resultat(ex[0])
        self.assertNotIn("resultat", r0)
        self.assertEqual(r0["empreinte"], ap.empreinte(ex[0]["resultat"]))
        self.assertNotIn("empreinte", ap.sans_resultat(ex[1]))
        d = {"mots": [{"carte": "POL", "strate": 7, "passage": {"extrait": "le parlement a ADOPTÉ la loi de finances"}},
                      {"carte": "CTR", "strate": 7, "passage": {"extrait": "phrase absente des résultats"}},
                      {"carte": "SEU", "strate": 7}]}
        e = ap.empreintes_passages(d, ex)
        self.assertEqual(e, [{"mot": "POL@7", "empreinte": r0["empreinte"]}, {"mot": "CTR@7", "empreinte": None}])

    def test_sonde_delai_59(self):
        # 0.10.59 : une sonde qui ne répond jamais est abandonnée au délai, avec une erreur passagère lisible
        import asyncio, os
        import alphabet_modeles as am

        async def muet(modele, consigne):
            await asyncio.sleep(30)
        os.environ["ALPHABET_SONDE_DELAI"] = "0.2"
        try:
            r = asyncio.run(am.sonder("x/y", muet))
        finally:
            del os.environ["ALPHABET_SONDE_DELAI"]
        self.assertFalse(r["disponible"])
        self.assertIn("aucune réponse", r["erreur"])
        self.assertTrue(am.passagere(r))

    def test_reparations_55(self):
        # 0.10.55 : rejet rendu en liste sans clé « carte » ; liaison d'une strate posée entre deux strates
        lec = {"rejets_classes": [{"mot": "INC", "strate": 7, "categorie": "aucun_fait", "motif": "x"},
                                  {"categorie": "aucun_fait", "motif": "sans carte"},
                                  {"motif": "y", "x": "POLARITÉ@7"}]}
        r, _ = ap.rejets_moteur(lec)
        self.assertEqual(sorted(r), ["INC@7", "POL@7"])
        d = {"mots": [{"carte": "TRC", "strate": 6, "intensite": "f", "portee": "aucune"},
                      {"carte": "POL", "strate": 7, "intensite": "f", "portee": "aucune"}],
             "candidats": [], "rejets": {}, "questions": [],
             "liaisons": ["TRC@6 tension POL@7", "TRC@6 transfert POL@7"], "preuves_liaisons": ["a", "b"]}
        ap.reparer_dossier(d, {"evenement": {"carte": "SEU", "strate": 7}, "candidats": []}, "2026-10-25")
        self.assertEqual(d["liaisons"], ["TRC@6 transfert POL@7"])
        self.assertEqual(d["preuves_liaisons"], ["b"])

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
        # 0.10.53 : ombre « avec liaisons » : toutes les liaisons partent au moteur
        with mock.patch.object(ap.subprocess, "run", faux_run):
            ap.appeler_moteur({"liaisons": ["POL@13 averti SEU@13", "POL@13 tension CTR@13"]}, "[x]", "SEUIL@13 apparait",
                              "presence", "2026-10-25", {"frequence": 0.1}, toutes_liaisons=True)
        i = [k for k, x in enumerate(vu["cmd"]) if x == "--liaison"]
        self.assertEqual(len(i), 2)

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


def test_azure_openai_101():
    import alphabet_modeles as am
    env = {"AZURE_AI_API_BASE": "https://x.services.ai.azure.com/openai/v1/responses", "AZURE_AI_API_KEY": "k"}
    m, kw = am.adapter("azure_ai/gpt-5-mini", {"temperature": 0.2, "top_p": 1}, env=env)
    assert m == "openai/gpt-5-mini"
    assert kw["base_url"] == "https://x.services.ai.azure.com/openai/v1"
    assert kw["api_key"] == "k" and kw["drop_params"] is True and "top_p" not in kw
    # Mistral et Bedrock inchangés
    assert am.adapter("mistral/mistral-medium-latest", {"top_p": 1}, env=env) == ("mistral/mistral-medium-latest", {"top_p": 1})
    assert am.adapter("bedrock/x", {}, env={})[0] == "bedrock/x"
    # appel simulé de bout en bout par litellm
    import litellm
    r = litellm.completion(model=m, messages=[{"role": "user", "content": "ok"}], mock_response="oui", **kw)
    assert r.choices[0].message.content == "oui"


def test_azure_base_102():
    import alphabet_modeles as am, pytest
    with pytest.raises(ValueError):
        am.adapter("azure_ai/gpt-5-mini", {}, env={})
    m, kw = am.adapter("azure_ai/gpt-5-mini", {}, env={"AZURE_AI_API_BASE": "https://r.services.ai.azure.com/"})
    assert m == "openai/gpt-5-mini" and kw["base_url"] == "https://r.services.ai.azure.com/openai/v1"


def test_ombre_combinee_103():
    import alphabet_pipeline as ap
    ev = {"carte": "SEU", "type": "apparait", "strate": 7}
    evt = {"vue_exterieure": {"frequence": 0.3}}
    d = {"_categories_rejet": {}}
    s = {"p": 0.6, "sensibilite": {"generatif": {"p": 0.4}}}
    c = ap.ombre_combinee(s, d, ev, evt)
    assert c["p_generatif"] == 0.4 and abs(c["p"] - 0.4) < 1e-6        # rien de contredit : la symétrie ne change rien
    # une candidate contredite qui aurait agi sur SEUIL@7 fait baisser le combiné sous le génératif
    src = [a for a, _ in ap.sources_matrice("SEU")][0]
    d2 = {"_categories_rejet": {f"{src}@7": "contredit"}}
    c2 = ap.ombre_combinee(s, d2, ev, evt)
    assert c2["p"] < 0.4 and c2["p_symetrique_produit"] < 0.6 and c2["lr_contre"] > 1
    assert ap.ombre_combinee(s, d, ev, {"vue_exterieure": {}}) is None


def test_b_saison_104():
    from datetime import date, timedelta
    import math
    import banc_forecastbench as fb
    # série quotidienne saisonnière : chaude en juillet, froide en janvier ; en octobre, elle baisse
    d0 = date(2026, 10, 15)
    pts = [{"date": (d0 - timedelta(days=i)).isoformat(),
            "valeur": 15 + 10 * math.cos(2 * math.pi * ((d0 - timedelta(days=i)).timetuple().tm_yday - 200) / 365.25)}
           for i in range(1, 3650)]
    s = fb.b_saison(pts, 7, d0)
    assert s and s["p"] < 0.2 and s["intervalles"] >= 50
    b = fb.b_hausse(pts, 7, d0)
    assert 0.35 < b[0] < 0.65                    # B annuel : ~50 %, aveugle à la saison
    assert fb.b_saison(pts[:200], 7, d0) is None  # moins d'un an d'historique : rien
    import essais as es
    assert es.ESSAIS["b_saisonnier"]["statut"] == "clos"


def test_banc_a_106(tmp_path, monkeypatch):
    import banc_a as ba
    assert abs(ba.combiner(0.5, 0.5) - 0.5) < 1e-9
    assert 0.5 < ba.combiner(0.8, 0.5) < 0.8           # la moitié du chemin, en logit
    monkeypatch.setattr(ba, "FICHIER", tmp_path / "a.jsonl")
    L = [{"jeu": "2026-08-02", "question_id": f"fb:2026-08-02:fred:S{i}:x", "source_question": "fred", "issue": i % 2,
          "p_A": 0.7 if i % 2 else 0.3, "p_B": 0.5, "p_AB": ba.combiner(0.7 if i % 2 else 0.3, 0.5),
          "modeles_A": "m", "exclue": False, "version_bot": "0.10.107", "ordre": [i, "2026-08-02"]} for i in range(40)]
    r = ba.resumer(L)
    assert r["m"]["n"] == 40 and r["m"]["A"] < r["m"]["AB"] < r["m"]["B"]
    assert "regard" in r["m"]["critere_AB"]
    assert "m" not in ba.resumer([dict(x, version_bot="0.10.106") for x in L])   # premier passage : hors critère
    c = ba.consigne_a({"titre": "T", "criteres": "C", "contexte": "X"}, {"frequence": 0.4, "calcul": "k/n"},
                      [{"date": "2026-08-01", "valeur": 1}], "", "2026-08-02")
    assert "0.400" in c and "2026-08-01 : 1" in c


def test_motifs_ordinaux_108():
    from datetime import date, timedelta
    import banc_o as bo
    assert bo.motif([1, 2, 3]) == (0, 1, 2) and bo.motif([3, 2, 1]) == (2, 1, 0) and bo.motif([5, 5, 1]) == (2, 0, 1)
    d0 = date(2026, 8, 1)
    # série alternée régulière : après « monte, baisse », toujours une hausse à 1 jour
    vals = [(1 if i % 2 else 0) for i in range(400)]
    pts = bo.preparer([{"date": (d0 - timedelta(days=400 - i)).isoformat(), "valeur": v} for i, v in enumerate(vals)], d0)
    ps = bo.paires(pts, 1, d0)
    assert ps and all(len(m) == 3 for m, _ in ps)
    e = bo.entropie_permutation(pts)
    assert e is not None and e < 0.5                   # série très régulière : peu d'entropie
    assert bo.jeffreys(1, 4) is None and abs(bo.jeffreys(5, 5) - 5.5 / 6) < 1e-9
    qs = [{"jeu": "2026-08-01", "question_id": f"q{s}", "source_question": "fred", "serie": f"fred:{s}", "issue": 1,
           "p_B": 0.5, "h": 1, "_pts": pts} for s in range(3)]
    ls = bo.calculer(qs)
    assert all(x["p_O_local"] is not None and x["p_O_trans"] is not None for x in ls)
    assert all(x["n_trans"] == 2 * x["n_local"] for x in ls)      # les deux autres séries, pas elle-même
    import essais as es
    assert es.ESSAIS["motifs_ordinaux"]["statut"] == "clos" and es.ESSAIS["combo_abo"]["statut"] == "clos"


def test_classes_signature_110():
    import classes_signature as cs
    qs = [{"question_id": f"fb:{j}:acled:q{i}:x", "jeu": j, "source_question": "acled", "issue": y, "p_B": 0.5,
           "signature": ["SEU", "apparait", "7"]} for i, (j, y) in enumerate([("2026-09-27", 1)] * 20 + [("2026-10-11", 1)] * 5)]
    ls = cs.calculer(qs)
    assert len(ls) == 5 and all(x["n_cas"] == 20 and abs(x["p_sig"] - (20 + 5) / 30) < 1e-9 for x in ls)


def test_poster_ab_111(poster_ab):
    import alphabet_pipeline as ap
    c7 = {"statut": "estime", "p_B": 0.3, "p_C": 0.6, "plan": {"evenement": {"strate": 7}}}
    b, p = ap.choisir_bras(c7, 0.1)
    assert b == "AB" and 0.1 < p < 0.3
    c13 = {"statut": "hors_strate", "p_B": 0.4, "plan": {"evenement": {"strate": "13"}}}
    assert ap.choisir_bras(c13, 0.6)[0] == "AB"
    c6 = {"statut": "etat_nul", "p_B": 0.4, "plan": {"evenement": {"strate": 6}}}
    assert ap.choisir_bras(c6, 0.6) == ("B", 0.4)
    assert ap.choisir_bras({"statut": "refuse", "plan": {"evenement": {"strate": 7}}}, 0.6)[0] == "A"   # pas de B
    q = ap.Question(id="q", url="u", titre="t", contexte="", criteres="", precisions="", resolution=None)
    txt = ap.commentaire(q, 0.1, "raison", dict(c7, evenement="E", semantique="S", vue={}), "AB")
    assert "AB" in txt and "raison" in txt


def test_banc_langage_112():
    import banc_l as bl
    v = bl.variables([{"type": "acte", "sens": "hausse", "p": 0.8}, {"type": "acte", "sens": "hausse", "p": 0.7},
                      {"type": "description", "sens": "baisse", "p": 0.2}])
    assert v["n_actes"] == 2 and abs(v["E"] - 2 / 3) < 1e-9 and v["D"] > 0.2
    # les actes en hausse annoncent les OUI : β appris positif, et la validation croisée l'applique hors du jeu
    ls = [{"jeu": f"2026-0{7 + i % 3}-01", "question_id": f"q{i}", "issue": i % 2, "p_A": 0.5, "p_B": 0.4,
           "E": 0.6 if i % 2 else -0.6, "D": 0.1, "n_actes": 1} for i in range(60)]
    cv = bl.validation_croisee(ls)
    assert len(cv) == 60 and all(x["beta"] > 0 for x in cv)
    assert sum(x["p_acte"] > 0.5 for x in cv if x["issue"] == 1) == 30


def test_regimes_113():
    from datetime import date, timedelta
    import math
    import banc_b as bb
    d0 = date(2026, 9, 13)
    pts = [{"date": (d0 - timedelta(days=i)).isoformat(),
            "valeur": 15 + 10 * math.cos(2 * math.pi * ((d0 - timedelta(days=i)).timetuple().tm_yday - 200) / 365.25)}
           for i in range(1, 3650)]
    pr = bb.proprietes(pts, d0, {"phi": 0.01})
    assert pr["saison_forte"] and not pr["inertie_forte"]
    assert bb.aiguiller(pr, 0.5, {"p": 0.6}, {"p": 0.1}) == ("B_saison", 0.1)
    assert bb.aiguiller({"inertie_forte": True}, 0.5, {"p": 0.6}, None) == ("B_AR", 0.6)
    assert bb.aiguiller({}, 0.5, None, None) == ("B", 0.5)


def test_signaux_couteux_114():
    import banc_signaux as bs
    v = bs.variables([{"type": "acte", "sens": "hausse", "cout": "gratuit"}, {"type": "acte", "sens": "hausse", "cout": "couteux"},
                      {"type": "acte", "sens": "baisse", "cout": "couteux"}, {"type": "description", "sens": "hausse"}])
    assert abs(v["G"] - 0.5) < 1e-9 and v["K"] == 0 and v["n_couteux"] == 2
    # gratuits en hausse sur les NON, coûteux en hausse sur les OUI : βG < 0 < βK
    ls = [{"jeu": f"2026-0{7 + i % 3}-01", "question_id": f"q{i}", "issue": i % 2, "p_A": 0.5, "p_B": 0.5,
           "G": 0.0 if i % 2 else 0.6, "K": 0.6 if i % 2 else 0.0, "n_gratuit": 1, "n_couteux": 1} for i in range(60)]
    bg, bk = bs.ajuster2([(0.0, x["G"], x["K"], x["issue"]) for x in ls])
    assert bg < 0 < bk
    assert len(bs.validation_croisee(ls)) == 60


def test_type_question_115():
    import type_question as tq
    cas = {"Will there be more 'Riots' in Armenia for the 30 days before 2026-10-04?": "conflit",
           "Will the 15-year fixed rate mortgage average in the US have increased by 2026-07-12 as compared to its value on 2026-07-05?": "macro",
           "Will the sitting U.S. president’s net worth reach ≥4x its value?": "marche",
           "Will any of Belgium or France leave the EU before 2030?": "election",
           "Will SpaceX launch Starship to orbit before March 2027?": "annonce",
           "Will Russia and Ukraine agree to a ceasefire before 2027?": "conflit",
           "Will it snow in Nîmes before 2027?": "meteo", "Will H5N1 cases exceed 1000 in the US?": "sante",
           "Will the number of exoplanets reach 7000?": "indetermine"}
    for t, attendu in cas.items():
        assert tq.classer(t)["type"] == attendu, t
    assert tq.classer("Will there be more 'Protests' in Chad?")["regime"] == ["intention", "contagion"]


def test_aiguillage_ombre_118():
    import alphabet_pipeline as ap
    c = {"p_B": 0.3, "etat": "[2026-09-27 | 7 jours] PÉRIODICITÉ@7[f] + POLARITÉ@7[F]",
         "plan": {"evenement": {"strate": 7}}}
    a = ap.aiguillage_ombre("Will Russia and Ukraine agree to a ceasefire before 2027?", "", c, 0.45)
    assert a["type"] == "conflit" and a["strate"] == 7
    assert a["regimes_par_cartes"] == ["cycle_force", "intention"]
    assert a["p_A_recalibre"] < 0.45 and "p_AB_recalibre" in a          # le calibrage abaisse les probabilités moyennes
    b = ap.aiguillage_ombre("Will the Fed cut rates in December 2026?", "", {"plan": {"evenement": {"strate": 6}}}, 0.4)
    assert b["type"] == "macro" and "p_A_recalibre" not in b


def test_banc_indicateurs_119():
    import random
    import banc_indicateurs as bi
    assert bi.pays_de("Will there be more 'Riots' in Armenia for the 30 days before 2026-10-04?") == "Armenia"
    rnd = random.Random(0)
    ls = []
    for i in range(240):
        w = rnd.gauss(0, 1)
        y = int(rnd.random() < bi.sig(-1.5 + 1.2 * w))
        ls.append({"jeu": f"2026-0{7 + i % 3}-01", "question_id": f"fb:2026-0{7 + i % 3}-01:acled:q{i}:x", "issue": y,
                   "p_A": 0.3, "p_B": 0.3, "wiki": w, "ioda": 0.0, "fcdo": 0.0, "pluie": 0.0, "presents": {"wiki": True}})
    r = bi.resumer(ls)
    assert r["coefficients_tout"]["wiki"] > 0.6 and r["A_recalibre_plus_indicateurs"] < r["A_recalibre"]


def test_gdelt_comptes_120():
    import io, zipfile
    import gdelt_comptes as gc
    def ligne(racine, lieu):
        cols = [""] * 58
        cols[gc.COL_RACINE], cols[gc.COL_LIEU] = racine, lieu
        return "\t".join(cols)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("x.CSV", "\n".join([ligne("14", "Yerevan, Yerevan, Armenia"), ligne("14", "Gyumri, Shirak, Armenia"),
                                       ligne("19", "Khartoum, Sudan"), ligne("01", "Paris, France")]) + "\n")
    c = gc.agreger(buf.getvalue())
    assert c[("Armenia", "manif")] == 2 and c[("Sudan", "violence")] == 1 and ("France", "manif") not in c


def test_banc_indicateurs_principal_121(tmp_path, monkeypatch):
    """0.10.121 : le passage complet s'exécute (le premier a échoué sur un `async with` mêlant un fichier)."""
    import asyncio, json
    import banc_indicateurs as bi
    monkeypatch.setattr(bi, "FICHIER", tmp_path / "i.jsonl")
    monkeypatch.setattr(bi, "RESUME", tmp_path / "i.json")
    monkeypatch.setattr(bi.ba, "lignes", lambda: [{"source_question": "acled", "modeles_A": bi.MODELE, "p_A": 0.3,
        "exclue": False, "issue": 0, "question_id": "fb:2026-08-02:acled:q1:x", "jeu": "2026-08-02", "p_B": 0.3,
        "titre": "Will there be more 'Riots' in Armenia for the 30 days before 2026-08-09?", "ordre": [0, "2026-08-02"]}])
    async def faux_obtenir(c, url, pause=1.0):
        return None
    monkeypatch.setattr(bi, "obtenir", faux_obtenir)
    assert asyncio.run(bi.principal()) == 0
    assert json.loads((tmp_path / "i.jsonl").read_text().splitlines()[0])["pays"] == "Armenia"


def test_juge_silence_123():
    import juge_silence as js
    assert js.recal(0.45) < 0.45 and js.silence(0.45, 0) < js.silence(0.45, 2) == js.recal(0.45)
