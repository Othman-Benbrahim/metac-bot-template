import competitions_regle as cpr


def test_favorite_garde_le_raisonnement_du_modele():
    e = cpr.estimer("Will Jannik Sinner win the 2027 Australian Open?", 0.35)
    assert e is not None
    # mélange plafonné : jamais plus de 15 points sous le raisonnement du modèle
    assert e["p"] >= 0.35 - 0.15 - 1e-9
    assert e["p_regle"] < 0.02
