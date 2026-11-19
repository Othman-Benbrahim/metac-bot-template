"""Modélisation par écosystèmes : une fiche compartimentée par thème, et le schéma d'interrelations qui les relie.

Décision de l'auteur, 2026-11-19, 3 h 44 : « une fiche compartimentée pour l'ensemble des sujets traités, chaque facteur
compris à son niveau d'action ; chaque thème a sa compartimentation, ses relations et ses ponts avec des thèmes
connexes ; par un schéma d'interrelation nourri, on schématisera petit à petit quelque chose de cohérent ».
Principe (2026-11-19, 3 h 39) : chaque fiche est UN écosystème — un découpage déclaré par un observateur pour un but —,
pas L'écosystème. Les fiches se superposent et se partagent des éléments ; aucune n'est « la bonne ».

Fiches : ecosystemes/<theme>.yaml (format dans ecosystemes/LISEZMOI.md). Ce module les valide, déduit ce qui peut
l'être (forme d'une relation à partir des deux effets), assemble le schéma global et écrit :
- registre/ecosystemes-schema.json : nœuds (thème:compartiment), relations, ponts ;
- registre/ecosystemes-a-faire.md : ponts vers des thèmes encore sans fiche, compartiments sans trace, relations à
  vérifier — la liste de travail.
Aucun appel réseau, aucun modèle ; rien n'entre dans le bot.

    python ecosystemes.py            # valide et assemble
    python ecosystemes.py --mermaid ormuz   # schéma Mermaid d'une fiche
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

DOSSIER = Path("ecosystemes")
SCHEMA = Path("registre/ecosystemes-schema.json")
A_FAIRE = Path("registre/ecosystemes-a-faire.md")

AXES = ("espace", "temps", "vitesse", "taille")
EFFETS = ("+", "-", "0", "±")
FORMES = ("competition", "predation", "mutualisme", "commensalisme", "amensalisme", "neutralisme", "forcage",
          "contrainte", "ambivalent")
STYLES = ("donnant-donnant", "rancunier", "conciliant", "indifferent", "inconnu")
STATUTS = ("a_verifier", "verifie", "conteste")
TRACES = ("collecte", "a_brancher", "fermee", "inconnue")
FORCES = ("faible", "moyenne", "forte", "inconnue")
# 0.10.315 (idée de l'auteur, 2026-11-19, 3 h 56) : l'INTENSITÉ. La force d'une relation n'est pas fixe : plus
# l'intensité du moment est forte (tension, chaleur, rareté, attention), plus la relation transmet. On distingue :
# - force : ce que la relation transmet d'ordinaire (structurel) ;
# - intensite.mesure : ce qui dit l'intensité du moment (une trace) ;
# - intensite.regle : comment la force varie avec l'intensité.
REGLES_INTENSITE = ("proportionnelle", "seuil", "saturation", "hysteresis", "inconnue")


def forme_deduite(effet: str, retour: str | None) -> str:
    """Forme écologique d'après l'effet de la source sur la cible et le retour de la cible sur la source.
    Sans retour (élément non vivant, influence à sens unique) : forçage."""
    if retour is None:
        return "forcage"
    paire = (effet, retour)
    table = {("-", "-"): "competition", ("+", "+"): "mutualisme", ("+", "0"): "commensalisme",
             ("0", "+"): "commensalisme", ("-", "0"): "amensalisme", ("0", "-"): "amensalisme",
             ("0", "0"): "neutralisme", ("-", "+"): "predation", ("+", "-"): "predation"}
    return table.get(paire, "ambivalent")


def charger(dossier: Path = DOSSIER) -> dict[str, dict]:
    out = {}
    for f in sorted(dossier.glob("*.yaml")):
        d = yaml.safe_load(f.read_text(encoding="utf-8"))
        out[d["theme"]] = d
    return out


def valider(fiche: dict) -> list[str]:
    err = []
    t = fiche.get("theme", "?")
    for k in ("theme", "nom", "declaration", "compartiments", "relations"):
        if k not in fiche:
            err.append(f"{t} : clé « {k} » absente")
    dec = fiche.get("declaration") or {}
    for k in ("but", "limites", "observateur", "date") + AXES:
        if k not in dec:
            err.append(f"{t} : déclaration sans « {k} » (un écosystème est un découpage déclaré)")
    ids = [c.get("id") for c in fiche.get("compartiments") or []]
    if len(ids) != len(set(ids)):
        err.append(f"{t} : identifiants de compartiments en double")
    for c in fiche.get("compartiments") or []:
        for a in AXES:
            if a not in (c.get("niveau") or {}):
                err.append(f"{t}:{c.get('id')} : niveau d'action sans « {a} »")
        for tr in c.get("traces") or []:
            if tr.get("statut") not in TRACES:
                err.append(f"{t}:{c.get('id')} : statut de trace inconnu {tr.get('statut')!r}")
    for i, r in enumerate(fiche.get("relations") or []):
        lab = f"{t} relation {i + 1} ({r.get('de')} → {r.get('vers')})"
        for bout in ("de", "vers"):
            if r.get(bout) not in ids:
                err.append(f"{lab} : « {r.get(bout)} » n'est pas un compartiment de la fiche")
        if r.get("effet") not in EFFETS:
            err.append(f"{lab} : effet {r.get('effet')!r} hors de {EFFETS}")
        if r.get("retour") is not None and r.get("retour") not in EFFETS:
            err.append(f"{lab} : retour {r.get('retour')!r} hors de {EFFETS}")
        if r.get("forme") is not None and r.get("forme") not in FORMES:
            err.append(f"{lab} : forme {r.get('forme')!r} hors de {FORMES}")
        if r.get("style") is not None and r.get("style") not in STYLES:
            err.append(f"{lab} : style {r.get('style')!r} hors de {STYLES}")
        if r.get("statut") not in STATUTS:
            err.append(f"{lab} : statut {r.get('statut')!r} hors de {STATUTS}")
        if r.get("force", "inconnue") not in FORCES:
            err.append(f"{lab} : force {r.get('force')!r} hors de {FORCES}")
        it = r.get("intensite")
        if it is not None:
            if not isinstance(it, dict) or not it.get("mesure"):
                err.append(f"{lab} : intensité sans « mesure » (ce qui dit l'intensité du moment)")
            elif it.get("regle") not in REGLES_INTENSITE:
                err.append(f"{lab} : règle d'intensité {it.get('regle')!r} hors de {REGLES_INTENSITE}")
    for p in fiche.get("ponts") or []:
        if p.get("depuis") not in ids:
            err.append(f"{t} pont : « {p.get('depuis')} » n'est pas un compartiment de la fiche")
        if ":" not in str(p.get("vers", "")):
            err.append(f"{t} pont : « vers » doit s'écrire theme:compartiment")
    return err


def assembler(fiches: dict[str, dict]) -> dict:
    noeuds, liens, ponts = [], [], []
    for t, f in fiches.items():
        for c in f["compartiments"]:
            noeuds.append({"id": f"{t}:{c['id']}", "theme": t, "nom": c.get("nom", c["id"]), "niveau": c["niveau"],
                           "traces": c.get("traces") or []})
        for r in f["relations"]:
            forme = r.get("forme") or forme_deduite(r["effet"], r.get("retour"))
            liens.append({"de": f"{t}:{r['de']}", "vers": f"{t}:{r['vers']}", "forme": forme,
                          "forme_ecrite": r.get("forme") is not None, **{k: r.get(k) for k in
                          ("effet", "retour", "style", "delai", "force", "intensite", "coupure", "statut", "source", "texte")}})
        for p in f.get("ponts") or []:
            cible_theme, cible_comp = str(p["vers"]).split(":", 1)
            existe = cible_theme in fiches and any(c["id"] == cible_comp for c in fiches[cible_theme]["compartiments"])
            ponts.append({"de": f"{t}:{p['depuis']}", "vers": p["vers"], "nature": p.get("nature"), "resolu": existe})
    return {"themes": sorted(fiches), "noeuds": noeuds, "relations": liens, "ponts": ponts,
            "bilan": {"themes": len(fiches), "compartiments": len(noeuds), "relations": len(liens), "ponts": len(ponts),
                      "ponts_en_attente": sum(not p["resolu"] for p in ponts),
                      "relations_a_verifier": sum(l["statut"] == "a_verifier" for l in liens),
                      "relations_avec_intensite": sum(bool(l.get("intensite")) for l in liens),
                      "compartiments_sans_trace_collectee": sum(not any(tr.get("statut") == "collecte" for tr in n["traces"])
                                                               for n in noeuds)}}


def a_faire(s: dict) -> str:
    l = ["# Écosystèmes : liste de travail (écrite par ecosystemes.py, ne pas retoucher)", "",
         f"Bilan : {s['bilan']}", "", "## Thèmes à écrire (ponts en attente)"]
    attente: dict[str, list[str]] = {}
    for p in s["ponts"]:
        if not p["resolu"]:
            attente.setdefault(p["vers"].split(":")[0], []).append(f"{p['de']} → {p['vers']} ({p.get('nature') or ''})")
    for t in sorted(attente, key=lambda t: -len(attente[t])):
        l.append(f"- **{t}** ({len(attente[t])} pont(s)) : " + " ; ".join(attente[t]))
    l += ["", "## Compartiments sans trace collectée (à notre portée ? ou oubliés ?)"]
    for n in s["noeuds"]:
        if not any(tr.get("statut") == "collecte" for tr in n["traces"]):
            prop = [f"{tr.get('source')} ({tr.get('statut')})" for tr in n["traces"]]
            l.append(f"- {n['id']} : " + (", ".join(prop) if prop else "aucune trace connue"))
    l += ["", "## Relations à vérifier sur une source relue"]
    for r in s["relations"]:
        if r["statut"] == "a_verifier":
            l.append(f"- {r['de']} → {r['vers']} [{r['forme']}] {r.get('texte') or ''}")
    return "\n".join(l) + "\n"


def mermaid(fiche: dict) -> str:
    l = ["flowchart LR"]
    for c in fiche["compartiments"]:
        l.append(f'  {c["id"]}["{c.get("nom", c["id"])}"]')
    fleche = {"competition": "<-.->", "mutualisme": "<==>", "predation": "-->", "forcage": "==>", "contrainte": "-.->"}
    for r in fiche["relations"]:
        forme = r.get("forme") or forme_deduite(r["effet"], r.get("retour"))
        l.append(f'  {r["de"]} {fleche.get(forme, "-->")}|{forme}| {r["vers"]}')
    return "\n".join(l)


def principal(args) -> int:
    fiches = charger()
    erreurs = [e for f in fiches.values() for e in valider(f)]
    if erreurs:
        print("\n".join(erreurs))
        return 1
    if args.mermaid:
        print(mermaid(fiches[args.mermaid]))
        return 0
    s = assembler(fiches)
    SCHEMA.write_text(json.dumps(s, ensure_ascii=False, indent=1), encoding="utf-8")
    A_FAIRE.write_text(a_faire(s), encoding="utf-8")
    print(json.dumps(s["bilan"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("--mermaid")
    sys.exit(principal(a.parse_args()))
