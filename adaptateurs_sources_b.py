"""Adaptateurs des sources déjà collectées mais dormantes, lot B (0.10.323) : GDELT (hostilités, manifestations,
paires d'États, sanctions chinoises), UCDP, voisins, ConflictForecast, prix alimentaires, ACAPS, Telegram (comptes
agrégés), récit russe, RSS, routines officielles, Wikipédia.

Chaque fonction (reg, *paramètres) rend une liste triée de (AAAA-MM-JJ, valeur), à la fréquence de la donnée. Pour un
compte d'événements, les jours couverts par la collecte sans événement valent 0 (liste des jours couverts tirée des
fichiers *-jours.txt quand ils existent, sinon de la plage du fichier). Lecture seule, aucun réseau, aucune personne :
uniquement des comptes agrégés. Inscription dans adaptateurs.ADAPTATEURS en bas du module.
"""
from __future__ import annotations

import csv
import gzip
import json
from datetime import date, timedelta
from pathlib import Path

import adaptateurs as _ad


def _lignes(reg: Path, nom: str) -> list[dict]:
    f = reg / nom
    if not f.exists():
        return []
    ouvrir = gzip.open if nom.endswith(".gz") else open
    with ouvrir(f, "rt", encoding="utf-8") as h:
        return list(csv.DictReader(h))


def _jours_couverts(reg: Path, nom: str) -> list[str]:
    f = reg / nom
    return sorted({l.strip() for l in f.read_text(encoding="utf-8").splitlines() if l.strip()}) if f.exists() else []


def _plage(jours: list[str]) -> list[str]:
    if not jours:
        return []
    d, fin, out = date.fromisoformat(min(jours)), date.fromisoformat(max(jours)), []
    while d <= fin:
        out.append(d.isoformat())
        d += timedelta(days=1)
    return out


def _avec_zeros(comptes: dict[str, float], couverts: list[str]) -> list[tuple[str, float]]:
    jours = couverts or _plage(list(comptes))
    return [(j, float(comptes.get(j, 0.0))) for j in sorted(set(jours) | set(comptes))]


def _f(x) -> float:
    try:
        return float(x)
    except (TypeError, ValueError):
        return 0.0


# ---- GDELT ----
def hostilites(reg: Path, pays: str, colonne: str = "total") -> list[tuple[str, float]]:
    """Actes hostiles d'acteurs russes dans un pays (ISO2) par jour : agressions, combats, violence_masse ou total."""
    c: dict[str, float] = {}
    for r in _lignes(reg, "gdelt-hostilites-ru.csv"):
        if r["pays"] == pays:
            v = sum(_f(r[k]) for k in ("agressions", "combats", "violence_masse")) if colonne == "total" else _f(r[colonne])
            c[r["jour"]] = c.get(r["jour"], 0.0) + v
    return _avec_zeros(c, _jours_couverts(reg, "gdelt-hostilites-jours.txt"))


def manifestations(reg: Path, pays: str, colonne: str = "manifestations") -> list[tuple[str, float]]:
    """Manifestations (ou émeutes, articles) par jour dans un pays (ISO2), GDELT."""
    c = {r["jour"]: _f(r[colonne]) for r in _lignes(reg, "gdelt-manifestations.csv") if r["pays"] == pays}
    return _avec_zeros(c, _jours_couverts(reg, "gdelt-jours.txt"))


def paire(reg: Path, a: str, b: str, colonne: str = "force") -> list[tuple[str, float]]:
    """Gestes de A envers B par jour (ISO2) : démonstrations de force (force) ou coopération militaire (coop_mil)."""
    c = {r["jour"]: _f(r[colonne]) for r in _lignes(reg, "gdelt-paires-jour.csv") if r["a"] == a and r["b"] == b}
    return _avec_zeros(c, _jours_couverts(reg, "gdelt-paires-jours.txt"))


