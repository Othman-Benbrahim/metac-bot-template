import numpy as np

import placebo as pl


def test_specifique():
    rng = np.random.default_rng(1)
    sans = rng.uniform(0.3, 0.7, 200)
    objet = np.arange(200) < 60
    avec = sans - np.where(objet, 0.15, 0.0) + rng.normal(0, 0.02, 200)
    assert pl.placebo(avec, sans, objet)["lecture"].startswith("spécifique")


def test_generique():
    rng = np.random.default_rng(2)
    sans = rng.uniform(0.3, 0.7, 200)
    objet = np.arange(200) < 60
    avec = sans - 0.1 + rng.normal(0, 0.02, 200)
    assert pl.placebo(avec, sans, objet)["lecture"].startswith("générique")


def test_trop_peu():
    assert "indéterminé" in pl.placebo([0.1] * 6, [0.2] * 6, [True] * 3 + [False] * 3)["lecture"]
