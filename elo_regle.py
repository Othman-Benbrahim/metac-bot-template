"""Brique « compétitions : force mesurée (Elo) » (preenregistrements/elo-competitions.md, écrite avant le calcul).
Coupe du monde 2026 (sélections, Elo du World Football Elo) et NFL 2025 (Elo nflverse) : notes recalculées sur les
seuls matchs joués avant la date ; simulation du format (20 000 tirages). Aucune cote, jamais.
"""
from __future__ import annotations

import csv
import datetime as dt
import io
import math
import random
import re
from collections import defaultdict
from functools import lru_cache

RESULTATS = "https://raw.githubusercontent.com/martj42/international_results/master/results.csv"
TIRS = "https://raw.githubusercontent.com/martj42/international_results/master/shootouts.csv"
NFL = "https://raw.githubusercontent.com/nflverse/nfldata/master/data/games.csv"
TIRAGES = 20000
NUL = 0.27
HOTES = {"United States", "Mexico", "Canada"}
FIN_BARRAGES = dt.date(2026, 4, 1)
POULES = (dt.date(2026, 6, 11), dt.date(2026, 6, 27))
ANCIENS = {"Uruguay", "Italy", "Germany", "Brazil", "England", "Argentina", "France", "Spain"}
ALIAS = {"usa": "United States", "usmnt": "United States", "us": "United States", "u.s.": "United States",
         "united states": "United States", "korea republic": "South Korea", "south korea": "South Korea",
         "czechia": "Czech Republic", "ivory coast": "Ivory Coast", "côte d'ivoire": "Ivory Coast",
         "curacao": "Curaçao", "türkiye": "Turkey", "turkiye": "Turkey", "dr congo": "DR Congo"}

NFL_EQUIPES = {
    "ARI": ("cardinals", "arizona"), "ATL": ("falcons", "atlanta"), "BAL": ("ravens", "baltimore"),
    "BUF": ("bills", "buffalo"), "CAR": ("panthers", "carolina"), "CHI": ("bears", "chicago"),
    "CIN": ("bengals", "cincinnati"), "CLE": ("browns", "cleveland"), "DAL": ("cowboys", "dallas"),
    "DEN": ("broncos", "denver"), "DET": ("lions", "detroit"), "GB": ("packers", "green bay"),
    "HOU": ("texans", "houston"), "IND": ("colts", "indianapolis"), "JAX": ("jaguars", "jacksonville"),
    "KC": ("chiefs", "kansas city"), "LV": ("raiders", "las vegas"), "LAC": ("chargers",), "LA": ("rams",),
    "MIA": ("dolphins", "miami"), "MIN": ("vikings", "minnesota"), "NE": ("patriots", "new england"),
    "NO": ("saints", "new orleans"), "NYG": ("giants",), "NYJ": ("jets",), "PHI": ("eagles", "philadelphia"),
    "PIT": ("steelers", "pittsburgh"), "SF": ("49ers", "san francisco"), "SEA": ("seahawks", "seattle"),
    "TB": ("buccaneers", "tampa bay"), "TEN": ("titans", "tennessee"), "WAS": ("commanders", "washington"),
}
DIVISIONS = {
    "AFC East": ["BUF", "MIA", "NE", "NYJ"], "AFC North": ["BAL", "CIN", "CLE", "PIT"],
    "AFC South": ["HOU", "IND", "JAX", "TEN"], "AFC West": ["DEN", "KC", "LV", "LAC"],
    "NFC East": ["DAL", "NYG", "PHI", "WAS"], "NFC North": ["CHI", "DET", "GB", "MIN"],
    "NFC South": ["ATL", "CAR", "NO", "TB"], "NFC West": ["ARI", "LA", "SF", "SEA"],
}
ANCIEN_CODE = {"OAK": "LV", "SD": "LAC", "STL": "LA"}


# ---- données -------------------------------------------------------------------------------------------------------
@lru_cache(maxsize=4)
def _texte(url: str) -> str:
    import httpx
    import politesse
    with httpx.Client(headers={"User-Agent": politesse.UA}) as c:
        r = c.get(url, timeout=60, follow_redirects=True)
        r.raise_for_status()
        return r.text


