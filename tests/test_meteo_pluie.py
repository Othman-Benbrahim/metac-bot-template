"""0.10.476 : pluie GHCN-Daily (fiche Inde, mousson) — lecture, inventaire, adaptateur pluie:<point>. Sans réseau."""
import csv
from datetime import date, timedelta

import adaptateurs as ad
import calibrer as cb
import collecte_meteo as cm


def test_lire_pluie_et_inventaire():
    t = ("IN012345678,20260601,PRCP,123,,,S,\n"
         "IN012345678,20260602,PRCP,40,,X,S,\n"          # douteuse : écartée
         "IN012345678,20260602,TMAX,350,,,S,\n")
    assert cm.lire_pluie(t, "2026-01-01") == [("2026-06-01", 12.3)]
    inv = ("IN012345678  19.1  72.8 PRCP 1950 2026\n"
           "IN099999999  19.2  72.9 TMAX 1950 2026\nIN099999999  19.2  72.9 TMIN 1950 2026\n")
    assert cm.lire_inventaire(inv, 2026, "pluie") == {"IN012345678"}
    assert cm.lire_inventaire(inv, 2026) == {"IN099999999"}
    assert set(cm.POINTS_PLUIE) <= set(cm.POINTS) and cb.lieux("pluie:mumbai") == {"IN"}


def test_adaptateur_pluie(tmp_path):
    # 5 ans : 10 mm par jour en juin ; l'année 2026 à 5 mm par jour → environ 50 % de la normale
    lignes = []
    for an in range(2021, 2027):
        d = date(an, 6, 1)
        while d <= date(an, 7, 15):
            lignes.append(("mumbai", d.isoformat(), 5.0 if an == 2026 else 10.0))
            d += timedelta(days=1)
    with (tmp_path / "meteo-pluie.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["point", "jour", "pluie_mm"])
        w.writerows(lignes)
    s = dict(ad.lire("pluie:mumbai", tmp_path))
    assert s["2026-07-15"] == 50.0
    assert "2021-07-15" not in s                                   # pas de référence la première année
    assert dict(ad.lire("pluie:mumbai:30", tmp_path))["2026-07-15"] == 50.0


def test_ucdp_mois(tmp_path):
    """0.10.477 : morts par mois d'un pays (ISO3), zéros entre le premier et le dernier mois publiés."""
    (tmp_path / "cartes").mkdir()
    (tmp_path / "cartes" / "ucdp-pays-mois.csv").write_text(
        "pays_source,iso3,code_pays,mois,source,evenements,somme\n"
        "Myanmar (Burma),MMR,775,2026-01,mois,3,10.0\nIndia,IND,750,2026-03,mois,2,5.0\n", encoding="utf-8")
    assert ad.lire("ucdp_mois:MMR", tmp_path) == [("2026-01-01", 10.0), ("2026-02-01", 0.0), ("2026-03-01", 0.0)]
    assert cb.lieux("ucdp_mois:MMR") == {"MM"}
