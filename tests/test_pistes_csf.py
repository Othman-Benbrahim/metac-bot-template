import os
import tempfile

os.environ["ALPHABET_REGISTRE"] = tempfile.mkdtemp(prefix="registre-test-")  # registre fictif avant tout import
os.environ["ALPHABET_TESTS"] = "1"

import unittest

import banc_attention_gdelt as ba
import banc_credibilite as bc
import gdelt_bq as gq


class Attention(unittest.TestCase):
    def test_serie_et_tendance(self):
        e = {"debut": "2026-01-01", "fin": "2026-03-31", "jours": {"2026-03-31": 10, "2026-01-05": 1}}
        s = ba.serie(e)
        self.assertEqual(len(s), 90)
        self.assertEqual(s[-1], 10)
        self.assertGreater(ba.tendance(s), 0)
        self.assertEqual(ba.tendance([0] * 90), 0.0)
        self.assertIsNone(ba.serie(dict(e, filtrable=False)))

    def test_sursaut(self):
        self.assertIsNone(ba.sursaut([0] * 90))
        self.assertLess(ba.sursaut([3] * 90), -0.9)              # régulier
        self.assertGreater(ba.sursaut([0] * 89 + [50]), 0.8)     # rafale

    def test_ajustement_garde_le_sens(self):
        for p in (0.05, 0.3, 0.7, 0.95):
            q = ba.ajuste_sursaut(p, 1.0, 0.6)
            self.assertEqual(p > 0.5, q > 0.5)
            self.assertLessEqual(abs(q - 0.5), abs(p - 0.5))
        self.assertEqual(ba.ajuste_sursaut(0.2, None, 1.0), 0.2)
        self.assertAlmostEqual(ba.ajuste_tendance(0.3, 0.0, 0.8), 0.3)

    def test_loo_sans_la_question(self):
        ls = [{"p_M": 0.5, "issue": i % 2, "tendance": 1.0 if i % 2 else -1.0} for i in range(20)]
        ps_ = ba.loo(ls, ba.ajuste_tendance, "tendance", ba.GRILLE_BETA)
        self.assertTrue(all(p > 0.5 for p, x in zip(ps_, ls) if x["issue"]))

    def test_sql_comptes(self):
        t = gq.sql_comptes()
        self.assertIn("GROUP BY qid, jour", t)
        self.assertIn("r_trouves = n_requis", t)
        self.assertEqual(gq.PLAFOND_REQUETE_GO["comptes"], 120.0)


class RetourMoyenne(unittest.TestCase):
    def test_ou_rappelle_un_niveau_haut(self):
        import random
        from datetime import date, timedelta

        import banc_forecastbench as fb
        random.seed(1)
        d0, x, pts = date(2026, 1, 1), 0.0, []
        for i in range(400):
            x = 0.8 * x + random.gauss(0, 1)
            pts.append({"date": (d0 - timedelta(days=400 - i)).isoformat(), "valeur": x})
        pts[-1]["valeur"] = 5.0
        r = fb.b_ou(pts, 7, d0)
        self.assertLess(r["p"], 0.1)
        self.assertTrue(0 <= r["phi"] <= 0.999)
        self.assertIsNone(fb.b_ou(pts[:10], 7, d0))


class Credibilite(unittest.TestCase):
    def test_categories(self):
        self.assertEqual(bc.categorie("Will the ECB cut rates before June?"), "banque_centrale")
        self.assertEqual(bc.categorie("Will the Fed cut rates?"), "banque_centrale")
        self.assertEqual(bc.categorie("Will Trump sign the bill?"), "executif")
        self.assertEqual(bc.categorie("Will OpenAI release GPT-6?"), "entreprise")
        self.assertEqual(bc.categorie("Will it rain in Paris?"), "aucun")
        self.assertEqual(bc.action("Will OpenAI announce GPT-6?"), "annonce")
        self.assertEqual(bc.action("Will OpenAI release GPT-6?"), "acte")

    def test_sans_fuite(self):
        xs = [{"source": "m", "id": str(i), "jeu": f"2026-0{1 + i // 3}-01", "resolue_le": f"2026-0{1 + i // 3}-15",
               "cloture": f"2026-0{1 + i // 3}-15", "titre": "Will the Fed cut rates?", "issue": 1, "p_R1": 0.5}
              for i in range(6)]
        bc.calculer_c(xs)
        self.assertEqual(xs[0]["n_cellule"], 0)                  # rien de clos avant le premier jeu
        self.assertEqual(xs[0]["p_C"], 0.5)
        self.assertEqual(xs[3]["n_cellule"], 3)
        self.assertGreater(xs[3]["p_C"], 0.5)


if __name__ == "__main__":
    unittest.main()
