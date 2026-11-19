"""0.10.366 : type d'inconnu par compartiment (Smithson)."""
import inconnus as inc


def test_fichier_valide():
    assert inc.valider() == []


def test_absence_deduite_et_manuels():
    t = inc.table()
    assert "tabou" in t["humain:opinion_privee"]["types"]
    assert t["elections-amerique-latine:economie"]["types"] == ["confusion"]          # mesurée : pas d'absence ajoutée
    assert all("absence" in v["types"] for v in t.values() if not v["mesure"])
