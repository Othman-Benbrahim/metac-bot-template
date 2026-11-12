"""0.10.50 : recherche bornée des tests rétrospectifs et du banc ForecastBench sans Exa (TinyFish, pages datées)."""
from __future__ import annotations

import asyncio
import os
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import alphabet_recherche as rech  # noqa: E402
import alphabet_retro as ar  # noqa: E402


class Tests(unittest.TestCase):
    def test_tinyfish_relais(self):
        with mock.patch.dict(os.environ, {"TINYFISH_API_KEY": "tf"}, clear=True):
            self.assertTrue(ar.recherche_bornee_disponible())
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertFalse(ar.recherche_bornee_disponible())       # GDELT seul ne suffit pas
        avant = datetime(2026, 10, 25, tzinfo=timezone.utc)
        vus = {}

        async def faux_tinyfish(q, av=None):
            vus["avant"] = av
            return "[2026-10-20] Titre — https://exemple.org/a\nextrait"
        ar._CHAINE = None
        with mock.patch.dict(os.environ, {"TINYFISH_API_KEY": "tf"}, clear=True), \
                mock.patch.dict(rech.MOTEURS_HTTP, {"tinyfish": ("TINYFISH_API_KEY", faux_tinyfish)}):
            t = asyncio.run(ar.chercher_avant("q", avant))
        self.assertIn("[moteur : tinyfish]", t)
        self.assertEqual(vus["avant"], avant)                          # la date limite est bien transmise
        self.assertEqual(ar.moteurs_utilises(), {"tinyfish": 1})
        ar._CHAINE = None


if __name__ == "__main__":
    unittest.main()
