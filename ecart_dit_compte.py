"""Écart entre ce qui est DIT et ce qui est COMPTÉ (bot 0.10.361, ombre ; rien n'entre dans le bot).

Décisions de l'auteur du 2026-11-19 : une déclaration (note, sondage, rapport, y compris d'État) ne mesure pas ce qu'elle
prétend mesurer mais renseigne sur son émetteur ; le signal est l'écart entre le dit et le compté (épiphénomène,
intention, communication trompeuse). Règle (18 h 37) : au moins DEUX SOURCES INDÉPENDANTES, de producteurs (propriétaires)
différents — deux sources du même propriétaire « s'entendent » et leur accord ne signifie rien. Nuance : deux
producteurs différents peuvent partager une même matière première (la presse) ; c'est signalé, pas caché.

Pour chaque couple déclaré dans COUPLES :
- dit : ton moyen hebdomadaire des gestes de A envers B dans la presse codée par GDELT (dyade:) ;
- compté : une série d'un autre producteur, sommée par semaine (lundi), dans le pays visé.
On mesure, sur les semaines communes :
- r : corrélation de rang (Spearman) des VARIATIONS d'une semaine à l'autre (on retire la tendance commune), avec une
  p-valeur par permutation (2 000 tirages) ;
- les semaines d'écart : résidu standardisé |z| > 2 de la régression du ton sur log(1 + compté). Un écart négatif = la
  presse raconte plus de conflit que ce qui se compte ; positif = elle raconte moins de conflit que ce qui se compte.
Sorties : registre/ecart-dit-compte.json et .md.
"""
from __future__ import annotations

import json
import math
import random
import sys
from datetime import date, timedelta
from pathlib import Path

import adaptateurs as ad

SORTIE = Path("registre") / "ecart-dit-compte"
# type d'adaptateur → (producteur, matière première)
PRODUCTEURS = {
    "dyade": ("GDELT (codage automatique de la presse)", "presse"),
    "gestes": ("GDELT (codage automatique de la presse)", "presse"),
    "hostilites": ("GDELT (codage automatique de la presse)", "presse"),
    "manifestations": ("GDELT (codage automatique de la presse)", "presse"),
    "paire": ("GDELT (codage automatique de la presse)", "presse"),
    "ucdp": ("UCDP, université d'Uppsala (codage humain)", "presse et rapports"),
    "feux": ("NASA FIRMS (satellites)", "capteurs"),
    "radar": ("Cloudflare Radar", "capteurs du réseau"),
    "ooni": ("OONI (mesures de volontaires)", "capteurs du réseau"),
    "portwatch": ("FMI et université d'Oxford (PortWatch)", "transpondeurs AIS"),
    "violations": ("ViolationsWatch", "rapports"),
}
COUPLES = [
    ("dyade:RUS:UKR", "ucdp:Ukraine"),
    ("dyade:RUS:UKR", "feux:UA"),
    ("dyade:ISR:LBN", "feux:LB"),
    ("dyade:IRN:ISR", "ucdp:Israel"),
]
PERMUTATIONS = 2000
SEUIL_Z = 2.0
MIN_SEMAINES = 15


def producteur(adaptateur: str) -> tuple[str, str]:
    return PRODUCTEURS.get(adaptateur.split(":")[0], ("inconnu", "inconnue"))


def independants(a: str, b: str) -> tuple[bool, str]:
    pa, pb = producteur(a), producteur(b)
    if "inconnu" in (pa[0], pb[0]):
        return False, "producteur inconnu : indépendance non établie"
    if pa[0] == pb[0]:
        return False, f"même producteur ({pa[0]}) : leur accord ne signifie rien"
    note = f"amont partagé ({pa[1]})" if pa[1] == pb[1] or "presse" in pa[1] and "presse" in pb[1] else "amont distinct"
    return True, note


def par_semaine(serie: list[tuple[str, float]]) -> dict[str, float]:
    out: dict[str, float] = {}
    for j, v in serie:
        d = date.fromisoformat(j)
        lundi = (d - timedelta(days=d.weekday())).isoformat()
        out[lundi] = out.get(lundi, 0.0) + v
    return out


