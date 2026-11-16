"""Récolte des questions Metaculus RÉSOLUES et classement par le code, sans modèle de langue (bot 0.10.166).

Décision d'auteur du 2026-11-16 (10 h 49) : préparer un taux de base « B Metaculus » par classe de questions. Récupérer
les questions est gratuit (API Metaculus) ; le classement se fait d'abord par des règles fixées d'avance (ce fichier),
le modèle ne lira ensuite que les questions que le code n'aura pas su classer.

Ce qu'on garde (registre/metaculus-resolues.jsonl), une ligne par question binaire résolue oui/non :
  identifiants, titre, dates (ouverture, fermeture prévue, résolution), issue (1/0), catégories et étiquettes de
  Metaculus, pays cités (noms CLDR anglais/français du collecteur RSS), domaine et forme (règles ci-dessous), seuils
  numériques du titre, durée d'ouverture, dernière prévision agrégée de la communauté si l'API la donne.
On ne garde PAS les descriptions ni les critères de résolution (texte de Metaculus, dépôt public).

Règles de classement (fixées le 2026-11-16, avant toute lecture des issues) :
  domaine : premier domaine dont un mot-clé apparaît dans le titre ou les catégories (ordre de DOMAINES) ;
  forme   : premier motif de FORMES qui correspond au titre ;
  « non classée » : domaine OU forme introuvable ; ces questions seront seules confiées au modèle.

Usage : python recolte_metaculus.py [--max 20000]   (variable METACULUS_TOKEN)
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from collections import Counter
from pathlib import Path

import httpx

API = "https://www.metaculus.com/api/posts/"
SORTIE = Path("registre") / "metaculus-resolues.jsonl"
RESUME = Path("registre") / "metaculus-resolues-resume.md"

DOMAINES = [
    ("elections", r"\b(election|elected|vote|voting|referendum|ballot|primary|presiden(t|cy|tial)|prime minister|"
                  r"parliament|senate|congress|seats?|coalition|chancellor|impeach|mayor|governor)\b"),
    ("conflits", r"\b(war|ceasefire|cease-fire|invasion|invade|attack|strike|missile|troops|military|killed|fatalities|"
                 r"conflict|terror|nuclear test|drone|annex|occupation|nato|hamas|hezbollah|houthi)\b"),
    ("sante", r"\b(pandemic|epidemic|outbreak|virus|covid|h5n1|influenza|mpox|measles|ebola|cholera|vaccine|who |"
              r"pheic|cases|deaths from|disease)\b"),
    ("ia_tech", r"\b(ai|artificial intelligence|gpt|llm|openai|anthropic|deepmind|model|benchmark|agi|chip|"
                r"semiconductor|quantum|spacex|starship|launch|satellite|robot)\b"),
    ("economie", r"\b(gdp|inflation|cpi|unemployment|interest rate|fed|federal reserve|ecb|recession|stock|s&p|"
                 r"nasdaq|dow|bitcoin|ethereum|crypto|price|oil|brent|gold|dollar|euro|yuan|tariff|debt|default|"
                 r"rating|bond|yield|market cap|ipo|bankrupt)\b"),
    ("climat", r"\b(temperature|climate|hurricane|earthquake|wildfire|flood|drought|sea ice|co2|emissions|el ni[nñ]o|"
               r"heat ?wave|record high)\b"),
    ("justice_politique", r"\b(court|supreme court|indict|convict|sentenc|trial|lawsuit|ruling|law|bill|act|"
                          r"executive order|ban|sanction|resign|arrest|pardon)\b"),
    ("sport_culture", r"\b(world cup|olympic|championship|super bowl|nba|nfl|fifa|uefa|oscar|grammy|eurovision|"
                      r"box office|nobel)\b"),
]
FORMES = [
    ("seuil_depasse", r"\b(more than|at least|exceed|above|over|greater than|higher than|surpass|reach|below|"
                      r"less than|under|fewer than|lower than)\b"),
    ("evenement_avant", r"\b(before|by (the end of )?(january|february|march|april|may|june|july|august|september|"
                        r"october|november|december|\d{4}|q[1-4]|end of)|prior to)\b"),
    ("vainqueur", r"\b(win|won|winner|be elected|become|remain|still be|be re-?elected|lead)\b"),
    ("occurrence", r"^\s*(will|is|does|do|has|have|are|can|would|shall)\b"),
]
NOMBRE = re.compile(r"(?<![\w.])(\d{1,3}(?:[,\s]\d{3})+|\d+(?:\.\d+)?)\s*(%|percent|k\b|m\b|million|billion|bn|trillion)?",
                    re.I)


def domaine(texte: str) -> str | None:
    t = texte.lower()
    for nom, motif in DOMAINES:
        if re.search(motif, t):
            return nom
    return None


def forme(titre: str) -> str | None:
    t = titre.lower()
    for nom, motif in FORMES:
        if re.search(motif, t):
            return nom
    return None


MOIS = r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?"
DATE_TEXTE = re.compile(rf"\b{MOIS}\s+\d{{1,2}}(?:st|nd|rd|th)?\b|\b\d{{1,2}}(?:st|nd|rd|th)?\s+{MOIS}|\bq[1-4]\b", re.I)


def seuils(titre: str) -> list[str]:
    out = []
    for m in NOMBRE.finditer(DATE_TEXTE.sub(" ", titre)):
        n = m.group(1)
        if re.fullmatch(r"(19|20)\d{2}", n) and not m.group(2):  # une année n'est pas un seuil
            continue
        out.append((n + (m.group(2) or "")).strip())
    return out[:4]


def _date(x) -> str | None:
    return str(x)[:10] if x else None


def _noms(projets: dict, cle: str) -> list[str]:
    v = (projets or {}).get(cle) or []
    return [str(p.get("name") or p.get("slug") or "") for p in v if isinstance(p, dict)]


def _derniere_prevision(q: dict):
    ag = (q.get("aggregations") or {})
    for cle in ("recency_weighted", "unweighted", "metaculus_prediction"):
        lat = ((ag.get(cle) or {}).get("latest") or {})
        c = lat.get("centers")
        if isinstance(c, list) and c and isinstance(c[0], (int, float)):
            return round(float(c[0]), 4)
    return None


def ligne(post: dict, motifs_pays) -> dict | None:
    q = post.get("question")
    if not isinstance(q, dict):
        REJETS["sans question (groupe, conditionnelle)"] += 1
        return None
    if q.get("type") != "binary":
        REJETS[f"type {q.get('type')}"] += 1
        return None
    r = str(q.get("resolution") or "").lower()
    if r not in ("yes", "no"):
        REJETS[f"résolution {r or 'vide'}"] += 1
        return None
    titre = post.get("title") or q.get("title") or ""
    cats, tags = _noms(post.get("projects"), "category"), _noms(post.get("projects"), "tag")
    texte = " ".join([titre] + cats + tags)
    pays = sorted({code for motif, code in motifs_pays if motif.search(titre)})
    d, f = domaine(texte), forme(titre)
    ouv, ferm = _date(q.get("open_time") or post.get("open_time")), _date(q.get("scheduled_close_time"))
    res = _date(q.get("actual_resolve_time") or q.get("scheduled_resolve_time"))
    duree = None
    if ouv and ferm:
        from datetime import date
        try:
            duree = (date.fromisoformat(ferm) - date.fromisoformat(ouv)).days
        except ValueError:
            pass
    return {"post_id": post.get("id"), "question_id": q.get("id"), "titre": titre, "issue": 1 if r == "yes" else 0,
            "ouverture": ouv, "fermeture_prevue": ferm, "resolution": res, "duree_jours": duree,
            "categories": cats, "etiquettes": tags[:12], "pays": pays, "domaine": d, "forme": f,
            "seuils": seuils(titre), "communaute_finale": _derniere_prevision(q),
            "classee": bool(d and f)}


REJETS: Counter = Counter()


def diagnostic(post: dict) -> str:
    """Forme d'un post (clés et types), sans texte : pour comprendre un passage qui ne garde rien."""
    q = post.get("question")
    if not isinstance(q, dict):
        return f"post sans « question » ; clés : {sorted(post.keys())[:25]}"
    return (f"clés du post : {sorted(post.keys())[:25]} ; question.type={q.get('type')!r} ; "
            f"question.resolution={q.get('resolution')!r} ; question.status={q.get('status')!r}")


