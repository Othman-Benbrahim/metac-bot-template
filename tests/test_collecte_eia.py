"""0.10.333 : collecte EIA (stocks de brut), lecture de la page d'historique et adaptateur."""
from pathlib import Path

import adaptateurs as ad
import collecte_eia as ce

PAGE = """<table><tr><th>Year-Month</th><th>Week 1</th></tr>
<tr><td class="B6">&nbsp;&nbsp;2025-Dec&nbsp;</td><td class="B5">12/05&nbsp;</td><td class="B3">421,234</td>
<td class="B5">12/12&nbsp;</td><td class="B3">418,001</td><td class="B5">&nbsp;</td><td class="B3">&nbsp;</td></tr>
<tr><td class="B6">&nbsp;&nbsp;2026-Jan&nbsp;</td><td class="B5">01/02&nbsp;</td><td class="B3">416,500</td></tr>
<tr><td>notes</td><td>sans date</td></tr></table>"""


def test_lire_page():
    assert ce.lire_page(PAGE) == [("2025-12-05", 421234.0), ("2025-12-12", 418001.0), ("2026-01-02", 416500.0)]
    assert ce.lire_page("<html>rien</html>") == []


def test_adaptateur_eia(tmp_path: Path):
    (tmp_path / "eia.csv").write_text("serie,jour,valeur\nWCESTUS1,2026-01-02,416500\nWCESTUS1,2025-12-05,421234\n"
                                      "WCRFPUS2,2026-01-02,13500\n", encoding="utf-8")
    assert ad.lire("eia:WCESTUS1", tmp_path) == [("2025-12-05", 421234.0), ("2026-01-02", 416500.0)]
    assert ad.lire("eia:WCRFPUS2", tmp_path) == [("2026-01-02", 13500.0)]
