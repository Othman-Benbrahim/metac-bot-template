"""Contagion simple ou complexe des manifestations entre voisins : calcul unique du préenregistrement
preenregistrements/contagion-complexe-manifestations.md (sha256 83fbcd7ddab848a8), qu'il suit sans le changer.

Écrit registre/contagion-complexe.json.
"""
from __future__ import annotations

import csv
import datetime as dt
import json
import random
import statistics as st
from collections import defaultdict
from pathlib import Path

ICI = Path(__file__).resolve().parent.parent
REG = ICI / "registre"
GRAINE = 20261125


def charger():
    jours = [l.strip() for l in (REG / "gdelt-jours.txt").read_text().split() if l.strip()]
    jours = sorted(set(jours))
    comptes = defaultdict(dict)
    with (REG / "gdelt-manifestations.csv").open(encoding="utf-8") as h:
        for r in csv.DictReader(h):
            try:
                comptes[r["pays"]][r["jour"]] = float(r["manifestations"] or 0)
            except ValueError:
                pass
    voisins = json.loads((REG / "voisins.json").read_text(encoding="utf-8"))
    return jours, comptes, voisins


def pics_par_semaine(jours, comptes):
    """{pays: {semaine: 1 si au moins un pic}} ; semaines jugées seulement à partir du 91e jour couvert."""
    out = {}
    for p, c in comptes.items():
        serie = [c.get(j, 0.0) for j in jours]
        sem = defaultdict(int)
        for i in range(90, len(jours)):
            med = st.median(serie[i - 90:i])
            s = dt.date.fromisoformat(jours[i]).isocalendar()
            cle = f"{s[0]}-{s[1]:02d}"
            sem[cle] = max(sem[cle], int(serie[i] >= max(5.0, 3.0 * med)))
        out[p] = dict(sem)
    return out


def semaine_prec(cle: str) -> str:
    a, w = map(int, cle.split("-"))
    d = dt.date.fromisocalendar(a, w, 1) - dt.timedelta(days=7)
    s = d.isocalendar()
    return f"{s[0]}-{s[1]:02d}"


def unites(pics, vois):
    """Liste (pays, Y, k) : pays-semaines sans pic la semaine précédente ; k = voisins distincts avec pic la veille."""
    out = []
    for p, sem in pics.items():
        vs = [v for v in vois.get(p, []) if v in pics]
        if not vs:
            continue
        for cle, y in sem.items():
            pr = semaine_prec(cle)
            if pr not in sem or sem[pr]:
                continue
            k = sum(1 for v in vs if pics[v].get(pr, 0))
            out.append((p, y, k))
    return out


def taux(U, pays_poids=None):
    n = defaultdict(float)
    y = defaultdict(float)
    for p, yy, k in U:
        w = 1.0 if pays_poids is None else pays_poids.get(p, 0)
        if not w:
            continue
        kk = min(k, 3)
        n[kk] += w
        y[kk] += w * yy
    return {k: (y[k] / n[k] if n[k] else None) for k in range(4)}, dict(n)


def pseudo_voisins(pays, vrais, rng):
    out = {}
    for p in pays:
        nv = len([v for v in vrais.get(p, []) if v in pays])
        if not nv:
            continue
        cand = [q for q in pays if q != p and q not in vrais.get(p, [])]
        out[p] = rng.sample(cand, min(nv, len(cand)))
    return out


def temoin(pics, vois, tirages, rng, pays_poids=None):
    pays = sorted(pics)
    acc = defaultdict(list)
    for _ in range(tirages):
        pv = pseudo_voisins(pays, vois, rng)
        r, _n = taux(unites(pics, pv), pays_poids)
        for k, v in r.items():
            if v is not None:
                acc[k].append(v)
    return {k: (sum(v) / len(v) if v else None) for k, v in acc.items()}


def statistiques(r, rt):
    e = {k: (r[k] - rt[k]) if r.get(k) is not None and rt.get(k) is not None else None for k in range(4)}
    D = (e[2] - e[1]) - (e[1] - e[0]) if None not in (e[0], e[1], e[2]) else None
    return e, D


def principal() -> int:
    jours, comptes, vois = charger()
    pics = pics_par_semaine(jours, comptes)
    pays_ok = [p for p in pics if any(v in pics for v in vois.get(p, []))]
    pics = {p: pics[p] for p in pics}          # les pseudo-voisins se tirent parmi tous les pays présents
    U = [u for u in unites(pics, vois) if u[0] in pays_ok]
    r, n = taux(U)
    rng = random.Random(GRAINE)
    rt = temoin(pics, vois, 200, rng)
    e, D = statistiques(r, rt)
    # rééchantillonnage des pays
    bs_D, bs_e1 = [], []
    rng2 = random.Random(GRAINE)
    for b in range(1000):
        tir = [rng2.choice(pays_ok) for _ in pays_ok]
        poids = defaultdict(int)
        for p in tir:
            poids[p] += 1
        rb, _ = taux(U, poids)
        rtb = temoin(pics, vois, 50, rng2, poids)
        eb, Db = statistiques(rb, rtb)
        if Db is not None:
            bs_D.append(Db)
        if eb[1] is not None:
            bs_e1.append(eb[1])
        if b % 100 == 99:
            print(f"  rééchantillon {b + 1}/1000", flush=True)
    q = lambda v, a: sorted(v)[int(a * (len(v) - 1))]
    icD = (q(bs_D, 0.05), q(bs_D, 0.95))
    ice1 = (q(bs_e1, 0.05), q(bs_e1, 0.95))
    verdict = lambda ic: "au-dessus de 0" if ic[0] > 0 else ("au-dessous de 0" if ic[1] < 0 else "contient 0")
    res = {"preenregistrement": "preenregistrements/contagion-complexe-manifestations.md", "sha256": "83fbcd7ddab848a8",
           "jours": [jours[0], jours[-1]], "pays": len(pays_ok), "unites": len(U),
           "effectifs": {str(k): n.get(k, 0) for k in range(4)},
           "r": {str(k): r[k] for k in range(4)}, "r_temoin": {str(k): rt.get(k) for k in range(4)},
           "exces": {str(k): e[k] for k in range(4)}, "D": D, "ic90_D": icD, "ic90_e1": ice1,
           "verdict_contagion": verdict(ice1), "verdict_forme": {"au-dessus de 0": "complexe", "au-dessous de 0": "simple",
                                                                  "contient 0": "non tranché"}[verdict(icD)]}
    (REG / "contagion-complexe.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(res, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(principal())
