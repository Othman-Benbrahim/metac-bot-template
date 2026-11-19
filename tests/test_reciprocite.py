"""0.10.312 : banc de la réciprocité entre États (données synthétiques)."""
import random

import banc_reciprocite as br


def _donnees(reciproque: bool):
    ss = br.semaines("2023-01-02", "2026-10-26")
    rnd = random.Random(3)
    sens = {}
    for p in range(6):
        a, b = f"A{p}", f"B{p}"
        x, y = 0.0, 0.0
        da, db = {}, {}
        for s in ss:
            nx = rnd.gauss(0, 1)
            ny = (0.7 * x if reciproque else 0.0) + rnd.gauss(0, 1)
            x, y = nx, ny
            da[s] = {"n": 20, "somme_g": round(x * 25, 2)}
            db[s] = {"n": 20, "somme_g": round(y * 25, 2)}
        sens[f"{a}>{b}"], sens[f"{b}>{a}"] = da, db
    return {"debut": "2023-01-02", "fin": "2026-10-26", "sens": sens}


def test_reciprocite_vue_quand_elle_existe():
    r = br.analyser(_donnees(True))
    assert r["verdict"] == "la réciprocité se voit" and r["paires"] == 6
    assert r["par_sens"]["B0>A0"]["rho"] > 0.4 and r["par_sens"]["B0>A0"]["style"] in ("donnant-donnant", "rancunier", "conciliant")


def test_reciprocite_absente():
    r = br.analyser(_donnees(False))
    assert r["verdict"] != "la réciprocité se voit"


def test_sans_donnees():
    assert "en attente" in br.analyser({"debut": "2023-01-02", "fin": "2023-02-01", "sens": {}})["verdict"]


def test_sql_dyades_borne_et_publique():
    import gdelt_bq as g
    s = g.sql_dyades()
    assert "_PARTITIONTIME BETWEEN" in s and "LIMIT 40" in s and "('GOV', 'MIL')" in s
    assert g.PLAFOND_REQUETE_GO["dyades"] <= 120
