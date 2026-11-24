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
    """Ton moyen hebdomadaire (Goldstein, −10 conflit à +10 coopération) des gestes de A envers B (GDELT).
    0.10.360 : retiré des fiches (une note de qualité n'est pas une mesure) ; gardé pour le banc de réciprocité déjà publié."""
    f = reg / "gdelt-dyades.json"
    if not f.exists():
        return []
    s = json.loads(f.read_text(encoding="utf-8"))["sens"].get(f"{a}>{b}", {})
    return sorted((k, v["somme_g"] / (v["n"] + 5)) for k, v in s.items())


def gestes(reg: Path, a: str, b: str, categorie: str = "n") -> list[tuple[str, float]]:
    """NOMBRE hebdomadaire de gestes de A envers B (GDELT, mode dyades) ; catégorie : n (tous), coop_verbale,
    coop_materielle, conflit_verbal, conflit_materiel. 0.10.360 (décision d'auteur du 2026-11-19, 18 h 23) : remplace
    dyade: dans les fiches ; une note donnée à la qualité d'un échange (échelle de Goldstein) n'a pas de valeur de
    mesure, un compte en a une."""
    f = reg / "gdelt-dyades.json"
    if not f.exists():
        return []
    s = json.loads(f.read_text(encoding="utf-8"))["sens"].get(f"{a}>{b}", {})
    return sorted((k, float(v.get(categorie, 0))) for k, v in s.items())


def fred(reg: Path, serie: str) -> list[tuple[str, float]]:
    """Une série publique de la FRED (collecte_fred.py) : Brent, stocks, taux, inflation, dollar, alimentation."""
    return sorted((r["jour"], float(r["valeur"])) for r in _csv(reg, "fred.csv") if r["serie"] == serie)


def eia(reg: Path, serie: str) -> list[tuple[str, float]]:
    """Une série hebdomadaire de l'EIA (collecte_eia.py) : stocks de brut, réserve stratégique, production, demande."""
    return sorted((r["jour"], float(r["valeur"])) for r in _csv(reg, "eia.csv") if r["serie"] == serie)


def ouvert(reg: Path, serie: str) -> list[tuple[str, float]]:
    """Séries ouvertes des compartiments vides (collecte_ouvertes.py) : polarisation_chambre, co2_mauna_loa, attention_crise."""
    return sorted((r["jour"], float(r["valeur"])) for r in _csv(reg, "ouvertes.csv") if r["serie"] == serie)


def webamon(reg: Path, index: str = "new_domains") -> list[tuple[str, float]]:
    """Comptes quotidiens Webamon (collecte_webamon.py) : new_domains (nouveaux domaines), scans (analyses d'URL)."""
    return sorted((r["jour"], float(r["total"])) for r in _csv(reg, "webamon.csv") if r["index"] == index)


def openmeasures(reg: Path, site: str = "telegram", serie: str = "complot") -> list[tuple[str, float]]:
    """Part quotidienne d'une série de termes (collecte_openmeasures.py) dans le volume de la plateforme, en pour
    dix mille messages de référence ; « brut » en dernier paramètre rend le compte non normalisé."""
    lignes = _csv(reg, "openmeasures.csv")
    n = {r["jour"]: float(r["n"]) for r in lignes if r["site"] == site and r["serie"] == serie}
    if serie == "reference":
        return sorted(n.items())
    ref = {r["jour"]: float(r["n"]) for r in lignes if r["site"] == site and r["serie"] == "reference"}
    return sorted((j, round(1e4 * v / ref[j], 3)) for j, v in n.items() if ref.get(j))


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


def pluie(reg: Path, point: str, fenetre: str = "30") -> list[tuple[str, float]]:
    """0.10.476 : pluie des N derniers jours (30 par défaut) rapportée à la normale, en pour cent — la normale est la
    moyenne des cumuls de la même fenêtre (même jour de fin) des années précédentes, au moins 3 ans. 100 = normale ;
    87 = la mousson 2026 de l'IMD. Jours manquants : la fenêtre doit en avoir au moins 80 %."""
    from datetime import date, timedelta
    n = int(fenetre)
    obs = {r["jour"]: float(r["pluie_mm"]) for r in _csv(reg, "meteo-pluie.csv") if r["point"] == point}
    if not obs:
        return []

    def cumul(fin: date) -> float | None:
        jours = [(fin - timedelta(days=k)).isoformat() for k in range(n)]
        v = [obs[j] for j in jours if j in obs]
        return sum(v) * n / len(v) if len(v) >= 0.8 * n else None

    out = []
    for j in sorted(obs):
        d = date.fromisoformat(j)
        x = cumul(d)
        if x is None:
            continue
        ref = []
        for a in range(1, 11):
            try:
                y = cumul(d.replace(year=d.year - a))
            except ValueError:                  # 29 février
                y = cumul(d.replace(year=d.year - a, day=28))
            if y is not None:
                ref.append(y)
        if len(ref) >= 3 and sum(ref) > 0:
            out.append((j, round(100 * x / (sum(ref) / len(ref)), 1)))
    return out


