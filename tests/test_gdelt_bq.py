import json
import sys
import tempfile
import types
import unittest
from pathlib import Path

import gdelt_bq as gb


class FauxBQ(types.ModuleType):
    def __init__(self):
        super().__init__("google.cloud.bigquery")
        for nom in ("ArrayQueryParameter", "StructQueryParameter", "ScalarQueryParameter"):
            setattr(self, nom, lambda *a, **k: (a, k))

        class Cfg:
            def __init__(self, dry_run=False, **k):
                self.dry_run = dry_run
        self.QueryJobConfig = Cfg


class FauxClient:
    def __init__(self, go, lignes):
        self.go, self.lignes, self.executees = go, lignes, 0

    def query(self, texte, job_config):
        c = self
        if job_config.dry_run:
            return types.SimpleNamespace(total_bytes_processed=c.go * 1e9)
        c.executees += 1
        return types.SimpleNamespace(result=lambda: c.lignes)


class TGdeltBQ(unittest.TestCase):
    def setUp(self):
        d = Path(tempfile.mkdtemp())
        gb.COMPTEUR, gb.TOURNOI = d / "c.json", d / "t.json"
        sys.modules.setdefault("google", types.ModuleType("google"))
        sys.modules.setdefault("google.cloud", types.ModuleType("google.cloud"))
        sys.modules["google.cloud.bigquery"] = FauxBQ()
        self.qs = [{"qid": "q1", "titre": "Will Lula be reelected in Brazil?", "debut": "2026-01-01", "fin": "2026-01-31"}]

    def test_resultats_et_compteur(self):
        c = FauxClient(3.0, [{"qid": "q1", "vu": 20260115120000, "url": "https://a.org/x", "titre": "Lula  leads Brazil poll",
                              "trouves": 2}])
        r = gb.lancer(self.qs, "nuit", client=c)
        self.assertEqual(r["q1"][0], {"vu": "2026-01-15", "url": "https://a.org/x", "titre": "Lula leads Brazil poll"})
        self.assertEqual(c.executees, 1)
        self.assertAlmostEqual(list(json.loads(gb.COMPTEUR.read_text()).values())[0], 3.0)
        self.assertIn("[2026-01-15] Lula leads Brazil poll — https://a.org/x", gb.texte_recherche(r["q1"]))

    def test_plafond_par_requete(self):
        c = FauxClient(30.0, [])
        with self.assertRaises(RuntimeError):
            gb.lancer(self.qs, "nuit", client=c)
        self.assertEqual(c.executees, 0)          # refusée après l'essai à blanc, jamais exécutée

    def test_plafond_mensuel(self):
        from datetime import datetime, timezone
        gb.COMPTEUR.write_text(json.dumps({datetime.now(timezone.utc).strftime("%Y-%m"): 799.0}))
        c = FauxClient(2.0, [])
        with self.assertRaises(RuntimeError):
            gb.lancer(self.qs, "nuit", client=c)
        self.assertEqual(c.executees, 0)

    def test_lecture_par_le_bot(self):
        gb.TOURNOI.write_text(json.dumps({gb.cle("42"): {"articles": [{"vu": "2026-11-17", "url": "https://b.org/y",
                                                                       "titre": "T"}]}}))
        self.assertIn("https://b.org/y", gb.pour_question(42))
        self.assertEqual(gb.pour_question(43), "")

    def test_gdelt_lit_bigquery_pour_la_question_courante(self):
        import asyncio
        import alphabet_recherche as ar_
        gb.TOURNOI.write_text(json.dumps({gb.cle("42"): {"articles": [{"vu": "2026-11-17", "url": "https://b.org/y",
                                                                       "titre": "T"}]}}))

        async def run():
            ar_.QUESTION_COURANTE.set(42)
            return await ar_.gdelt("anything here", None)
        t = asyncio.run(run())
        self.assertIn("https://b.org/y", t)
        self.assertFalse(t.startswith("[moteur"))


if __name__ == "__main__":
    unittest.main()
