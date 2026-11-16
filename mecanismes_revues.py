"""Pilote : mécanismes proposés à partir des résumés de revues de géographie et de sciences sociales (bot 0.10.187).

Décision d'auteur du 2026-11-16 (15 h 18) : « Oui, ça peut toujours servir ». Usage n° 3 des crédits Bedrock : le
modèle PROPOSE des fiches pour le catalogue des mécanismes ; il ne juge rien. Chaque fiche proposée passe ensuite, comme
les autres, le rasoir d'Ockham, l'observatoire et un pré-enregistrement (preenregistrements/catalogue-mecanismes.md).
L'auteur voit les propositions avant toute inscription au catalogue.

1. Récolte (gratuite) : OAI-PMH d'OpenEdition (https://oai.openedition.org/, format oai_dc), revues de la liste
   REVUES ; on garde les articles depuis 2005 dont le titre, le résumé ou les mots-clés touchent aux crises (MOTS).
2. Extraction (payante, plafonnée) : le petit modèle lit titre + résumé + lieux, et rend 0 à 2 mécanismes explicitement
   énoncés par le résumé (une phrase, indicateur observable avant l'événement, sens, saison ou date fixe s'il y en a,
   région, pays, domaine).

Droits : les résumés ne sont PAS conservés (droits des revues) ; on garde la référence (revue, date, titre, URL) et
la fiche proposée, rédigée par le modèle, avec la citation de l'article.

Registres : registre/mecanismes/articles.jsonl ; registre/mecanismes/proposes.jsonl ; registre/mecanismes/resume.md.
Usage : python mecanismes_revues.py [--max 300] [--budget 3]
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
import time
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

import httpx
import garde_injection as gi

OAI = "https://oai.openedition.org/"
DOSSIER = Path("registre") / "mecanismes"
ARTICLES, PROPOSES, RESUME = DOSSIER / "articles.jsonl", DOSSIER / "proposes.jsonl", DOSSIER / "resume.md"
MODELE = os.environ.get("MECANISMES_MODELE", "bedrock/global.anthropic.claude-haiku-4-5-20251001-v1:0")
UA = {"User-Agent": "alphabet-situationnel-bot/1.0 (recherche ; GitHub Othman-Benbrahim)"}

# revues en accès ouvert sur OpenEdition (identifiant de collection OAI « journals:<nom> »), choisies le 2026-11-16
REVUES = ["echogeo", "espacepolitique", "com", "etudesafricaines", "conflits", "geocarrefour", "belgeo", "cybergeo",
          "remi", "emam", "mediterranee", "vertigo", "eps"]   # 0.10.191 : « cdlj » retiré (aucune notice)
MOTS = re.compile(
    r"conflit|violence|émeute|manifestation|protest|riot|insurrection|rébellion|coup d.?[ée]tat|guerre|"
    r"jihad|djihad|terror|famine|soudure|transhumance|pastoral|sécheresse|drought|inondation|flood|élection|election|"
    r"crise|crisis|réfugié|refugee|déplacé|migration forcée|prix alimentaire|food price|coupure|blocage|grève|strike",
    re.I)
NS = {"oai": "http://www.openarchives.org/OAI/2.0/", "dc": "http://purl.org/dc/elements/1.1/",
      "oai_dc": "http://www.openarchives.org/OAI/2.0/oai_dc/"}


def lire_page(xml: bytes) -> tuple[list[dict], str | None, str | None]:
    """(articles, jeton de reprise, erreur OAI)."""
    r = ET.fromstring(xml)
    err = r.find("oai:error", NS)
    if err is not None:
        return [], None, f"{err.get('code')}: {(err.text or '').strip()}"
    out = []
    for rec in r.iter(f"{{{NS['oai']}}}record"):
        md = rec.find(".//oai_dc:dc", NS)
        if md is None:
            continue
        champ = lambda k: [(e.text or "").strip() for e in md.findall(f"dc:{k}", NS) if (e.text or "").strip()]
        ids = [i for i in champ("identifier") if i.startswith("http")]
        out.append({"titre": (champ("title") or [""])[0], "resumes": champ("description"), "date": (champ("date") or [""])[0][:10],
                    "url": ids[0] if ids else "", "sujets": champ("subject")[:15], "lieux": champ("coverage")[:10],
                    "type": " ".join(champ("type"))})
    tok = r.find(".//oai:resumptionToken", NS)
    return out, (tok.text.strip() if tok is not None and tok.text and tok.text.strip() else None), None


def pertinent(a: dict) -> bool:
    if a["date"][:4] < "2005" or "article" not in a["type"].lower() and a["type"]:
        return False
    return bool(MOTS.search(" ".join([a["titre"], *a["resumes"], *a["sujets"]])))


def recolter(c: httpx.Client, revue: str, plafond_pages: int = 60) -> list[dict]:
    params = {"verb": "ListRecords", "metadataPrefix": "oai_dc", "set": f"journals:{revue}"}
    out, pages = [], 0
    while pages < plafond_pages:
        r = c.get(OAI, params=params)
        if r.status_code != 200:
            print(f"  {revue} : HTTP {r.status_code}")
            break
        arts, tok, err = lire_page(r.content)
        if err:
            print(f"  {revue} : erreur OAI {err}")
            break
        if pages == 0 and arts:
            a = arts[0]
            print(f"  {revue} : exemple « {a['titre'][:70]} » ({a['date']}, {len(a['resumes'])} résumé(s), "
                  f"lieux {a['lieux'][:3]}, type {a['type'][:30]})")
        out += [dict(x, revue=revue) for x in arts]
        pages += 1
        if not tok:
            break
        params = {"verb": "ListRecords", "resumptionToken": tok}
        time.sleep(1)
    return out


CONSIGNE = """Tu lis le résumé d'un article de recherche (géographie, sciences sociales). Relève au plus DEUX mécanismes
causaux que le résumé ÉNONCE explicitement et qui pourraient aider à prévoir, quelques jours à quelques semaines à
l'avance, des manifestations, émeutes, violences, crises alimentaires, déplacements de population, coupures ou crises
politiques. N'invente rien : si le résumé n'énonce pas de mécanisme causal, rends une liste vide.

