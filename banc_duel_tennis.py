"""Duel des méthodes de force au tennis (preenregistrements/duel-tennis.md). Une passe ; aucun modèle de langue.
Rapport : banc_duel_tennis.json (et résumé imprimé)."""
from __future__ import annotations

import csv
import io
import json
import math
import sys
import time
from collections import defaultdict, deque

import httpx

import politesse
from collecte_elo import SACKMANN, SACKMANN_HF

NIVEAUX = {"atp": {"G", "M"}, "wta": {"G", "PM", "T1"}}
TOURS = ["R128", "R64", "R32", "R16", "QF", "SF", "F"]
PMIN = 1e-4


def charger(t: str) -> list[dict]:
    rows = []
    with httpx.Client(headers={"User-Agent": politesse.UA}, timeout=60, follow_redirects=True) as c:
        for a in range(1990, 2027):
            txt = None
            for u in (SACKMANN.format(t=t, a=a), SACKMANN_HF.format(t=t, a=a)):
                try:
                    r = c.get(u)
                    if r.status_code == 200 and r.text.strip():
                        txt = r.text
                        break
                except httpx.HTTPError:
                    pass
            if txt:
                rows += list(csv.DictReader(io.StringIO(txt)))
            else:
                print(f"{t} {a} : indisponible", flush=True)
            time.sleep(1)
    return rows


def rang(x) -> float:
    try:
        v = float(x)
        return v if v > 0 else 500.0
    except (TypeError, ValueError):
        return 500.0


def arbre(ms: list[dict]):
    """Reconstruit le tableau depuis les résultats ; rend une fonction de calcul exact, ou None si incohérent."""
    par_tour = defaultdict(list)
    for m in ms:
        if m.get("round") in TOURS:
            par_tour[m["round"]].append(m)
    if len(par_tour.get("F", [])) != 1:
        return None
    gagne = {}   # (tour, joueur) -> match gagné à ce tour
    for t, L in par_tour.items():
        for m in L:
            gagne[(t, m["winner_name"])] = m

    def noeud(m, i):
        """Arbre du match m (tour d'indice i) : ('j', nom) ou ('m', gauche, droite)."""
        enfants = []
        for p in (m["winner_name"], m["loser_name"]):
            prec = gagne.get((TOURS[i - 1], p)) if i > 0 else None
            enfants.append(noeud(prec, i - 1) if prec else ("j", p))
        return ("m", enfants[0], enfants[1])

    try:
        return noeud(par_tour["F"][0], TOURS.index("F"))
    except RecursionError:
        return None


def joueurs(n) -> list[str]:
    return [n[1]] if n[0] == "j" else joueurs(n[1]) + joueurs(n[2])


def proba_titre(n, pm) -> dict:
    """Distribution exacte du vainqueur d'un sous-arbre ; pm(a, b) = P(a bat b)."""
    if n[0] == "j":
        return {n[1]: 1.0}
    G, D = proba_titre(n[1], pm), proba_titre(n[2], pm)
    out = {}
    for a, pa in G.items():
        out[a] = pa * sum(pb * pm(a, b) for b, pb in D.items())
    for b, pb in D.items():
        out[b] = pb * sum(pa * pm(b, a) for a, pa in G.items())
    return out


def ajuster(X: list[tuple[float, float]], Y: list[int]) -> tuple[float, float]:
    """Régression logistique sans constante (symétrie), 2 paramètres, méthode de Newton."""
    a = b = 0.0
    for _ in range(25):
        ga = gb = hab = 0.0
        haa = hbb = 1e-6                    # légère régularisation (variable constante)
        for (x1, x2), y in zip(X, Y):
            p = 1 / (1 + math.exp(-(a * x1 + b * x2)))
            ga += (y - p) * x1
            gb += (y - p) * x2
            w = p * (1 - p)
            haa += w * x1 * x1
            hab += w * x1 * x2
            hbb += w * x2 * x2
        det = haa * hbb - hab * hab
        if det <= 1e-12:
            break
        a += (hbb * ga - hab * gb) / det
        b += (haa * gb - hab * ga) / det
    return a, b


