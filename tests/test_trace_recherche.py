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
