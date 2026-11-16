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

0.10.203 (décision d'auteur du 2026-11-16, 19 h 14) : deux sources, IRSEM et Le Rubicon (revue francophone d'analyse
stratégique, Paris et Montréal, CC BY-NC-ND 4.0), et un CRITÈRE EXTÉRIEUR à la place de la portée déclarée par le
modèle, trop généreuse au pilote IRSEM (18 « candidats » sur 90, dont des truismes) : un mécanisme n'est candidat que
si (1) le modèle rattache son indicateur à l'une de nos sources de données (liste fermée REGISTRES), (2) le texte de
l'indicateur contient bien les mots de cette source (vérification par expression régulière, sans modèle), et (3) un
délai est énoncé. La portée déclarée reste notée, à titre d'information.

Registres : registre/mecanismes/{source}-publications.jsonl ; {source}-proposes.jsonl ; {source}-resume.md.
Usage : python mecanismes_irsem.py [--source irsem|rubicon] --verifier | [--serie "Brève stratégique"] [--max 60] [--budget 1]
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
RUBICON = "https://lerubicon.org"
RUBICON_LISTE = RUBICON + "/publications/"


def chemins(source: str) -> tuple[Path, Path, Path]:
    return (DOSSIER / f"{source}-publications.jsonl", DOSSIER / f"{source}-proposes.jsonl", DOSSIER / f"{source}-resume.md")


# 0.10.203 : nos sources de données (liste fermée) et les mots qui doivent figurer dans l'indicateur pour s'y rattacher
REGISTRES = {
    "manifestations": ("manifestations, émeutes, troubles (GDELT, ACLED)",
                       r"manifest|émeute|emeute|protest|troubles|mobilisation|grève|greve|rassemblement|révolte|revolte"),
    "violence": ("combats, attaques, frappes, violences armées (ACLED, GDELT)",
                 r"combat|attaque|frappe|violence|affrontement|offensive|bombard|attentat|incursion|escarmouche"),
    "sanctions": ("sanctions et désignations (OFAC, Royaume-Uni)", r"sanction|embargo|désignation|designation|gel des avoirs"),
    "elections": ("calendrier électoral (Wikidata)", r"élection|election|scrutin|vote|référendum|referendum|campagne électorale"),
    "coupures": ("coupures d'internet, censure (Cloudflare Radar, OONI)",
                 r"coupure|internet|censure|blocage|réseau|reseau|messagerie|télécommunication|telecommunication"),
    "maritime": ("passages de navires dans les détroits (IMF PortWatch)",
                 r"détroit|detroit|navire|maritime|transit|\bports?\b|fret|pétrolier|petrolier|convoi"),
    "avions_etat": ("vols d'avions d'État (OpenSky)", r"avion|vol |vols|aéronef|aeronef|visite officielle|déplacement présidentiel"),
    "recit": ("volume et ton des médias, récits d'État (GDELT, flux RSS)",
              r"récit|recit|narratif|propagande|média|media|presse|désinformation|desinformation|rhétorique|rhetorique|discours"),
    "calendrier": ("dates fixes connues d'avance (commémorations, échéances, saisons)",
                   r"commémor|commemor|anniversaire|échéance|echeance|saison|calendrier|date (fixe|connue|prévue|prevue)|sommet|remplissage"),
    "risques_humanitaires": ("risques humanitaires des analystes (ACAPS, INFORM)",
                             r"humanitaire|famine|déplacé|deplace|réfugié|refugie|crise alimentaire|insécurité alimentaire"),
    "prix": ("prix alimentaires et de l'énergie", r"prix|inflation|carburant|pénurie|penurie|blé|ble|énergie|energie"),
    "economie": ("indicateurs économiques, notations souveraines, nowcasts", r"notation|dette|pib|croissance|monnaie|devise|défaut|defaut|réserves"),
    "aucun": ("aucune de nos sources", r"$^"),
}
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


CONSIGNE = """Tu lis une analyse stratégique ({editeur}). Relève au plus
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
"registre": "UN mot parmi : {registres} : la source de données qui permet d'observer l'indicateur, ou aucun",
"region": "région concernée", "pays": ["codes ISO à deux lettres"], "domaine": "conflit | attaque | coup d'État |
crise politique | élection | sanctions | diplomatie | maritime ou commerce | coupure | influence | manifestations |
autre", "citation": "les mots du texte qui l'énoncent (15 mots au plus)"}}]}}"""


