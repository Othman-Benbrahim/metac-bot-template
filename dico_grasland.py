"""Second codeur pour la détection des pays dans les flux RSS : dictionnaire de Grasland et Toureille
(bot 0.10.219, en ombre).

Décision d'auteur du 2026-11-17 (2 h 19). Source : C. Grasland et E. Toureille, « A multilingual dictionary for the
recognition of macro-regions and countries mentioned in daily press news », Cybergeo, Data papers, 2026
(doi:10.4000/16cap) ; dictionnaire du projet ANR-DFG IMAGEUN ; programmes sous licence MIT
(github.com/worldregio/cybergeo_datapaper). Le dictionnaire est LU à chaque passage depuis leur dépôt, jamais recopié
dans le nôtre (la version Dataverse est en CC BY-ND : pas de version modifiée diffusée).

Ce qu'il apporte à notre détection (noms et gentilés) :
- les capitales employées pour désigner un État (« Moscou dément… » → Russie) et quelques chefs d'État ou de
  gouvernement (actes publics dans leur fonction, comptés en agrégé : règle éthique du 2026-11-16) ;
- 108 entités supranationales (UE, OTAN, Union africaine, Sahel, Balkans…), comptées à part ;
- ses propres exclusions (clubs, entreprises, régions françaises : code ZZZ) et ses ambiguïtés (« Bruxelles »,
  « America », Congo, Guinée : codes XXX), masquées sans être comptées.
Il ne connaît pas les gentilés (« russe ») : les deux méthodes sont complémentaires.

Application, comme dans leurs programmes : apostrophes, tirets et deux-points remplacés par des espaces ; recherche
SENSIBLE À LA CASSE ; expressions les plus longues d'abord, chaque expression trouvée masquée.
"""
from __future__ import annotations

import csv
import io
import re

URL = "https://raw.githubusercontent.com/worldregio/cybergeo_datapaper/main/dict/dict_final.csv"
CODES = "https://raw.githubusercontent.com/datasets/country-codes/main/data/country-codes.csv"
_COUPURES = re.compile(r"['’\-:]")


def normaliser(texte: str) -> str:
    return _COUPURES.sub(" ", texte or "")


def construire(lignes: list[dict], iso3_iso2: dict[str, str], langues: tuple[str, ...]) -> list[tuple[re.Pattern, str, str]]:
    """(motif, genre, cible) ; genre « pays » (cible ISO à deux lettres), « region » (code de la macro-région) ou
    « masque » (exclusion ou ambiguïté : masquée, jamais comptée)."""
    entrees = {}
    for x in lignes:
        if x.get("lang") not in langues:
            continue
        alias = normaliser(str(x.get("alias") or "")).strip()
        alias = re.sub(r"\s+", " ", alias)
        code = str(x.get("code") or "")
        parties = code.split("_")
        if len(alias) < 2 or not parties:
            continue
        if parties[0] == "STA" and len(parties) >= 3 and parties[1] != "XXX":
            iso2 = iso3_iso2.get(parties[2])
            if not iso2:
                continue
            genre, cible = "pays", iso2
        elif parties[0] == "REG":
            genre, cible = "region", code
        else:                                   # ZZZ (exclusion), XXX et STA_XXX (ambiguïté)
            genre, cible = "masque", code
        entrees.setdefault(alias, (genre, cible))
    return [(re.compile(r"(?<![\w])" + re.escape(a).replace(r"\ ", r"\s+") + r"(?![\w])"), g, c)
            for a, (g, c) in sorted(entrees.items(), key=lambda t: -len(t[0]))]


def detecter(texte: str, motifs: list[tuple[re.Pattern, str, str]]) -> tuple[set[str], set[str]]:
    """(pays, macro-régions) reconnus dans le texte."""
    t = normaliser(texte)
    pays, regions = set(), set()
    for m, genre, cible in motifs:
        if m.search(t):
            if genre == "pays":
                pays.add(cible)
            elif genre == "region":
                regions.add(cible)
            t = m.sub(" ", t)
    return pays, regions


_CACHE: dict = {}


def charger(c, langues: tuple[str, ...] = ("en", "fr")) -> list[tuple[re.Pattern, str, str]]:
    """Lit le dictionnaire et la table des codes ; liste vide si une source manque (les comptes ne sont pas écrits)."""
    if "lignes" in _CACHE:
        return construire(_CACHE["lignes"], _CACHE["table"], langues)
    try:
        r = c.get(URL, timeout=60)
        r.raise_for_status()
        lignes = list(csv.DictReader(io.StringIO(r.content.decode("utf-8-sig")), delimiter=";"))
        t = c.get(CODES, timeout=60)
        t.raise_for_status()
        table = {x["ISO3166-1-Alpha-3"].strip(): x["ISO3166-1-Alpha-2"].strip()
                 for x in csv.DictReader(io.StringIO(t.text))
                 if len((x.get("ISO3166-1-Alpha-3") or "").strip()) == 3 and len((x.get("ISO3166-1-Alpha-2") or "").strip()) == 2}
        table.setdefault("XKX", "XK")
    except Exception:
        return []
    _CACHE.update(lignes=lignes, table=table)
    return construire(lignes, table, langues)
