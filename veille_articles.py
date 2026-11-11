"""Veille d'articles, chaque semaine, SANS modèle (décision d'auteur du 2026-11-11).

Deux sources :
  1. arXiv (API publique) : les articles soumis dans les 8 derniers jours, dans les rubriques IA, langage,
     apprentissage, statistiques, économie et réseaux sociaux, qui contiennent au moins une expression [fort] ;
  2. DAIR.AI, « AI Papers of the Week » : la dernière semaine publiée (complément, articles les plus visibles).

Chaque article est noté sur son titre et son résumé : 3 points par expression [fort], 1 par expression [faible]
différente ; 2 si elle est dans le titre ; il est retenu à partir de 3 points. Les mots-clés sont dans veille/mots-cles.txt,
modifiable à la main. Les articles déjà signalés (veille/vus.json) ne reviennent pas.

Sortie : veille/semaine-<date>.md ; dans le workflow, un ticket GitHub assigné à l'auteur (notification par e-mail).
Rien n'entre dans le bot : c'est une liste de lecture, le tri reste humain.

    python veille_articles.py [--jours 8] [--max 20] [--sans-arxiv] [--sans-dair]
"""
from __future__ import annotations

import argparse
import json
import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ICI = Path(__file__).resolve().parent / "veille"
CATEGORIES = ["cs.AI", "cs.CL", "cs.LG", "cs.SI", "cs.CY", "stat.ML", "stat.ME", "stat.AP", "econ.EM", "econ.GN",
              "physics.soc-ph"]
ARXIV = "https://export.arxiv.org/api/query"
DAIR = "https://raw.githubusercontent.com/dair-ai/AI-Papers-of-the-Week/main/years/{annee}.md"
UA = {"User-Agent": "alphabet-bot-veille/1.0 (https://github.com/Othman-Benbrahim/metac-bot-template)"}
NS = {"a": "http://www.w3.org/2005/Atom"}


def lire_mots(f: Path = ICI / "mots-cles.txt") -> dict[str, list[str]]:
    out: dict[str, list[str]] = {"fort": [], "faible": [], "malus": [], "exemption": []}
    section = None
    for ligne in f.read_text(encoding="utf-8").splitlines():
        ligne = ligne.strip()
        if not ligne or ligne.startswith("#"):
            continue
        m = re.fullmatch(r"\[(fort|faible|malus|exemption)\]", ligne)
        if m:
            section = m.group(1)
        elif section:
            out[section].append(ligne)
    return out


def motif(expr: str) -> re.Pattern:
    """« forecast* » : forecast, forecasting… ; les espaces acceptent aussi un tiret ; bornes de mot."""
    etoile = expr.endswith("*")
    e = r"[\s\-]*".join(re.escape(p) for p in re.split(r"[\s\-]+", expr.rstrip("*")) if p)
    return re.compile(rf"(?<![A-Za-z0-9]){e}{'[A-Za-z]*' if etoile else ''}(?![A-Za-z0-9])", re.I)


def noter(texte: str, mots: dict[str, list[str]], titre: str = "") -> tuple[int, list[str], list[str]]:
    """3 points par expression forte ; 1 par faible, 2 si elle est dans le titre (« Forecasting Scientific Progress
    with AI » : le titre dit le sujet mieux que le résumé)."""
    tout = f"{titre} {texte}"
    forts = [m for m in mots["fort"] if motif(m).search(tout)]
    faibles = [m for m in mots["faible"] if motif(m).search(tout)]
    s = 3 * len(forts) + sum(2 if titre and motif(m).search(titre) else 1 for m in faibles)
    malus = [m for m in mots.get("malus", []) if motif(m).search(tout)]
    if malus and not any(motif(m).search(tout) for m in mots.get("exemption", [])):
        s -= 4
        faibles = faibles + [f"malus : {malus[0]}"]
    return s, forts, faibles


def retenu(score: int) -> bool:
    return score >= 3


def _get(url: str, essais: int = 3) -> bytes:
    for i in range(essais):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                return r.read()
        except Exception:
            if i == essais - 1:
                raise
            time.sleep(5 * (i + 1))
    return b""


def requete_arxiv(exprs: list[str], debut: date, fin: date) -> str:
    """Une requête arXiv : (rubriques) AND (expressions, titre ou résumé) AND date de soumission."""
    cats = " OR ".join(f"cat:{c}" for c in CATEGORIES)
    termes = []
    for e in exprs:
        # arXiv racinise les mots mais pas les expressions entre guillemets : une expression de plusieurs mots est
        # cherchée mot à mot (rappel large) ; le tri local, lui, exige l'expression (précision)
        mots_ = re.split(r"[\s\-]+", e.rstrip("*"))
        if len(mots_) == 1 or min(len(m) for m in mots_) < 3:
            t = f'"{e.rstrip("*")}"' if len(mots_) > 1 else mots_[0]
            termes += [f"ti:{t}", f"abs:{t}"]
        else:
            termes += ["(" + " AND ".join(f"{c}:{m}" for m in mots_) + ")" for c in ("ti", "abs")]
    return (f"({cats}) AND ({' OR '.join(termes)}) AND "
            f"submittedDate:[{debut:%Y%m%d}0000 TO {fin:%Y%m%d}2359]")


def parser_atom(xml: bytes) -> list[dict]:
    out = []
    for e in ET.fromstring(xml).findall("a:entry", NS):
        ident = (e.findtext("a:id", "", NS) or "").rsplit("/abs/", 1)[-1]
        ident = re.sub(r"v\d+$", "", ident)
        out.append({"id": f"arxiv:{ident}", "titre": " ".join((e.findtext("a:title", "", NS) or "").split()),
                    "resume": " ".join((e.findtext("a:summary", "", NS) or "").split()),
                    "url": f"https://arxiv.org/abs/{ident}", "date": (e.findtext("a:published", "", NS) or "")[:10],
                    "source": "arXiv"})
    return out


