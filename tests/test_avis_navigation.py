"""0.10.206 : avertissements de navigation (NGA), exercices chinois, module Chine couche 3."""
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

import collecte_avis_navigation as an
import indicateurs_niche as ni

W = {"navArea": "P", "msgYear": 2026, "msgNumber": 1234, "issueDate": "091200Z NOV 2026", "cancelDate": None,
     "text": "EAST CHINA SEA. ZHEJIANG. CHINESE MILITARY EXERCISES 0000Z TO 0800Z DAILY 10 THRU 12 NOV IN AREA BOUND BY ..."}


class TestAvis(unittest.TestCase):
    def test_date(self):
        self.assertEqual(an.date_iso("091200Z NOV 2026"), "2026-11-09")
        self.assertIsNone(an.date_iso(None))

    def test_classer(self):
        f = an.classer(W)
        self.assertEqual(f["id"], "P-2026-1234")
        self.assertEqual(f["emission"], "2026-11-09")
        self.assertEqual(f["pays"], "CN;JP;TW")
        self.assertEqual(f["militaire"], 1)
        self.assertIn("EAST CHINA SEA", f["zones"])
        self.assertNotIn("CHINA", f["zones"].split(";"))       # « CHINA » inclus dans « EAST CHINA SEA » : pas compté
        self.assertIsNone(an.classer({"text": "GULF OF MEXICO. HAZARDOUS OPERATIONS."}))
        self.assertEqual(an.classer({**W, "text": "SOUTH CHINA SEA. DERELICT VESSEL ADRIFT."})["militaire"], 0)

    def test_indicateur(self):
        with tempfile.TemporaryDirectory() as t:
            f, j = Path(t) / "a.csv", Path(t) / "j.txt"
            x = {**an.classer(W), "premier_vu": "2026-11-09"}
            f.write_text(",".join(an.CHAMPS) + "\n" + ",".join(f'"{x.get(k, "")}"' for k in an.CHAMPS) + "\n", encoding="utf-8")
            j.write_text("2026-10-20\n2026-11-15\n", encoding="utf-8")
            with mock.patch.multiple(ni, AVIS_NAVIGATION=f, AVIS_JOURS=j):
                self.assertEqual(ni.avis_navigation("TW", date(2026, 11, 16))["valeur"], 1)
                self.assertEqual(ni.avis_navigation("PH", date(2026, 11, 16))["valeur"], 0)
                self.assertFalse(ni.avis_navigation("TW", date(2026, 10, 25))["present"])


if __name__ == "__main__":
    unittest.main()
