"""0.10.138 : indicateurs de niche, avec un faux client HTTP."""
import asyncio
import json
import os
import tempfile
import unittest
from datetime import date, timedelta

os.environ["ALPHABET_REGISTRE"] = tempfile.mkdtemp(prefix="registre-")
import alphabet_pipeline as _ap_regle_ab
_ap_regle_ab.POSTER_AB = False

import indicateurs_niche as ni
import induction as ind


class Rep:
    def __init__(self, j=None, texte=None):
        self.status_code = 200
        self._j, self.text = j, texte

    def json(self):
        return self._j


class FauxClient:
    def __init__(self, d0):
        self.d0 = d0

    async def get(self, url, **kw):
        if "edits/per-page" in url:
            if "Politics_of" not in url:
                r = Rep({})
                r.status_code = 404
                return r
            res = [{"timestamp": (self.d0 - timedelta(days=i)).isoformat() + "T00:00:00.000Z",
                    "edits": 3 if i <= 30 else 1} for i in range(1, 210)]
            return Rep({"items": [{"results": res}]})
        if "package_show" in url:
            return Rep({"result": {}})
        if "package_search" in url:
            return Rep({"result": {"results": [{"title": "Kenya - WFP food prices for Kenya",
                                                "resources": [{"format": "CSV", "url": "http://x/kenya.csv"}]}]}})
        if url.endswith("kenya.csv"):
            lignes = ["date,market,commodity,unit,pricetype,price", "#date,#loc,#item,#unit,#type,#value"]
            for m in ("A", "B", "C"):
                lignes.append(f"2025-08-15,{m},Maize,KG,Retail,100")
                lignes.append(f"2026-07-15,{m},Maize,KG,Retail,120")
            return Rep(texte="\n".join(lignes))
        return None


def lancer(coro):
    b = asyncio.new_event_loop()
    try:
        return b.run_until_complete(coro)
    finally:
        b.close()


class TestNiche(unittest.TestCase):
    def test_wikimodif(self):
        d0 = date(2026, 9, 1)
        r = lancer(ni.wikimodif(FauxClient(d0), "Kenya", d0))
        self.assertTrue(r["present"])
        self.assertEqual(r["pages"], 1)
        self.assertGreater(r["valeur"], 0.5)        # 3 modifs/jour récemment contre 1 avant

    def test_prix_alim(self):
        d0 = date(2026, 9, 1)
        r = lancer(ni.prix_alim(FauxClient(d0), "Kenya", d0, {}, {}))
        self.assertTrue(r["present"])
        self.assertAlmostEqual(r["valeur"], 0.1823, places=3)   # log(120/100)

    def test_vols(self):
        from unittest import mock

        class C:
            async def post(self, url, data=None, timeout=None):
                class R:
                    status_code = 200
                    def raise_for_status(self): pass
                    def json(self): return {"access_token": "t", "expires_in": 1800}
                return R()

            async def get(self, url, params=None, headers=None, timeout=None):
                assert headers == {"Authorization": "Bearer t"}
                n = 9 if params["end"] - params["begin"] == 7 * 86400 and params["end"] % 86400 == 0 and params["begin"] > 1788000000 else 19
                return Rep([{}] * n)

        with mock.patch.dict(os.environ, {"OPENSKY_CLIENT_ID": "i", "OPENSKY_CLIENT_SECRET": "s"}):
            o = ni.OpenSky(C())
            self.assertTrue(o.disponible)
            o.aeroports = [{"iso_country": "KE", "type": "large_airport", "scheduled_service": "yes", "ident": "HKJK",
                            "latitude_deg": "-1.3", "longitude_deg": "36.9"}]
            self.assertEqual(lancer(o.aeroport("KE", [-1.28, 36.8])), "HKJK")
            n = lancer(o.arrivees("HKJK", date(2026, 8, 25), date(2026, 9, 1)))
            self.assertIsInstance(n, int)

    def test_telegram(self):
        from datetime import datetime, timezone

        class M:
            def __init__(self, d): self.date = d

        class FauxTg:
            def iter_messages(self, ent, search=None, offset_date=None):
                assert ent is None and search == "Kenya"
                dates = [offset_date - timedelta(days=i) for i in (1, 2, 3, 4, 20, 30)]

                async def gen():
                    for d in dates:
                        yield M(d)
                return gen()

        tg = ni.Telegram()
        tg.client = FauxTg()
        r = lancer(ni.telegram(tg, "Kenya", date(2026, 9, 1)))
        self.assertEqual((r["messages_14j"], r["messages_14j_avant"]), (4, 1))   # le message à 30 jours arrête la lecture
        self.assertGreater(r["valeur"], 0)

    def test_induction_lit_les_niches(self):
        import pathlib
        from unittest import mock
        f = pathlib.Path(tempfile.mkdtemp()) / "niche.jsonl"
        f.write_text(json.dumps({"pays": "Kenya", "jeu": "2026-09-01", "wikimodif": {"present": False},
                                 "prix_alim": {"present": True, "valeur": 0.2}}) + "\n")
        ls = [{"pays": "Kenya", "jeu": "2026-09-01", "famille": "mobilisation", "issue": 1, "p_B": 0.3, "presents": {}}]
        with mock.patch.object(ind, "NICHE", f):
            x = ind.joindre_niche(ls)[0]
        self.assertEqual(x["prix_alim"], 0.2)
        self.assertTrue(x["presents"]["prix_alim"])
        self.assertNotIn("wikimodif", x["presents"])


if __name__ == "__main__":
    unittest.main()
