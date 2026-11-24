import escalade_regle as e


def test_classes():
    assert e.classe("Will China invade Taiwan by September 30, 2026?") == "lourd"
    assert e.classe("Will Saudi Arabia strike Iran by March 31?") == "leger"
    assert e.classe("Will the US and Iran agree to a ceasefire before May 2026?") is None
    assert e.classe("Will the United States launch another strike against Islamic State in Nigeria?") is None
    assert e.TAUX["lourd"] < e.TAUX["leger"]


def test_garde():
    r = e.estimer("Will China invade Taiwan by September 30, 2026?", 0.4)
    assert r["p"] < 0.4 and 0.4 - r["p"] <= 0.15 + 1e-9
