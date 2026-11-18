import math
import unittest

import profil_erreurs as pe


class TProfil(unittest.TestCase):
    def test_deux_cotes_et_decomposition(self):
        paires = [(0.9, 1), (0.2, 1), (0.1, 0), (0.6, 0), (0.1, 0)]
        r = pe.profil(paires)
        self.assertAlmostEqual(r["perte_venue_des_oui"] + r["perte_venue_des_non"], r["perte_log"], places=3)
        self.assertEqual((r["rates_oui_sous_30"], r["fausses_alertes_non_sur_50"]), (1, 1))
        # Murphy : Brier = fiabilité − résolution + incertitude quand chaque classe est homogène en p
        self.assertAlmostEqual(r["brier"], r["fiabilite_plus_bas_mieux"] - r["resolution_plus_haut_mieux"]
                               + r["incertitude"], places=3)

    def test_le_piege_du_seul_cote_oui(self):
        toujours_oui = [(0.9, y) for y in [1] + [0] * 5]
        prudent = [(0.2, 1)] + [(0.1, 0)] * 5
        a, b = pe.profil(toujours_oui), pe.profil(prudent)
        self.assertLess(a["perte_venue_des_oui"], b["perte_venue_des_oui"])   # vu du seul côté « oui », il gagne
        self.assertGreater(a["perte_log"], b["perte_log"])                    # au total, il perd

    def test_memes_questions(self):
        ls = [{"issue": 1, "a": 0.5, "b": 0.6}, {"issue": 0, "a": 0.3, "b": None}]
        r = pe.profils(ls, {"A": "a", "B": "b"})
        self.assertEqual((r["A"]["n"], r["B"]["n"]), (1, 1))


if __name__ == "__main__":
    unittest.main()


class TUnites(unittest.TestCase):
    def test_alerte_repetitions(self):
        ls = [{"question_id": f"metaculus:{q}:2026-0{j}-01", "issue": q % 2} for q in range(10) for j in (1, 2, 3)]
        r = pe.unites(ls)
        self.assertEqual((r["lignes"], r["questions_distinctes"], r["questions_oui_distinctes"]), (30, 10, 5))
        self.assertIsNotNone(r["alerte"])
        self.assertIsNone(pe.unites(ls[::3])["alerte"])

    def test_bancs_de_jugement_par_question(self):
        """Tout banc de jugement doit tirer ses intervalles PAR QUESTION (garde-fou contre l'erreur du 2026-11-18)."""
        import re
        from pathlib import Path
        for f in ("banc_jugement_alphabet.py", "banc_jugement_variantes.py", "banc_abstention.py",
                  "banc_gdelt_complement.py"):
            s = Path(f).read_text(encoding="utf-8")
            appels = re.findall(r"critere_ombre_b\((?:[^()]|\([^()]*\))*\)", s, re.S)
            self.assertTrue(appels, f)
            for a in appels:
                self.assertIn('bloc_par="question"', a, f)

    def test_examen_des_cartes_par_question(self):
        import psychometrie_alphabet as ps
        ls = [{"question_id": f"m:{q}:2026-0{j}-01", "issue": 1, "notes": {}} for q in range(4) for j in (1, 2)]
        self.assertEqual(len(ps.une_par_question(ls)), 4)
