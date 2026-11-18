import os
import tempfile

os.environ["ALPHABET_REGISTRE"] = tempfile.mkdtemp(prefix="registre-test-")  # registre fictif avant tout import
os.environ["ALPHABET_TESTS"] = "1"

import asyncio
import tempfile
import unittest
from pathlib import Path

import banc_abstention as ba
import banc_jugement_alphabet as bja


class TBancAbstention(unittest.TestCase):
    def test_passage_simule(self):
        d = Path(tempfile.mkdtemp())
        ba.FICHIER, ba.RESUME, ba.tr.CACHE = d / "a.jsonl", d / "a.json", d / "cache"
        vides = {i for i in range(0, 400, 3)}
        compteur = {"n": 0}

        async def recherche(t, i):
            compteur["n"] += 1
            if compteur["n"] % 3 == 0:
                raise RuntimeError("aucun moteur de recherche n'a répondu (exa : aucun résultat)")
            return "[moteur : exa]\n[2026-01-01] Titre — https://apnews.com/a\n" + "texte utile " * 40

        async def appeler(m, c):
            if "Tu NE DONNES PAS" in c:
                return {"notes": {k: {"note": 2, "pourquoi": "x"} for k in bja.CLES}}
            return {"p": 0.3}

        async def faux_json(url):
            return {"questions": []}
        anc = (ba.ar.chercher_avant, ba.bv.appeler, ba.fb._json)
        ba.ar.chercher_avant, ba.bv.appeler, ba.fb._json = recherche, appeler, faux_json
        try:
            self.assertEqual(asyncio.run(ba.principal(1.0)), 0)
        finally:
            ba.ar.chercher_avant, ba.bv.appeler, ba.fb._json = anc
        ls = ba.lignes()
        self.assertTrue(ls)
        self.assertTrue(all(x["recherche"]["moteur"] == "aucun résultat" for x in ls))
        self.assertTrue(all(x["p_M_aveugle"] == 0.3 for x in ls))
        r = ba.resumer(ls)
        self.assertIn("verdict", r)


if __name__ == "__main__":
    unittest.main()