def resultats(texte: str | None = None) -> list[dict]:
    return list(csv.DictReader(io.StringIO(texte or _texte(RESULTATS))))


def tirs(texte: str | None = None) -> dict:
    return {(r["date"], r["home_team"], r["away_team"]): r["winner"] for r in csv.DictReader(io.StringIO(texte or _texte(TIRS)))}


def matchs_nfl(texte: str | None = None) -> list[dict]:
    return list(csv.DictReader(io.StringIO(texte or _texte(NFL))))


# ---- notes ---------------------------------------------------------------------------------------------------------
def k_selection(tournoi: str) -> float:
    t = tournoi.lower()
    if t == "fifa world cup":
        return 60
    if t in ("uefa euro", "copa américa", "african cup of nations", "afc asian cup", "gold cup", "confederations cup"):
        return 50
    if "qualification" in t:
        return 40
    if t == "friendly":
        return 20
    return 30


def elo_selections(rows: list[dict], avant: dt.date) -> dict[str, float]:
    R = defaultdict(lambda: 1500.0)
    a = avant.isoformat()
    for r in rows:
        if r["date"] >= a:
            break
        try:
            hs, as_ = int(r["home_score"]), int(r["away_score"])
        except ValueError:
            continue
        h, w_ = r["home_team"], r["away_team"]
        dr = R[h] - R[w_] + (0 if r["neutral"].upper() == "TRUE" else 100)
        we = 1 / (10 ** (-dr / 400) + 1)
        w = 1.0 if hs > as_ else 0.5 if hs == as_ else 0.0
        n = abs(hs - as_)
        k = k_selection(r["tournament"]) * (1 if n <= 1 else 1.5 if n == 2 else 1.75 + (n - 3) / 8)
        d = k * (w - we)
        R[h] += d
        R[w_] -= d
    return dict(R)


def elo_nfl(rows: list[dict], avant: dt.date) -> dict[str, float]:
    R, saison = defaultdict(lambda: 1505.0), None
    a = avant.isoformat()
    for r in sorted(rows, key=lambda r: (r["gameday"], r["game_id"])):
        if r["gameday"] >= a:
            break
        if not r["home_score"] or not r["away_score"]:
            continue
        if r["season"] != saison:
            saison = r["season"]
            for e in list(R):
                R[e] = R[e] * 2 / 3 + 1505 / 3
        h, w_ = ANCIEN_CODE.get(r["home_team"], r["home_team"]), ANCIEN_CODE.get(r["away_team"], r["away_team"])
        hs, as_ = int(r["home_score"]), int(r["away_score"])
        dr = R[h] + (0 if r.get("location") == "Neutral" else 48) - R[w_]
        e = 1 / (1 + 10 ** (-dr / 400))
        w = 1.0 if hs > as_ else 0.5 if hs == as_ else 0.0
        ecart = abs(hs - as_)
        mult = math.log(ecart + 1) * 2.2 / ((dr if w == 1 else -dr) * 0.001 + 2.2) if ecart else 1.0
        d = 20 * mult * (w - e)
        R[h] += d
        R[w_] -= d
    return dict(R)


def we(dr: float) -> float:
    return 1 / (1 + 10 ** (-dr / 400))


# ---- reconnaissance ------------------------------------------------------------------------------------------------
def _equipe_cdm(t: str, noms: set[str]) -> str | None:
    tl = t.lower()
    for a, n in ALIAS.items():
        if re.search(rf"(?<![\w.]){re.escape(a)}(?![\w])", tl):
            return n
    trouves = [n for n in noms if re.search(rf"\b{re.escape(n.lower())}\b", tl)]
    trouves = [n for n in trouves if not any(n != m and n.lower() in m.lower() for m in trouves)]
    return trouves[0] if len(trouves) == 1 else None


def _equipe_nfl(t: str) -> str | None:
    tl = t.lower()
    tr = [c for c, ms in NFL_EQUIPES.items() if any(re.search(rf"\b{re.escape(m)}\b", tl) for m in ms)]
    return tr[0] if len(tr) == 1 else None


