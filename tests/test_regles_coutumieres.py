"""0.10.371 : base des règles coutumières (validation)."""
import regles_coutumieres as rc


def test_base_valide():
    assert rc.valider() == []


def test_garde_fous():
    assert rc.valider([{"id": "x", "structure": "course", "echelle": {"axe": "taille"}, "statut": "source", "sources": []}])
    assert rc.valider([{"id": "y", "structure": "course", "echelle": {"axe": "taille"}, "statut": "absence",
                        "parametres": {"a": 1}, "aide": "z"}])
