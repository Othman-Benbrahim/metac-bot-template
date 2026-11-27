"""0.10.513 : porte de compatibilité famille de situation × brique (familles_situation.py)."""
import familles_situation as fs


def test_nobel_bloque_pour_autres_accords():
    ok, fam = fs.compatible("autres_accords", "Will Elon Musk win the Nobel Peace Prize in 2026?")
    assert not ok and "distinction_classement" in fam


def test_nobel_permis_pour_un_parmi_n():
    assert fs.compatible("competitions", "Will Elon Musk win the Nobel Peace Prize in 2026?")[0]


def test_rencontre_permise():
    assert fs.compatible("rencontres", "Will Donald Trump and Vladimir Putin meet in person before 2027?")[0]


def test_question_sans_famille_permise():
    ok, fam = fs.compatible("autres_accords", "Will GB News be broadcasting in 2025?")
    assert ok and fam == []


def test_brique_inconnue_permise():
    assert fs.compatible("brique_inexistante", "Will Elon Musk win the Nobel Peace Prize in 2026?")[0]


def test_prix_permis():
    assert fs.compatible("prix", "Will Strategy (MSTR) close below $100 on Friday, November 27, 2026?")[0]


def test_escalade_permise():
    assert fs.compatible("escalade", "Will Israel strike Iran's nuclear facilities before 2027?")[0]


def test_nobel_route_vers_un_parmi_n():
    import competitions_regle as c
    e = c.estimer("Will Elon Musk win the Nobel Peace Prize in 2026?", 0.10)
    assert e is not None and e["n"] == 287 and e["saillance"] == 1.0 and e["p"] < 0.10
