"""0.10.179 : calendrier électoral Wikidata et indicateur."""
import os
import tempfile
import unittest
from datetime import date
from pathlib import Path

os.environ["ALPHABET_REGISTRE"] = tempfile.mkdtemp(prefix="registre-")
import collecte_elections as ce
import indicateurs_niche as ni


class TestElections(unittest.TestCase):
    def test_lignes(self):
        corps = {"results": {"bindings": [
            {"e": {"value": "http://www.wikidata.org/entity/Q1"}, "eLabel": {"value": "2026 X election"},
             "date": {"value": "2026-10-05T00:00:00Z"}, "iso": {"value": "br"}, "type": {"value": "election"}},
            {"e": {"value": "http://www.wikidata.org/entity/Q2"}, "date": {"value": "2026"}, "iso": {"value": "FR"}}]}}
        self.assertEqual(ce.lignes(corps), [{"qid": "Q1", "pays": "BR", "date": "2026-10-05", "type": "election",
                                             "nom": "2026 X election"}])

    def test_indicateur(self):
        d = Path(tempfile.mkdtemp())
        ancien = ni.ELECTIONS
        ni.ELECTIONS = d / "e.csv"
        try:
            ni.ELECTIONS.write_text("qid,pays,date,type,nom\nQ1,BR,2026-09-20,election,a\nQ2,BR,2026-10-20,election,b\n"
                                    "Q3,BR,2026-12-20,election,c\n")
            m = ni.elections("BR", date(2026, 10, 1))
            self.assertEqual((m["valeur"], m["apres_30j"]), (1, 1))
        finally:
            ni.ELECTIONS = ancien


if __name__ == "__main__":
    unittest.main()
