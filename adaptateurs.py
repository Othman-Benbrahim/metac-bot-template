"""Adaptateurs : traduisent une trace collectée (registre/) en série datée lisible par la carte vivante (0.10.317).

Décision de l'auteur, 2026-11-19, 4 h 33 : « des adaptateurs pour traduire la description en une forme interprétable
par le code ». Une trace de fiche d'écosystème porte un nom d'adaptateur (« portwatch:ormuz:petroliers ») ; l'adaptateur
rend [(AAAA-MM-JJ, valeur)] trié, à partir de nos seuls fichiers (aucun appel réseau).

Pour en ajouter un : une fonction (registre, *paramètres) → liste, inscrite dans ADAPTATEURS.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

REG = Path("registre")


def _csv(reg: Path, nom: str) -> list[dict]:
    f = reg / nom
    if not f.exists():
        return []
    with f.open(encoding="utf-8") as h:
        return list(csv.DictReader(h))


def portwatch(reg: Path, detroit: str, colonne: str = "navires") -> list[tuple[str, float]]:
    """Passages quotidiens d'un détroit (IMF PortWatch)."""
    return sorted((r["jour"], float(r[colonne] or 0)) for r in _csv(reg, "portwatch-detroits.csv") if r["detroit"] == detroit)


def portwatch_ref(reg: Path, detroit: str, colonne: str = "navires") -> list[tuple[str, float]]:
    """Année de référence d'avant-crise d'un détroit (exception Ormuz, 0.10.335) : sert d'habitude, pas d'état du jour."""
    return sorted((r["jour"], float(r[colonne] or 0)) for r in _csv(reg, "portwatch-reference.csv") if r["detroit"] == detroit)


def ooni(reg: Path, pays: str) -> list[tuple[str, float]]:
    """Part des mesures OONI en anomalie, par jour, pour un pays (censure, coupures)."""
    j: dict[str, list[float]] = {}
    for r in _csv(reg, "ooni-censure.csv"):
        if r["pays"] == pays:
            a = j.setdefault(r["jour"], [0.0, 0.0])
            a[0] += float(r["anomalies"] or 0)
            a[1] += float(r["mesures"] or 0)
    return sorted((d, a / m) for d, (a, m) in j.items() if m > 0)


def feux(reg: Path, pays: str) -> list[tuple[str, float]]:
    """Détections de feux actifs (FIRMS) par jour pour un pays."""
    return sorted((r["jour"], float(r["detections"] or 0)) for r in _csv(reg, "feux.csv") if r["pays"] == pays)


def sanctions(reg: Path, pays: str) -> list[tuple[str, float]]:
    """Désignations de sanctions par jour visant un pays (toutes sources)."""
    j: dict[str, float] = {}
    for r in _csv(reg, "sanctions.csv"):
        if r["pays"] == pays:
            j[r["jour"]] = j.get(r["jour"], 0.0) + float(r["designations"] or 0)
    return sorted(j.items())


def dyade(reg: Path, a: str, b: str) -> list[tuple[str, float]]:
    """Ton moyen hebdomadaire (Goldstein, −10 conflit à +10 coopération) des gestes de A envers B (GDELT)."""
    f = reg / "gdelt-dyades.json"
    if not f.exists():
        return []
    s = json.loads(f.read_text(encoding="utf-8"))["sens"].get(f"{a}>{b}", {})
    return sorted((k, v["somme_g"] / (v["n"] + 5)) for k, v in s.items())


def fred(reg: Path, serie: str) -> list[tuple[str, float]]:
    """Une série publique de la FRED (collecte_fred.py) : Brent, stocks, taux, inflation, dollar, alimentation."""
    return sorted((r["jour"], float(r["valeur"])) for r in _csv(reg, "fred.csv") if r["serie"] == serie)


def eia(reg: Path, serie: str) -> list[tuple[str, float]]:
    """Une série hebdomadaire de l'EIA (collecte_eia.py) : stocks de brut, réserve stratégique, production, demande."""
    return sorted((r["jour"], float(r["valeur"])) for r in _csv(reg, "eia.csv") if r["serie"] == serie)


def ouvert(reg: Path, serie: str) -> list[tuple[str, float]]:
    """Séries ouvertes des compartiments vides (collecte_ouvertes.py) : polarisation_chambre, co2_mauna_loa, attention_crise."""
    return sorted((r["jour"], float(r["valeur"])) for r in _csv(reg, "ouvertes.csv") if r["serie"] == serie)


