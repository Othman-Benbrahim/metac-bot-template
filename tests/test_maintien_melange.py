import maintien_regle as mr


def test_melange_plafonne():
    # quel que soit le chiffre des tables, la prévision reste à 15 points au plus du raisonnement du modèle
    for p_bot in (0.05, 0.4, 0.8):
        for p_regle in (0.005, 0.5, 0.99):
            p = mr.melanger(p_bot, p_regle)
            assert abs(p - p_bot) <= 0.15 + 1e-9
