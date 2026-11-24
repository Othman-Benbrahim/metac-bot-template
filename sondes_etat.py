"""État des sondes de l'écosystème (preenregistrements/sondes-ecosysteme.md) : étalon glissant et règle d'arrêt.

1. Étalon : pour chaque sonde, k recalculé sur les questions résolues du corpus (registre/jugement-questions.jsonl)
   dont la date de résolution tombe dans les 182 jours précédant la date du calcul, et que la sonde lit ; grille −3…3,
   pas 0,1 ; base = part de oui du corpus hors groupe ; moins de 10 questions lues : k = 0 (la sonde se tait).
2. Règle d'arrêt (e-valeurs) sur les questions du bot résolues où la sonde a joué (journal-sondes.jsonl, dernière ligne
   par question ; issues.jsonl) : log E = Σ log(p_sonde(issue) / p_base(issue)) ; log E ≤ −ln 20 → débranchée
   (définitivement, sauf décision de l'auteur) ; ≥ ln 20 → plafond 10 points ; ≥ ln 400 → 15 points.
Écrit ecosystemes/sondes-etat.json.

    python sondes_etat.py [AAAA-MM-JJ]
"""
from __future__ import annotations

import datetime as dt
import json
import math
import sys
from collections import Counter
from pathlib import Path

import ecosysteme_couche as ecc
import sondes as so

ICI = Path(__file__).resolve().parent
REG = ICI / "registre"


def _groupe(t: str) -> str:
    from mise_au_point.procedure_inertie import groupe
    return groupe(t)


def _ll(p, y):
    p = min(max(p, .02), .98)
    return -math.log(p if y else 1 - p)


def etalon(S: so.Sondes, jour: dt.date) -> dict:
    vus, T = set(), []
    for l in (REG / "jugement-questions.jsonl").read_text(encoding="utf-8").splitlines():
        q = json.loads(l)
        if q["titre"] in vus or str(q.get("issue")) not in ("0", "1") or not q.get("resolue_le"):
            continue
        vus.add(q["titre"])
        T.append(q)
    tot = sum(int(q["issue"]) for q in T)
    gr = Counter(_groupe(q["titre"]) for q in T)
    go = Counter(_groupe(q["titre"]) for q in T if q["issue"] == "1")
    fen = [q for q in T if jour - dt.timedelta(days=182) <= dt.date.fromisoformat(q["resolue_le"][:10]) < jour]
    lus = {n: [] for n in so.NOMS}
    for q in fen:
        g = _groupe(q["titre"])
        p0 = (tot - go[g]) / max(1, len(T) - gr[g])
        L = S.lire(q["titre"], float(q.get("horizon") or 90), dt.date.fromisoformat(q["jeu"]))
        for n, x in L.items():
            lus[n].append((p0, x["d"], x["sens"], int(q["issue"])))
    grille = [round(-3 + 0.1 * i, 1) for i in range(61)]
    out = {}
    for n, X in lus.items():
        if len(X) < 10:
            out[n] = {"k": 0.0, "lues": len(X)}
            continue
        perte = lambda k: sum(_ll(ecc.deplacer(p0, d, s, k), y) for p0, d, s, y in X) / len(X)
        k = min(grille, key=perte)
        out[n] = {"k": k, "lues": len(X), "perte_base": round(perte(0), 4), "perte_k": round(perte(k), 4)}
    return {"fenetre": [str(jour - dt.timedelta(days=182)), str(jour)], "questions_fenetre": len(fen), "sondes": out}


def e_valeurs() -> dict:
    issues = {}
    f = REG / "issues.jsonl"
    if f.exists():
        for l in f.read_text(encoding="utf-8").splitlines():
            if l.strip():
                x = json.loads(l)
                if "issue" in x:
                    issues[str(x["question_id"])] = int(x["issue"])
    dernier = {}
    f = REG / "journal-sondes.jsonl"
    if f.exists():
        for l in f.read_text(encoding="utf-8").splitlines():
            if l.strip():
                x = json.loads(l)
                dernier[str(x["question_id"])] = x
    out = {n: {"log_e": 0.0, "resolues": 0} for n in so.NOMS}
    for q, x in dernier.items():
        if q not in issues:
            continue
        y, pb = issues[q], min(max(float(x["p_base"]), .001), .999)
        for n, v in (x.get("sondes") or {}).items():
            ps = min(max(float(v["p_sonde"]), .001), .999)
            out[n]["log_e"] += math.log((ps if y else 1 - ps) / (pb if y else 1 - pb))
            out[n]["resolues"] += 1
    return out


def principal() -> int:
    jour = dt.date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else dt.date.today()
    precedent = so.etat()
    S = so.Sondes()
    et = etalon(S, jour)
    ev = e_valeurs()
    sondes = {}
    for n in so.NOMS:
        avant = (precedent.get("sondes") or {}).get(n) or {}
        actif = avant.get("actif", True)
        plafond = float(avant.get("plafond", so.PLAFOND_DEPART))
        le = ev[n]["log_e"]
        if le <= -math.log(20):
            actif = False
        elif le >= math.log(400):
            plafond = max(plafond, 0.15)
        elif le >= math.log(20):
            plafond = max(plafond, 0.10)
        sondes[n] = {"actif": actif, "plafond": plafond, "k": et["sondes"][n]["k"], "etalon": et["sondes"][n],
                     "log_e": round(le, 4), "resolues": ev[n]["resolues"]}
    etat = {"calcule_le": str(jour), "fenetre_etalon": et["fenetre"], "questions_fenetre": et["questions_fenetre"],
            "sondes": sondes, "procedure": "preenregistrements/sondes-ecosysteme.md"}
    so.ETAT.write_text(json.dumps(etat, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(etat, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(principal())
