"""0.10.385 : classes homologues tirées des fiches."""
import classes_homologues as ch


def test_acteurs_lus_dans_les_fiches():
    a = {x["acteur"][:25]: x for x in ch.acteurs()}
    p = a["le président en personne "]
    assert p["organisation"] == "personne" and p["vitesse"] == "jours" and p["vitesse_jours"] == 3


def test_classe():
    k = ch.classe("Will Trump meet Putin in person before 2026-03-01?", 30)
    assert k["fiche"] == "politique-americaine" and k["rapport"] == "large"     # Trump nommé en premier
    assert ch.classe("Will the Senate pass the bill before July?", 30)["rapport"] == "courte"      # chambre : vitesse en mois
    assert ch.classe("Will it rain in Paris tomorrow?", 1) is None
