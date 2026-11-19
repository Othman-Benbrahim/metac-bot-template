from pathlib import Path

import adaptateurs as ad
import collecte_openmeasures as co


def test_seaux_tolerants():
    es = {"aggregations": {"x": {"buckets": [{"key_as_string": "2026-04-01T00:00:00Z", "doc_count": 12}]}}}
    assert co.seaux(es) == [("2026-04-01", 12.0)]
    assert co.seaux({"created_key": [{"key": 1775001600000, "doc_count": 3}]})[0][1] == 3.0
    assert co.seaux({"hits": {"hits": [{"_source": {"txt": "x"}}]}}) == []


def test_adaptateur_normalise(tmp_path: Path):
    (tmp_path / "openmeasures.csv").write_text("site,serie,jour,n\ntelegram,complot,2026-04-01,50\n"
                                              "telegram,reference,2026-04-01,100000\n", encoding="utf-8")
    assert ad.lire("openmeasures:telegram:complot", tmp_path) == [("2026-04-01", 5.0)]
