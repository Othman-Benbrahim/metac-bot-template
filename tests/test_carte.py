"""0.10.317 : carte vivante, adaptateurs, quatre axes (taille d'abord)."""
from pathlib import Path

import adaptateurs as ad
import carte as ca
import ecosystemes as ec


def test_axes_lus_en_grandeurs():
    a = ec.axes({"taille": "micro (un navire) à méso (une flotte)", "espace": "marchés mondiaux", "vitesse": "jours à mois",
                 "temps": "saisons"})
    assert a["taille"] == [1, 2] and a["espace"] == [5, 5] and a["vitesse_jours"] == [1, 30] and a["temps"] == "saisons"
    assert ec.axes({"taille": "énorme"})["taille"] is None


def test_taille_obligatoire_et_acteurs():
    f = {"theme": "t", "nom": "T", "declaration": {k: "x" for k in ("but", "limites", "observateur", "date") + ec.AXES},
         "compartiments": [{"id": "a", "niveau": {"espace": "x", "temps": "x", "vitesse": "jours", "taille": "énorme"},
                            "acteurs": [{"nom": "un navire"}]}], "relations": [], "ponts": []}
    e = " | ".join(ec.valider(f))
    assert "taille illisible" in e and "acteur sans nom ou sans taille" in e


def test_echelle_dans_la_propagation():
    assert ca.facteur_echelle([1, 1], [3, 3], None) == ca.ATTENUATION_MONTEE ** 2      # micro → macro : atténué
    assert ca.facteur_echelle([1, 1], [3, 3], "seuil") == 1.0                          # le petit qui fait basculer le grand
    assert ca.facteur_echelle([3, 3], [1, 1], None) == 1.0                             # descente : s'impose
    assert ca.retard_propre([30, 365]) == ca.PART_TEMPS_PROPRE * 30


def test_carte_du_depot_et_propagation():
    c = ca.Carte()
    effets = {e["compartiment"]: e for e in c.propager({"ormuz:force": 1.0}, 365)}
    assert effets["ormuz:navigation"]["sens"] == "baisse"
    assert "energie-mondiale:prix" in effets                                         # par le pont entre fiches
    v = {e["compartiment"] for e in c.voisinage("energie-mondiale:prix", 1)}
    assert "energie-mondiale:stocks" in v and "ormuz:prix" in v


def test_adaptateurs(tmp_path: Path):
    (tmp_path / "portwatch-detroits.csv").write_text("detroit,jour,navires,petroliers,porte_conteneurs\normuz,2026-01-02,3,1,0\n"
                                                      "suez,2026-01-02,40,9,9\normuz,2026-01-01,5,2,1\n", encoding="utf-8")
    assert ad.lire("portwatch:ormuz:petroliers", tmp_path) == [("2026-01-01", 2.0), ("2026-01-02", 1.0)]
    assert ad.lire("dyade:USA:IRN", tmp_path) == []
    try:
        ad.lire("inconnu:x", tmp_path)
        assert False
    except KeyError:
        pass


def test_ponts_meme_et_influence():
    c = ca.Carte()
    types = {(p["de"], p["vers"]): p["type"] for p in c.s["ponts"]}
    assert types[("ormuz:prix", "energie-mondiale:prix")] == "meme"
    e = {x["compartiment"]: x for x in c.propager({"climat-extremes:saisons": 1.0}, 365)}
    assert e["ormuz:milieu"]["ampleur"] < 1.0 and e["ormuz:milieu"]["jour"] > 0      # influence : partielle, avec retard


def test_niveaux_d_organisation_et_passage():
    cat = ec.niveaux()
    assert {"mineral", "climat", "meteo", "animal", "personne", "entourage", "statut", "ideologie", "geopolitique"} <= set(cat["niveaux"])
    assert {"personne", "statut", "ideologie"} <= set(cat["facettes"])
    n = cat["niveaux"]
    assert ca.passage_de_niveau(0.9, "personne", "geopolitique", n, None) == 1.0       # assez fort pour changer d'échelle
    assert ca.passage_de_niveau(0.3, "personne", "geopolitique", n, None) == 0.2       # trop faible : amorti
    assert ca.passage_de_niveau(0.3, "animal", "animal", n, None) == 1.0               # au sein du même niveau


def test_chaine_de_fukuoka():
    c = ca.Carte()
    e = {x["compartiment"]: x for x in c.propager({"foret-et-sols-vivants:interventions": 1.0}, 3650)}
    assert e["foret-et-sols-vivants:rongeurs"]["sens"] == "baisse"
    assert e["foret-et-sols-vivants:predateurs"]["sens"] == "baisse"                 # le poison prive les prédateurs
    assert e["foret-et-sols-vivants:insectes_nematodes"]["sens"] == "hausse"         # moins d'oiseaux, plus d'insectes


def test_facettes_validees():
    f = {"theme": "t", "nom": "T", "declaration": {k: "x" for k in ("but", "limites", "observateur", "date") + ec.AXES},
         "compartiments": [{"id": "a", "organisation": "astral", "niveau": {**{k: "x" for k in ec.AXES}, "taille": "méso"},
                            "acteurs": [{"nom": "n", "taille": "micro", "facette": "aura"}]}], "relations": [], "ponts": []}
    e = " | ".join(ec.valider(f))
    assert "niveau d'organisation inconnu 'astral'" in e and "facette inconnue 'aura'" in e


def test_habitude_avant_crise_ormuz(tmp_path):
    """0.10.335 : l'habitude d'Ormuz vient de 2025 (même saison), pas des mois de crise."""
    from datetime import date, timedelta
    import carte as ca
    d0 = date(2026, 6, 1)
    crise = [((d0 + timedelta(days=i)).isoformat(), 2.0 + (i % 3)) for i in range(150)]
    ref = [((date(2025, 1, 1) + timedelta(days=i)).isoformat(), 40.0 + (i % 5)) for i in range(365)]
    base = ca.habitude_de_reference(crise, ref)
    assert len(base) == 61 and min(base) >= 40                                   # ± 30 jours autour du 28 octobre
    assert ca.habitude_de_reference(crise, ref[:10]) == []                       # trop court : habitude glissante


def test_serie_perimee_ignoree(tmp_path, monkeypatch):
    """0.10.349 : une série dont le dernier relevé est trop vieux ne donne pas l'état du jour."""
    import datetime as dt
    import adaptateurs as ad
    import carte as ca
    vieux = [((dt.date(2026, 1, 1) + dt.timedelta(days=i)).isoformat(), float(i % 7)) for i in range(60)]
    monkeypatch.setitem(ad.ADAPTATEURS, "meteo", lambda reg, point: vieux)
    c = ca.Carte(reg=tmp_path, calibration=None)
    c.aujourdhui = dt.date(2026, 11, 19)
    e = c.etat()
    perimes = [v for v in e.values() if "perime" in v and "z" not in v]
    assert perimes and all("meteo:" in v["perime"] for v in perimes)
    c2 = ca.Carte(reg=tmp_path, calibration=None)
    c2.aujourdhui = dt.date(2026, 3, 15)
    assert any("z" in v and str(v.get("adaptateur", "")).startswith("meteo:") for v in c2.etat().values())
