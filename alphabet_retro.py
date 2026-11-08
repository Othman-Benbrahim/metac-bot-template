"""Tests rétrospectifs de l'alphabet, pour UNE seule chose : mesurer le biais de C par rapport à B et apprendre le
décalage qui le corrige (0.5.0). Rien n'est posté sur Metaculus.

    uv run python alphabet_retro.py --n 5 --apres 2026-07-01

Le risque d'un test rétrospectif est la fuite : le modèle ou la recherche connaissent l'issue (§26). Trois parades :
  1. questions résolues APRÈS --apres (à choisir après la date de connaissance du modèle) ;
  2. recherche web bornée à la date d'information (Exa, date de publication ; les pages sans date sont écartées) ;
  3. sonde : avant tout, on demande au modèle s'il connaît l'issue ; s'il la connaît et a raison, la question est exclue.
Le bras A n'est pas calculé (sa recherche n'est pas bornée dans le temps). Les lignes vont dans registre/retro.jsonl,
scellées, jamais mélangées au journal des prévisions réelles.

Sens de la fuite résiduelle : un modèle qui devine l'issue ancre des cartes sur les OUI et n'en trouve pas sur les NON,
ce qui fait paraître C MEILLEUR qu'il n'est. Le décalage appris ici est donc, au pire, trop faible : il corrige dans le
bon sens sans surcorriger.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime, timezone

import alphabet_pipeline as ap

RETRO = "retro.jsonl"


def deja_faites() -> set[str]:
    f = ap.REGISTRE / RETRO
    if not f.is_file():
        return set()
    return {json.loads(x)["question_id"] for x in f.read_text(encoding="utf-8").splitlines() if x.strip()}


def consigne_sonde(titre: str, criteres: str) -> str:
    return f"""Sans faire de recherche, sais-tu comment cette question de prévision a été résolue ?

QUESTION : {titre}
CRITÈRES : {criteres}

Réponds honnêtement. Rends UNIQUEMENT un objet JSON : {{"connait": true ou false, "issue": "yes" | "no" | null}}"""


_CHAINE = None


async def chercher_avant(requete: str, avant: datetime) -> str:
    """0.6.1 : Exa borné à la date d'information (seconde clé si la première échoue), puis GDELT, borné lui aussi.
    Tavily n'est pas utilisé ici : leur bornage par date est moins sûr, et la fuite est le risque n° 1."""
    global _CHAINE
    import alphabet_recherche as ar_
    if _CHAINE is None:
        _CHAINE = ar_.Chaine(None, ordre="exa,gdelt")
    _CHAINE.exa = lambda q: _exa_avant(q, avant)
    return await _CHAINE.chercher(requete, avant)


async def _exa_avant(requete: str, avant: datetime) -> str:
    """Recherche Exa bornée à la date d'information : seules les pages DATÉES et publiées avant comptent."""
    from forecasting_tools.ai_models.exa_searcher import ExaSearcher, SearchInput
    s = SearchInput(web_search_query=requete, highlight_query=requete, include_domains=[], exclude_domains=[],
                    include_text=None, start_published_date=None, end_published_date=avant)
    sources = await ExaSearcher(include_text=False, include_highlights=True, num_results=6).invoke(s)
    garde = [x for x in sources if x.published_date is not None and x.published_date.astimezone(timezone.utc) <= avant]
    return "\n\n".join(f"[{x.readable_publish_date}] {x.title or ''} — {x.url or ''}\n" + " … ".join(x.highlights[:3])
                       for x in garde)


async def historique_avant(cles: list[str], aujourdhui: str) -> list[dict]:
    from forecasting_tools import ApiFilter, MetaculusClient
    avant = datetime.fromisoformat(aujourdhui).replace(tzinfo=timezone.utc)
    sortie = []
    for cle in cles:
        f = ApiFilter(allowed_types=["binary"], allowed_statuses=["resolved"], scheduled_resolve_time_lt=avant,
                      other_url_parameters={"search": cle})
        for q in (await MetaculusClient().get_questions_matching_filter(f))[:10]:
            fin = q.actual_resolution_time or q.scheduled_resolution_time
            sortie.append({"titre": q.question_text, "issue": q.resolution_string,
                           "resolue_le": fin.date().isoformat() if fin else None})
    return sortie


