"""0.10.38 : provenance des F « independantes », vérifiée hors du modèle."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import alphabet_pipeline as ap  # noqa: E402
import alphabet_provenance as pv  # noqa: E402
import score_registre as sr  # noqa: E402

TEXTES = """[1] (situation, SEU) « budget »
[2026-11-01] CBO outlook — https://www.cbo.gov/publication/62105
extrait
[2026-11-02] OMB budget — https://whitehouse.gov/omb/budget-2027/?utm=x
[2026-11-03] Relais — https://www.cbo.gov/other-page
[2026-11-03] BBC — https://www.bbc.co.uk/news/1
[2026-11-03] Guardian — https://www.theguardian.co.uk/a"""


def mot(urls, corr="independantes", i="F"):
    return {"carte": "SEU", "strate": 7, "intensite": i, "corroboration": corr, "source_urls": urls}


class Tests(unittest.TestCase):
    def test_provenance(self):
        self.assertEqual(pv.domaine("https://news.bbc.co.uk/x"), "bbc.co.uk")
        self.assertEqual(pv.domaine("https://www.cbo.gov/a"), "cbo.gov")
        self.assertEqual(pv.normaliser("https://WWW.cbo.gov/publication/62105/"), "cbo.gov/publication/62105")
        d = {"mots": [mot(["https://cbo.gov/publication/62105", "https://whitehouse.gov/omb/budget-2027"]),
                      mot(["https://www.cbo.gov/publication/62105", "https://www.cbo.gov/other-page"]),
                      mot(["https://www.cbo.gov/publication/62105", "https://reuters.com/invente"]),
                      mot("https://www.bbc.co.uk/news/1"),
                      mot(None),
                      mot(["https://www.bbc.co.uk/news/1", "https://www.theguardian.co.uk/a"]),
                      mot(None, corr="unique"), mot(None, i="f")]}
        r = pv.provenance_F(d, TEXTES)
        self.assertEqual([x["statut"] for x in r["details"]],
                         ["verifiee", "meme_domaine", "url_hors_resultats", "une_seule_url", "sans_urls", "verifiee"])
        self.assertEqual(r["F_independantes"], 6)
        self.assertFalse(r["toutes_verifiees"])
        self.assertIsNone(pv.provenance_F({"mots": [mot(None, corr="unique")]}, TEXTES))
        self.assertIn("source_urls", ap.regles_dossier())
        lignes = [{"question_id": 1, "bras": {"C": {"p_C": 0.8, "provenance_F": r}}},
                  {"question_id": 2, "bras": {"C": {"p_C": 0.3, "provenance_F": pv.provenance_F(
                      {"mots": [d["mots"][0]]}, TEXTES)}}}]
        s = sr.provenance_F(lignes, {1: 0, 2: 0})
        self.assertEqual(s["F_par_statut"]["verifiee"], 3)
        self.assertEqual(set(s["perte_C"]), {"toutes_verifiees", "au_moins_une_non_verifiee"})


if __name__ == "__main__":
    unittest.main()
