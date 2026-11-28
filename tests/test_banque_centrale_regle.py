import datetime as dt

import banque_centrale_regle as bc


def test_reconnaitre_formes():
    assert bc.reconnaitre("No change in Fed interest rates after May 2025 meeting?")["barreaux"] == ("M",)
    assert bc.reconnaitre("Fed increases interest rates by 25+ bps after July 2025 meeting?")["barreaux"] == ("H25", "H50")
    assert bc.reconnaitre("Will the Fed decrease interest rates by 25 bps after the June 2026 meeting?")["barreaux"] == ("B25",)
    assert bc.reconnaitre("Will 8+ Fed rate cuts happen in 2025?") == {"type": "compte", "n": 8, "au_moins": True, "annee": 2025}
    assert bc.reconnaitre("Fed emergency rate cut in 2025?")["type"] == "urgence"
    assert bc.reconnaitre("Will Trump nominate Jerome Powell as the next Fed chair?") is None
    assert bc.reconnaitre("Bank of England decreases interest rates by 25 bps after March 2026 meeting?") is None


def test_echelle_somme_a_un():
    R, C = bc.charger()
    jeu = dt.date(2025, 5, 1)
    tot = sum(bc.probabilite(bc.reconnaitre(t), jeu, R, C) for t in (
        "No change in Fed interest rates after June 2025 meeting?",
        "Fed increases interest rates by 25+ bps after June 2025 meeting?",
        "Fed decreases interest rates by 50+ bps after June 2025 meeting?",
        "Fed decreases interest rates by 25 bps after June 2025 meeting?"))
    assert abs(tot - 1) < 1e-9


def test_sans_regard_vers_l_avant():
    R, C = bc.charger()
    f = bc.reconnaitre("Fed rate hike in 2026?")
    # la hausse de septembre 2026 n'est pas connue en juin 2026
    assert bc.probabilite(f, dt.date(2026, 6, 21), R, C) < 1
    assert bc.probabilite(f, dt.date(2026, 10, 1), R, C) == 1.0


def test_fred_complete_les_changements(tmp_path):
    f = tmp_path / "fred.csv"
    f.write_text("serie,jour,valeur\nDFEDTARU,2026-12-09,4.00\nDFEDTARU,2026-12-10,3.75\n", encoding="utf-8")
    R, C = bc.charger(fred=f)
    assert C[-1] == (dt.date(2026, 12, 10), -25, 3.75)


def test_melange_plafonne():
    assert bc.melanger(0.5, 0.01) >= 0.35


def test_abstention_hors_calendrier():
    """2026-11-28 : une fenêtre au-delà du calendrier officiel connu ne compte pas « zéro réunion ». Chaque titre est
    d'abord vérifié comme reconnu, pour que l'abstention vienne bien de la règle (relecture indépendante)."""
    import datetime as dt
    import banque_centrale_regle as b
    jeu = dt.date(2026, 11, 20)
    for t in ["Will 2+ Fed rate cuts happen in 2029?", "Will there be a Fed rate hike in 2029?",
              "Will the Fed raise the federal funds target range before March 1, 2029?",
              "Will the Fed announce an emergency rate cut in 2029?",
              "Will the Fed hold a cut-pause-cut sequence in 2029?",
              "No change in Fed interest rates after March 2029 meeting?"]:
        assert b.reconnaitre(t) is not None, t
        assert b.estimer(t, jeu) is None, t
    assert b.estimer("Will 2+ Fed rate cuts happen in 2027?", jeu) is not None


def test_urgence_exposition_annee_seule():
    import datetime as dt
    import banque_centrale_regle as b
    p26 = b.estimer("Will the Fed announce an emergency rate cut in 2027?", dt.date(2026, 11, 20))["p"]
    p27 = b.estimer("Will the Fed announce an emergency rate cut in 2027?", dt.date(2027, 1, 1))["p"]
    assert abs(p26 - p27) < 0.02      # même exposition : l'année 2027 seule
