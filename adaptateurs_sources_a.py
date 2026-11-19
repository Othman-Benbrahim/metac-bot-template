"""Adaptateurs des sources collectées mais dormantes, lot A (0.10.323) : espace aérien, internet, institutions
américaines, calendriers.

Chaque fonction (reg, *paramètres) rend une série QUOTIDIENNE triée [(AAAA-MM-JJ, valeur)] lue dans registre/, sans
réseau. Comptes d'événements : jours sans événement = 0, sur la plage couverte par la source. Calendriers : « jours
avant la prochaine échéance » (0 le jour même), ce qui donne une intensité qui monte à l'approche de la date ; les
jours fériés chinois rendent 1 pendant le congé, 0 sinon. Aucune donnée personnelle : seulement des comptes agrégés
(les noms des personnes nommées ou des parties aux procès ne sont jamais lus).

Paramètre « tous » (par défaut) = pas de filtre.
"""
from __future__ import annotations

import json
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path

import adaptateurs as ad

TOUS = "tous"


def _jsonl(reg: Path, nom: str) -> list[dict]:
    f = reg / nom
    if not f.exists():
        return []
    return [json.loads(l) for l in f.read_text(encoding="utf-8").splitlines() if l.strip()]


def _jour(texte: str | None) -> str | None:
    """« 2026-11-18 », « 2026-11-18T23:07Z » ou « 11/18/2026 » → « 2026-11-18 » ; illisible → None."""
    t = (texte or "").strip()
    try:
        if len(t) >= 10 and t[4] == "-":
            return date.fromisoformat(t[:10]).isoformat()
        if "/" in t:
            m, j, a = t.split("/")[:3]
            return date(int(a[:4]), int(m), int(j)).isoformat()
    except (ValueError, IndexError):
        return None
    return None


def _quotidien(comptes: Counter, debut: str | None = None, fin: str | None = None) -> list[tuple[str, float]]:
    """Comptes par jour → série quotidienne continue (0 les jours sans événement)."""
    jours = [j for j in comptes if j]
    if not jours and not (debut and fin):
        return []
    d0 = date.fromisoformat(debut or min(jours))
    d1 = date.fromisoformat(fin or max(jours))
    out, d = [], d0
    while d <= d1:
        out.append((d.isoformat(), float(comptes.get(d.isoformat(), 0))))
        d += timedelta(days=1)
    return out


def _jours_avant(echeances: list[str], debut: str, fin: str) -> list[tuple[str, float]]:
    """Pour chaque jour de [debut, fin], nombre de jours jusqu'à la prochaine échéance (0 le jour même) ; les jours
    après la dernière échéance connue sont omis (on ne sait pas)."""
    dates = sorted({date.fromisoformat(e) for e in echeances})
    if not dates:
        return []
    out, d, i = [], date.fromisoformat(debut), 0
    while d <= date.fromisoformat(fin):
        while i < len(dates) and dates[i] < d:
            i += 1
        if i == len(dates):
            break
        out.append((d.isoformat(), float((dates[i] - d).days)))
        d += timedelta(days=1)
    return out


# ---- espace aérien

def _par_jour_releves(lignes: list[dict], releves_fichier: str, reg: Path, garder) -> list[tuple[str, float]]:
    """Moyenne par jour des comptes par relevé (relevés réussis à zéro compris)."""
    par_releve: dict[str, float] = {}
    for r in lignes:
        if garder(r):
            par_releve[r["releve"]] = par_releve.get(r["releve"], 0.0) + float(r["appareils"] or 0)
    f = reg / releves_fichier
    tous = set(f.read_text(encoding="utf-8").split()) if f.exists() else {r["releve"] for r in lignes}
    jours: dict[str, list[float]] = {}
    for rel in tous:
        jours.setdefault(rel[:10], []).append(par_releve.get(rel, 0.0))
    return sorted((j, sum(v) / len(v)) for j, v in jours.items())


def avions_al(reg: Path, pays: str = TOUS) -> list[tuple[str, float]]:
    """Avions militaires visibles selon airplanes.live (contrôle de couverture d'adsb.fi), moyenne par jour."""
    return _par_jour_releves(ad._csv(reg, "militaires-airplaneslive.csv"), "airplaneslive-releves.txt", reg,
                             lambda r: pays == TOUS or r["pays"] == pays)


def urgences(reg: Path, code: str = "7700", pays: str = TOUS) -> list[tuple[str, float]]:
    """Aéronefs affichant un code d'urgence (7700 urgence, 7600 panne radio, 7500 détournement), moyenne par jour."""
    return _par_jour_releves(ad._csv(reg, "urgences-airplaneslive.csv"), "airplaneslive-releves.txt", reg,
                             lambda r: r["code"] == code and (pays == TOUS or r["pays"] == pays))


