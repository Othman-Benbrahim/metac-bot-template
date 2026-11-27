"""Lecteur des sites sans flux RSS (2026-11-27, décision de l'auteur, 20 h 15 : « Pas besoin de RSS bridge, on fait ça
pour tous les liens sans flux »).

Même règle que la collecte : robots.txt respecté, et seuls le lien et le titre du lien sont gardés, jamais le texte de la
page. Pour chaque site, un motif d'adresse choisit les liens qui sont des articles (fixé après la sonde, jamais deviné).

- `sonde(html, base)` : regroupe les liens d'une page par gabarit d'adresse (chiffres → N), pour choisir le motif ;
- `lire(html, base, motif)` : liens du même site dont le chemin suit le motif, sans doublon, avec leur titre.
"""
from __future__ import annotations

import collections
import html as html_mod
import re
from urllib.parse import urljoin, urlparse

# nom → page lue et motif du chemin des articles (None tant que la sonde n'a pas été lue)
SITES: dict[str, dict] = {
    # sonde du 2026-11-27 (run 46055564179) : 36 liens /elections/id/N, titrés par le seul type (« Referendum ») ; le
    # pays est un autre lien de la même ligne du tableau, d'où « ligne » : le titre réunit les liens de la ligne.
    "ElectionGuide": {"url": "https://www.electionguide.org/elections/type/upcoming/",
                      "motif": r"^/elections/id/\d+/?$", "ligne": True,
                      "valide": True},
    # 2026-11-27, 20 h 48 : laboratoires d'IA sans flux connu ; sonde d'abord (motif None : non collectés).
    # Anthropic : conflit d'intérêts déclaré (le code est écrit par un modèle d'Anthropic).
    "Anthropic": {"url": "https://www.anthropic.com/news", "motif": None},
    "Meta AI": {"url": "https://ai.meta.com/blog/", "motif": None},
    "Mistral": {"url": "https://mistral.ai/news", "motif": None},
    "xAI": {"url": "https://x.ai/news", "motif": None},
    "Prix Nobel": {"url": "https://www.nobelprize.org/", "motif": None},   # 2026-11-27, 20 h 58 : demande de l'auteur
    "CPI, Assemblée des États parties": {"url": "https://asp.icc-cpi.int/press-releases", "motif": None},  # 20 h 59
    "CPI, la Cour": {"url": "https://www.icc-cpi.int/news", "motif": None},   # communiqués de la Cour elle-même
    "Oscars, presse": {"url": "https://press.oscars.org/tag/news", "motif": None},   # 21 h 01 : demande de l'auteur
    "CIJ, communiqués": {"url": "https://www.icj-cij.org/press-releases", "motif": None},   # 21 h 02 : demande de l'auteur   # lecture d'essai relue (run 46055978219) : titres « type — pays » propres
}

_A = re.compile(r"<a\b[^>]*?href=[\"']([^\"'#]+)[\"'][^>]*>(.*?)</a>", re.I | re.S)
_BALISE = re.compile(r"<[^>]+>")


def liens(html: str, base: str) -> list[tuple[str, str]]:
    """(adresse absolue, titre du lien) pour les liens du même site que la page."""
    hote = urlparse(base).netloc
    out = []
    for href, corps in _A.findall(html):
        u = urljoin(base, href.strip())
        if urlparse(u).netloc != hote or not u.startswith("http"):
            continue
        titre = " ".join(html_mod.unescape(_BALISE.sub(" ", corps)).split())
        out.append((u, titre))
    return out


def gabarit(url: str) -> str:
    """Chemin réduit à ses deux premiers segments, chiffres remplacés par N."""
    segs = [s for s in urlparse(url).path.split("/") if s][:3]
    return "/" + "/".join(re.sub(r"\d+", "N", s) for s in segs)


def sonde(html: str, base: str, n: int = 12) -> list[tuple[str, int, str, str]]:
    """Les gabarits les plus fréquents : (gabarit, nombre, exemple d'adresse, exemple de titre)."""
    groupes = collections.defaultdict(list)
    for u, t in liens(html, base):
        groupes[gabarit(u)].append((u, t))
    tri = sorted(groupes.items(), key=lambda x: -len(x[1]))[:n]
    return [(g, len(v), v[0][0], v[0][1][:80]) for g, v in tri]


