"""Pilote : mécanismes proposés à partir des Brèves stratégiques de l'IRSEM (bot 0.10.201).

Décision d'auteur du 2026-11-16 (18 h 47). L'IRSEM (Institut de recherche stratégique de l'École militaire) ne publie ni
flux RSS ni données : comme compteur, ses publications arrivent après les faits. On en tire seulement des PROPOSITIONS
de mécanismes pour le catalogue (preenregistrements/catalogue-mecanismes.md), comme le pilote des revues (0.10.187) :
le modèle propose, il ne juge rien ; l'auteur voit tout avant toute inscription.

Règle d'arrêt fixée AVANT le pilote : si moins de 3 mécanismes proposés sont à la fois prévisionnels (un précurseur
observable quelques jours à quelques semaines avant l'événement) et généraux (valables au-delà du cas étudié), on
arrête là.

1. Récolte (gratuite) : pages de https://www.irsem.fr/publications, puis page de chaque publication (série, numéro,
   mois, lien PDF). Série retenue par défaut : « Brève stratégique » (textes courts, orientés vers l'action).
2. Extraction (payante, plafonnée) : texte du PDF (6 premières pages, 12 000 caractères au plus), passé par la garde
   contre l'injection (0.10.198) ; le petit modèle rend 0 à 2 mécanismes ÉNONCÉS par le texte.

Droits : les textes ne sont PAS conservés ; on garde la référence (série, numéro, mois, titre, URL) et la fiche
proposée, avec une citation de 15 mots au plus.

Registres : registre/mecanismes/irsem-publications.jsonl ; irsem-proposes.jsonl ; irsem-resume.md.
Usage : python mecanismes_irsem.py --verifier | [--serie "Brève stratégique"] [--max 60] [--budget 1]
(le workflow lance le script avec `uv run --with pypdf`).
"""
from __future__ import annotations

import argparse
import asyncio
import html
import io
import json
import os
import re
import sys
import time
from collections import Counter
from pathlib import Path

import httpx

import garde_injection as gi

BASE = "https://www.irsem.fr"
LISTE = BASE + "/publications"
DOSSIER = Path("registre") / "mecanismes"
PUBLICATIONS = DOSSIER / "irsem-publications.jsonl"
PROPOSES = DOSSIER / "irsem-proposes.jsonl"
RESUME = DOSSIER / "irsem-resume.md"
MODELE = os.environ.get("MECANISMES_MODELE", "bedrock/global.anthropic.claude-haiku-4-5-20251001-v1:0")
UA = {"User-Agent": "alphabet-situationnel-bot/1.0 (recherche ; GitHub Othman-Benbrahim)"}
SERIES = ("Brève stratégique", "Étude", "Note de recherche", "Note stratégique", "Veille stratégique")
_LIEN = re.compile(r'href="(?:https?://www\.irsem\.fr)?(/publications/[a-z0-9][a-z0-9-]+)/?"', re.I)
_ETIQUETTE = re.compile(r"(Brève stratégique|Étude|Note de recherche|Note stratégique|Veille stratégique)"
                        r"\s*(?:n°\s*)?(\d+)?\s*[-–—]\s*(?:\d{2}/)?(\d{2})/(\d{4})", re.I)
_PDF = re.compile(r'href="([^"]+?\.pdf)"', re.I)
_TITRE = re.compile(r"<h1[^>]*>(.*?)</h1>", re.I | re.S)


def liens_de_page(page_html: str) -> list[str]:
    vus, out = set(), []
    for chemin in _LIEN.findall(page_html):
        if chemin not in vus:
            vus.add(chemin)
            out.append(BASE + chemin)
    return out


def lister(c: httpx.Client, pages_max: int = 30) -> list[str]:
    out: list[str] = []
    for n in range(1, pages_max + 1):
        r = c.get(LISTE, params={"page": n} if n > 1 else None)
        if r.status_code != 200:
            print(f"  page {n} : HTTP {r.status_code}")
            break
        nouveaux = [u for u in liens_de_page(r.text) if u not in out]
        if not nouveaux:
            break
        out += nouveaux
        time.sleep(1)
    return out