_MOIS = {"janvier": 1, "février": 2, "fevrier": 2, "mars": 3, "avril": 4, "mai": 5, "juin": 6, "juillet": 7, "août": 8,
         "aout": 8, "septembre": 9, "octobre": 10, "novembre": 11, "décembre": 12, "decembre": 12}
_DATE_FR = re.compile(r"\b(\d{1,2})(?:er)?\s+(" + "|".join(_MOIS) + r")\s+(20\d{2})\b", re.I)
_PDF_RUBICON = re.compile(r'href="(https?://lerubicon\.org/[a-z0-9-]+/)fulltext\.pdf"', re.I)


def liens_rubicon(page_html: str) -> list[str]:
    """Articles du Rubicon qui ont un PDF (« …/fulltext.pdf »), dans l'ordre de la page."""
    out = []
    for u in _PDF_RUBICON.findall(page_html):
        if u not in out:
            out.append(u)
    return out


def lister_rubicon(c: httpx.Client, pages_max: int = 10) -> list[str]:
    out: list[str] = []
    for n in range(1, pages_max + 1):
        r = c.get(RUBICON_LISTE, params={"sf_paged": n} if n > 1 else None)
        if r.status_code != 200:
            print(f"  page {n} : HTTP {r.status_code}")
            break
        nouveaux = [u for u in liens_rubicon(r.text) if u not in out]
        if not nouveaux:
            break
        out += nouveaux
        time.sleep(1)
    return out


def fiche_rubicon(page_html: str, url: str) -> dict:
    titre = _TITRE.search(page_html)
    t = html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", page_html)))
    d = _DATE_FR.search(t)
    return {"url": url, "serie": "Le Rubicon", "numero": None,
            "mois": f"{d.group(3)}-{_MOIS[d.group(2).lower()]:02d}" if d else None,
            "titre": html.unescape(re.sub(r"<[^>]+>|\s+", " ", titre.group(1))).strip() if titre else None,
            "pdf": url + "fulltext.pdf"}


EDITEURS = {"irsem": "IRSEM, institut de recherche stratégique du ministère des Armées",
            "rubicon": "Le Rubicon, revue francophone d'analyse stratégique"}


async def extraire(c: httpx.Client, pubs: list[dict], budget: float, source: str = "irsem") -> list[dict]:
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
                    CONSIGNE.format(editeur=EDITEURS[source], registres=" | ".join(REGISTRES),
                                    titre=p.get("titre") or "?", serie=p.get("serie") or "", numero=p.get("numero") or "",
                                    mois=p.get("mois") or "", texte=gi.bloc(texte, 12000, origine=f"publication {source}"))))
                for m in (rep.get("mecanismes") or [])[:2]:
                    if isinstance(m, dict) and m.get("mecanisme"):
                        out.append({**{k: m.get(k) for k in ("mecanisme", "indicateur", "delai", "sens", "portee", "registre",
                                                             "region", "pays", "domaine", "citation")},
                                    "source": {k: p.get(k) for k in ("serie", "numero", "mois", "titre", "url")},
                                    "origine": "modèle", "modele": MODELE, "statut": "proposé"})
            except Exception as e:
                print(f"  {str(p.get('titre'))[:50]} : {type(e).__name__}: {str(e)[:80]}")
            cumul += float(cm.current_usage or 0)
        time.sleep(1)
    print(f"Extraction : {len(out)} mécanismes proposés, coût {cumul:.2f} $.")
    return out


def rattache(p: dict) -> str | None:
    """0.10.203 : la source de données à laquelle l'indicateur se rattache, si le modèle l'a nommée ET si le texte de
    l'indicateur en contient les mots (vérification sans modèle) ; sinon None."""
    r = str(p.get("registre") or "").strip().lower()
    if r not in REGISTRES or r == "aucun":
        return None
    return r if re.search(REGISTRES[r][1], str(p.get("indicateur") or ""), re.I) else None


def candidats(props: list[dict]) -> list[dict]:
    """Règle d'arrêt : indicateur rattaché à l'une de nos sources (vérifié) et délai énoncé. La portée déclarée par le
    modèle n'entre plus dans la règle (0.10.203)."""
    return [p for p in props if rattache(p) and p.get("delai") not in (None, "", "null", "None")]