def duel(t: str) -> dict:
    rows = [r for r in charger(t) if r.get("winner_name") and r.get("loser_name") and len(r.get("tourney_date") or "") == 8]
    tournois = defaultdict(list)
    for r in rows:
        tournois[(r["tourney_date"], r["tourney_id"])].append(r)
    R, n = defaultdict(lambda: 1500.0), defaultdict(int)
    forme = defaultdict(lambda: deque(maxlen=10))
    a = b = 0.0
    saison_fit = None
    hist = []               # matchs pour l'ajustement : (saison, x1, x2, y)
    res = defaultdict(lambda: defaultdict(list))
    niveaux_vus, ecartes = set(), 0

    def F(p):
        d = forme[p]
        if len(d) < 3:
            return 0.5
        w = [1 / math.log(ro + 2) for _, ro in d]
        return sum(y * wi for (y, _), wi in zip(d, w)) / sum(w)

    for (date, tid), ms in sorted(tournois.items()):
        saison = int(date[:4])
        niveau = ms[0].get("tourney_level") or ""
        rk = {}
        for m in ms:
            rk.setdefault(m["winner_name"], rang(m.get("winner_rank")))
            rk.setdefault(m["loser_name"], rang(m.get("loser_rank")))
        if saison != saison_fit and saison >= 2010:       # réajustement au début de chaque saison, données antérieures
            H = [(x1, x2, y) for s, x1, x2, y in hist if s < saison]
            if H:
                a, b = ajuster([(x1, x2) for x1, x2, _ in H], [y for *_, y in H])
            saison_fit = saison
        if niveau in NIVEAUX[t] and saison >= 2010:
            niveaux_vus.add(niveau)
            A = arbre(ms)
            finale = [m for m in ms if m.get("round") == "F"]
            if A is None or not finale:
                ecartes += 1
            else:
                champion = finale[0]["winner_name"]
                J = joueurs(A)
                Fj = {p: F(p) for p in J}
                pe = proba_titre(A, lambda x, y: 1 / (1 + 10 ** ((R[y] - R[x]) / 400)))
                pf = proba_titre(A, lambda x, y: 1 / (1 + math.exp(-(a * (Fj[x] - Fj[y]) +
                                                                      b * (math.log(rk.get(y, 500)) - math.log(rk.get(x, 500)))))))
                for nom, p in (("1/N", 1 / len(J)), ("elo", pe.get(champion, 0)), ("forme", pf.get(champion, 0))):
                    res[saison][nom].append(-math.log(max(p, PMIN)))
        # mises à jour avec les matchs du tournoi (état de la veille gardé pour le pronostic ci-dessus)
        for m in sorted(ms, key=lambda m: TOURS.index(m["round"]) if m.get("round") in TOURS else -1):
            g, p = m["winner_name"], m["loser_name"]
            hist.append((saison, F(g) - F(p), math.log(rk.get(p, 500)) - math.log(rk.get(g, 500)), 1))
            hist.append((saison, F(p) - F(g), math.log(rk.get(g, 500)) - math.log(rk.get(p, 500)), 0))
            if "W/O" in (m.get("score") or ""):
                continue
            e = 1 / (1 + 10 ** ((R[p] - R[g]) / 400))
            kg, kp = 250 / (n[g] + 5) ** 0.4, 250 / (n[p] + 5) ** 0.4
            R[g] += kg * (1 - e)
            R[p] -= kp * (1 - e)
            n[g] += 1
            n[p] += 1
            forme[g].append((1, rang(m.get("loser_rank"))))
            forme[p].append((0, rang(m.get("winner_rank"))))
    S = {s: {k: round(sum(v) / len(v), 4) for k, v in d.items()} | {"n": len(d["1/N"])} for s, d in sorted(res.items())}
    test = [s for s in S if 2010 <= s <= 2025]
    tous = lambda k: [x for s in test for x in res[s][k]]
    ens = {k: round(sum(tous(k)) / max(1, len(tous(k))), 4) for k in ("1/N", "elo", "forme")}
    bat = {k: sum(S[s][k] < S[s]["1/N"] for s in test) for k in ("elo", "forme")}
    duel_ = {"elo": sum(S[s]["elo"] < S[s]["forme"] for s in test), "forme": sum(S[s]["forme"] < S[s]["elo"] for s in test)}
    retenue = {k: ens[k] < ens["1/N"] and bat[k] >= math.ceil(2 * len(test) / 3) for k in ("elo", "forme")}
    ecart = ens["elo"] - ens["forme"]
    gagnant = "non concluant" if abs(ecart) < 0.02 else ("forme" if ecart > 0 else "elo")
    return {"circuit": t, "niveaux_vus": sorted(niveaux_vus), "tableaux_ecartes": ecartes, "saisons": S,
            "ensemble_2010_2025": ens, "saisons_test": len(test), "saisons_battant_1_sur_N": bat,
            "duel_saisons_gagnees": duel_, "retenue": retenue, "duel_ensemble": gagnant,
            "params_forme_derniere_saison": {"a": round(a, 3), "b": round(b, 3)}}


if __name__ == "__main__":
    out = {t: duel(t) for t in (sys.argv[1:] or ["atp", "wta"])}
    json.dump(out, open("banc_duel_tennis.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    for t, r in out.items():
        print(f"\n== {t.upper()} (niveaux {r['niveaux_vus']}, tableaux écartés {r['tableaux_ecartes']})")
        for s, v in r["saisons"].items():
            print(f"  {s} n={v['n']:>2}  1/N {v['1/N']:.3f}  elo {v['elo']:.3f}  forme {v['forme']:.3f}")
        print(f"  ensemble 2010-2025 : {r['ensemble_2010_2025']}")
        print(f"  saisons battant 1/N (sur {r['saisons_test']}) : {r['saisons_battant_1_sur_N']} ; retenue : {r['retenue']}")
        print(f"  duel elo/forme, saisons gagnées : {r['duel_saisons_gagnees']} ; ensemble : {r['duel_ensemble']}")
