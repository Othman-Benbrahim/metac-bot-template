"""Diagnostic PIT des fourchettes numériques et sensibilité à la fenêtre d'ajustement (descriptif, aucun verdict ;
pistes Learning Bayesian Statistics et Risk Data Lab n° 06, décisions de l'auteur du 2026-11-21, 12 h 34 et 12 h 53).

PIT : pour chaque prévision passée, rang de la valeur réalisée dans la distribution prévue (0 = sous tout, 1 = au-dessus
de tout). Des prévisions bien calibrées donnent des rangs uniformes. Lecture :
- moyenne au-dessus de 0,5 : la réalité tombe trop souvent au-dessus (prévisions décalées vers le bas), et inversement ;
- trop de rangs aux deux bouts (sous 0,1 et au-dessus de 0,9, 10 % attendus de chaque côté) : fourchettes trop
  étroites ; trop peu : trop larges.
Les trois modèles en service le permettent exactement, car leur distribution est un ensemble d'écarts passés : le rang
est celui de l'écart réalisé parmi eux.
Limite : séries autocorrélées, prévisions qui se chevauchent ; le nombre effectif est plus petit que n, les marges
indiquées (binomiales) sont donc optimistes. Aucun modèle n'est changé ici : tout changement passerait par un essai
préenregistré.

Sensibilité : même calcul en faisant varier la fenêtre (indicateurs et Tokyo : 24 / 36 / 60 écarts ; chiffre
d'affaires : 12 / 20 / 32), la fenêtre en service étant 36 et 20. e-Stat : This service uses API functions from
e-Stat, however its contents are not guaranteed by government.

    python mise_au_point/pit_fourchettes.py
"""
from __future__ import annotations

import csv
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from collecte_edgar import NOUVELLES_V2
from mise_au_point.resultats_entreprises_v2_essai import blocs_consecutifs

SORTIE = Path("registre") / "mise-au-point" / "pit-fourchettes.json"


def rang(pool: list[float], obs: float) -> float:
    """Rang PIT de obs parmi les écarts du modèle (égalités au milieu), dans ]0 ; 1[."""
    moins = sum(1 for p in pool if p < obs)
    egal = sum(1 for p in pool if p == obs)
    return (moins + 0.5 * egal + 0.5) / (len(pool) + 1)


def resumer(us: list[float]) -> dict:
    n = len(us)
    if not n:
        return {"n": 0}
    bas, haut = sum(u < 0.1 for u in us) / n, sum(u > 0.9 for u in us) / n
    moy = sum(us) / n
    marge = 1.645 * math.sqrt(0.09 / n)               # ±90 % autour de 10 % (binomiale, optimiste)
    lecture = []
    if bas + haut > 0.2 + 1.645 * math.sqrt(0.16 / n):
        lecture.append("fourchettes trop étroites")
    elif bas + haut < 0.2 - 1.645 * math.sqrt(0.16 / n):
        lecture.append("fourchettes trop larges")
    if moy > 0.5 + 1.645 * math.sqrt(1 / 12 / n):
        lecture.append("réalité trop souvent au-dessus (prévisions trop basses)")
    elif moy < 0.5 - 1.645 * math.sqrt(1 / 12 / n):
        lecture.append("réalité trop souvent au-dessous (prévisions trop hautes)")
    deciles = [round(sum(1 for u in us if i / 10 <= u < (i + 1) / 10) / n, 3) for i in range(10)]
    return {"n": n, "moyenne": round(moy, 3), "sous_0_1": round(bas, 3), "au_dessus_0_9": round(haut, 3),
            "marge_90_par_bout": round(marge, 3), "deciles": deciles,
            "lecture": "; ".join(lecture) or "pas d'écart net à l'uniforme"}


