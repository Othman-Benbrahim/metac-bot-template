import numpy as np

import verification_a_priori as va


def test_sd_conseille_analytique():
    X = np.ones((50, 4))                       # ‖x‖ = 2
    assert abs(va.sd_conseille(X, 0.5) - 0.5 / (0.6745 * 2)) < 1e-9


def test_alerte_si_a_priori_trop_large():
    X = np.ones((100, 6))
    r = va.simuler(X, np.full(100, 0.3), sd=1.0)
    assert r["alerte"] and r["decalage_median_logit"] > 0.5


def test_pas_d_alerte_avec_sd_conseille():
    X = np.ones((100, 6))
    sd = va.sd_conseille(X)
    r = va.simuler(X, np.full(100, 0.3), sd=sd * 0.95)
    assert not r["alerte"]


def test_indicateurs_nuls_ne_deplacent_rien():
    r = va.simuler(np.zeros((20, 3)), np.full(20, 0.4))
    assert r["decalage_median_logit"] == 0 and r["sd_conseille"] is None and not r["alerte"]


def test_taille_necessaire_et_ecart_detectable_coherents():
    n = va.taille_necessaire(0.2, 0.04)
    assert 150 < n < 170
    assert abs(va.ecart_detectable(0.2, n) - 0.04) < 0.001
    assert va.taille_necessaire(0.2, 0.02) > 3.9 * n         # écart moitié : quatre fois plus de questions


def test_puissance_bilan():
    r = va.puissance([0.1, -0.2, 0.3, 0.0, -0.1, 0.2])
    assert r["n"] == 6 and r["sigma_par_question"] > 0 and "0.005" in r["questions_necessaires"]


def test_blocs_chronologiques_sans_fuite():
    dates = [f"2026-01-{d:02d}" for d in range(1, 31)] * 2
    blocs = va.blocs_chronologiques(dates, k=5, min_apprentissage=10)
    assert blocs
    for appris, juge in blocs:
        assert max(dates[i] for i in appris) < min(dates[i] for i in juge)
