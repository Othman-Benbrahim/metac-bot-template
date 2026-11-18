import unittest
from datetime import datetime, timedelta, timezone

import planificateur as pl

UTC = timezone.utc


class T(unittest.TestCase):
    def test_nuit(self):
        self.assertTrue(pl.de_nuit(datetime(2026, 11, 18, 22, 0, tzinfo=UTC)))
        self.assertTrue(pl.de_nuit(datetime(2026, 11, 18, 3, 0, tzinfo=UTC)))
        self.assertFalse(pl.de_nuit(datetime(2026, 11, 18, 6, 0, tzinfo=UTC)))
        self.assertFalse(pl.de_nuit(datetime(2026, 11, 18, 12, 0, tzinfo=UTC)))

    def test_dues(self):
        t = datetime(2026, 11, 18, 1, 0, tzinfo=UTC)          # mercredi, après minuit
        p = {f: [{"cree": t - timedelta(hours=20), "conclusion": "success"}] for f, _ in pl.COLLECTES}
        p["collecte_gdelt.yaml"] = [{"cree": t - timedelta(hours=3), "conclusion": "success"}]          # fait
        p["collecte_ooni.yaml"] = [{"cree": t - timedelta(hours=1), "conclusion": "failure"}]           # tentative récente
        p["collecte_radar.yaml"] = [{"cree": t - timedelta(minutes=5), "conclusion": None}]             # en cours
        p["collecte_rss.yaml"] = []                                                                     # jamais : premier
        d = pl.dues(p, t, bancs_actifs=True)
        self.assertEqual(d[0], "collecte_rss.yaml")
        for f in ("collecte_gdelt.yaml", "collecte_ooni.yaml", "collecte_radar.yaml", "veille_articles.yaml"):
            self.assertNotIn(f, d)
        self.assertIn("collecte_avions_etat.yaml", d)
        avant_minuit = datetime(2026, 11, 17, 22, 0, tzinfo=UTC)
        self.assertNotIn("collecte_avions_etat.yaml", pl.dues({}, avant_minuit, False))
        samedi = datetime(2026, 11, 21, 1, 0, tzinfo=UTC)
        self.assertNotIn("collecte_nowcast_inflation.yaml", pl.dues({}, samedi, False))


if __name__ == "__main__":
    unittest.main()
