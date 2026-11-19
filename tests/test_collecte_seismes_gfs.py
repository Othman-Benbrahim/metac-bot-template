"""0.10.355 : séismes USGS (comptes par jour) et prévisions GFS (chaleur annoncée)."""
from datetime import date, timedelta
from pathlib import Path

import adaptateurs as ad
import collecte_gfs as cg
import collecte_seismes as cs

CSV = ("time,latitude,longitude,depth,mag,magType\n"
       "2026-11-01T03:00:00.000Z,35.0,51.0,10,4.8,mb\n"
       "2026-11-01T09:00:00.000Z,-20.0,-70.0,30,6.4,mww\n"
       "2026-11-03T01:00:00.000Z,10.0,120.0,30,7.1,mww\n"
       "2026-11-03T02:00:00.000Z,10.0,120.0,30,4.2,mb\n"
       "2026-11-03T02:00:00.000Z,10.0,120.0,30,,mb\n")


def test_agreger():
    a = cs.agreger(CSV)
    assert a["2026-11-01"] == {"m45": 2, "m6": 1, "m7": 0, "mmax": 6.4, "iran_m45": 1}
    assert a["2026-11-03"]["m45"] == 1 and a["2026-11-03"]["m7"] == 1 and "2026-11-02" not in a


def test_ecrire_zeros_et_adaptateur(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(cs, "SORTIE", tmp_path / "seismes-usgs.csv")
    monkeypatch.setattr(cs, "DEBUT", date(2026, 10, 31))
    cs.ecrire(cs.agreger(CSV), date(2026, 11, 3))
    assert ad.lire("seismes:m6", tmp_path) == [("2026-10-31", 0.0), ("2026-11-01", 1.0), ("2026-11-02", 0.0), ("2026-11-03", 1.0)]
    assert ad.lire("seismes:iran_m45", tmp_path)[1] == ("2026-11-01", 1.0)
    assert cs.lire()["2026-11-03"]["mmax"] == 7.1


def test_tranches():
    h = date(2026, 11, 18)
    assert len(cs.tranches({}, h)) == 2026 - cs.DEBUT.year + 1 and cs.tranches({}, h)[-1][1] == date(2026, 11, 19)
    assert cs.tranches({"x": {}}, h) == [(h - timedelta(days=cs.RECHARGE), date(2026, 11, 19))]


def test_plage_index():
    idx = ("1:0:d=2026111900:PRMSL:mean sea level:24 hour fcst:\n"
           "2:51234:d=2026111900:TMP:2 m above ground:24 hour fcst:\n"
           "3:99000:d=2026111900:SPFH:2 m above ground:24 hour fcst:\n")
    assert cg.plage(idx) == (51234, 98999)
    assert cg.plage("1:0:d=x:TMP:2 m above ground:24 hour fcst:\n") == (0, None)
    assert cg.plage("1:0:d=x:UGRD:10 m above ground:\n") is None


def test_moyennes():
    inst = {h: {p: float(h) for p in cg.cm.POINTS} for h in range(24, 24 * 8)}
    m = cg.moyennes(inst)
    assert ("delhi", 1, 33.0) in m and len(m) == 7 * len(cg.cm.POINTS)
    del inst[30]
    assert not any(e == 1 for _, e, _ in cg.moyennes(inst))


def test_meteo_prevue(tmp_path: Path):
    lignes = ["point,jour,t_moy"]
    for an in range(2016, 2027):
        for k in range(-10, 30):
            j = date(an, 11, 1) + timedelta(days=k)
            if j <= date(2026, 11, 19):
                lignes.append(f"delhi,{j},{20.0 if an < 2026 else 22.0}")
    (tmp_path / "meteo-points.csv").write_text("\n".join(lignes) + "\n", encoding="utf-8")
    prev = ["run,point,jour,echeance,t_moy"]
    for r in range(1, 20):                             # runs du 1er au 19 novembre, la grille a 1 °C de trop
        run = date(2026, 11, r)
        for e in range(1, 8):
            prev.append(f"{run},delhi,{run + timedelta(days=e)},{e},{23.0 if e < 7 else 26.0}")
    (tmp_path / "gfs-previsions.csv").write_text("\n".join(prev) + "\n", encoding="utf-8")
    s = dict(ad.lire("meteo_prevue:delhi", tmp_path))
    assert s["2026-11-01"] == round((6 * 3 + 6) / 7, 2)                 # sans biais connu : 3 °C annoncés, 6 à J+7
    assert s["2026-11-19"] == round((6 * 2 + 5) / 7, 2)                 # biais de 1 °C retranché (≥ 10 paires)
    assert dict(ad.lire("meteo_prevue:delhi:7", tmp_path))["2026-11-19"] == 5.0
