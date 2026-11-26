"""Classements de force (Elo) pour les compétitions (sources validées par l'auteur le 2026-11-24, 23 h 24 ; licences non
commerciales acceptées, 23 h 21). Aucune cote de bookmaker, jamais.

- clubs : Club Elo (api.clubelo.com, CSV ; licence non indiquée ; robots.txt vérifié avant toute requête) : un relevé
  mensuel de tous les clubs (historique depuis 2010), puis le relevé du jour.
- selections : résultats internationaux (martj42/international_results, CC0) ; Elo calculé ici selon la formule publique
  du World Football Elo (K selon la compétition, majoré par l'écart de buts, avantage du terrain 100).
- tennis_atp, tennis_wta : matchs du circuit (Jeff Sackmann, CC BY-NC-SA 4.0, attribution : Jeff Sackmann /
  Tennis Abstract ; copie de secours sur Hugging Face, même licence) ; Elo calculé ici (K = 250 / (n + 5)^0,4).
- nfl : calendrier et résultats (nflverse/nfldata, CC BY 4.0) ; Elo calculé ici (K = 20, terrain 48, multiplicateur
  d'écart de points, retour d'un tiers vers 1505 à chaque saison).
Écrit registre/elo/<famille>.csv.gz : date (fin de mois, plus le dernier jour connu), entite, elo.

    python collecte_elo.py [familles...]
"""
from __future__ import annotations

import csv
import datetime as dt
import gzip
import io
import math
import re
import sys
import time
from collections import defaultdict
from pathlib import Path

import httpx

import politesse

REG = Path("registre") / "elo"
SELECTIONS = "https://raw.githubusercontent.com/martj42/international_results/master/results.csv"
NFL = "https://raw.githubusercontent.com/nflverse/nfldata/master/data/games.csv"
SACKMANN = "https://raw.githubusercontent.com/JeffSackmann/tennis_{t}/master/{t}_matches_{a}.csv"
SACKMANN_HF = "https://huggingface.co/datasets/Aneeshers/tennis-sackmann-archive/resolve/main/{t}/{t}_matches_{a}.csv"
CLUBELO = "http://api.clubelo.com/{d}"


def _get(c: httpx.Client, url: str) -> str | None:
    if not politesse.autorise(c, url):
        print(f"refusé par robots.txt : {url}")
        return None
    r = c.get(url, timeout=60, follow_redirects=True)
    return r.text if r.status_code == 200 else None


def ecrire(famille: str, notes: dict[str, list[tuple[str, float]]]) -> None:
    """notes : entité → [(jour, elo)] dans l'ordre ; on garde la fin de chaque mois et le dernier relevé."""
    REG.mkdir(parents=True, exist_ok=True)
    lignes = []
    for e, L in notes.items():
        par_mois = {}
        for j, v in L:
            par_mois[j[:7]] = (j, v)
        for m, (j, v) in sorted(par_mois.items()):
            lignes.append((j, e, round(v, 1)))
    lignes.sort()
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["date", "entite", "elo"])
    w.writerows(lignes)
    with gzip.open(REG / f"{famille}.csv.gz", "wt", encoding="utf-8", newline="") as f:
        f.write(buf.getvalue())
    print(f"{famille} : {len(notes)} entités, {len(lignes)} lignes")


# ---- sélections nationales (World Football Elo) --------------------------------------------------------------------
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


def selections(c: httpx.Client) -> None:
    txt = _get(c, SELECTIONS)
    if not txt:
        return
    R, notes = defaultdict(lambda: 1500.0), defaultdict(list)
    for r in csv.DictReader(io.StringIO(txt)):
        try:
            hs, as_ = int(r["home_score"]), int(r["away_score"])
        except ValueError:
            continue                                   # match à venir
        h, a = r["home_team"], r["away_team"]
        dr = R[h] - R[a] + (0 if r["neutral"].upper() == "TRUE" else 100)
        we = 1 / (10 ** (-dr / 400) + 1)
        w = 1.0 if hs > as_ else 0.5 if hs == as_ else 0.0
        n = abs(hs - as_)
        k = k_selection(r["tournament"]) * (1 if n <= 1 else 1.5 if n == 2 else 1.75 + (n - 3) / 8)
        d = k * (w - we)
        R[h] += d
        R[a] -= d
        notes[h].append((r["date"], R[h]))
        notes[a].append((r["date"], R[a]))
    ecrire("selections", notes)


