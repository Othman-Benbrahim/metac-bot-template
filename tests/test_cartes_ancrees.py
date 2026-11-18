import os
import tempfile

os.environ["ALPHABET_REGISTRE"] = tempfile.mkdtemp(prefix="registre-test-")
os.environ["ALPHABET_TESTS"] = "1"

import asyncio  # noqa: E402
import unittest  # noqa: E402
from pathlib import Path  # noqa: E402

import banc_cartes_ancrees as bca  # noqa: E402
import cartes_ancrees as ca  # noqa: E402

RECH = ("[moteur : exa]\n[2026-02-01] Vote — https://a.org/x\nThe Senate is scheduled to vote on the bill on March 10, 2026, "
        "according to the majority leader.\n\n[2026-02-02] Chiffres — https://b.org/y\n"
        "Unemployment stood at 4.6% in January, the statistics office said.")


class TVerification(unittest.TestCase):
    def test_citation(self):
        self.assertTrue(ca.citation_verifiee("the senate is scheduled to vote on the bill on March 10, 2026", RECH))
        self.assertTrue(ca.citation_verifiee("The  Senate is scheduled to vote on the bill", RECH))   # espaces
        self.assertFalse(ca.citation_verifiee("The Senate will vote on Friday on the bill", RECH))  # inventée
        self.assertFalse(ca.citation_verifiee("Senate", RECH))                                       # trop courte

    def test_declencheur(self):
        bon = {"evenement": "vote", "date": "2026-03-10", "citation": "scheduled to vote on the bill on March 10, 2026"}
        self.assertEqual(ca.note_declencheur(bon, RECH, "2026-03-01", "2026-06-30"), (4, "daté dans la fenêtre"))
        self.assertEqual(ca.note_declencheur(dict(bon, date="2026-06-01"), RECH, "2026-03-01", "2026-06-30")[0], 3)
        self.assertEqual(ca.note_declencheur(dict(bon, date="2026-08-01"), RECH, "2026-03-01", "2026-06-30")[0], 1)
        self.assertEqual(ca.note_declencheur(dict(bon, citation="The vote is on Friday next week for sure"),
                                             RECH, "2026-03-01", "2026-06-30"), (1, "rejeté (citation introuvable)"))
        self.assertEqual(ca.note_declencheur(None, RECH, "2026-03-01", "2026-06-30")[0], 1)

    def test_distance(self):
        f = {"valeur": 4.6, "seuil": 5.0, "sens": "au_dessus", "citation": "Unemployment stood at 4.6% in January"}
        self.assertEqual(ca.note_distance(f, RECH)[0], 2)                         # 8 % de chemin
        self.assertEqual(ca.note_distance(dict(f, seuil=4.5), RECH)[0], 4)        # déjà atteint
        self.assertEqual(ca.note_distance(dict(f, valeur=4.9), RECH),             # valeur absente de la citation
                         (1, "rejeté (valeur absente de la citation)"))
        self.assertEqual(ca.note_distance(None, RECH), (None, "sans objet"))

    def test_ancrer_compte_les_rejets(self):
        r = ca.ancrer({"declencheur": {"date": "2026-03-10", "citation": "a phrase that is nowhere in the text"},
                       "distance": None}, RECH, "2026-03-01", "2026-06-30")
        self.assertEqual((r["faits_proposes"], r["faits_rejetes"], r["declencheur"]), (1, 1, 1))


class TBanc(unittest.TestCase):
    def test_passage_simule(self):
        d = Path(tempfile.mkdtemp())
        bca.FICHIER, bca.RESUME, bca.tr.CACHE = d / "a.jsonl", d / "a.json", d / "cache"

        async def recherche(t, i):
            return RECH

        async def appeler(m, c):
            if "haiku" in m:
                return {"declencheur": {"date": "2026-12-31", "citation": "scheduled to vote on the bill on March 10, 2026"}}
            return {"declencheur": {"date": "2026-03-10", "citation": "invented sentence that is not there at all"}}

        async def faux_json(url):
            return {"questions": []}
        anc = (bca.ar.chercher_avant, bca.bv.appeler, bca.fb._json)
        bca.ar.chercher_avant, bca.bv.appeler, bca.fb._json = recherche, appeler, faux_json
        try:
            self.assertEqual(asyncio.run(bca.principal(5.0, 5.0)), 0)
        finally:
            bca.ar.chercher_avant, bca.bv.appeler, bca.fb._json = anc
        ls = bca.lignes()
        self.assertTrue(ls)
        self.assertEqual(len({":".join(x["question_id"].split(":")[:2]) for x in ls}), len(ls))   # questions distinctes
        r = bca.resumer(ls)
        self.assertEqual(r["hallucinations_gpt"]["part"], 1.0)
        self.assertIn("verdict_principal", r)


if __name__ == "__main__":
    unittest.main()
