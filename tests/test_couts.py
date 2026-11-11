"""Bot 0.10.33 : coûts par question et budget (registre/couts.jsonl)."""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import alphabet_bot as ab  # noqa: E402
import alphabet_pipeline as ap  # noqa: E402
import score_registre as sr  # noqa: E402


class Tests(unittest.TestCase):
    def test_couts_et_budget(self):
        reg = Path(tempfile.mkdtemp(prefix="registre-couts-"))
        ancien = ap.REGISTRE
        ap.REGISTRE = reg
        os.environ["ALPHABET_MODELES"] = json.dumps({"principal": "bedrock/global.anthropic.claude-sonnet-4-6"})
        try:
            lot = [SimpleNamespace(id_of_question=1, page_url="u1"), SimpleNamespace(id_of_question=2, page_url="u2"),
                   SimpleNamespace(id_of_question=3, page_url="u3")]
            rapports = [SimpleNamespace(price_estimate=0.8, minutes_taken=3.0), RuntimeError("échec"),
                        SimpleNamespace(price_estimate=0.7, minutes_taken=2.0)]
            self.assertAlmostEqual(ab.noter_couts("minibench", rapports, lot), 1.5)
            self.assertAlmostEqual(ab.depense_depuis(None), 1.5)
            self.assertAlmostEqual(ab.depense_depuis("2999-01-01"), 0.0)
            c = sr.couts(reg)
            self.assertEqual(c["par_modele"]["bedrock/global.anthropic.claude-sonnet-4-6"]["questions"], 2)
            self.assertAlmostEqual(c["total_usd"], 1.5)
        finally:
            ap.REGISTRE = ancien
            os.environ.pop("ALPHABET_MODELES", None)


if __name__ == "__main__":
    unittest.main()