async def un_test(mq, llm, deja: set[str]) -> dict | None:
    """Une question résolue : sonde, puis bras B et C à la date d'information, scellés avec l'issue."""
    qid = str(mq.id_of_question)
    issue = (mq.resolution_string or "").lower()
    debut = mq.open_time or mq.published_time
    fin = mq.scheduled_resolution_time or mq.actual_resolution_time
    if qid in deja or issue not in ("yes", "no") or debut is None or fin is None or fin <= debut:
        return None
    info = debut.astimezone(timezone.utc)
    ligne = {"type": "retro", "version_bot": ap.VERSION_BOT, "version_skill": ap.version_skill(), "question_id": qid,
             "modeles": ap.modeles_actifs(),
             "url": mq.page_url, "titre": mq.question_text, "date_information": info.date().isoformat(),
             "resolution": fin.date().isoformat(), "issue": 1 if issue == "yes" else 0}
    try:
        sonde = ap.extraire_json(await llm(consigne_sonde(mq.question_text, mq.resolution_criteria or "")))
    except Exception as e:
        sonde = {"erreur": str(e)[:200]}
    ligne["sonde"] = sonde
    if sonde.get("connait") is True and str(sonde.get("issue") or "").lower() == issue:
        ligne["statut"] = "exclue_connue"          # le modèle connaît l'issue : la question ne mesure rien
        return ligne
    q = ap.Question(id=qid, url=mq.page_url or "", titre=mq.question_text, contexte=mq.background_info or "",
                    criteres=mq.resolution_criteria or "", precisions=mq.fine_print or "", resolution=fin.date())
    jours = max(1, (fin.date() - info.date()).days)

    async def chercher(req: str) -> str:
        return await chercher_avant(req, info)
    c = await ap.alphabet(q, "", llm, chercher, True, info.date().isoformat(), jours, historique_avant)
    ligne.update(statut=c.get("statut"), p_B=c.get("p_B"), p_C=c.get("p_C"), motif=c.get("motif"),
                 evenement=c.get("evenement"), etat=c.get("etat"), vues=c.get("vues"), classe_statut=c.get("classe_statut"),
                 nature_etat_nul=c.get("nature_etat_nul"),
                 attribution=ap.controle_attribution(c.get("dossier"), c.get("_textes")))
    if c.get("dossier") is not None:
        d = ap.REGISTRE / "dossiers-retro"
        d.mkdir(parents=True, exist_ok=True)
        nom = f"{qid}-{info.date().isoformat()}.json"
        (d / nom).write_text(json.dumps(c["dossier"], ensure_ascii=False, indent=1), encoding="utf-8")
        ligne["dossier_fichier"] = f"dossiers-retro/{nom}"
        ligne["dossier_sha256"] = ap.sceau(c["dossier"])
    return ligne


def ecrire(ligne: dict) -> None:
    ap.REGISTRE.mkdir(parents=True, exist_ok=True)
    ligne["sceau"] = ap.sceau(ligne)
    with open(ap.REGISTRE / RETRO, "a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(ligne, ensure_ascii=False, sort_keys=True) + "\n")


async def principal(n: int, apres: str) -> int:
    from forecasting_tools import ApiFilter, MetaculusClient
    import alphabet_bot as ab
    cherche = os.environ.get("ALPHABET_CHERCHEUR", "")
    if not cherche.startswith("smart-searcher") or not os.environ.get("EXA_API_KEY"):
        print("Tests rétrospectifs : la recherche doit être Exa (smart-searcher + EXA_API_KEY), seule bornable dans le "
              "temps ici. Rien n'est lancé.")
        return 1
    import alphabet_modeles as am
    choix, essais = await am.choisir()       # 0.6.0 : suites de modèles, le premier qui répond
    for e_ in essais:
        print(f"{'✅' if e_['json_ok'] else '❌'}  {e_['role']} : {e_['modele']}")
    if not choix["principal"]:
        print("Aucun modèle principal disponible. Rien n'est lancé.")
        return 1
    am.appliquer(choix)
    llm_modele = ab.configuration().get("default")
    if llm_modele is None:
        print("ALPHABET_LLM manquant.")
        return 1

    async def llm(consigne: str) -> str:
        return await llm_modele.invoke(consigne)
    seuil = datetime.fromisoformat(apres).replace(tzinfo=timezone.utc)
    f = ApiFilter(allowed_types=["binary"], allowed_statuses=["resolved"], scheduled_resolve_time_gt=seuil,
                  scheduled_resolve_time_lt=datetime.now(timezone.utc))
    candidates = await MetaculusClient().get_questions_matching_filter(f, num_questions=max(4 * n, 20),
                                                                       randomly_sample=True,
                                                                       error_if_question_target_missed=False)
    deja, faites = deja_faites(), 0
    for mq in candidates:
        if faites >= n:
            break
        try:
            ligne = await un_test(mq, llm, deja)
        except Exception as e:
            ligne = {"type": "retro", "version_bot": ap.VERSION_BOT, "question_id": str(mq.id_of_question),
                     "url": mq.page_url, "statut": "erreur", "motif": f"{type(e).__name__}: {e}"[:300]}
        if ligne is None:
            continue
        ecrire(ligne)
        deja.add(ligne["question_id"])
        faites += 1
        print(f"{ligne['question_id']} : {ligne.get('statut')} · B {ligne.get('p_B')} · C {ligne.get('p_C')} · "
              f"issue {ligne.get('issue')}")
    print(f"{faites} test(s) rétrospectif(s) écrit(s) dans registre/{RETRO}.")
    return 0


if __name__ == "__main__":
    a = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    a.add_argument("--n", type=int, default=int(os.environ.get("ALPHABET_RETRO_N") or 5), help="questions à tester")
    a.add_argument("--apres", default=os.environ.get("ALPHABET_RETRO_APRES") or "2026-07-01",
                   help="questions résolues après cette date (après la date de connaissance du modèle)")
    args = a.parse_args()
    sys.exit(asyncio.run(principal(args.n, args.apres)))
