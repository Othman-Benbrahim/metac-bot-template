"""Banc Wikipédia : l'attention du public (pages vues) et l'agitation anticipée (protections d'articles) — 0.10.298.

Décision d'auteur du 2026-11-18, 22 h 30 (« je valide l'ensemble, plus de folie »). Préenregistrement :
preenregistrements/wikipedia.md. Sources officielles et gratuites de la Wikimedia Foundation, données agrégées et
DATÉES (aucune fuite possible : chaque chiffre porte son jour) :
- pages vues par article et par jour (API REST Wikimedia, données CC0) ;
- journal des protections d'articles (API MediaWiki, logevents type « protect ») : un administrateur qui verrouille
  l'article d'un dirigeant ou d'un pays anticipe une vague de modifications.
Aucun appel à un modèle, aucune cote, aucune personne privée (seulement les articles des entités nommées dans les
titres des questions : pays, institutions, personnalités publiques).

    python banc_wikipedia.py --collecter      # interroge Wikimedia (GitHub Actions), écrit registre/wikipedia-comptes.json
    python banc_wikipedia.py                  # calcule le banc à partir des comptes
"""
from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import quote

import alphabet_pipeline as ap
import banc_attention_gdelt as ba
import banc_jugement as bj
import banc_tendance_large as btl

COMPTES = Path("registre/wikipedia-comptes.json")
RESUME = Path("registre/banc-wikipedia.json")
UA = "alphabet-situationnel/0.10 (https://github.com/Othman-Benbrahim/metac-bot-template; recherche non commerciale)"
API = "https://en.wikipedia.org/w/api.php"
VUES = "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia/all-access/user/{t}/daily/{a}/{b}"
FENETRE = 90
MAX_ENTITES = 2
COMMUNS = {"Will", "Who", "What", "When", "Which", "How", "Before", "By", "After", "The", "A", "An", "In", "On", "At",
           "Yes", "No", "January", "February", "March", "April", "May", "June", "July", "August", "September",
           "October", "November", "December", "Q1", "Q2", "Q3", "Q4", "US", "U.S.", "President", "Prime", "Minister"}


def entites(titre: str) -> list[str]:
    """Groupes de mots à majuscule du titre (noms propres), les plus longs d'abord, au plus MAX_ENTITES."""
    groupes = re.findall(r"[A-Z][\w'’.-]+(?:\s+(?:of|de|la|the)?\s*[A-Z][\w'’.-]+)*", titre or "")
    out = []
    for g in groupes:
        mots = [m for m in g.split() if m not in COMMUNS]
        while mots and mots[0].islower():
            mots.pop(0)
        while mots and mots[-1].islower():
            mots.pop()
        g = " ".join(mots).strip()
        if len(g) >= 3 and not re.fullmatch(r"[\d\W]+", g) and g not in out:
            out.append(g)
    return sorted(out, key=lambda g: (-len(g.split()), -len(g)))[:MAX_ENTITES]


def questions() -> list[dict]:
    """Les questions distinctes de 2026 du jeu de données (première date de jeu), comme le banc de la tendance large."""
    xs = bj.cohorte_complete([json.loads(l) for l in bj.REGISTRE.read_text(encoding="utf-8").splitlines() if l.strip()])
    vus, out = set(), []
    for x in sorted(xs, key=lambda x: x["jeu"]):
        k = f'{x["source"]}:{x["id"]}'
        if k in vus:
            continue
        vus.add(k)
        if x["jeu"] >= "2026-01-01":
            out.append({"qid": f'{k}:{x["jeu"]}', "titre": x["titre"], "jeu": x["jeu"]})
    return out


async def _json(client, url: str, params: dict | None = None) -> dict:
    for essai in range(3):
        r = await client.get(url, params=params)
        if r.status_code == 429:
            await asyncio.sleep(5 * (essai + 1))
            continue
        if r.status_code == 404:
            return {}
        r.raise_for_status()
        return r.json()
    return {}


async def article(client, entite: str, cache: dict) -> str | None:
    if entite not in cache:
        d = await _json(client, API, {"action": "query", "list": "search", "srsearch": entite, "srlimit": 1,
                                      "format": "json"})
        res = (d.get("query") or {}).get("search") or []
        cache[entite] = res[0]["title"] if res else None
    return cache[entite]


async def vues(client, titre: str, debut: date, fin: date) -> dict[str, int]:
    url = VUES.format(t=quote(titre.replace(" ", "_"), safe=""), a=debut.strftime("%Y%m%d"), b=fin.strftime("%Y%m%d"))
    d = await _json(client, url)
    return {f'{i["timestamp"][:4]}-{i["timestamp"][4:6]}-{i["timestamp"][6:8]}': int(i["views"]) for i in d.get("items", [])}


async def protections(client, titre: str, debut: date, fin: date) -> int:
    d = await _json(client, API, {"action": "query", "list": "logevents", "letype": "protect", "letitle": titre,
                                  "lestart": f"{fin.isoformat()}T23:59:59Z", "leend": f"{debut.isoformat()}T00:00:00Z",
                                  "lelimit": 50, "format": "json"})
    return len((d.get("query") or {}).get("logevents") or [])


