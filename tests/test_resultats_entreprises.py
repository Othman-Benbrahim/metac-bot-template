import math
from datetime import date, timedelta

import resultats_entreprises as rex

OPTS = ["1,615 million or less", ">1,615 mil. & <1,670 mil.", "≥1,670 mil. & ≤1,725 mil.",
        ">1,725 mil. & ≤1,785 mil.", ">1,785 mil."]


def _edgar(tmp_path, monkeypatch, n=30, fin="2026-07-31"):
    p = tmp_path / "edgar.csv"
    lignes = ["entreprise,mesure,debut,fin,valeur"]
    d = date.fromisoformat(fin)
    for i in range(n):
        f = d - timedelta(days=91 * (n - 1 - i))
        v = 1e9 * (1.07 ** (i / 4)) * [1, 1.1, 0.95, 1.2][i % 4] * (1 + 0.01 * ((i * 7) % 5 - 2))
        lignes.append(f"SNOW,chiffre_affaires,{f - timedelta(days=90)},{f},{v}")
    p.write_text("\n".join(lignes), encoding="utf-8")
    monkeypatch.setattr(rex, "EDGAR", p)


def test_reconnaissance():
    assert rex.entreprise("What will the first reported revenues after October 2026 be for Snowflake?") == "SNOW"
    assert rex.entreprise("What will Snowflake's share price be?") is None
    assert rex.entreprise("Q3 revenue of Acme (NVDA)?") == "NVDA"
    assert rex.info_publiee("Product revenue guidance for Q3 is $1,588m")
    assert rex.info_publiee("Analysts expect revenue of $1.65 billion")
    assert not rex.info_publiee("Revenue grew 29% year over year last quarter.")


def test_bornes():
    assert rex.bornes(OPTS[0]) == (0.0, 1.615e9)
    assert rex.bornes(OPTS[2]) == (1.67e9, 1.725e9)
    assert rex.bornes(OPTS[4]) == (1.785e9, math.inf)
    assert rex.bornes("$2.1 billion or more") == (2.1e9, math.inf)


def test_repartition_et_garde(tmp_path, monkeypatch):
    _edgar(tmp_path, monkeypatch)
    m = rex.modele("SNOW", "2026-11-20")
    assert m and m["trimestre_vise"].startswith("2026-10")
    # cdf croissante, queues non nulles
    ys = [0.5e9 + k * 0.05e9 for k in range(60)]
    c = [rex.cdf(m, y) for y in ys]
    assert all(b >= a for a, b in zip(c, c[1:])) and 0 < c[0] and c[-1] < 1
    centre = math.exp(m["centre"])
    opts = [f"{centre * 0.9 / 1e6:,.0f} million or less", f">{centre * 0.9 / 1e6:,.0f} mil. & <{centre * 1.1 / 1e6:,.0f} mil.",
            f"{centre * 1.1 / 1e6:,.0f} million or more"]
    r = rex.repartition(m, opts)
    assert r and abs(sum(r.values()) - 1) < 1e-9 and max(r, key=r.get) == opts[1]
    assert rex.modele("SNOW", "2027-03-01") is None          # dernier trimestre trop ancien : déjà publié ailleurs
    assert rex.echelle_numerique(m, 500, 5000) == 1e6
    assert rex.echelle_numerique(m, 0.5, 5) == 1e9
