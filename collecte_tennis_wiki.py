"""Résultats des grands tournois de tennis manquants chez Sackmann, lus dans les tableaux de Wikipédia (décision de
l'auteur, 2026-11-26, 12 h 21 : « Oui, je valide, pas le choix » ; Wikipédia, CC BY-SA 4.0 ; robots.txt respecté).

Les fichiers de Sackmann s'arrêtent en mai 2026. Pour faire avancer l'Elo jusqu'au jour, on lit les tableaux des
Grands Chelems, des Masters 1000 / WTA 1000 et des Masters de fin d'année commencés après la dernière date de Sackmann.
Seuls les grands tournois sont lus (déclaré : l'Elo du second semestre 2026 ne voit pas les petits tournois).

Écrit registre/tennis-wiki/<atp|wta>.csv : tourney_date, tourney_name, round, winner_name, loser_name, score, page.
    python collecte_tennis_wiki.py
"""
from __future__ import annotations

import csv
import re
import sys
import time
from pathlib import Path

import httpx

import politesse

ICI = Path(__file__).resolve().parent
REG = ICI / "registre" / "tennis-wiki"
API = "https://en.wikipedia.org/w/api.php"
DEPUIS = "20260526"   # lendemain de la dernière date connue chez Sackmann (miroir) ; Roland-Garros 2026 y figure

# (date de début approximative AAAAMMJJ, recherche Wikipédia) — dates approximatives, servent seulement à l'ordre
TOURNOIS = {
    "atp": [("20260629", "2026 Wimbledon Championships Men's singles"), ("20260803", "2026 Canadian Open Men's singles"),
            ("20260813", "2026 Cincinnati Open Men's singles"), ("20260831", "2026 US Open Men's singles"),
            ("20261001", "2026 Shanghai Masters singles"), ("20261026", "2026 Paris Masters singles"),
            ("20261109", "2026 ATP Finals singles")],
    "wta": [("20260629", "2026 Wimbledon Championships Women's singles"), ("20260803", "2026 Canadian Open Women's singles"),
            ("20260813", "2026 Cincinnati Open Women's singles"), ("20260831", "2026 US Open Women's singles"),
            ("20260924", "2026 China Open Women's singles"), ("20261012", "2026 Wuhan Open singles"),
            ("20261102", "2026 WTA Finals singles")],
}


# ---- lecture du wikitexte ----------------------------------------------------------------------------------------------
def gabarits(texte: str) -> list[str]:
    """Corps des gabarits de tableau ({{...Bracket...}}), avec appariement des accolades."""
    out, i = [], 0
    while True:
        k = texte.find("{{", i)
        if k < 0:
            return out
        tete = texte[k + 2:k + 80]
        if "Bracket" not in tete.split("|")[0]:
            i = k + 2
            continue
        prof, j = 0, k
        while j < len(texte) - 1:
            if texte.startswith("{{", j):
                prof += 1
                j += 2
            elif texte.startswith("}}", j):
                prof -= 1
                j += 2
                if prof == 0:
                    break
            else:
                j += 1
        out.append(texte[k + 2:j - 2])
        i = j


def parametres(corps: str) -> dict[str, str]:
    """Paramètres nommés au niveau 0 (les | dans [[...]] et {{...}} ne coupent pas)."""
    morceaux, prof_l, prof_t, cur, i = [], 0, 0, [], 0
    while i < len(corps):
        two = corps[i:i + 2]
        if two == "[[":
            prof_l += 1; cur.append(two); i += 2; continue
        if two == "]]":
            prof_l -= 1; cur.append(two); i += 2; continue
        if two == "{{":
            prof_t += 1; cur.append(two); i += 2; continue
        if two == "}}":
            prof_t -= 1; cur.append(two); i += 2; continue
        if corps[i] == "|" and prof_l == 0 and prof_t == 0:
            morceaux.append("".join(cur)); cur = []; i += 1; continue
        cur.append(corps[i]); i += 1
    morceaux.append("".join(cur))
    P = {}
    for m in morceaux[1:]:
        if "=" in m:
            k, v = m.split("=", 1)
            P[k.strip()] = v.strip()
    return P


