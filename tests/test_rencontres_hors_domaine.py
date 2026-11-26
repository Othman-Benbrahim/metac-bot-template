from rencontres_regle import pays_du_titre


def test_appel_telephonique_hors_domaine():
    t = "Will Donald Trump and Vladimir Putin meet in person or talk on the phone before January 1, 2027?"
    assert pays_du_titre(t) is None


def test_rencontre_en_personne_reste_mesuree():
    t = "Will Donald Trump and Vladimir Putin meet in person before January 1, 2027?"
    assert pays_du_titre(t) is not None
