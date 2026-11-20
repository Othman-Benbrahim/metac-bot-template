"""Seuils de prix (0.10.398) : formules log-normales."""
import seuils_prix as sp


def test_a_la_date_symetrique():
    assert abs(sp.p_a_la_date(100, 100, 0.5, 0.1) - 0.5) < 1e-9
    assert sp.p_a_la_date(100, 120, 0.5, 0.1) < 0.5 < sp.p_a_la_date(100, 80, 0.5, 0.1)


def test_toucher_vaut_environ_deux_fois():
    p_date = sp.p_a_la_date(100, 130, 0.6, 0.05)
    p_touche = sp.p_atteint_avant(100, 130, 0.6, 0.05)
    assert abs(p_touche - 2 * p_date) < 1e-9


def test_actif():
    assert sp.actif("Will Bitcoin reach $110,000 by December 31, 2025?") == "CBBTCUSD"
    assert sp.actif("Will the S&P 500 close above 6000?") == "SP500"
