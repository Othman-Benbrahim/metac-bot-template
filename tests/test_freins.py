"""0.10.41 : freins du skill 0.7.72 dans le bot (score, λ_I appris, puissance)."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import alphabet_pipeline as ap  # noqa: E402
import apprentissage_lambda as al  # noqa: E402
import score_registre as sr  # noqa: E402


class Tests(unittest.TestCase):
    def test_freins(self):
        m = ap._moteur()
        self.assertLess(m.P["lambda"]["I"], 1)
        self.assertIn("I", al.CLASSES)
        n = al.compte_sources(m, "[2026-11 | 3 mois] CONTRAINTE@7[F]", "CRO@7")
        self.assertEqual(n["I"], 1)
        lignes = [{"question_id": "1", "bras": {"B": {"p": 0.3}, "C": {"p_C": 0.2, "etat": "[2026-11 | 3 mois] CONTRAINTE@7[F]",
                                                                        "evenement": "CRO@7 apparait"}}},
                  {"question_id": "2", "bras": {"B": {"p": 0.3}, "C": {"p_C": 0.4, "etat": "[2026-11 | 3 mois] CROISSANCE@7[F]",
                                                                        "evenement": "CTR@7 apparait"}}}]
        r = sr.freins(lignes, {"1": 0, "2": 1})
        self.assertEqual(r["avec_frein"]["n"], 1)
        self.assertGreater(r["avec_frein"]["gain_C_sur_B"], 0)     # le frein a fait gagner C sur une issue NON
        self.assertEqual(r["sans_frein"]["n"], 1)
        rows = [{"source": "bot", "f": 0.3, "y": 0, "n": {"F": 0, "M": 0, "f": 0, "I": 1}} for _ in range(12)]
        x = al.apprendre(rows)
        self.assertLess(x["lambda_appris"]["I"], m.P["lambda"]["I"])   # des NON avec frein : λ_I appris plus bas


if __name__ == "__main__":
    unittest.main()