def fiche(page_html: str, url: str) -> dict:
    t = re.sub(r"<[^>]+>", " ", page_html)
    t = html.unescape(re.sub(r"\s+", " ", t))
    e = _ETIQUETTE.search(t)
    pdf = next((p for p in _PDF.findall(page_html) if "file_manager" in p or "storage" in p), None) or \
        next(iter(_PDF.findall(page_html)), None)
    titre = _TITRE.search(page_html)
    return {"url": url,
            "serie": next((s for s in SERIES if e and e.group(1).lower() == s.lower()), e.group(1) if e else None),
            "numero": int(e.group(2)) if e and e.group(2) else None,
            "mois": f"{e.group(4)}-{e.group(3)}" if e else None,
            "titre": html.unescape(re.sub(r"<[^>]+>|\s+", " ", titre.group(1))).strip() if titre else None,
            "pdf": (BASE + pdf if pdf and pdf.startswith("/") else pdf)}


def texte_pdf(contenu: bytes, pages: int = 6, n: int = 12000) -> str:
    from pypdf import PdfReader
    r = PdfReader(io.BytesIO(contenu))
    return "\n".join((p.extract_text() or "") for p in r.pages[:pages])[:n]


CONSIGNE = """Tu lis une note d'analyse stratégique (IRSEM, institut de recherche du ministère des Armées). Relève au plus
DEUX mécanismes causaux que le texte ÉNONCE explicitement et qui pourraient aider à prévoir, quelques jours à quelques
semaines à l'avance, un événement observable : conflit armé, attaque, coup d'État, crise politique, élection
contestée, sanctions, rupture diplomatique, perturbation maritime ou commerciale, coupure, opération d'influence,
manifestations. N'invente rien : si le texte n'énonce pas de mécanisme causal de ce genre, rends une liste vide.

Publication : {titre} ({serie} {numero}, {mois})

{texte}

Réponds uniquement par un objet JSON :
{{"mecanismes": [{{"mecanisme": "une phrase : X entraîne Y", "indicateur": "ce qu'on peut observer AVANT l'événement",
"delai": "délai entre l'indicateur et l'événement, selon le texte, ou null", "sens": "+ ou -",
"portee": "cas | région | général (le texte le présente-t-il comme valable au-delà du cas étudié ?)",
"region": "région concernée", "pays": ["codes ISO à deux lettres"], "domaine": "conflit | attaque | coup d'État |
crise politique | élection | sanctions | diplomatie | maritime ou commerce | coupure | influence | manifestations |
autre", "citation": "les mots du texte qui l'énoncent (15 mots au plus)"}}]}}"""


async def extraire(c: httpx.Client, pubs: list[dict], budget: float) -> list[dict]:
    import alphabet_modeles as am
    import alphabet_pipeline as ap
    from forecasting_tools import MonetaryCostManager
    out, cumul = [], 0.0
    for i, p in enumerate(pubs):
        if cumul >= budget:
            print(f"Plafond atteint ({cumul:.2f} $ ≥ {budget:.2f} $) après {i} publications.")
            break
        try:
            r = c.get(p["pdf"])
            r.raise_for_status()
            texte = texte_pdf(r.content)
        except Exception as e:
            print(f"  PDF illisible : {p['url']} ({type(e).__name__})")
            continue
        if len(texte) < 500:
            print(f"  texte trop court ({len(texte)} car.) : {p['url']}")
            continue
        with MonetaryCostManager() as cm:
            try:
                rep = ap.extraire_json(await am.llm(MODELE, temperature=0.1, timeout=180, allowed_tries=2).invoke(
                    CONSIGNE.format(titre=p.get("titre") or "?", serie=p.get("serie") or "", numero=p.get("numero") or "",
                                    mois=p.get("mois") or "", texte=gi.bloc(texte, 12000, origine="publication IRSEM"))))
                for m in (rep.get("mecanismes") or [])[:2]:
                    if isinstance(m, dict) and m.get("mecanisme"):
                        out.append({**{k: m.get(k) for k in ("mecanisme", "indicateur", "delai", "sens", "portee", "region",
                                                             "pays", "domaine", "citation")},
                                    "source": {k: p.get(k) for k in ("serie", "numero", "mois", "titre", "url")},
                                    "origine": "modèle", "modele": MODELE, "statut": "proposé"})
            except Exception as e:
                print(f"  {str(p.get('titre'))[:50]} : {type(e).__name__}: {str(e)[:80]}")
            cumul += float(cm.current_usage or 0)
        time.sleep(1)
    print(f"Extraction : {len(out)} mécanismes proposés, coût {cumul:.2f} $.")
    return out


def candidats(props: list[dict]) -> list[dict]:
    """Règle d'arrêt (fixée avant le pilote) : indicateur présent, délai énoncé, portée régionale ou générale."""
    return [p for p in props if (p.get("indicateur") or "").strip() and p.get("delai") not in (None, "", "null")
            and str(p.get("portee") or "").lower() in ("région", "region", "général", "general")]


