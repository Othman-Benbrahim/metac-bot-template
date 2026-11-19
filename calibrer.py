"""Calibration de la carte sur nos séries (bot 0.10.325).

Consigne de l'auteur, 2026-11-19, 6 h 39 : « il faut que le programme soit fonctionnel, et qu'on ait plus qu'à le
calibrer ». Les fiches donnent des valeurs de départ (force en mots, délai en mots, règle d'intensité, seuil, gain de
modulation) ; ce script les MESURE partout où les deux bouts d'une relation ont une série branchée, et écrit
registre/calibration.json, que carte.Carte lit d'elle-même (une relation mesurée significative remplace sa force, son
délai, son signe et, si la mesure le dit, sa règle).

Méthode, fixée avant de regarder les résultats (aucun réglage après coup) :
- les deux séries sont ramenées au même pas : semaine si les deux sont au plus hebdomadaires, sinon mois ;
- on prend les DIFFÉRENCES d'une période à l'autre (une tendance commune ne fait pas une relation), centrées réduites ;
- corrélation de la source à t avec la cible à t + k, pour k = 0 … RETARD_MAX ; on garde le k de plus forte |r| ;
- significatif si |r|·√n dépasse le quantile normal corrigé de Bonferroni sur les RETARD_MAX + 1 retards (α = 0,05) ;
- poids mesuré = min(1, 2·|r|) (|r| = 0,5 vaut une relation « forte ») ; délai = k × pas ;
- règle : pente de la cible sur la source quand |source| > SEUIL_REGLE, contre la pente en dessous ; rapport > 1,5 →
  seuil, < 0,67 → saturation, sinon proportionnelle (seulement si ≥ 6 périodes au-dessus et ≥ 12 en dessous) ;
- modulation (clé « module ») : corrélation de la relation visée quand le modulateur est au-dessus de sa médiane
  contre en dessous ; différence testée par la transformation de Fisher (α = 0,05) ; gain = hausse relative de |r|
  par unité d'écart du modulateur, bornée à [0 ; 1,5].
On prend la PREMIÈRE série utilisable de chaque bout (ordre des traces dans la fiche) : pas de choix de la meilleure
paire, qui multiplierait les tests. Une corrélation n'est pas une cause : la mesure dit le délai et l'ampleur d'un lien
déjà posé par une lecture ; elle ne crée aucune relation.

    python calibrer.py            # écrit registre/calibration.json et affiche le bilan
"""
from __future__ import annotations

import json
import math
import statistics
import sys
from datetime import date
from pathlib import Path
from statistics import NormalDist

import adaptateurs as ad
import carte
import ecosystemes as ec

SORTIE = Path("registre/calibration.json")
RETARD_MAX = 12
N_MIN = 24
ALPHA = 0.05
SEUIL_REGLE = 1.5
# Les comptes à rebours (jours jusqu'à la prochaine échéance) sont des calendriers, pas des intensités : leur différence
# vaut −1 par jour sauf au saut ; les corréler fabrique des liens. Exclus de la mesure.
from carte import COMPTES_A_REBOURS  # noqa: E402  (une seule liste, partagée avec la carte)


