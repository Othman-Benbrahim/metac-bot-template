"""0.10.380 / 0.10.383 : test du journal (cadre + lecture), suivi séquentiel."""
import journal_cadre as tj


def test_commun():
    assert abs(tj.commun(0.2, 0.2) - 0.2) < 1e-9
    assert abs(tj.commun(0.9, 0.1) - 0.5) < 1e-9


def test_en_attente(capsys):
    assert tj.principal() == 0
    assert "en attente" in capsys.readouterr().out


def test_e_processus():
    alpha = 0.05 / 16
    # le commun gagne nettement à chaque question : la richesse doit atteindre 1/α (un gain faible ne suffit pas : puissance limitée)
    bon = tj.e_processus([-1.0] * 60, alpha)
    assert bon["atteint_a"] is not None and bon["richesse"] >= 1 / alpha
    # sous H0 (écarts alternés de moyenne nulle) : richesse qui ne s'envole pas
    nul = tj.e_processus([0.3, -0.3] * 50, alpha)
    assert nul["atteint_a"] is None and nul["richesse"] < 1 / alpha
    # le commun perd : la richesse ne monte pas
    assert tj.e_processus([0.2] * 50, alpha)["richesse"] <= 1.0


def test_alpha_journal():
    # 0.10.384 : échantillon à part, risque de 5 % ; un gain modéré et régulier atteint le seuil 20 en moins de 100 questions
    assert tj.ALPHA == 0.05
    assert tj.e_processus([-0.4] * 99, tj.ALPHA)["atteint_a"] is not None