_MOIS = r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?"
_DATE = re.compile(r"\b(\d{4}-\d{2}-\d{2}|\d{4}/\d{1,2}/\d{1,2}|\d{1,2}/\d{1,2}/\d{4}|" + _MOIS + r" \d{1,2},? \d{4}|"
                   r"\d{1,2} " + _MOIS + r",? \d{4})\b")
_DATETIME = re.compile(r"datetime=[\"'](\d{4}-\d{2}-\d{2})")


def iso(date_txt: str) -> str:
    """Date affichée → AAAA-MM-JJ quand le format est sans ambiguïté ; sinon chaîne vide (12/06/2026 : ambigu)."""
    from datetime import datetime
    t = date_txt.replace(",", " ").replace(".", " ")
    t = " ".join(t.split())
    for f in ("%Y-%m-%d", "%Y/%m/%d", "%b %d %Y", "%B %d %Y", "%d %b %Y", "%d %B %Y"):
        try:
            return datetime.strptime(t, f).date().isoformat()
        except ValueError:
            pass
    return ""


def lire(html: str, base: str, motif: str, ligne: bool = False) -> list[dict]:
    """Liens d'articles (chemin conforme au motif), sans doublon, avec un titre non vide.

    ligne=True : le titre réunit les titres de tous les liens de la même ligne de tableau (<tr>), et la première date
    de la ligne est gardée comme métadonnée (« date_affichee »). Rien d'autre du texte n'est gardé.
    """
    rx = re.compile(motif)
    blocs = re.split(r"<tr\b", html, flags=re.I) if ligne else [html]
    vus, out = set(), []
    for b in blocs:
        ls = liens(b, base)
        for u, t in ls:
            if u in vus or not rx.search(urlparse(u).path):
                continue
            if ligne:
                t = " — ".join(x for _, x in ls if x)
            if not t:
                continue
            vus.add(u)
            d = {"lien": u, "titre": t}
            m = (_DATETIME.search(b) or _DATE.search(_BALISE.sub(" ", b))) if ligne else None
            if m:
                d["date_affichee"] = iso(m.group(1)) or m.group(1)
            out.append(d)
    return out


def collecter(client, jour: str, vues_fichier=None) -> list[dict]:
    """Lignes du puits pour les liens jamais vus des SITES (jour = jour de première vue). Robots respecté.

    Une page sans flux montre les mêmes liens d'un jour à l'autre : les liens déjà vus sont mémorisés dans
    registre/puits/pages-vues.json (liens seuls). Un site en échec est sauté, la collecte continue.
    """
    import json
    from pathlib import Path

    import politesse
    p = Path(vues_fichier or Path("registre") / "puits" / "pages-vues.json")
    try:
        vues = set(json.loads(p.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        vues = set()
    out = []
    for nom, d in SITES.items():
        if not d.get("motif") or not d.get("valide"):
            continue
        try:
            if not politesse.autorise(client, d["url"]):
                print(f"Pages sans flux : {nom} refusé par robots.txt")
                continue
            r = client.get(d["url"])
            if r.status_code != 200:
                print(f"Pages sans flux : {nom} HTTP {r.status_code}")
                continue
            arts = lire(r.text, str(r.url), d["motif"], d.get("ligne", False))
        except Exception as e:
            print(f"Pages sans flux : {nom} en échec ({type(e).__name__})")
            continue
        neufs = [a for a in arts if a["lien"] not in vues]
        print(f"Pages sans flux : {nom}, {len(arts)} liens lus, {len(neufs)} nouveaux")
        for a in neufs:
            vues.add(a["lien"])
            out.append({"jour": jour, "lien": a["lien"], "titre": a["titre"], "famille": "page:" + nom,
                        "date_affichee": a.get("date_affichee", "")})
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(sorted(vues), ensure_ascii=False), encoding="utf-8")
    return out
