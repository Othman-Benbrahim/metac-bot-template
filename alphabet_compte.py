"""Le compte des puits de données (0.9.5) : la fréquence à laquelle une série a rempli la condition d'une question,
sur des fenêtres de la durée de la question. C'est le taux de base calculé par le code (bras B).

Sorti d'alphabet_puits.py pour être le SEUL fichier modifiable par la boucle du banc d'essai `banc/compte/` (juge et
corpus verrouillés : séries simulées dont la vraie probabilité est connue). Mesure :

    uv run python banc/compte/juge.py
"""
from __future__ import annotations

import math
from datetime import date, timedelta


def _jour(v) -> str | None:
    import re
    s = str(v or "").strip()
    m = re.match(r"(\d{4})(?:-?(\d{2}))?(?:-?(\d{2}))?", s)
    if not m:
        return None
    return f"{m.group(1)}-{m.group(2) or '01'}-{m.group(3) or '01'}"


def _agreger(points: list[dict], agregation: str | None) -> list[dict]:
    if agregation not in ("mois", "annee"):
        return points
    cles: dict[str, float] = {}
    for p in points:
        k = p["date"][:7] + "-01" if agregation == "mois" else p["date"][:4] + "-01-01"
        cles[k] = cles.get(k, 0.0) + (p["valeur"] if p.get("valeur") is not None else 1.0)
    return [{"date": k, "valeur": v} for k, v in sorted(cles.items())]


def _remplit(v: float | None, seuil: float | None, sens: str) -> bool:
    if seuil is None:
        return True                                         # un événement suffit
    if v is None:
        return False
    return v >= seuil if sens == ">=" else v > seuil if sens == ">" else v <= seuil if sens == "<=" else v < seuil


