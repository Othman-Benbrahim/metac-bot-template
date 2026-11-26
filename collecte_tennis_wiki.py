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
WIKI = "https://en.wikipedia.org/wiki/"
# 2026-11-26 : robots.txt de Wikipédia refuse /w/ (api.php) ; la page brute (/wiki/<titre>?action=raw) est permise.
# Pas de recherche (Special:Search est refusé) : titres d'usage essayés dans l'ordre, redirections suivies une fois.
DEPUIS = "20260526"   # lendemain de la dernière date connue chez Sackmann (miroir) ; Roland-Garros 2026 y figure

# (date de début approximative AAAAMMJJ, recherche Wikipédia) — dates approximatives, servent seulement à l'ordre
TOURNOIS = {
    "atp": [("20260629", ["2026 Wimbledon Championships – Men's singles"]),
            ("20260803", ["2026 Canadian Open – Men's singles", "2026 National Bank Open – Men's singles"]),
            ("20260813", ["2026 Cincinnati Open – Men's singles"]),
            ("20260831", ["2026 US Open – Men's singles"]),
            ("20261001", ["2026 Shanghai Masters – Singles", "2026 Rolex Shanghai Masters – Singles"]),
            ("20261026", ["2026 Paris Masters – Singles", "2026 Rolex Paris Masters – Singles"]),
            ("20261109", ["2026 ATP Finals – Singles", "2026 Nitto ATP Finals – Singles"])],
    "wta": [("20260629", ["2026 Wimbledon Championships – Women's singles"]),
            ("20260803", ["2026 Canadian Open – Women's singles", "2026 National Bank Open – Women's singles"]),
            ("20260813", ["2026 Cincinnati Open – Women's singles"]),
            ("20260831", ["2026 US Open – Women's singles"]),
            ("20260924", ["2026 China Open – Women's singles"]),
            ("20261012", ["2026 Wuhan Open – Singles"]),
            ("20261102", ["2026 WTA Finals – Singles"])],
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
def brut(c: httpx.Client, titres: list[str]) -> tuple[str | None, str]:
    """Wikitexte de la première page trouvée (redirection suivie une fois)."""
    for t in titres:
        u = WIKI + t.replace(" ", "_") + "?action=raw"
        if not politesse.autorise(c, u):
            print(f"refusé par robots.txt : {u}")
            continue
        r = c.get(u)
        time.sleep(1)
        print(f"  essai « {t} » : HTTP {r.status_code}, {len(r.text)} caractères")   # diagnostic en une passe
        if r.status_code != 200 or not r.text.strip():
            continue
        m = re.match(r"\s*#REDIRECT\s*\[\[([^\]|#]+)", r.text, re.I)
        if m:
            u2 = WIKI + m.group(1).strip().replace(" ", "_") + "?action=raw"
            if politesse.autorise(c, u2):
                r = c.get(u2)
                time.sleep(1)
                if r.status_code == 200:
                    return m.group(1).strip(), r.text
            continue
        return t, r.text
    return None, ""


def principal() -> int:
    REG.mkdir(parents=True, exist_ok=True)
    with httpx.Client(headers={"User-Agent": politesse.UA}, timeout=60, follow_redirects=True) as c:
        for circuit, L in TOURNOIS.items():
            lignes = []
            for date, titres in L:
                if date < DEPUIS:
                    continue
                t, texte = brut(c, titres)
                if not t:
                    print(f"{circuit} : page introuvable ({titres[0]})")
                    continue
                M = matchs(texte)
                print(f"{circuit} : {t} : {len(M)} matchs")
                if len(M) < 10:                                   # diagnostic : gabarits trouvés sur la page
                    noms_g = [g.split("|")[0].strip() for g in gabarits(texte)]
                    print(f"  peu de matchs ; gabarits de tableau : {noms_g[:12]} ; extrait : {texte[:300]!r}")
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
