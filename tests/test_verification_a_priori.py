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
