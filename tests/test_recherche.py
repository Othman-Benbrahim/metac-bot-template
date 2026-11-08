"""Tests hors ligne de la chaîne de recherche (0.6.1)."""
import asyncio
import os
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import alphabet_recherche as ar  # noqa: E402


class TestsChaine(unittest.TestCase):
    def test_bascule_seconde_cle_puis_moteurs(self):
        env = {"EXA_API_KEY": "k1", "EXA_API_KEY_2": "k2", "TAVILY_API_KEY": "t"}
        vues = []

        async def exa(q):
            vues.append(env["EXA_API_KEY"])
            if env["EXA_API_KEY"] == "k1":
                raise RuntimeError("402 quota")
            return "résultat exa"
        ch = ar.Chaine(exa, env)
        t = asyncio.run(ch.chercher("q"))
        self.assertTrue(t.startswith("[moteur : exa2]"))
        self.assertEqual(vues, ["k1", "k2"])
        self.assertTrue(ch.seconde_cle)
        asyncio.run(ch.chercher("q2"))
        self.assertEqual(vues[-1], "k2")                          # la bascule vaut pour tout le passage

        async def exa_mort(q):
            raise RuntimeError("402")

        async def tavily(q, avant=None):
            return "[2026-11-01] titre — https://x\nextrait"
        ch = ar.Chaine(exa_mort, dict(env, EXA_API_KEY_2=""))
        with mock.patch.dict(ar.MOTEURS_HTTP, {"tavily": ("TAVILY_API_KEY", tavily)}):
            t = asyncio.run(ch.chercher("q"))
        self.assertTrue(t.startswith("[moteur : tavily]"))
        self.assertEqual(ar.moteur_de(t), "tavily")
        self.assertNotIn("brave", ar.MOTEURS_HTTP)                 # 0.6.2 : Brave retiré

    def test_sans_cle_saute_et_tout_echoue(self):
        async def vide(q, avant=None):
            return ""
        ch = ar.Chaine(None, {}, ordre="exa,tavily,gdelt")
        with mock.patch.dict(ar.MOTEURS_HTTP, {"gdelt": (None, vide)}):
            with self.assertRaises(RuntimeError) as e:
                asyncio.run(ch.chercher("q"))
        self.assertIn("gdelt : aucun résultat", str(e.exception))     # exa et tavily sautés (pas de clé)

    def test_gdelt_borne_dans_le_temps(self):
        vu = {}

        class Rep:
            text = ""

            def raise_for_status(self):
                pass

            def json(self):
                return {"articles": [{"title": "T", "url": "u", "seendate": "20261001T000000Z", "domain": "d",
                                      "sourcecountry": "France", "language": "French"}]}

        class Client:
            def __init__(self, *a, **k):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, *a):
                pass

            async def get(self, url, params=None, headers=None):
                vu.update(params)
                return Rep()
        with mock.patch.object(ar.httpx, "AsyncClient", Client):
            t = asyncio.run(ar.gdelt("Escalade, frontière ?", datetime(2026, 10, 15, tzinfo=timezone.utc)))
        self.assertEqual(vu["enddatetime"], "20261015000000")
        self.assertNotIn(",", vu["query"])
        self.assertIn("T — u", t)


if __name__ == "__main__":
    unittest.main()
