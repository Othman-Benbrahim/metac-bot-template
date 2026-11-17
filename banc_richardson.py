"""Loi de Richardson : queue lourde des morts des conflits, contre le taux du bot (bot 0.10.238, en ombre).

Décision d'auteur du 2026-11-17 (19 h 47). Richardson (1948) : la taille des conflits suit une loi de puissance ;
Valiquette et al. (arXiv 2305.17095) : une loi à queue légère (binomiale négative) sous-estime alors les dépassements
rares. Préenregistrement : preenregistrements/geo-math.md, test 3. Aucun modèle de langue ; UCDP (jeton en secret).

Questions fabriquées : morts estimés (« best ») par UCDP dans un pays, 30 jours après d0 (premier de chaque mois depuis
2024-09-01) : « au moins N morts ? », N = max(1, ⌈quantile 90 % des fenêtres disjointes de 30 jours avant d0⌉)
(au moins 12 fenêtres) ; 25 pays du banc précédent, depuis 2022-01-01 ; relevé au plafond retiré.
Trois taux pour la même question :
  B_bot : part des fenêtres passées ≥ N (alphabet_compte.compter : k / n, bords 1/(2n) et 1 − 1/(2n)) ;
  B_bn  : binomiale négative ajustée par les moments (Poisson si variance ≤ moyenne), P(X ≥ N) ;
  B_ln  : lognormale ajustée sur ln(x + 1), P(ln(X + 1) ≥ ln(N + 1)) (queue lourde).
Critère : B_ln contre B_bot, confirmation d0 ≥ 2025-11-01, bootstrap par mois, risque es.risque_corrige(1) ; meilleur si
la borne haute de l'écart < 0. B_bn et le seuil « 2 × médiane » : rapportés.

    python banc_richardson.py
"""
from __future__ import annotations

import asyncio
import json
import math
import os
import statistics
import sys
from datetime import date, timedelta
from pathlib import Path

import banc_cr_metaculus as bm
import banc_cr_sources as bs
import combinaisons as cb
import combinaisons_gdelt as cg

SORTIE = Path("registre") / "banc-richardson.json"
DEBUT = "2022-01-01"


def p_bn(fen: list[float], n: float) -> float:
    m = sum(fen) / len(fen)
    v = statistics.pvariance(fen)
    if m <= 0:
        return 0.5 / (len(fen) + 1)
    if v <= m:                                           # Poisson
        lam = m
        cdf = sum(math.exp(-lam + k * math.log(lam) - math.lgamma(k + 1)) for k in range(int(math.ceil(n))))
    else:
        r, p = m * m / (v - m), m / v
        cdf = sum(math.exp(math.lgamma(k + r) - math.lgamma(r) - math.lgamma(k + 1) + r * math.log(p) + k * math.log(1 - p))
                  for k in range(int(math.ceil(n))))
    return min(max(1 - cdf, 1e-4), 1 - 1e-4)


def p_ln(fen: list[float], n: float) -> float:
    lg = [math.log(x + 1) for x in fen]
    mu, sd = sum(lg) / len(lg), statistics.pstdev(lg)
    if sd <= 1e-9:
        return 1 - 1e-4 if mu >= math.log(n + 1) else 1e-4
    zz = (math.log(n + 1) - mu) / sd
    return min(max(0.5 * math.erfc(zz / math.sqrt(2)), 1e-4), 1 - 1e-4)


