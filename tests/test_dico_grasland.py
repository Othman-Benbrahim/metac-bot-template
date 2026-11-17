"""0.10.219 : second codeur des flux RSS (dictionnaire Grasland-Toureille)."""
import dico_grasland as dg
import collecte_rss as cr

LIGNES = [
    {"lang": "fr", "alias": "Russie", "code": "STA_NAM_RUS"},
    {"lang": "fr", "alias": "Moscou", "code": "STA_CAP_RUS"},
    {"lang": "fr", "alias": "Erdogan", "code": "STA_HEA_TUR_Erdogan"},
    {"lang": "fr", "alias": "OTAN", "code": "REG_ORG_XXX_NATO"},
    {"lang": "fr", "alias": "Bruxelles", "code": "XXX_XXX_EUR_Brussels"},
    {"lang": "fr", "alias": "Paris Saint-Germain", "code": "ZZZ_ZZZ_ZZZ"},
    {"lang": "fr", "alias": "Paris", "code": "STA_CAP_FRA"},
    {"lang": "fr", "alias": "Congo", "code": "STA_XXX_AFR_Congo"},
    {"lang": "de", "alias": "Moskau", "code": "STA_CAP_RUS"},
]
TABLE = {"RUS": "RU", "TUR": "TR", "FRA": "FR"}


def test_detecter():
    m = dg.construire(LIGNES, TABLE, ("fr",))
    assert dg.detecter("Moscou dément ; Erdogan menace", m) == ({"RU", "TR"}, set())
    assert dg.detecter("L'OTAN et Bruxelles", m) == (set(), {"REG_ORG_XXX_NATO"})
    assert dg.detecter("Le Paris Saint-Germain gagne", m) == (set(), set())      # exclusion masquée
    assert dg.detecter("Paris accueille", m) == ({"FR"}, set())
    assert dg.detecter("Au Congo", m) == (set(), set())                            # ambiguïté masquée
    assert dg.detecter("moscou", m) == (set(), set())                              # sensible à la casse
    assert dg.detecter("Moskau", m) == (set(), set())                              # langue non demandée


def test_bilan_accord():
    t = cr.bilan_accord({("RU", "2026-11-17"): [3, 1, 2]}, {"RU": 1}, {"RU": 2})
    assert "accord 50%" in t
