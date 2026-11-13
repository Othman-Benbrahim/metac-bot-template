"""Bot 0.10.14 : monde synthétique (skill §43) et part des sorties illisibles au score."""
from __future__ import annotations

import asyncio
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import alphabet_pipeline as ap  # noqa: E402
import monde_synthetique as ms  # noqa: E402
import score_registre as sr  # noqa: E402


class Tests(unittest.TestCase):
    def test_monde(self):
        m = ap._moteur()
        cartes = [c for c in sorted(m.NOMS) if not m.hors_domaine(f"{c}@7")]
        sits = [ms.situation(7, g, cartes) for g in range(4)]
        appels = {"n": 0}

        async def narrateur(c):
            self.assertIn("FICTIVES", c)
            return "[2026-11-01] Titre — https://a.example/x\nUn fait."

        async def lecteur(c):
            s = sits[appels["n"]]
            appels["n"] += 1
            self.assertIn("RÈGLES DU DOSSIER", c)
            if appels["n"] == 4:
                return "pas de json"
            # lit toutes les présentes (la première en F) et une absente en f
            mots = [{"carte": k.split("@")[0], "strate": 7, "intensite": "F" if i == 0 else "f"}
                    for i, k in enumerate(s["presentes"])]
            mots.append({"carte": s["absentes"][0].split("@")[0], "strate": 7, "intensite": "f"})
            return json.dumps({"mots": mots, "rejets_classes": {}})
        r = asyncio.run(ms.lancer(narrateur, lecteur, 4, 7, 0, "2026-11-11"))
        x = r["resultat"]
        self.assertEqual((x["lues"], x["illisibles"]["lecteur"]), (3, 1))
        pres = sum(len(s["presentes"]) for s in sits[:3])
        avec = sum(1 for s in sits[:3] if s["presentes"])
        self.assertEqual(x["cartes_presentes"], pres)
        self.assertAlmostEqual(x["mesure"]["sens"], 1.0 if pres else None)
        self.assertAlmostEqual(x["mesure"]["sens_F"], round(avec / pres, 4))
        self.assertAlmostEqual(x["mesure"]["fp_f"], round(3 / x["cartes_absentes"], 4))
        self.assertEqual(x["stipule"]["sens_F"], m.P["generatif"]["sens_F"])
        self.assertEqual(ms.fuites("Le SEUIL est franchi"), ["SEUIL"])
        self.assertIsNone(x["mesure_verifiee"])
        self.assertIn("passager clandestin", " ".join(ms.marqueurs("COM")))

    def test_canevas_corrobore(self):
        # 0.10.31 : médias imposés, moitié des faits corroborés par deux médias ; plus de réécriture
        m = ap._moteur()
        cartes = [c for c in sorted(m.NOMS) if not m.hors_domaine(f"{c}@7")]
        s = ms.situation(7, 0, cartes)
        cv = ms.canevas(s["presentes"], 7, 0, "2026-11-11")
        self.assertEqual(len(cv["depeches"]), 1 + len(s["presentes"]) + len(cv["corrobores"]))
        self.assertEqual(cv, ms.canevas(s["presentes"], 7, 0, "2026-11-11"))     # reproductible
        for c in cv["corrobores"]:
            ds = [d for d in cv["depeches"] if d["carte"] == c]
            self.assertEqual(len({d["media"] for d in ds}), 2)                     # deux médias distincts
        appels = {"n": 0}

        async def narrateur(c):
            appels["n"] += 1
            self.assertIn("(média :", c)
            return "[2026-11-01] T — https://a.example/x\nV1"

        async def verificateur(c):
            return json.dumps({k.split("@")[0]: "oui" for k in s["presentes"]})

        async def lecteur(c):
            corro = cv["corrobores"]
            return json.dumps({"mots": [{"carte": k.split("@")[0], "strate": 7, "intensite": "F" if k in corro else "f"}
                                        for k in s["presentes"]]})
        r = asyncio.run(ms.lancer(narrateur, lecteur, 1, 7, 0, "2026-11-11", verificateur=verificateur))
        self.assertEqual(appels["n"], 1)                                           # un seul appel au narrateur
        mv = r["resultat"]["mesure_verifiee"]
        if cv["corrobores"]:
            self.assertEqual(mv["corrobores"]["sens_F"], 1.0)
        self.assertEqual(mv["source_unique"]["sens_F"], 0 if mv["source_unique"]["cartes"] else None)

    def test_effacement_parasites_negation(self):
        # 0.10.34 : noms effacés dans la consigne (identifiants neutres), lecture ramenée aux vraies cartes ;
        # dépêches parasites dans le canevas ; cohérence de la négation
        m = ap._moteur()
        t = ms.table_effacement(5)
        self.assertEqual(sorted(t), sorted(m.NOMS))
        e = ms.effacer_noms("Lis SEUIL@7 et TRACE · MÉMOIRE (TRC) ; un seuil reste un mot.", t)
        self.assertNotIn("SEUIL", e)
        self.assertNotIn("TRC", e)
        self.assertIn("un seuil reste un mot", e)                                   # les définitions restent
        inv = {i: a for a, i in t.items()}
        self.assertEqual(ms.ancrees({"mots": [{"carte": t["SEU"], "strate": 7, "intensite": "f"}]}, 7, inv), {"SEU@7": "f"})
        cvs = [ms.canevas(["SEU@7"], 7, g, "2026-11-11") for g in range(20)]
        self.assertTrue(any(c["parasites"] == 2 for c in cvs) and any(c["parasites"] == 0 for c in cvs))
        self.assertEqual(ap.coherence_negation(0.7, 0.4)["incoherence"], 0.1)

    def test_reprise_json(self):
        # 0.10.25 : une sortie illisible a une seconde chance, et le premier échec reste compté
        rep = iter(["pas de json", '{"ok": true}'])

        async def llm(c):
            return next(rep)
        t = {}
        self.assertEqual(asyncio.run(ap.json_avec_reprise(llm, "x", t, "lecture")), {"ok": True})
        self.assertEqual(t["reprises_json"], {"lecture": 1})
        L = {"modeles": {"principal": "m"}, "bras": {"C": {"statut": "estime", "reprises_json": {"lecture": 1}}}}
        self.assertEqual(sr.sorties_illisibles([L])["par_modele"]["m"]["etapes"], {"lecture": 1})

    def test_verification(self):
        # 0.10.23 : une absente que le narrateur a montrée (selon le vérificateur) sort de la mesure des faux positifs
        m = ap._moteur()
        cartes = [c for c in sorted(m.NOMS) if not m.hors_domaine(f"{c}@7")]
        s = ms.situation(7, 0, cartes)
        a0 = s["absentes"][0]

        async def narrateur(c):
            self.assertNotIn("Structure mathématique", c)        # plus de fiches complètes : marqueurs seulement
            return "[2026-11-01] T — https://a.example/x\nUn fait."

        async def lecteur(c):
            mots = [{"carte": k.split("@")[0], "strate": 7, "intensite": "f"} for k in s["presentes"] + [a0]]
            return json.dumps({"mots": mots})

        async def verificateur(c):
            return json.dumps({k.split("@")[0]: "oui" for k in s["presentes"] + [a0]})
        r = asyncio.run(ms.lancer(narrateur, lecteur, 1, 7, 0, "2026-11-11", verificateur=verificateur))
        x = r["resultat"]
        self.assertGreater(x["mesure"]["fp"], 0)
        self.assertEqual(x["mesure_verifiee"]["fp"], 0)
        self.assertEqual(x["mesure_verifiee"]["erreurs_narrateur"]["absentes_montrees"], 1)
        self.assertEqual(ms.fuites("au seuil de la crise"), [])

    def test_sorties_illisibles(self):
        L = lambda mod, c: {"modeles": {"principal": mod}, "bras": {"C": c}}
        r = sr.sorties_illisibles([
            L("a", {"motif": "lecture illisible : JSONDecodeError"}),
            L("a", {"statut": "estime", "critique": {"statut": "illisible"}}),
            L("a", {"statut": "estime"}),
            L("b", {"motif": "plan corrigé illisible : x"}),
        ])
        self.assertEqual((r["lignes"], r["illisibles"]), (4, 3))
        self.assertEqual(r["par_modele"]["a"]["etapes"], {"lecture": 1, "critique": 1})
        self.assertEqual(r["par_modele"]["b"]["etapes"], {"plan_corrige": 1})
        self.assertAlmostEqual(r["par_modele"]["a"]["part"], 0.6667)
        self.assertIsNone(sr.sorties_illisibles([]))


