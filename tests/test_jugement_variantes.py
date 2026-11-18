import asyncio
import json
import tempfile
import unittest
from pathlib import Path

import banc_jugement_alphabet as bja
import banc_jugement_variantes as bv

Q = {"titre": "Will X happen?", "cloture": "2026-12-31", "criteres": "c", "contexte": "k"}
NOTES = {k: {"note": 3, "pourquoi": "p"} for k in bja.CLES}


class TConsignes(unittest.TestCase):
    def test_avocat_et_finale(self):
        c = bv.consigne_avocat(Q, 0.2, NOTES, "rech", "2026-06-01")
        self.assertIn("AVOCAT DU OUI", c)
        self.assertNotIn("probabilité que la réponse", c)
        f = bv.consigne_finale_avocat(Q, 0.2, NOTES, {"chemin": "un vote", "signes": "aucun", "solidite": 2}, "r", "2026-06-01")
        self.assertLess(f.index("un vote"), f.index("Rends UNIQUEMENT"))

    def test_neutre(self):
        a = bv.consigne_neutre(Q, 0.2, NOTES, "r", "2026-06-01", True)
        b = bv.consigne_neutre(Q, 0.2, NOTES, "r", "2026-06-01", False)
        self.assertLess(a.index("ISSUE R"), a.index("ISSUE N"))
        self.assertLess(b.index("ISSUE N"), b.index("ISSUE R"))
        self.assertNotIn("OUI", a.split("TAUX DE BASE")[0].split("Deux issues")[1])
        self.assertAlmostEqual(bv.lire_neutre({"R": 0.3, "N": 0.9}), 0.25)
        n = sum(bv.ordre_neutre(f"q{i}") for i in range(1000))
        self.assertTrue(400 < n < 600)


class TPassage(unittest.TestCase):
    def test_passage_simule(self):
        d = Path(tempfile.mkdtemp())
        bv.FICHIER, bv.RESUME = d / "v.jsonl", d / "v.json"
        bv.tr.CACHE = d / "cache"

        async def faux_appeler(modele, consigne):
            if "AVOCAT DU OUI dans" in consigne:
                return {"chemin": "c", "signes": "s", "solidite": 3}
            if "Deux issues" in consigne:
                return {"R": 0.3, "N": 0.7}
            if "Tu NE DONNES PAS" in consigne:
                return {"notes": {k: {"note": 2, "pourquoi": "x"} for k in bja.CLES}}
            return {"p": 0.2, "connait_issue": False}

        async def faux_json(url):
            jeu = url.rsplit("/", 1)[1][:10]
            return {"questions": [{"id": x["id"], "background": "b"} for x in bja.candidates() if x["jeu"] == jeu]}

        async def fausse_recherche(t, i):
            return "rien"
        ancien = (bv.appeler, bv.fb._json, bv.ar.chercher_avant, bv.ar.recherche_bornee_disponible)
        bv.appeler, bv.fb._json, bv.ar.chercher_avant = faux_appeler, faux_json, fausse_recherche
        bv.ar.recherche_bornee_disponible = lambda: True
        try:
            self.assertEqual(asyncio.run(bv.principal(3, 1.0, 1.0)), 0)
        finally:
            bv.appeler, bv.fb._json, bv.ar.chercher_avant, bv.ar.recherche_bornee_disponible = ancien
        ls = bv.lignes()
        self.assertEqual(len(ls), 3)
        x = ls[0]
        self.assertEqual((x["p_M_refait"], x["p_M_avocat"], x["p_M_neutre"]), (0.2, 0.2, 0.3))
        self.assertEqual((x["haiku"]["p_A"], x["haiku"]["p_M"], x["haiku"]["p_M_avocat"]), (0.2, 0.2, 0.2))
        r = json.loads(bv.RESUME.read_text())
        self.assertEqual(r["gpt_avocat_oui"]["n"], 3)
        self.assertIn("en attente", r["replique_haiku_M_contre_A"]["critere"]["verdict"]) if "replique_haiku_M_contre_A" in r else None


if __name__ == "__main__":
    unittest.main()
