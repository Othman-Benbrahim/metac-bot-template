"""Tests hors ligne des tests rétrospectifs et de la correction du biais de C (0.5.0)."""
import asyncio
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

import os as _os  # noqa: E402
import tempfile as _tempfile  # noqa: E402
# 0.7.4 : JAMAIS le vrai registre dans les tests (des lignes fictives y avaient été écrites puis publiées).
_os.environ.setdefault("ALPHABET_REGISTRE", _tempfile.mkdtemp(prefix="registre-test-"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
os.environ.setdefault("ALPHABET_REGISTRE", tempfile.mkdtemp(prefix="registre-"))
import alphabet_pipeline as ap  # noqa: E402
import test_pipeline as tp  # noqa: E402  (données fictives communes ; règle NB_VUES = 1, classe non figée)
import alphabet_retro as ar  # noqa: E402
import score_registre as sr  # noqa: E402


def mq(qid=501, issue="no"):
    return mock.Mock(id_of_question=qid, resolution_string=issue, page_url=f"https://www.metaculus.com/questions/{qid}/",
                     question_text="Will A and B cross an escalation threshold?", resolution_criteria="crit",
                     background_info="", fine_print="", open_time=datetime(2026, 10, 15, tzinfo=timezone.utc),
                     published_time=None, scheduled_resolution_time=datetime(2026, 11, 1, tzinfo=timezone.utc),
                     actual_resolution_time=None)


class TestsRetro(unittest.TestCase):
    def setUp(self):
        self.ancien = ap.REGISTRE
        ap.REGISTRE = Path(tempfile.mkdtemp(prefix="registre-retro-"))

    def tearDown(self):
        ap.REGISTRE = self.ancien

    def lancer(self, reponses, q=None):
        async def cherche(req, avant):
            self.assertLessEqual(avant, datetime(2026, 10, 15, tzinfo=timezone.utc))   # bornée à la date d'information
            return f"résultat daté pour {req}"

        async def histo(cles, aujourdhui):
            return []
        with mock.patch.object(ar, "chercher_avant", cherche), mock.patch.object(ar, "historique_avant", histo):
            return asyncio.run(ar.un_test(q or mq(), tp.LlmSimule(reponses), set()))

    def test_sonde_exclut_si_issue_connue(self):
        ligne = self.lancer([{"connait": True, "issue": "no"}])
        self.assertEqual(ligne["statut"], "exclue_connue")
        self.assertNotIn("p_C", ligne)

    def test_sonde_fausse_garde_la_question(self):
        lec = tp.lecture()
        for m in lec["mots"]:
            m["date_consultation"] = "2026-10-15"                      # lue à la date d'information simulée
        ligne = self.lancer([{"connait": True, "issue": "yes"}, tp.PLAN, tp.vue(0.2), lec])
        self.assertEqual(ligne["statut"], "estime")
        self.assertEqual(ligne["issue"], 0)
        self.assertEqual(ligne["date_information"], "2026-10-15")
        self.assertIsNotNone(ligne["p_C"])
        self.assertTrue((ap.REGISTRE / ligne["dossier_fichier"]).is_file())

    def test_question_deja_faite_ou_annulee(self):
        self.assertIsNone(asyncio.run(ar.un_test(mq(), tp.LlmSimule([]), {"501"})))
        self.assertIsNone(asyncio.run(ar.un_test(mq(issue="annulled"), tp.LlmSimule([]), set())))

    def test_score_retro_et_correction(self):
        for i in range(20):    # C surestime : 0,30 quand B dit 0,10 et que l'issue est OUI une fois sur dix
            ar.ecrire({"type": "retro", "question_id": str(i), "statut": "estime", "p_B": 0.1, "p_C": 0.3,
                       "issue": 1 if i % 10 == 0 else 0})
        s = sr.scorer_retro(ap.REGISTRE)
        self.assertEqual(s["n_chiffres"], 20)
        c = s["correction"]
        self.assertLess(c["decalage_logit"], 0)
        self.assertTrue(c["proposee"])
        self.assertTrue(sr.enregistrer_correction(ap.REGISTRE, s))
        corr = ap.correction_retro()
        self.assertLess(ap.corriger_C(0.3, corr), 0.3)
        r, _ = tp.lancer([tp.PLAN, tp.vue(0.2), tp.lecture()])          # la prévision réelle porte C corrigé…
        cbras = r.ligne["bras"]["C"]
        self.assertLess(cbras["p_C_corrige"], cbras["p_C"])
        self.assertEqual(r.bras_poste, "C")
        self.assertAlmostEqual(r.p_poste, ap.borner(cbras["p_C"]))       # … mais poste C non corrigé (règle L7)

    def test_pas_de_correction_sur_peu_de_questions(self):
        for i in range(5):
            ar.ecrire({"type": "retro", "question_id": str(i), "statut": "estime", "p_B": 0.1, "p_C": 0.3, "issue": 0})
        s = sr.scorer_retro(ap.REGISTRE)
        self.assertFalse(s["correction"]["proposee"])
        self.assertFalse(sr.enregistrer_correction(ap.REGISTRE, s))
        self.assertIsNone(ap.correction_retro())

    def test_sans_correction_rien(self):
        r, _ = tp.lancer([tp.PLAN, tp.vue(0.2), tp.lecture()])
        self.assertIsNone(r.ligne["bras"]["C"]["p_C_corrige"])
        self.assertIsNone(r.ligne["bras"]["C"]["correction"])


if __name__ == "__main__":
    unittest.main()
