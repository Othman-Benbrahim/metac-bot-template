"""Brique « banque centrale : inertie de la Fed » (décision de l'auteur, 2026-11-24, 15 h 59 : « je te laisse le champ libre »).
Procédure : preenregistrements/banque-centrale.md, écrite et versée avant tout calcul.

Mécanisme (carte : inflation mondiale, banques centrales) : la Fed bouge par petits pas, dans la même direction, avec des
pauses. Échelle d'une réunion : B50 (baisse de 50 points ou plus), B25, M (maintien), H25, H50 (hausse de 50 ou plus).
Mesure : toutes les réunions programmées du FOMC (calendriers officiels 1994-2002 et 2007-2026, federalreserve.gov) et
tous les changements de cible (openmarket.htm et son archive), hors réunions tenues au plancher (borne haute ≤ 0,25 %).
État avant une réunion : sens du dernier changement, et s'il a eu lieu depuis la réunion précédente (« récent ») ou non
(« pause ») → quatre états. Probabilités : fréquences de l'échelle par état, plus 0,5 par case.
Plusieurs réunions : chaîne de Markov sur ces quatre états. Baisses comptées en pas de 25 points (B50 = 2).
Baisse d'urgence : taux annuel des baisses hors réunion programmée, hors temps passé au plancher.
Lecture du titre seul ; abstention sur tout ce qui n'est pas reconnu (présidence de la Fed, autres banques centrales…).
"""
from __future__ import annotations

import csv
import datetime as dt
import math
import re
from pathlib import Path

ICI = Path(__file__).resolve().parent
REUNIONS = ICI / "ecosystemes" / "fomc-reunions.csv"
CHANGEMENTS = ICI / "ecosystemes" / "fed-changements-taux.csv"
BARREAUX = ("B50", "B25", "M", "H25", "H50")
ETATS = ("baisse_recente", "pause_apres_baisse", "hausse_recente", "pause_apres_hausse")
LISSAGE = 0.5
PLANCHER = 0.25
POIDS = 0.25
ECART_MAX = 0.15
MOIS = {m: i + 1 for i, m in enumerate(("january", "february", "march", "april", "may", "june", "july", "august",
                                        "september", "october", "november", "december"))}
MOIS_COURTS = {m[:3]: i for m, i in MOIS.items()}
COUVERTURE = ((dt.date(1994, 1, 1), dt.date(2002, 12, 31)), (dt.date(2007, 1, 1), dt.date(2099, 12, 31)))
EXCLURE = re.compile(r"\b(chair|nominat\w*|powell|cook|warsh|governors?|differently|bank of england|ecb|bank of japan|boe|boj)\b", re.I)
J = dt.date.fromisoformat


def charger(reunions: Path = REUNIONS, changements: Path = CHANGEMENTS):
    R = sorted(J(r["fin"]) for r in csv.DictReader(reunions.open(encoding="utf-8")))
    C = sorted((J(r["date"]), int(r["points"]), float(r["niveau_haut"]))
               for r in csv.DictReader(changements.open(encoding="utf-8")))
    return R, C


def barreau(points: int) -> str:
    return "B50" if points <= -50 else "B25" if points < 0 else "M" if points == 0 else "H25" if points < 50 else "H50"


def _decision(fin: dt.date, C) -> int:
    for d, p, _ in C:
        if fin <= d <= fin + dt.timedelta(days=2):
            return p
    return 0


def _precedente(fin: dt.date, R) -> dt.date:
    av = [r for r in R if r < fin]
    if av and (fin - av[-1]).days <= 70:
        return av[-1]
    return fin - dt.timedelta(days=49)                      # trou du calendrier (2003-2006) : sept semaines


def etat(fin: dt.date, R, C, connu_avant: dt.date | None = None):
    """État avant la réunion qui se termine le `fin` (changements connus avant `connu_avant`, par défaut `fin`)."""
    borne = connu_avant or fin
    av = [(d, p, h) for d, p, h in C if d < min(fin, borne)]
    if not av:
        return None, None
    d, p, h = av[-1]
    recent = d >= _precedente(fin, R)
    if p < 0:
        return ("baisse_recente" if recent else "pause_apres_baisse"), h
    return ("hausse_recente" if recent else "pause_apres_hausse"), h


def _couverte(d: dt.date) -> bool:
    return any(a <= d <= b for a, b in COUVERTURE)


def table(R, C, jusqua: dt.date):
    """Fréquences de l'échelle par état, sur les réunions closes avant `jusqua`, hors plancher."""
    n = {e: {b: 0 for b in BARREAUX} for e in ETATS}
    for fin in R:
        if fin >= jusqua or not _couverte(fin):
            continue
        e, h = etat(fin, R, C)
        if e is None or h <= PLANCHER:
            continue
        n[e][barreau(_decision(fin, C))] += 1
    P = {}
    for e in ETATS:
        tot = sum(n[e].values()) + LISSAGE * len(BARREAUX)
        P[e] = {b: (n[e][b] + LISSAGE) / tot for b in BARREAUX}
    return P, n