Article : {titre} ({revue}, {date})
Lieux : {lieux}
Résumé :
{resume}

Réponds uniquement par un objet JSON :
{{"mecanismes": [{{"mecanisme": "une phrase : X entraîne Y", "indicateur": "ce qu'on peut observer AVANT l'événement",
"sens": "+ ou -", "periodicite": "saison ou date fixe si le mécanisme revient à date connue, sinon null",
"region": "région concernée", "pays": ["codes ISO à deux lettres"], "domaine": "manifestations | émeutes | violence |
crise alimentaire | déplacements | coupures | crise politique | autre", "citation": "les mots du résumé qui l'énoncent
(15 mots au plus)"}}]}}"""


async def extraire(articles: list[dict], budget: float) -> list[dict]:
    import alphabet_modeles as am
    import alphabet_pipeline as ap
    from forecasting_tools import MonetaryCostManager
    out, cumul = [], 0.0
    for i, a in enumerate(articles):
        if cumul >= budget:
            print(f"Plafond atteint ({cumul:.2f} $ ≥ {budget:.2f} $) après {i} articles.")
            break
        resume = max(a["resumes"], key=len)[:2500] if a["resumes"] else ""
        if len(resume) < 200:
            continue
        with MonetaryCostManager() as cm:
            try:
                r = ap.extraire_json(await am.llm(MODELE, temperature=0.1, timeout=120, allowed_tries=2).invoke(
                    CONSIGNE.format(titre=a["titre"], revue=a["revue"], date=a["date"], lieux=", ".join(a["lieux"]) or "—",
                                    resume=gi.bloc(resume, 6000, origine="résumé de revue (OpenEdition)"))))
                for m in (r.get("mecanismes") or [])[:2]:
                    if isinstance(m, dict) and m.get("mecanisme"):
                        out.append({**{k: m.get(k) for k in ("mecanisme", "indicateur", "sens", "periodicite", "region",
                                                             "pays", "domaine", "citation")},
                                    "source": {"revue": a["revue"], "date": a["date"], "titre": a["titre"], "url": a["url"]},
                                    "origine": "modèle", "modele": MODELE, "statut": "proposé"})
            except Exception as e:
                print(f"  {a['titre'][:50]} : {type(e).__name__}: {str(e)[:80]}")
            cumul += float(cm.current_usage or 0)
        if (i + 1) % 25 == 0:
            print(f"  {i + 1} articles lus, {len(out)} mécanismes proposés, {cumul:.2f} $")
    print(f"Extraction : {len(out)} mécanismes proposés, coût {cumul:.2f} $.")
    return out


def resumer(arts: list[dict], props: list[dict]) -> str:
    dom = Counter((p.get("domaine") or "?") for p in props)
    per = [p for p in props if p.get("periodicite") not in (None, "", "null")]
    l = [f"# Mécanismes proposés à partir des revues (pilote du {time.strftime('%Y-%m-%d')})", "",
         f"{len(arts)} articles retenus ; {len(props)} mécanismes proposés (statut « proposé » : rien n'est inscrit au "
         f"catalogue sans décision d'auteur).", "", "## Par domaine", ""]
    l += [f"- {k} : {v}" for k, v in dom.most_common()]
    l += ["", f"## À date ou saison fixe ({len(per)}) : candidats PÉRIODICITÉ, prévisibles d'avance", ""]
    for p in per[:60]:
        s = p["source"]
        l.append(f"- **{p['mecanisme']}** — {p.get('periodicite')} ; {p.get('region')} ; sens {p.get('sens')} ; "
                 f"[{s['revue']} {s['date'][:4]}]({s['url']})")
    l += ["", "## Autres (extrait)", ""]
    for p in [p for p in props if p not in per][:60]:
        s = p["source"]
        l.append(f"- {p['mecanisme']} — indicateur : {p.get('indicateur')} ; {p.get('region')} ; "
                 f"[{s['revue']} {s['date'][:4]}]({s['url']})")
    return "\n".join(l)


def verifier() -> int:
    """0.10.188 : vérification de l'accès aux revues, sans modèle ni écriture : une page OAI par revue, et un exemple."""
    lignes, ok = ["## Vérification de l'accès aux revues (OAI-PMH d'OpenEdition)", "",
                  "| revue | état | notices sur la 1re page | pertinentes | exemple |", "|---|---|---|---|---|"], 0
    with httpx.Client(headers=UA, timeout=120, follow_redirects=True) as c:
        for revue in REVUES:
            try:
                r = c.get(OAI, params={"verb": "ListRecords", "metadataPrefix": "oai_dc", "set": f"journals:{revue}"})
                if r.status_code != 200:
                    etat, arts = f"HTTP {r.status_code}", []
                else:
                    arts, tok, err = lire_page(r.content)
                    etat = f"erreur OAI {err}" if err else ("ok" if arts else "vide")
            except Exception as e:
                etat, arts = f"{type(e).__name__}", []
            ok += etat == "ok"
            ex = arts[0] if arts else {}
            lignes.append(f"| {revue} | {etat} | {len(arts)} | {sum(pertinent(x) for x in arts)} | "
                          f"{(ex.get('titre') or '')[:60]} ({ex.get('date', '')}, {len(ex.get('resumes') or [])} résumé(s)) |")
            time.sleep(1)
        if ok < len(REVUES):
            try:
                r = c.get(OAI, params={"verb": "ListSets"})
                noms = re.findall(r"<setSpec>(journals:[^<]+)</setSpec>", r.text)
                lignes += ["", f"Collections « journals: » annoncées par le serveur (extrait) : {', '.join(noms[:40])}"]
            except Exception as e:
                lignes += ["", f"ListSets indisponible ({type(e).__name__})"]
    lignes += ["", f"{ok} revue(s) sur {len(REVUES)} accessibles. Aucun appel au modèle, rien d'écrit."]
    texte = "\n".join(lignes)
    print(texte)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
            f.write(texte + "\n")
    return 0 if ok else 1


def principal() -> int:
    ap_ = argparse.ArgumentParser()
    ap_.add_argument("--max", type=int, default=300)
    ap_.add_argument("--budget", type=float, default=3.0)
    ap_.add_argument("--verifier", action="store_true", help="vérifier l'accès aux revues seulement (gratuit)")
    a = ap_.parse_args()
    if a.verifier:
        return verifier()
    tous = []
    with httpx.Client(headers=UA, timeout=120, follow_redirects=True) as c:
        for revue in REVUES:
            arts = recolter(c, revue)
            garde = [x for x in arts if pertinent(x)]
            print(f"{revue} : {len(arts)} notices, {len(garde)} retenues")
            tous += garde
            time.sleep(1)
    vus, uniques = set(), []
    for x in sorted(tous, key=lambda x: x["date"], reverse=True):
        if x["url"] and x["url"] not in vus:
            vus.add(x["url"])
            uniques.append(x)
    choisis = uniques[:a.max]
    print(f"{len(uniques)} articles pertinents ; {len(choisis)} envoyés au modèle (les plus récents).")
    DOSSIER.mkdir(parents=True, exist_ok=True)
    ARTICLES.write_text("\n".join(json.dumps({k: x[k] for k in ("revue", "date", "titre", "url", "lieux", "sujets")},
                                             ensure_ascii=False) for x in choisis) + "\n", encoding="utf-8")
    if not choisis:
        print("Aucun article : rien à extraire.")
        return 1
    props = asyncio.run(extraire(choisis, a.budget))
    PROPOSES.write_text("\n".join(json.dumps(p, ensure_ascii=False) for p in props) + "\n", encoding="utf-8")
    r = resumer(choisis, props)
    RESUME.write_text(r + "\n", encoding="utf-8")
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
            f.write(r + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