# 0.10.172 : la première combinaison de paramètres a rendu 0 post ; on essaie plusieurs variantes sur la première page
# et on garde la première qui rend des posts (le filtrage oui/non se fait de toute façon localement, dans `ligne`).
VARIANTES = [
    {"statuses": "resolved", "forecast_type": "binary", "order_by": "-scheduled_resolve_time"},
    {"statuses": "resolved", "forecast_type": "binary"},
    {"statuses": "resolved"},
    {"status": "resolved", "forecast_type": "binary"},
    {"forecast_type": "binary", "order_by": "-scheduled_resolve_time"},
    {"forecast_type": "binary"},
    {},
]


def _page(c: httpx.Client, params: dict) -> tuple[list, dict]:
    for essai in range(6):
        r = c.get(API, params=params)
        if r.status_code == 429 or r.status_code >= 500:
            time.sleep(min(60, 5 * 2 ** essai))
            continue
        break
    if r.status_code >= 400:
        print(f"  API Metaculus : HTTP {r.status_code} ({params}) : {r.text[:300]}")
    r.raise_for_status()
    corps = r.json()
    return corps.get("results") or [], corps


def choisir_variante(c: httpx.Client) -> dict | None:
    for v in VARIANTES:
        res, corps = _page(c, {**v, "limit": 20, "offset": 0, "with_cp": "true"})
        print(f"  variante {v} : {len(res)} posts ; clés {sorted(corps.keys())}")
        if res:
            print("  " + diagnostic(res[0]))
            return v
        time.sleep(1.0)
    return None


