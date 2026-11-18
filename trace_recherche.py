"""Trace et gel de la recherche des bancs de jugement (bot 0.10.258).

Décision d'auteur du 2026-11-18, 11 h 52 (« Ok, pour le 1 à 3 qui ne coûtent rien ») après le diagnostic du bruit
(claude/resultat-jugement-variantes-2026-11-18.md) : M refait sur une recherche relancée passait de 0,363 à 0,403 ;
une partie vient du contenu de la recherche, qui change d'un passage à l'autre, et on ne gardait aucune trace de ce
que le modèle avait lu. Trente questions où Haiku disait connaître l'issue font craindre une fuite (pages publiées ou
mises à jour après la date de la question).

1. TRACER : pour chaque recherche, le moteur qui a répondu, et pour chaque source l'adresse et la date affichée ;
   l'empreinte et la longueur du texte. Aucun texte n'est publié dans le dépôt (droits des articles).
2. CONTRÔLER : sont signalées les sources datées après la date de la question, sans date, ou dont l'adresse porte
   une date postérieure (/2026/05/…) ; et les mots de résolution (« resolved », « was approved »…) n'y sont PAS
   cherchés : on ne lit pas le texte, on regarde les métadonnées.
3. GELER : le texte lu est gardé dans un cache de GitHub Actions (cache/recherche-jugement/, jamais commité) ; un banc
   rejoué sur les mêmes questions relit exactement le même texte.
"""
from __future__ import annotations

import hashlib
import re
from datetime import date, datetime
from pathlib import Path

CACHE = Path("cache/recherche-jugement")
AUCUN = "(aucun résultat publié avant la date chez aucun moteur)"
_MOTEUR = re.compile(r"^\[moteur : ([^\]]+)\]")
_SOURCE = re.compile(r"^\[([^\]]*)\] (.*?) — (\S*)\s*$")
_DATE = re.compile(r"(20\d\d|19\d\d)-(\d\d)-(\d\d)")
_DATE_URL = re.compile(r"/(20\d\d)/(\d{1,2})(?:/(\d{1,2}))?/")


def _jour(s: str) -> date | None:
    m = _DATE.search(s or "")
    if not m:
        return None
    try:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None


def _date_url(url: str) -> date | None:
    m = _DATE_URL.search(url or "")
    if not m:
        return None
    try:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3) or 1))
    except ValueError:
        return None


def tracer(texte: str, jeu: str) -> dict:
    """Métadonnées de ce que le modèle a lu ; les sources suspectes au regard de la date de la question."""
    limite = date.fromisoformat(jeu[:10])
    lignes = (texte or "").splitlines()
    moteur = next((m.group(1) for m in (_MOTEUR.match(l) for l in lignes[:1]) if m), "aucun")
    sources, suspectes = [], []
    for l in lignes:
        m = _SOURCE.match(l)
        if not m:
            continue
        d, url = _jour(m.group(1)), m.group(3)
        du = _date_url(url)
        s = {"date": d.isoformat() if d else None, "url": url[:300]}
        sources.append(s)
        motif = ("datée après la question" if d and d > limite else
                 "adresse datée après la question" if du and du > limite else
                 "sans date" if d is None else None)
        if motif:
            suspectes.append({**s, "motif": motif})
    if (texte or "").startswith("("):
        moteur = "aucun résultat" if texte == AUCUN else "panne"
    return {"moteur": moteur, "n_sources": len(sources), **({"panne": texte[:200]} if moteur == "panne" else {}), "sources": sources, "suspectes": suspectes,
            "empreinte": hashlib.sha1((texte or "").encode()).hexdigest()[:16], "longueur": len(texte or "")}


def _chemin(cle: str) -> Path:
    return CACHE / (hashlib.sha1(cle.encode()).hexdigest() + ".txt")


def lire_cache(cle: str) -> str | None:
    p = _chemin(cle)
    return p.read_text(encoding="utf-8") if p.exists() else None


def ecrire_cache(cle: str, texte: str) -> None:
    if not texte or texte.startswith("(recherche indisponible"):
        return                                 # une panne ne se gèle pas : elle sera retentée
    CACHE.mkdir(parents=True, exist_ok=True)
    _chemin(cle).write_text(texte, encoding="utf-8")