def questions(morts: dict[str, dict[str, float]], dernier: date, seuil: str = "q90") -> list[dict]:
    ancres = cg.mois(cg.DEBUT, dernier - timedelta(days=30))
    debut = date.fromisoformat(DEBUT)
    out = []
    for pays, c in sorted(morts.items()):
        def somme(a, b):
            d, s = a, 0.0
            while d < b:
                s += c.get(d.isoformat(), 0.0)
                d += timedelta(days=1)
            return s
        for d0 in ancres:
            fen, b = [], d0
            while b - timedelta(days=30) >= debut:
                fen.append(somme(b - timedelta(days=30), b))
                b -= timedelta(days=30)
            if len(fen) < 12:
                continue
            if seuil == "q90":
                n = max(1, math.ceil(sorted(fen)[int(0.9 * (len(fen) - 1))]))
            else:
                n = max(1, math.ceil(2 * statistics.median(fen)))
            y = int(somme(d0, d0 + timedelta(days=30)) >= n)
            out.append({"jeu": d0.isoformat(), "pays": pays, "seuil": n, "issue": y,
                        "p_bot": bm.frequence_bot(fen, n), "p_bn": p_bn(fen, n), "p_ln": p_ln(fen, n)})
    return out


def resumer(xs: list[dict], juge: bool) -> dict:
    import essais as es
    conf = [x for x in xs if x["jeu"] >= cg.COUPURE]
    pm = lambda s, k: round(sum(cb.pl(x[k], x["issue"]) for x in s) / len(s), 4) if s else None
    r = {"questions": len(xs), "n_confirmation": len(conf), "oui": round(sum(x["issue"] for x in conf) / len(conf), 3) if conf else None,
         "perte_bot": pm(conf, "p_bot"), "perte_bn": pm(conf, "p_bn"), "perte_ln": pm(conf, "p_ln"),
         "exploration": {"perte_bot": pm([x for x in xs if x["jeu"] < cg.COUPURE], "p_bot"),
                         "perte_bn": pm([x for x in xs if x["jeu"] < cg.COUPURE], "p_bn"),
                         "perte_ln": pm([x for x in xs if x["jeu"] < cg.COUPURE], "p_ln")}}
    if juge and len(conf) >= 30:
        ec = [(x["jeu"][:7], cb.pl(x["p_ln"], x["issue"]) - cb.pl(x["p_bot"], x["issue"])) for x in conf]
        bas, haut = cb.bootstrap(ec, es.risque_corrige(1))
        r.update(ecart_moyen=round(sum(e for _, e in ec) / len(ec), 4), intervalle_corrige=[round(bas, 4), round(haut, 4)],
                 verdict="lognormale meilleure que le bot" if haut < 0 else
                 ("lognormale moins bonne que le bot" if bas > 0 else "non tranché"))
    return r


async def collecter(avant: date) -> tuple[dict, list[str]]:
    import alphabet_puits as apz
    morts, journal = {}, []
    for p in bs.PAYS_UCDP:
        try:
            r = await apz.appeler("ucdp", {"pays": p, "debut": DEBUT}, avant)
        except Exception as e:
            journal.append(f"{p} : {type(e).__name__}: {apz.masquer(str(e))[:120]}")
            continue
        pts = r.get("points") or []
        if len(pts) >= bs.PLAFONDS["ucdp"]:
            journal.append(f"{p} : {len(pts)} événements, plafond atteint : retiré")
            continue
        c: dict[str, float] = {}
        for x in pts:
            j = str(x.get("date") or "")[:10]
            if j >= DEBUT and x.get("valeur") is not None:
                c[j] = c.get(j, 0.0) + float(x["valeur"])
        morts[p] = c
        journal.append(f"{p} : {len(pts)} événements, {round(sum(c.values()))} morts")
        await asyncio.sleep(0.5)
    return morts, journal


def principal() -> int:
    avant = date.today()
    morts, journal = asyncio.run(collecter(avant))
    print("\n".join(journal))
    dernier = avant - timedelta(days=1)
    res = {"note": "perte log, plus bas = mieux ; aucun modèle de langue ; données UCDP GED", "journal": journal,
           "seuil_q90": resumer(questions(morts, dernier, "q90"), True),
           "seuil_double_mediane": resumer(questions(morts, dernier, "2med"), False)}
    SORTIE.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    texte = json.dumps({k: v for k, v in res.items() if k != "journal"}, ensure_ascii=False, indent=1)
    print(texte)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as fo:
            fo.write("## Loi de Richardson (UCDP)\n\n```\n" + texte + "\n```\n")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
