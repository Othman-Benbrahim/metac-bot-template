"""0.10.43 : banc ForecastBench (appariement, construction, garde-fous ; sans réseau)."""
from __future__ import annotations

import asyncio
import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import alphabet_pipeline as ap  # noqa: E402
import banc_forecastbench as fb  # noqa: E402

Q = {"questions": [
    {"id": "SOFR", "source": "fred", "question": "Will X have increased by {resolution_date} vs {forecast_due_date}?",
     "background": "b", "resolution_criteria": "r", "url": "u", "freeze_datetime": "2026-10-15T00:00:00+00:00",
     "freeze_datetime_value": "4.1", "freeze_datetime_value_explanation": "taux"},
    {"id": "11045", "source": "metaculus", "question": "Will a Democrat win?", "freeze_datetime_value": "0.6"},
    {"id": ["A", "B"], "source": "fred", "question": "combo"}]}
R = {"resolutions": [
    {"id": "SOFR", "source": "fred", "resolution_date": "2026-11-24", "resolved_to": 0.0, "resolved": True},
    {"id": "SOFR", "source": "fred", "resolution_date": "2026-11-01", "resolved_to": 1.0, "resolved": True},
    {"id": "11045", "source": "metaculus", "resolution_date": "2026-11-01", "resolved_to": 0.6, "resolved": False},
    {"id": ["A", "B"], "source": "fred", "resolution_date": "2026-11-01", "resolved_to": 1.0, "resolved": True}]}


class Tests(unittest.TestCase):
    def test_banc(self):
        items = fb.apparier(Q, R)
        self.assertEqual(len(items), 1)                                   # marché et combinée écartés
        self.assertEqual((items[0]["resolution_date"], items[0]["issue"]), ("2026-11-01", 1))   # premier horizon
        x = fb.construire(items[0], "2026-10-25")
        self.assertEqual(x["titre"], "Will X have increased by 2026-11-01 vs 2026-10-25?")
        self.assertIn("4.1", x["contexte"])
        self.assertTrue(x["qid"].startswith("fb:2026-10-25:fred:SOFR:"))
        self.assertNotIn("metaculus", fb.SOURCES_SERIES)
        self.assertEqual(fb.apparier(Q, R, ("metaculus",)), [])             # jamais de cote de foule : non résolue
        j = fb.jeux_candidats(date(2026, 11, 11), date(2026, 9, 1))
        self.assertEqual(j[:3], ["2026-10-25", "2026-10-11", "2026-09-27"])
        self.assertTrue(all(d > "2026-09-01" for d in j))


    def test_b_calcule(self):
        self.assertLess(fb.b_acled(0.0), 0.06)                      # aucun événement en 360 jours : rare
        self.assertAlmostEqual(fb.b_acled(160.0), 0.5, delta=0.03)   # gros comptes : environ une chance sur deux
        pts = [{"date": f"2026-{1 + i // 28:02d}-{1 + i % 28:02d}", "valeur": float(i)} for i in range(200)]
        f, k, n = fb.b_hausse(pts, 7, date(2026, 10, 25))
        self.assertGreater(f, 0.9)                                   # série toujours croissante
        self.assertIsNone(fb.b_hausse(pts[:5], 7, date(2026, 10, 25)))
        x = {"resolution": "2026-11-01"}
        q = {"source": "yfinance", "question": "Will A have a higher rate of return than B between ...?", "id": "A_B"}
        v = asyncio.run(fb.vue_calculee(x, q, "2026-10-25"))
        self.assertEqual(v["frequence"], 0.5)
        self.assertIsNone(ap.controle_vue(v, "2026-10-25"))          # la vue passe les contrôles du bot
        q2 = {"source": "acled", "freeze_datetime_value": "0.25", "freeze_datetime": "2026-10-15T00:00:00+00:00"}
        v2 = asyncio.run(fb.vue_calculee(x, q2, "2026-10-25"))
        self.assertIsNone(ap.controle_vue(v2, "2026-10-25"))
        x3 = dict(x, criteres="Résolu OUI si …", url="https://acleddata.com", source="acled", titre="t")
        v3 = asyncio.run(fb.vue_calculee(x3, q2, "2026-10-25"))
        self.assertTrue(v3["resolution"] and v3["source_resolution"]["emetteur"] == "ACLED")   # 0.10.46

    def test_reparations(self):
        d = {"mots": [{"carte": "POL", "strate": 6, "intensite": "f"}], "candidats": ["POL@6"],
             "rejets": {"POL@6": "x"}, "_categories_rejet": {"POL@6": "aucun_fait"},
             "liaisons": [{"de": "POL@6", "type": "renforcement", "vers": "CTR@6"}, {"bizarre": 1}, "trop court"]}
        notes = ap.reparer_dossier(d, {"candidats": ["CTR@6", "SEU@7"]})
        self.assertNotIn("POL@6", d["rejets"])                       # ancrée : plus rejetée
        self.assertEqual(d["candidats"], ["POL@6", "CTR@6"])          # complétée par le plan, même strate
        self.assertIn("non_cherchee", d["rejets"]["CTR@6"])
        self.assertEqual(d["liaisons"], ["POL@6 renforcement CTR@6"])
        self.assertGreaterEqual(len(notes), 4)
        self.assertEqual(ap.cle_normale("POLARITÉ@13_portee"), "POL@13")
        self.assertEqual(ap.code_carte("POL@6"), "POL")
        # 0.10.46 : clé sans strate, rejet hors des candidates, contre-candidate manquante
        d2 = {"mots": [{"carte": "INC", "strate": 6, "intensite": "f"}], "candidats": ["INC", "CTR@6"],
              "rejets": {"CTR@6": "a", "SEU@6": "b"}, "_categories_rejet": {}, "liaisons": [], "contre_candidate": None}
        ap.reparer_dossier(d2, {"evenement": {"carte": "SEU", "strate": 6}, "candidats": []})
        self.assertEqual(d2["candidats"], ["INC@6", "CTR@6", "SEU@6"])
        self.assertEqual(d2["contre_candidate"], ["CTR@6"])


if __name__ == "__main__":
    unittest.main()
