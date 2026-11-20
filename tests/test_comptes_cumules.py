"""Comptes cumulés (0.10.403) : version 1 branchée pour le total CDC de la rougeole (pari d'auteur)."""
import comptes_cumules as cc
import collecte_rougeole as cr


def test_fourchette_cumul_croissante():
    f = cc.fourchette_cumul([10, 12, 9, 11, 10, 13, 12, 11, 10], 500, 1)
    vals = [v for _, v in f]
    assert vals == sorted(vals) and vals[0] >= 500


def test_rougeole_attend_neuf_releves(tmp_path, monkeypatch):
    f = tmp_path / "r.csv"
    f.write_text("jour,total\n2026-11-12,5412\n", encoding="utf-8")
    monkeypatch.setattr(cc, "ROUGEOLE", f)
    t = "How many confirmed U.S. measles cases for 2026 will CDC report in its November 27, 2026 update?"
    assert cc.fourchette_rougeole(t, "2026-11-20", "2026-11-27") is None
    lignes = "\n".join(f"2026-{m:02d}-{d:02d},{5000 + 40 * i}" for i, (m, d) in enumerate(
        [(9, 17), (9, 24), (10, 1), (10, 8), (10, 15), (10, 22), (10, 29), (11, 5), (11, 12)]))
    f.write_text("jour,total\n" + lignes + "\n", encoding="utf-8")
    r = cc.fourchette_rougeole(t, "2026-11-20", "2026-11-27")
    assert r and r["dernier_total"] == 5320 and r["percentiles"][0][1] >= 5320


def test_lire_page_cdc():
    html = "<p>As of November 12, 2026, 5,412 confirmed measles cases were reported</p>"
    assert cr.lire(html) == ("2026-11-12", 5412)
