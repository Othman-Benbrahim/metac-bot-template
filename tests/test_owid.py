"""2026-11-25 : adaptateur Our World in Data."""
import gzip

import adaptateurs as ad


def _ecrit(tmp_path, slug, texte):
    (tmp_path / "owid").mkdir(exist_ok=True)
    with gzip.open(tmp_path / "owid" / f"{slug}.csv.gz", "wt", encoding="utf-8") as f:
        f.write(texte)


def test_monde_pays_moyenne_somme(tmp_path):
    _ecrit(tmp_path, "g", "Entity,Code,Year,a,b\nWorld,OWID_WRL,2020,2.0,1\nFrance,FRA,2020,1.0,1\nChile,CHL,2020,3.0,1\nAfrica,,2020,9,9\n")
    assert ad.owid(tmp_path, "g") == [("2020-07-01", 2.0)]
    assert ad.owid(tmp_path, "g", "FRA") == [("2020-07-01", 1.0)]
    assert ad.owid(tmp_path, "g", "moyenne") == [("2020-07-01", 2.0)]
    assert ad.owid(tmp_path, "g", "World", "somme") == [("2020-07-01", 3.0)]
    assert ad.owid(tmp_path, "absent") == []


def test_jour(tmp_path):
    _ecrit(tmp_path, "j", "Entity,Code,Day,x\nArctic Ocean,,2026-09-15,4.5\n")
    assert ad.lire("owid:j:Arctic Ocean", tmp_path) == [("2026-09-15", 4.5)]
