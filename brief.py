"""Briefs standardisés (2026-11-25, demande de l'auteur à 12 h 38).

Chaîne : flux RSS choisis → filtre mécanique (un terme validé de la carte dans le titre) → page lue en mémoire (robots.txt
respecté, jamais écrite) → un modèle de langage remplit une grille fixe en JSON → contrôles par le code → brief Markdown
court (150 à 200 mots) dans briefs/<jour>/, et une ligne au journal briefs/journal.jsonl.

Le code fait le plus possible ; le modèle ne fait que reformuler et extraire :
- les compartiments candidats viennent des listes validées (routage de la carte), le modèle en choisit au plus deux ;
- chaque chiffre rendu par le modèle est cherché dans le texte de la source : retrouvé → « vérifié dans la source »,
  sinon → « chiffre non retrouvé dans la source » ;
- une origine citée autre que le média → « relayé (attribué à …) » ;
- un fait qui recopie 10 mots de suite de la source est retiré (pas de texte d'article conservé) ;
- les domaines de manipulation (domaines_manipulation.txt) sont écartés avant toute lecture.

Relais de modèles (ordre décidé par l'auteur le 2026-11-25) : OpenRouter (crédit jusqu'au 24 mai 2027), Gemini, Mistral,
Cerebras ; un fournisseur sans clé est sauté ; un échec passe au suivant. BRIEF_MODELES (liste séparée par des virgules)
remplace l'ordre par défaut.
    uv run python brief.py [--max 10] [--url https://… ...] [--sec]
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import html
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI / "mise_au_point"))

DOSSIER = ICI / "briefs"
JOURNAL = DOSSIER / "journal.jsonl"
FAMILLES = {"geopolitique_europe": 4, "analyse": 2, "surveillance": 2, "defense": 1, "tech": 1}   # flux de collecte_rss.FLUX
RELAIS = [("openrouter/openai/gpt-oss-120b", "OPENROUTER_API_KEY"),
          ("gemini/gemini-2.5-flash", "GEMINI_API_KEY"),
          ("mistral/mistral-small-latest", "MISTRAL_API_KEY"),
          ("cerebras/gpt-oss-120b", "CEREBRAS_API_KEY")]
TEXTE_MAX = 12_000
MOTS_MAX_CHANGE = 45

CONSIGNE = """Tu rédiges un brief factuel et court en français à partir d'UN document. Règles strictes :
- N'utilise que le document fourni. Aucune connaissance extérieure, aucune supposition présentée comme un fait.
- Reformule toujours avec tes mots ; ne recopie jamais une phrase du document.
- Au plus 3 faits, les plus importants. Chaque fait : une phrase de 25 mots au plus.
- "chiffre" : le nombre exact tel qu'il apparaît dans le document (ex. "9 745", "37 %"), ou "" s'il n'y en a pas.
- "origine" : qui avance ce fait selon le document (une institution, une étude, une personne publique, ou le média lui-même).
- "ce_que_ca_change" : une ou deux phrases, 40 mots au plus, sur la portée du document, sans prédiction, ton neutre,
  sans superlatif ni jugement (pas de « révolutionne », « historique », « majeur ») ; dis ce que le document affirme, pas ce qui est vrai.
