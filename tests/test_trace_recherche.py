import asyncio
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

import trace_recherche as tr

TEXTE = """[moteur : exa]
[2026-02-10] Avant — https://a.org/x
extrait
[2026-04-01] Après — https://b.org/y
extrait
[s.d.] Sans date — https://c.org/z
[2026-02-01] Adresse — https://d.org/2026/05/12/article
"""


class TTrace(unittest.TestCase):
    def test_tracer(self):
        t = tr.tracer(TEXTE, "2026-03-01")
        self.assertEqual((t["moteur"], t["n_sources"]), ("exa", 4))
        self.assertEqual([s["motif"] for s in t["suspectes"]],
                         ["datée après la question", "sans date", "adresse datée après la question"])
        self.assertNotIn("extrait", str(t))
        self.assertEqual(tr.tracer("", "2026-03-01")["moteur"], "aucun")

    def test_gel(self):
        tr.CACHE = Path(tempfile.mkdtemp()) / "c"
        appels = []

        async def chercher(q, avant):
            appels.append(q)
            return "[moteur : exa]\ntexte"
        t1, c1 = asyncio.run(tr.chercher_fige("q1", "titre", datetime(2026, 3, 1, tzinfo=timezone.utc), chercher))
        t2, c2 = asyncio.run(tr.chercher_fige("q1", "titre", datetime(2026, 3, 1, tzinfo=timezone.utc), chercher))
        self.assertEqual((t1 == t2, c1, c2, len(appels)), (True, False, True, 1))

    def test_panne_non_gelee(self):
        tr.CACHE = Path(tempfile.mkdtemp()) / "c"

        async def panne(q, avant):
            raise RuntimeError("x")
        t, c = asyncio.run(tr.chercher_fige("q2", "t", datetime(2026, 3, 1, tzinfo=timezone.utc), panne))
        self.assertTrue(t.startswith("(recherche indisponible"))
        self.assertIsNone(tr.lire_cache("q2"))

    def test_resume(self):
        x = {"trace": tr.tracer(TEXTE, "2026-03-01")}
        r = tr.resumer_traces([dict(x, haiku_dit_connaitre=True), dict(x, haiku_dit_connaitre=False)])
        self.assertEqual(r["haiku_dit_connaitre"]["questions_avec_source_suspecte"], 1)


if __name__ == "__main__":
    unittest.main()


class TFiltre(unittest.TestCase):
    def test_marches_et_pages_vivantes(self):
        import alphabet_recherche as ar_
        t = ("[moteur : exa]\n[2026-01-02] Marché — https://polymarket.com/event/x\nextrait\n\n"
             "[2026-01-02] Wiki — https://en.wikipedia.org/wiki/X\nextrait\n\n[2026-01-02] Presse — https://apnews.com/a\nextrait")
        r = ar_.filtrer(t, retro=True)
        self.assertNotIn("polymarket", r)
        self.assertNotIn("wikipedia", r)
        self.assertIn("apnews", r)
        self.assertIn("wikipedia", ar_.filtrer(t, retro=False))
        self.assertNotIn("polymarket", ar_.filtrer(t, retro=False))

    def test_aucun_resultat_gele_panne_non(self):
        tr.CACHE = Path(tempfile.mkdtemp()) / "c"

        async def vide(q, avant):
            raise RuntimeError("aucun moteur de recherche n'a répondu (exa : aucun résultat ; gdelt : aucun résultat)")

        async def panne(q, avant):
            raise RuntimeError("aucun moteur de recherche n'a répondu (exa : HTTPStatusError ; gdelt : aucun résultat)")
        d = datetime(2026, 3, 1, tzinfo=timezone.utc)
        t, _ = asyncio.run(tr.chercher_fige("v", "t", d, vide))
        self.assertEqual((t, tr.lire_cache("v")), (tr.AUCUN, tr.AUCUN))
        self.assertEqual(tr.tracer(t, "2026-03-01")["moteur"], "aucun résultat")
        t, _ = asyncio.run(tr.chercher_fige("p", "t", d, panne))
        self.assertIsNone(tr.lire_cache("p"))
        self.assertEqual(tr.tracer(t, "2026-03-01")["moteur"], "panne")


class TSansFoule(unittest.TestCase):
    def test_phrases_retirees(self):
        import alphabet_recherche as ar_
        t = ("Le Sénat vote mardi. Polymarket donne 72 % au oui. Le texte a été amendé.\n"
             "- Kalshi traders are pricing a 60% chance\n"
             "- Reuters: the committee approved the bill on March 3.\n"
             "Source : https://manifold.markets/x/y\n"
             "The manifold of options remains open.")
        r, n = ar_.sans_foule(t)
        self.assertEqual(n, 3)
        for mot in ("Polymarket", "Kalshi", "manifold.markets"):
            self.assertNotIn(mot, r)
        for garde in ("Le Sénat vote mardi.", "Le texte a été amendé.", "committee approved", "manifold of options"):
            self.assertIn(garde, r)
