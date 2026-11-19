from pathlib import Path

import adaptateurs as ad
import collecte_webamon as cw


def test_formes_et_adaptateur(tmp_path: Path):
    assert all("{j}" in f for f in cw.FORMES) and "infostealers" not in cw.INDEX
    assert cw.FORMES[0].format(j="2026-11-18", k="2026-11-19") == "date:[2026-11-18 TO 2026-11-18]"
    (tmp_path / "webamon.csv").write_text("index,jour,total\nscans,2026-11-18,1200\nnew_domains,2026-11-18,90000\n",
                                         encoding="utf-8")
    assert ad.lire("webamon:scans", tmp_path) == [("2026-11-18", 1200.0)]
