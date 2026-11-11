"""Bot 0.10.17 : aucune clé d'API dans le registre ; millésime FRED jamais dans le futur de Saint-Louis."""
from __future__ import annotations

import asyncio
import os
import sys
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import alphabet_pipeline as ap  # noqa: E402
import alphabet_puits as pz  # noqa: E402


class Tests(unittest.TestCase):
    def test_sans_cles(self):
        u = "url 'https://x.org/a?series_id=F&api_key=abc123&token=zz&file_type=json'"
        self.assertEqual(pz.masquer(u), "url 'https://x.org/a?series_id=F&api_key=***&token=***&file_type=json'")
        self.assertNotIn("abc123", str(ap.sans_cles({"a": [{"motif": u}]})))
        self.assertEqual(ap.sans_cles({"p": 0.3, "t": "rien"}), {"p": 0.3, "t": "rien"})

    def test_fred_millesime(self):
        vu = {}

        async def faux_get(url, params=None, **k):
            vu.update(params)
            return {"observations": []}
        os.environ.setdefault("FRED_API_KEY", "test")
        ancien = pz._get
        pz._get = faux_get
        try:
            asyncio.run(pz.fred("FYONET", avant=datetime.now(timezone.utc).date()))
        finally:
            pz._get = ancien
        hier = (datetime.now(timezone.utc).date() - timedelta(days=1)).isoformat()
        self.assertEqual((vu["realtime_start"], vu["realtime_end"]), (hier, hier))
        self.assertEqual(vu["observation_end"], datetime.now(timezone.utc).date().isoformat())


if __name__ == "__main__":
    unittest.main()
