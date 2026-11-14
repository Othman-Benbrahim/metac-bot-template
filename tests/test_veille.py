"""Veille d'articles : mots-clés, notation, requête arXiv, lecture d'Atom et de DAIR.AI (sans réseau)."""
from __future__ import annotations

import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import veille_articles as v  # noqa: E402

ATOM = b"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
<entry><id>http://arxiv.org/abs/2611.01234v2</id><published>2026-11-05T10:00:00Z</published>
<title>Judgmental Forecasting with
 Language Models</title><summary>We study base rates and the Brier score.</summary></entry>
<entry><id>http://arxiv.org/abs/2611.09999v1</id><published>2026-11-06T10:00:00Z</published>
<title>A Faster Transformer</title><summary>Throughput improves.</summary></entry>
</feed>"""

DAIR = """## Top AI Papers of the Week (November 2 - November 8) - 2026
| **Paper**  | **Links** |
| ------------- | ------------- |
| 1) **Reliability without Validity** - An LLM-as-a-judge study. <br>● Agreement is high. | [Paper](https://arxiv.org/abs/2606.19544), [Tweet](https://x.com/a) |
| 2) **Context Compaction** - Long context. | [Paper](https://academy.dair.ai/papers/long-2611.05306) |

---

## Top AI Papers of the Week (October 26 - November 1) - 2026
| 1) **Old** - old. | [Paper](https://arxiv.org/abs/2610.00001) |
"""


class Tests(unittest.TestCase):
    def test_veille(self):
        mots = v.lire_mots()
        self.assertIn("Brier score", mots["fort"])
        self.assertIn("forecast*", mots["faible"])
        self.assertNotIn("reasoning", mots["faible"])
        self.assertTrue(v.motif("forecast*").search("Forecasting"))
        self.assertTrue(v.motif("LLM-as-a-judge").search("LLM as a judge"))
        self.assertFalse(v.motif("news").search("newsletter"))
        s, f, fa = v.noter("Nothing here.", mots, "Forecasting Science")
        self.assertEqual((s, f), (2, []))                     # faible dans le titre : 2 points, pas retenu seul
        arts = v.parser_atom(ATOM)
        self.assertEqual(arts[0]["id"], "arxiv:2611.01234")
        self.assertEqual(arts[0]["titre"], "Judgmental Forecasting with Language Models")
        semaine, d = v.parser_dair(DAIR)
        self.assertIn("November 2", semaine)
        self.assertEqual([x["id"] for x in d], ["arxiv:2606.19544", "arxiv:2611.05306"])
        r = v.trier(arts + d, mots, {"arxiv:2606.19544"}, 10)
        self.assertEqual([x["id"] for x in r], ["arxiv:2611.01234"])   # déjà vu écarté, bruit écarté
        q = v.requete_arxiv(["judgmental forecast*", "Metaculus", "e-value*"], date(2026, 11, 3), date(2026, 11, 11))
        self.assertIn("(abs:judgmental AND abs:forecast)", q)
        self.assertIn('abs:"e-value"', q)
        self.assertIn("submittedDate:[202611030000 TO 202611112359]", q)
        self.assertIn("Rien de retenu", v.rediger([], "", ["arXiv (x)"], 8))


class Sources14Nov(unittest.TestCase):
    def test_github_et_zenodo(self):
        import veille_articles as va
        g = va.parser_github({"items": [{"full_name": "a/forecastbench-market-blend", "html_url": "https://github.com/a/b",
                                         "description": "Does blending an LLM forecast improve Brier score?",
                                         "topics": ["forecasting"], "created_at": "2026-11-03T15:42:19Z",
                                         "stargazers_count": 2}]})
        self.assertEqual(g[0]["id"], "github:a/forecastbench-market-blend")
        self.assertIn("forecasting", g[0]["resume"])
        z = va.parser_zenodo({"hits": {"hits": [{"id": 19762753, "links": {"self_html": "https://zenodo.org/records/19762753"},
                                                 "metadata": {"title": "Calibration benchmark", "description": "<p>Brier score of LLM forecasts</p>",
                                                              "publication_date": "2026-04-25", "resource_type": {"title": "Dataset"}}}]}})
        self.assertEqual(z[0]["resume"], "Brier score of LLM forecasts")
        self.assertEqual(z[0]["source"], "Zenodo · Dataset")
        mots = va.lire_mots()
        self.assertTrue(va.retenu(va.noter(g[0]["resume"], mots, g[0]["titre"])[0]))
        self.assertIn("evaluation harness", mots["fort"])


if __name__ == "__main__":
    unittest.main()