- "compartiments" : au plus 2 identifiants choisis UNIQUEMENT dans la liste fournie ; [] si aucun ne convient.
- "limites" : ce que le document ne dit pas ou ne prouve pas (1 ou 2 points courts).
Réponds par un objet JSON seul, sans texte autour :
{"titre": "...", "faits": [{"fait": "...", "chiffre": "...", "origine": "..."}], "ce_que_ca_change": "...",
 "compartiments": ["..."], "limites": ["..."]}"""


# ---------- entrées ----------

def items_flux(xml: bytes) -> list[dict]:
    racine = ET.fromstring(xml)
    ns = lambda t: t.split("}", 1)[-1]
    out = []
    for e in racine.iter():
        if ns(e.tag) not in ("item", "entry"):
            continue
        c = {}
        for f in e:
            t = ns(f.tag)
            if t == "link" and f.get("href"):
                c.setdefault("link", f.get("href"))
            elif f.text:
                c.setdefault(t, f.text.strip())
        lien = c.get("link", "")
        if lien:
            out.append({"url": lien, "titre": html.unescape(re.sub(r"<[^>]+>", " ", c.get("title", ""))).strip(),
                        "resume": html.unescape(re.sub(r"<[^>]+>", " ", c.get("description") or c.get("summary") or "")).strip(),
                        "date": c.get("pubDate") or c.get("published") or c.get("updated") or ""})
    return out


def texte_page(brut: str) -> str:
    t = re.sub(r"(?is)<(script|style|nav|header|footer|aside|form)[^>]*>.*?</\1>", " ", brut)
    t = re.sub(r"(?s)<[^>]+>", " ", t)
    return re.sub(r"\s+", " ", html.unescape(t)).strip()[:TEXTE_MAX]


# ---------- filtre et compartiments (mécanique) ----------

def candidats(texte: str, routage=None) -> list[str]:
    if routage is None:
        import lecture_mecanique as lm
        routage = lm.routage()[0]
    vus = []
    for motif, comps in routage:
        if motif.search(texte):
            for c in sorted(comps):
                if c not in vus:
                    vus.append(c)
    return vus[:25]


def noms_compartiments() -> dict[str, str]:
    import ecosystemes as e
    out = {}
    for theme, fiche in e.charger(ICI / "ecosystemes").items():
        for c in fiche.get("compartiments") or []:
            out[f"{theme}:{c['id']}"] = c.get("nom", "")
    return out


# ---------- modèle (relais) ----------

ESSAIS: list[str] = []   # échecs des fournisseurs précédents pour le dernier appel (écrits au journal)


def appeler(messages: list[dict], relais=None, appel=None) -> tuple[str, str]:
    """Rend (texte, modèle utilisé). appel(model, messages) est injectable pour les tests."""
    if appel is None:
        import litellm

        def appel(m, msgs):
            r = litellm.completion(model=m, messages=msgs, temperature=0.2, max_tokens=1200, timeout=90)
            return r.choices[0].message.content or ""
    ordre = relais or [(m.strip(), None) for m in os.environ.get("BRIEF_MODELES", "").split(",") if m.strip()] or RELAIS
    erreurs = []
    for modele, cle in ordre:
        if cle and not os.environ.get(cle):
            erreurs.append(f"{modele}: clé {cle} absente")
            continue
        try:
            t = appel(modele, messages)
            if extraire_json(t) is not None:
                ESSAIS[:] = erreurs
                return t, modele
            erreurs.append(f"{modele}: réponse non JSON")
        except Exception as ex:                                  # quota, réseau, modèle retiré : on passe au suivant
            erreurs.append(f"{modele}: {type(ex).__name__}: {str(ex)[:120]}")
    raise RuntimeError(" ; ".join(erreurs))


def extraire_json(t: str) -> dict | None:
    t = re.sub(r"(?s)<think>.*?</think>", "", t or "")
    m = re.search(r"(?s)\{.*\}", t)
    if not m:
        return None
    try:
        d = json.loads(m.group(0))
    except ValueError:
        return None
    return d if isinstance(d, dict) and isinstance(d.get("faits", []), list) else None


# ---------- contrôles par le code ----------

def _norm_nombre(s: str) -> str:
    return re.sub(r"[\s  ,.]", "", s)


def chiffre_present(chiffre: str, texte: str) -> bool:
    nums = re.findall(r"\d[\d\s  .,]*\d|\d", chiffre or "")
    if not nums:
        return True
    plat = _norm_nombre(texte)
    return all(_norm_nombre(n) in plat for n in nums)


def recopie(fait: str, texte: str, n: int = 10) -> bool:
    m = re.findall(r"\w+", fait.lower())
    plat = " ".join(re.findall(r"\w+", texte.lower()))
    return any(" ".join(m[i:i + n]) in plat for i in range(0, max(0, len(m) - n + 1)))


def _plat(t: str) -> str:
    import unicodedata
    return re.sub(r"[^a-z0-9]", "", unicodedata.normalize("NFKD", t.lower()).encode("ascii", "ignore").decode())


def _meme_media(origine: str, media: str) -> bool:
    """« Le Grand Continent » = legrandcontinent.eu ; « Atlantic Council » = atlanticcouncil.org ; « le média » aussi."""
    o, m = _plat(origine), _plat(media.split(".")[0])
    return o in ("lemedia", "ledocument", "media", "document", "auteur", "lauteur") or (len(m) >= 4 and (m in o or o.removeprefix("le").removeprefix("la") in m))


def controler(d: dict, texte: str, media: str, permis: list[str], page_lue: bool = True) -> dict:
    faits = []
    for f in (d.get("faits") or [])[:3]:
        fait = str(f.get("fait", "")).strip()
        if not fait or recopie(fait, texte):
            continue
        chiffre, origine = str(f.get("chiffre", "")).strip(), str(f.get("origine", "")).strip()
        if chiffre and not chiffre_present(chiffre, texte):
            statut = "chiffre non retrouvé dans la source"
        elif origine and not _meme_media(origine, media):
            statut = f"relayé (attribué à {origine})"
        else:
            statut = "vérifié dans la source" if page_lue else "affirmé par le média (résumé du flux)"
        faits.append({"fait": fait, "chiffre": chiffre, "origine": origine, "statut": statut})
    change = " ".join(str(d.get("ce_que_ca_change", "")).split()[:MOTS_MAX_CHANGE])
    comps = [c for c in (d.get("compartiments") or []) if c in permis][:2]
    limites = [str(x).strip() for x in (d.get("limites") or []) if str(x).strip()][:2]
    return {"titre": str(d.get("titre", "")).strip(), "faits": faits, "ce_que_ca_change": change,
            "compartiments": comps, "limites": limites}


# ---------- rendu ----------

def rendre(b: dict, url: str, media: str, classe: str, date: str, modele: str, page_lue: bool, noms: dict) -> str:
    l = [f"# {b['titre'] or 'Sans titre'}", "",
         f"Source : {media} ({classe}) · {date} · {url}"]
    if b["compartiments"]:
        l.append("Carte : " + ", ".join(f"{c} ({noms.get(c, '')})" for c in b["compartiments"]))
    l += ["", "## Faits"]
    l += [f"- {f['fait']}" + (f" — {f['chiffre']}" if f["chiffre"] else "") + f" — *{f['statut']}*" for f in b["faits"]] or ["- aucun fait retenu"]
    l += ["", "## Ce que ça change", b["ce_que_ca_change"] or "—", "", "## Limites"]
    l += [f"- {x}" for x in b["limites"]] or ["- non précisées"]
    if not page_lue:
        l.append("- page non lue (robots.txt ou accès refusé) : brief fait sur le résumé du flux seulement")
    l += ["", f"*Brief automatique, modèle {modele} ; chiffres contrôlés par le code, pas de prédiction.*", ""]
    return "\n".join(l)


# ---------- principal ----------

def deja_traites() -> set[str]:
    if not JOURNAL.exists():
        return set()
    return {json.loads(l)["url"] for l in JOURNAL.read_text(encoding="utf-8").splitlines() if l.strip()}


def traiter(item: dict, routage, noms: dict, aujourdhui: str, appel=None, lecteur=None, relais=None) -> dict:
    import sources_preuve as sp
    url, media = item["url"], sp.domaine(item["url"])
    if media in sp.domaines_manipulation():
        return {"url": url, "statut": "domaine_de_manipulation"}
    perm = candidats(item["titre"] + " " + item.get("resume", ""), routage)
    if not perm:
        return {"url": url, "statut": "filtre_aucun_terme"}
    brut = (lecteur or sp.lire_page)(url)
    page_lue = brut is not None
    texte = texte_page(brut) if page_lue else f"{item['titre']}. {item.get('resume', '')}"
    liste = "\n".join(f"- {c} : {noms.get(c, '')}" for c in perm)
    msgs = [{"role": "system", "content": CONSIGNE},
            {"role": "user", "content": f"Média : {media}\nTitre : {item['titre']}\nCompartiments permis :\n{liste}\n\nDocument :\n{texte}"}]
    try:
        rep, modele = appeler(msgs, relais=relais, appel=appel)
    except RuntimeError as ex:
        return {"url": url, "statut": "echec_relais", "erreur": str(ex)[:500]}
    b = controler(extraire_json(rep), texte, media, perm, page_lue)
    md = rendre(b, url, media, sp.classe(url, item["titre"]), aujourdhui, modele, page_lue, noms)
    jour = DOSSIER / aujourdhui
    jour.mkdir(parents=True, exist_ok=True)
    import unicodedata
    base = unicodedata.normalize("NFKD", (b["titre"] or item["titre"]).lower()).encode("ascii", "ignore").decode()
    nom = re.sub(r"[^a-z0-9]+", "-", base)[:60].strip("-") or hashlib.sha1(url.encode()).hexdigest()[:10]
    (jour / f"{nom}.md").write_text(md, encoding="utf-8")
    # le journal garde le brief structuré : la page « briefs » de la carte (lecteur-local, carte/briefs.py) le lit
    return {"url": url, "statut": "ok", "fichier": f"{aujourdhui}/{nom}.md", "modele": modele, "page_lue": page_lue,
            "media": media, "classe": sp.classe(url, item["titre"]), "titre_source": item["titre"],
            "brief": b, "compartiments": b["compartiments"], "mots": len(md.split()), "echecs_relais": list(ESSAIS)}


def principal() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max", type=int, default=10)
    ap.add_argument("--url", nargs="*", default=[])
    ap.add_argument("--sec", action="store_true", help="sans appel au modèle : liste seulement ce qui passerait le filtre")
    a = ap.parse_args()
    import httpx

    import collecte_rss as cr
    import lecture_mecanique as lm
    import politesse
    aujourdhui = dt.datetime.now(dt.timezone.utc).date().isoformat()
    routage, noms, vus = lm.routage()[0], noms_compartiments(), deja_traites()
    items = [{"url": u, "titre": u, "resume": ""} for u in a.url]
    with httpx.Client(headers={"User-Agent": politesse.UA}, follow_redirects=True, timeout=30) as c:
        for fam, n in FAMILLES.items():
            for flux in cr.FLUX.get(fam, []):
                if not politesse.autorise(c, flux):
                    continue
                try:
                    pris = [x for x in items_flux(cr.lire(c, flux).content) if x["url"] not in vus]
                except Exception as ex:
                    print("flux illisible :", flux, type(ex).__name__)
                    continue
                items += [x for x in pris if candidats(x["titre"] + " " + x["resume"], routage)][:n]
    lignes = []
    for it in items[:a.max]:
        if a.sec:
            print("passerait :", it["titre"][:90], "→", candidats(it["titre"] + " " + it["resume"], routage)[:3])
            continue
        r = traiter(it, routage, noms, aujourdhui)
        r["jour"] = aujourdhui
        lignes.append(r)
        print(json.dumps(r, ensure_ascii=False))
    if lignes:
        DOSSIER.mkdir(exist_ok=True)
        with JOURNAL.open("a", encoding="utf-8") as h:
            for r in lignes:
                h.write(json.dumps(r, ensure_ascii=False) + "\n")
        ok = [r for r in lignes if r["statut"] == "ok"]
        idx = DOSSIER / aujourdhui / "index.md"
        if ok:
            idx.parent.mkdir(parents=True, exist_ok=True)
            idx.write_text(f"# Briefs du {aujourdhui}\n\n" + "\n".join(f"- [{Path(r['fichier']).stem}]({Path(r['fichier']).name}) ({r['modele']})" for r in ok) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
