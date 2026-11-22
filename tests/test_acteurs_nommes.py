import acteurs_nommes as an


def test_acteurs_nommes_valides():
    assert an.valider() == []


def test_niveaux_distance_dans_le_graphe():
    d = {"liens": [{"de": "a", "vers": "b", "relation": "allie"}, {"de": "b", "vers": "c", "relation": "nomme"},
                   {"de": "c", "vers": "d", "relation": "finance"}, {"de": "d", "vers": "e", "relation": "associe"},
                   {"de": "a", "vers": "x:y", "relation": "gouverne"}]}
    assert an.niveaux(d, "a") == {"b": 1, "c": 2, "d": 3}          # e à 4 pas : hors des trois niveaux ; x:y est la population


def test_lien_sans_source_refuse():
    d = {"acteurs": [{"id": "a", "nom": "A", "sorte": "dirigeant", "role": "r", "depuis": "2020", "cycle": "c",
                      "compartiments": ["humain:opinion_publique"], "sources": [{"url": "https://x", "lecture": "lu"}]}],
         "liens": [{"id": "l", "de": "a", "vers": "humain:opinion_publique", "relation": "informe", "domaine": "d",
                    "temps": {"statut": "structurel"}, "sources": []}]}
    assert any("aucune source" in e for e in an.valider(d))