def reconnaitre(titre: str, noms_cdm: set[str] | None = None) -> dict | None:
    t = titre or ""
    tl = t.lower()
    if re.search(r"top goalscorer|golden boot|mvp|rookie|coach|award|player|boycott|attend|visit|blue card|record|"
                 r"halftime|perform|trump|putin|neymar|messi|ronaldo|kane|haaland|mbapp|yamal|europe or|from europe|"
                 r"outside of europe|club world cup|women|u-?\d\d", tl):
        return None
    if re.search(r"world cup", tl) and not re.search(r"cricket|rugby|\bt20\b|ski|hockey|darts|esports|20(1\d|2[0-5])", tl):
        if re.search(r"first[- ]time winner|never won before", tl):
            return {"comp": "cdm", "forme": "premier_vainqueur"}
        if re.search(r"host nation", tl) and re.search(r"semi", tl):
            return {"comp": "cdm", "forme": "hote_demi"}
        e = _equipe_cdm(t, noms_cdm or set())
        if not e:
            return None
        m = re.search(r"win group ([a-l])\b", tl)
        if m:
            return {"comp": "cdm", "forme": "poule", "equipe": e, "poule": m.group(1).upper()}
        if re.search(r"out of the group stage|advance from the group|knockout stage", tl):
            return {"comp": "cdm", "forme": "sortie_poule", "equipe": e}
        if re.search(r"reach (the )?quarter", tl):
            return {"comp": "cdm", "forme": "quart", "equipe": e}
        if re.search(r"reach (the )?semi", tl):
            return {"comp": "cdm", "forme": "demi", "equipe": e}
        if re.search(r"(reach|make it to) the (?:[\w ]*?)\bfinal\b", tl) and not re.search(r"semi-?final|quarter-?final", tl):
            return {"comp": "cdm", "forme": "finale", "equipe": e}
        if re.search(r"\bwin\b", tl):
            return {"comp": "cdm", "forme": "titre", "equipe": e}
        return None
    if re.search(r"super bowl|\bnfl\b|\bafc\b|\bnfc\b", tl):
        e = _equipe_nfl(t)
        if not e:
            return None
        m = re.search(r"\b(afc|nfc) (east|north|south|west)\b", tl)
        if m and re.search(r"\bwin\b", tl):
            return {"comp": "nfl", "forme": "division", "equipe": e, "division": f"{m.group(1).upper()} {m.group(2).title()}"}
        if re.search(r"(afc|nfc) championship", tl):
            return {"comp": "nfl", "forme": "conference", "equipe": e}
        if re.search(r"win (the )?super bowl", tl) and re.search(r"super bowl (lx|2026)\b", tl):
            return {"comp": "nfl", "forme": "super_bowl", "equipe": e}
    return None


# ---- Coupe du monde 2026 -------------------------------------------------------------------------------------------
def _match_poule(ra: float, rb: float, rng: random.Random) -> tuple[int, int]:
    e = we(ra - rb)
    d = NUL * (1 - abs(2 * e - 1))
    u = rng.random()
    if u < e - d / 2:
        return 1, 0
    if u < e + d / 2:
        return 0, 0
    return 0, 1


def _note(R, e):
    return R.get(e, 1500.0) + (100 if e in HOTES else 0)


