"""Puits de données (2026-11-27)."""
from datetime import date

import puits


def test_ajouter_et_chercher(tmp_path):
    n = puits.ajouter([
        {"jour": "2026-11-20", "lien": "https://www.reuters.com/a", "titre": "Ukraine and Russia agree ceasefire talks",
         "famille": "monde", "pays": {"UA", "RU"}, "noms": ["Zelensky", "Putin"]},
        {"jour": "2026-11-25", "lien": "https://apnews.com/b", "titre": "Fed holds rates steady", "famille": "economie"},
        {"jour": "2026-12-05", "lien": "https://x.org/c", "titre": "Ceasefire collapses in Ukraine", "famille": "monde"},
        {"jour": "2026-11-21", "lien": "", "titre": "sans lien"},
    ], tmp_path)
    assert n == 3
    r = puits.chercher("Ukraine ceasefire Putin", date(2026, 11, 27), dossier=tmp_path)
    assert [x["d"] for x in r] == ["reuters.com"]            # l'article du 5 décembre est après la date : exclu
    assert "texte" not in r[0] and r[0]["u"] == "https://www.reuters.com/a"