# ---- tennis ----------------------------------------------------------------------------------------------------------
def tennis(c: httpx.Client, t: str) -> None:
    R, n, notes = defaultdict(lambda: 1500.0), defaultdict(int), defaultdict(list)
    for a in range(1990, dt.date.today().year + 1):
        txt = _get(c, SACKMANN.format(t=t, a=a)) or _get(c, SACKMANN_HF.format(t=t, a=a))
        if not txt:
            print(f"{t} {a} : indisponible")
            continue
        rows = sorted(csv.DictReader(io.StringIO(txt)), key=lambda r: (r.get("tourney_date") or "", int(r.get("match_num") or 0)))
        for r in rows:
            g, p = r.get("winner_name"), r.get("loser_name")
            d = r.get("tourney_date") or ""
            if not g or not p or len(d) != 8 or "W/O" in (r.get("score") or ""):
                continue
            j = f"{d[:4]}-{d[4:6]}-{d[6:]}"
            e = 1 / (1 + 10 ** ((R[p] - R[g]) / 400))
            kg, kp = 250 / (n[g] + 5) ** 0.4, 250 / (n[p] + 5) ** 0.4
            R[g] += kg * (1 - e)
            R[p] -= kp * (1 - e)
            n[g] += 1
            n[p] += 1
            notes[g].append((j, R[g]))
            notes[p].append((j, R[p]))
        time.sleep(1)
    # 2026-11-26 (décision de l'auteur) : grands tournois postérieurs à Sackmann, lus sur Wikipédia
    # (collecte_tennis_wiki.py) ; même formule, seulement après la dernière date de Sackmann.
    fin = max((L[-1][0] for L in notes.values() if L), default="")
    wiki = REG.parent / "tennis-wiki" / f"{t}.csv"
    if wiki.exists():
        import unicodedata
        def cle(x: str) -> str:
            # casse, accents, ligatures, tirets ; ordre des mots indifférent (« Zheng Qinwen » = « Qinwen Zheng »,
            # « Kwon Soon-woo » = « Soonwoo Kwon »)
            x = x.replace("æ", "ae").replace("Æ", "Ae").replace("ø", "o").replace("Ø", "O").replace("ß", "ss")
            x = unicodedata.normalize("NFKD", x).encode("ascii", "ignore").decode().lower().replace("-", " ")
            return " ".join(sorted(re.sub(r"[^a-z ]", "", x).split()))
        connus = {cle(e): e for e in notes}             # « Alex de Minaur » (Wikipédia) = « Alex De Minaur » (Sackmann)
        jetons = [(set(k.split()), e) for k, e in connus.items()]

        def retrouver(x: str) -> str:
            k = cle(x)
            if k in connus:
                return connus[k]
            J = set(k.split())                           # « Irene Burillo » ⊂ « Irene Burillo Escorihuela », si unique
            c = [e for js, e in jetons if len(J) >= 2 and J <= js]
            return c[0] if len(c) == 1 else x
        W = sorted(csv.DictReader(wiki.open(encoding="utf-8")), key=lambda r: (r["tourney_date"], int(r["round"] or 0)))
        for r in W:
            r["winner_name"] = retrouver(r["winner_name"])
            r["loser_name"] = retrouver(r["loser_name"])
            d = r["tourney_date"]
            j = f"{d[:4]}-{d[4:6]}-{d[6:]}"
            if j <= fin or "w/o" in (r.get("score") or "").lower():
                continue
            g, p = r["winner_name"], r["loser_name"]
            e = 1 / (1 + 10 ** ((R[p] - R[g]) / 400))
            kg, kp = 250 / (n[g] + 5) ** 0.4, 250 / (n[p] + 5) ** 0.4
            R[g] += kg * (1 - e)
            R[p] -= kp * (1 - e)
            n[g] += 1
            n[p] += 1
            notes[g].append((j, R[g]))
            notes[p].append((j, R[p]))
    if notes:
        ecrire(f"tennis_{t}", notes)


