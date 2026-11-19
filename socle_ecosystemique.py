"""Socle du programme écosystémique (bot 0.10.372, ombre).

Assemble, pour chaque fiche, ce que le programme sait déjà sans le redéduire : règles coutumières de son espace (les
règles « monde » valent pour toutes et sont listées une fois), types d'inconnu de ses compartiments (inconnus.py), nature de ses traces
(classer_series.py), et, pour tout le programme, l'état des briques (registre/briques.json) et les mécanismes à
connaître (ecosystemes/mecanismes.yaml). N'invente rien : une fiche sans règle pour son espace le dit.
`python socle_ecosystemique.py` écrit registre/socle-ecosystemique.json et .md.
"""
from __future__ import annotations

import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import yaml

import ecosystemes as ec
import inconnus
import regles_coutumieres as rc

REG = Path("registre")
SORTIE_JSON, SORTIE_MD = REG / "socle-ecosystemique.json", REG / "socle-ecosystemique.md"
MECANISMES = ec.DOSSIER / "mecanismes.yaml"
# mots du champ « espace » d'une fiche → espace des règles coutumières (rattachement écrit, revu à la main)
MOTS = {"amerique_du_nord": ["états-unis", "etats-unis", "amérique du nord"],
        "europe": ["europ", "atlantique nord", "ukraine", "russie"],
        "afrique": ["afrique", "nil"],
        "asie": ["chine", "asie", "inde", "iran", "pacifique", "malacca", "taïwan"],
        "amerique_latine": ["amérique latine", "argentine", "amériques"],
        "oceanie": ["océanie", "australie"]}


def mecanismes() -> list[dict]:
    return (yaml.safe_load(MECANISMES.read_text(encoding="utf-8")) or {}).get("mecanismes") or []


def espaces(fiche: dict) -> list[str]:
    t = str((fiche.get("declaration") or {}).get("espace") or "").lower()
    return [k for k, ms in MOTS.items() if any(m in t for m in ms)]


def _ipu() -> dict:
    import ipu_parlements as ipu
    cs = ipu.chambres()
    return {"chambres": len(cs), "suspendues": sorted({c["pays"] for c in cs if c["statut"] == "Suspendu"}),
            "non_elues_directement": sum(c["designation"] != "Scrutin direct" for c in cs)}


def assembler() -> dict:
    fiches = ec.charger(ec.DOSSIER)
    regles = [r for r in rc.regles()]
    inc = inconnus.table(fiches)
    natures = defaultdict(Counter)
    f_nat = REG / "nature-des-series.csv"
    if f_nat.exists():
        for l in csv.DictReader(f_nat.open(encoding="utf-8")):
            natures[l["fiche"]][l["nature"]] += 1
    briques = json.loads((REG / "briques.json").read_text(encoding="utf-8")) if (REG / "briques.json").exists() else {}
    out = {}
    for t, f in sorted(fiches.items()):
        es = espaces(f)
        rs = [r for r in regles if r["espace"] in es]
        comp = {k.split(":", 1)[1]: v["types"] for k, v in inc.items() if k.startswith(t + ":")}
        out[t] = {"espaces": es,
                  "regles": [{"id": r["id"], "structure": r["structure"], "statut": r["statut"]} for r in rs],
                  "abstentions": [r["id"] for r in rs if r["statut"] == "absence"],
                  "inconnus": dict(Counter(x for v in comp.values() for x in v)),
                  "natures": dict(natures.get(t, {})),
                  "declarations": natures.get(t, {}).get("declaration", 0)}
    return {"fiches": out,
            "briques": {s: {"axe": v.get("axe"), "statut": (v.get("ensemble") or {}).get("statut")}
                        for s, v in (briques.get("structures") or {}).items()},
            "mecanismes": [{"id": m["id"], "nom": m["nom"], "garde": m["garde"]} for m in mecanismes()],
            "regles": dict(Counter(r["statut"] for r in regles)),
            "parlements_ipu": _ipu(),
            "regles_monde": [r["id"] for r in regles if r["espace"] == "monde"]}


def markdown(s: dict) -> str:
    L = ["# Socle du programme écosystémique", "",
         f"Règles coutumières : {s['regles']} ; valables partout : {', '.join(s['regles_monde'])}. Briques : "
         + ", ".join(f"{k} ({v['axe']}) {v['statut']}" for k, v in s["briques"].items()) + ".", "",
         "| Fiche | Espaces des règles | Règles (dont absences) | Inconnus | Natures des traces |", "|---|---|---|---|---|"]
    for t, v in s["fiches"].items():
        L.append(f"| {t} | {', '.join(v['espaces']) or '—'} | {len(v['regles'])} ({len(v['abstentions'])}) | "
                 f"{', '.join(f'{k} {n}' for k, n in v['inconnus'].items()) or '—'} | "
                 f"{', '.join(f'{k} {n}' for k, n in v['natures'].items()) or '—'} |")
    p = s["parlements_ipu"]
    L += ["", f"Parlements (IPU Parline) : {p['chambres']} chambres, {p['non_elues_directement']} non élues au suffrage direct ; "
          f"suspendues (inertie des régimes fermés) : {', '.join(p['suspendues'])}."]
    L += ["", "## Mécanismes à connaître (non mesurables) et leur garde", ""]
    L += [f"- **{m['nom']}** : {m['garde']}" for m in s["mecanismes"]]
    return "\n".join(L) + "\n"


def principal() -> int:
    err = rc.valider()
    ids = [m["id"] for m in mecanismes()]
    if len(ids) != len(set(ids)) or not all(m.get("garde") for m in mecanismes()):
        err.append("mécanismes : identifiant en double ou garde manquante")
    if err:
        print("\n".join(err))
        return 1
    s = assembler()
    SORTIE_JSON.write_text(json.dumps(s, ensure_ascii=False, indent=1), encoding="utf-8")
    SORTIE_MD.write_text(markdown(s), encoding="utf-8")
    print(f"{len(s['fiches'])} fiches ; {sum(1 for v in s['fiches'].values() if v['espaces'])} rattachées à un espace ; "
          f"{len(s['mecanismes'])} mécanismes")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
