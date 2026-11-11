"""Bot 0.10.35 : relecteur de fidélité du plan, en ombre."""
from __future__ import annotations

import asyncio
import json
import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import alphabet_pipeline as ap  # noqa: E402
import score_registre as sr  # noqa: E402

Q = ap.Question(id="7", url="", titre="Will the ceasefire collapse before March?", contexte="",
                criteres="Resolves yes if hostilities resume.", precisions="", resolution=date(2027, 3, 1))
PLAN = {"evenement": {"carte": "SEU", "strate": 7, "type": "apparait"}, "semantique": "au-moins-une-fois",
        "candidats": ["POL@7"], "pourquoi": "RAISONNEMENT SECRET DU PLANIFICATEUR"}


class Tests(unittest.TestCase):
    def test_relecture(self):
        vu = {}

        async def llm(c):
            vu["c"] = c
            return json.dumps({"fidele": "partiel", "ecarts": [{"type": "evenement_plus_facile", "motif": "m"}]})
        r = asyncio.run(ap.relire_fidelite(Q, PLAN, 110, llm))
        self.assertEqual((r["statut"], r["fidele"], r["ecarts"][0]["type"]), ("relu", "partiel", "evenement_plus_facile"))
        self.assertNotIn("RAISONNEMENT SECRET", vu["c"])                     # aveugle au raisonnement du planificateur
        self.assertNotIn("POL@7", vu["c"])                                  # ni aux candidates
        self.assertIn("SEUIL", vu["c"])

        async def casse(c):
            raise RuntimeError("panne")
        self.assertEqual(asyncio.run(ap.relire_fidelite(Q, PLAN, 110, casse))["statut"], "erreur")
        L = {"question_id": "7", "bras": {"C": {"p_C": 0.3, "fidelite_plan": r}}}
        s = sr.fidelite_plan([L], {"7": 1})
        self.assertEqual((s["relus"], s["verdicts"], s["perte_C_selon_verdict"]["partiel"]["n"]), (1, {"partiel": 1}, 1))


if __name__ == "__main__":
    unittest.main()
