"""Football, vainqueur d'un championnat (preenregistrements/football-championnats.md). Une passe ; aucun modèle de
langue. Données : football-data.co.uk (matchs) et ClubElo (Elo à une date) ; robots.txt lu avant toute requête.

    python banc_football.py --diagnostic   # correspondances de noms seulement : aucune probabilité, aucune issue
    python banc_football.py                # le passage unique ; rapport banc_football.json
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import random
import re
import statistics
import sys
import time
import unicodedata
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

import httpx

import politesse

LIGUES = {"E0": ("ENG", 20, "premier league"), "SP1": ("ESP", 20, "la ?liga"), "I1": ("ITA", 20, "serie a"),
          "D1": ("GER", 18, "bundesliga"), "F1": ("FRA", 18, "ligue 1")}
FD = "https://www.football-data.co.uk/mmz4281/{s}/{d}.csv"
CE = "http://api.clubelo.com/{j}"
DEV = [2015, 2016, 2017, 2018]           # saison = année de début
EPREUVE = [2019, 2020, 2021, 2022, 2023, 2024, 2025]
MOIS = [9, 10, 11, 12, 1, 2, 3, 4, 5]
TIRAGES, GRAINE, BOOT = 10_000, 20261127, 10_000
PMIN, PMAX = 0.01, 0.99
SAILLANCE = 2.0

# football-data / titres de questions -> forme proche de ClubElo (complétée après le diagnostic, jamais après le score)
ALIAS = {
    "nottm forest": "forest", "nott m forest": "forest", "nottingham forest": "forest",
    "man city": "man city", "manchester city": "man city", "man united": "man united", "manchester united": "man united",
    "wolverhampton": "wolves", "sheffield united": "sheffield united", "leeds united": "leeds", "west ham": "west ham",
    "ath madrid": "atletico", "atletico madrid": "atletico", "ath bilbao": "bilbao", "athletic bilbao": "bilbao",
    "real betis": "betis", "real sociedad": "sociedad", "celta vigo": "celta", "espanol": "espanyol",
    "vallecano": "rayo vallecano", "real oviedo": "oviedo", "sp gijon": "gijon",
    "bayern munich": "bayern", "ein frankfurt": "frankfurt", "eintracht frankfurt": "frankfurt", "m gladbach": "gladbach",
    "fc koln": "koeln", "koln": "koeln", "greuther furth": "fuerth", "schalke 04": "schalke", "werder bremen": "werder",
    "rb leipzig": "rb leipzig", "fortuna dusseldorf": "duesseldorf", "dusseldorf": "duesseldorf", "nurnberg": "nuernberg",
    "hannover": "hannover", "paderborn": "paderborn",
    "paris sg": "paris sg", "psg": "paris sg", "st etienne": "saint etienne", "saint etienne": "saint etienne",
    "olympique lyonnais": "lyon", "olympique marseille": "marseille", "as monaco": "monaco",
    "ac milan": "milan", "inter milan": "inter", "as roma": "roma", "hellas verona": "verona", "spal": "spal",
}
VIDES = {"fc", "cf", "ac", "as", "sc", "afc", "ssc", "us", "sv", "vfl", "vfb", "tsg", "fsv", "ogc", "rc", "sd", "ud",
         "cd", "rcd", "ca", "club", "de", "the", "1", "04", "05", "1899", "1846", "1907", "1909", "1910", "1913"}


def cle(nom: str) -> str:
    s = unicodedata.normalize("NFKD", nom or "").encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    s = ALIAS.get(s, s)
    return " ".join(t for t in s.split() if t not in VIDES) or s


def saison_code(a: int) -> str:
    return f"{a % 100:02d}{(a + 1) % 100:02d}"


def lire_date(t: str) -> date | None:
    for f in ("%d/%m/%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(t.strip(), f).date()
        except (ValueError, AttributeError):
            pass
    return None


class Source:
    def __init__(self):
        self.c = httpx.Client(headers={"User-Agent": politesse.UA}, timeout=60, follow_redirects=True)
        self.elo_cache: dict[str, list[dict]] = {}

    def get(self, url: str) -> str | None:
        if not politesse.autorise(self.c, url):
            print(f"refusé par robots.txt : {url}", flush=True)
            try:   # transparence : le texte du robots.txt, pour savoir si le refus vise tout le monde ou ce robot
                from urllib.parse import urlparse
                u = urlparse(url)
                print(self.c.get(f"{u.scheme}://{u.netloc}/robots.txt").text[:3000], flush=True)
            except httpx.HTTPError:
                pass
            sys.exit(2)
        for _ in range(3):
            try:
                r = self.c.get(url)
                time.sleep(1)
                if r.status_code == 200:
                    return r.content.decode("utf-8-sig", errors="replace") if b"\xef\xbb\xbf" == r.content[:3] \
                        else r.content.decode("latin-1")
                if r.status_code in (403, 404):
                    print(f"{r.status_code} : {url}", flush=True)
                    return None
            except httpx.HTTPError:
                time.sleep(3)
        return None

    def matchs(self, div: str, a: int) -> list[dict]:
        txt = self.get(FD.format(s=saison_code(a), d=div))
        out = []
        for r in csv.DictReader(io.StringIO(txt or "")):
            d = lire_date(r.get("Date", ""))
            if not d or not r.get("HomeTeam"):
                continue
            def n(x):
                try:
                    return int(float(x))
                except (TypeError, ValueError):
                    return None
            out.append({"d": d, "h": r["HomeTeam"].strip(), "a": r["AwayTeam"].strip(),
                        "hg": n(r.get("FTHG")), "ag": n(r.get("FTAG"))})
        return out

    def elo(self, j: date) -> list[dict]:
        k = j.isoformat()
        if k not in self.elo_cache:
            txt = self.get(CE.format(j=k)) or ""
            self.elo_cache[k] = [r for r in csv.DictReader(io.StringIO(txt)) if r.get("Club")]
        return self.elo_cache[k]


def correspondance(clubs: list[str], elos: list[dict], pays: str) -> tuple[dict, list[str]]:
    cand = [(cle(r["Club"]), float(r["Elo"])) for r in elos if r.get("Country") == pays]
    res, manque = {}, []
    for c in clubs:
        k = cle(c)
        v = [e for kk, e in cand if kk == k] or [e for kk, e in cand if (k in kk.split() or kk in k.split()) and len(min(k, kk, key=len)) >= 4]
        if len(v) >= 1:
            res[c] = v[0]
        else:
            manque.append(c)
    return res, manque


def classement(ms: list[dict], D: date) -> dict:
    pts = defaultdict(int)
    for m in ms:
        pts[m["h"]] += 0
        pts[m["a"]] += 0
        if m["d"] < D and m["hg"] is not None and m["ag"] is not None:
            if m["hg"] > m["ag"]:
                pts[m["h"]] += 3
            elif m["hg"] < m["ag"]:
                pts[m["a"]] += 3
            else:
                pts[m["h"]] += 1
                pts[m["a"]] += 1
    return dict(pts)


def champion(ms: list[dict]) -> str | None:
    pts, gd, gf = defaultdict(int), defaultdict(int), defaultdict(int)
    for m in ms:
        if m["hg"] is None or m["ag"] is None:
            return None
        for eq, f, c in ((m["h"], m["hg"], m["ag"]), (m["a"], m["ag"], m["hg"])):
            gd[eq] += f - c
            gf[eq] += f
            pts[eq] += 3 if f > c else (1 if f == c else 0)
    return max(pts, key=lambda e: (pts[e], gd[e], gf[e])) if pts else None


def probas_match(eh: float, ea: float, H: float, pn: float) -> tuple[float, float, float]:
    E = 1 / (1 + 10 ** (-(eh - ea + H) / 400))
    v, l = max(0.02, E - pn / 2), max(0.02, 1 - E - pn / 2)
    s = v + pn + l
    return v / s, pn / s, l / s


def simuler(ms: list[dict], D: date, force: dict, H: float, pn: float, rng) -> dict:
    """10 000 tirages vectorisés (numpy) ; égalité de points tranchée au hasard (bruit < 1 point)."""
    import numpy as np
    base = classement(ms, D)
    eqs = sorted(base)
    ix = {e: i for i, e in enumerate(eqs)}
    reste = [m for m in ms if m["d"] >= D]
    pts = np.tile(np.array([base[e] for e in eqs], dtype=float), (TIRAGES, 1))
    if reste:
        h = np.array([ix[m["h"]] for m in reste])
        a = np.array([ix[m["a"]] for m in reste])
        pr = np.array([probas_match(force[m["h"]], force[m["a"]], H, pn) for m in reste])
        u = rng.random((TIRAGES, len(reste)))
        v = u < pr[:, 0]
        n = (~v) & (u < pr[:, 0] + pr[:, 1])
        l = ~(v | n)
        for col, (hi, ai) in enumerate(zip(h, a)):
            pts[:, hi] += 3 * v[:, col] + n[:, col]
            pts[:, ai] += 3 * l[:, col] + n[:, col]
    gagnant = np.argmax(pts + rng.random(pts.shape) * 0.5, axis=1)
    comptes = np.bincount(gagnant, minlength=len(eqs))
    return {e: float(comptes[ix[e]]) / TIRAGES for e in eqs}


def regler(src: Source, div: str) -> tuple[float, float]:
    """H et p_N sur les saisons de développement (préenregistrement, § Méthode M, point 5)."""
    pays = LIGUES[div][0]
    n = nuls = dom = 0
    paires = []
    for a in DEV:
        ms = src.matchs(div, a)
        par_mois = defaultdict(list)
        for m in ms:
            if m["hg"] is not None:
                par_mois[date(m["d"].year, m["d"].month, 1)].append(m)
        for j, lot in par_mois.items():
            f, _ = correspondance(sorted({m["h"] for m in lot} | {m["a"] for m in lot}), src.elo(j), pays)
            for m in lot:
                n += 1
                nuls += m["hg"] == m["ag"]
                dom += m["hg"] > m["ag"]
                if m["h"] in f and m["a"] in f:
                    paires.append((f[m["h"]] - f[m["a"]], m["hg"] > m["ag"]))
    pn = nuls / n
    cible = dom / n
    meilleur = min(range(0, 155, 5), key=lambda H: abs(sum(probas_match(d, 0, H, pn)[0] for d, _ in paires) / len(paires) - cible))
    return float(meilleur), pn


def ll(p: float, y: int) -> float:
    import math
    p = min(max(p, PMIN), PMAX)
    return -math.log(p if y else 1 - p)


def p_brique(N: int) -> float:
    return 1 - (1 - 1 / N) ** SAILLANCE


def questions_reelles() -> list[dict]:
    import familles_situation as fs
    import competitions_regle as cp
    qs = {}
    for l in open(Path("registre") / "jugement-questions.jsonl", encoding="utf-8"):
        d = json.loads(l)
        t = d.get("titre", "")
        if t.startswith(fs.COMBINAISON) or re.search(r"indian premier league", t, re.I):
            continue
        qs[(d["source"], t.strip())] = d
    out = []
    for d in qs.values():
        t = d["titre"]
        div = next((k for k, (_, _, rx) in LIGUES.items() if re.search(rx, t, re.I)), None)
        if not div or not cp.n_concurrents(t):
            continue
        m = re.match(r"\s*will (the )?(.+?) wins? (the )?", t, re.I)
        if not m:
            continue
        out.append({"source": d["source"], "id": d["id"], "titre": t, "div": div, "club": m.group(2),
                    "jeu": date.fromisoformat(d["jeu"][:10]), "issue": d.get("issue")})
    return out


def saison_de(D: date) -> int:
    return D.year if D.month >= 7 else D.year - 1


def principal() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--diagnostic", action="store_true")
    diag = ap.parse_args().diagnostic
    src = Source()
    reelles = questions_reelles()
    manques = defaultdict(set)
    saisons = {}
    for div in LIGUES:
        for a in DEV + EPREUVE:
            saisons[(div, a)] = src.matchs(div, a)
            print(f"{div} {a} : {len(saisons[(div, a)])} matchs", flush=True)
    if diag:
        for (div, a), ms in saisons.items():
            if a not in EPREUVE or not ms:
                continue
            clubs = sorted({m["h"] for m in ms} | {m["a"] for m in ms})
            _, mq = correspondance(clubs, src.elo(date(a, 10, 1)), LIGUES[div][0])
            for c in mq:
                manques[div].add(c)
        for q in reelles:
            ms = saisons.get((q["div"], saison_de(q["jeu"]))) or []
            clubs = sorted({m["h"] for m in ms} | {m["a"] for m in ms})
            if cle(q["club"]) not in {cle(c) for c in clubs}:
                manques["question:" + q["div"]].add(f"{q['club']}  ⇢ clubs : {', '.join(clubs)}")
        print(json.dumps({k: sorted(v) for k, v in manques.items()}, ensure_ascii=False, indent=1))
        print(f"questions réelles reconnues : {len(reelles)}")
        return 0

    import numpy as np
    rng = np.random.default_rng(GRAINE)
    reglages = {div: regler(src, div) for div in LIGUES}
    print("réglages H, p_N :", reglages, flush=True)
    lignes, exclus = [], []
    for div, (pays, N, _) in LIGUES.items():
        H, pn = reglages[div]
        for a in EPREUVE:
            ms = saisons[(div, a)]
            ch = champion(ms)
            if not ms or ch is None:
                exclus.append(f"{div} {a} : saison incomplète")
                continue
            clubs = sorted({m["h"] for m in ms} | {m["a"] for m in ms})
            for mo in MOIS:
                D = date(a + (mo < 7), mo, 1)
                f, mq = correspondance(clubs, src.elo(D), pays)
                if len(mq) > 2:
                    exclus.append(f"{div} {a} {D} : {len(mq)} clubs sans Elo")
                    continue
                med = statistics.median(f.values())
                force = {c: f.get(c, med) for c in clubs}
                pM = simuler(ms, D, force, H, pn, rng)
                pT = simuler(ms, D, {c: 1500.0 for c in clubs}, H, pn, rng)
                for c in clubs:
                    y = int(c == ch)
                    lignes.append({"div": div, "saison": a, "date": D.isoformat(), "club": c, "y": y, "sans_elo": c in mq,
                                   "M": ll(pM[c], y), "B": ll(p_brique(N), y), "T": ll(pT[c], y)})
            print(f"{div} {a} : fait", flush=True)

    def boot(cle_a: str, cle_b: str, L: list[dict]) -> dict:
        grappes = defaultdict(list)
        for x in L:
            grappes[(x["div"], x["saison"], x["date"])].append(x[cle_a] - x[cle_b])
        G = list(grappes.values())
        moy = sum(sum(g) for g in G) / sum(len(g) for g in G)
        r = random.Random(GRAINE)
        bs = []
        for _ in range(BOOT):
            s = [G[r.randrange(len(G))] for _ in G]
            bs.append(sum(sum(g) for g in s) / sum(len(g) for g in s))
        bs.sort()
        return {"ecart": round(moy, 4), "ic90": [round(bs[int(.05 * BOOT)], 4), round(bs[int(.95 * BOOT)], 4)],
                "grappes": len(G), "questions": sum(len(g) for g in G)}

    moy = lambda L, k: round(sum(x[k] for x in L) / len(L), 4) if L else None
    res = {"preenregistrement": "preenregistrements/football-championnats.md", "reglages": reglages, "exclus": exclus,
           "epreuve1": {"n": len(lignes), "M": moy(lignes, "M"), "B": moy(lignes, "B"), "T": moy(lignes, "T"),
                        "M_moins_B": boot("M", "B", lignes), "M_moins_T": boot("M", "T", lignes),
                        "par_mois": {m: {k: moy([x for x in lignes if int(x["date"][5:7]) == m], k) for k in "MBT"} for m in MOIS},
                        "par_ligue": {d: {k: moy([x for x in lignes if x["div"] == d], k) for k in "MBT"} for d in LIGUES}}}
    ok = res["epreuve1"]["M_moins_B"]["ecart"] < 0 and res["epreuve1"]["M_moins_B"]["ic90"][1] < 0
    res["critere_atteint"] = ok

    r2 = []
    for q in reelles:
        a = saison_de(q["jeu"])
        ms = saisons.get((q["div"], a)) or []
        clubs = sorted({m["h"] for m in ms} | {m["a"] for m in ms})
        c = next((x for x in clubs if cle(x) == cle(q["club"])), None)
        if not ms or c is None or str(q["issue"]) not in ("0", "1"):
            r2.append({"titre": q["titre"], "exclue": "club ou saison introuvable"})
            continue
        pays, N, _ = LIGUES[q["div"]]
        f, mq = correspondance(clubs, src.elo(q["jeu"]), pays)
        med = statistics.median(f.values())
        force = {x: f.get(x, med) for x in clubs}
        H, pn = reglages[q["div"]]
        y = int(q["issue"])
        pM = simuler(ms, q["jeu"], force, H, pn, rng)[c]
        pT = simuler(ms, q["jeu"], {x: 1500.0 for x in clubs}, H, pn, rng)[c]
        r2.append({"titre": q["titre"], "jeu": q["jeu"].isoformat(), "y": y, "pM": round(pM, 4), "pT": round(pT, 4),
                   "pB": round(p_brique(N), 4), "M": ll(pM, y), "B": ll(p_brique(N), y), "T": ll(pT, y)})
    ok2 = [x for x in r2 if "M" in x]
    res["epreuve2"] = {"n": len(ok2), "M": moy(ok2, "M"), "B": moy(ok2, "B"), "T": moy(ok2, "T"), "questions": r2}
    Path("banc_football.json").write_text(json.dumps(res, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print(json.dumps({k: v for k, v in res.items() if k != "epreuve2"}, ensure_ascii=False, indent=1, default=str))
    print("épreuve 2 :", {k: v for k, v in res["epreuve2"].items() if k != "questions"})
    return 0


if __name__ == "__main__":
    raise SystemExit(principal())
