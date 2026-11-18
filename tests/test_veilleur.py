import os
import unittest

import veilleur as v


class FauxGH:
    def __init__(self, en_cours=None):
        self._en_cours, self.lances = en_cours or [], []

    def en_cours(self):
        return self._en_cours

    def lancer(self, fichier, entrees=None):
        self.lances.append((fichier, entrees))


class TVeilleur(unittest.TestCase):
    def setUp(self):
        os.environ["GITHUB_TOKEN"], os.environ["METACULUS_TOKEN"] = "x", "y"
        self.ancien = (v.Github, v.nouvelles, v.time.sleep, v.DUREE_PASSAGE)

    def tearDown(self):
        v.Github, v.nouvelles, v.time.sleep, v.DUREE_PASSAGE = self.ancien

    def lancer_un_tour(self, gh, n):
        v.Github = lambda jeton: gh
        v.nouvelles = lambda: n
        tours = {"k": 0}

        def dormir(s):
            tours["k"] += 1
            v.DUREE_PASSAGE = -1          # le tour suivant s'arrête et relance le veilleur
        v.time.sleep = dormir
        return v.principal(False)

    def test_lance_le_bot_sur_question_nouvelle(self):
        gh = FauxGH()
        self.lancer_un_tour(gh, {"minibench": 2, "tournament": 0})
        self.assertIn(("run_alphabet_bot.yaml", {"mode": "minibench", "max_questions": "0"}), gh.lances)
        self.assertIn(("veilleur.yaml", None), gh.lances)          # relance de lui-même

    def test_tournoi_principal(self):
        gh = FauxGH()
        self.lancer_un_tour(gh, {"minibench": 0, "tournament": 5})
        self.assertIn(("run_alphabet_bot.yaml", {"mode": "tournament", "max_questions": "0"}), gh.lances)

    def test_pas_de_doublon_si_le_bot_tourne(self):
        gh = FauxGH([{"path": ".github/workflows/run_alphabet_bot.yaml", "id": 1}])
        self.lancer_un_tour(gh, {"minibench": 2, "tournament": 0})
        self.assertNotIn("run_alphabet_bot.yaml", [f for f, _ in gh.lances])

    def test_un_seul_veilleur(self):
        gh = FauxGH([{"path": ".github/workflows/veilleur.yaml", "id": 999}])
        os.environ["GITHUB_RUN_ID"] = "1"
        try:
            self.assertEqual(self.lancer_un_tour(gh, {"minibench": 2}), 0)
        finally:
            del os.environ["GITHUB_RUN_ID"]
        self.assertEqual(gh.lances, [])