def recolter(c: httpx.Client, maximum: int):
    v = choisir_variante(c)
    if v is None:
        return
    offset, n = 0, 0
    while n < maximum:
        res, _ = _page(c, {**v, "limit": 100, "offset": offset, "with_cp": "true"})
        if not res:
            return
        for p in res:
            yield p
        n += len(res)
        offset += len(res)
        if offset % 2000 == 0:
            print(f"  {offset} posts lus")
        time.sleep(1.0)


def resumer(lignes: list[dict]) -> str:
    n = len(lignes)
    if not n:
        return "Aucune question récoltée."
    cl = [x for x in lignes if x["classee"]]
    dom, fo = Counter(x["domaine"] or "—" for x in lignes), Counter(x["forme"] or "—" for x in lignes)
    out = [f"# Questions Metaculus résolues (binaires) : {n}", "",
           f"- classées par le code : {len(cl)} ({len(cl) / n:.0%}) ; non classées : {n - len(cl)}",
           f"- avec au moins un pays reconnu : {sum(1 for x in lignes if x['pays'])}",
           f"- part des « oui » : {sum(x['issue'] for x in lignes) / n:.3f}", "", "## Domaines", "",
           "| domaine | questions |", "|---|---|"]
    out += [f"| {k} | {v} |" for k, v in dom.most_common()]
    out += ["", "## Formes", "", "| forme | questions |", "|---|---|"]
    out += [f"| {k} | {v} |" for k, v in fo.most_common()]
    out += ["", "Les taux de « oui » par classe ne sont PAS affichés ici : ils seront calculés dans le pré-enregistrement"
            " du B Metaculus, après le classement des questions restantes."]
    return "\n".join(out)


DEJA_VUS = Path("registre") / "metaculus-posts-vus.txt"   # 0.10.174 : posts déjà traités (y compris écartés)


def detail(c: httpx.Client, post_id) -> dict | None:
    """0.10.174 : la liste des posts ne donne pas la résolution (question.resolution = None) ; la page d'un post la
    donne. Une requête par question, d'où la reprise d'un passage à l'autre."""
    for essai in range(6):
        try:
            r = c.get(f"{API}{post_id}/")
        except httpx.HTTPError:
            time.sleep(5 * 2 ** essai)
            continue
        if r.status_code == 429 or r.status_code >= 500:
            time.sleep(min(120, 5 * 2 ** essai))
            continue
        if r.status_code >= 400:
            REJETS[f"détail HTTP {r.status_code}"] += 1
            return None
        return r.json()
    REJETS["détail : trop d'échecs"] += 1
    return None


def _cles_resolution(d, prefixe="", out=None, profondeur=0):
    """Chemins et valeurs des clés qui ressemblent à une résolution (diagnostic 0.10.192)."""
    out = [] if out is None else out
    if profondeur > 4:
        return out
    if isinstance(d, dict):
        for k, v in d.items():
            ch = f"{prefixe}.{k}" if prefixe else k
            if any(m in k.lower() for m in ("resol", "outcome", "status", "actual", "result")) and not isinstance(v, (dict, list)):
                out.append(f"{ch}={v!r}"[:120])
            _cles_resolution(v, ch, out, profondeur + 1)
    elif isinstance(d, list) and d:
        _cles_resolution(d[0], prefixe + "[0]", out, profondeur + 1)
    return out


