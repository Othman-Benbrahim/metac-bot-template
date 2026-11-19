"""0.10.337 : sources ouvertes des compartiments vides, et ordre des collectes."""
from pathlib import Path

import adaptateurs as ad
import collecte_ouvertes as co
import priorites_traces as pt


def test_polarisation():
    lignes = ["congress,chamber,icpsr,party_code,bioname,nominate_dim1"]
    lignes += [f"118,House,{i},100,X,{-0.4 + i / 1000}" for i in range(12)]
    lignes += [f"118,House,{100 + i},200,Y,{0.5 + i / 1000}" for i in range(12)]
    lignes += ["118,Senate,999,200,Z,0.9", "117,House,1,100,X,-0.3"]
    assert co.polarisation("\n".join(lignes)) == [("2023-01-03", 0.9)]      # 117e Congrès : trop peu d'élus, écarté


def test_co2_et_vues():
    t = "# commentaire\n# encore\nyear,month,decimal date,average,deseasonalized,ndays,sdev,unc\n2025,1,2025.04,424.6,425.0,30,0.5,0.1\n2025,2,2025.12,-99.99,1,1,1,1\n"
    assert co.co2(t) == [("2025-01-15", 424.6)]
    assert co.vues({"items": [{"timestamp": "2026011800", "views": 120}]}) == {"2026-01-18": 120.0}


def test_adaptateur_ouvert(tmp_path: Path):
    (tmp_path / "ouvertes.csv").write_text("serie,jour,valeur\nco2_mauna_loa,2025-01-15,424.6\n", encoding="utf-8")
    assert ad.lire("ouvert:co2_mauna_loa", tmp_path) == [("2025-01-15", 424.6)]


def test_priorites_alternent_les_niveaux():
    choix = pt.classer(n=10)
    assert len(choix) == 10 and len({c["niveau"] for c in choix}) >= 6
    assert all(not c["fermee"] for c in choix)