def paire_mois(reg: Path, a: str, b: str, colonne: str = "conflit") -> list[tuple[str, float]]:
    """Événements (ou événements conflictuels) par mois entre deux pays (ISO2, paire non orientée), daté au 1er du mois."""
    x, y = sorted((a, b))
    return sorted((r["mois"] + "-01", _f(r[colonne])) for r in _lignes(reg, "gdelt-paires-mois.csv") if r["a"] == x and r["b"] == y)


def sanctions_chine(reg: Path, pays: str) -> list[tuple[str, float]]:
    """Sanctions, embargos, boycotts d'acteurs chinois visant un pays (ISO2), par jour (GDELT, CAMEO 163)."""
    c: dict[str, float] = {}
    for r in _lignes(reg, "gdelt-chine-sanctions.csv"):
        if r["pays"] == pays:
            c[r["jour"]] = c.get(r["jour"], 0.0) + _f(r["evenements"])
    return _avec_zeros(c, _jours_couverts(reg, "gdelt-chine-jours.txt"))


# ---- UCDP, voisins, ConflictForecast ----
def ucdp(reg: Path, pays: str, colonne: str = "morts") -> list[tuple[str, float]]:
    """Morts (ou événements) de violence organisée par jour dans un pays (nom anglais UCDP, ex. « Sudan »)."""
    toutes = _lignes(reg, "ucdp-cellules.csv.gz")
    c: dict[str, float] = {}
    for r in toutes:
        if r["pays"] == pays:
            c[r["jour"]] = c.get(r["jour"], 0.0) + _f(r[colonne])
    return _avec_zeros(c, _plage([r["jour"] for r in toutes]) if c else [])


def voisins(reg: Path, pays: str, source: str = "manifestations") -> list[tuple[str, float]]:
    """Somme, chez les voisins terrestres d'un pays (ISO2), des manifestations (ou hostilités russes) par jour."""
    f = reg / "voisins.json"
    vs = json.loads(f.read_text(encoding="utf-8")).get(pays, []) if f.exists() else []
    lire = hostilites if source == "hostilites" else manifestations
    total: dict[str, float] = {}
    for v in vs:
        for j, x in lire(reg, v):
            total[j] = total.get(j, 0.0) + x
    return sorted(total.items())


def conflictforecast(reg: Path, iso3: str, cible: str = "anyviolence", horizon: str = "12") -> list[tuple[str, float]]:
    """Probabilité publiée par ConflictForecast (p_all, en %) pour un pays (ISO3), datée au mois de la version."""
    out = {}
    for r in _lignes(reg, "conflictforecast.csv"):
        if r["isocode"] == iso3 and r["cible"] == cible and r["horizon"] == horizon and r["p_all"] not in ("", None):
            out[r["version"][:7] + "-01"] = _f(r["p_all"])
    return sorted(out.items())


# ---- prix alimentaires, ACAPS ----
def prix_alimentaires(reg: Path, pays: str, colonne: str = "inflation") -> list[tuple[str, float]]:
    """Inflation alimentaire (ou prix de clôture de l'indice) par mois pour un pays (ISO2), dernière version publiée."""
    par_mois: dict[str, tuple[str, float]] = {}
    for r in _lignes(reg, "prix-alimentaires.csv"):
        if r["pays"] == pays and r[colonne] not in ("", None):
            m = r["mois"]
            if m not in par_mois or r["version"] >= par_mois[m][0]:
                par_mois[m] = (r["version"], _f(r[colonne]))
    return sorted((m + "-01", v) for m, (_, v) in par_mois.items())


def acaps(reg: Path, pays: str) -> list[tuple[str, float]]:
    """Indice de sévérité des crises ACAPS (INFORM, 0 à 5) d'un pays (ISO2) : maximum des crises du pays par relevé."""
    out: dict[str, float] = {}
    for r in _lignes(reg, "acaps-inform.csv"):
        if r["pays"] == pays and r["indice"] not in ("", None):
            out[r["instantane"]] = max(out.get(r["instantane"], 0.0), _f(r["indice"]))
    return sorted(out.items())