def resumer(pubs: list[dict], props: list[dict]) -> str:
    cand = candidats(props)
    l = [f"# Mécanismes proposés à partir de l'IRSEM (pilote du {time.strftime('%Y-%m-%d')})", "",
         f"{len(pubs)} publications lues ; {len(props)} mécanismes proposés ; {len(cand)} passent le filtre de la règle "
         f"d'arrêt (indicateur, délai énoncé, portée régionale ou générale). Règle : moins de 3 → on arrête là. "
         f"Rien n'est inscrit au catalogue sans décision d'auteur.", "",
         "## Par domaine", ""]
    l += [f"- {k} : {v}" for k, v in Counter((p.get("domaine") or "?") for p in props).most_common()]
    l += ["", f"## Candidats ({len(cand)})", ""]
    for p in cand:
        s = p["source"]
        l.append(f"- **{p['mecanisme']}** — indicateur : {p.get('indicateur')} ; délai : {p.get('delai')} ; "
                 f"portée : {p.get('portee')} ; {p.get('region')} ; [{s.get('serie')} {s.get('numero')}, {s.get('mois')}]({s.get('url')})")
    l += ["", "## Autres", ""]
    for p in [p for p in props if p not in cand]:
        s = p["source"]
        l.append(f"- {p['mecanisme']} — portée : {p.get('portee')} ; délai : {p.get('delai')} ; "
                 f"[{s.get('serie')} {s.get('numero')}]({s.get('url')})")
    return "\n".join(l)


def _sommaire(texte: str) -> None:
    print(texte)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
            f.write(texte + "\n")


def verifier(c: httpx.Client) -> int:
    """Accès au site, sans modèle ni écriture : liste, une fiche, un PDF."""
    urls = lister(c, pages_max=2)
    l = ["## Vérification de l'accès à l'IRSEM", "", f"Publications trouvées sur les 2 premières pages : {len(urls)}"]
    if not urls:
        _sommaire("\n".join(l + ["Aucune : accès refusé ou structure de page changée."]))
        return 1
    f = fiche(c.get(urls[0]).text, urls[0])
    l.append(f"Première fiche : {json.dumps(f, ensure_ascii=False)}")
    if f.get("pdf"):
        try:
            r = c.get(f["pdf"])
            t = texte_pdf(r.content) if r.status_code == 200 else ""
            l.append(f"PDF : HTTP {r.status_code}, {len(r.content)} octets, {len(t)} caractères de texte extraits.")
        except Exception as e:
            l.append(f"PDF illisible : {type(e).__name__}: {str(e)[:100]}")
    else:
        l.append("Aucun lien PDF trouvé sur la fiche.")
    _sommaire("\n".join(l + ["", "Aucun appel au modèle, rien d'écrit."]))
    return 0


def principal() -> int:
    a_ = argparse.ArgumentParser()
    a_.add_argument("--serie", default="Brève stratégique")
    a_.add_argument("--max", type=int, default=60)
    a_.add_argument("--budget", type=float, default=1.0)
    a_.add_argument("--verifier", action="store_true")
    a = a_.parse_args()
    with httpx.Client(headers=UA, timeout=120, follow_redirects=True) as c:
        if a.verifier:
            return verifier(c)
        urls = lister(c)
        print(f"{len(urls)} publications listées.")
        pubs = []
        for u in urls:
            try:
                pubs.append(fiche(c.get(u).text, u))
            except Exception as e:
                print(f"  fiche illisible : {u} ({type(e).__name__})")
            time.sleep(1)
        print("Séries :", dict(Counter(p.get("serie") for p in pubs)))
        retenues = [p for p in pubs if (p.get("serie") or "").lower() == a.serie.lower() and p.get("pdf")]
        retenues = sorted(retenues, key=lambda p: (p.get("mois") or "", p.get("numero") or 0), reverse=True)[:a.max]
        print(f"{len(retenues)} « {a.serie} » avec PDF envoyées au modèle.")
        DOSSIER.mkdir(parents=True, exist_ok=True)
        PUBLICATIONS.write_text("\n".join(json.dumps(p, ensure_ascii=False) for p in pubs) + "\n", encoding="utf-8")
        if not retenues:
            return 1
        props = asyncio.run(extraire(c, retenues, a.budget))
    PROPOSES.write_text("\n".join(json.dumps(p, ensure_ascii=False) for p in props) + "\n", encoding="utf-8")
    r = resumer(retenues, props)
    RESUME.write_text(r + "\n", encoding="utf-8")
    _sommaire(r)
    return 0


if __name__ == "__main__":
    sys.exit(principal())
