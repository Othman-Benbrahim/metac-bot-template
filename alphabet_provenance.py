"""Provenance des F « indépendantes », vérifiée SANS modèle, en ombre (bot 0.10.38 ; décision d'auteur du 2026-11-11,
d'après « The Corroboration Illusion », arXiv 2609.22246 : un LLM traite tout texte pertinent comme une preuve forte et
ignore l'éditeur ; la provenance doit se vérifier hors du modèle).

Pour chaque mot F dont la corroboration est « independantes », le lecteur donne `source_urls` (une URL par source, dans
l'ordre des sources). Le code vérifie :
  - qu'il y a au moins deux URL ;
  - que chacune figure dans les résultats de recherche effectivement exécutés (pas une adresse inventée) ;
  - qu'elles viennent de deux sites différents (domaine enregistrable : deux pages d'un même site, une source).
Rien ne change au calcul ni au chiffre posté : le verdict est inscrit au registre (C.provenance_F) et scoré.
"""
from __future__ import annotations

import re
from urllib.parse import urlsplit

URL_RE = re.compile(r"https?://[^\s<>\"'\)\]]+")
# suffixes à deux niveaux les plus courants (co.uk, gouv.fr…) : sans eux, bbc.co.uk et gov.uk seraient « co.uk »
DEUX_NIVEAUX = {"co", "com", "org", "net", "gov", "gouv", "ac", "edu", "go", "or", "ne", "gob", "nic", "mil"}


def normaliser(url: str) -> str:
    """Sans schéma, sans « www. », sans requête ni ancre, sans barre finale, en minuscules pour l'hôte."""
    u = urlsplit(str(url or "").strip().rstrip(".,;"))
    hote = (u.hostname or "").lower()
    hote = hote[4:] if hote.startswith("www.") else hote
    return f"{hote}{u.path.rstrip('/')}"


def domaine(url: str) -> str:
    hote = normaliser(url).split("/")[0]
    p = hote.split(".")
    if len(p) >= 3 and p[-2] in DEUX_NIVEAUX and len(p[-1]) == 2:
        return ".".join(p[-3:])
    return ".".join(p[-2:])


def urls_des_resultats(textes: str) -> set[str]:
    return {normaliser(u) for u in URL_RE.findall(str(textes or ""))}


def verdict(mot: dict, connues: set[str]) -> dict:
    urls = mot.get("source_urls")
    if isinstance(urls, str):
        urls = [x for x in re.split(r"[\s;,]+", urls) if x]
    urls = [str(u) for u in (urls or []) if str(u).startswith("http")]
    d = {"carte": f"{mot.get('carte')}@{mot.get('strate')}", "urls": urls[:4]}
    if not urls:
        return dict(d, statut="sans_urls")
    if len(urls) < 2:
        return dict(d, statut="une_seule_url")
    hors = [u for u in urls if normaliser(u) not in connues]
    doms = sorted({domaine(u) for u in urls})
    d["domaines"] = doms
    if hors:
        return dict(d, statut="url_hors_resultats", hors=hors[:4])
    if len(doms) < 2:
        return dict(d, statut="meme_domaine")
    return dict(d, statut="verifiee")


def provenance_F(dossier: dict | None, textes: str | None) -> dict | None:
    """None s'il n'y a aucun F « independantes » ; sinon le verdict de chacun et le compte par statut."""
    mots = [m for m in ((dossier or {}).get("mots") or []) if isinstance(m, dict)
            and m.get("intensite") == "F" and m.get("corroboration") == "independantes"]
    if not mots:
        return None
    connues = urls_des_resultats(textes or "")
    details = [verdict(m, connues) for m in mots]
    par: dict[str, int] = {}
    for x in details:
        par[x["statut"]] = par.get(x["statut"], 0) + 1
    return {"F_independantes": len(details), "par_statut": par, "toutes_verifiees": par.get("verifiee", 0) == len(details),
            "urls_dans_les_resultats": len(connues), "details": details}
