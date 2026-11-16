"""0.10.166 : classement des questions Metaculus résolues par des règles fixées."""
import os
import re
import tempfile
import unittest

os.environ["ALPHABET_REGISTRE"] = tempfile.mkdtemp(prefix="registre-")
import recolte_metaculus as rm

MOTIFS = [(re.compile(r"(?<![\w-])france(?![\w-])", re.I), "FR"), (re.compile(r"(?<![\w-])ukraine(?![\w-])", re.I), "UA")]


class TestRecolte(unittest.TestCase):
    def test_ligne(self):
        post = {"id": 1, "title": "Will Russia and Ukraine agree to a ceasefire before July 1, 2026?",
                "projects": {"category": [{"name": "Geopolitics"}]},
                "question": {"id": 2, "type": "binary", "resolution": "no", "open_time": "2026-01-01T00:00:00Z",
                             "scheduled_close_time": "2026-06-30T00:00:00Z",
                             "aggregations": {"recency_weighted": {"latest": {"centers": [0.12]}}}}}
        x = rm.ligne(post, MOTIFS)
        self.assertEqual((x["issue"], x["pays"], x["domaine"], x["forme"]), (0, ["UA"], "conflits", "evenement_avant"))
        self.assertEqual((x["duree_jours"], x["communaute_finale"], x["seuils"]), (180, 0.12, []))
        self.assertTrue(x["classee"])

    def test_non_binaire_ou_annulee(self):
        self.assertIsNone(rm.ligne({"question": {"type": "numeric", "resolution": "3"}}, MOTIFS))
        self.assertIsNone(rm.ligne({"question": {"type": "binary", "resolution": "annulled"}}, MOTIFS))

    def test_seuils_et_formes(self):
        self.assertEqual(rm.seuils("Will US inflation exceed 3.5% in 2026?"), ["3.5%"])
        self.assertEqual(rm.seuils("More than 10,000 deaths before 1 March 2027?"), ["10,000"])
        self.assertEqual(rm.forme("Will US inflation exceed 3.5% in 2026?"), "seuil_depasse")
        self.assertEqual(rm.domaine("Will Macron win the presidential election?"), "elections")


class TestPrincipal(unittest.TestCase):
    def test_detail_et_reprise(self):
        from pathlib import Path
        from unittest import mock
        d = Path(tempfile.mkdtemp())
        liste = [{"id": 1, "question": {"type": "binary", "resolution": None}},
                 {"id": 2, "question": {"type": "binary", "resolution": None}}]
        details = {1: {"id": 1, "title": "Will France hold a referendum before 2027?",
                       "question": {"id": 11, "type": "binary", "resolution": "no"}},
                   2: {"id": 2, "title": "x", "question": {"id": 12, "type": "binary", "resolution": "annulled"}}}
        with mock.patch.object(rm, "SORTIE", d / "r.jsonl"), mock.patch.object(rm, "RESUME", d / "r.md"), \
                mock.patch.object(rm, "DEJA_VUS", d / "vus.txt"), \
                mock.patch.object(rm, "recolter", lambda c, m: iter(liste)), \
                mock.patch.object(rm, "detail", lambda c, pid: details[pid]), \
                mock.patch.object(rm.time, "sleep", lambda s: None), \
                mock.patch("collecte_rss.noms_pays", lambda c: MOTIFS), \
                mock.patch("sys.argv", ["recolte_metaculus.py"]), \
                mock.patch.dict(os.environ, {"METACULUS_RECOLTE_AUTORISEE": "oui"}):
            self.assertEqual(rm.principal(), 0)
            self.assertEqual(len((d / "r.jsonl").read_text().splitlines()), 1)
            self.assertEqual(set((d / "vus.txt").read_text().split()), {"1", "2"})
            rm.principal()                                         # reprise : rien de relu, rien de doublé
            self.assertEqual(len((d / "r.jsonl").read_text().splitlines()), 1)


class TestSuspension(unittest.TestCase):
    def test_sans_autorisation(self):
        from unittest import mock
        with mock.patch("sys.argv", ["recolte_metaculus.py"]), mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("METACULUS_RECOLTE_AUTORISEE", None)
            self.assertEqual(rm.principal(), 1)


if __name__ == "__main__":
    unittest.main()
