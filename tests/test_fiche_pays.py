"""0.10.150 : fiche pays par la Banque mondiale (REST Countries v3.1 retiré)."""
import asyncio
import os
import tempfile
import unittest
from unittest import mock

os.environ["ALPHABET_REGISTRE"] = tempfile.mkdtemp(prefix="registre-")
import alphabet_pipeline as _ap_regle_ab
_ap_regle_ab.POSTER_AB = False

import banc_indicateurs as bi

BM = [{"page": 1}, [
    {"id": "RUS", "iso2Code": "RU", "name": "Russian Federation", "region": {"value": "Europe & Central Asia"},
     "capitalCity": "Moscow", "longitude": "37.6176", "latitude": "55.7558"},
    {"id": "WLD", "iso2Code": "1W", "name": "World", "region": {"value": "Aggregates"}, "capitalCity": "",
     "longitude": "", "latitude": ""},
]]


class TestFiche(unittest.TestCase):
    def test_alias_et_agregats(self):
        async def obtenir(c, url, pause=0.3):
            return BM if "worldbank" in url else None

        bi._PAYS_BM = None
        with mock.patch.object(bi, "obtenir", obtenir):
            b = asyncio.new_event_loop()
            try:
                f = b.run_until_complete(bi.fiche_pays(None, "Russia", {}))
            finally:
                b.close()
        self.assertEqual((f["cca2"], f["capitale"]), ("RU", "Moscow"))
        self.assertNotIn("world", bi._PAYS_BM)
        bi._PAYS_BM = None


if __name__ == "__main__":
    unittest.main()
