import carte_robot as cb
import couverture_regles as cr


def test_rattachements_types():
    cat = cr.catalogue()
    r = lambda t: cb.rattacher(t, cat)
    assert "us_fed_calendrier" in r("Will the Fed decrease interest rates by 25 bps after the June 2026 meeting?")
    assert r("Will Iran participate in the 2026 FIFA World Cup?") == []
    assert "coupe_du_monde_vainqueurs_hotes" in r("Will France win the 2026 FIFA World Cup?")
    assert "presidentielles_mode_de_scrutin" not in r("Will Haiti hold the first round of its presidential election before September 1, 2026?")
    assert "us_erreur_sondages_par_echelle" not in r("Will Daniel Vilela win the Governor of Goiás election?")
    assert "calendriers_annonces_glissent" not in r("Will the United States launch an attack against JNIM in Mali during August 2026?")
    assert "sondages_erreur_comparee" not in r("Will Oh Se-hoon win the 2026 Seoul Mayoral Election")


def test_reproductible():
    a, b = cb.carte("banc_m"), cb.carte("banc_m")
    assert a == b and a["couvertes"] > 30