def suivant(e: str, b: str) -> str:
    if b.startswith("B"):
        return "baisse_recente"
    if b.startswith("H"):
        return "hausse_recente"
    return {"baisse_recente": "pause_apres_baisse", "hausse_recente": "pause_apres_hausse"}.get(e, e)


def _unites(b: str) -> int:
    return {"B50": 2, "B25": 1}.get(b, 0)


def chaine(e0: str, P, k: int, evenement) -> float:
    """Probabilité que la suite de k barreaux vérifie `evenement(suite)` ; énumération exacte (5^k, k ≤ 8)."""
    tot = 0.0

    def rec(e, suite, p):
        nonlocal tot
        if len(suite) == k:
            if evenement(suite):
                tot += p
            return
        for b in BARREAUX:
            rec(suivant(e, b), suite + (b,), p * P[e][b])
    rec(e0, (), 1.0)
    return tot


def _reunion_du_mois(R, mois: int, annee: int):
    m = [r for r in R if r.year == annee and r.month == mois]
    return m[0] if m else None


def _taux_urgence(R, C, jusqua: dt.date) -> float:
    """Baisses hors réunion programmée par année d'exposition (au-dessus du plancher), avant `jusqua`."""
    hors = [d for d, p, _ in C if p < 0 and d < jusqua and _couverte(d)
            and not any(f <= d <= f + dt.timedelta(days=2) for f in R)]
    jours, niveau = 0, None
    jour = dt.date(1994, 1, 1)
    niv = {d: h for d, _, h in C}
    hist = sorted(niv)
    i = 0
    niveau = [h for d, _, h in C if d < jour][-1]
    while jour < jusqua:
        while i < len(hist) and hist[i] <= jour:
            niveau = niv[hist[i]]
            i += 1
        if _couverte(jour) and niveau > PLANCHER:
            jours += 1
        jour += dt.timedelta(days=1)
    return len(hors) / (jours / 365.25) if jours else 0.0


def reconnaitre(titre: str) -> dict | None:
    t = (titre or "").strip()
    if not re.search(r"\b(fed|federal reserve|fomc)\b", t, re.I) or EXCLURE.search(t):
        return None
    tl = t.lower().replace("–", "-").replace("—", "-")
    m = re.search(r"emergency rate cut in (\d{4})", tl)
    if m:
        return {"type": "urgence", "annee": int(m.group(1))}
    m = re.search(r"\b(cut|pause|hike)-(cut|pause|hike)-(cut|pause|hike)\b", tl)
    if m:
        seq = tuple(m.groups())
        mm = re.search(r"\((\w{3})-(\w{3})-(\w{3})\)", tl)
        ma = re.search(r"in (\d{4})", tl)
        if mm and all(x in MOIS_COURTS for x in mm.groups()):
            return {"type": "sequence", "seq": seq, "mois": tuple(MOIS_COURTS[x] for x in mm.groups())}
        if ma:
            return {"type": "sequence", "seq": seq, "annee": int(ma.group(1))}
        return None
    mr = re.search(r"(" + "|".join(MOIS) + r") (\d{4}) meeting", tl)
    reu = (MOIS[mr.group(1)], int(mr.group(2))) if mr else None
    if re.search(r"no change in fed interest rates after", tl) and reu:
        return {"type": "reunion", "reunion": reu, "barreaux": ("M",)}
    m = re.search(r"(increase|decrease)s? interest rates by (25|50)(\+?) bps after", tl)
    if m and reu:
        s = "H" if m.group(1) == "increase" else "B"
        b = (s + "50",) if m.group(2) == "50" else ((s + "25", s + "50") if m.group(3) else (s + "25",))
        return {"type": "reunion", "reunion": reu, "barreaux": b}
    m = re.search(r"rate (cut|hike) by (\w+) (\d{4}) meeting", tl)
    if m and m.group(2) in MOIS:
        return {"type": "au_moins_un", "sens": "B" if m.group(1) == "cut" else "H",
                "jusqua_reunion": (MOIS[m.group(2)], int(m.group(3)))}
    m = re.search(r"raise the federal funds target range before (\w+) (\d{1,2}), (\d{4})", tl)
    if m and m.group(1) in MOIS:
        return {"type": "au_moins_un", "sens": "H", "avant": dt.date(int(m.group(3)), MOIS[m.group(1)], int(m.group(2)))}
    m = re.search(r"(?:rate hike|hike interest rates) in (\d{4})", tl)
    if m:
        return {"type": "au_moins_un", "sens": "H", "annee": int(m.group(1))}
    m = re.search(r"\b(\d+)(\+?) fed rate cuts? happen in (\d{4})", tl) or \
        re.search(r"cut interest rates (\d+)()\s+times? in (\d{4})", tl)
    if m:
        return {"type": "compte", "n": int(m.group(1)), "au_moins": bool(m.group(2)), "annee": int(m.group(3))}
    m = re.search(r"no fed rate cuts happen in (\d{4})", tl)
    if m:
        return {"type": "compte", "n": 0, "au_moins": False, "annee": int(m.group(1))}
    return None


