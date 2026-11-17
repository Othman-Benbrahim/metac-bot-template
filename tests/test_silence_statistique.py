"""0.10.209 : M15, silence statistique chinois (calendrier NBS prévu contre publications observées)."""
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

import collecte_calendrier_nbs as cn
import indicateurs_niche as ni

PAGE = '''<li><a href="https://www.stats.gov.cn/english/PressRelease/202611/t20261111_1965808.html">4.Consumer Price Index in October 2026</a><span>2026-11-10</span></li>
<li><a href="./202611/t20261113_1965821.html">3.Market Prices of Important Means of Production in Circulation</a></li>
<li><a href="https://www.stats.gov.cn/english/PressRelease/202611/t20261116_1965843.html">1.National Economy was Generally Stable</a></li>'''


class TestNBS(unittest.TestCase):
    def test_lire_page(self):
        xs = cn.lire_page(PAGE)
        self.assertEqual([(x["jour"], x["publication"]) for x in xs],
                         [("2026-11-11", "ipc"), ("2026-11-16", "economie_nationale")])

    def test_indicateur(self):
        with tempfile.TemporaryDirectory() as t:
            cal, obs = Path(t) / "c.csv", Path(t) / "o.csv"
            cal.write_text("publication,date_prevue\nipc,2026-11-09\nipp,2026-11-09\npmi,2026-10-31\n"
                           "profits_industriels,2026-10-27\n", encoding="utf-8")
            obs.write_text("jour,publication,titre,url\n2026-10-20,immobilier,x,u0\n2026-10-28,profits_industriels,x,u1\n"
                           "2026-11-11,ipc,x,u2\n2026-11-08,pmi,x,u3\n", encoding="utf-8")
            with mock.patch.multiple(ni, CALENDRIER_NBS=cal, PUBLICATIONS_NBS=obs):
                r = ni.silence_statistique("CN", date(2026, 11, 16))
                # ipc à temps (+2) ; profits à temps (+1) ; pmi en retard (+8) ; ipp absente
                self.assertEqual((r["a_temps"], r["retard"], r["absente"], r["valeur"]), (2, 1, 1, 2))
                self.assertFalse(ni.silence_statistique("FR", date(2026, 11, 16))["present"])
                # à la date du 2026-11-12, l'IPC (prévu le 9, tolérance 3) n'est pas encore jugeable
                r = ni.silence_statistique("CN", date(2026, 11, 12))
                self.assertNotIn("ipc 2026-11-09 (absente)", r.get("manquantes", []))

    def test_titre_profit_singulier(self):
        self.assertEqual(cn.publication("Profit of Industrial Enterprises above the Designated Size in 2025"),
                         "profits_industriels")

    def test_echeance_feries(self):
        f = {date(2026, 10, d) for d in range(1, 8)}
        self.assertEqual(ni.echeance_nbs(date(2026, 9, 30), 3, f), date(2026, 10, 10))
        self.assertEqual(ni.echeance_nbs(date(2026, 11, 9), 3, f), date(2026, 11, 12))


if __name__ == "__main__":
    unittest.main()
