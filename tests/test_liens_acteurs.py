"""0.10.387 : liens propres aux acteurs."""
import liens_acteurs as la


def test_valide():
    assert la.valider() == []
    assert any(l["temps"]["statut"] == "conjoncturel" for l in la.liens())
