import indicateurs_lents as il


def _serie(tmp_path, monkeypatch, n=60):
    p = tmp_path / "estat.csv"
    lignes = ["mois,base,inflation_hors_frais_sur_un_an"]
    for i in range(n):
        a, m = 2021 + i // 12, i % 12 + 1
        lignes.append(f"{a}-{m:02d},2025,{1 + 0.1 * (i % 5)}")
        lignes.append(f"{a}-{m:02d},2020,9.9")
    p.write_text("\n".join(lignes), encoding="utf-8")
    monkeypatch.setattr(il, "_ESTAT", p)


def test_mois_suivant_seulement(tmp_path, monkeypatch):
    _serie(tmp_path, monkeypatch)      # dernière valeur : 2025-12
    t = "What will the Tokyo (Ku-area) core CPI year-on-year inflation rate be for January 2026?"
    f = il.fourchette_tokyo(t)
    assert f and f["date"] == "2025-12" and f["mention"].startswith("This service uses API functions from e-Stat")
    assert all(v < 5 for _, v in f["percentiles"])          # base 2025 seulement, jamais la base 2020
    assert il.fourchette_tokyo(t.replace("January 2026", "February 2026")) is None
    assert il.fourchette_publication(t) == f


def test_autres_titres(tmp_path, monkeypatch):
    _serie(tmp_path, monkeypatch)
    assert il.fourchette_tokyo("What will Japan's national core CPI be for January 2026?") is None
    assert il.fourchette_publication("What will Tokyo core CPI be for January 2026? U.S. comparison") is not None


def test_consensus():
    assert il.consensus_trouve("Economists polled by Reuters expect core CPI to rise 2.5%.")
    assert il.consensus_trouve("The market consensus is 0.3% m/m.")
    assert il.consensus_trouve("A QUICK survey of economists shows a median forecast of 2.6%.")
    assert not il.consensus_trouve("Core CPI rose 2.6% in October, after 2.7% in September.")
