"""2026-11-27 : en-têtes de sondages en photos ou en sigles."""
from datetime import date

import banc_scrutin as bs

BRESIL = """{| class="wikitable"
! rowspan="2" | Pollster
! rowspan="2" | Polling period
! [[File:Lula 2023 (cropped).jpg|70x70px]]
! [[File:Flávio Bolsonaro.jpg|70x70px]]
|-
! Lula
! Flávio
|-
| Datafolha || 10–12 Nov 2026 || 41% || 33%
|-
| Quaest || 2–4 Nov 2026 || 43% || 31%
|}
"""

QUEBEC = """{| class="wikitable"
! Polling firm !! Last date of polling !! [[Quebec Liberal Party|QLP]] !! [[Parti Québécois|PQ]] !! [[Coalition Avenir Québec|CAQ]]
|-
| Léger || 20 Nov 2026 || 28 || 33 || 17
|-
| Pallas || 12 Nov 2026 || 26 || 35 || 18
|}
"""


def test_photos_et_noms():
    t = bs.tableaux(BRESIL, 2026)
    assert t and any("Lula" in c for c in t[0]["colonnes"]) and any("Bolsonaro" in c for c in t[0]["colonnes"])
    m = bs.moyenne_sondages(t, date(2026, 11, 27), "Flávio Bolsonaro")
    assert m and round(m[m["__sujet__"]]) == 32


def test_sigle_et_cible_du_lien():
    t = bs.tableaux(QUEBEC, 2026)
    m = bs.moyenne_sondages(t, date(2026, 11, 27), "Quebec Liberal Party")
    assert m and round(m[m["__sujet__"]]) == 27
