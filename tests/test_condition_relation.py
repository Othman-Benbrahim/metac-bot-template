"""2026-11-25 : champ facultatif « condition » des relations (necessaire, suffisante_partielle)."""
import ecosystemes as e


def test_condition_valide_et_inconnue():
    base = {"de": "a", "vers": "b", "effet": "+"}
    assert not any("condition" in x for x in e.cles_inconnues({"relations": [dict(base, condition="necessaire")]}))
    err = e.cles_inconnues({"relations": [dict(base, condition="peut-etre")]})
    assert any("condition inconnue" in x for x in err)
