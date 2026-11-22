import banc_accord_lecteur as bal

CLES = ("a", "b")


def test_kappa_pondere_bornes():
    assert bal.kappa_pondere([1, 2, 3, 4], [1, 2, 3, 4]) == 1.0
    assert bal.kappa_pondere([1, 2, 3, 4], [4, 3, 2, 1]) < 0
    assert bal.kappa_pondere([2, 2, 2], [2, 2, 2]) is None          # aucune variation : indéfini
    assert bal.kappa_pondere([], []) is None


def test_kappa_pondere_ecart_proche_penalise_moins():
    loin = bal.kappa_pondere([1, 2, 3, 4, 1, 4], [4, 2, 3, 1, 1, 4])
    pres = bal.kappa_pondere([1, 2, 3, 4, 1, 4], [2, 2, 3, 3, 1, 4])
    assert pres > loin


def test_resume_et_lecture():
    l = lambda n1, n2, nx, p1, p2: {"r1": {"notes": {"a": n1, "b": n1}, "p": p1}, "r2": {"notes": {"a": n2, "b": n2}, "p": p2},
                                    "x": {"notes": {"a": nx, "b": 2}}}
    ls = [l(1, 1, 1, .2, .25), l(2, 2, 3, .4, .4), l(3, 3, 3, .6, .8), l(4, 4, 2, .9, .85)]
    r = bal.resumer(ls, CLES)
    assert r["n_completes"] == 4
    assert r["stabilite_r1_r2"]["kappa_moyen"] == 1.0
    assert r["lecture"]["stabilite"] == "stable"
    assert r["probabilite_r1_r2"]["part_ecart_sup_0_10"] == 0.25
    assert r["part_des_2"]["x"]["b"] == 1.0
