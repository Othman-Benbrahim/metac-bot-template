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

    def test_pics_isoles(self):
        s = [1] * 90
        s[40] = 30                                   # pic isolé : ramené à la médiane
        self.assertEqual(ba.sans_pics_isoles(s)[40], 1.0)
        s[41] = 20                                   # pic confirmé par le lendemain : gardé
        self.assertEqual(ba.sans_pics_isoles(s)[40], 30.0)
        b = [1] * 89 + [30]                          # bord (J−1) : jamais touché
        self.assertEqual(ba.sans_pics_isoles(b)[-1], 30.0)
        self.assertLess(ba.sursaut([1] * 40 + [9] + [1] * 49), ba.sursaut([1] * 40 + [9] + [1] * 49, filtre=False))
        self.assertIsNone(ba.sursaut([0] * 40 + [9] + [0] * 49))      # seul jour d actualité, isolé : plus rien

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
        self.assertGreater(r["bic_ecart"], 2)              # rappel réel : le BIC le préfère
        x, rw = 0.0, []
        for i in range(400):
            x = x + 0.1 + random.gauss(0, 1)
            rw.append({"date": (d0 - timedelta(days=400 - i)).isoformat(), "valeur": x})
        self.assertLess(fb.b_ou(rw, 7, d0)["bic_ecart"], 2)  # marche avec dérive : B garde la main


class TendanceLarge(unittest.TestCase):
    def test_loo_rapide_identique(self):
        import banc_tendance_large as btl
        ls = [{"p_S": 0.4, "issue": i % 2, "tendance": (1.0 if i % 2 else -1.0) * (1 + i % 3)} for i in range(30)]
        p1, beta = btl.loo(ls, "p_S")
        p2 = ba.loo([dict(x, p_M=x["p_S"]) for x in ls], ba.ajuste_tendance, "tendance", ba.GRILLE_BETA)
        for a, b in zip(p1, p2):
            self.assertAlmostEqual(a, b)
        self.assertGreater(beta, 0)


class StructureArbre(unittest.TestCase):
    def test_k2_trouve_un_vrai_lien_et_pas_le_bruit(self):
        import random

        import banc_structure_arbre as bsa
        rnd = random.Random(3)
        d = []
        for _ in range(400):
            x = {c: rnd.randint(1, 4) for c in bsa.CLES}
            x["issue"] = int(rnd.random() < (0.9 if x["proportion"] >= 3 else 0.1))
            d.append(x)
        par = bsa.k2(d, list(bsa.CLES) + ["issue"])
        self.assertIn("proportion", par["issue"])
        self.assertEqual(len(bsa.aretes(par)) - len(par["issue"]), 0)   # aucune note liée à une autre (bruit pur)

    def test_bdeu_prefere_le_vide_sur_peu_de_donnees_bruitees(self):
        import random

        import banc_structure_arbre as bsa
        rnd = random.Random(1)
        d = [{**{c: rnd.randint(1, 4) for c in bsa.CLES}, "issue": rnd.randint(0, 1)} for _ in range(60)]
        self.assertEqual(bsa.k2(d, list(bsa.CLES) + ["issue"])["issue"], ())


class FiltreAzure(unittest.TestCase):
    def test_variantes(self):
        import banc_filtre_azure as bfa
        q = {"titre": "Will X happen?", "cloture": "2026-12-31", "criteres": "CRITERES-ICI"}
        rech = "a" * 5000 + "FIN-RECHERCHE"
        base = bfa.consigne("identique", q, rech, "2026-01-01")
        self.assertIn("MOT POUR MOT", base)
        s = bfa.consigne("sans_mot_pour_mot", q, rech, "2026-01-01")
        self.assertNotIn("MOT POUR MOT", s)
        self.assertNotIn("sera rejetée", s)
        self.assertNotIn("phrase exacte", s)
        self.assertNotIn("FIN-RECHERCHE", bfa.consigne("recherche_4000", q, rech, "2026-01-01"))
        self.assertNotIn("CRITERES-ICI", bfa.consigne("sans_criteres", q, rech, "2026-01-01"))
        self.assertTrue(bfa.est_refus(Exception("The response was filtered due to the prompt triggering Azure")))


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
