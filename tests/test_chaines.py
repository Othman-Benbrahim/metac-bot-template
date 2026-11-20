"""0.10.388 : chaînes de valeur, matières reconnues, famille S&P Global Energy."""
import chaines
import collecte_rss as cr


def test_chaine_graphite_valide():
    assert chaines.valider() == []
    assert "graphite" in chaines.chaines()


def test_matieres():
    assert cr.MATIERES["graphite"].search("Graphite prices fall") and not cr.MATIERES["acier"].search("Steelers win")
    assert "sp_energie" not in cr.FLUX and "economie" in cr.FAMILLES_MATIERES     # 0.10.390 : 403 depuis GitHub
    assert len(cr.FLUX["matieres_presse"]) == 8 and "matieres_presse" in cr.FAMILLES_MATIERES   # 0.10.393


def test_collecte_matieres():
    import collecte_matieres as cm
    import collecte_fred as cf
    assert set(cm.PRODUITS) == {"250410", "250490", "380110"} and cm.MOIS.match("2026M10")
    assert "PCOPPUSDM" in cf.SERIES and "PURANUSDM" in cf.SERIES
