import numpy as np

from mise_au_point import kalman_indicateurs_essai as ke


def test_crps_empirique_et_gaussien():
    rng = np.random.default_rng(0)
    pts = rng.normal(0, 1, 4000)
    assert abs(ke.crps_empirique(pts, 0.3) - ke.crps_gauss(0, 1, 0.3)) < 0.03
    assert ke.crps_empirique(np.array([1.0]), 1.0) == 0


def test_kalman_suit_une_tendance():
    y = [0.1 * t + np.sin(t) * 0.01 for t in range(80)]
    m, s = ke.prevision_kalman(y)
    assert abs(m - 8.0) < 0.2 and s > 0
