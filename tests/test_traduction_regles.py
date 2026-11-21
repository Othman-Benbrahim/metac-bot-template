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


def test_fed_decisions_et_traduction():
    dec = tr.decisions_connues("2026-03-01")
    assert dec[-1] == ("2026-01-28", 0.0) and ("2022-06-15", 0.75) in dec
    assert all(m < "2026-02-20" for m, _ in dec)                      # seulement les réunions visibles avant le jeu
    p = tr.p_fed("Will the Fed decrease interest rates by 25 bps after the April 2026 meeting?", "2026-03-01", "2026-04-30")
    q = tr.p_fed("Will there be no change in Fed interest rates after the April 2026 meeting?", "2026-03-01", "2026-04-30")
    assert 0 < p < 1 and 0 < q < 1 and p + q < 1
    assert tr.p_fed("Will the Fed Cut–Pause–Pause in the next three decisions (Dec–Jan–Mar)?", "2026-03-01", "2026-03-19") is None


def test_sondages(tmp_path, monkeypatch):
    import json
    f = tmp_path / "s.json"
    f.write_text(json.dumps({"questions": {"poly:1": {"statut": "ok", "colonne_sujet": "A",
        "moyennes": {"A": {"moyenne": 30}, "B": {"moyenne": 20}, "C": {"moyenne": 10}}}}}))
    monkeypatch.setattr(tr, "SONDAGES", f)
    tr._sondages.cache_clear()
    assert tr.p_sondages("poly:1", "Will A win the 2026 X election?", 10) > 0.9
    assert tr.p_sondages("poly:1", "Will A finish in second place in the 2026 X election?", 10) < 0.1
    assert tr.p_sondages("poly:1", "Will A win a majority of seats?", 10) is None
    assert tr.p_sondages("poly:2", "Will A win?", 10) is None
    tr._sondages.cache_clear()