def arxiv(mots: dict[str, list[str]], jours: int) -> list[dict]:
    fin = date.today()
    debut = fin - timedelta(days=jours)
    vus, out = set(), []
    fortes = mots["fort"]
    for i in range(0, len(fortes), 8):         # 8 expressions par requête : des URL raisonnables
        q = requete_arxiv(fortes[i:i + 8], debut, fin)
        url = f"{ARXIV}?{urllib.parse.urlencode({'search_query': q, 'start': 0, 'max_results': 500, 'sortBy': 'submittedDate'})}"
        for a in parser_atom(_get(url)):
            if a["id"] not in vus:
                vus.add(a["id"])
                out.append(a)
        time.sleep(3)                          # règle d'usage de l'API arXiv
    return out


def parser_dair(md: str) -> tuple[str, list[dict]]:
    """La première section « ## Top AI Papers of the Week (…) » : une ligne de tableau par article."""
    m = re.search(r"^## (Top AI Papers of the Week[^\n]*)\n(.*?)(?=^## |\Z)", md, re.M | re.S)
    if not m:
        return "", []
    out = []
    for ligne in m.group(2).splitlines():
        if not re.match(r"\|\s*\d+\)", ligne):
            continue
        cellules = [c.strip() for c in ligne.strip().strip("|").split("|")]
        titre = re.search(r"\*\*(.+?)\*\*", cellules[0])
        liens = re.findall(r"\((https?://[^)\s]+)\)", " ".join(cellules[1:])) or re.findall(r"https?://\S+", cellules[0])
        papier = next((l for l in liens if "arxiv.org" in l), liens[0] if liens else "")
        ax = (re.search(r"arxiv\.org/(?:abs|pdf)/(\d{4}\.\d{4,5})", papier)
              or re.search(r"academy\.dair\.ai/papers/\S*?(\d{4}\.\d{4,5})$", papier))
        resume = re.sub(r"<br>|●", " ", cellules[0])
        out.append({"id": f"arxiv:{ax.group(1)}" if ax else f"dair:{titre.group(1) if titre else ligne[:60]}",
                    "titre": titre.group(1) if titre else ligne[:80], "resume": " ".join(resume.split()),
                    "url": papier, "date": "", "source": "DAIR.AI"})
    return m.group(1), out


def dair() -> tuple[str, list[dict]]:
    return parser_dair(_get(DAIR.format(annee=date.today().year)).decode("utf-8", "replace"))


def trier(articles: list[dict], mots: dict[str, list[str]], deja: set[str], n: int) -> list[dict]:
    garde = {}
    for a in articles:
        if a["id"] in deja:
            continue
        s, forts, faibles = noter(a["resume"], mots, a["titre"])
        if not retenu(s):
            continue
        a = dict(a, score=s, forts=forts, faibles=faibles)
        if a["id"] not in garde or garde[a["id"]]["score"] < s:
            sources = {garde[a["id"]]["source"], a["source"]} if a["id"] in garde else {a["source"]}
            garde[a["id"]] = dict(a, source=" + ".join(sorted(sources)))
    return sorted(garde.values(), key=lambda a: (-a["score"], a["titre"]))[:n]


def rediger(retenus: list[dict], semaine_dair: str, erreurs: list[str], jours: int) -> str:
    l = [f"Articles soumis sur arXiv ces {jours} derniers jours, et dernière semaine de DAIR.AI"
         f"{f' ({semaine_dair})' if semaine_dair else ''}, triés par mots-clés (`veille/mots-cles.txt`), sans modèle. "
         "Transmets à Claude ceux qui méritent une lecture.", ""]
    if erreurs:
        l += [f"> Source indisponible : {e}" for e in erreurs] + [""]
    if not retenus:
        l.append("Rien de retenu cette semaine.")
    for i, a in enumerate(retenus, 1):
        l += [f"**{i}. [{a['titre']}]({a['url']})** — {a['source']}{(' · ' + a['date']) if a['date'] else ''} · score {a['score']}",
              f"Mots : {', '.join(a['forts'] + a['faibles'])}", "",
              f"> {a['resume'][:420]}{'…' if len(a['resume']) > 420 else ''}", ""]
    return "\n".join(l)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--jours", type=int, default=8)
    p.add_argument("--max", type=int, default=20)
    p.add_argument("--sans-arxiv", action="store_true")
    p.add_argument("--sans-dair", action="store_true")
    a = p.parse_args()
    mots = lire_mots()
    f_vus = ICI / "vus.json"
    deja = set(json.loads(f_vus.read_text(encoding="utf-8"))) if f_vus.is_file() else set()
    articles, erreurs, semaine = [], [], ""
    if not a.sans_arxiv:
        try:
            articles += arxiv(mots, a.jours)
        except Exception as e:
            erreurs.append(f"arXiv ({type(e).__name__}: {str(e)[:120]})")
    if not a.sans_dair:
        try:
            semaine, d = dair()
            articles += d
        except Exception as e:
            erreurs.append(f"DAIR.AI ({type(e).__name__}: {str(e)[:120]})")
    retenus = trier(articles, mots, deja, a.max)
    texte = rediger(retenus, semaine, erreurs, a.jours)
    jour = datetime.now(timezone.utc).date().isoformat()
    (ICI / f"semaine-{jour}.md").write_text(texte + "\n", encoding="utf-8")
    f_vus.write_text(json.dumps(sorted(deja | {x["id"] for x in retenus}), ensure_ascii=False, indent=0) + "\n",
                     encoding="utf-8")
    print(f"{len(articles)} articles lus, {len(retenus)} retenus → veille/semaine-{jour}.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
