"""0.10.222 : M17, coopération militaire avec le rival d'une puissance proche (GDELT, paires de pays)."""
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest import mock

import collecte_gdelt as cg
import indicateurs_niche as ni

ISO = {"CHN": "CN", "JPN": "JP", "PHL": "PH", "USA": "US", "FRA": "FR"}


def ligne(a1, code, a2, quad="1"):
    col = [""] * 58
    col[7], col[26], col[28], col[17], col[29] = a1, code, code[:2], a2, quad
    return "\t".join(col)


class TestM17(unittest.TestCase):
    def test_collecte(self):
        t = "\n".join([ligne("JPN", "062", "PHL"), ligne("PHL", "0312", "JPN"), ligne("CHN", "152", "PHL", "4"),
                       ligne("CHN", "112", "JPN", "3"), ligne("CHN", "042", "JPN", "1"), ligne("CHN", "062", "CHN")])
        j, m = cg.paires(t, ISO)
        self.assertEqual(j[("JP", "PH")], [1, 0])
        self.assertEqual(j[("PH", "JP")], [1, 0])
        self.assertEqual(j[("CN", "PH")], [0, 1])
        self.assertEqual(m[("CN", "JP")], [2, 1])
        self.assertEqual(m[("CN", "PH")], [1, 1])

    def test_indicateur(self):
        d0 = date(2026, 11, 10)
        with tempfile.TemporaryDirectory() as t:
            fj, fm, fd = Path(t) / "j.csv", Path(t) / "m.csv", Path(t) / "d.txt"
            mois = [f"2025-{m:02d}" for m in range(11, 13)] + [f"2026-{m:02d}" for m in range(1, 11)]
            lignes = ["mois,a,b,evenements,conflit"]
            for mo in mois:
                lignes += [f"{mo},CN,JP,100,40", f"{mo},CN,PH,50,30", f"{mo},FR,JP,100,5"]
            fm.write_text("\n".join(lignes) + "\n", encoding="utf-8")
            fj.write_text("jour,a,b,coop_mil,force\n2026-11-05,JP,PH,2,0\n2026-11-06,FR,JP,3,0\n2026-10-01,JP,PH,9,0\n",
                          encoding="utf-8")
            jours = [f"{mo}-01" for mo in mois] + [(d0 - timedelta(days=k)).isoformat() for k in range(1, 15)]
            fd.write_text("\n".join(jours) + "\n", encoding="utf-8")
            with mock.patch.multiple(ni, PAIRES_JOUR=fj, PAIRES_MOIS=fm, PAIRES_JOURS=fd), \
                    mock.patch.object(ni, "voisins", lambda c: []):
                self.assertEqual(ni.rivalites(d0), {("CN", "JP"), ("CN", "PH")})
                r = ni.alignement_rival("PH", d0)
                self.assertEqual((r["valeur"], r["puissances"]), (2, ["CN"]))
                self.assertEqual(ni.alignement_rival("FR", d0)["valeur"], 0)   # la Chine n'est ni rivale ni voisine de la France


if __name__ == "__main__":
    unittest.main()
