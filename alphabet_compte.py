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
    """Série strictement positive, à tendance nette (au moins trois pas sur quatre dans le même sens) et dont les pas
    grandissent avec le niveau (seconde moitié des pas absolus au moins 1,5 fois la première) : croissance relative."""
    vals = [x for _, x in v]
    if len(vals) < 6 or min(vals) <= 0:
        return False
    incr = [vals[i + 1] - vals[i] for i in range(len(vals) - 1)]
    part_hausse = sum(1 for x in incr if x > 0) / len(incr)
    if 0.25 < part_hausse < 0.75:
        return False
    moitie = len(incr) // 2
    a = sum(abs(x) for x in incr[:moitie]) / max(1, moitie)
    b = sum(abs(x) for x in incr[moitie:]) / max(1, len(incr) - moitie)
    return a > 0 and b / a >= 1.5


def _niveaux(pts: list[dict], W: int, seuil: float, sens: str) -> dict | None:
    """Série de NIVEAUX : le seuil se juge par rapport à la DERNIÈRE valeur. On compte, sur toutes les fenêtres
    glissantes de W jours de l'historique, la part où la série s'est déplacée d'au moins l'écart actuel (dans le sens
    de la condition). Lissage (k + 0,5) / (n + 1)."""
    v = [(date.fromisoformat(p["date"]), p["valeur"]) for p in pts if isinstance(p.get("valeur"), (int, float))]
    if len(v) < 6:
        return None
    dernier = v[-1][1]
    haut = sens in (">=", ">")
    ecart = (seuil - dernier) if haut else (dernier - seuil)
    if ecart <= 0:
        n = len(v)
        return {"frequence": 1 - 0.5 / (n + 1), "k": n, "n": n, "methode": "deja_rempli"}
    # bootstrap des variations observées : chemins futurs tirés parmi les pas réels de la série (sans forme supposée)
    import random as _r
    ecarts_j = sorted((v[i + 1][0] - v[i][0]).days for i in range(len(v) - 1))
    pas_j = max(1, ecarts_j[len(ecarts_j) // 2])
    m = max(1, round(W / pas_j))
    incr = [v[i + 1][1] - v[i][1] for i in range(len(v) - 1)]
    # 0.10.19 : série en CROISSANCE (dépenses publiques, PIB, dette, prix, calcul…) : les pas absolus anciens sont
    # bien plus petits que les récents, et les rejouer sous-estime l'avenir (cas FYONET du 2026-11-11 : seuil jamais
    # atteint, taux de base près de 0,1 alors que la tendance l'atteint). On rejoue alors les pas RELATIFS (log), et
    # l'écart à franchir devient log(seuil / dernière valeur).
    if croissance(v):
        incr = [math.log(v[i + 1][1] / v[i][1]) for i in range(len(v) - 1)]
        ecart = math.log(seuil / dernier) if haut else math.log(dernier / seuil)
        multiplicatif = True
    else:
        multiplicatif = False
    if not haut:
        incr = [-x for x in incr]
    rnd = _r.Random(len(v) * 7919 + m)
    N = 2000
    hits = 0
    for _ in range(N):
        y = 0.0
        for _ in range(m):
            y += incr[rnd.randrange(len(incr))]
            if y >= ecart:
                hits += 1
                break
    return {"frequence": (hits + 0.5) / (N + 1), "k": hits, "n": N,
            "methode": "bootstrap_pas_relatifs" if multiplicatif else "bootstrap_pas", "pas_jours": pas_j, "pas": m}
    k = n = 0
    for i, (d0, x0) in enumerate(v):
        fin_f = d0 + timedelta(days=W)
        if fin_f > v[-1][0]:
            break
        suite = [x for d, x in v[i + 1:] if d <= fin_f]
        if not suite:
            continue
        mouv = (max(suite) - x0) if haut else (x0 - min(suite))
        n += 1
        k += mouv >= ecart
    if n < 5:
        return None
    return {"frequence": (k + 0.5) / (n + 1), "k": k, "n": n, "methode": "ecart_glissant"}


def compter(releve: dict, fenetre_jours: int, mode: str = "atteint", seuil: float | None = None, sens: str = ">=",
            agregation: str | None = None, fin: date | None = None, nature: str | None = None) -> dict:
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
        r = _niveaux(pts, int(fenetre_jours), seuil, sens)
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