def rangs(x: list[float]) -> list[float]:
    ordre = sorted(range(len(x)), key=lambda i: x[i])
    r = [0.0] * len(x)
    i = 0
    while i < len(x):
        j = i
        while j + 1 < len(x) and x[ordre[j + 1]] == x[ordre[i]]:
            j += 1
        for k in range(i, j + 1):
            r[ordre[k]] = (i + j) / 2
        i = j + 1
    return r


def pearson(x: list[float], y: list[float]) -> float:
    n = len(x)
    mx, my = sum(x) / n, sum(y) / n
    sx = math.sqrt(sum((a - mx) ** 2 for a in x))
    sy = math.sqrt(sum((b - my) ** 2 for b in y))
    return 0.0 if not sx or not sy else sum((a - mx) * (b - my) for a, b in zip(x, y)) / (sx * sy)


def spearman_perm(x: list[float], y: list[float], n_perm: int = PERMUTATIONS, graine: int = 1) -> tuple[float, float]:
    rx, ry = rangs(x), rangs(y)
    r = pearson(rx, ry)
    alea = random.Random(graine)
    plus = 0
    for _ in range(n_perm):
        p = ry[:]
        alea.shuffle(p)
        plus += abs(pearson(rx, p)) >= abs(r)
    return r, (plus + 1) / (n_perm + 1)


def ecarts(dit: dict[str, float], compte: dict[str, float]) -> dict:
    semaines = sorted(set(dit) & set(compte))
    if len(semaines) < MIN_SEMAINES:
        return {"semaines": len(semaines), "note": f"moins de {MIN_SEMAINES} semaines communes : rien à conclure"}
    y = [dit[s] for s in semaines]
    x = [math.log1p(max(compte[s], 0.0)) for s in semaines]
    dy = [b - a for a, b in zip(y, y[1:])]
    dx = [b - a for a, b in zip(x, x[1:])]
    r, p = spearman_perm(dx, dy)
    mx, my = sum(x) / len(x), sum(y) / len(y)
    vx = sum((a - mx) ** 2 for a in x)
    pente = sum((a - mx) * (b - my) for a, b in zip(x, y)) / vx if vx else 0.0
    res = [b - (my + pente * (a - mx)) for a, b in zip(x, y)]
    sd = math.sqrt(sum(e * e for e in res) / max(1, len(res) - 2)) or 1.0
    flag = [{"semaine": s, "z": round(e / sd, 2), "ton": round(dit[s], 2), "compte": compte[s]}
            for s, e in zip(semaines, res) if abs(e / sd) > SEUIL_Z]
    return {"semaines": len(semaines), "du": semaines[0], "au": semaines[-1], "r_variations": round(r, 3),
            "p": round(p, 4), "pente_niveaux": round(pente, 3), "semaines_d_ecart": flag}


def principal() -> int:
    out = []
    for a, b in COUPLES:
        ok, note = independants(a, b)
        ligne = {"dit": a, "compte": b, "producteur_dit": producteur(a)[0], "producteur_compte": producteur(b)[0],
                 "independance": note}
        if ok:
            ligne.update(ecarts(dict(ad.lire(a)), par_semaine(ad.lire(b))))
        out.append(ligne)
    Path(str(SORTIE) + ".json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    md = ["# Écart entre le dit et le compté (ombre)", "",
          "Dit : ton de la presse codée par GDELT. Compté : série d'un autre producteur. r = corrélation de rang des "
          "variations hebdomadaires (attendu négatif : plus de violence comptée, ton plus conflictuel) ; semaines d'écart : "
          f"|z| > {SEUIL_Z} (z < 0 : la presse raconte plus de conflit que ce qui se compte ; z > 0 : moins).", "",
          "| dit | compté | indépendance | semaines | r | p | écarts (5 derniers) |", "|---|---|---|---|---|---|---|"]
    for l in out:
        e = ", ".join(f"{x['semaine']} ({x['z']:+})" for x in l.get("semaines_d_ecart", [])[-5:]) or "—"
        md.append(f"| `{l['dit']}` | `{l['compte']}` | {l['independance']} | {l.get('semaines', '—')} | "
                  f"{l.get('r_variations', '—')} | {l.get('p', '—')} | {e if 'r_variations' in l else l.get('note', '—')} |")
    Path(str(SORTIE) + ".md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))
    return 0


if __name__ == "__main__":
    sys.exit(principal())
