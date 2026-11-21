from mise_au_point import pit_fourchettes as pf


def test_rang_bornes_et_milieu():
    pool = list(range(10))
    assert 0 < pf.rang(pool, -5) < 0.1 and 0.9 < pf.rang(pool, 50) < 1
    assert abs(pf.rang(pool, 4.5) - 0.5) < 1e-9


def test_resumer_detecte_trop_etroit():
    us = [0.01] * 30 + [0.99] * 30 + [0.5] * 40
    assert "trop étroites" in pf.resumer(us)["lecture"]
    us = [i / 1000 + 0.0005 for i in range(1000)]
    assert pf.resumer(us)["lecture"] == "pas d'écart net à l'uniforme"
