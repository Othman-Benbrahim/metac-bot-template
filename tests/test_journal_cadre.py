"""0.10.380 : test du journal (cadre + lecture), préenregistré."""
import journal_cadre as tj


def test_commun():
    assert abs(tj.commun(0.2, 0.2) - 0.2) < 1e-9
    p = tj.commun(0.9, 0.1)
    assert abs(p - 0.5) < 1e-9


def test_en_attente(capsys):
    assert tj.principal() == 0
    assert "en attente" in capsys.readouterr().out
