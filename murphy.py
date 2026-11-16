"""Diagramme de Murphy et « valeur captée » (bot 0.10.197, lecture descriptive, jamais critère d'adoption).

Décision d'auteur du 2026-11-16 (17 h 53), après lecture de Ren, « Does a Better Brier Score Buy Better Decisions? »
(AI x Epistemics Research Sprint, novembre 2026 ; dépôt gavenren/decision-value-audit). Méthode classique :
Schervish (1989), Ehm et al. (2016), Richardson (2000) pour la valeur économique relative.

Un utilisateur de rapport coût-perte θ agit quand p > θ. Regret contre la prescience, en unités de la perte :
    r_θ(p, y) = θ (1 − y) 1{p > θ} + (1 − θ) y 1{p < θ}   (à p = θ, une demi-action de chaque côté)
et ∫₀¹ 2 r_θ(p, y) dθ = (p − y)² : le Brier est la moyenne sur des θ uniformes.
Valeur captée V(θ) = 1 − R_f(θ) / R_0(θ), où R_0 est la politique « taux de base » (même action pour toutes les
questions d'une même source, selon la fréquence observée de cette source sur l'échantillon). V = 1 : prescience ;
V = 0 : taux de base ; V < 0 : mieux valait ignorer la prévision. Profils d'utilisateurs : densités Beta sur θ.

Intervalles : bootstrap par question (graine fixe), taux de base tenus fixes (comme les effets de question dans
l'article). Aucun modèle de langue, aucun coût. Le critère d'adoption reste la règle commune (perte log, blocs).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

SEUILS = (0.02, 0.05, 0.10, 0.23, 0.50, 0.77, 0.90, 0.95, 0.98)
PROFILS = {"uniforme (= Brier)": (1, 1), "précaution (θ moyen 0,1)": (1, 9),
           "seuil haut (θ moyen 0,9)": (9, 1), "enjeux égaux (θ moyen 0,5)": (20, 20)}
GRILLE = (np.arange(1, 1000) - 0.5 + 0.5) / 1000.0     # 0,001 … 0,999
N_BOOT, GRAINE = 1000, 20261116


def regret(p: np.ndarray, y: np.ndarray, theta: np.ndarray) -> np.ndarray:
    """Matrice (questions × seuils) des regrets."""
    p, y, t = p[:, None], y[:, None], theta[None, :]
    agit = np.where(p > t, 1.0, np.where(p == t, 0.5, 0.0))
    return t * (1 - y) * agit + (1 - t) * y * (1 - agit)


def poids_beta(a: float, b: float, theta: np.ndarray = GRILLE) -> np.ndarray:
    w = theta ** (a - 1) * (1 - theta) ** (b - 1)
    return w / w.sum()


def taux_de_base(y: np.ndarray, sources: list[str]) -> np.ndarray:
    s = np.array(sources)
    out = np.empty_like(y, dtype=float)
    for k in set(sources):
        m = s == k
        out[m] = y[m].mean()
    return out


def _valeurs(rf: np.ndarray, r0: np.ndarray, idx_seuils: list[int], profils: dict) -> dict:
    """rf, r0 : regrets moyens sur la grille (vecteurs, ou matrices bootstrap × grille)."""
    with np.errstate(divide="ignore", invalid="ignore"):
        v_seuils = 1 - rf[..., idx_seuils] / r0[..., idx_seuils]
        v_prof = {n: 1 - (rf * w).sum(-1) / (r0 * w).sum(-1) for n, w in profils.items()}
    return {"seuils": v_seuils, "profils": v_prof}


def comparer(lignes: list[dict], bras: dict[str, callable], reference: str = "B") -> dict:
    """lignes : dicts avec « issue » (0/1), « source_question », « question_id ». bras : nom → fonction p(ligne) ou None.
    Chaque bras est comparé à la référence sur les questions où les deux ont une probabilité."""
    idx_seuils = [int(np.argmin(np.abs(GRILLE - s))) for s in SEUILS]
    profils = {n: poids_beta(*ab) for n, ab in PROFILS.items()}
    rng = np.random.default_rng(GRAINE)
    out = {"note": "valeur captée : 1 = prescience, 0 = taux de base par source, < 0 = pire que l'ignorer ; "
                   "lecture descriptive, pas un critère d'adoption ; IC 95 % bootstrap par question",
           "seuils": list(SEUILS), "comparaisons": {}}
    f_ref = bras[reference]
    for nom, f in bras.items():
        if nom == reference:
            continue
        ok = [x for x in lignes if x.get("issue") in (0, 1) and f_ref(x) is not None and f(x) is not None]
        if len(ok) < 30:
            out["comparaisons"][nom] = {"n": len(ok), "note": "trop peu de questions"}
            continue
        y = np.array([float(x["issue"]) for x in ok])
        base = taux_de_base(y, [x["source_question"] for x in ok])
        mats = {reference: regret(np.array([f_ref(x) for x in ok], dtype=float), y, GRILLE),
                nom: regret(np.array([f(x) for x in ok], dtype=float), y, GRILLE)}
        m0 = regret(base, y, GRILLE)
        n = len(ok)
        tirages = rng.multinomial(n, np.full(n, 1 / n), size=N_BOOT) / n          # N_BOOT × n
        res = {"n": n, "sources": {k: int(sum(x["source_question"] == k for x in ok))
                                   for k in sorted({x["source_question"] for x in ok})}}
        point, boot = {}, {}
        r0, r0b = m0.mean(0), tirages @ m0
        for k, m in mats.items():
            point[k] = _valeurs(m.mean(0), r0, idx_seuils, profils)
            boot[k] = _valeurs(tirages @ m, r0b, idx_seuils, profils)

        def resume(v, vb):
            lo, hi = np.nanpercentile(vb, [2.5, 97.5], axis=0)
            return {"V": _r(v), "ic95": [_r(lo), _r(hi)]}

        res["par_seuil"] = {}
        for i, s in enumerate(SEUILS):
            d = point[nom]["seuils"][i] - point[reference]["seuils"][i]
            db = boot[nom]["seuils"][:, i] - boot[reference]["seuils"][:, i]
            res["par_seuil"][f"{s:.2f}"] = {reference: resume(point[reference]["seuils"][i], boot[reference]["seuils"][:, i]),
                                            nom: resume(point[nom]["seuils"][i], boot[nom]["seuils"][:, i]),
                                            "ecart": resume(d, db)}
        res["par_profil"] = {}
        for p_ in PROFILS:
            d = point[nom]["profils"][p_] - point[reference]["profils"][p_]
            db = boot[nom]["profils"][p_] - boot[reference]["profils"][p_]
            res["par_profil"][p_] = {reference: resume(point[reference]["profils"][p_], boot[reference]["profils"][p_]),
                                     nom: resume(point[nom]["profils"][p_], boot[nom]["profils"][p_]),
                                     "ecart": resume(d, db)}
        res["courbe"] = {"theta": [round(float(t), 3) for t in GRILLE[::25]],
                         reference: [_r(v) for v in (1 - mats[reference].mean(0) / r0)[::25]],
                         nom: [_r(v) for v in (1 - mats[nom].mean(0) / r0)[::25]]}
        out["comparaisons"][nom] = res
    return out


def _r(v) -> float | None:
    v = float(v)
    return None if not np.isfinite(v) else round(v, 4)


def _p(cle: str):
    return lambda x: (x.get(cle) or {}).get("p") if isinstance(x.get(cle), dict) else None


BRAS_B = {"B": lambda x: x.get("p_B"), "B_AR": _p("ombre_b_ar"), "B_saison": _p("ombre_b_saison"),
          "aiguillage_regime": lambda x: x.get("p_regime")}


def pour_banc_b(lignes: list[dict]) -> dict:
    return comparer(lignes, BRAS_B)


def tableau(r: dict) -> str:
    """Résumé lisible (Markdown) : V par profil et par seuil, écart au bras de référence avec IC."""
    l = [f"Valeur captée (1 = prescience, 0 = taux de base). {r['note']}.", ""]
    for nom, c in r["comparaisons"].items():
        if "par_profil" not in c:
            l.append(f"- {nom} : {c['n']} questions, {c['note']}")
            continue
        l += [f"### B contre {nom} ({c['n']} questions : " + ", ".join(f"{k} {v}" for k, v in c["sources"].items()) + ")",
              "", f"| profil ou seuil θ | B | {nom} | écart (IC 95 %) |", "|---|---|---|---|"]
        rangs = list(c["par_profil"].items()) + [(f"θ = {k}", v) for k, v in c["par_seuil"].items()]
        for k, v in rangs:
            e = v["ecart"]
            l.append(f"| {k} | {v['B']['V']} | {v[nom]['V']} | {e['V']} [{e['ic95'][0]} ; {e['ic95'][1]}] |")
        l.append("")
    return "\n".join(l)


if __name__ == "__main__":
    src = Path(sys.argv[1] if len(sys.argv) > 1 else "registre/banc-b.jsonl")
    lignes = [json.loads(x) for x in src.open(encoding="utf-8") if x.strip()]
    r = pour_banc_b(lignes)
    dest = src.with_name(src.stem + "-murphy.json")
    dest.write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
    print(tableau(r))
    print(f"Écrit : {dest}")
