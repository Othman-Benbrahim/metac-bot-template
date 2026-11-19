"""0.10.313 : fiches d'écosystèmes (format, déduction des formes, assemblage)."""
from pathlib import Path

import ecosystemes as ec


def test_formes_deduites():
    assert ec.forme_deduite("-", "-") == "competition" and ec.forme_deduite("+", "+") == "mutualisme"
    assert ec.forme_deduite("-", "+") == "predation" and ec.forme_deduite("+", None) == "forcage"
    assert ec.forme_deduite("±", "+") == "ambivalent"


def test_toutes_les_fiches_du_depot_sont_valides():
    fiches = ec.charger(Path("ecosystemes"))
    assert "ormuz" in fiches
    erreurs = [e for f in fiches.values() for e in ec.valider(f)]
    assert erreurs == [], erreurs


def test_validation_attrape_les_fautes():
    f = {"theme": "t", "nom": "T", "declaration": {"but": "b"}, "compartiments": [{"id": "a", "niveau": {}}],
         "relations": [{"de": "a", "vers": "zz", "effet": "?", "statut": "peut-etre"}], "ponts": [{"depuis": "a", "vers": "x"}]}
    e = " | ".join(ec.valider(f))
    for attendu in ("déclaration sans « limites »", "niveau d'action sans « vitesse »", "« zz » n'est pas", "effet '?'",
                    "statut 'peut-etre'", "theme:compartiment"):
        assert attendu in e


def test_assemblage_et_ponts():
    fiches = {
        "a": {"theme": "a", "compartiments": [{"id": "x", "niveau": {}, "traces": [{"source": "s", "statut": "collecte"}]}],
              "relations": [], "ponts": [{"depuis": "x", "vers": "b:y"}, {"depuis": "x", "vers": "c:z"}]},
        "b": {"theme": "b", "compartiments": [{"id": "y", "niveau": {}}],
              "relations": [{"de": "y", "vers": "y", "effet": "+", "statut": "a_verifier"}], "ponts": []}}
    s = ec.assembler(fiches)
    assert s["bilan"]["ponts_en_attente"] == 1 and s["relations"][0]["forme"] == "forcage"
    assert s["bilan"]["compartiments_sans_trace_collectee"] == 1
    assert "**c**" in ec.a_faire(s)


def test_intensite():
    base = {"theme": "t", "nom": "T", "declaration": {k: "x" for k in ("but", "limites", "observateur", "date") + ec.AXES},
            "compartiments": [{"id": "a", "niveau": {k: "x" for k in ec.AXES}}], "ponts": []}
    ok = dict(base, relations=[{"de": "a", "vers": "a", "effet": "+", "statut": "a_verifier",
                                "intensite": {"mesure": "tension", "regle": "seuil"}}])
    assert ec.valider(ok) == []
    ko = dict(base, relations=[{"de": "a", "vers": "a", "effet": "+", "statut": "a_verifier", "intensite": {"regle": "seuil"}}])
    assert any("sans « mesure »" in e for e in ec.valider(ko))
    assert ec.assembler({"t": ok})["bilan"]["relations_avec_intensite"] == 1
