"""0.10.388 : chaînes de valeur, matières reconnues, famille S&P Global Energy."""
import chaines
import collecte_rss as cr


def test_chaine_graphite_valide():
    assert chaines.valider() == []
    assert "graphite" in chaines.chaines()


def test_matieres():
    assert cr.MATIERES["graphite"].search("Graphite prices fall") and not cr.MATIERES["acier"].search("Steelers win")
    assert len(cr.FLUX["sp_energie"]) == 14 and "sp_energie" in cr.DEDOUBLONNER