def acaps_risques(reg: Path, pays: str) -> list[tuple[str, float]]:
    """Nombre de risques ACAPS ouverts pour un pays (ISO2) à chaque date de mise à jour d'un de ses risques (cumul des
    risques entrés jusqu'à cette date, hors risques marqués « matérialisés » ou « non matérialisés » à cette date)."""
    rs = [r for r in _lignes(reg, "acaps-risques.csv") if r["pays"] == pays]
    dates = sorted({r["date_entered"] for r in rs} | {r["last_risk_update"] for r in rs if r["last_risk_update"]})
    out = []
    for d in dates:
        n = sum(1 for r in rs if r["date_entered"] <= d and not (r["last_risk_update"] and r["last_risk_update"] <= d
                                                                  and r["status"].lower().endswith("materialised")))
        out.append((d, float(n)))
    return out


# ---- Telegram (comptes agrégés), récit russe, RSS, routines ----
def telegram(reg: Path, chaine: str = "tout") -> list[tuple[str, float]]:
    """Messages publiés par jour sur les chaînes publiques suivies (toutes, ou une chaîne publique d'institution ou de
    média) ; aucun contenu gardé, seulement le compte."""
    c: dict[str, float] = {}
    for r in _lignes(reg, "telegram-messages.csv"):
        if chaine == "tout" or r["chaine"].lower() == chaine.lower():
            j = (r.get("heure") or "")[:10]
            if j:
                c[j] = c.get(j, 0.0) + 1.0
    return _avec_zeros(c, [])


def recit_russe(reg: Path, pays: str, colonne: str = "articles") -> list[tuple[str, float]]:
    """Articles des médias d'État russes surveillés mentionnant un pays (ISO2), par jour (ou « alibi »)."""
    toutes = _lignes(reg, "recit-russe.csv")
    c = {r["jour"]: _f(r[colonne]) for r in toutes if r["pays"] == pays}
    if not c:                                     # pays hors de la liste surveillée : pas de série (et non des zéros)
        return []
    return _avec_zeros(c, sorted({r["jour"] for r in toutes}))


# 0.10.455 : familles en ombre exclues du total « tout », qui garde sa composition d'avant (les variantes _large,
# _grasland, _fusion le sont aussi, par le préfixe).
HORS_TOUT = ("sp_energie", "matieres_presse", "monnaie", "religion", "biodiversite", "defense", "sante_afrique", "crime",
             "genre", "psyche", "asie", "transport", "tech", "minerais", "inegalites", "analyse", "afrique",   # 0.10.456
             "surveillance", "geopolitique_europe", "moyen_orient", "chine", "russie", "amerique_latine", "inde",
             "voix_etat",   # 2026-11-25
             "primaires",   # 2026-11-27
             "laboratoires_ia")   # 2026-11-26


def rss(reg: Path, pays: str, famille: str = "tout") -> list[tuple[str, float]]:
    """Articles des flux RSS suivis (institutions, santé, vérification…) citant un pays (ISO2), par jour."""
    c: dict[str, float] = {}
    for r in _lignes(reg, "rss-comptes.csv"):
        # 0.10.388 : « tout » garde sa composition d'avant (sp_energie en est exclue)
        if r["pays"] == pays and ((famille == "tout" and not r["famille"].startswith(HORS_TOUT)) or r["famille"] == famille):
            c[r["jour"]] = c.get(r["jour"], 0.0) + _f(r["articles"])
    return sorted(c.items())