def resumer(pubs: list[dict], props: list[dict], source: str = "irsem") -> str:
    cand = candidats(props)
    nom = {"irsem": "l'IRSEM", "rubicon": "Le Rubicon"}.get(source, source)
    l = [f"# Mécanismes proposés à partir de {nom} (pilote du {time.strftime('%Y-%m-%d')})", "",
         f"{len(pubs)} publications lues ; {len(props)} mécanismes proposés ; {len(cand)} passent la règle d'arrêt "
         f"(indicateur rattaché à l'une de nos sources, vérifié par les mots de l'indicateur, et délai énoncé). "
         f"Règle : moins de 3 → on arrête là. Rien n'est inscrit au catalogue sans décision d'auteur.", "",
         "## Par source de données rattachée", ""]
    l += [f"- {k} : {v}" for k, v in Counter((rattache(p) or "non rattaché") for p in props).most_common()]
    l += ["", f"## Candidats ({len(cand)})", ""]
    for p in cand:
        s = p["source"]
        l.append(f"- **{p['mecanisme']}** — indicateur : {p.get('indicateur')} ; source : {rattache(p)} ; délai : "
                 f"{p.get('delai')} ; portée déclarée : {p.get('portee')} ; {p.get('region')} ; "
                 f"[{s.get('serie')} {s.get('numero') or ''}, {s.get('mois')}]({s.get('url')})")
    l += ["", "## Autres", ""]
    for p in [p for p in props if p not in cand]:
        s = p["source"]
        l.append(f"- {p['mecanisme']} — source déclarée : {p.get('registre')} ; délai : {p.get('delai')} ; "
                 f"[{s.get('serie')} {s.get('numero') or ''}]({s.get('url')})")
    return "\n".join(l)


def _sommaire(texte: str) -> None:
    print(texte)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
            f.write(texte + "\n")


def verifier(c: httpx.Client, source: str = "irsem") -> int:
    """Accès au site, sans modèle ni écriture : liste, une fiche, un PDF."""
    urls = lister(c, pages_max=2) if source == "irsem" else lister_rubicon(c, pages_max=1)
    l = [f"## Vérification de l'accès ({source})", "", f"Publications trouvées : {len(urls)}"]
    if not urls:
        _sommaire("\n".join(l + ["Aucune : accès refusé ou structure de page changée."]))
        return 1
    page = c.get(urls[0]).text
    f = fiche(page, urls[0]) if source == "irsem" else fiche_rubicon(page, urls[0])
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
    a_.add_argument("--source", choices=("irsem", "rubicon"), default="irsem")
    a_.add_argument("--serie", default="Brève stratégique", help="IRSEM seulement")
    a_.add_argument("--max", type=int, default=60)
    a_.add_argument("--budget", type=float, default=1.0)
    a_.add_argument("--verifier", action="store_true")
    a = a_.parse_args()
    publications, proposes, resume = chemins(a.source)
    with httpx.Client(headers=UA, timeout=120, follow_redirects=True) as c:
        if a.verifier:
            return verifier(c, a.source)
        urls = lister(c) if a.source == "irsem" else lister_rubicon(c)
        print(f"{len(urls)} publications listées.")
        pubs = []
        for u in urls:
            try:
                page = c.get(u).text
                pubs.append(fiche(page, u) if a.source == "irsem" else fiche_rubicon(page, u))
            except Exception as e:
                print(f"  fiche illisible : {u} ({type(e).__name__})")
            time.sleep(1)
            if a.source == "rubicon" and len(pubs) >= a.max:
                break                     # liste du plus récent au plus ancien : inutile de tout lire
        print("Séries :", dict(Counter(p.get("serie") for p in pubs)))
        if a.source == "irsem":
            retenues = [p for p in pubs if (p.get("serie") or "").lower() == a.serie.lower() and p.get("pdf")]
        else:
            retenues = [p for p in pubs if p.get("pdf")]
        retenues = sorted(retenues, key=lambda p: (p.get("mois") or "", p.get("numero") or 0), reverse=True)[:a.max]
        print(f"{len(retenues)} publications avec PDF envoyées au modèle.")
        DOSSIER.mkdir(parents=True, exist_ok=True)
        publications.write_text("\n".join(json.dumps(p, ensure_ascii=False) for p in pubs) + "\n", encoding="utf-8")
        if not retenues:
            return 1
        props = asyncio.run(extraire(c, retenues, a.budget, a.source))
    proposes.write_text("\n".join(json.dumps(p, ensure_ascii=False) for p in props) + "\n", encoding="utf-8")
    r = resumer(retenues, props, a.source)
    resume.write_text(r + "\n", encoding="utf-8")
    _sommaire(r)
    return 0


if __name__ == "__main__":
    sys.exit(principal())