def avions(reg: Path, pays: str = TOUS) -> list[tuple[str, float]]:
    """Avions militaires visibles (adsb.fi), moyenne par jour des relevés ; pays ISO2, « mer », ou tous (somme)."""
    par_releve: dict[str, float] = {}
    for r in ad._csv(reg, "militaires-adsbfi.csv"):
        if pays == TOUS or r["pays"] == pays:
            par_releve[r["releve"]] = par_releve.get(r["releve"], 0.0) + float(r["appareils"] or 0)
    tous_releves = {r["releve"] for r in ad._csv(reg, "militaires-adsbfi.csv")}
    par_jour: dict[str, list[float]] = {}
    for rel in tous_releves:                         # un relevé sans ce pays compte 0
        par_jour.setdefault(_jour(rel), []).append(par_releve.get(rel, 0.0))
    return sorted((j, round(sum(v) / len(v), 3)) for j, v in par_jour.items() if j)


TFR_RECUL = 30


def tfr(reg: Path, type_: str = TOUS) -> list[tuple[str, float]]:
    """Interdictions temporaires de survol de la FAA créées par jour (date de création) ; type SECURITY, SPECIAL, VIP,
    HAZARDS, « SPACE OPERATIONS »… ou tous. La liste de la FAA ne montre que les interdictions ENCORE actives : avant
    notre premier relevé, les comptes sont biaisés (seules les survivantes y figurent). La série commence donc
    TFR_RECUL jours avant le premier relevé, et le biais reste à garder en tête sur ce premier mois."""
    lignes = _jsonl(reg, "faa-tfr.jsonl")
    vus = [_jour(x.get("vu_le")) for x in lignes if _jour(x.get("vu_le"))]
    if not vus:
        return []
    debut = (date.fromisoformat(min(vus)) - timedelta(days=TFR_RECUL)).isoformat()
    c = Counter(j for x in lignes if (type_ == TOUS or (x.get("type") or "").upper() == type_.upper())
                for j in [_jour(x.get("cree_le"))] if j and j >= debut)
    return _quotidien(c, debut, max(max(vus), max(c) if c else debut))


def violations(reg: Path, pays: str = TOUS, gravite: str = TOUS) -> list[tuple[str, float]]:
    """Incidents recensés par ViolationsWatch par jour ; pays (nom anglais) et gravité (Critical, High, Medium…)."""
    lignes = ad._csv(reg, "violationswatch-comptes.csv")
    c: Counter = Counter()
    for r in lignes:
        if (pays == TOUS or r["pays"] == pays) and (gravite == TOUS or r["gravite"] == gravite):
            c[r["jour"]] += float(r["incidents"] or 0)
    jours = [r["jour"] for r in lignes]
    return _quotidien(c, min(jours), max(jours)) if jours else []


# ---- internet

def radar(reg: Path, pays: str = TOUS, cause: str = TOUS) -> list[tuple[str, float]]:
    """Coupures d'internet en cours par jour (Cloudflare Radar) ; pays ISO2 ; cause GOVERNMENT_DIRECTED, CABLE_CUT,
    POWER_OUTAGE… Plage : depuis le début de la couverture (radar-couverture.txt) jusqu'à la dernière coupure."""
    lignes = ad._csv(reg, "radar-coupures.csv")
    f = reg / "radar-couverture.txt"
    debut = f.read_text(encoding="utf-8").split()[0] if f.exists() and f.read_text(encoding="utf-8").strip() else None
    c: Counter = Counter()
    fin_max = None
    for r in lignes:
        d0, d1 = _jour(r["debut"]), _jour(r["fin"]) or _jour(r["debut"])
        if not d0:
            continue
        fin_max = max(fin_max or d1, d1)
        if (pays == TOUS or r["pays"] == pays) and (cause == TOUS or r["cause"] == cause):
            d = date.fromisoformat(d0)
            while d <= date.fromisoformat(d1):
                c[d.isoformat()] += 1
                d += timedelta(days=1)
    if not lignes:
        return []
    return _quotidien(c, debut or min(_jour(r["debut"]) for r in lignes if _jour(r["debut"])), fin_max)


def certificats(reg: Path, domaine: str = TOUS) -> list[tuple[str, float]]:
    """Nouveaux noms de certificats émis par jour (Cert Spotter), par domaine suivi (laboratoires d'IA) ou tous."""
    c = Counter(_jour(x.get("vu_le")) for x in _jsonl(reg, "certificats.jsonl") if domaine == TOUS or x.get("domaine") == domaine)
    c.pop(None, None)
    return _quotidien(c)


# ---- institutions américaines

def federal_register(reg: Path, type_: str = TOUS, agence: str = TOUS) -> list[tuple[str, float]]:
    """Textes déposés en inspection publique au Federal Register par jour de dépôt ; type (Rule, « Proposed Rule »,
    Notice, « Presidential Document »…) ; agence : fragment du nom (insensible à la casse)."""
    c = Counter(_jour(x.get("depose_le")) for x in _jsonl(reg, "federal-register.jsonl")
                if (type_ == TOUS or (x.get("type") or "").lower() == type_.lower())
                and (agence == TOUS or any(agence.lower() in (a or "").lower() for a in x.get("agences") or [])))
    c.pop(None, None)
    return _quotidien(c)