def cdm(rows: list[dict], shoot: dict, jour: dt.date, n: int = TIRAGES, graine: int = 1) -> dict:
    """Probabilités par équipe : titre, finale, demi, quart, sortie de poule, premier de poule ; et événements globaux."""
    R = elo_selections(rows, jour)
    j = jour.isoformat()
    m26 = [r for r in rows if r["tournament"] == "FIFA World Cup" and r["date"] >= "2026-06-01"]
    if jour >= FIN_BARRAGES:
        adj = defaultdict(set)
        for r in m26:
            if POULES[0].isoformat() <= r["date"] <= POULES[1].isoformat():
                adj[r["home_team"]].add(r["away_team"])
                adj[r["away_team"]].add(r["home_team"])
        poules, vus = [], set()
        for e in sorted(adj):
            if e in vus:
                continue
            pile, comp = [e], set()
            while pile:
                x = pile.pop()
                if x not in comp:
                    comp.add(x)
                    pile += list(adj[x])
            vus |= comp
            poules.append(sorted(comp))
    else:
        poules = None
    joues, elimines = {}, set()
    for r in m26:
        if r["date"] >= j:
            continue
        try:
            hs, as_ = int(r["home_score"]), int(r["away_score"])
        except ValueError:
            continue
        if r["date"] <= POULES[1].isoformat():
            joues[frozenset((r["home_team"], r["away_team"]))] = {r["home_team"]: hs, r["away_team"]: as_}
        else:
            if hs == as_:
                g = shoot.get((r["date"], r["home_team"], r["away_team"]))
            else:
                g = r["home_team"] if hs > as_ else r["away_team"]
            if g:
                elimines.add(r["away_team"] if g == r["home_team"] else r["home_team"])
    if poules is None:
        champ = sorted(R, key=lambda e: -R[e])
        champ = [e for e in champ if e not in HOTES][:45] + sorted(HOTES)
    else:
        champ = [e for p in poules for e in p]
    rng = random.Random(graine)
    C = {k: defaultdict(int) for k in ("titre", "finale", "demi", "quart", "sortie_poule", "premier")}
    nb_premier = nb_hote = 0
    for _ in range(n):
        if poules is None:
            ch = champ[:]
            rng.shuffle(ch)
            P = [ch[i * 4:i * 4 + 4] for i in range(12)]
        else:
            P = poules
        q1, q3 = [], []
        for p in P:
            pts, bd = defaultdict(int), defaultdict(int)
            for a in range(len(p)):
                for b in range(a + 1, len(p)):
                    x, y = p[a], p[b]
                    k = frozenset((x, y))
                    if k in joues:
                        gx, gy = joues[k][x], joues[k][y]
                    else:
                        sx, sy = _match_poule(_note(R, x), _note(R, y), rng)
                        marge = rng.randint(1, 3)
                        gx, gy = (marge, 0) if sx > sy else (0, marge) if sy > sx else (1, 1)
                    pts[x] += 3 if gx > gy else 1 if gx == gy else 0
                    pts[y] += 3 if gy > gx else 1 if gx == gy else 0
                    bd[x] += gx - gy
                    bd[y] += gy - gx
            cl = sorted(p, key=lambda e: (-pts[e], -bd[e], rng.random()))
            C["premier"][cl[0]] += 1
            q1 += cl[:2]
            if len(cl) > 2:
                q3.append((pts[cl[2]], bd[cl[2]], rng.random(), cl[2]))
        q3 = [x[3] for x in sorted(q3, key=lambda x: (-x[0], -x[1], x[2]))[:8]]
        tour = q1 + q3
        for e in tour:
            C["sortie_poule"][e] += 1
        rng.shuffle(tour)
        while len(tour) > 1:
            if len(tour) == 8:
                for e in tour:
                    C["quart"][e] += 1
            if len(tour) == 4:
                for e in tour:
                    C["demi"][e] += 1
                nb_hote += any(e in HOTES for e in tour)
            if len(tour) == 2:
                for e in tour:
                    C["finale"][e] += 1
            suiv = []
            for i in range(0, len(tour), 2):
                x, y = tour[i], tour[i + 1]
                if x in elimines and y not in elimines:
                    suiv.append(y)
                elif y in elimines and x not in elimines:
                    suiv.append(x)
                else:
                    suiv.append(x if rng.random() < we(_note(R, x) - _note(R, y)) else y)
            tour = suiv
        C["titre"][tour[0]] += 1
        nb_premier += tour[0] not in ANCIENS
    out = {k: {e: v / n for e, v in d.items()} for k, d in C.items()}
    out["premier_vainqueur"] = nb_premier / n
    out["hote_demi"] = nb_hote / n
    return out


