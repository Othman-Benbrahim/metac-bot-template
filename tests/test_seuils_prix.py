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


def test_lire():
    q = sp.lire("Will Bitcoin reach $110,000 by December 31, 2025?")
    assert q == {"actif": "CBBTCUSD", "k": 110000.0, "type": "touche", "au_dessus": True}
    assert sp.lire("Will NVIDIA’s (NASDAQ Ticker: $NVDA) stock price close above $480 per share?")["actif"] == "NVDA"  # pas l'indice
    assert sp.estimer("Will Strategy (MSTR) close below $100 on Friday, November 27, 2026?", "2026-11-20", "2026-11-27") is None  # actions pas encore dans le bot
    assert sp.lire("Will Brent crude oil close above $100 on 27 November 2026?")["type"] == "date"


def test_estimer_et_fraicheur(monkeypatch):
    import math
    pts = [(f"2026-10-{d:02d}", 100 * math.exp(0.01 * ((-1) ** d))) for d in range(1, 32)] + \
          [(f"2026-11-{d:02d}", 100 * math.exp(0.01 * ((-1) ** d))) for d in range(1, 18)]
    monkeypatch.setattr(sp, "series", lambda: {"CBBTCUSD": pts})
    e = sp.estimer("Will Bitcoin close above $150 on December 31, 2026?", "2026-11-18", "2026-12-31")
    assert e and e["type"] == "date" and e["p"] < 0.05
    assert sp.estimer("Will Bitcoin close above $150 on December 31, 2026?", "2026-12-01", "2026-12-31") is None  # prix trop ancien


def test_echeance():
    assert sp.echeance("Will Bitcoin reach $110,000 by December 31, 2025?", "2025-03-02") == "2025-12-31"
    assert sp.echeance("Will bitcoin trade below $20,000 before 2023?", "2022-05-24") == "2022-12-31"
