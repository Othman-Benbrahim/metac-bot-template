"""2026-11-25 : recoupement chiffré des briefs (étages 1 et 2), calculé par le code."""
import recoupement_briefs as rb


def test_nombre():
    assert rb.nombre("9 745") == 9745 and rb.nombre("4,6 %") == 4.6 and rb.nombre("1,2 milliard de dollars") == 1.2e9
    assert rb.nombre("434 GW") == 434 and rb.nombre("") is None and rb.nombre("12.401.107") == 12401107


def test_contexte_sans_avenir_et_anomalie():
    bruit = [0.3, -0.1, 0.5, 0.2, -0.4, 0.1, 0.6, -0.2, 0.0, 0.35, -0.3, 0.15, 0.45, -0.05, 0.25, -0.15, 0.4, 0.05, -0.25, 0.2]
    s = [(f"2026-01-{i:02d}", 10.0 + bruit[i - 1]) for i in range(1, 21)] + [("2026-01-21", 30.0), ("2026-02-01", 99.0)]
    c = rb.contexte(s, "2026-01-25")
    assert c["date"] == "2026-01-21" and c["valeur"] == 30.0 and c["age_jours"] == 4 and c["anormal"]
    assert rb.contexte(s, "2025-12-31") is None


def test_traiter():
    series = {"a:b": [("owid:x", "x"), ("rss_matiere:y", "y")], "c:d": []}
    donnees = {"owid:x": [("2024-07-01", 887.0), ("2025-07-01", 1202.0)], "rss_matiere:y": [("2026-11-24", 3.0)]}
    lignes = [{"statut": "ok", "fichier": "f.md", "jour": "2026-11-25", "compartiments": ["a:b", "c:d"],
               "brief": {"faits": [{"chiffre": "1 200 GW"}, {"chiffre": "5 %"}, {"chiffre": ""}]}}]
    out, sans = rb.traiter(lignes, series, lire=lambda a, reg: donnees.get(a, []))
    b = out["f.md"]
    assert b["compartiments"][0]["series"][0]["valeur"] == 1202.0 and b["compartiments"][0]["attention"][0]["adaptateur"] == "rss_matiere:y"
    assert [f["verdict"] for f in b["chiffres"]] == ["cohérent avec la série", "non recoupable"]
    assert sans == {"c:d": 1}
