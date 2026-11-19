from pathlib import Path

import adaptateurs as ad
import collecte_airplaneslive as ca


def test_jamais_ladd_ni_pia():
    src = Path(ca.__file__).read_text(encoding="utf-8")
    assert "/ladd\"" not in src and "/pia\"" not in src and set(ca.CODES) == {"7700", "7600", "7500"}


def test_adaptateurs(tmp_path: Path):
    (tmp_path / "urgences-airplaneslive.csv").write_text(
        "releve,code,pays,appareils\n2026-11-19T00:17Z,7700,FR,2\n2026-11-19T06:17Z,7700,mer,1\n", encoding="utf-8")
    (tmp_path / "militaires-airplaneslive.csv").write_text("releve,pays,appareils\n2026-11-19T00:17Z,US,40\n", encoding="utf-8")
    (tmp_path / "airplaneslive-releves.txt").write_text("2026-11-19T00:17Z\n2026-11-19T06:17Z\n", encoding="utf-8")
    assert ad.lire("urgences:7700", tmp_path) == [("2026-11-19", 1.5)]
    assert ad.lire("avions_al:US", tmp_path) == [("2026-11-19", 20.0)]