def diagnostiquer(c: httpx.Client, n: int = 3) -> int:
    """0.10.192 : la page d'un post ne donnait pas non plus de résolution ; on affiche, pour quelques posts résolus,
    toutes les clés qui ressemblent à une résolution (liste et détail), sans rien écrire."""
    vus = 0
    for p in recolter(c, 100):
        if vus >= n:
            break
        print(f"--- post {p.get('id')} : {str(p.get('title'))[:80]}")
        print("  liste  : " + " ; ".join(_cles_resolution(p)))
        d = detail(c, p.get("id"))
        print("  détail : " + " ; ".join(_cles_resolution(d or {})))
        q = (d or {}).get("question") or {}
        print(f"  clés de question (détail) : {sorted(q.keys())}")
        vus += 1
        time.sleep(1)
    return 0


def principal() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max", type=int, default=20000)
    ap.add_argument("--minutes", type=float, default=200, help="durée maximale des requêtes de détail")
    ap.add_argument("--diagnostic", action="store_true", help="afficher où se trouve la résolution, sans rien écrire")
    a = ap.parse_args()
    jeton = os.environ.get("METACULUS_TOKEN", "")
    entetes = {"User-Agent": "alphabet-situationnel-bot/1.0 (recherche)"}
    if jeton:
        entetes["Authorization"] = f"Token {jeton}"
    from collecte_rss import noms_pays
    # 0.10.171 : client distinct pour les noms de pays (le jeton Metaculus envoyé à un autre site faisait échouer
    # le téléchargement : 9 noms au lieu de 475)
    with httpx.Client(headers={"User-Agent": entetes["User-Agent"]}, timeout=60, follow_redirects=True) as cp:
        motifs = noms_pays(cp)
    print(f"{len(motifs)} noms de pays.")
    lignes = [json.loads(l) for l in SORTIE.read_text(encoding="utf-8").splitlines() if l.strip()] if SORTIE.exists() else []
    vus = set(DEJA_VUS.read_text(encoding="utf-8").split()) if DEJA_VUS.exists() else set()
    print(f"Reprise : {len(lignes)} questions déjà gardées, {len(vus)} posts déjà traités.")
    SORTIE.parent.mkdir(exist_ok=True)
    fin = time.time() + 60 * a.minutes
    nouveaux = 0
    if a.diagnostic:
        with httpx.Client(headers=entetes, timeout=60, follow_redirects=True) as c:
            return diagnostiquer(c)
    with httpx.Client(headers=entetes, timeout=60, follow_redirects=True) as c:
        a_lire = [p for p in recolter(c, a.max) if str(p.get("id")) not in vus]
        print(f"{len(a_lire)} posts résolus à lire en détail.")
        with SORTIE.open("a", encoding="utf-8") as f, DEJA_VUS.open("a", encoding="utf-8") as fv:
            for p in a_lire:
                if time.time() > fin:
                    print("Durée maximale atteinte : la suite au prochain passage (reprise automatique).")
                    break
                q = p.get("question") or {}
                if q.get("resolution") is None:
                    d = detail(c, p.get("id"))
                    time.sleep(0.7)
                    if d is None:
                        continue                      # non marqué comme vu : retenté au prochain passage
                    p = d
                avant_rejets = REJETS["résolution vide"]
                x = ligne(p, motifs)
                if REJETS["résolution vide"] > avant_rejets:
                    continue                          # 0.10.192 : jamais marqué « vu » sans résolution lue
                fv.write(f"{p.get('id')}\n")
                if x:
                    f.write(json.dumps(x, ensure_ascii=False) + "\n")
                    lignes.append(x)
                    nouveaux += 1
                    if nouveaux % 250 == 0:
                        f.flush()
                        fv.flush()
                        print(f"  {nouveaux} nouvelles questions gardées")
    if REJETS:
        print("Posts écartés : " + " ; ".join(f"{k} : {v}" for k, v in REJETS.most_common()))
    if not lignes:
        print("Aucune question gardée.")
        return 1
    r = resumer(lignes)
    RESUME.write_text(r + "\n", encoding="utf-8")
    print(r)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
            f.write(r + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
