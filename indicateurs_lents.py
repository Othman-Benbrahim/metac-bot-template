"""Indicateurs qui bougent lentement (inflation, chômage, sondages) : fourchette de la prochaine publication
(0.10.404, préenregistrement preenregistrements/indicateurs-lents.md). Dernière valeur publiée + quantiles empiriques des
variations passées entre deux publications (36 dernières). Rien dans le bot à ce stade.
"""
from __future__ import annotations


def fourchette_suivante(valeurs: list[float], h: int = 1, ps=(0.1, 0.2, 0.4, 0.6, 0.8, 0.9), fenetre: int = 36):
    """`valeurs` : publications successives, de la plus ancienne à la plus récente. h : nombre de publications à venir."""
    if len(valeurs) < fenetre // 2 + h + 1:
        return None
    v = valeurs[-(fenetre + h):]
    pas = sorted(b - a for a, b in zip(v[:-h], v[h:]))
    if not pas:
        return None
    def q(p):
        i = p * (len(pas) - 1)
        lo, hi = int(i), min(len(pas) - 1, int(i) + 1)
        return pas[lo] + (pas[hi] - pas[lo]) * (i - lo)
    return [(p, valeurs[-1] + q(p)) for p in ps]


# ---- branchement (0.10.404) : séries FRED déjà collectées, prochaine publication seulement (h = 1)
import csv as _csv
import re as _re
from pathlib import Path as _Path

_FRED = _Path("registre") / "fred.csv"
SERIES = [  # (motif du titre, série FRED, transformation)
    (_re.compile(r"\bcore\b.*\b(cpi|consumer price)\b.*\b(year[- ]over[- ]year|yoy|annual|12-month)\b|"
                 r"\b(year[- ]over[- ]year|yoy|annual|12-month)\b.*\bcore\b.*\b(cpi|consumer price)\b", _re.I), "CPILFESL", "glissement"),
    (_re.compile(r"\b(u\.?s\.?|united states|american)\b.*\b(cpi|consumer price)\b.*\b(year[- ]over[- ]year|yoy|annual|12-month)\b", _re.I), "CPIAUCSL", "glissement"),
    (_re.compile(r"\b(u\.?s\.?|united states|american)\b.*\bunemployment rate\b", _re.I), "UNRATE", "niveau"),
    (_re.compile(r"\b(university of michigan|umich)\b.*\bsentiment\b", _re.I), "UMCSENT", "niveau"),
]


_US = _re.compile(r"\b(u\.?s\.?|united states|american|bls)\b", _re.I)
_AILLEURS = _re.compile(r"\b(tokyo|japan\w*|euro\w*|uk|britain|british|china|chinese|canada|canadian|germany|german|"
                        r"france|french|india\w*|brazil\w*|mexic\w*|korea\w*|australia\w*|turkey|turkish|argentin\w*)\b", _re.I)


def fourchette_publication(titre: str) -> dict | None:
    """Fourchette de la prochaine publication d'une série FRED reconnue dans le titre (question numérique) ; seulement
    pour une question américaine sans mention d'un autre pays. 0.10.405 : inflation de Tokyo (e-Stat)."""
    t_ = fourchette_tokyo(titre)
    if t_ is not None:
        return t_
    if not _US.search(titre or "") or _AILLEURS.search(titre or ""):
        return None
    for rx, serie, tr in SERIES:
        if rx.search(titre or ""):
            break
    else:
        return None
    if not _FRED.exists():
        return None
    pts = sorted((r["jour"], float(r["valeur"])) for r in _csv.DictReader(_FRED.open(encoding="utf-8")) if r["serie"] == serie)
    x = [v for _, v in pts]
    if tr == "glissement":
        x = [100 * (x[i] / x[i - 12] - 1) for i in range(12, len(x))]
    f = fourchette_suivante(x)
    if not f:
        return None
    return {"serie": serie, "transformation": tr, "derniere_valeur": round(x[-1], 3), "date": pts[-1][0], "percentiles": f}


# ---- branchement (0.10.405) : inflation de Tokyo hors produits frais, e-Stat (preenregistrements/inflation-tokyo.md,
# critère atteint : 0,751 / 0,610). This service uses API functions from e-Stat, however its contents are not
# guaranteed by government.
MENTION_ESTAT = "This service uses API functions from e-Stat, however its contents are not guaranteed by government."
_ESTAT = _Path("registre") / "estat-tokyo-cpi.csv"
_TOKYO = _re.compile(r"\btokyo\b.*\bcore\b.*\b(cpi|consumer price|inflation)\b|\bcore\b.*\b(cpi|consumer price)\b.*\btokyo\b", _re.I)
_MOIS = {m: i for i, m in enumerate(["january", "february", "march", "april", "may", "june", "july", "august",
                                      "september", "october", "november", "december"], 1)}
_MOIS_RX = _re.compile(r"\b(" + "|".join(_MOIS) + r")\s+(20\d\d)\b", _re.I)


def fourchette_tokyo(titre: str) -> dict | None:
    """Mois demandé = mois suivant la dernière valeur publiée (seul horizon calibré) ; sinon rien."""
    if not _TOKYO.search(titre or "") or not _ESTAT.exists():
        return None
    m = _MOIS_RX.search(titre or "")
    if not m:
        return None
    cible = f"{m.group(2)}-{_MOIS[m.group(1).lower()]:02d}"
    pts = sorted((r["mois"], float(r["inflation_hors_frais_sur_un_an"]))
                 for r in _csv.DictReader(_ESTAT.open(encoding="utf-8")) if r["base"] == "2025")
    if not pts:
        return None
    a, mo = map(int, pts[-1][0].split("-"))
    suivant = f"{a + mo // 12}-{mo % 12 + 1:02d}"
    if cible != suivant:
        return None
    f = fourchette_suivante([v for _, v in pts])
    if not f:
        return None
    return {"serie": "TOKYO_CORE_CPI", "transformation": "glissement publié", "derniere_valeur": pts[-1][1],
            "date": pts[-1][0], "percentiles": f, "mention": MENTION_ESTAT}
