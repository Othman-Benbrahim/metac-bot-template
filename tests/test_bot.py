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
        _, code = ab.bilan([RuntimeError("clé refusée")], [], True)
        self.assertEqual(code, 1)                      # tout a échoué : passage en rouge
        texte, code = ab.bilan([], [], True)
        self.assertEqual(code, 0)
        self.assertIn("aucune question ouverte", texte)


if __name__ == "__main__":
    unittest.main()