# ---- NFL 2025 ------------------------------------------------------------------------------------------------------
def nfl_saison(rows: list[dict], jour: dt.date, saison: str = "2025", n: int = TIRAGES, graine: int = 1) -> dict:
    R = elo_nfl(rows, jour)
    j = jour.isoformat()
    jeux = [r for r in rows if r["season"] == saison and r["game_type"] == "REG"]
    if not any(r["gameday"] < j for r in jeux):          # avant la saison : retour d'un tiers vers la moyenne
        R = {e: v * 2 / 3 + 1505 / 3 for e, v in R.items()}
    div_de = {e: d for d, es in DIVISIONS.items() for e in es}
    rng = random.Random(graine)
    C = {k: defaultdict(int) for k in ("division", "conference", "super_bowl")}
    post = [r for r in rows if r["season"] == saison and r["game_type"] != "REG" and r["gameday"] < j and r["home_score"]]
    elimines = set()
    for r in post:
        hs, as_ = int(r["home_score"]), int(r["away_score"])
        elimines.add(r["away_team"] if hs > as_ else r["home_team"])
    for _ in range(n):
        v = defaultdict(float)
        for r in jeux:
            h, a = r["home_team"], r["away_team"]
            if r["gameday"] < j and r["home_score"]:
                hs, as_ = int(r["home_score"]), int(r["away_score"])
                res = 1.0 if hs > as_ else 0.5 if hs == as_ else 0.0
            else:
                res = 1.0 if rng.random() < we(R.get(h, 1505) + (0 if r.get("location") == "Neutral" else 48) - R.get(a, 1505)) else 0.0
            v[h] += res
            v[a] += 1 - res
        finalistes = []
        for conf in ("AFC", "NFC"):
            gagnants = []
            for d, es in DIVISIONS.items():
                if d.startswith(conf):
                    g = max(es, key=lambda e: (v[e], rng.random()))
                    C["division"][g] += 1
                    gagnants.append(g)
            autres = [e for d, es in DIVISIONS.items() if d.startswith(conf) for e in es if e not in gagnants]
            rep = sorted(autres, key=lambda e: (-v[e], rng.random()))[:3]
            tetes = sorted(gagnants, key=lambda e: (-v[e], rng.random())) + rep

            def jouer(x, y, terrain_x=True):
                if x in elimines and y not in elimines:
                    return y
                if y in elimines and x not in elimines:
                    return x
                return x if rng.random() < we(R.get(x, 1505) + (48 if terrain_x else 0) - R.get(y, 1505)) else y
            g1 = [jouer(tetes[1], tetes[6]), jouer(tetes[2], tetes[5]), jouer(tetes[3], tetes[4])]
            g1 = sorted(g1, key=lambda e: tetes.index(e))
            r2 = [jouer(tetes[0], g1[-1]), jouer(g1[0], g1[1])]
            r2 = sorted(r2, key=lambda e: tetes.index(e))
            ch = jouer(r2[0], r2[1])
            C["conference"][ch] += 1
            finalistes.append(ch)
        x, y = finalistes
        if x in elimines and y not in elimines:
            sb = y
        elif y in elimines and x not in elimines:
            sb = x
        else:
            sb = x if rng.random() < we(R.get(x, 1505) - R.get(y, 1505)) else y
        C["super_bowl"][sb] += 1
    return {k: {e: c / n for e, c in d.items()} for k, d in C.items()}


# ---- estimation ----------------------------------------------------------------------------------------------------
def estimer(titre: str, jour: dt.date | None = None, donnees: dict | None = None) -> dict | None:
    jour = jour or dt.date.today()
    D = donnees or {}
    rows = D.get("resultats")
    noms = None
    if re.search(r"world cup", titre or "", re.I):
        rows = rows or resultats()
        noms = {r["home_team"] for r in rows} | {r["away_team"] for r in rows}
    q = reconnaitre(titre, noms)
    if not q:
        return None
    if q["comp"] == "cdm":
        if jour > dt.date(2026, 7, 19):
            return None
        S = cdm(rows, D.get("tirs") or tirs(), jour)
        if q["forme"] == "premier_vainqueur":
            p = S["premier_vainqueur"]
        elif q["forme"] == "hote_demi":
            p = S["hote_demi"]
        else:
            cle = {"poule": "premier", "sortie_poule": "sortie_poule", "quart": "quart", "demi": "demi",
                   "finale": "finale", "titre": "titre"}[q["forme"]]
            p = S[cle].get(q["equipe"], 0.0)
    else:
        if not (dt.date(2025, 3, 1) <= jour <= dt.date(2026, 2, 8)):
            return None
        S = nfl_saison(D.get("nfl") or matchs_nfl(), jour)
        if q["forme"] == "division" and q["equipe"] not in DIVISIONS.get(q["division"], []):
            return None
        p = S[{"division": "division", "conference": "conference", "super_bowl": "super_bowl"}[q["forme"]]].get(q["equipe"], 0.0)
    return {**q, "p": min(0.99, max(0.01, p)), "tirages": TIRAGES}