def meteo(reg: Path, point: str) -> list[tuple[str, float]]:
    """ANOMALIE de température du jour (°C) par rapport aux mêmes jours de l'année (± 7 jours) des années
    précédentes, pour un point (collecte_meteo.py). Jours sans référence (première année) : écartés."""
    from datetime import date
    serie = sorted((r["jour"], float(r["t_moy"])) for r in _csv(reg, "meteo-points.csv") if r["point"] == point)
    par_jour: dict[int, list[tuple[int, float]]] = {}
    for j, t in serie:
        d = date.fromisoformat(j)
        par_jour.setdefault(d.timetuple().tm_yday, []).append((d.year, t))
    out = []
    for j, t in serie:
        d = date.fromisoformat(j)
        doy = d.timetuple().tm_yday
        ref = [x for k in range(doy - 7, doy + 8) for (an, x) in par_jour.get((k - 1) % 366 + 1, []) if an < d.year]
        if len(ref) >= 15:
            out.append((j, round(t - sum(ref) / len(ref), 2)))
    return out


def climat(reg: Path, point: str) -> list[tuple[str, float]]:
    """Le CLIMAT et non la météo (rappel de l'auteur) : moyenne glissante sur 365 jours de l'anomalie de température
    d'un point — la dérive lente, débarrassée des jours et des saisons."""
    s = meteo(reg, point)
    out, somme = [], 0.0
    for i, (j, x) in enumerate(s):
        somme += x
        if i >= 365:
            somme -= s[i - 365][1]
        if i >= 364:
            out.append((j, round(somme / 365, 3)))
    return out


def nowcast(reg: Path, *parties: str) -> list[tuple[str, float]]:
    """Prévision immédiate de l'inflation (Réserve fédérale de Cleveland, collecte_nowcast_inflation.py), par jour de
    relevé ; mesure par exemple « variation_mensuelle:CPI » (les deux-points de la mesure sont gardés)."""
    mesure = ":".join(parties)
    return sorted((r["releve_le"], float(r["valeur"])) for r in _csv(reg, "nowcast-inflation.csv")
                  if r["mesure"] == mesure and r["valeur"] not in ("", None))


ADAPTATEURS = {"nowcast": nowcast, "portwatch": portwatch, "ooni": ooni, "feux": feux, "sanctions": sanctions, "dyade": dyade,
               "fred": fred, "meteo": meteo, "climat": climat, "eia": eia, "ouvert": ouvert,
               "portwatch_ref": portwatch_ref}


def variation(serie: list[tuple[str, float]], pas: int) -> list[tuple[str, float]]:
    """Variation en % sur `pas` relevés (0.10.323) : pour une série à tendance (un indice de prix qui monte chaque mois),
    c'est le rythme qui dit l'intensité, pas le niveau."""
    return [(serie[i][0], round(100 * (serie[i][1] / serie[i - pas][1] - 1), 4)) for i in range(pas, len(serie)) if serie[i - pas][1]]


def lire(nom: str, reg: Path = REG) -> list[tuple[str, float]]:
    """« portwatch:ormuz:petroliers » → série datée ; nom inconnu → erreur explicite."""
    type_, *params = nom.split(":")
    if params and params[-1].startswith("var") and params[-1][3:].isdigit():   # « fred:CPIAUCSL:var12 »
        return variation(lire(":".join([type_] + params[:-1]), reg), int(params[-1][3:]))
    if type_ not in ADAPTATEURS:
        raise KeyError(f"adaptateur inconnu : {type_} (connus : {sorted(ADAPTATEURS)})")
    return ADAPTATEURS[type_](reg, *params)


# 0.10.323 : les adaptateurs des sources déjà collectées mais encore « dormantes » vivent dans des modules à part
# (adaptateurs_sources_*.py), chacun inscrivant ses fonctions dans ADAPTATEURS.
import importlib as _il
import pkgutil as _pk
for _m in sorted(m.name for m in _pk.iter_modules([str(Path(__file__).resolve().parent)]) if m.name.startswith("adaptateurs_sources_")):
    try:
        _il.import_module(_m)
    except Exception as _e:                                    # un module cassé ne doit pas casser la carte
        print(f"adaptateurs : {_m} ignoré ({type(_e).__name__}: {_e})")
