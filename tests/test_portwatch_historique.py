"""2026-11-26 : historique long PortWatch, une case (détroit, année) par passage, jamais relue."""
import collecte_portwatch as cp


def test_une_case_par_passage(tmp_path, monkeypatch):
    monkeypatch.setattr(cp, "HISTORIQUE", tmp_path / "h.csv")
    appels = []

    def fausse(c, motif, an, *a, **k):
        appels.append((motif, an))
        return [{"date": f"{an}-03-01", "n_total": 5, "n_tanker": 1, "n_container": 2}]
    monkeypatch.setattr(cp, "requete", fausse)
    cp.historique(None, 2021)
    cp.historique(None, 2021)
    assert appels == [("Suez", 2019), ("Bab el-Mandeb", 2019)]
    lignes = (tmp_path / "h.csv").read_text().splitlines()
    assert len(lignes) == 3 and "suez,2019-03-01,5,1,2,2019" in lignes


def test_case_vide_marquee(tmp_path, monkeypatch):
    monkeypatch.setattr(cp, "HISTORIQUE", tmp_path / "h.csv")
    monkeypatch.setattr(cp, "requete", lambda *a, **k: [])
    cp.historique(None, 2020)
    cp.historique(None, 2020)
    txt = (tmp_path / "h.csv").read_text()
    assert "suez,,,,,2019" in txt and "bab_el_mandeb,,,,,2019" in txt


def test_adaptateur_long(tmp_path):
    import adaptateurs as ad
    (tmp_path / "portwatch-historique.csv").write_text(
        "detroit,jour,navires,petroliers,porte_conteneurs,annee\nsuez,2019-03-01,5,1,2,2019\nsuez,,,,,2020\n")
    (tmp_path / "portwatch-detroits.csv").write_text("detroit,jour,navires,petroliers,porte_conteneurs\nsuez,2026-06-01,9,1,1\n")
    assert ad.portwatch_long(tmp_path, "suez") == [("2019-03-01", 5.0), ("2026-06-01", 9.0)]
