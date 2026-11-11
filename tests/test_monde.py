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