def pas_jours(serie: list[tuple[str, float]]) -> float:
    d = [date.fromisoformat(x[0][:10]) for x in serie[-60:]]
    e = sorted((b - a).days for a, b in zip(d, d[1:]))
    return e[len(e) // 2] if e else 1


def regrouper(serie: list[tuple[str, float]], pas: str) -> dict[str, float]:
    paquets: dict[str, list[float]] = {}
    for j, v in serie:
        d = date.fromisoformat(j[:10])
        if d > date.today():                       # calendriers tournés vers l'avenir : on ne garde que le passé
            continue
        k = f"{d.isocalendar()[0]}-S{d.isocalendar()[1]:02d}" if pas == "semaine" else d.strftime("%Y-%m")
        paquets.setdefault(k, []).append(v)
    return {k: statistics.mean(v) for k, v in paquets.items()}


def reduire(v: list[float]) -> list[float]:
    m, s = statistics.mean(v), statistics.pstdev(v) or 1e-9
    return [(x - m) / s for x in v]


def aligner(sx: list, sy: list) -> tuple[list[float], list[float], str]:
    pas = "semaine" if max(pas_jours(sx), pas_jours(sy)) <= 10 else "mois"
    gx, gy = regrouper(sx, pas), regrouper(sy, pas)
    cles = sorted(set(gx) & set(gy))
    x, y = [gx[k] for k in cles], [gy[k] for k in cles]
    if len(x) < 3:
        return [], [], pas
    dx, dy = [b - a for a, b in zip(x, x[1:])], [b - a for a, b in zip(y, y[1:])]
    return reduire(dx), reduire(dy), pas


def correlation(a: list[float], b: list[float]) -> float:
    if len(a) < 3:
        return 0.0
    ma, mb = statistics.mean(a), statistics.mean(b)
    num = sum((p - ma) * (q - mb) for p, q in zip(a, b))
    den = math.sqrt(sum((p - ma) ** 2 for p in a) * sum((q - mb) ** 2 for q in b)) or 1e-12
    return num / den


def pente(a: list[float], b: list[float]) -> float:
    ma, mb = statistics.mean(a), statistics.mean(b)
    v = sum((p - ma) ** 2 for p in a) or 1e-12
    return sum((p - ma) * (q - mb) for p, q in zip(a, b)) / v


def ajuster_masse_critique(x: list[float], y: list[float]) -> dict:
    """Schelling : y ≈ b · x · (0,3 + 1,2 · Φ((|x| − mu)/sigma)), seuils individuels distribués (mu, sigma) ; grille fixe,
    b par moindres carrés ; comparée à la droite y ≈ b · x par le BIC (2 paramètres de plus)."""
    n = len(x)
    def sse(m):
        num = sum(p * mm * q for p, mm, q in zip(x, m, y))
        den = sum((p * mm) ** 2 for p, mm in zip(x, m)) or 1e-12
        b = num / den
        return sum((q - b * p * mm) ** 2 for p, mm, q in zip(x, m, y))
    lin = sse([1.0] * n)
    best = min(((sse([0.3 + 1.2 * carte.repartition(abs(p), mu, sg) for p in x]), mu, sg)
                for mu in (0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0, 2.5, 3.0) for sg in (0.1, 0.25, 0.5, 1.0)))
    bic = lambda e, k: n * math.log(max(e, 1e-12) / n) + k * math.log(n)
    return {"mu": best[1], "sigma": best[2], "delta_bic": round(bic(lin, 1) - bic(best[0], 3), 2)}


def mesurer(x: list[float], y: list[float], pas: str) -> dict:
    """Retard, signe, poids, significativité et règle d'une relation x → y (séries déjà alignées et réduites)."""
    meilleurs = []
    for k in range(RETARD_MAX + 1):
        a, b = x[: len(x) - k], y[k:]
        if len(a) >= N_MIN:
            meilleurs.append((abs(correlation(a, b)), k, correlation(a, b), len(a)))
    if not meilleurs:
        return {"verdict": "chevauchement_insuffisant", "n": len(x)}
    _, k, r, n = max(meilleurs)
    z = NormalDist().inv_cdf(1 - ALPHA / (2 * (RETARD_MAX + 1)))
    out = {"verdict": "significatif" if abs(r) * math.sqrt(n) > z else "non_significatif", "r": round(r, 3), "n": n,
           "retard": k, "pas": pas, "delai_jours": k * (7 if pas == "semaine" else 30),
           "signe": "+" if r > 0 else "-", "poids": round(min(1.0, 2 * abs(r)), 3)}
    a, b = x[: len(x) - k], y[k:]
    haut = [(p, q) for p, q in zip(a, b) if abs(p) > SEUIL_REGLE]
    bas = [(p, q) for p, q in zip(a, b) if abs(p) <= SEUIL_REGLE]
    if len(haut) >= 6 and len(bas) >= 12:
        ph, pb = abs(pente(*zip(*haut))), abs(pente(*zip(*bas)))
        rapport = ph / max(pb, 1e-6)
        out["rapport_pentes"] = round(rapport, 2)
        out["regle"] = "seuil" if rapport > 1.5 else "saturation" if rapport < 0.67 else "proportionnelle"
        if out["regle"] == "seuil":
            out["seuil"] = SEUIL_REGLE
            mc = ajuster_masse_critique(a, b)
            out.update(mc)
            if mc.get("delta_bic", 0) > 2:                 # la courbe en S explique mieux qu'une droite : masse critique
                out["regle"] = "masse_critique"
    return out


def mesurer_modulation(m: list[float], x: list[float], y: list[float], retard: int) -> dict:
    """La relation x → y est-elle plus forte quand le modulateur m est haut ? (trois séries alignées, réduites)"""
    k = retard
    tri = list(zip(m[: len(m) - k], x[: len(x) - k], y[k:]))
    if len(tri) < 2 * N_MIN:
        return {"verdict": "chevauchement_insuffisant", "n": len(tri)}
    med = statistics.median(abs(t[0]) for t in tri)
    hauts = [t for t in tri if abs(t[0]) > med]
    bas = [t for t in tri if abs(t[0]) <= med]
    rh = correlation([t[1] for t in hauts], [t[2] for t in hauts])
    rb = correlation([t[1] for t in bas], [t[2] for t in bas])
    zf = (math.atanh(max(-0.999, min(0.999, rh))) - math.atanh(max(-0.999, min(0.999, rb)))) / math.sqrt(
        1 / max(len(hauts) - 3, 1) + 1 / max(len(bas) - 3, 1))
    d_int = statistics.mean(abs(t[0]) for t in hauts) - statistics.mean(abs(t[0]) for t in bas)
    gain = (abs(rh) - abs(rb)) / max(abs(rb), 0.1) / max(d_int, 1e-6)
    return {"verdict": "significatif" if abs(zf) > NormalDist().inv_cdf(1 - ALPHA / 2) and abs(rh) > abs(rb) else "non_significatif",
            "r_haut": round(rh, 3), "r_bas": round(rb, 3), "n": len(tri), "z_fisher": round(zf, 2),
            "gain": round(max(0.0, min(1.5, gain)), 3)}


# Ajzen (Attitudes, Personality and Behavior), principe de COMPATIBILITÉ : une mesure ne prédit une autre que si elles
# portent sur la même action, la même cible, le même contexte et le même temps. Ici, le contexte le plus sûr à lire est
# le lieu : dans la fiche générique « humain » (et ses ponts), où une relation décrit UNE population, une mesure entre
# séries de pays différents est déclarée « incompatible » et la carte ne l'utilise pas. Ailleurs (géopolitique,
# finance), relier deux pays est le propos même : pas de contrôle. Lieu inconnu ou mondial : pas de contrôle.
VILLES = {"delhi": "IN", "houston": "US", "berlin": "DE", "shanghai": "CN", "kyiv": "UA", "moscou": "RU",
          "teheran": "IR", "bandar_abbas": "IR"}
ISO3 = {"RUS": "RU", "UKR": "UA", "ISR": "IL", "IRN": "IR", "USA": "US", "LBN": "LB", "CHN": "CN", "TWN": "TW"}
NOMS = {"Sudan": "SD", "Ukraine": "UA", "Palestine": "PS", "Yemen": "YE", "Israel": "IL", "Lebanon": "LB", "Syria": "SY"}
FRED_MONDE = {"PFOODINDEXM", "DCOILBRENTEU", "ECBDFR"}
GEO = {"manifestations", "hostilites", "paire", "paire_mois", "dyade", "ooni", "feux", "sanctions", "violations", "ucdp",
       "prix_alimentaires", "acaps", "acaps_risques", "radar", "avions", "voisins", "sanctions_chine"}


def lieux(adaptateur: str) -> set[str] | None:
    """Pays d'une série (codes ISO2), None si inconnu ou mondial."""
    nom, *par = adaptateur.split(":")
    if nom == "fred":
        return None if par and par[0] in FRED_MONDE else {"US"}
    if nom in ("meteo", "climat"):
        return {VILLES[par[0]]} if par and par[0] in VILLES else None
    if nom == "federal_register" or nom == "congres" or nom == "tribunaux":
        return {"US"}
    if nom not in GEO:
        return None
    out = set()
    for x in par:
        if len(x) == 2 and x.isupper():
            out.add(x)
        elif x in ISO3:
            out.add(ISO3[x])
        elif x in NOMS:
            out.add(NOMS[x])
    return out or None


def compatibles(ax: str, ay: str) -> bool:
    a, b = lieux(ax), lieux(ay)
    return a is None or b is None or bool(a & b)


def lire_serie(adaptateur: str, reg: Path) -> list:
    if adaptateur.split(":")[0] in COMPTES_A_REBOURS:
        return []
    try:
        s = ad.lire(adaptateur, reg)
    except Exception:
        return []
    return s if len(s) >= N_MIN else []


def mesurer_asymetrie(x: list[float], y: list[float], retard: int, sens_perte: float) -> dict:
    """Kahneman, aversion aux pertes : y = b·x + c·x·[x dans le sens de la perte] ; λ = |b + c| / |b| ; c testé (t)."""
    a, b = x[: len(x) - retard], y[retard:]
    d = [1.0 if (p > 0) == (sens_perte > 0) else 0.0 for p in a]
    x1, x2 = a, [p * q for p, q in zip(a, d)]
    s11, s22, s12 = sum(v * v for v in x1), sum(v * v for v in x2), sum(p * q for p, q in zip(x1, x2))
    s1y, s2y = sum(p * q for p, q in zip(x1, b)), sum(p * q for p, q in zip(x2, b))
    det = s11 * s22 - s12 * s12
    n = len(a)
    if det <= 1e-9 or n < N_MIN or sum(d) < 6 or n - sum(d) < 6:
        return {"lambda_verdict": "insuffisant"}
    cb = (s11 * s2y - s12 * s1y) / det
    bb = (s22 * s1y - s12 * s2y) / det
    res = [q - bb * p - cb * r for p, r, q in zip(x1, x2, b)]
    s2 = sum(e * e for e in res) / max(n - 2, 1)
    se_c = math.sqrt(s2 * s11 / det)
    lam = abs(bb + cb) / max(abs(bb), 1e-6)
    return {"lambda_pertes": round(min(lam, 5.0), 2), "t_asymetrie": round(cb / max(se_c, 1e-12), 2),
            "lambda_significatif": abs(cb / max(se_c, 1e-12)) > NormalDist().inv_cdf(1 - ALPHA / 2)}


def persistance(serie: list[tuple[str, float]]) -> dict:
    """Kahneman, ch. 17 : le retour vers la moyenne. AR(1) sur la série au pas naturel (semaine ou mois), tendance
    linéaire retirée : φ, puis le temps caractéristique τ = −pas / ln φ (jours) que la simulation utilise."""
    pas = "semaine" if pas_jours(serie) <= 10 else "mois"
    g = regrouper(serie, pas)
    v = [g[k] for k in sorted(g)]
    n = len(v)
    if n < N_MIN:
        return {}
    t = list(range(n))
    b = pente(t, v)
    m = statistics.mean(v) - b * statistics.mean(t)
    e = [y - (m + b * i) for i, y in zip(t, v)]
    phi = correlation(e[:-1], e[1:])
    j = 7 if pas == "semaine" else 30
    out = {"phi": round(phi, 3), "pas": pas, "n": n}
    if 0 < phi < 0.999:
        out["tau_jours"] = round(-j / math.log(phi), 1)
    return out


def premiere_serie(noeud: dict, reg: Path) -> tuple[str | None, list]:
    for tr in noeud.get("traces") or []:
        if tr.get("adaptateur") and tr["adaptateur"].split(":")[0] not in COMPTES_A_REBOURS:
            try:
                s = ad.lire(tr["adaptateur"], reg)
            except Exception:
                continue
            if len(s) >= N_MIN:
                return tr["adaptateur"], s
    return None, []


def calibrer(dossier: Path = ec.DOSSIER, reg: Path = ad.REG) -> dict:
    s = ec.assembler(ec.charger(dossier))
    noeuds = {n["id"]: n for n in s["noeuds"]}
    series = {nid: premiere_serie(n, reg) for nid, n in noeuds.items()}
    rel, raisons = {}, {}
    par_cle = {f"{r['de']}>{r['vers']}": r for r in s["relations"]}
    for cle, r in par_cle.items():
        if r.get("module"):
            continue
        if r["de"] == r["vers"]:
            raisons["boucle_sur_soi"] = raisons.get("boucle_sur_soi", 0) + 1
            continue
        (ax, sx), (ay, sy) = series[r["de"]], series[r["vers"]]
        if r.get("series"):                        # la fiche impose la paire (même lieu aux deux bouts)
            ax, ay = r["series"]
            sx, sy = lire_serie(ax, reg), lire_serie(ay, reg)
            ax, ay = (ax if sx else None), (ay if sy else None)
        if ax and ax == ay:
            raisons["meme_serie"] = raisons.get("meme_serie", 0) + 1
            continue
        if not ax or not ay:
            k = "source_sans_serie" if not ax else "cible_sans_serie"
            raisons[k] = raisons.get(k, 0) + 1
            continue
        x, y, pas = aligner(sx, sy)
        m = mesurer(x, y, pas) if x else {"verdict": "chevauchement_insuffisant", "n": 0}
        if "humain:" in cle and not compatibles(ax, ay) and m["verdict"] in ("significatif", "non_significatif"):
            m["verdict_brut"], m["verdict"] = m["verdict"], "incompatible"
        par = r.get("parametres") or {}
        if "lambda_pertes" in par and x and "retard" in m:
            m.update(mesurer_asymetrie(x, y, m["retard"], float(par.get("sens_perte", -1))))
        m.update(source=ax, cible=ay, effet_ecrit=r.get("effet"),
                 concorde=(None if r.get("effet") in ("±", "0") or "signe" not in m else m["signe"] == r.get("effet")))
        rel[cle] = m
    for r in s["relations"]:
        if not r.get("module"):
            continue
        cible = par_cle.get(r["module"])
        (am, sm) = series[r["de"]]
        if not cible or not am or not series[cible["de"]][0] or not series[cible["vers"]][0]:
            raisons["modulation_sans_series"] = raisons.get("modulation_sans_series", 0) + 1
            continue
        pas = "semaine" if max(pas_jours(sm), pas_jours(series[cible["de"]][1]), pas_jours(series[cible["vers"]][1])) <= 10 else "mois"
        g = [regrouper(x, pas) for x in (sm, series[cible["de"]][1], series[cible["vers"]][1])]
        cles = sorted(set(g[0]) & set(g[1]) & set(g[2]))
        v = [[gi[k] for k in cles] for gi in g]
        d = [reduire([b - a for a, b in zip(s_, s_[1:])]) if len(s_) > 3 else [] for s_ in v]
        retard = (rel.get(r["module"]) or {}).get("retard", 0)
        mm = mesurer_modulation(*d, retard) if d[0] else {"verdict": "chevauchement_insuffisant", "n": 0}
        mm.update(modulateur=am)
        rel[f"module:{r['de']}>{r['module']}"] = mm
    # Simon (architecture de la complexité, 1962) : un système complexe est « presque décomposable » — liens forts et
    # rapides à l'intérieur des sous-systèmes, faibles et lents entre eux. Test sur nos données : les ponts entre fiches
    # sont mesurés comme les relations, et le bilan compare |r| moyen dedans et entre.
    for p in s["ponts"]:
        if not p["resolu"] or p["de"] == p["vers"]:
            continue
        (ax, sx), (ay, sy) = series.get(p["de"], (None, [])), series.get(p["vers"], (None, []))
        if not ax or not ay or ax == ay:
            continue
        x, y, pas = aligner(sx, sy)
        m = mesurer(x, y, pas) if x else {"verdict": "chevauchement_insuffisant", "n": 0}
        if "humain:" in p["de"] + p["vers"] and not compatibles(ax, ay) and m["verdict"] in ("significatif", "non_significatif"):
            m["verdict_brut"], m["verdict"] = m["verdict"], "incompatible"
        m.update(source=ax, cible=ay, type=p.get("type", "influence"))
        rel[f"pont:{p['de']}>{p['vers']}"] = m
    comp = {nid: dict(persistance(sr), serie=a) for nid, (a, sr) in series.items() if a}
    comp = {k: v for k, v in comp.items() if "phi" in v}
    def moy(sel):
        v = [abs(m["r"]) for k, m in rel.items() if sel(k) and "r" in m]
        return {"n": len(v), "r_moyen": round(statistics.mean(v), 3) if v else None}
    decomposabilite = {"dedans": moy(lambda k: not k.startswith(("pont:", "module:"))), "entre": moy(lambda k: k.startswith("pont:"))}
    bilan = {"relations": len(s["relations"]), "mesurees": len(rel), "compartiments_persistance": len(comp),
             "decomposabilite": decomposabilite,
             "incompatibles": sum(v["verdict"] == "incompatible" for v in rel.values()),
             "significatives": sum(v["verdict"] == "significatif" for v in rel.values()),
             "signe_contredit": sum(v.get("concorde") is False and v["verdict"] == "significatif" for v in rel.values()),
             "non_calibrables": raisons}
    return {"date": date.today().isoformat(), "methode": {"retard_max": RETARD_MAX, "n_min": N_MIN, "alpha": ALPHA,
                                                          "seuil_regle": SEUIL_REGLE},
            "bilan": bilan, "relations": rel, "compartiments": comp}


def principal() -> int:
    out = calibrer()
    SORTIE.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(out["bilan"], ensure_ascii=False))
    for k, v in sorted(out["relations"].items(), key=lambda kv: -abs(kv[1].get("r", kv[1].get("r_haut", 0)) or 0)):
        if v["verdict"] == "significatif":
            print(f"{k:<80} r {v.get('r', v.get('r_haut'))} retard {v.get('retard', '-')} {v.get('pas', '')} "
                  f"règle {v.get('regle', '-')} concorde {v.get('concorde')}")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
