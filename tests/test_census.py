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


class Diagnostics94(unittest.TestCase):
    def test_codes_gw(self):
        self.assertEqual(apz.code_gw("Sudan"), "625")
        self.assertEqual(apz.code_gw(" south sudan "), "626")
        self.assertEqual(apz.code_gw("625,626"), "625,626")
        with self.assertRaises(apz.ErreurSource):
            apz.code_gw("Atlantis")

    def test_reponse_non_json_dite(self):
        import httpx

        def rep(request):
            return httpx.Response(200, text="<html><body>Invalid Key. key=SECRET</body></html>")
        transport = httpx.MockTransport(rep)
        vrai = httpx.AsyncClient
        with mock.patch.object(apz.httpx, "AsyncClient", lambda **kw: vrai(transport=transport, **kw)):
            with self.assertRaises(apz.ErreurSource) as e:
                asyncio.run(apz._get("https://api.census.gov/data/x", {"key": "SECRET"}))
        self.assertIn("Invalid Key", str(e.exception))
        self.assertNotIn("SECRET", str(e.exception))

    def test_bls_statut(self):
        import httpx

        def rep(request):
            return httpx.Response(200, json={"status": "REQUEST_NOT_PROCESSED", "message": ["daily threshold"]})
        transport = httpx.MockTransport(rep)
        vrai = httpx.AsyncClient
        with mock.patch.object(apz.httpx, "AsyncClient", lambda **kw: vrai(transport=transport, **kw)):
            with self.assertRaises(apz.ErreurSource) as e:
                asyncio.run(apz.bls("LNS14000000"))
        self.assertIn("daily threshold", str(e.exception))


class Firms211(unittest.TestCase):
    """0.10.211 : l'API « country » de FIRMS ne répond plus ; la source lit le registre des feux."""

    def test_lit_le_registre(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as t:
            d = Path(t) / "registre"
            d.mkdir()
            (d / "feux.csv").write_text("pays,jour,detections,forte_confiance\nGR,2026-05-30,2,1\nGR,2026-05-31,1,0\n"
                                        "FR,2026-05-31,9,0\n", encoding="utf-8")
            (d / "feux-jours.txt").write_text("2026-05-29\n2026-05-30\n2026-05-31\n", encoding="utf-8")

            async def faux_get(url, params=None, headers=None, json_=True):
                return "ISO3166-1-Alpha-2,ISO3166-1-Alpha-3\nGR,GRC\nFR,FRA\n"
            ici = os.getcwd()
            try:
                os.chdir(t)
                with mock.patch.object(apz, "_get", faux_get), mock.patch.dict(os.environ, {"FIRMS_MAP_KEY": "k"}):
                    r = asyncio.run(apz.firms("GRC", 3, avant=date(2026, 5, 31)))
                    self.assertEqual(sorted(p["valeur"] for p in r["points"]), [1.0, 2.0])
                    with self.assertRaises(apz.ErreurSource):
                        asyncio.run(apz.firms("GRC", 3, avant=date(2026, 9, 1)))
            finally:
                os.chdir(ici)

if __name__ == "__main__":
    unittest.main()
