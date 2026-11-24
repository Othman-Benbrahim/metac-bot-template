"""Inventaire de rendement de la carte (2026-11-24, décision de l'auteur à 12 h 51) : où la carte peut produire un
résultat mesurable sur les questions de prévision. Descriptif, sans modèle de langue, rien n'entre dans le bot.

Croise :
- les questions résolues du corpus (registre/jugement-questions.jsonl : titre, source, date, issue) ;
- les compartiments des fiches (ecosystemes/*.yaml) et leurs traces numériques (traces à adaptateur = série lue par le
  bot) ;
- les termes validés par l'auteur (lecteur-local/listes/valides.txt) et leurs rattachements aux compartiments.

Rattachement d'une question à un compartiment : un terme validé, rattaché à ce compartiment, apparaît dans le titre
(mot entier, sans casse, termes de 4 lettres au moins). Les rattachements à un espace (« espace:pays:… ») sont ignorés.
Les questions reposées (même titre) comptent une fois.

    python mise_au_point/inventaire_rendement.py ../lecteur-local/listes/valides.txt
"""
from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import yaml

ICI = Path(__file__).resolve().parent.parent
REG = ICI / "registre"


def termes(f: Path) -> dict[str, set[str]]:
    out = defaultdict(set)
    for l in f.read_text(encoding="utf-8").splitlines():
        p = [x.strip() for x in l.split("|")]
        if len(p) < 4 or p[0] != "+" or len(p[1]) < 4:
            continue
        for r in p[3].split(";"):
            r = r.strip()
            if r and not r.startswith("espace:") and r.count(":") == 1:
                out[p[1]].add(r)
    return out


def compartiments() -> dict[str, dict]:
    out = {}
    for f in sorted((ICI / "ecosystemes").glob("*.yaml")):
        d = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
        if not isinstance(d, dict) or "compartiments" not in d:
            continue
        for c in d.get("compartiments") or []:
            if not isinstance(c, dict) or not c.get("id"):
                continue
            tr = c.get("traces") or []
            out[f"{d.get('theme', f.stem)}:{c['id']}"] = {
                "nom": c.get("nom", ""),
                "series": sorted({t["adaptateur"] for t in tr if isinstance(t, dict) and t.get("adaptateur")}),
                "traces_collectees": sum(1 for t in tr if isinstance(t, dict) and t.get("statut") == "collecte")}
    return out


def principal() -> int:
    fv = Path(sys.argv[1]) if len(sys.argv) > 1 else ICI.parent / "lecteur-local" / "listes" / "valides.txt"
    T = termes(fv)
    motifs = [(re.compile(r"(?<![\w-])" + re.escape(t) + r"(?![\w-])", re.I), r) for t, r in T.items()]
    C = compartiments()
    vus, qs = set(), []
    for l in (REG / "jugement-questions.jsonl").read_text(encoding="utf-8").splitlines():
        q = json.loads(l)
        if q["titre"] in vus or str(q.get("issue")) not in ("0", "1"):
            continue
        vus.add(q["titre"])
        qs.append(q)
    par = defaultdict(list)
    sans = 0
    for q in qs:
        cs = set()
        for m, rs in motifs:
            if m.search(q["titre"]):
                cs |= {r for r in rs if r in C}
        if not cs:
            sans += 1
        for c in cs:
            par[c].append(q)
    lignes = []
    for c, info in C.items():
        L = par.get(c, [])
        n = len(L)
        lignes.append({"compartiment": c, "nom": info["nom"], "questions": n,
                       "metaculus": sum(1 for q in L if q["source"] == "metaculus"),
                       "oui": round(sum(int(q["issue"]) for q in L) / n, 3) if n else None,
                       "premiere": min((str(q.get("jeu") or "") for q in L), default=None),
                       "series": info["series"], "n_series": len(info["series"])})
    lignes.sort(key=lambda x: (-(x["questions"] > 0 and x["n_series"] > 0), -x["questions"]))
    seuils = {"q>=30 et série": sum(1 for x in lignes if x["questions"] >= 30 and x["n_series"]),
              "q>=100 et série": sum(1 for x in lignes if x["questions"] >= 100 and x["n_series"]),
              "q>=30 sans série": sum(1 for x in lignes if x["questions"] >= 30 and not x["n_series"]),
              "série sans question": sum(1 for x in lignes if x["n_series"] and not x["questions"]),
              "ni l'un ni l'autre": sum(1 for x in lignes if not x["n_series"] and not x["questions"])}
    res = {"questions": len(qs), "questions_sans_compartiment": sans, "compartiments": len(C), "termes": len(T),
           "classes": seuils, "lignes": lignes}
    (REG / "inventaire-rendement.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(qs)} questions distinctes, {sans} sans compartiment ; {len(C)} compartiments ; {len(T)} termes")
    print(seuils)
    for x in lignes[:40]:
        print(f"{x['questions']:5} q ({x['metaculus']:4} M) oui={x['oui']} séries={x['n_series']} {x['compartiment']} {x['series'][:3]}")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
