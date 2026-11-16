"""0.10.205 : module Chine, couche 2 (contre-mesures chinoises lues dans GDELT, sans saisie à la main)."""
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest import mock

import collecte_gdelt as cg
import indicateurs_niche as ni


def ligne(acteur1, code, acteur2):
    col = [""] * 58
    col[7], col[26], col[28], col[17] = acteur1, code, code[:2], acteur2
    return "\t".join(col)


class TestChine(unittest.TestCase):
    def test_collecte(self):
        t = "\n".join([ligne("CHN", "163", "USA"), ligne("CHN", "1631", "USA"), ligne("CHN", "163", "JPN"),
                       ligne("USA", "163", "CHN"), ligne("CHN", "120", "USA"), ligne("CHN", "163", "CHN")])
        self.assertEqual(cg.sanctions_chine(t, {"USA": "US", "JPN": "JP", "CHN": "CN"}), {"US": 2, "JP": 1})

    def test_indicateur(self):
        d0 = date(2026, 11, 1)
        with tempfile.TemporaryDirectory() as t:
            f, j = Path(t) / "c.csv", Path(t) / "j.txt"
            f.write_text("pays,jour,evenements\nUS,2026-10-09,4\nUS,2026-03-01,5\nJP,2026-10-20,1\n", encoding="utf-8")
            j.write_text("\n".join((d0 - timedelta(days=k)).isoformat() for k in range(1, 91)), encoding="utf-8")
            with mock.patch.multiple(ni, CHINE_SANCTIONS=f, CHINE_JOURS=j):
                self.assertEqual(ni.contremesures_chine("US", d0)["valeur"], 4)
                self.assertEqual(ni.contremesures_chine("FR", d0)["valeur"], 0)
                j.write_text("2026-10-30\n", encoding="utf-8")
                self.assertFalse(ni.contremesures_chine("US", d0)["present"])


if __name__ == "__main__":
    unittest.main()