async def collecter() -> int:
    import httpx
    qs = questions()
    base = json.loads(COMPTES.read_text(encoding="utf-8")) if COMPTES.exists() else {}
    cache: dict[str, str | None] = {}
    sem = asyncio.Semaphore(4)
    async with httpx.AsyncClient(headers={"User-Agent": UA}, timeout=30) as client:
        async def une(q):
            if q["qid"] in base:
                return
            async with sem:
                jeu = date.fromisoformat(q["jeu"][:10])
                debut, fin = jeu - timedelta(days=FENETRE), jeu - timedelta(days=1)
                jours: dict[str, int] = {}
                arts, prot = [], 0
                try:
                    for e in entites(q["titre"]):
                        t = await article(client, e, cache)
                        if not t or t in arts:
                            continue
                        arts.append(t)
                        for j, n in (await vues(client, t, debut, fin)).items():
                            jours[j] = jours.get(j, 0) + n
                        prot += await protections(client, t, debut, fin)
                    base[q["qid"]] = {"debut": debut.isoformat(), "fin": fin.isoformat(), "articles": arts,
                                      "jours": jours, "protections": prot, "filtrable": bool(arts)}
                except Exception as e:
                    print(f"{q['qid']} : {type(e).__name__}: {str(e)[:120]}", flush=True)
        await asyncio.gather(*(une(q) for q in qs))
    COMPTES.write_text(json.dumps(base, ensure_ascii=False), encoding="utf-8")
    print(f"{len(qs)} questions ; {sum(1 for v in base.values() if v['articles'])} avec au moins un article Wikipédia.")
    return 0


def resumer(ls: list[dict], cpt: dict) -> dict:
    import profil_erreurs as pe
    import psychometrie_alphabet as ps
    import score_registre as sr
    out = {"version_bot": ap.VERSION_BOT, "questions": len(ls), "avec_articles": sum(1 for x in ls if x["articles"]),
           "note": "questions distinctes de 2026 ; base S ; β appris sans la question jugée ; pages vues Wikipédia (en)"}
    if len(ls) < 50:
        return dict(out, verdict="en attente (python banc_wikipedia.py --collecter)")
    p_aj, beta = btl.loo(ls, "p_S")
    n = len(ls)
    out.update({"perte_S": round(sum(ba._pl(x["p_S"], x["issue"]) for x in ls) / n, 4),
                "perte_ajustee": round(sum(ba._pl(p, x["issue"]) for x, p in zip(ls, p_aj)) / n, 4),
                "beta_sur_tout": beta,
                "critere": sr.critere_ombre_b([dict(x, p_B=x["p_S"], o={"p": p}) for x, p in zip(ls, p_aj)], "o",
                                              "tendance_wikipedia", exclure_vus=False, bloc_par="question", tout_juger=True),
                "par_source": {s: {"n": len(v), "S": round(sum(ba._pl(x["p_S"], x["issue"]) for x, _ in v) / len(v), 4),
                                   "ajustee": round(sum(ba._pl(p, x["issue"]) for x, p in v) / len(v), 4)}
                               for s in sorted({x["source"] for x in ls})
                               for v in [[(x, p) for x, p in zip(ls, p_aj) if x["source"] == s]]},
                "profils": pe.profils([dict(x, p_aj=p) for x, p in zip(ls, p_aj)], {"S": "p_S", "ajuste": "p_aj"}),
                "unites": pe.unites(ls)})
    avec = [x for x in ls if x["articles"]]
    if len(avec) >= 10:
        out["spearman_tendance_issue"] = round(ps.spearman([x["tendance"] for x in avec], [x["issue"] for x in avec]), 3)
    # descriptif : protections d'articles (agitation anticipée) et lien avec la tendance GDELT
    prot = [x for x in ls if x["protections"] > 0]
    sans = [x for x in ls if x["articles"] and x["protections"] == 0]
    out["protections_descriptif"] = {
        "questions_avec_protection": len(prot),
        "oui_avec_protection": round(sum(x["issue"] for x in prot) / len(prot), 3) if prot else None,
        "S_moyen_avec_protection": round(sum(x["p_S"] for x in prot) / len(prot), 3) if prot else None,
        "oui_sans_protection": round(sum(x["issue"] for x in sans) / len(sans), 3) if sans else None,
        "S_moyen_sans_protection": round(sum(x["p_S"] for x in sans) / len(sans), 3) if sans else None}
    gd = {x["question_id"]: x["tendance"] for x in btl.donnees()} if btl.COMPTES.exists() else {}
    paires = [(x["tendance"], gd[x["question_id"]]) for x in avec if x["question_id"] in gd]
    if len(paires) >= 10:
        out["rang_wikipedia_contre_gdelt"] = round(ps.spearman([a for a, _ in paires], [b for _, b in paires]), 3)
    return out


def donnees() -> tuple[list[dict], dict]:
    cpt = json.loads(COMPTES.read_text(encoding="utf-8")) if COMPTES.exists() else {}
    xs = bj.cohorte_complete([json.loads(l) for l in bj.REGISTRE.read_text(encoding="utf-8").splitlines() if l.strip()])
    bj.calculer(xs)
    out = []
    for x in xs:
        qid = f'{x["source"]}:{x["id"]}:{x["jeu"]}'
        if qid not in cpt:
            continue
        e = cpt[qid]
        s = ba.serie(e)
        out.append({"question_id": qid, "source": x["source"], "issue": x["issue"], "p_S": x["p_S"],
                    "articles": len(e.get("articles") or []), "tendance": ba.tendance(s),
                    "protections": int(e.get("protections") or 0)})
    return sorted(out, key=lambda x: x["question_id"]), cpt


def principal(collecte: bool) -> int:
    if collecte:
        return asyncio.run(collecter())
    ls, cpt = donnees()
    r = resumer(ls, cpt)
    RESUME.write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(r, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("--collecter", action="store_true")
    sys.exit(principal(a.parse_args().collecter))
