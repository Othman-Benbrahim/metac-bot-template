import evenements_regle as e


def test_reconnaissance():
    assert e.reconnaitre("Will Saudi Arabia conduct a direct military strike against Iran before June 1, 2026?")["serie"] == "ucdp_dyade:SAU:IRN"
    assert e.reconnaitre("Will China invade Taiwan by September 30, 2026?") is None
    assert e.reconnaitre("Will France, UK, or Germany strike Iran by February 28?") is None
    assert e.reconnaitre("Will the United States launch another strike against Islamic State in Nigeria?") is None
    assert e.reconnaitre("Earthquake 7.0 or above by August 31?") is None
    assert e.reconnaitre("Will an earthquake of magnitude 6 or above hit Japan before May?")["serie"] == "seismes:m6"


def test_probabilite_et_garde():
    serie = [(f"{2024 + (i // 12)}-{i % 12 + 1:02d}-01", 1.0 if i % 4 == 0 else 0.0) for i in range(30)]
    pr = e.probabilite(serie, "mois", "2026-07-01", "2026-10-01")
    assert pr["k"] == 6 and pr["n"] == 24 and pr["m"] == 4 and 0 < pr["p_regle"] < 1
    assert abs(e.melanger(0.3, 0.3) - 0.3) < 1e-9
    assert e.melanger(0.1, 0.99) > 0.1
