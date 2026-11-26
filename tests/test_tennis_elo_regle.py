import datetime as dt
import random
import tennis_elo_regle as t


def test_formes_hors_domaine():
    assert t.estimer("Will Jannik Sinner reach the final of the 2027 Australian Open?") is None
    assert t.estimer("Will Jannik Sinner win the 2027 Brisbane International?") is None


def test_tableau_et_favori():
    N = {f"Joueur {i}": ("2026-11-01", 2400 - 5 * i) for i in range(200)}
    p0 = t.probabilite("Joueur 0", N, 128, dt.date(2026, 11, 26), tirages=500)
    p50 = t.probabilite("Joueur 50", N, 128, dt.date(2026, 11, 26), tirages=500)
    assert p0 > p50 and 0 < p0 < 1
    P = t._tableau(sorted(N)[:96], {e: v for e, (_, v) in N.items()}, 96, random.Random(1))
    assert sum(x is None for x in P) == 32
