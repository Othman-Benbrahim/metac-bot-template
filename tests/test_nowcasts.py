"""0.10.181 : nowcasts publics (GDPNow par ALFRED, inflation de Cleveland par relevés quotidiens)."""
import asyncio
import os
import tempfile
import unittest
from datetime import date
from pathlib import Path

os.environ["ALPHABET_REGISTRE"] = tempfile.mkdtemp(prefix="registre-")
import alphabet_puits as ap
import collecte_nowcast_inflation as cn

PAGE = """<h3>Month-over-month percent change</h3><table><tr><th>Month</th><th>CPI</th><th>Core CPI</th><th>PCE</th><th>Core PCE</th></tr>
<tr><td>November 2026</td><td>0.31</td><td>0.28</td><td>0.25</td><td>0.24</td></tr></table>
<h3>Year-over-year percent change</h3><table><tr><th>Month</th><th>CPI</th></tr><tr><td>November 2026</td><td>3.9</td></tr></table>
<table><tr><th>Quarter</th><th>CPI</th><th>Core CPI</th></tr><tr><td>2026:Q4</td><td>3.1</td><td>2.9</td></tr></table>
<table><tr><th>Autre</th><th>x</th></tr><tr><td>a</td><td>1</td></tr></table>"""


class TestNowcasts(unittest.TestCase):
    def test_releves(self):
        r = cn.releves(cn.tableaux(PAGE))
        self.assertIn(("November 2026", "variation_mensuelle:CPI", 0.31), r)
        self.assertIn(("November 2026", "glissement_annuel:CPI", 3.9), r)
        self.assertIn(("2026:Q4", "trimestre_annualise:Core CPI", 2.9), r)
        self.assertEqual(len(r), 7)
        sans_titres = [("", t) for _, t in cn.tableaux(PAGE)]           # sans titre : l'ordre de la page décide
        self.assertIn(("November 2026", "glissement_annuel:CPI", 3.9), cn.releves(sans_titres))

    def test_puits_inflation_sans_fuite(self):
        d = Path(tempfile.mkdtemp()) / "n.csv"
        d.write_text("releve_le,periode,mesure,valeur\n2026-11-10,November 2026,variation_mensuelle:CPI,0.30\n"
                     "2026-11-12,November 2026,variation_mensuelle:CPI,0.33\n2026-11-12,November 2026,variation_mensuelle:Core CPI,0.28\n")
        ancien = ap.NOWCAST_INFLATION
        ap.NOWCAST_INFLATION = d
        try:
            b = asyncio.new_event_loop()
            try:
                r = b.run_until_complete(ap.nowcast_inflation("CPI", avant=date(2026, 11, 11)))
            finally:
                b.close()
            self.assertEqual([p["valeur"] for p in r["points"]], [0.30])
            b = asyncio.new_event_loop()
            try:
                r = b.run_until_complete(ap.nowcast_inflation("CPI"))
            finally:
                b.close()
            self.assertEqual([p["valeur"] for p in r["points"]], [0.30, 0.33])     # sans « Core CPI »
        finally:
            ap.NOWCAST_INFLATION = ancien

    def test_catalogue(self):
        self.assertIn("gdpnow", ap.CATALOGUE)
        self.assertIn("nowcast_inflation", ap.CATALOGUE)


if __name__ == "__main__":
    unittest.main()
