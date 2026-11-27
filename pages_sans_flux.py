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
    "ElectionGuide": {"url": "https://www.electionguide.org/elections/", "motif": None},
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


def lire(html: str, base: str, motif: str) -> list[dict]:
    """Liens d'articles (chemin conforme au motif), sans doublon, avec un titre non vide."""
    rx = re.compile(motif)
    vus, out = set(), []
    for u, t in liens(html, base):
        if u in vus or not t or not rx.search(urlparse(u).path):
            continue
        vus.add(u)
        out.append({"lien": u, "titre": t})
    return out
