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


if __name__ == "__main__":
    unittest.main()