# ---- NFL -------------------------------------------------------------------------------------------------------------
def nfl(c: httpx.Client) -> None:
    txt = _get(c, NFL)
    if not txt:
        return
    R, notes, saison = defaultdict(lambda: 1505.0), defaultdict(list), None
    rows = sorted(csv.DictReader(io.StringIO(txt)), key=lambda r: (r["gameday"], r["game_id"]))
    for r in rows:
        if not r["home_score"] or not r["away_score"]:
            continue
        if r["season"] != saison:                     # retour d'un tiers vers la moyenne à chaque saison
            saison = r["season"]
            for e in list(R):
                R[e] = R[e] * 2 / 3 + 1505 / 3
        h, a = r["home_team"], r["away_team"]
        hs, as_ = int(r["home_score"]), int(r["away_score"])
        terrain = 0 if r.get("location") == "Neutral" else 48
        dr = R[h] + terrain - R[a]
        e = 1 / (1 + 10 ** (-dr / 400))
        w = 1.0 if hs > as_ else 0.5 if hs == as_ else 0.0
        ecart = abs(hs - as_)
        mult = math.log(ecart + 1) * 2.2 / ((dr if w == 1 else -dr) * 0.001 + 2.2) if ecart else 1.0
        d = 20 * mult * (w - e)
        R[h] += d
        R[a] -= d
        notes[h].append((r["gameday"], R[h]))
        notes[a].append((r["gameday"], R[a]))
    ecrire("nfl", notes)


# ---- clubs (Club Elo) ------------------------------------------------------------------------------------------------
def clubs(c: httpx.Client) -> None:
    f = REG / "clubs.csv.gz"
    notes = defaultdict(list)
    deja = set()
    if f.exists():
        with gzip.open(f, "rt", encoding="utf-8") as g:
            for r in csv.DictReader(g):
                notes[r["entite"]].append((r["date"], float(r["elo"])))
                deja.add(r["date"][:7])
    auj = dt.date.today()
    jours = [dt.date(a, m, 1) for a in range(2010, auj.year + 1) for m in range(1, 13) if dt.date(a, m, 1) <= auj]
    jours = [j for j in jours if j.strftime("%Y-%m") not in deja or j.strftime("%Y-%m") == auj.strftime("%Y-%m")]
    if auj not in jours:
        jours.append(auj)
    for j in jours:
        txt = _get(c, CLUBELO.format(d=j.isoformat()))
        if txt is None:
            print("Club Elo : arrêt (refus ou erreur)")
            break
        for r in csv.DictReader(io.StringIO(txt)):
            if r.get("Club") and r.get("Elo"):
                notes[r["Club"]].append((j.isoformat(), float(r["Elo"])))
        time.sleep(2)
    if notes:
        for e in notes:
            notes[e].sort()
        ecrire("clubs", notes)


def principal() -> int:
    familles = sys.argv[1:] or ["selections", "nfl", "tennis_atp", "tennis_wta", "clubs"]
    with httpx.Client(headers={"User-Agent": politesse.UA}) as c:
        for fam in familles:
            try:
                if fam.startswith("tennis_"):
                    tennis(c, fam.split("_")[1])
                else:
                    globals()[fam](c)
            except Exception as e:                      # une famille qui échoue n'arrête pas les autres
                print(f"{fam} : échec ({type(e).__name__}: {e})")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
