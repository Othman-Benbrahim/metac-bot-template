import traduction_regles as tr


def test_poisson_et_orientation():
    p = tr.p_regle("sommets_etats_unis_russie", "Will Trump and Putin meet in person before October 1?", 365, "2026-01-01", "2026-12-31")
    assert abs(p - (1 - 2.718281828 ** (-8 / 26))) < 0.01
    q = tr.p_regle("sommets_etats_unis_russie", "Will Trump and Putin not meet?", 365, "2026-01-01", "2026-12-31")
    assert abs(p + q - 1) < 1e-9


def test_cas_particuliers():
    assert tr.p_regle("chefs_d_etat_sortie_irreguliere", "Will Viktor Orban remain PM after the 2026 election?", 30, "2026-03-01", "2026-04-01") is None
    assert tr.p_regle("royal_mail_hausses_tarifs", "Will the Royal Mail raise prices before September 10?", 30, "2026-08-10", "2026-09-10") < 0.2
    assert tr.p_regle("royal_mail_hausses_tarifs", "Will the Royal Mail raise prices before April 30?", 30, "2026-03-20", "2026-04-30") > 0.8
    assert tr.p_regle("calendriers_annonces_glissent", "Will Claude 5 be released by April 30?", 30, "2026-03-01", "2026-04-30") is None
    assert tr.p_regle("us_fed_calendrier", "Will the Fed cut rates?", 30, "2026-03-01", "2026-04-01") is None


def test_combiner():
    assert tr.combiner(0.3, []) == 0.3
    assert 0.3 < tr.combiner(0.3, [0.8]) < 0.8
