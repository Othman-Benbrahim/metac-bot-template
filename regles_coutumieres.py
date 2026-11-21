"""Règles coutumières par écosystème et par échelle (bot 0.10.371, ombre).

Lit et valide ecosystemes/regles-coutumieres.yaml. Décision d'auteur du 2026-11-19 : ne pas déduire, écrire les règles
telles qu'elles existent avec leur source ; sans source, « absence » et abstention. `python regles_coutumieres.py`
écrit registre/regles-coutumieres.md (bilan par espace, structure et statut ; liste des aides demandées à l'auteur).
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

import yaml

FICHIER = Path("ecosystemes") / "regles-coutumieres.yaml"
SORTIE = Path("registre") / "regles-coutumieres.md"
STRUCTURES = {"course", "seuil", "procedure", "evenement_rare", "maintien", "contexte"}   # contexte : mécanisme de fond
AXES = {"taille", "vitesse", "espace", "temps"}
# 2026-11-21 (carte de couverture v4) : vocabulaire fermé du périmètre d'une règle sourcée
REGIONS = {"monde", "afrique", "amerique_du_nord", "amerique_latine", "asie", "europe", "moyen_orient", "oceanie"}
PAYS = {"États-Unis": "amerique_du_nord", "Canada": "amerique_du_nord", "Mexique": "amerique_du_nord",
        "France": "europe", "Brésil": "amerique_latine", "Indonésie": "asie", "Japon": "asie", "Australie": "oceanie",
        "Inde": "asie", "Corée du Nord": "asie", "Royaume-Uni": "europe"}
STATUTS = {"source", "auteur", "absence"}


def regles() -> list[dict]:
    return (yaml.safe_load(FICHIER.read_text(encoding="utf-8")) or {}).get("regles") or []


def compartiments_des_fiches() -> dict[str, set]:
    """theme -> identifiants de ses compartiments (fiches d'écosystème)."""
    import glob
    out = {}
    for f in glob.glob("ecosystemes/*.yaml"):
        d = yaml.safe_load(open(f, encoding="utf-8"))
        if isinstance(d, dict) and d.get("theme") and d.get("compartiments"):
            out[d["theme"]] = {c.get("id") for c in d["compartiments"]}
    return out


def valider(rs: list[dict] | None = None, fiches: dict[str, set] | None = None) -> list[str]:
    rs = regles() if rs is None else rs
    fiches = compartiments_des_fiches() if fiches is None else fiches
    err, vus = [], set()
    for r in rs:
        i = r.get("id")
        if not i or i in vus:
            err.append(f"identifiant manquant ou double : {i}")
        vus.add(i)
        if r.get("structure") not in STRUCTURES:
            err.append(f"{i} : structure inconnue {r.get('structure')}")
        if (r.get("echelle") or {}).get("axe") not in AXES:
            err.append(f"{i} : axe d'échelle inconnu")
        st = r.get("statut")
        if st not in STATUTS:
            err.append(f"{i} : statut inconnu {st}")
        if st == "source" and not any((s or {}).get("url") for s in r.get("sources") or []):
            err.append(f"{i} : statut « source » sans lien")
        if st == "absence" and (r.get("parametres") or {}):
            err.append(f"{i} : une absence ne porte pas de paramètres")
        if st == "absence" and not r.get("aide"):
            err.append(f"{i} : absence sans aide demandée")
        if st == "source" and len(str(r.get("objet") or "")) < 10:   # 2026-11-21 : carte de couverture v4
            err.append(f"{i} : règle sourcée sans objet (l'événement qu'elle prédit)")
        if st == "source":
            per = r.get("perimetre")
            if not per or any(x not in REGIONS and x not in PAYS for x in per):
                err.append(f"{i} : périmètre absent ou inconnu {per}")
        for c in r.get("compartiments") or []:       # 2026-11-21 : lien règle → compartiment de fiche (piste écosystémique)
            f_, _, k_ = str(c).partition(":")
            if k_ not in fiches.get(f_, set()):
                err.append(f"{i} : compartiment inconnu {c}")
    return err


def principal() -> int:
    err = valider()
    if err:
        print("\n".join(err))
        return 1
    rs = regles()
    c = Counter((r["espace"], r["structure"], r["statut"]) for r in rs)
    l = ["# Règles coutumières : bilan", "", f"{len(rs)} règles ; " + ", ".join(f"{k} {v}" for k, v in Counter(r['statut'] for r in rs).items()) + ".", "",
         "| espace | structure | statut | n |", "|---|---|---|---|"]
    l += [f"| {e} | {s} | {st} | {n} |" for (e, s, st), n in sorted(c.items())]
    l += ["", "## Ce que l'auteur pourrait apporter (règles sans source)", ""]
    l += [f"- `{r['id']}` ({r['ecosysteme']}) : {r['aide']}" for r in rs if r["statut"] == "absence"]
    SORTIE.write_text("\n".join(l) + "\n", encoding="utf-8")
    print("\n".join(l))
    return 0


if __name__ == "__main__":
    sys.exit(principal())
