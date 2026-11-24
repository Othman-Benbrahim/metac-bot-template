import competitions_regle as c


def test_reconnaissance():
    assert c.n_concurrents("Will England win the 2026 FIFA World Cup?") == 48
    assert c.n_concurrents("Will Tottenham finish in 2nd place in the 2025-26 English Premier League?") is None
    assert c.n_concurrents("Will the Denver Nuggets win the NBA Western Conference Finals?") is None
    assert c.n_concurrents("Will Timothée Chalamet win Best Actor at the 98th Academy Awards?") == 5


def test_estimation():
    e = c.estimer("Will England win the 2026 FIFA World Cup?", 0.1)
    assert e["saillance"] == 2.0 and abs(e["p_regle"] - (1 - (47 / 48) ** 2)) < 1e-12 and abs(e["p"] - 0.1) <= 0.15
