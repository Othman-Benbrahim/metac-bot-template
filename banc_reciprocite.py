"""Banc de la réciprocité entre États (Rapoport, Axelrod ; bot 0.10.312), banc de compréhension.

Décision d'auteur du 2026-11-19, 3 h 10. Préenregistrement : preenregistrements/reciprocite-dyades.md. Données :
registre/gdelt-dyades.json (gdelt_bq.py --mode dyades). Ne touche ni le bot ni les questions ; aucun appel à un modèle.

    python banc_reciprocite.py
"""
from __future__ import annotations

import json
import random
from datetime import date, timedelta
from pathlib import Path

import numpy as np

import alphabet_pipeline as ap

DONNEES = Path("registre/gdelt-dyades.json")
RESUME = Path("registre/banc-reciprocite.json")
RETRECI = 5
COUPURE = "2025-07-01"
TIRAGES = 2000
GRAINE = 0
SEUIL_STYLE = 0.05


def semaines(debut: str, fin: str) -> list[str]:
    d = date.fromisoformat(debut)
    d -= timedelta(days=d.weekday())
    out = []
    while d.isoformat() <= fin:
        out.append(d.isoformat())
        d += timedelta(days=7)
    return out


def serie(sens: dict, ss: list[str]) -> np.ndarray:
    return np.array([(sens.get(s, {}).get("somme_g", 0.0)) / (sens.get(s, {}).get("n", 0) + RETRECI) for s in ss])


def mco(X: np.ndarray, y: np.ndarray) -> np.ndarray:
    return np.linalg.lstsq(X, y, rcond=None)[0]


def un_sens(y_ba: np.ndarray, y_ab: np.ndarray, test: np.ndarray) -> dict:
    """y_BA[t] = c + φ·y_BA[t−1] + ρ·y_AB[t−1] contre le même sans ρ ; test = masque des semaines de test (t)."""
    Y, L_ba, L_ab = y_ba[1:], y_ba[:-1], y_ab[:-1]
    te = test[1:]
    tr = ~te
    un = np.ones_like(Y)
    X1, X0 = np.column_stack([un, L_ba, L_ab]), np.column_stack([un, L_ba])
    b1, b0 = mco(X1[tr], Y[tr]), mco(X0[tr], Y[tr])
    e1 = float(np.mean((Y[te] - X1[te] @ b1) ** 2))
    e0 = float(np.mean((Y[te] - X0[te] @ b0) ** 2))
    Xa = np.column_stack([un, L_ba, np.minimum(L_ab, 0), np.maximum(L_ab, 0)])
    ba = mco(Xa, Y)                                          # descriptif, toute la période
    rho_neg, rho_pos = float(ba[2]), float(ba[3])
    style = ("donnant-donnant" if rho_neg > SEUIL_STYLE and rho_pos > SEUIL_STYLE else
             "rancunier" if rho_neg > SEUIL_STYLE else "conciliant" if rho_pos > SEUIL_STYLE else "indifférent")
    return {"ecart_mse": e1 - e0, "mse_avec": e1, "mse_sans": e0, "phi": float(b1[1]), "rho": float(b1[2]),
            "rho_conflit": rho_neg, "rho_cooperation": rho_pos, "style": style}


def analyser(d: dict) -> dict:
    ss = semaines(d["debut"], d["fin"])
    test = np.array([s >= COUPURE for s in ss])
    sens = d["sens"]
    res = {}
    for k in sorted(sens):
        a, b = k.split(">")
        inverse = f"{b}>{a}"
        if inverse not in sens:
            continue
        r = un_sens(serie(sens[k], ss), serie(sens[inverse], ss), test)   # k = B→A répond à A→B (= inverse)
        r["evenements"] = sum(v["n"] for v in sens[k].values())
        res[k] = r
    paires: dict[str, list[float]] = {}
    for k, r in res.items():
        a, b = k.split(">")
        paires.setdefault("|".join(sorted((a, b))), []).append(r["ecart_mse"])
    cles = sorted(paires)
    rnd = random.Random(GRAINE)
    moy = lambda ks: float(np.mean([x for k in ks for x in paires[k]]))
    tirages = sorted(moy([cles[rnd.randrange(len(cles))] for _ in cles]) for _ in range(TIRAGES)) if cles else []
    out = {"version_bot": ap.VERSION_BOT, "sens": len(res), "paires": len(cles), "semaines": len(ss),
           "coupure_test": COUPURE,
           "note": "banc de compréhension ; écart = erreur de test avec réponse au geste de l'autre − sans ; négatif = la réciprocité aide"}
    if not cles:
        return dict(out, verdict="en attente (gdelt_bq.py --mode dyades)")
    b, h = tirages[int(0.05 * TIRAGES)], tirages[int(0.95 * TIRAGES) - 1]
    out.update({"ecart_moyen": round(moy(cles), 5), "intervalle_90_par_paires": [round(b, 5), round(h, 5)],
                "verdict": "la réciprocité se voit" if h < 0 else "la réciprocité ne se voit pas à une semaine",
                "rho_median": round(float(np.median([r["rho"] for r in res.values()])), 3),
                "styles": {s: sum(1 for r in res.values() if r["style"] == s)
                           for s in ("donnant-donnant", "rancunier", "conciliant", "indifférent")},
                "par_sens": {k: {kk: (round(v, 4) if isinstance(v, float) else v) for kk, v in r.items()}
                             for k, r in sorted(res.items(), key=lambda t: -t[1]["evenements"])}})
    return out


def principal() -> int:
    d = json.loads(DONNEES.read_text(encoding="utf-8")) if DONNEES.exists() else {"debut": "2023-01-01", "fin": "2023-01-01", "sens": {}}
    r = analyser(d)
    RESUME.write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in r.items() if k != "par_sens"}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(principal())
