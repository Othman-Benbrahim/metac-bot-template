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
    # un camp peut être une coalition : « Government of Israel, Government of United States of America »
    for part in _re.split(r",\s*(?=Government of )", camp.strip()):
        m = _re.match(r"Government of (.+)$", part.strip())
        if m and table.get(_re.sub(r"\s*\(.*?\)\s*", "", m.group(1)).strip().lower()) in isos:
            return True
    return False


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


def epoch(reg: Path, labo: str = "frontiere") -> list[tuple[str, float]]:
    """0.10.509 (carte complétée, carte blanche de l'auteur du 2026-11-24, 20 h 48) : nombre de modèles publiés par mois
    par les laboratoires de pointe (OpenAI, Anthropic, Google, xAI, Meta), d'après Epoch AI (registre/epoch-modeles.csv)."""
    import collections
    labos = ("openai", "anthropic", "google", "xai", "meta") if labo == "frontiere" else (labo.lower(),)
    n = collections.Counter()
    for r in _csv(reg, "epoch-modeles.csv"):
        org = (r.get("Organization") or "").lower().replace(" ", "")
        d = (r.get("Publication date") or "")[:7]
        if len(d) == 7 and any(l in org for l in labos):
            n[d + "-01"] += 1
    if not n:
        return []
    mois, fin = sorted(n), max(n)
    a, m = map(int, mois[0][:7].split("-"))
    out = []
    while f"{a}-{m:02d}-01" <= fin:
        out.append((f"{a}-{m:02d}-01", float(n.get(f"{a}-{m:02d}-01", 0))))
        a, m = (a + 1, 1) if m == 12 else (a, m + 1)
    return out


def elo(reg: Path, famille: str, quoi: str = "dispersion") -> list[tuple[str, float]]:
    """2026-11-24 (sources validées par l'auteur, 23 h 24) : classements de force (collecte_elo.py, registre/elo/).
    « elo:<famille>:<entité> » : la note de l'entité à chaque fin de mois ;
    « elo:<famille>:dispersion » : écart-type des 20 meilleures notes du mois (plus il est grand, plus les favoris
    dominent) ; « elo:<famille>:forme » : variation absolue moyenne d'un mois sur l'autre des 30 meilleurs (forme)."""
    import csv as _c
    import gzip as _g
    import statistics as _st
    f = reg / "elo" / f"{famille}.csv.gz"
    if not f.exists():
        return []
    par_mois, par_ent = {}, {}
    with _g.open(f, "rt", encoding="utf-8") as h:
        for r in _c.DictReader(h):
            m, e, v = r["date"][:7], r["entite"], float(r["elo"])
            par_mois.setdefault(m, {})[e] = v
            par_ent.setdefault(e, {})[m] = v
    if quoi not in ("dispersion", "forme"):
        return [(m + "-01", v) for m, v in sorted(par_ent.get(quoi, {}).items())]
    out, dernier, prec = [], {}, {}
    for m in sorted(par_mois):
        prec = dict(dernier)
        dernier.update(par_mois[m])
        top = sorted(dernier.items(), key=lambda x: -x[1])
        if quoi == "dispersion" and len(top) >= 20:
            out.append((m + "-01", round(_st.pstdev([v for _, v in top[:20]]), 2)))
        elif quoi == "forme":
            ch = [abs(par_mois[m][e] - prec[e]) for e, _ in top[:30] if e in par_mois[m] and e in prec]
            if len(ch) >= 5:
                out.append((m + "-01", round(sum(ch) / len(ch), 2)))
    return out


def fts(reg: Path, quoi: str = "couverture") -> list[tuple[str, float]]:
    """2026-11-25 (source validée par l'auteur) : appels humanitaires (collecte_fts.py, registre/fts/appels.csv.gz).
    « fts:couverture » : fonds reçus / besoins, tous appels confondus, par année (point daté du 1er juillet) ;
    « fts:couverture:<ISO3> » : idem pour un pays."""
    import csv as _c
    import gzip as _g
    f = reg / "fts" / "appels.csv.gz"
    if not f.exists():
        return []
    pays = quoi.split(":")[1] if ":" in quoi else None
    besoins, fonds = {}, {}
    with _g.open(f, "rt", encoding="utf-8") as h:
        for r in _c.DictReader(h):
            if pays and r["countryCode"] != pays:
                continue
            try:
                a, b, v = int(float(r["year"])), float(r["requirements"] or 0), float(r["funding"] or 0)
            except ValueError:
                continue
            if b <= 0:
                continue
            besoins[a] = besoins.get(a, 0) + b
            fonds[a] = fonds.get(a, 0) + v
    return [(f"{a}-07-01", round(100 * fonds[a] / besoins[a], 2)) for a in sorted(besoins)]


