"""0.10.204 : module Chine, couche 2 (contre-mesures, registre tenu à la main)."""
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

import indicateurs_niche as ni


class TestContremesures(unittest.TestCase):
    def test_vide_puis_compte(self):
        with tempfile.TemporaryDirectory() as t:
            f = Path(t) / "c.csv"
            f.write_text("date,liste,pays_vise,entites,source\n", encoding="utf-8")
            with mock.patch.object(ni, "CHINE_CONTREMESURES", f):
                self.assertFalse(ni.contremesures_chine("US", date(2026, 11, 1))["present"])
                f.write_text("date,liste,pays_vise,entites,source\n2026-10-09,controle_exportations,US,14,x\n"
                             "2026-03-01,non_fiables,US,5,x\n2026-10-20,controle_exportations,JP,3,x\n", encoding="utf-8")
                r = ni.contremesures_chine("US", date(2026, 11, 1))
                self.assertEqual((r["valeur"], r["entites"]), (1, 14))
                self.assertEqual(ni.contremesures_chine("FR", date(2026, 11, 1))["valeur"], 0)


if __name__ == "__main__":
    unittest.main()
