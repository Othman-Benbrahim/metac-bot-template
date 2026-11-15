"""Banc des indicateurs indirects — signaux faibles (0.10.119, décision d'auteur du 2026-11-15 ; Ansoff, California
Management Review 1975 : une surprise s'annonce par des signaux marginaux). AUCUN modèle de langue : sur les questions de
conflits (ACLED) du banc du bras A, on mesure, AVANT la date d'information, des indicateurs qui précèdent les
événements sans en parler, et on teste s'ils ajoutent de l'information au jugement A, une fois A recalibré.

Indicateurs (sources gratuites, sans clé, vérifiées par la sonde du 2026-11-15) :
- wiki : attention du public, log(vues moyennes des 14 derniers jours / vues moyennes des 90 jours précédents) de
  l'article Wikipedia (anglais) du pays (Wikimedia REST) ;
- ioda : coupures d'internet, log(1 + alertes IODA dans les 30 jours avant la date) (Georgia Tech) ;
- fcdo : conseils aux voyageurs du Royaume-Uni, nombre de changements dans les 30 jours avant la date dont la note
  parle de sécurité (manifestation, troubles, violence, couvre-feu, « advise against »…) (API de contenu de gov.uk) ;
- pluie : écart de précipitations des 90 derniers jours à la moyenne des mêmes 90 jours sur les 10 années
  précédentes, en écarts-types, à la capitale (archive Open-Meteo ; coordonnées par restcountries.com).
Indicateur absent (territoire, océan, source muette) : 0 (neutre).

Modèles, validation croisée « un jeu laissé de côté » :
- référence : logit(p) = a + b·logit(A)                           (A recalibré, Platt)
- indicateurs : logit(p) = a + b·logit(A) + Σ βk·zk               (a priori normal 0, écart-type 1 sur les βk)
Critère : preenregistrements/indicateurs.md. Registre : registre/banc-indicateurs.jsonl ; résumé : registre/banc-indicateurs.json.

    python banc_indicateurs.py
"""
from __future__ import annotations

import asyncio
import json
import math
import re
import statistics
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import httpx

import alphabet_pipeline as ap
import banc_a as ba

REGISTRE = Path("registre")
FICHIER = REGISTRE / "banc-indicateurs.jsonl"
RESUME = REGISTRE / "banc-indicateurs.json"
MODELE = "azure_ai/gpt-5-mini"
INDICATEURS = ("wiki", "ioda", "fcdo", "pluie")
MOTS_SECURITE = re.compile(r"protest|demonstrat|unrest|riot|violence|curfew|security|advise against|terror|clash|"
                           r"military|conflict|state of emergency|kidnap", re.I)
UA = {"User-Agent": "alphabet-situationnel-bot/1.0 (recherche ; GitHub Othman-Benbrahim)"}


def pays_de(titre: str) -> str | None:
    m = re.search(r"in (.+?) for the", titre)
    return m.group(1).strip() if m else None


async def obtenir(c: httpx.AsyncClient, url: str, pause: float = 1.0):
    await asyncio.sleep(pause)
    try:
        r = await c.get(url)
        return r.json() if r.status_code == 200 else None
    except Exception:
        return None


async def fiche_pays(c, nom: str, cache: dict) -> dict:
    if nom in cache:
        return cache[nom]
    j = await obtenir(c, f"https://restcountries.com/v3.1/name/{nom}?fields=name,cca2,capitalInfo,latlng")
    f = {"nom": nom}
    if isinstance(j, list) and j:
        e = j[0]
        f.update(cca2=e.get("cca2"), commun=(e.get("name") or {}).get("common") or nom,
                 latlng=(e.get("capitalInfo") or {}).get("latlng") or e.get("latlng"))
    cache[nom] = f
    return f


