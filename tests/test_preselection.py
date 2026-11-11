"""Bot 0.10.15 : présélection des cartes par plongement multilingue, en ombre."""
from __future__ import annotations

import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import alphabet_pipeline as ap  # noqa: E402
import preselection as ps  # noqa: E402
import score_registre as sr  # noqa: E402

Q = ap.Question(id=1, url="", titre="Will the ceasefire collapse?", contexte="", criteres="", precisions="",
                resolution=date(2027, 1, 1))
PLAN = {"candidats": ["POL@7", "CTR@7"], "contre_candidate": ["INC@7"], "evenement": {"carte": "SEU", "strate": 7}}


class Tests(unittest.TestCase):
    def test_preselection(self):
        cartes = ps.textes_cartes()
        self.assertEqual(len(cartes), 16)
        noms = sorted(cartes)
        favoris = ["POL", "CTR", "SEU", "RES"]   # le faux plongeur range ces cartes en tête, dans cet ordre

        def plongeur(textes):
            vec = [[1.0, 0.0]]
            for c in noms:
                i = favoris.index(c) if c in favoris else 10
                vec.append([1.0 / (1 + i), 1.0])
            return vec
        r = ps.preselectionner(Q, PLAN, plongeur)
        self.assertEqual(r["statut"], "calcule")
        self.assertEqual(r["cartes_du_plan"], ["CTR", "INC", "POL"])
        self.assertEqual(r["k"], 3)
        self.assertEqual(r["top_k"], ["POL", "CTR", "SEU"])
        self.assertEqual(r["communes"], ["CTR", "POL"])
        self.assertAlmostEqual(r["recouvrement"], 0.6667)
        self.assertEqual(r["rang_evenement"], 3)

        def casse(textes):
            raise ImportError("fastembed absent")
        self.assertEqual(ps.preselectionner(Q, PLAN, casse)["statut"], "indisponible")
        L = lambda y: {"bras": {"C": {"preselection": y}}}
        s = sr.preselection_ombre([L(r), L({"statut": "indisponible"}), {"bras": {"C": {}}}])
        self.assertEqual((s["questions"], s["calculees"], s["indisponibles"]), (2, 1, 1))
        self.assertAlmostEqual(s["recouvrement_moyen"], 0.6667)


if __name__ == "__main__":
    unittest.main()
