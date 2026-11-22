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
            "compartiments": [{"id": "a", "niveau": {**{k: "x" for k in ec.AXES}, "taille": "méso"}}], "ponts": []}
    ok = dict(base, relations=[{"de": "a", "vers": "a", "effet": "+", "statut": "a_verifier",
                                "intensite": {"mesure": "tension", "regle": "seuil"}}])
    assert ec.valider(ok) == []
    ko = dict(base, relations=[{"de": "a", "vers": "a", "effet": "+", "statut": "a_verifier", "intensite": {"regle": "seuil"}}])
    assert any("sans « mesure »" in e for e in ec.valider(ko))
    assert ec.assembler({"t": ok})["bilan"]["relations_avec_intensite"] == 1


def test_virgule_non_protegee_refusee():
    import yaml
    f = yaml.safe_load('theme: t\nrelations:\n  - {de: a, vers: b, effet: "+", statut: a_verifier, texte: saisies, menaces}\n')
    assert any("clé inconnue" in e for e in ec.cles_inconnues(f))


def test_code_odd_verifie():
    # 0.10.420 : un code ODD de trace doit figurer dans ecosystemes/odd.yaml (vérifié dans le cadre officiel)
    assert ec.odd()["1.1.1"].startswith("Proportion of the population living below the international poverty line")
    f = {"theme": "t", "nom": "T", "compartiments": [{"id": "a", "niveau": {}, "traces": [
        {"source": "s", "statut": "a_brancher", "odd": ["1.1.1", "99.9.9"]}]}], "relations": []}
    e = " | ".join(ec.valider(f))
    assert "'99.9.9' absent" in e and "'1.1.1'" not in e


def test_ponts_transversaux_valides():
    # 0.10.435 : chaque pont transversal relie deux compartiments existants de deux fiches, par un canal déclaré
    f = ec.charger()
    assert ec.erreurs_transversaux(f) == []
    ponts, canaux = ec.ponts_transversaux()
    assert len(ponts) >= 150 and "energie" in canaux
    # ils sont bien ajoutés aux ponts de la fiche de départ, avec leur canal
    assert any(p.get("canal") == "energie" for p in f["energie-mondiale"]["ponts"])
    assert not any(p.get("canal") for p in ec.charger(transversaux=False)["energie-mondiale"].get("ponts") or [])


def test_trois_sortes_de_ponts():
    # 0.10.443 (filtre « causes », décision de l'auteur du 2026-11-22) : cause (influence), même chose, voisinage
    assert ec.TYPES_PONT == ("meme", "influence", "voisinage")
    f = ec.charger()
    types = {p.get("type", "influence") for x in f.values() for p in x.get("ponts") or []}
    assert types == {"meme", "influence", "voisinage"}


def test_cycles_et_tensions():
    """0.10.461 : cycles (mécanisme obligatoire, période et sources seulement pour « identifie ») et tensions (deux
    pôles, stock pour une tension cumulative, seuil avec hystérésis)."""
    import ecosystemes as eco
    base = {"theme": "t", "nom": "n", "declaration": {}, "relations": [],
            "compartiments": [{"id": "a"}, {"id": "b"}]}
    ok = dict(base, cycles=[{"id": "c", "sorte": "force", "mecanisme": "parce que"}],
              tensions=[{"id": "x", "forme": "cumulative", "entre": ["a", "b"], "stock": "b", "module_par": ["c"],
                         "seuil": {"hysteresis": "oui"}}])
    assert not eco.erreurs_cycles_tensions(ok, {"a", "b"})
    sans_meca = dict(base, cycles=[{"id": "c", "sorte": "force"}])
    assert any("mécanisme" in e for e in eco.erreurs_cycles_tensions(sans_meca, {"a", "b"}))
    identifie_nu = dict(base, cycles=[{"id": "c", "sorte": "force", "mecanisme": "m", "statut": "identifie"}])
    assert any("identifie" in e for e in eco.erreurs_cycles_tensions(identifie_nu, {"a", "b"}))
    sans_stock = dict(base, tensions=[{"id": "x", "forme": "cumulative", "entre": ["a", "b"]}])
    assert any("stock" in e for e in eco.erreurs_cycles_tensions(sans_stock, {"a", "b"}))
    un_pole = dict(base, tensions=[{"id": "x", "forme": "oppositionnelle", "entre": ["a"]}])
    assert any("deux pôles" in e for e in eco.erreurs_cycles_tensions(un_pole, {"a", "b"}))
    fiches = eco.charger()
    eau = fiches["eau-douce-potable"]
    assert len(eau["cycles"]) == 3 and len(eau["tensions"]) == 3