def rss_villes(reg: Path, pays: str, famille: str = "tout") -> list[tuple[str, float]]:
    """2026-11-25, en ombre : articles citant un pays (ISO2) par son nom, son adjectif ou une de ses villes (GeoNames)."""
    c: dict[str, float] = {}
    for r in _lignes(reg, "rss-villes.csv"):
        if r["pays"] == pays and ((famille == "tout" and not r["famille"].startswith(HORS_TOUT)) or r["famille"] == famille):
            c[r["jour"]] = c.get(r["jour"], 0.0) + _f(r["articles"])
    return sorted(c.items())


def rss_region(reg: Path, region: str, famille: str = "tout") -> list[tuple[str, float]]:
    """Articles des flux RSS suivis rattachés à une région ou organisation (code de région du collecteur), par jour."""
    c: dict[str, float] = {}
    for r in _lignes(reg, "rss-regions.csv"):
        if r["region"] == region and ((famille == "tout" and not r["famille"].startswith(HORS_TOUT)) or r["famille"] == famille):
            c[r["jour"]] = c.get(r["jour"], 0.0) + _f(r["articles"])
    return sorted(c.items())


def routines(reg: Path, source: str) -> list[tuple[str, float]]:
    """Publications quotidiennes d'un site officiel suivi (maison_blanche, kremlin_president_en, commission_europeenne…)."""
    toutes = _lignes(reg, "routines-comptes.csv")
    c = {r["jour"]: _f(r["n"]) for r in toutes if r["source"] == source}
    return _avec_zeros(c, _plage([r["jour"] for r in toutes]) if c else [])


# ---- Wikipédia ----
def wikipedia(reg: Path, article: str) -> list[tuple[str, float]]:
    """Pages vues par jour d'un article de Wikipédia (en), relevées pour les bancs : seules les entrées dont l'article
    est l'unique article relevé sont prises, et la valeur la plus haute est gardée quand plusieurs fenêtres se recouvrent."""
    f = reg / "wikipedia-comptes.json"
    if not f.exists():
        return []
    out: dict[str, float] = {}
    for e in json.loads(f.read_text(encoding="utf-8")).values():
        if (e.get("articles") or []) == [article]:
            for j, n in (e.get("jours") or {}).items():
                out[j] = max(out.get(j, 0.0), float(n))
    return sorted(out.items())


def rss_matiere(reg: Path, matiere: str) -> list[tuple[str, float]]:
    """2026-11-25 : articles par jour dont le titre ou le résumé nomme une matière ou un sujet (collecte_rss.MATIERES),
    toutes familles lues pour ce sujet ; jours sans article comptés à zéro depuis le premier relevé."""
    toutes = _lignes(reg, "rss-matieres.csv")
    c: dict[str, float] = {}
    for r in toutes:
        if r["matiere"] == matiere:
            c[r["jour"]] = c.get(r["jour"], 0.0) + _f(r["articles"])
    return _avec_zeros(c, _plage([r["jour"] for r in toutes]) if c else [])


def rss_famille(reg: Path, famille: str) -> list[tuple[str, float]]:
    """2026-11-25 : articles nouveaux par jour d'une famille de flux (rss-familles.csv), avec ou sans pays reconnu."""
    toutes = _lignes(reg, "rss-familles.csv")
    c = {r["jour"]: _f(r["articles"]) for r in toutes if r["famille"] == famille}
    return _avec_zeros(c, _plage([r["jour"] for r in toutes if r["famille"] == famille]) if c else [])


_ad.ADAPTATEURS.update({
    "hostilites": hostilites, "manifestations": manifestations, "paire": paire, "paire_mois": paire_mois,
    "sanctions_chine": sanctions_chine, "ucdp": ucdp, "voisins": voisins, "conflictforecast": conflictforecast,
    "prix_alimentaires": prix_alimentaires, "acaps": acaps, "acaps_risques": acaps_risques, "telegram": telegram,
    "recit_russe": recit_russe, "rss": rss, "rss_villes": rss_villes, "rss_matiere": rss_matiere, "rss_famille": rss_famille, "rss_region": rss_region, "routines": routines, "wikipedia": wikipedia,
})
