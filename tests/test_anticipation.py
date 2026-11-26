import anticipation as an


def test_noms_propres_sans_mots_vides():
    N = an.noms("Senegal President Faye dissolves National Assembly; The Lavrov visit to Florida in December")
    assert "Lavrov" in " ".join(N) and "Florida" in N and "National Assembly" in N
    assert not any(n in ("The", "December") for n in N)


def test_liste_repere_une_montee():
    par = {"Senegal": {f"2026-11-{d:02d}": (1 if d < 24 else 12) for d in range(5, 27)},
           "Paris": {f"2026-11-{d:02d}": 10 for d in range(5, 27)}}
    L = an.liste("2026-11-26", par)
    assert L and L[0][0] == "Senegal"