def congres(reg: Path, quoi: str = "reunions", chambre: str = TOUS) -> list[tuple[str, float]]:
    """Congrès des États-Unis : « reunions » (réunions de commission par date prévue ; chambre House ou Senate) ou
    « nominations » (nominations reçues par jour). Comptes seulement, aucun nom lu."""
    if quoi == "nominations":
        c = Counter(_jour(x.get("recue_le")) for x in _jsonl(reg, "congres-nominations.jsonl"))
    else:
        c = Counter(_jour(x.get("date")) for x in _jsonl(reg, "congres-reunions.jsonl")
                    if chambre == TOUS or (x.get("chambre") or "").lower() == chambre.lower())
    c.pop(None, None)
    return _quotidien(c)


def tribunaux(reg: Path, tribunal: str = TOUS) -> list[tuple[str, float]]:
    """Dossiers déposés par jour (CourtListener) ; tribunal scotus, cadc… Comptes seulement, les parties ne sont pas lues."""
    c = Counter(_jour(x.get("depot")) for x in _jsonl(reg, "tribunaux-dossiers.jsonl") if tribunal == TOUS or x.get("tribunal") == tribunal)
    c.pop(None, None)
    return _quotidien(c)


# ---- calendriers

def _aujourdhui() -> date:
    return datetime.utcnow().date()


def elections(reg: Path, pays: str) -> list[tuple[str, float]]:
    """Jours avant la prochaine élection nationale ou locale connue (Wikidata) d'un pays ISO2, du premier relevé au
    jour de la dernière élection connue."""
    dates = [r["date"] for r in ad._csv(reg, "elections.csv") if r["pays"] == pays and _jour(r["date"])]
    tout = [r["date"] for r in ad._csv(reg, "elections.csv") if _jour(r["date"])]
    if not dates or not tout:
        return []
    return _jours_avant(dates, min(tout), max(dates))


def memoire(reg: Path, pays: str) -> list[tuple[str, float]]:
    """Jours avant la prochaine date de mémoire d'un pays (anniversaires annuels, dates-memoire.csv), sur les deux ans
    écoulés et l'année à venir."""
    mj = [r["mois_jour"] for r in ad._csv(reg, "dates-memoire.csv") if r["pays"] == pays]
    if not mj:
        return []
    auj = _aujourdhui()
    echeances = []
    for an in range(auj.year - 2, auj.year + 2):
        for x in mj:
            try:
                echeances.append(date(an, int(x[:2]), int(x[3:5])).isoformat())
            except ValueError:
                pass
    return _jours_avant(echeances, date(auj.year - 2, 1, 1).isoformat(), (auj + timedelta(days=365)).isoformat())


def feries_chine(reg: Path) -> list[tuple[str, float]]:
    """1 pendant un congé public chinois (dates officielles de jours-feries-chine.csv), 0 sinon, sur l'année couverte."""
    lignes = ad._csv(reg, "jours-feries-chine.csv")
    if not lignes:
        return []
    c: Counter = Counter()
    for r in lignes:
        d = date.fromisoformat(r["debut"])
        while d <= date.fromisoformat(r["fin"]):
            c[d.isoformat()] = 1
            d += timedelta(days=1)
    an = min(r["debut"] for r in lignes)[:4]
    return _quotidien(c, f"{an}-01-01", f"{max(r['fin'] for r in lignes)[:4]}-12-31")


def publications_nbs(reg: Path, publication: str = TOUS) -> list[tuple[str, float]]:
    """Publications réellement parues du Bureau national des statistiques chinois, par jour (ipc, pmi, pib…)."""
    c = Counter(_jour(r["jour"]) for r in ad._csv(reg, "publications-nbs.csv") if publication == TOUS or r["publication"] == publication)
    c.pop(None, None)
    return _quotidien(c)


def calendrier_nbs(reg: Path, publication: str = TOUS) -> list[tuple[str, float]]:
    """Jours avant la prochaine publication PRÉVUE du Bureau des statistiques chinois (calendrier officiel)."""
    dates = [r["date_prevue"] for r in ad._csv(reg, "calendrier-nbs.csv")
             if (publication == TOUS or r["publication"] == publication) and _jour(r["date_prevue"])]
    if not dates:
        return []
    return _jours_avant(dates, f"{min(dates)[:4]}-01-01", max(dates))


ad.ADAPTATEURS.update({
    "avions": avions, "tfr": tfr, "violations": violations, "radar": radar, "certificats": certificats,
    "federal_register": federal_register, "congres": congres, "tribunaux": tribunaux, "elections": elections,
    "memoire": memoire, "feries_chine": feries_chine, "publications_nbs": publications_nbs, "calendrier_nbs": calendrier_nbs,
    "avions_al": avions_al, "urgences": urgences,
})
