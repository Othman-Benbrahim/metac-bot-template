"""0.10.40 : puits DBnomics (lecture d'une réponse, sans réseau)."""
from __future__ import annotations

import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import alphabet_puits as apz  # noqa: E402

REPONSE = {"series": {"docs": [{
    "provider_code": "IMF", "dataset_code": "WEO:latest", "series_code": "FRA.NGDP_RPCH", "series_name": "France – GDP",
    "@frequency": "annual",
    "period": ["2019", "2020", "2021", "2030"], "period_start_day": ["2019-01-01", "2020-01-01", "2021-01-01", "2030-01-01"],
    "value": [1.8, -7.5, "NA", 1.2]}]}}


class Tests(unittest.TestCase):
    def test_dbnomics(self):
        x, pts = apz.parser_dbnomics(REPONSE)
        self.assertEqual([p["date"] for p in pts], ["2019-01-01", "2020-01-01"])   # NA écarté, projection 2030 écartée
        self.assertEqual(pts[1]["valeur"], -7.5)
        self.assertEqual(pts[0]["publie_le"], "2020-03-26")                          # annuel : 450 jours de retard
        r = apz._releve("DBnomics", "t", "u", pts, date(2021, 1, 1))
        self.assertEqual(len(r["points"]), 1)                                        # 2020 n'était pas encore publié
        with self.assertRaises(RuntimeError):
            apz.parser_dbnomics({"series": {"docs": []}})
        self.assertIn("dbnomics", apz.CATALOGUE)
        self.assertIn("dbnomics_recherche", apz.catalogue_texte({}))


if __name__ == "__main__":
    unittest.main()
