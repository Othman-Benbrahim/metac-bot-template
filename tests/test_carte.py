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
