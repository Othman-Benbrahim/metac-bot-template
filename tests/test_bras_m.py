import asyncio
import json
import unittest
from datetime import date

import bras_m as bm


class TChoix(unittest.TestCase):
    M = {"statut": "estime", "p": 0.2, "p_depart": 0.15, "notes": {}}

    def test_remplace_a_et_b_vue(self):
        self.assertEqual(bm.choisir_m("A", 0.5, None, self.M), ("M", 0.2))
        self.assertEqual(bm.choisir_m("B", 0.4, "vue_modele", self.M), ("M", 0.2))

    def test_garde_les_taux_calcules_et_c(self):
        self.assertEqual(bm.choisir_m("B", 0.4, "compte_fenetres", self.M), ("B", 0.4))
        self.assertEqual(bm.choisir_m("B", 0.4, "fixee", self.M), ("B", 0.4))
        self.assertEqual(bm.choisir_m("C", 0.3, None, self.M), ("C", 0.3))

    def test_m_en_echec(self):
        self.assertEqual(bm.choisir_m("A", 0.5, None, {"statut": "erreur"}), ("A", 0.5))
        self.assertEqual(bm.choisir_m("A", 0.5, None, None), ("A", 0.5))


class TArret(unittest.TestCase):
    def test_attente_puis_verdicts(self):
        self.assertTrue(bm.regle_arret([(0.2, 0.3, 0)] * 99)["verdict"].startswith("en attente"))
        self.assertEqual(bm.regle_arret([(0.2, 0.3, 0)] * 100)["verdict"], "M maintenu")
        self.assertTrue(bm.regle_arret([(0.6, 0.3, 0)] * 100)["verdict"].startswith("ARRÊT"))
        self.assertEqual(bm.regle_arret([])["n"], 0)


class TPrevoir(unittest.TestCase):
    def test_deux_appels_et_cartes(self):
        appels = []

        async def llm(consigne):
            appels.append(consigne)
            if len(appels) == 1:
                return json.dumps({"notes": {k: {"note": 3, "pourquoi": "parce que"} for k in bm.bja.CLES}})
            return json.dumps({"p": 0.27, "raison": "ok"})
        bm.semblables = lambda *a: 0.18
        try:
            m = asyncio.run(bm.prevoir_m(llm, "Will X happen?", "", "", date(2027, 1, 1), "rien", date(2026, 11, 18)))
        finally:
            import importlib
            importlib.reload(bm)
        self.assertEqual((m["statut"], m["p"], m["p_depart"], len(m["notes"])), ("estime", 0.27, 0.18, 7))
        self.assertIn("0.180", bm.commentaire_m(0.4, m, "raisonnement A").replace(",", "."))
        self.assertIn("HIERARCHY", bm.texte_cartes(m))
        self.assertIn("NOT posted: 0.400", bm.commentaire_m(0.4, m, "r"))


if __name__ == "__main__":
    unittest.main()


class TPipeline(unittest.TestCase):
    def test_m_poste_et_journalise(self):
        import tempfile
        from pathlib import Path
        import alphabet_pipeline as ap

        async def faux_alphabet(*a, **k):
            return {"statut": "erreur", "motif": "test"}
        ancien, ancien_ecrire = ap.alphabet, ap.ecrire_registre
        lignes = []
        ap.alphabet, ap.ecrire_registre = faux_alphabet, lambda ligne, dossier=None: lignes.append(ligne)
        try:
            q = ap.Question(id="1", url="u", titre="Will X?", contexte="", criteres="", precisions="",
                            resolution=date(2027, 1, 1))
            m = {"statut": "estime", "p": 0.21, "p_depart": 0.15, "raison": "r",
                 "notes": {k: {"note": 2, "pourquoi": "p"} for k in bm.bja.CLES}}
            r = asyncio.run(ap.prevoir_binaire(q, "", 0.5, "raison A", None, None, False, matriochka=m))
        finally:
            ap.alphabet, ap.ecrire_registre = ancien, ancien_ecrire
        self.assertEqual((r.bras_poste, r.p_poste), ("M", 0.21))
        self.assertEqual(lignes[0]["bras_M"]["p"], 0.21)
        self.assertIn("Posted arm: M", r.commentaire)


class TReglesCode(unittest.TestCase):
    def test_recherche_vide(self):
        import trace_recherche as tr
        self.assertTrue(bm.recherche_vide(""))
        self.assertTrue(bm.recherche_vide(tr.AUCUN))
        self.assertTrue(bm.recherche_vide("(recherche indisponible : RuntimeError)"))
        self.assertTrue(bm.recherche_vide("[moteur : exa]\ncourt"))
        self.assertFalse(bm.recherche_vide("[moteur : exa]\n" + "Le comité a voté le texte en première lecture. " * 6))
        self.assertTrue(bm.recherche_vide("Polymarket gives 70%. " * 20))      # rien d'utile une fois la foule retirée

    def test_interrupteur(self):
        self.assertTrue(bm.m_coupe({"ALPHABET_POSTER_M": "non"}))
        self.assertFalse(bm.m_coupe({}))
        import os
        os.environ["ALPHABET_POSTER_M"] = "non"
        try:
            self.assertEqual(bm.choisir_m("A", 0.5, None, {"statut": "estime", "p": 0.2}), ("A", 0.5))
        finally:
            del os.environ["ALPHABET_POSTER_M"]

    def test_abstention(self):
        import os
        self.assertFalse(bm.abstention_active({}))
        os.environ["ALPHABET_ABSTENTION"] = "oui"
        ancien = bm.semblables
        bm.semblables = lambda *a: 0.12

        async def llm(c):
            raise AssertionError("le modèle ne doit pas être appelé")
        try:
            m = asyncio.run(bm.prevoir_m(llm, "Will X?", "", "", date(2027, 1, 1), "", date(2026, 11, 18)))
        finally:
            del os.environ["ALPHABET_ABSTENTION"]
            bm.semblables = ancien
        self.assertEqual((m["statut"], m["abstention"], m["p"]), ("estime", True, 0.12))
        self.assertIn("No usable research", bm.commentaire_m(0.4, m, "r"))


class TBot(unittest.TestCase):
    def test_disjoncteur_et_pause(self):
        import alphabet_bot as ab
        self.assertFalse(ab.disjoncter(4, 4))
        self.assertFalse(ab.disjoncter(10, 3))
        self.assertTrue(ab.disjoncter(10, 4))
        self.assertTrue(ab.en_pause({"ALPHABET_PAUSE": "oui"}))
        self.assertFalse(ab.en_pause({}))
