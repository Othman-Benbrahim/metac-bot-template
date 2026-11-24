import maintien_regle as m


def test_reconnaissance_et_abstentions():
    assert m.reconnaitre("Will Keir Starmer cease to be Prime Minister of the UK during 2026?")["sens"] == "depart"
    assert m.reconnaitre("Will Ali Khamenei remain Supreme Leader of Iran through December 31st, 2025?")["sens"] == "reste"
    assert m.reconnaitre("Trump removed via 25th Amendment in 2025?") is None
    assert m.reconnaitre("Will Viktor Orban remain Hungary's prime minister after the 2026 elections?") is None
    assert m.reconnaitre("Will Elon Musk step down from being Tesla CEO by the end of 2025?") is None


def test_probabilites():
    e = m.estimer("Will Pope Francis cease to be pope before the end of 2025?", "2025-03-16", "2025-12-31", 0.2,
                  verifier_elections=False)
    assert 0.2 < e["p_depart"] < 0.5 and abs(e["p"] - 0.2) <= 0.15 + 1e-9
    r = m.estimer("Will Ali Khamenei remain Supreme Leader of Iran through December 31st, 2025?", "2025-08-17",
                  "2025-12-31", 0.9, verifier_elections=False)
    assert r["p_regle"] == 1 - r["p_depart"]
