from mise_au_point.lecture_mecanique import _MotifContexte


def test_party_exige_un_contexte_politique():
    m = _MotifContexte("party", ["political", "election", "Labour"])
    assert m.search("Will Elon Musk create a political party in 2025?")
    assert m.search("Will the party win the election?")
    assert not m.search("Will Taylor Swift throw a birthday party in 2026?")


def test_senat_americain_seulement():
    m = _MotifContexte("Senate", ["US", "Republican", "Democrats"])
    assert not m.search("Will AICO win the most seats in the 2026 Colombian Senate election?")
    assert m.search("Will Republicans keep the US Senate?")
