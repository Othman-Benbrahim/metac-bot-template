import banc_fidelite as bf


def test_formes():
    assert bf.formes("1,234") == {"1234", "1.234"}
    assert bf.formes("3,5") == {"3.5"}
    assert bf.formes("3.50") == {"3.5"}
    assert bf.formes("1 200 000") == {"1200000"}
    assert bf.formes("2026") == {"2026"}


def test_jetons_date_pointee():
    assert bf.jetons("le 12.10.2026") == ["12", "10", "2026"]
    assert bf.jetons("1.200.000 habitants") == ["1.200.000"]


def test_controle_trouve_et_absent():
    corpus = "Inflation was 3.5% in September 2026, unemployment 4.1 percent, 1,250 events."
    synthese = "L'inflation était de 3,5 % en septembre 2026 ; 1 250 événements ; le chômage atteint 4,7 %."
    c = bf.controler(synthese, corpus)
    assert c["nombres"] == 4
    assert c["absents"] == 1
    assert c["cas"][0]["nombre"] == "4,7"


def test_chiffre_isole_ignore():
    c = bf.controler("3 pays et 7 villes", "rien")
    assert c["nombres"] == 0


def test_resumer():
    ls = [{"modele": "m", "source_question": "fred", "controle": {"nombres": 4, "absents": 1, "cas": []}},
          {"modele": "m", "source_question": "acled", "controle": {"nombres": 6, "absents": 0, "cas": []}}]
    r = bf.resumer(ls)
    assert r["m"]["part_nombres_absents"] == 0.1
    assert r["m"]["part_syntheses_avec_absent"] == 0.5