def ucdp_mois(reg: Path, iso3: str, colonne: str = "somme") -> list[tuple[str, float]]:
    """0.10.477 : morts par mois d'un pays (code ISO3) d'après la carte UCDP lue chaque mois (lecture_cartes.py,
    registre/cartes/ucdp-pays-mois.csv) ; tous les pays, historique 1989-2025 et mois de 2026. Un mois sans ligne
    compte zéro entre le premier et le dernier mois publiés. Date : le premier du mois."""
    lignes = _csv(reg / "cartes", "ucdp-pays-mois.csv")
    if not lignes:
        return []
    mois = sorted({r["mois"] for r in lignes})
    c = {r["mois"]: float(r.get(colonne) or 0) for r in lignes if r["iso3"] == iso3}
    if not c:
        return []
    out, m = [], mois[0]
    while m <= mois[-1]:
        out.append((m + "-01", c.get(m, 0.0)))
        a, b = int(m[:4]), int(m[5:7])
        m = f"{a + (b == 12)}-{b % 12 + 1:02d}"
    return out


def _camp_pays(camp: str, isos: set[str], table: dict[str, str]) -> bool:
    """« Government of Israel » appartient à ISR ; « Government of United States of America » à USA. Les camps non
    étatiques (Hamas, IS…) ne sont rattachés à aucun pays."""
    import re as _re
    m = _re.match(r"Government of (.+)$", camp.strip())
    if not m:
        return False
    nom = _re.sub(r"\s*\(.*?\)\s*", "", m.group(1)).strip().lower()
    return table.get(nom) in isos


def ucdp_dyade(reg: Path, a: str, b: str, colonne: str = "evenements") -> list[tuple[str, float]]:
    """0.10.493 : violence organisée entre les gouvernements de deux pays (codes ISO3, paire non orientée), par mois,
    d'après registre/cartes/ucdp-dyades-mois.csv (camps de la GED). Un mois sans ligne compte zéro entre le premier et le
    dernier mois publiés. colonne : evenements ou somme (morts, meilleure estimation)."""
    import lecture_cartes as _lc
    lignes = _csv(reg / "cartes", "ucdp-dyades-mois.csv")
    if not lignes:
        return []
    table = _lc.table_pays()
    mois = sorted({r["mois"] for r in lignes})
    c: dict[str, float] = {}
    for r in lignes:
        if ((_camp_pays(r["camp_a"], {a}, table) and _camp_pays(r["camp_b"], {b}, table)) or
                (_camp_pays(r["camp_a"], {b}, table) and _camp_pays(r["camp_b"], {a}, table))):
            c[r["mois"]] = c.get(r["mois"], 0.0) + float(r.get(colonne) or 0)
    out, m = [], mois[0]
    while m <= mois[-1]:
        out.append((m + "-01", c.get(m, 0.0)))
        y, k = int(m[:4]), int(m[5:7])
        m = f"{y + (k == 12)}-{k % 12 + 1:02d}"
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


def pub(reg: Path, serie: str) -> list[tuple[str, float]]:
    """Séries publiques (collecte_series_publiques.py) : banquise, météo spatiale, El Niño, fleuves, sécheresse, récoltes
    prévues par l'USDA, prépublications arXiv."""
    return sorted((r["jour"], float(r["valeur"])) for r in _csv(reg, "series-publiques.csv") if r["serie"] == serie)


def port(reg: Path, nom: str, colonne: str = "escales") -> list[tuple[str, float]]:
    """Escales quotidiennes d'un port (IMF PortWatch, collecte_portwatch.py)."""
    return sorted((r["jour"], float(r[colonne] or 0)) for r in _csv(reg, "portwatch-ports.csv") if r["port"] == nom)


def seismes(reg: Path, colonne: str = "m6") -> list[tuple[str, float]]:
    """Séismes par jour (catalogue USGS, collecte_seismes.py) : m45, m6, m7 (nombre au-dessus de la magnitude), mmax,
    iran_m45 (plateau iranien). Les jours sans séisme sont dans le registre (zéro)."""
    return [(r["jour"], float(r[colonne])) for r in _csv(reg, "seismes-usgs.csv")]


