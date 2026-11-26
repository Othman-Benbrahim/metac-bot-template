import banc_duel_tennis as bd


def test_arbre_et_proba_exacte():
    ms = [{"round": "SF", "winner_name": "A", "loser_name": "B"}, {"round": "SF", "winner_name": "C", "loser_name": "D"},
          {"round": "F", "winner_name": "A", "loser_name": "C"}]
    T = bd.arbre(ms)
    assert sorted(bd.joueurs(T)) == ["A", "B", "C", "D"]
    p = bd.proba_titre(T, lambda x, y: 0.5)
    assert abs(sum(p.values()) - 1) < 1e-9 and abs(p["A"] - 0.25) < 1e-9


def test_ajustement_retrouve_le_sens():
    X = [(1.0, 0.0)] * 30 + [(-1.0, 0.0)] * 30
    Y = [1] * 25 + [0] * 5 + [0] * 25 + [1] * 5
    a, b = bd.ajuster(X, Y)
    assert a > 1
