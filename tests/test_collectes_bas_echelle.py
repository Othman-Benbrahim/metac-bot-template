"""0.10.318 : traces du bas de l'échelle (FRED, Open-Meteo) et leurs adaptateurs, sans réseau."""
from pathlib import Path

import adaptateurs as ad
import collecte_fred as cf


def test_lecture_csv_fred_ignore_les_points():
    t = "observation_date,DCOILBRENTEU\n2026-11-02,64.1\n2026-11-03,.\n2026-11-04,65.0\n"
    assert cf.lire_csv(t, "DCOILBRENTEU") == [("2026-11-02", 64.1), ("2026-11-04", 65.0)]


def test_adaptateur_fred(tmp_path: Path):
    (tmp_path / "fred.csv").write_text("serie,jour,valeur\nDFF,2026-01-02,4.33\nDGS10,2026-01-02,4.1\nDFF,2026-01-01,4.32\n",
                                       encoding="utf-8")
    assert ad.lire("fred:DFF", tmp_path) == [("2026-01-01", 4.32), ("2026-01-02", 4.33)]


def test_adaptateur_meteo_rend_une_anomalie(tmp_path: Path):
    lignes = ["point,jour,t_moy"]
    for an in (2023, 2024, 2025):
        for j in range(1, 29):
            lignes.append(f"berlin,{an}-01-{j:02d},{0.0 if an < 2025 else 5.0}")
    (tmp_path / "meteo-points.csv").write_text("\n".join(lignes) + "\n", encoding="utf-8")
    s = dict(ad.lire("meteo:berlin", tmp_path))
    assert s["2025-01-15"] == 5.0                 # 5 °C au-dessus des mêmes jours des années précédentes
    assert "2023-01-15" not in s                  # première année : pas de référence


def test_adaptateur_nowcast(tmp_path: Path):
    (tmp_path / "nowcast-inflation.csv").write_text("releve_le,periode,mesure,valeur\n2026-11-16,November 2026,variation_mensuelle:CPI,0.14\n",
                                                    encoding="utf-8")
    assert ad.lire("nowcast:variation_mensuelle:CPI", tmp_path) == [("2026-11-16", 0.14)]