def _taux(pts: list[dict], debut: date, fin: date, W: int, seuil, sens: str) -> dict | None:
    """Événements : taux d'arrivée estimé sur TOUT l'historique, (k + 0,5) / durée, puis P(au moins un en W jours)
    = 1 − exp(−taux·W) (processus de Poisson). Plus efficace que des fenêtres disjointes, sans effet d'alignement."""
    import math
    duree = (fin - debut).days
    if duree < 2 * W or duree < 365:
        return None
    k = sum(1 for p in pts if debut.isoformat() < p["date"] <= fin.isoformat() and _remplit(p.get("valeur"), seuil, sens))
    # pondération vers le récent SEULEMENT si les deux moitiés de l'historique diffèrent nettement (test binomial
    # approché : sous un taux constant, la part des événements tombés dans la seconde moitié suit B(k, ½))
    milieu = (debut + timedelta(days=duree // 2)).isoformat()
    k2 = sum(1 for p in pts if milieu < p["date"] <= fin.isoformat() and _remplit(p.get("valeur"), seuil, sens))
    if k < 4 or abs(k2 - k / 2) < 2 * math.sqrt(k / 4):
        taux = (k + 0.5) / duree
        f = 1 - math.exp(-taux * W)
        return {"frequence": min(f, 1 - 1e-3), "k": k, "n": round(duree / W, 1), "methode": "taux_poisson"}
    h = duree / 6
    lam = math.log(2) / h
    poids = sum(math.exp(-lam * (fin - date.fromisoformat(p["date"])).days) for p in pts
                if debut.isoformat() < p["date"] <= fin.isoformat() and _remplit(p.get("valeur"), seuil, sens))
    expo = (1 - math.exp(-lam * duree)) / lam                       # durée effective pondérée
    taux = (poids + 0.5 * expo / duree) / expo
    f = 1 - math.exp(-taux * W)
    return {"frequence": min(f, 1 - 1e-3), "k": k, "n": round(duree / W, 1), "methode": "taux_poisson"}


def croissance(v: list[tuple]) -> bool:
    """Croissance RELATIVE : série strictement positive, à dérive nette (t de la moyenne des pas en log au-delà de 2)
    et dont les pas sont plus homogènes en log qu'en valeur absolue, ou à dérive relative très nette (t ≥ 5)."""
    vals = [x for _, x in v]
    if len(vals) < 6 or min(vals) <= 0:
        return False
    lg = [math.log(vals[i + 1] / vals[i]) for i in range(len(vals) - 1)]
    n = len(lg)
    moy = sum(lg) / n
    sd = math.sqrt(sum((x - moy) ** 2 for x in lg) / max(1, n - 1))
    if sd == 0 or abs(moy) / (sd / math.sqrt(n)) < 2:
        return False
    t = abs(moy) / (sd / math.sqrt(n))
    li = [vals[i + 1] - vals[i] for i in range(n)]
    h = n // 2

    def rapport(xs):
        a_, b_ = sum(abs(x) for x in xs[:h]) / max(1, h), sum(abs(x) for x in xs[h:]) / max(1, n - h)
        return abs(math.log(b_ / a_)) if a_ > 0 and b_ > 0 else float("inf")
    # pas plus homogènes en log qu'en valeur entre les deux moitiés de l'historique ; ou dérive relative très nette
    # (t ≥ 5), où rejouer des pas absolus anciens sous-estime toujours l'avenir
    return rapport(lg) < rapport(li) or t >= 5


def _robuste(xs: list[float]) -> tuple[list[int], int]:
    """Indices gardés après retrait des chocs ponctuels : pas à plus de 6 écarts robustes (MAD) de la médiane."""
    if len(xs) < 8:
        return list(range(len(xs))), 0
    med = sorted(xs)[len(xs) // 2]
    mad = 1.4826 * sorted(abs(x - med) for x in xs)[len(xs) // 2]
    if mad <= 0:
        return list(range(len(xs))), 0
    garde = [i for i, x in enumerate(xs) if abs(x - med) <= 6 * mad]
    return (garde, len(xs) - len(garde)) if garde else (list(range(len(xs))), 0)


def _ar1(y: list[float], garde: list[int]) -> tuple | None:
    """Régression Δy(t) = a + b·y(t−1) sur les pas gardés. Rend (a, b, résidus, t de b) si t < −2,5 (au moins 24
    pas), sinon None. Entre −2,5 et −3,5 (zone où une marche aléatoire peut tromper, Dickey-Fuller), le compte MÉLANGE
    les deux modèles ; sous −3,5, il retient l'AR(1)."""
    xs = [y[i] for i in garde]
    ds = [y[i + 1] - y[i] for i in garde]
    n = len(xs)
    if n < 24:
        return None
    mx, md = sum(xs) / n, sum(ds) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    if sxx <= 0:
        return None
    b = sum((x - mx) * (d - md) for x, d in zip(xs, ds)) / sxx
    a = md - b * mx
    res = [d - a - b * x for x, d in zip(xs, ds)]
    s2 = sum(r * r for r in res) / max(1, n - 2)
    t = b / math.sqrt(s2 / sxx) if s2 > 0 else 0.0
    return (a, b, res, t) if t < -2.5 and -1 < b < 0 else None


def _niveaux(pts: list[dict], W: int, seuil: float, sens: str, bornes: tuple | None = None) -> dict | None:
    """Série de NIVEAUX : le seuil se juge par rapport à la DERNIÈRE valeur ; chemins futurs simulés à partir des pas
    réellement observés (bootstrap lissé). 0.10.19, quatre pièges traités, chacun mesuré par le juge 2 :
      - croissance relative (dépenses, PIB, prix…) : pas rejoués en log ;
      - série bornée (pourcentage) : pas rejoués sur l'échelle logit, si les bornes sont déclarées ;
      - choc ponctuel : pas extrêmes (plus de 6 MAD) retirés ;
      - retour vers la moyenne (taux, chômage) : processus AR(1) estimé, résidus rejoués."""
    v = [(date.fromisoformat(p["date"]), p["valeur"]) for p in pts if isinstance(p.get("valeur"), (int, float))]
    if len(v) < 6:
        return None
    dernier = v[-1][1]
    haut = sens in (">=", ">")
    if (seuil - dernier if haut else dernier - seuil) <= 0:
        n = len(v)
        return {"frequence": 1 - 0.5 / (n + 1), "k": n, "n": n, "methode": "deja_rempli"}
    N = 2000
    espace = "valeur"
    if bornes and bornes[0] < bornes[1]:
        lo, hi = float(bornes[0]), float(bornes[1])
        if (haut and seuil >= hi) or (not haut and seuil <= lo):
            return {"frequence": 0.5 / (N + 1), "k": 0, "n": N, "methode": "hors_bornes", "bornes": [lo, hi]}
        eps = 1e-4

        def f(x):
            u = min(1 - eps, max(eps, (x - lo) / (hi - lo)))
            return math.log(u / (1 - u))
        espace = "logit"
    elif croissance(v):
        f = math.log
        espace = "log"
    else:
        def f(x):
            return x
    y = [f(x) for _, x in v]
    cible = f(seuil)
    import random as _r
    ecarts_j = sorted((v[i + 1][0] - v[i][0]).days for i in range(len(v) - 1))
    pas_j = max(1, ecarts_j[len(ecarts_j) // 2])
    m = max(1, round(W / pas_j))
    incr = [y[i + 1] - y[i] for i in range(len(y) - 1)]
    garde, exclus = _robuste(incr)
    ar = _ar1(y, garde) if espace != "log" else None
    rnd = _r.Random(len(v) * 7919 + m)

    def simuler(tirage: list[float], a_b: tuple | None) -> int:
        mu_i = sum(tirage) / len(tirage)
        sd_i = math.sqrt(sum((x - mu_i) ** 2 for x in tirage) / max(1, len(tirage) - 1))
        h = 1.06 * sd_i * len(tirage) ** -0.2        # bootstrap LISSÉ : dépasse le plus grand pas observé
        hits = 0
        for _ in range(N):
            z = y[-1]
            for _ in range(m):
                e = tirage[rnd.randrange(len(tirage))] + (rnd.gauss(0, h) if h else 0.0)
                z = z + a_b[0] + a_b[1] * z + e if a_b else z + e
                if (z >= cible) if haut else (z <= cible):
                    hits += 1
                    break
        return hits
    poids_ar = 0.0 if not ar else min(1.0, max(0.0, (-ar[3] - 2.5) / 1.0))
    hits_rw = simuler([incr[i] for i in garde], None) if poids_ar < 1 else 0
    hits_ar = simuler(ar[2], ar[:2]) if ar else 0
    hits = round(poids_ar * hits_ar + (1 - poids_ar) * hits_rw)
    ar = ar if poids_ar > 0 else None
    methode = ("ar1" if poids_ar >= 1 else "ar1_melange") if ar else {"valeur": "bootstrap_pas", "log": "bootstrap_pas_relatifs",
                                 "logit": "bootstrap_pas_logit"}[espace]
    out = {"frequence": (hits + 0.5) / (N + 1), "k": hits, "n": N, "methode": methode, "espace": espace,
           "pas_jours": pas_j, "pas": m, "pas_exclus": exclus}
    if ar:
        out.update(phi=round(1 + ar[1], 4), poids_ar1=round(poids_ar, 2))
    return out


def compter(releve: dict, fenetre_jours: int, mode: str = "atteint", seuil: float | None = None, sens: str = ">=",
            agregation: str | None = None, fin: date | None = None, nature: str | None = None,
            bornes: tuple | list | None = None) -> dict:
    """Fenêtres DISJOINTES de la durée de la question, comptées à rebours depuis `fin` jusqu'au début du relevé.

    mode « evenement » : la fenêtre compte si au moins un point (filtré par le seuil s'il y en a un) y tombe ;
    mode « atteint »   : si au moins une valeur de la fenêtre remplit la condition ;
    mode « franchit »  : si la condition n'était PAS remplie au début de la fenêtre et l'est ensuite.
    Fréquence = k / n ; à 0 ou n, ramenée à 1/(2n) ou 1 - 1/(2n) (le moteur exige ]0, 1[). Moins de 5 fenêtres :
    pas de fréquence."""
    if mode not in ("evenement", "atteint", "franchit"):
        return {"frequence": None, "motif": f"mode inconnu : {mode}"}
    # 0.8.0 (audit M-13) : sommer une série de NIVEAUX (taux, indice, PIB) n'a pas de sens ; « atteint » et « franchit »
    # sans seuil non plus.
    if agregation in ("mois", "annee") and nature == "niveau":
        return {"frequence": None, "motif": "agrégation refusée : série de niveaux (seuls flux et événements se somment)"}
    if mode in ("atteint", "franchit") and seuil is None:
        return {"frequence": None, "motif": f"mode {mode} sans seuil"}
    pts = _agreger([p for p in releve.get("points") or [] if p.get("date")], agregation)
    if not pts or fenetre_jours < 1:
        return {"frequence": None, "motif": "relevé vide"}
    fin = fin or date.fromisoformat(releve.get("date_limite") or pts[-1]["date"])
    debut = date.fromisoformat(_jour(releve.get("debut")) or pts[0]["date"])
    W = timedelta(days=int(fenetre_jours))
    if mode == "evenement":
        r = _taux(pts, debut, fin, int(fenetre_jours), seuil, sens)
        if r is not None:
            return dict(r, fenetre_jours=int(fenetre_jours), mode=mode, seuil=seuil, sens=sens, agregation=agregation,
                        periode=f"{debut.isoformat()}/{fin.isoformat()}", dernier_point=pts[-1]["date"])
    if mode in ("atteint", "franchit") and nature == "niveau":
        r = _niveaux(pts, int(fenetre_jours), seuil, sens, tuple(bornes) if bornes else None)
        if r is not None:
            return dict(r, fenetre_jours=int(fenetre_jours), mode=mode, seuil=seuil, sens=sens, agregation=agregation,
                        periode=f"{debut.isoformat()}/{fin.isoformat()}", dernier_point=pts[-1]["date"])
    k = n = 0
    b = fin
    while b - W >= debut:
        a = b - W
        dans = [p for p in pts if a.isoformat() < p["date"] <= b.isoformat()]
        if mode == "evenement":
            ok = any(_remplit(p.get("valeur"), seuil, sens) for p in dans)
        else:
            avant = [p for p in pts if p["date"] <= a.isoformat()]
            if mode == "franchit" and not avant:
                b = a
                continue                                    # pas d'état initial connu : fenêtre non comptée
            ok = any(_remplit(p.get("valeur"), seuil, sens) for p in dans)
            if mode == "franchit":
                ok = ok and not _remplit(avant[-1].get("valeur"), seuil, sens)
        n += 1
        k += 1 if ok else 0
        b = a
    if n < 5:
        return {"frequence": None, "k": k, "n": n,
                "motif": f"trop peu de fenêtres de {fenetre_jours} jours dans le relevé ({n} < 5)"}
    f = k / n
    if k == 0:
        f = 1 / (2 * n)
    elif k == n:
        f = 1 - 1 / (2 * n)
    return {"frequence": f, "k": k, "n": n, "fenetre_jours": int(fenetre_jours), "mode": mode, "seuil": seuil,
            "sens": sens, "agregation": agregation, "periode": f"{debut.isoformat()}/{fin.isoformat()}",
            "dernier_point": pts[-1]["date"]}
