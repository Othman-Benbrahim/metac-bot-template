"""Tests de configuration du bot (forecasting-tools requis ; aucun appel réseau)."""
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
try:
    import alphabet_bot as ab
except ImportError as e:  # sans forecasting-tools : tests sautés
    ab = None
    RAISON = str(e)

BASE = {"METACULUS_TOKEN": "x", "ANTHROPIC_API_KEY": "x"}


def bot(env):
    with mock.patch.dict(os.environ, env, clear=True):
        b = ab.construire(publier=False)
        return b, ab.problemes(b, env)


@unittest.skipIf(ab is None, "forecasting-tools absent")
class TestsConfiguration(unittest.TestCase):
    def test_anthropic_seul_bloque(self):
        # Sans ALPHABET_CHERCHEUR, la recherche part vers le proxy Metaculus, qui n'existe plus.
        _, (bloquants, _) = bot(BASE)
        self.assertTrue(any("proxy" in x for x in bloquants))

    def test_anthropic_et_exa(self):
        env = dict(BASE, EXA_API_KEY="x", ALPHABET_LLM="anthropic/claude-sonnet-5-5",
                   ALPHABET_PETIT_LLM="anthropic/claude-haiku-5-5",
                   ALPHABET_CHERCHEUR="smart-searcher/anthropic/claude-haiku-5-5")
        b, (bloquants, avertissements) = bot(env)
        self.assertEqual(bloquants, [])
        self.assertEqual(avertissements, [])
        self.assertEqual(ab.GeneralLlm.to_model_name(b.get_llm("parser")), "anthropic/claude-haiku-5-5")
        self.assertEqual(ab.GeneralLlm.to_model_name(b.get_llm("default")), "anthropic/claude-sonnet-5-5")

    def test_exa_sans_cle(self):
        env = dict(BASE, ALPHABET_LLM="anthropic/claude-sonnet-5-5",
                   ALPHABET_CHERCHEUR="smart-searcher/anthropic/claude-sonnet-5-5")
        _, (bloquants, _) = bot(env)
        self.assertTrue(any("EXA_API_KEY" in x for x in bloquants))

    def test_bilan(self):
        ligne = {"bras_poste": "C", "bras": {"C": {"statut": "estime"}}}
        texte, code = ab.bilan([object()], [ligne], True)
        self.assertEqual(code, 0)
        self.assertIn("bras C posté : 1", texte)
        self.assertIn("bras B : 0", texte)
        _, code = ab.bilan([RuntimeError("clé refusée")], [], True)
        self.assertEqual(code, 1)                      # tout a échoué : passage en rouge
        texte, code = ab.bilan([], [], True)
        self.assertEqual(code, 0)
        self.assertIn("aucune question ouverte", texte)

    def test_journal_autres(self):
        import asyncio, json, tempfile
        from datetime import datetime, timedelta, timezone
        import alphabet_pipeline as ap
        from forecasting_tools import MultipleChoiceQuestion, PredictedOptionList, ReasonedPrediction
        ancien, ap.REGISTRE = ap.REGISTRE, Path(tempfile.mkdtemp(prefix="registre-autres-"))
        try:
            b, _ = bot(dict(BASE, EXA_API_KEY="x", ALPHABET_LLM="anthropic/claude-sonnet-5-5",
                            ALPHABET_CHERCHEUR="smart-searcher/anthropic/claude-sonnet-5-5"))
            q = MultipleChoiceQuestion(question_text="Who?", id_of_question=99, page_url="https://www.metaculus.com/questions/99/",
                                       options=["a", "b"], scheduled_resolution_time=datetime.now(timezone.utc) + timedelta(days=9))
            pred = PredictedOptionList(predicted_options=[{"option_name": "a", "probability": 0.6},
                                                          {"option_name": "b", "probability": 0.4}])
            rp = b._journaliser_autre(q, "choix_multiple", ReasonedPrediction(prediction_value=pred, reasoning="r"))
            self.assertIs(rp.prediction_value, pred)            # la prévision postée est inchangée
            x = json.loads((ap.REGISTRE / "journal-autres.jsonl").read_text(encoding="utf-8").splitlines()[0])
            s = x.pop("sceau")
            self.assertEqual(s, ap.sceau(x))
            self.assertEqual(x["type"], "choix_multiple")
            self.assertEqual(x["prediction"]["predicted_options"][0]["option_name"], "a")
            texte, _ = ab.bilan([object()], [], True, [x])
            self.assertIn("autres questions journalisées (bras A seul) : 1", texte)
        finally:
            ap.REGISTRE = ancien

    def test_numerique_seconde_tentative(self):
        import asyncio, tempfile
        from datetime import datetime, timedelta, timezone
        import alphabet_pipeline as ap
        import main
        from forecasting_tools import NumericQuestion, ReasonedPrediction
        q = NumericQuestion(question_text="Share?", id_of_question=7, page_url="https://www.metaculus.com/questions/7/",
                            upper_bound=0.805, lower_bound=0.095, open_upper_bound=False, open_lower_bound=False,
                            unit_of_measure="", scheduled_resolution_time=datetime.now(timezone.utc) + timedelta(days=9))
        vues = []

        async def faux(self, question, research):
            vues.append(question.unit_of_measure)
            if len(vues) == 1:
                raise ValueError("Some declared percentiles are far exceeding the bounds of the question.")
            return ReasonedPrediction(prediction_value=0.5, reasoning="r")

        ancien_reg, ap.REGISTRE = ap.REGISTRE, Path(tempfile.mkdtemp(prefix="registre-num-"))
        with mock.patch.object(main.FallTemplateBot2026, "_run_forecast_on_numeric", faux):
            b, _ = bot(dict(BASE, EXA_API_KEY="x", ALPHABET_LLM="anthropic/claude-sonnet-5-5",
                            ALPHABET_CHERCHEUR="smart-searcher/anthropic/claude-sonnet-5-5"))
            try:
                rp = asyncio.run(b._run_forecast_on_numeric(q, "recherche"))
            finally:
                ap.REGISTRE = ancien_reg
        self.assertEqual(rp.prediction_value, 0.5)
        self.assertEqual(len(vues), 2)
        self.assertIn("NOT percentages", vues[1])
        self.assertEqual(q.unit_of_measure, "")                 # l'unité d'origine est rétablie

    def test_plafond_quotidien(self):
        import tempfile
        import alphabet_pipeline as ap
        ancien, ap.REGISTRE = ap.REGISTRE, Path(tempfile.mkdtemp(prefix="registre-budget-"))
        try:
            self.assertEqual(ab.deja_envoyees_aujourdhui(), 0)
            q = type("Q", (), {"page_url": "https://www.metaculus.com/questions/1/"})()
            ab.noter_passage("minibench", "planifie", 5, [q, q])
            ab.noter_passage("minibench", "planifie", 3, [q])
            self.assertEqual(ab.deja_envoyees_aujourdhui(), 3)
            self.assertEqual(ab.deja_envoyees_aujourdhui("2000-01-01"), 0)   # un autre jour ne compte pas
        finally:
            ap.REGISTRE = ancien

    def test_genre_chercheur(self):                                # 0.2.0 (audit, B9)
        cas = {"smart-searcher/anthropic/claude-haiku-5-5": ("smart_searcher", True),
               "asknews/news-summaries": ("asknews", True),
               "perplexity/sonar": ("llm_web", True),
               "anthropic/claude-sonnet-5-5": ("memoire", False)}
        for chercheur, (genre, reelle) in cas.items():
            env = dict(BASE, EXA_API_KEY="x", ALPHABET_LLM="anthropic/claude-sonnet-5-5", ALPHABET_CHERCHEUR=chercheur)
            b, _ = bot(env)
            self.assertEqual(b._genre_chercheur()[0], genre, chercheur)
            self.assertEqual(b._recherche_reelle(), reelle, chercheur)   # classification et exécution alignées

    def test_second_chercheur(self):                               # 0.3.0
        base = dict(BASE, EXA_API_KEY="x", ALPHABET_LLM="anthropic/claude-sonnet-5-5",
                    ALPHABET_CHERCHEUR="smart-searcher/anthropic/claude-haiku-5-5")
        b, (bloquants, _) = bot(base)
        self.assertIsNone(b._second_chercheur())
        with mock.patch.dict(os.environ, dict(base, ALPHABET_CHERCHEUR_2="asknews/news-summaries"), clear=True):
            b = ab.construire(publier=False)
            self.assertEqual(b._second_chercheur()[0], "asknews")
            bloquants, _ = ab.problemes(b, os.environ)
            self.assertTrue(any("ALPHABET_CHERCHEUR_2" in x for x in bloquants))   # clé AskNews absente
        with mock.patch.dict(os.environ, dict(base, ALPHABET_CHERCHEUR_2="anthropic/claude-haiku-5-5"), clear=True):
            b = ab.construire(publier=False)
            self.assertIsNone(b._second_chercheur())                                # pas de web : ignoré
            _, avert = ab.problemes(b, os.environ)
            self.assertTrue(any("ignoré" in x for x in avert))

    def test_historique_issues_seules(self):                       # 0.3.0
        import asyncio
        from datetime import datetime, timezone
        q = mock.Mock(question_text="Will A happen?", resolution_string="no", community_prediction_at_access_time=0.9,
                      actual_resolution_time=datetime(2025, 3, 1, tzinfo=timezone.utc), scheduled_resolution_time=None)
        filtres = []

        async def faux(self, f, *a, **k):
            filtres.append(f)
            return [q]
        b, _ = bot(dict(BASE, EXA_API_KEY="x", ALPHABET_LLM="anthropic/claude-sonnet-5-5",
                        ALPHABET_CHERCHEUR="smart-searcher/anthropic/claude-haiku-5-5"))
        with mock.patch.object(ab.MetaculusClient, "get_questions_matching_filter", faux):
            out = asyncio.run(b._historique(["border clash"], "2026-11-03"))
        self.assertEqual(out, [{"titre": "Will A happen?", "issue": "no", "resolue_le": "2025-03-01"}])  # rien d'autre
        self.assertEqual(filtres[0].other_url_parameters, {"search": "border clash"})
        self.assertEqual(filtres[0].allowed_statuses, ["resolved"])

    def test_sans_publier_reserve_a_la_zone_de_test(self):          # 0.5.1
        import subprocess
        r = subprocess.run([sys.executable, str(Path(ab.__file__)), "--mode", "minibench", "--sans-publier"],
                           capture_output=True, text=True, env=dict(os.environ, METACULUS_TOKEN="", ANTHROPIC_API_KEY=""))
        self.assertEqual(r.returncode, 1)
        self.assertIn("test_questions", r.stdout)

    def test_passage_garde_les_questions_recues(self):              # 0.5.1
        import tempfile
        import alphabet_pipeline as ap
        ancien, ap.REGISTRE = ap.REGISTRE, Path(tempfile.mkdtemp(prefix="registre-recues-"))
        try:
            q1 = type("Q", (), {"page_url": "u1", "id_of_question": 1})()
            q2 = type("Q", (), {"page_url": "u2", "id_of_question": 2})()
            ab.noter_passage("minibench", "planifie", 2, [q1], [q1, q2])
            import json as js
            x = js.loads((ap.REGISTRE / "passages.jsonl").read_text(encoding="utf-8"))
            self.assertEqual(x["trouvees_ids"], ["1", "2"])
            self.assertEqual(x["envoyees"], 1)
        finally:
            ap.REGISTRE = ancien


if __name__ == "__main__":
    unittest.main()
