"""0.10.189 : audit « fuite temporelle ALFRED / FRED » (2026-11-16). Une série révisable n'est jamais lue sans
millésime ALFRED ; seules les cotations de marché de la liste fermée MARCHES_NON_REVISES peuvent l'être."""
import asyncio
import os
import tempfile
import unittest
from datetime import date, timedelta
from unittest import mock

os.environ["ALPHABET_REGISTRE"] = tempfile.mkdtemp(prefix="registre-")
import alphabet_pipeline as _ap_regle_ab
_ap_regle_ab.POSTER_AB = False

import alphabet_puits as apz
import banc_forecastbench as fb


def points(n=400, fin=date(2026, 10, 24)):
    return [{"date": (fin - timedelta(days=k)).isoformat(), "valeur": 100 + (k % 7)} for k in range(n)][::-1]


def lancer(serie, reponse_alfred, reponse_actuelle=None):
    appels = []

    async def fred(s, avant=None, debut=None):
        appels.append(avant)
        return reponse_alfred if avant else (reponse_actuelle or {"source": "FRED", "titre": s, "points": points()})

    x = {"resolution": "2026-11-01", "titre": f"{serie} higher?"}
    q = {"source": "fred", "id": serie, "question": f"Will {serie} increase?"}
    with mock.patch.object(apz, "fred", fred):
        b = asyncio.new_event_loop()
        try:
            v = b.run_until_complete(fb.vue_calculee(x, q, "2026-10-25"))
        finally:
            b.close()
    return v, appels, x


class TestAuditAlfred(unittest.TestCase):
    def test_millesime_valide(self):
        v, appels, x = lancer("UNRATE", {"source": "FRED (ALFRED, millésime)", "titre": "UNRATE", "points": points()})
        self.assertIsNotNone(v)
        self.assertEqual(len(appels), 1)
        self.assertIn("ALFRED", x["_provenance"])

    def test_revisable_sans_millesime_refuse(self):
        v, appels, x = lancer("UNRATE", {"points": []})
        self.assertIsNone(v)
        self.assertEqual(len(appels), 1)                        # plus de second appel FRED actuel
        self.assertIn("refusé", x["_provenance"])

    def test_revisable_millesime_indisponible_refuse(self):
        v, appels, _ = lancer("UNRATE", {"points": points(), "millesime": "indisponible : série publiée aujourd'hui"})
        self.assertIsNone(v)

    def test_marche_exception_maintenue(self):
        v, appels, x = lancer("SP500", {"points": []})
        self.assertIsNotNone(v)
        self.assertEqual(len(appels), 2)
        self.assertIn("exception", x["_provenance"])

    def test_liste_fermee(self):
        for s in ("SP500", "DGS10", "BAMLH0A0HYM2", "DEXUSEU", "T10Y3M", "VIXCLS", "SOFR90DAYAVG"):
            self.assertTrue(fb.marche_non_revise(s), s)
        for s in ("UNRATE", "ICSA", "CC4WSA", "ANFCI", "WEI", "TOTLL", "WM1NS", "STLFSI4", "MORTGAGE30US"):
            self.assertFalse(fb.marche_non_revise(s), s)


class TestPuitsFred(unittest.TestCase):
    def _fred(self, serie):
        appels = []

        async def get(url, p):
            appels.append(dict(p))
            if "realtime_start" in p:
                raise apz.ErreurSource("HTTP 400 : pas de millésime")
            return {"observations": [{"date": "2026-10-01", "value": "1.0"}]}

        with mock.patch.object(apz, "_get", get), mock.patch.dict(os.environ, {"FRED_API_KEY": "x"}):
            b = asyncio.new_event_loop()
            try:
                return b.run_until_complete(apz.fred(serie, avant=date(2026, 10, 25))), appels
            finally:
                b.close()

    def test_revisable_refuse(self):
        with self.assertRaises(apz.ErreurSource):
            self._fred("UNRATE")

    def test_marche_relu(self):
        r, appels = self._fred("SP500")
        self.assertEqual(len(appels), 2)
        self.assertIn("indisponible", r["millesime"])


if __name__ == "__main__":
    unittest.main()
