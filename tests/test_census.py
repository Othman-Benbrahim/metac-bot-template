"""0.10.93 : puits Census Bureau (indicateurs économiques mensuels), réponse simulée."""
import asyncio
import os
import pathlib
import sys
import unittest
from datetime import date
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import alphabet_puits as apz  # noqa: E402

REPONSE = [["cell_value", "time_slot_id", "data_type_code", "category_code", "seasonally_adj", "time", "us"],
           ["700,123", "0", "SM", "44X72", "yes", "2026-07", "1"],
           ["701500", "0", "SM", "44X72", "yes", "2026-08", "1"],
           ["(S)", "0", "SM", "44X72", "yes", "2026-09", "1"]]


class Census(unittest.TestCase):
    def test_lecture_et_borne(self):
        vus = {}

        async def faux_get(url, params=None, headers=None, json_=True):
            vus.update(url=url, params=params)
            return REPONSE
        with mock.patch.object(apz, "_get", faux_get), mock.patch.dict(os.environ, {"CENSUS_API_KEY": "k"}):
            r = asyncio.run(apz.census_eits("MARTS", "44X72", "SM", avant=date(2026, 9, 20)))
        self.assertTrue(vus["url"].endswith("/eits/marts"))
        self.assertEqual(vus["params"]["key"], "k")
        # août paraît vers le 15 septembre (retard 45 jours) : connu le 20 ; la valeur « (S) » est écartée
        self.assertEqual([p["date"] for p in r["points"]], ["2026-07-01", "2026-08-01"])
        self.assertEqual(r["points"][0]["valeur"], 700123.0)
        r = asyncio.run(self._sans_cle(date(2026, 9, 10)))
        self.assertEqual([p["date"] for p in r["points"]], ["2026-07-01"])
        self.assertIn("census_eits", apz.CATALOGUE)
        self.assertIn("key=***", apz.masquer("https://api.census.gov/data/x?key=SECRET&for=us:*"))

    async def _sans_cle(self, avant):
        async def faux_get(url, params=None, headers=None, json_=True):
            assert "key" not in params
            return REPONSE
        with mock.patch.object(apz, "_get", faux_get), mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("CENSUS_API_KEY", None)
            return await apz.census_eits("marts", "44X72", "SM", avant=avant)


if __name__ == "__main__":
    unittest.main()
