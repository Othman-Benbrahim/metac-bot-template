"""0.10.364 : brique « scrutin » (forme des questions, lecture des tableaux de sondages, calcul déterministe)."""
from datetime import date

import banc_scrutin as b

WIKI = """== 2026 ==
{| class="wikitable"
! Pollster
! Fieldwork date
! Sample size
! [[Luiz Inácio Lula da Silva|Lula]]
! [[Flávio Bolsonaro|Flávio]]
! [[Ronaldo Caiado|Caiado]]
! Others
! Lead
|-
| [[Datafolha]]
| {{dts|2026|9|20}}
| 2,000
| style="background:#fcc"| '''41'''
| 33
| 8
| 18
| 8
|-
| Quaest
| 10–12 Sep
| 2,100
| 39%
| 35%
| 9%
| 17
| 4
|-
| Old poll
| 3 Jan 2026
| 1,000
| 30
| 30
| 30
| 10
| 0
|}
"""


def test_formes():
    f = b.forme("Will Fernando Haddad finish in second place in the first round of the 2026 Brazilian presidential election?")
    assert (f["evenement"], f["rang"], f["classe"]) == ("rang", 2, "S1")
    assert b.forme("Will Mark Carney win the Canadian election by 9-12%?") is None
    assert b.forme("Will PVV win the most seats in the 2025 Netherlands parliamentary election?")["classe"] == "S2"
    assert b.forme("Will X qualify for the 2026 Canadian election runoff?") is None      # pas de second tour : hors brique


def test_tableau_et_moyenne():
    tabs = b.tableaux(WIKI, 2026)
    assert tabs and tabs[0]["colonnes"][3] == "Lula" and len(tabs[0]["lignes"]) == 3
    p = b.moyenne_sondages(tabs, date(2026, 9, 25), "Luiz Inácio Lula da Silva")
    assert p and p["__sujet__"] == "Lula" and p["Lula"] == 40.0 and p["Flávio"] == 34.0
    assert "Others" not in p and "Lead" not in p
    assert b.moyenne_sondages(tabs, date(2026, 6, 1), "Lula") is None               # aucun sondage dans les 30 jours


def test_calcul_deterministe():
    parts = {"Lula": 40.0, "Flávio": 34.0, "Caiado": 8.5, "__sujet__": "Lula"}
    f = {"evenement": "qualifie", "rang": 2, "classe": "S1"}
    p1, p2 = b.probabilite(parts, f, 10), b.probabilite(parts, f, 10)
    assert p1 == p2 == 0.98
    g = b.probabilite(dict(parts, __sujet__="Caiado"), {"evenement": "gagne", "rang": 1, "classe": "S1"}, 10)
    assert g == 0.02
    r2 = b.probabilite(dict(parts, __sujet__="Flávio"), {"evenement": "rang", "rang": 2, "classe": "S1"}, 300)
    assert 0.6 < r2 < 0.98                                                           # loin du vote : incertitude plus large
