"""0.10.348 : banc de la proxémie (la carte aide-t-elle à prévoir ?)."""
import adaptateurs as ad
import banc_proxemie as bp


def test_regles_de_rattachement():
    assert set(bp.fiches_de("Will Iran close the Strait of Hormuz before July?")) >= {"ormuz", "iran-nucleaire"}
    assert bp.fiches_de("Will Timothée Chalamet win Best Actor?") == []
    assert bp.COMBINEE.search("We are presenting you with two probability questions. Please predict")


def test_coupure_sans_fuite(monkeypatch):
    monkeypatch.setitem(ad.ADAPTATEURS, "faux", lambda reg: [("2026-01-01", 1.0), ("2026-03-01", 2.0)])
    c = bp._Coupure()
    c.date = "2026-02-01"
    assert c.lire("faux") == [("2026-01-01", 1.0)]
    c.date = "2026-12-31"
    assert len(c.lire("faux")) == 2