if __name__ == "__main__":
    unittest.main()


class TripletsRelatifs72(unittest.TestCase):
    def test_montrees_et_validite(self):
        import monde_synthetique as ms
        s = {"presentes": ["CTR@7", "SEU@7"], "absentes": ["POL@7", "RES@7"]}
        v = {"absentes_montrees": ["POL@7"], "presentes_non_montrees": ["SEU@7"]}
        self.assertEqual(ms.montrees(v, s), {"CTR", "POL"})
        self.assertIsNone(ms.montrees({"erreur": "x"}, s))
        cles = {"CTR", "SEU", "POL", "RES"}
        # l'ancre montre une carte en trop (POL) : l'accord qui la montre aussi reste valide (règle relative)
        ok = ms.validite_relative({"CTR", "SEU", "POL"}, {"CTR", "SEU", "POL"}, {"CTR", "POL"}, "SEU@7", cles)
        self.assertTrue(ok["accord_valide"] and ok["leurre_valide"])
        # leurre qui réalise quand même la carte : invalide
        ko = ms.validite_relative({"CTR", "SEU"}, {"CTR", "SEU"}, {"CTR", "SEU"}, "SEU@7", cles)
        self.assertFalse(ko["leurre_valide"])
        # une carte d'écart : invalide strictement, valide « à une carte près »
        un = ms.validite_relative({"CTR", "SEU"}, {"CTR", "SEU", "RES"}, {"CTR"}, "SEU@7", cles)
        self.assertFalse(un["accord_valide"])
        self.assertTrue(un["accord_souple"])

    def test_mesurer_triplets_relatif(self):
        import monde_synthetique as ms
        r = {"statut": "lue", "ancrees": {"CTR@7": "f", "SEU@7": "f"},
             "triplet": {"ancrees_accord": {"CTR@13": "f", "SEU@13": "f"}, "ancrees_leurre": {"CTR@7": "f"},
                         "carte_leurre": "SEU@7", "accord_valide": True, "leurre_valide": True,
                         "accord_rate_par_narrateur": True, "reecritures": {"accord": True}}}
        t = ms.mesurer_triplets([r])
        self.assertEqual(t["n"], 1)                 # le critère relatif l'emporte sur l'ancien drapeau absolu
        self.assertEqual(t["taux"], 1.0)
        self.assertEqual(t["leurre_discrimine"], 1)
        self.assertEqual(t["reecritures"]["accord_sauve"], 1)
