"""Corroboration et force de la preuve d'un « fait nouveau sourcé » (preenregistrements/dossier-interne.md, § 5 bis ;
décision de l'auteur du 2026-11-24, 22 h 12 : une source isolée est un risque, le fait doit se retrouver plusieurs
fois, et la force de la preuve dépend de la source). Classement par critères objectifs, jamais par le modèle.

Classes : primaire (domaine de l'acteur : gouvernemental ou institutionnel, entreprise nommée, sources des fiches),
agence (liste fermée), autre. Indépendance : domaines enregistrables différents ET pas la même dépêche d'agence (mention
cherchée dans la page, rien n'est gardé du texte) ET URL présente dans la recherche, date passée, page accessible.
"""
from __future__ import annotations

import datetime as dt
import re
import urllib.request
import urllib.robotparser
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse

ICI = Path(__file__).resolve().parent
AGENT = "metac-bot-template (prevision ; respecte robots.txt)"
MARGE = {"forte": 0.10, "moyenne": 0.05, "insuffisante": 0.0}

AGENCES = {"reuters.com": "Reuters", "apnews.com": "AP", "ap.org": "AP", "afp.com": "AFP", "bloomberg.com": "Bloomberg",
           "xinhuanet.com": "Xinhua", "news.cn": "Xinhua", "kyodonews.net": "Kyodo", "ansa.it": "ANSA", "efe.com": "EFE",
           "dpa.com": "dpa", "dpa-international.com": "dpa"}
MENTIONS = {"Reuters": r"\(Reuters\)|\bReuters\b", "AP": r"\(AP\)|Associated Press", "AFP": r"\(AFP\)|\bAFP\b|Agence France-Presse",
            "Bloomberg": r"\bBloomberg\b", "Xinhua": r"\bXinhua\b", "Kyodo": r"\bKyodo\b", "ANSA": r"\bANSA\b",
            "EFE": r"\(EFE\)|\bEFE\b", "dpa": r"\(dpa\)|\bdpa\b"}
INSTITUTIONNEL = re.compile(r"(\.gov|\.gouv\.[a-z]{2}|\.gob\.[a-z]{2}|\.gov\.[a-z]{2}|\.gc\.ca|\.europa\.eu|\.int|"
                            r"\.mil|\.govt\.nz|\.go\.[a-z]{2}|\.admin\.ch|\.bund\.de|\.government\.[a-z]{2})$")
INSTITUTIONS = {"federalreserve.gov", "ecb.europa.eu", "bis.org", "imf.org", "worldbank.org", "un.org", "nato.int",
                "supremecourt.gov", "consilium.europa.eu", "bcp.gov.py", "bankofengland.co.uk", "boj.or.jp", "iaea.org",
                "opec.org", "who.int", "wto.org", "oecd.org", "kremlin.ru", "mid.ru", "elysee.fr", "whitehouse.gov"}
SUFFIXES_DOUBLES = {"co.uk", "gov.uk", "ac.uk", "org.uk", "com.au", "gov.au", "co.jp", "or.jp", "go.jp", "com.br",
                    "gov.br", "gouv.fr", "gob.mx", "gob.ar", "com.ar", "gov.py", "com.py", "co.in", "gov.in", "co.za",
                    "gov.za", "com.cn", "gov.cn", "co.kr", "go.kr", "com.tr", "gov.tr", "com.mx", "co.nz", "govt.nz"}


def domaine(url: str) -> str:
    h = (urlparse(url).hostname or "").lower().removeprefix("www.")
    p = h.split(".")
    if len(p) >= 3 and ".".join(p[-2:]) in SUFFIXES_DOUBLES:
        return ".".join(p[-3:])
    return ".".join(p[-2:]) if len(p) >= 2 else h


@lru_cache(1)
def _domaines_fiches() -> frozenset:
    out = set()
    for f in (ICI / "ecosystemes").glob("*.yaml"):
        for u in re.findall(r"https?://[^\s\"'<>)]+", f.read_text(encoding="utf-8")):
            d = domaine(u)
            if d and d not in AGENCES:
                out.add(d)
    return frozenset(out - {"wikipedia.org", "github.com", "youtube.com"})


def classe(url: str, titre: str = "") -> str:
    h = (urlparse(url).hostname or "").lower()
    d = domaine(url)
    if d in AGENCES:
        return "agence"
    if INSTITUTIONNEL.search(h) or d in INSTITUTIONS or d in _domaines_fiches():
        return "primaire"
    racine = d.split(".")[0]
    if len(racine) >= 4 and re.search(rf"\b{re.escape(racine)}\b", titre or "", re.I):
        return "primaire"                              # domaine de l'entreprise ou de l'acteur nommé dans la question
    return "autre"


def lire_page(url: str, timeout: float = 15) -> str | None:
    """Texte de la page en mémoire (jamais écrit), si robots.txt le permet ; None sinon."""
    try:
        u = urlparse(url)
        rp = urllib.robotparser.RobotFileParser(f"{u.scheme}://{u.netloc}/robots.txt")
        rp.read()
        if not rp.can_fetch(AGENT, url):
            return None
        r = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": AGENT}), timeout=timeout)
        return r.read(2_000_000).decode("utf-8", "replace")
    except Exception:
        return None


def agence_creditee(texte: str, d: str) -> str | None:
    if d in AGENCES:
        return AGENCES[d]
    tete = (texte or "")[:200_000]
    for nom, m in MENTIONS.items():
        if re.search(m, tete):
            return nom
    return None


def force(preuves: list[dict], recherche: str, titre: str, aujourdhui: dt.date, lecteur=lire_page) -> dict:
    """preuves : [{"url", "date"}]. Rend la force, la marge admise et le détail de chaque source (scellé au journal)."""
    retenues, detail, vus_dom, vus_dep = [], [], set(), set()
    for p in preuves or []:
        url, ds = str(p.get("url") or ""), str(p.get("date") or "")
        x = {"url": url, "date": ds, "domaine": domaine(url), "classe": classe(url, titre)}
        try:
            d = dt.date.fromisoformat(ds[:10])
        except ValueError:
            d = None
        if not url or url not in (recherche or ""):
            x["rejet"] = "absente_de_la_recherche"
        elif d is None or d > aujourdhui:
            x["rejet"] = "date_absente_ou_future"
        elif x["domaine"] in vus_dom:
            x["rejet"] = "meme_domaine"
        else:
            t = lecteur(url)
            if t is None:
                x["rejet"] = "page_inaccessible"
            else:
                ag = agence_creditee(t, x["domaine"])
                x["agence_creditee"] = ag
                if ag and ag in vus_dep:
                    x["rejet"] = "meme_depeche"
                else:
                    vus_dom.add(x["domaine"])
                    if ag:
                        vus_dep.add(ag)
                    if ag and x["classe"] == "autre":
                        x["classe"] = "agence"               # reprise d'une dépêche : compte comme l'agence
                    retenues.append(x)
        detail.append(x)
    n = len(retenues)
    prim = sum(x["classe"] == "primaire" for x in retenues)
    agc = sum(x["classe"] == "agence" for x in retenues)
    if (prim >= 1 and n >= 2) or (n >= 3 and agc >= 2):
        f = "forte"
    elif n >= 2 and (agc >= 1 or prim >= 1):
        f = "moyenne"
    else:
        f = "insuffisante"
    return {"force": f, "marge": MARGE[f], "independantes": n, "primaires": prim, "agences": agc, "sources": detail}