def pit_marche(x: list[float], fenetre: int, debut: int = 19, garde=lambda t: True) -> list[float]:
    """Indicateurs lents et Tokyo : prochaine valeur = dernière + écart passé (fenetre derniers écarts, h = 1)."""
    us = []
    for t in range(debut, len(x) - 1):
        if not garde(t) or t + 1 < fenetre // 2 + 2:
            continue
        v = x[max(0, t + 1 - fenetre - 1): t + 1]
        pool = [b - a for a, b in zip(v[:-1], v[1:])]
        if pool:
            us.append(rang(pool, x[t + 1] - x[t]))
    return us


def pit_foster(par: dict, entreprises, fenetre: int, minimum: int = 12) -> list[float]:
    us = []
    for e in sorted(entreprises):
        for bl in blocs_consecutifs(sorted(par.get(e, []))) if e in par else []:
            x = [math.log(v) for _, v in bl]
            for t in range(1, len(x) - 1):
                xs = x[: t + 1]
                g = [xs[s] - xs[s - 4] for s in range(4, len(xs))]
                eps = [b - a for a, b in zip(g[:-1], g[1:])][-fenetre:]
                if len(eps) < minimum:
                    continue
                centre = xs[len(xs) - 4] + g[-1]
                us.append(rang(eps, x[t + 1] - centre))
    return us


def principal() -> int:
    s = {}
    for r in csv.DictReader(open("registre/fred.csv", encoding="utf-8")):
        s.setdefault(r["serie"], []).append((r["jour"], float(r["valeur"])))
    series = {"UNRATE": [v for _, v in sorted(s["UNRATE"])], "UMCSENT": [v for _, v in sorted(s["UMCSENT"])]}
    for cle in ("CPIAUCSL", "CPILFESL"):
        x = [v for _, v in sorted(s[cle])]
        series[cle] = [100 * (x[i] / x[i - 12] - 1) for i in range(12, len(x))]
    tk = sorted((r["mois"], float(r["inflation_hors_frais_sur_un_an"]))
                for r in csv.DictReader(open("registre/estat-tokyo-cpi.csv", encoding="utf-8")) if r["base"] == "2025")
    mois, vt = [m for m, _ in tk], [v for _, v in tk]
    par = defaultdict(list)
    for r in csv.DictReader(open("registre/edgar-trimestres.csv", encoding="utf-8")):
        if r["mesure"] == "chiffre_affaires" and float(r["valeur"]) > 0:
            par[r["entreprise"]].append((r["fin"], float(r["valeur"])))

    out = {"indicateurs_lents": {}, "tokyo": {}, "chiffre_affaires_nouvelles": {}}
    for f in (24, 36, 60):
        tous = []
        for k, x in series.items():
            u = pit_marche(x, f)
            tous += u
            if f == 36:
                out["indicateurs_lents"].setdefault("par_serie_fenetre_36", {})[k] = resumer(u)
        out["indicateurs_lents"][f"fenetre_{f}"] = resumer(tous)
        out["tokyo"][f"fenetre_{f}"] = resumer(pit_marche(vt, f, 0, lambda t: "2006-01" <= mois[t] <= "2026-09"))
    for f in (12, 20, 32):
        out["chiffre_affaires_nouvelles"][f"fenetre_{f}"] = resumer(pit_foster(par, NOUVELLES_V2, f, min(12, f)))
    out["note"] = ("descriptif ; fenêtres en service : 36 (indicateurs, Tokyo), 20 (chiffre d'affaires) ; "
                   "marges binomiales optimistes (séries autocorrélées) ; e-Stat : contenu non garanti par le gouvernement")
    SORTIE.parent.mkdir(parents=True, exist_ok=True)
    SORTIE.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    for bloc, d in out.items():
        if isinstance(d, dict):
            for k, v in d.items():
                if "n" in v:
                    print(f"{bloc:28s} {k:10s} n={v['n']:5d} moy={v['moyenne']} bas={v['sous_0_1']} haut={v['au_dessus_0_9']} → {v['lecture']}")
            for k, v in d.get("par_serie_fenetre_36", {}).items():
                print(f"{'   ' + k:28s} {'36':10s} n={v['n']:5d} moy={v['moyenne']} bas={v['sous_0_1']} haut={v['au_dessus_0_9']} → {v['lecture']}")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
