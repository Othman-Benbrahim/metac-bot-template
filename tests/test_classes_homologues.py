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


def test_motifs_sans_faux_amis():
    """Le pronom « who » n'est pas l'OMS ; Google Trends et Metaculus ne sont pas des laboratoires d'IA."""
    assert ch.classe("Who will win the Royal Society science book prize?", 30) is None
    assert ch.classe("Will the WHO declare a PHEIC for H5N1 before 2027?", 30)["fiche"] == "epidemies"
    assert ch.classe('Will there be a new all-time peak in Google Trends for "power outage"?', 30) is None
    assert ch.classe("Will Metaculus add a meta discussion feature?", 30) is None
    assert ch.classe("Will Google release a chatbot in 2016?", 30)["fiche"] == "sciences-techniques"
    assert ch.classe("Will AlphaGo beat Lee Sedol in March 2016?", 30)["fiche"] == "sciences-techniques"