def nom(valeur: str) -> str | None:
    liens = re.findall(r"\[\[([^\]|]+)(?:\|[^\]]*)?\]\]", valeur)
    liens = [l for l in liens if not l.lower().startswith(("file:", "image:"))]
    if not liens:
        return None
    return re.sub(r"\s*\([^)]*\)\s*$", "", liens[-1]).strip()


def matchs(texte: str) -> list[tuple[int, str, str, str]]:
    """(ordre du tour, gagnant, perdant, score) pour tous les tableaux de la page."""
    out = []
    G = gabarits(texte)
    for gi, g in enumerate(G):
        P = parametres(g)
        equipes = {}
        for k, v in P.items():
            m = re.fullmatch(r"RD(\d+)-team0*(\d+)", k)
            if m:
                equipes[(int(m.group(1)), int(m.group(2)))] = v
        if not equipes:
            continue
        nb_tours = max(r for r, _ in equipes)
        finale_ici = sum(1 for r, _ in equipes if r == nb_tours) == 2 and len(G) > 1 and gi == 0 and nb_tours <= 3
        for (r, s), va in sorted(equipes.items()):
            if s % 2 == 0 or (r, s + 1) not in equipes:
                continue
            vb = equipes[(r, s + 1)]
            na, nb = nom(va), nom(vb)
            if not na or not nb or "bye" in (va + vb).lower():
                continue
            sc = " ".join(P.get(f"RD{r}-score{str(x).zfill(2)}-{i}", P.get(f"RD{r}-score{x}-{i}", ""))
                          for x in (s, s + 1) for i in range(1, 6)).strip()
            ba, bb = "'''" in va, "'''" in vb
            if ba == bb:
                continue                                  # vainqueur illisible : écarté
            g_, p_ = (na, nb) if ba else (nb, na)
            ordre = (100 + r) if finale_ici else r
            out.append((ordre, g_, p_, sc))
    return out


# ---- collecte ----------------------------------------------------------------------------------------------------------
def titre(c: httpx.Client, recherche: str) -> str | None:
    r = c.get(API, params={"action": "query", "list": "search", "srsearch": recherche, "srlimit": 3, "format": "json"})
    for h in r.json().get("query", {}).get("search", []):
        if h["title"].startswith("2026") and "singles" in h["title"].lower():
            return h["title"]
    return None


def wikitexte(c: httpx.Client, t: str) -> str:
    r = c.get(API, params={"action": "parse", "page": t, "prop": "wikitext", "format": "json", "formatversion": 2})
    return r.json().get("parse", {}).get("wikitext", "")


def principal() -> int:
    REG.mkdir(parents=True, exist_ok=True)
    with httpx.Client(headers={"User-Agent": politesse.UA}, timeout=60, follow_redirects=True) as c:
        if not politesse.autorise(c, API + "?action=parse"):
            print("refusé par robots.txt : api.php")
            return 0
        for circuit, L in TOURNOIS.items():
            lignes = []
            for date, q in L:
                if date < DEPUIS:
                    continue
                t = titre(c, q)
                time.sleep(1)
                if not t:
                    print(f"{circuit} : page introuvable pour « {q} »")
                    continue
                M = matchs(wikitexte(c, t))
                time.sleep(1)
                print(f"{circuit} : {t} : {len(M)} matchs")
                for ordre, g, p, sc in sorted(M):
                    lignes.append({"tourney_date": date, "tourney_name": t, "round": ordre, "winner_name": g,
                                   "loser_name": p, "score": sc, "page": t})
            with open(REG / f"{circuit}.csv", "w", encoding="utf-8", newline="") as f:
                w = csv.DictWriter(f, fieldnames=["tourney_date", "tourney_name", "round", "winner_name", "loser_name",
                                                  "score", "page"])
                w.writeheader()
                w.writerows(lignes)
    return 0


if __name__ == "__main__":
    sys.exit(principal())