def probabilite(forme: dict, jeu: dt.date, R=None, C=None) -> float | None:
    """Probabilité de la brique pour une question reconnue, vue depuis la date `jeu` (rien après `jeu`)."""
    if R is None:
        R, C = charger()
    Ck = [x for x in C if x[0] < jeu]
    P, _ = table(R, Ck, jeu)
    futures = [r for r in R if r >= jeu]
    if not futures:
        return None

    def depart(premiere):
        e, h = etat(premiere, R, Ck, jeu)
        return e, h

    t = forme["type"]
    if t == "urgence":
        if forme["annee"] < jeu.year:
            return None
        if any(p < 0 and d.year == forme["annee"] and not any(f <= d <= f + dt.timedelta(days=2) for f in R)
               for d, p, _ in Ck):
            return 1.0
        reste = (dt.date(forme["annee"], 12, 31) - jeu).days / 365.25
        return 1 - math.exp(-_taux_urgence(R, Ck, jeu) * max(reste, 0))
    if t == "reunion":
        cible = _reunion_du_mois(R, *forme["reunion"])
        if cible is None or cible < jeu:
            return None
        avant = [r for r in futures if r <= cible]
        e, _ = depart(avant[0])
        return chaine(e, P, len(avant), lambda s: s[-1] in forme["barreaux"])
    if t == "au_moins_un":
        sens = forme["sens"]
        if "jusqua_reunion" in forme:
            cible = _reunion_du_mois(R, *forme["jusqua_reunion"])
            if cible is None:
                return None
            fen = [r for r in futures if r <= cible]
            deja = False
        elif "avant" in forme:
            fen = [r for r in futures if r < forme["avant"]]
            deja = False
        else:
            a = forme["annee"]
            fen = [r for r in futures if r.year == a]
            deja = any(d.year == a and ((p < 0) == (sens == "B")) for d, p, _ in Ck)
        if deja:
            return 1.0
        if not fen:
            return 0.0
        e, _ = depart(fen[0])
        return chaine(e, P, len(fen), lambda s: any(b.startswith(sens) for b in s))
    if t == "compte":
        a = forme["annee"]
        if a < jeu.year:
            return None
        faites = sum(-p // 25 for d, p, _ in Ck if d.year == a and p < 0)
        fen = [r for r in futures if r.year == a]
        n, aum = forme["n"], forme["au_moins"]
        ok = (lambda k: k >= n) if aum else (lambda k: k == n)
        if not fen:
            return 1.0 if ok(faites) else 0.0
        e, _ = depart(fen[0])
        return chaine(e, P, len(fen), lambda s: ok(faites + sum(_unites(b) for b in s)))
    if t == "sequence":
        if "mois" in forme:
            ans, reus = jeu.year, []
            # les trois mois se suivent dans le temps : on cherche la première réunion de chaque mois à partir de jeu - 1 an
            base = [r for r in R if r >= jeu - dt.timedelta(days=200)]
            for mo in forme["mois"]:
                c = next((r for r in base if r.month == mo and (not reus or r > reus[-1])), None)
                if c is None:
                    return None
                reus.append(c)
        else:
            reus = [r for r in R if r.year == forme["annee"]][-3:]
        if len(reus) != 3:
            return None
        voulu = {"cut": "B", "pause": "M", "hike": "H"}
        connues = [r for r in reus if r < jeu]
        for r, s in zip(reus, forme["seq"]):
            if r < jeu and barreau(_decision(r, Ck))[0] != voulu[s]:
                return 0.0
        reste = [r for r in reus if r >= jeu]
        if not reste:
            return 1.0
        k0 = len(connues)
        fen = [r for r in futures if r <= reste[-1]]
        idx = [fen.index(r) for r in reste]
        e, _ = depart(fen[0])
        return chaine(e, P, len(fen), lambda s: all(s[i][0] == voulu[forme["seq"][k0 + j]] for j, i in enumerate(idx)))
    return None


def _lg(p: float) -> float:
    p = min(max(p, .01), .99)
    return math.log(p / (1 - p))


def melanger(p_bot: float, p_regle: float) -> float:
    m = 1 / (1 + math.exp(-((1 - POIDS) * _lg(p_bot) + POIDS * _lg(p_regle))))
    return min(max(m, p_bot - ECART_MAX), p_bot + ECART_MAX)


def estimer(titre: str, jeu: dt.date | None = None) -> dict | None:
    forme = reconnaitre(titre)
    if forme is None:
        return None
    jeu = jeu or dt.date.today()
    try:
        p = probabilite(forme, jeu)
    except Exception:
        return None
    if p is None:
        return None
    return {"forme": forme, "p": min(max(p, .01), .99)}