async def indicateurs(c, f: dict, d0: date) -> dict:
    out = {k: 0.0 for k in INDICATEURS}
    present = {}
    titre = (f.get("commun") or f["nom"]).replace(" ", "_")
    a, b = (d0 - timedelta(days=104)).strftime("%Y%m%d"), (d0 - timedelta(days=1)).strftime("%Y%m%d")
    j = await obtenir(c, f"https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia/all-access/user/{titre}/daily/{a}/{b}")
    vues = [it["views"] for it in (j or {}).get("items") or []]
    if len(vues) >= 60:
        recent, avant = statistics.fmean(vues[-14:]), statistics.fmean(vues[:-14])
        if avant > 0 and recent > 0:
            out["wiki"] = math.log(recent / avant)
            present["wiki"] = True
    if f.get("cca2"):
        t1 = int(datetime(d0.year, d0.month, d0.day, tzinfo=timezone.utc).timestamp())
        j = await obtenir(c, f"https://api.ioda.inetintel.cc.gatech.edu/v2/outages/alerts?entityType=country"
                             f"&entityCode={f['cca2']}&from={t1 - 30 * 86400}&until={t1}")
        if j is not None:
            out["ioda"] = math.log1p(len(j.get("data") or []))
            present["ioda"] = True
    slug = re.sub(r"[^a-z]+", "-", (f.get("commun") or f["nom"]).lower()).strip("-")
    j = await obtenir(c, f"https://www.gov.uk/api/content/foreign-travel-advice/{slug}")
    if j:
        ch = (j.get("details") or {}).get("change_history") or []
        n = 0
        for e in ch:
            ts = str(e.get("public_timestamp") or "")[:10]
            if ts and d0 - timedelta(days=30) <= date.fromisoformat(ts) < d0 and MOTS_SECURITE.search(str(e.get("note") or "")):
                n += 1
        out["fcdo"] = float(n)
        present["fcdo"] = True
    if f.get("latlng"):
        lat, lon = f["latlng"][:2]
        j = await obtenir(c, f"https://archive-api.open-meteo.com/v1/archive?latitude={lat}&longitude={lon}"
                             f"&start_date={(d0 - timedelta(days=3740)).isoformat()}&end_date={(d0 - timedelta(days=1)).isoformat()}"
                             "&daily=precipitation_sum")
        d = (j or {}).get("daily") or {}
        jours, pl = d.get("time") or [], d.get("precipitation_sum") or []
        if jours:
            serie = {date.fromisoformat(t): (v or 0.0) for t, v in zip(jours, pl)}
            sommes = []
            for k in range(0, 11):
                fin = d0 - timedelta(days=1) - timedelta(days=round(365.25 * k))
                sommes.append(sum(serie.get(fin - timedelta(days=i), 0.0) for i in range(90)))
            hist = sommes[1:]
            if len(hist) >= 5 and statistics.pstdev(hist) > 0:
                out["pluie"] = (sommes[0] - statistics.fmean(hist)) / statistics.pstdev(hist)
                present["pluie"] = True
    return {**out, "presents": present}


def lg(p: float) -> float:
    p = min(max(p, 1e-3), 1 - 1e-3)
    return math.log(p / (1 - p))


def sig(x: float) -> float:
    return 1 / (1 + math.exp(-x))


def ajuster(xs: list[tuple[list[float], int]], prior_sd: list[float], prior_moy: list[float]) -> list[float]:
    """Régression logistique, maximum a posteriori (a priori normal par coefficient), Newton (petite dimension)."""
    k = len(prior_sd)
    w = list(prior_moy)
    for _ in range(80):
        g = [-(w[i] - prior_moy[i]) / prior_sd[i] ** 2 for i in range(k)]
        h = [[(-1 / prior_sd[i] ** 2 if i == j else 0.0) for j in range(k)] for i in range(k)]
        for z, y in xs:
            p = sig(sum(wi * zi for wi, zi in zip(w, z)))
            for i in range(k):
                g[i] += (y - p) * z[i]
                for j in range(k):
                    h[i][j] -= p * (1 - p) * z[i] * z[j]
        # résoudre h·d = g (élimination de Gauss)
        m = [row[:] + [g[i]] for i, row in enumerate(h)]
        for i in range(k):
            piv = max(range(i, k), key=lambda r: abs(m[r][i]))
            m[i], m[piv] = m[piv], m[i]
            if abs(m[i][i]) < 1e-12:
                return w
            for r in range(k):
                if r != i:
                    fct = m[r][i] / m[i][i]
                    m[r] = [a - fct * b for a, b in zip(m[r], m[i])]
        d = [m[i][k] / m[i][i] for i in range(k)]
        w = [wi - di for wi, di in zip(w, d)]
        if sum(abs(x) for x in d) < 1e-9:
            break
    return w