def wdi(reg: Path, pays: str, quoi: str) -> list[tuple[str, float]]:
    """2026-11-25 (remarque de l'auteur sur l'âge des populations) : Banque mondiale, WDI (collecte_banque_mondiale.py,
    registre/banque-mondiale-wdi.csv.gz). « wdi:monde:part65 » et « wdi:monde:part0014 » : part (%) des 65 ans et plus et
    des moins de 15 ans dans la population de toutes les économies, pondérée par la population ; « wdi:<ISO3>:<code> » :
    l'indicateur d'un pays. Un point par année, daté du 1er juillet."""
    import csv as _c
    import gzip as _g
    f = reg / "banque-mondiale-wdi.csv.gz"
    if not f.exists():
        return []
    num = {"part65": "SP.POP.65UP.TO", "part0014": "SP.POP.0014.TO"}
    a, b = {}, {}
    with _g.open(f, "rt", encoding="utf-8") as h:
        for r in _c.DictReader(h):
            an = r["annee"]
            if pays == "monde" and quoi in num:
                try:
                    x, t = float(r[num[quoi]]), float(r["SP.POP.TOTL"])
                except (KeyError, ValueError):
                    continue
                a[an] = a.get(an, 0.0) + x
                b[an] = b.get(an, 0.0) + t
            elif r["pays"] == pays:
                try:
                    a[an] = float(r[quoi])
                    b[an] = 1.0
                except (KeyError, ValueError):
                    continue
    k = 100.0 if pays == "monde" else 1.0
    return [(f"{an}-07-01", round(k * a[an] / b[an], 4)) for an in sorted(a) if b.get(an)]


def ages_dirigeants(reg: Path, region: str, quoi: str = "age_moyen") -> list[tuple[str, float]]:
    """2026-11-25 (demande de l'auteur) : âge des dirigeants en poste au 1er juillet, Archigos 4.1, 1946-2015
    (ecosystemes/dirigeants-ages.csv, mise_au_point/archigos_ages.py). « ages_dirigeants:<région>:age_moyen|part70 »,
    région = monde, ameriques, europe, afrique, moyen_orient, asie_oceanie."""
    import csv as _c
    f = Path(__file__).resolve().parent / "ecosystemes" / "dirigeants-ages.csv"
    if not f.exists() or quoi not in ("age_moyen", "part70"):
        return []
    with f.open(encoding="utf-8") as h:
        r = _c.DictReader(l for l in h if not l.startswith("#"))
        return [(f"{x['annee']}-07-01", float(x[quoi])) for x in r if x["region"] == region]


def confiance_actualite(reg: Path, pays: str) -> list[tuple[str, float]]:
    """2026-11-25 (source validée par l'auteur) : confiance dans l'actualité, Reuters Institute, Digital News Report 2026
    (ecosystemes/confiance-actualite.csv). « confiance_actualite:<ISO3> » ou « confiance_actualite:mediane » (médiane des
    48 marchés, 2025 et 2026 seulement, même échantillon). Daté du 15 juin, mois de publication du rapport (pas d'avance)."""
    import csv as _c
    import statistics as _st
    f = Path(__file__).resolve().parent / "ecosystemes" / "confiance-actualite.csv"
    if not f.exists():
        return []
    with f.open(encoding="utf-8") as h:
        r = list(_c.DictReader(l for l in h if not l.startswith("#")))
    if pays == "mediane":
        par = {}
        for x in r:
            if x["annee"] in ("2025", "2026"):
                par.setdefault(x["annee"], []).append(float(x["confiance"]))
        return [(f"{a}-06-15", float(_st.median(v))) for a, v in sorted(par.items())]
    return [(f"{x['annee']}-06-15", float(x["confiance"])) for x in r if x["pays"] == pays]


def owid(reg: Path, slug: str, entite: str = "World", col: str = "0") -> list[tuple[str, float]]:
    """2026-11-25 (source validée par l'auteur) : un graphique d'Our World in Data (registre/owid/<slug>.csv.gz,
    collecte_owid.py). « owid:<graphique>[:<entité>[:<colonne>]] » ; entité = nom (World, Arctic Ocean…), code ISO3, ou
    « somme » / « moyenne » des pays (codes à trois lettres), ou « unique » (graphique à une seule entité) ; colonne = rang de la colonne de valeurs (0 par défaut) ou
    « somme » de toutes. Année → 1er juillet ; une colonne Day garde sa date."""
    import csv as _c
    import gzip as _g
    f = reg / "owid" / f"{slug}.csv.gz"
    if not f.exists():
        return []
    with _g.open(f, "rt", encoding="utf-8-sig") as h:
        norm = {"entity": "Entity", "code": "Code", "year": "Year", "day": "Day", "date": "Day"}
        r = [{norm.get(k.lower(), k): v for k, v in x.items()} for x in _c.DictReader(h)]   # noms courts en minuscules
    if not r:
        return []
    cles = list(r[0])
    temps = "Day" if "Day" in cles else ("Year" if "Year" in cles else None)
    if temps is None:
        return []
    vals = [k for k in cles if k not in ("Entity", "Code", "Year", "Day", "owid_region")]   # owid_region : texte
    choix = vals if col == "somme" else vals[int(col):int(col) + 1]
    agr: dict[str, list[float]] = {}
    for x in r:
        code = x.get("Code") or ""
        if entite in ("somme", "moyenne"):
            if len(code) != 3:
                continue
        elif entite != "unique" and x["Entity"] != entite and code != entite:
            continue
        try:
            v = sum(float(x[k]) for k in choix)
        except (ValueError, KeyError):
            continue
        d = x[temps] if temps == "Day" else f"{int(x[temps]):04d}-07-01"
        agr.setdefault(d, []).append(v)
    return [(d, round(sum(v) / len(v) if entite == "moyenne" else sum(v), 6)) for d, v in sorted(agr.items())]


ADAPTATEURS = {"owid": owid, "confiance_actualite": confiance_actualite, "ages_dirigeants": ages_dirigeants, "elo": elo, "wdi": wdi, "fts": fts, "epoch": epoch, "nowcast": nowcast, "portwatch": portwatch, "ooni": ooni, "feux": feux, "sanctions": sanctions, "dyade": dyade,
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
