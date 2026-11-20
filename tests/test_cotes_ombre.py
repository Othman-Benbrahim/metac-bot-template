from datetime import date

import cotes_ombre as co

T = "Will Bitcoin close above $110,000 on December 31, 2026?"
R = date(2026, 12, 31)


def m(q, p=0.3, mise=1e6, fin="2026-12-31T12:00:00Z", **kw):
    return {"question": q, "outcomes": '["Yes", "No"]', "outcomePrices": f'["{p}", "{1 - p}"]', "volumeNum": mise,
            "endDate": fin, "closed": False, "active": True, "id": q, "slug": q[:20], **kw}


def test_apparie_le_meme_intitule():
    r, motif = co.apparier(T, R, [m("Will Bitcoin close above $110,000 on December 31, 2026?")])
    assert motif == "apparié" and r["p_oui"] == 0.3


def test_refuse_seuil_sens_date_mise_et_ambigu():
    assert co.apparier(T, R, [m("Will Bitcoin close above $100,000 on December 31, 2026?")])[0] is None   # seuil
    assert co.apparier(T, R, [m("Will Bitcoin close below $110,000 on December 31, 2026?")])[0] is None   # sens
    assert co.apparier(T, R, [m(T, fin="2027-06-30T00:00:00Z")])[0] is None                                # date
    assert co.apparier(T, R, [m(T, mise=10_000)])[0] is None                                               # mise
    assert co.apparier(T, R, [m(T, closed=True)])[0] is None
    r, motif = co.apparier(T, R, [m(T), m("Bitcoin close above $110,000 on December 31, 2026?")])
    assert r is None and motif.startswith("ambigu")
    autre = {"question": T, "outcomes": '["Trump", "Harris"]', "outcomePrices": '["0.5", "0.5"]', "volumeNum": 1e6,
             "endDate": "2026-12-31T00:00:00Z", "id": "x"}
    assert co.apparier(T, R, [autre])[0] is None                                                           # pas Oui/Non


def test_negation_et_mots():
    q = "Will Maduro remain president of Venezuela on December 31, 2026?"
    assert co.apparier(q, R, [m("Will Maduro leave office as president of Venezuela by December 31, 2026?")])[0] is None
    assert co.nombres("$110,000 and 2.50%") == {"110000", "2.5"}