def validation_croisee(ls: list[dict]) -> list[dict]:
    out = []
    for j in sorted({x["jeu"] for x in ls}):
        app = [x for x in ls if x["jeu"] != j]
        w0 = ajuster([([1.0, lg(x["p_A"])], x["issue"]) for x in app], [2.0, 2.0], [0.0, 1.0])
        w1 = ajuster([([1.0, lg(x["p_A"])] + [x[k] for k in INDICATEURS], x["issue"]) for x in app],
                     [2.0, 2.0] + [1.0] * len(INDICATEURS), [0.0, 1.0] + [0.0] * len(INDICATEURS))
        for x in ls:
            if x["jeu"] == j:
                z0 = [1.0, lg(x["p_A"])]
                out.append(dict(x, p_recal=sig(sum(a * b for a, b in zip(w0, z0))),
                                p_indic=sig(sum(a * b for a, b in zip(w1, z0 + [x[k] for k in INDICATEURS]))),
                                coefs=dict(zip(INDICATEURS, [round(v, 3) for v in w1[2:]]))))
    return sorted(out, key=lambda x: (x.get("ordre") or [10 ** 6, x["jeu"]]))


def resumer(ls: list[dict]) -> dict:
    import score_registre as sr
    ok = [x for x in ls if x.get("issue") in (0, 1) and x.get("p_A") is not None]
    if len({x["jeu"] for x in ok}) < 2:
        return {"n": len(ok)}
    cv = validation_croisee(ok)
    n = len(cv)
    moy = lambda c: round(sum(sr.log_score(x[c], x["issue"]) for x in cv) / n, 4)
    tous = ajuster([([1.0, lg(x["p_A"])] + [x[k] for k in INDICATEURS], x["issue"]) for x in ok],
                   [2.0, 2.0] + [1.0] * len(INDICATEURS), [0.0, 1.0] + [0.0] * len(INDICATEURS))
    return {"version_bot": ap.VERSION_BOT, "n": n, "note": "perte log, plus bas = mieux ; validation croisée par jeu",
            "A": moy("p_A"), "B": moy("p_B"), "A_recalibre": moy("p_recal"), "A_recalibre_plus_indicateurs": moy("p_indic"),
            "coefficients_tout": dict(zip(INDICATEURS, [round(v, 3) for v in tous[2:]])),
            "presence": {k: sum(1 for x in ok if (x.get("presents") or {}).get(k)) for k in INDICATEURS},
            "critere": sr.critere_ombre_b([dict(x, p_B=x["p_recal"], o={"p": x["p_indic"]}) for x in cv], "o",
                                          "indicateurs", exclure_vus=False)}


async def principal() -> int:
    a = {}
    for x in ba.lignes():
        if (x.get("source_question") == "acled" and x.get("modeles_A") == MODELE and x.get("p_A") is not None
                and not x.get("exclue") and x.get("issue") in (0, 1)):
            a.setdefault(x["question_id"], x)
    deja = set()
    if FICHIER.exists():
        deja = {json.loads(l)["question_id"] for l in FICHIER.read_text(encoding="utf-8").splitlines() if l.strip()}
    cache_pays, cache_ind = {}, {}
    REGISTRE.mkdir(exist_ok=True)
    async with httpx.AsyncClient(timeout=60, follow_redirects=True, headers=UA) as c:
      with FICHIER.open("a", encoding="utf-8") as fo:
        for q, x in sorted(a.items(), key=lambda t: (t[1].get("ordre") or [10 ** 6, t[1]["jeu"]])):
            if q in deja:
                continue
            nom = pays_de(x["titre"])
            if not nom:
                continue
            f = await fiche_pays(c, nom, cache_pays)
            cle = (nom, x["jeu"])
            if cle not in cache_ind:
                cache_ind[cle] = await indicateurs(c, f, date.fromisoformat(x["jeu"]))
            ind = cache_ind[cle]
            fo.write(json.dumps({"type": "banc_indicateurs", "jeu": x["jeu"], "ordre": x.get("ordre"), "question_id": q,
                                 "pays": nom, "version_bot": ap.VERSION_BOT, "issue": x["issue"], "p_A": x["p_A"],
                                 "p_B": x["p_B"], **ind}, ensure_ascii=False) + "\n")
            fo.flush()
            print(f"{nom[:25]:25s} {x['jeu']} : " + " · ".join(f"{k} {ind[k]:+.2f}" for k in INDICATEURS))
    ls = [json.loads(l) for l in FICHIER.read_text(encoding="utf-8").splitlines() if l.strip()]
    r = resumer(ls)
    RESUME.write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(r, ensure_ascii=False, indent=1)[:3000])
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(principal()))
