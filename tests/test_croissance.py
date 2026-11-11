"""Bot 0.10.19 : taux de base d'un seuil de NIVEAU sur une série en croissance (cas FYONET du 2026-11-11)."""
from __future__ import annotations

import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import alphabet_compte as ac  # noqa: E402
import alphabet_pipeline as ap  # noqa: E402
import score_registre as sr  # noqa: E402

FYONET = [1789, 1863, 2011, 2160, 2293, 2472, 2655, 2729, 2983, 3518, 3457, 3603, 3537, 3455, 3506, 3692, 3853, 3982,
          4109, 4447, 6554, 6822, 6273, 6135, 6752, 7010, 7396]


class Tests(unittest.TestCase):
    def test_fyonet(self):
        pts = [{"date": f"{2000 + i}-09-30", "valeur": x * 1000} for i, x in enumerate(FYONET)]
        r = ac.compter({"points": pts, "debut": "2000-01-01", "date_limite": "2026-11-10"}, 709, "atteint", 8050000, ">",
                       nature="niveau")
        self.assertEqual(r["methode"], "bootstrap_pas_relatifs")
        self.assertTrue(0.4 < r["frequence"] < 0.75)          # la tendance (≈ +4,5 %/an) atteint le seuil une fois sur deux

    def test_marche_aleatoire_inchangee(self):
        rnd = random.Random(3)
        v, x = [], 100.0
        for i in range(60):
            x += rnd.gauss(0, 1)
            v.append((None, x))
        self.assertFalse(ac.croissance(v))

    def test_bornee_et_retour(self):
        pts = [{"date": f"20{10 + i // 12:02d}-{i % 12 + 1:02d}-01", "valeur": 50 + (i % 5)} for i in range(60)]
        r = ac.compter({"points": pts, "debut": "2010-01-01", "date_limite": "2014-12-31"}, 90, "atteint", 101, ">",
                       nature="niveau", bornes=(0, 100))
        self.assertEqual(r["methode"], "hors_bornes")
        rnd = random.Random(5)
        x, pts = 5.0, []
        for i in range(240):
            x = 5 + 0.6 * (x - 5) + rnd.gauss(0, 0.2)
            pts.append({"date": f"{2000 + i // 12}-{i % 12 + 1:02d}-01", "valeur": x})
        r = ac.compter({"points": pts, "debut": "2000-01-01", "date_limite": "2019-12-31"}, 90, "atteint", 6.0, ">=",
                       nature="niveau")
        self.assertTrue(r["methode"].startswith("ar1"))

    def test_saison_et_volatilite(self):
        # 0.10.32 : série mensuelle saisonnière (pic en janvier) ; dernier point en octobre ; seuil atteignable
        # seulement au pic : avec la saison, la probabilité à 90 jours (jusqu'en janvier) dépasse celle à 30 jours.
        rnd = random.Random(2)
        pts, x = [], 100.0
        saison = [8, -2, -2, -1, -1, -1, -1, -1, -1, -1, 0, 3]          # pas moyens par mois (janvier = indice 0)
        for an in range(2014, 2026):
            for mo in range(1, 13):
                if an == 2025 and mo > 10:
                    break
                x += saison[mo - 1] + rnd.gauss(0, 0.5)
                pts.append({"date": f"{an}-{mo:02d}-15", "valeur": x})
        rel = {"points": pts, "debut": "2014-01-01", "date_limite": "2025-10-31"}
        r30 = ac.compter(rel, 30, "atteint", x + 6, ">=", nature="niveau")
        r90 = ac.compter(rel, 92, "atteint", x + 6, ">=", nature="niveau")
        self.assertIn("+saison", r90["methode"])
        self.assertLess(r30["frequence"], 0.1)
        self.assertGreater(r90["frequence"], 0.5)
        # volatilité groupée : une période agitée récente élargit les mouvements
        calme = [rnd.gauss(0, 0.2) for _ in range(150)]
        agite = [rnd.gauss(0, 2.0) for _ in range(30)]
        self.assertIsNotNone(ac._volatilite(calme + agite))
        self.assertGreater(ac._volatilite(calme + agite), 1.5)
        self.assertIsNone(ac._volatilite([rnd.gauss(0, 1) for _ in range(200)]))

    def test_discordance(self):
        d = ap.discordance(0.113, 0.5, "vue_modele")
        self.assertTrue(d["alarme"])
        self.assertFalse(ap.discordance(0.3, 0.5)["alarme"])
        L = lambda q, pb, pa: {"question_id": q, "bras": {"A": {"p": pa}, "B": {"p": pb, "methode": "vue_modele",
                                                                                 "discordance_A": ap.discordance(pb, pa, "vue_modele")}}}
        lignes = [L("1", 0.1, 0.6), L("2", 0.4, 0.5)]
        s = sr.discordances_B(lignes, {"1": 1, "2": 0})
        self.assertEqual((s["alarmes"], s["B_moins_A_avec_alarme"]["n"]), (1, 1))
        self.assertGreater(s["B_moins_A_avec_alarme"]["moyenne"], 0)
        self.assertEqual(sr.b_par_methode(lignes, {"1": 1, "2": 0})["vue_modele"]["n"], 2)


if __name__ == "__main__":
    unittest.main()
