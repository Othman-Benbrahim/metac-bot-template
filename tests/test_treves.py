import json
from datetime import date

import treves as t


def test_alerte_gdelt_seuils():
    hier = date(2026, 12, 10)
    base = {f"2026-11-{k:02d}": 1 for k in range(12, 31)} | {f"2026-12-{k:02d}": 1 for k in range(1, 10)}
    c = {("RUS", "UKR"): {**base, "2026-12-10": 6}}
    a = t.alertes_gdelt(c, hier)
    assert a and a[0]["guerre"] == "russie_ukraine" and a[0]["n"] == 6
    c2 = {("RUS", "UKR"): {**{k: 3 for k in base}, "2026-12-10": 6}}      # 6 < 4 x 3 : habituel
    assert t.alertes_gdelt(c2, hier) == []


def test_garde_fou_refus_ecarte():
    al = {"guerre": "russie_ukraine", "jour": "2026-12-10", "sources": {"gdelt": {"n": 6}}}
    titres = [{"titre": "Ukraine rejects Russian truce offer", "lien": "https://a/1"},
              {"titre": "Kremlin says ceasefire talks stalled", "lien": "https://a/2"}]
    rep = json.dumps({"classes": ["treve_refusee_ou_rompue", "treve_proposee_ou_negociee"]})
    r = t.garde_fou(al, titres, appel=lambda m, msgs: rep)
    assert r["statut"] == "ecartee_par_le_garde_fou"
    rep2 = json.dumps({"classes": ["treve_declaree", "sans_rapport"]})
    assert t.garde_fou(al, titres, appel=lambda m, msgs: rep2)["statut"] == "a_verifier"


def test_garde_fou_sans_titre_ni_modele():
    al = {"guerre": "israel_iran", "jour": "2026-12-10", "sources": {}}
    assert t.garde_fou(al, [])["statut"] == "non_filtree"


def test_titres_puits(tmp_path, monkeypatch):
    import puits
    puits.ajouter([{"jour": "2026-12-09", "lien": "https://x/1", "titre": "Israel and Iran agree to ceasefire"},
                   {"jour": "2026-12-09", "lien": "https://x/2", "titre": "Iran oil exports rise"}], tmp_path)
    monkeypatch.setattr(puits, "DOSSIER", tmp_path)
    orig = puits.charger
    monkeypatch.setattr(puits, "charger", lambda a, b, dossier=tmp_path: orig(a, b, dossier))
    ts = t.titres_puits("israel_iran", date(2026, 12, 10))
    assert [x["lien"] for x in ts] == ["https://x/1"]