async def chercher_fige(cle: str, requete: str, avant: datetime, chercher) -> tuple[str, bool]:
    """Le texte gelé s'il existe, sinon une recherche neuve gelée aussitôt. Rend (texte, venait_du_cache)."""
    import alphabet_recherche as ar_
    t = lire_cache(cle)
    if t is not None:
        return ar_.sans_foule(ar_.filtrer(t, retro=True))[0], True     # 0.10.260 : le gel antérieur au filtre est filtré à la lecture
    try:
        t = await chercher(requete, avant)
    except Exception as e:
        msg = str(e)
        if "aucun moteur" in msg and all("aucun résultat" in m for m in msg.split("(", 1)[-1].split(";")):
            # 0.10.260 : rien n'existe avant la date chez aucun moteur : c'est une réponse, elle se gèle
            t = AUCUN
            ecrire_cache(cle, t)
            return t, False
        return f"(recherche indisponible : {type(e).__name__}: {msg[:150]})", False
    ecrire_cache(cle, t)
    return t, False


TRACES = Path("registre/trace-recherche-jugement.jsonl")


def resumer_traces(ls: list[dict]) -> dict:
    """Sources suspectes : questions où Haiku a dit connaître l'issue, contre les autres."""
    out = {}
    for nom, g in (("haiku_dit_connaitre", [x for x in ls if x.get("haiku_dit_connaitre")]),
                   ("autres", [x for x in ls if not x.get("haiku_dit_connaitre")])):
        n = len(g)
        if not n:
            continue
        motifs: dict[str, int] = {}
        for x in g:
            for s in x["trace"]["suspectes"]:
                motifs[s["motif"]] = motifs.get(s["motif"], 0) + 1
        out[nom] = {"questions": n, "sources_par_question": round(sum(x["trace"]["n_sources"] for x in g) / n, 2),
                    "questions_avec_source_suspecte": sum(1 for x in g if x["trace"]["suspectes"]),
                    "sans_recherche": sum(1 for x in g if x["trace"]["moteur"] in ("aucun", "panne", "aucun résultat")),
                    "motifs": motifs,
                    "moteurs": {m: sum(1 for x in g if x["trace"]["moteur"] == m) for m in {x["trace"]["moteur"] for x in g}}}
    return out


async def principal(n: int) -> int:
    """Recherche seule (aucun modèle de langue) sur les questions du banc jugement_alphabet : gèle et trace."""
    import json
    from datetime import timezone

    import alphabet_retro as ar
    import banc_jugement_alphabet as bja
    import banc_jugement_variantes as bv
    if not ar.recherche_bornee_disponible():
        print("Il faut une recherche bornable dans le temps (EXA_API_KEY ou TINYFISH_API_KEY).")
        return 1
    base = bv.base_banc()
    haiku = {x["question_id"]: bool(x["haiku"].get("exclue")) for x in bv.lignes()}
    # 0.10.260 : une recherche en échec (« aucun » ou « panne ») est retentée ; la dernière ligne d'une question fait foi
    anciennes = [json.loads(l) for l in TRACES.read_text(encoding="utf-8").splitlines() if l.strip()] if TRACES.exists() else []
    deja = {x["question_id"] for x in anciennes if x["trace"]["moteur"] not in ("aucun", "panne")}
    faites = 0
    with TRACES.open("a", encoding="utf-8") as f:
        for x in bja.candidates():
            qid = f'{x["source"]}:{x["id"]}:{x["jeu"]}'
            if faites >= n:
                break
            if qid not in base or qid in deja:
                continue
            info = datetime.fromisoformat(x["jeu"]).replace(tzinfo=timezone.utc)
            texte, du_cache = await chercher_fige(qid, x["titre"], info, ar.chercher_avant)
            f.write(json.dumps({"question_id": qid, "jeu": x["jeu"], "issue": x["issue"],
                                "haiku_dit_connaitre": haiku.get(qid), "trace": tracer(texte, x["jeu"]),
                                "cache": du_cache}, ensure_ascii=False) + "\n")
            faites += 1
    ls = list({x["question_id"]: x for x in (json.loads(l) for l in TRACES.read_text(encoding="utf-8").splitlines()
                                              if l.strip())}.values())
    r = resumer_traces(ls)
    Path("registre/trace-recherche-jugement.json").write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{faites} recherche(s) tracée(s) et gelée(s).\n" + json.dumps(r, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    import argparse
    import asyncio
    import sys
    a = argparse.ArgumentParser()
    a.add_argument("--n", type=int, default=309)
    sys.exit(asyncio.run(principal(a.parse_args().n)))