def meteo_prevue(reg: Path, point: str, echeance: str = "") -> list[tuple[str, float]]:
    """Chaleur ANNONCÉE (GFS, collecte_gfs.py), datée du jour du run : anomalie de la température prévue par rapport
    aux mêmes jours de l'année des années précédentes à la station GHCN du point (même référence que meteo:).
    Sans échéance : moyenne des anomalies de J+1 à J+7 ; « meteo_prevue:delhi:3 » : J+3 seulement.
    Biais grille/station : retranché quand au moins 10 paires (prévision à J+1, observation du même jour) existent
    dans les 60 jours qui précèdent le run."""
    from datetime import date, timedelta
    obs = {j: t for j, t in ((r["jour"], float(r["t_moy"])) for r in _csv(reg, "meteo-points.csv") if r["point"] == point)}
    par_doy: dict[int, list[tuple[int, float]]] = {}
    for j, t in obs.items():
        d = date.fromisoformat(j)
        par_doy.setdefault(d.timetuple().tm_yday, []).append((d.year, t))

    def normale(j: str) -> float | None:
        d = date.fromisoformat(j)
        doy = d.timetuple().tm_yday
        ref = [x for k in range(doy - 7, doy + 8) for (an, x) in par_doy.get((k - 1) % 366 + 1, []) if an < d.year]
        return sum(ref) / len(ref) if len(ref) >= 15 else None

    prev = [r for r in _csv(reg, "gfs-previsions.csv") if r["point"] == point]
    j1 = {r["jour"]: float(r["t_moy"]) for r in prev if r["echeance"] == "1"}
    par_run: dict[str, list[tuple[str, float]]] = {}
    for r in prev:
        if not echeance or r["echeance"] == echeance:
            par_run.setdefault(r["run"], []).append((r["jour"], float(r["t_moy"])))
    out = []
    for run, jours in sorted(par_run.items()):
        d0 = date.fromisoformat(run)
        paires = [j1[j] - obs[j] for j in j1 if j in obs and d0 - timedelta(days=60) <= date.fromisoformat(j) < d0]
        biais = sum(paires) / len(paires) if len(paires) >= 10 else 0.0
        an = [t - biais - n for j, t in jours if (n := normale(j)) is not None]
        if an:
            out.append((run, round(sum(an) / len(an), 2)))
    return out


def nowcast(reg: Path, *parties: str) -> list[tuple[str, float]]:
    """Prévision immédiate de l'inflation (Réserve fédérale de Cleveland, collecte_nowcast_inflation.py), par jour de
    relevé ; mesure par exemple « variation_mensuelle:CPI » (les deux-points de la mesure sont gardés)."""
    mesure = ":".join(parties)
    return sorted((r["releve_le"], float(r["valeur"])) for r in _csv(reg, "nowcast-inflation.csv")
                  if r["mesure"] == mesure and r["valeur"] not in ("", None))


ADAPTATEURS = {"nowcast": nowcast, "portwatch": portwatch, "ooni": ooni, "feux": feux, "sanctions": sanctions, "dyade": dyade,
               "fred": fred, "meteo": meteo, "pluie": pluie, "ucdp_mois": ucdp_mois, "ucdp_dyade": ucdp_dyade, "climat": climat, "eia": eia, "ouvert": ouvert, "webamon": webamon, "openmeasures": openmeasures,
               "portwatch_ref": portwatch_ref, "seismes": seismes, "meteo_prevue": meteo_prevue,
               "pub": pub, "port": port, "gestes": gestes}


def variation(serie: list[tuple[str, float]], pas: int) -> list[tuple[str, float]]:
    """Variation en % sur `pas` relevés (0.10.323) : pour une série à tendance (un indice de prix qui monte chaque mois),
    c'est le rythme qui dit l'intensité, pas le niveau."""
    return [(serie[i][0], round(100 * (serie[i][1] / serie[i - pas][1] - 1), 4)) for i in range(pas, len(serie)) if serie[i - pas][1]]


def lire(nom: str, reg: Path = REG) -> list[tuple[str, float]]:
    """« portwatch:ormuz:petroliers » → série datée ; nom inconnu → erreur explicite."""
    type_, *params = nom.split(":")
    if params and params[-1].startswith("proche") and params[-1][6:].isdigit():   # « memoire:RU:proche7 » (0.10.338)
        # un compte à rebours devient une intensité : 1 les N jours qui précèdent l'échéance (et le jour même), 0 sinon
        n = int(params[-1][6:])
        return [(j, 1.0 if 0 <= v <= n else 0.0) for j, v in lire(":".join([type_] + params[:-1]), reg)]
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
