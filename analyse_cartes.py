"""Analyse des cartes lues (UCDP) : l'état avant, et l'état du mois — bot 0.10.471 (0.10.472 : détail du mois,
manifestations politiques violentes, déclenchements), hors cadre.

Décision de l'auteur, 2026-11-23, 7 h 51 - 8 h 00 : analyser les cartes dans le temps (calibrer la lecture du bot et
mettre la carte à jour). Description seulement, aucune prévision envoyée nulle part.

À partir de registre/cartes/ucdp-pays-mois.csv :
- chaque pays-mois reçoit un ÉTAT selon le nombre de morts (meilleure estimation de l'UCDP) : calme (0), bas (1-24),
  moyen (25-999), haut (1 000 et plus). Seuils de lecture choisis par Claude, acceptés par défaut (25 reprend le seuil
  annuel de l'UCDP pour un conflit armé, appliqué ici au mois) ;
- les ENCHAÎNEMENTS d'un mois au suivant sur l'historique 1989-2025 (matrice de transition), et la durée des épisodes
  d'au moins 25 morts par mois ;
- l'ÉTAT DU MOIS de chaque pays (dernier mois publié), ses 13 derniers mois, et, d'après la matrice, la probabilité
  de chaque état le mois suivant (taux de départ, pas une prévision propre au pays).
Les pays présents sont ceux où l'UCDP a relevé au moins un événement depuis 1989 ; un mois sans événement compte calme.
Écrit registre/cartes/ucdp-etats.json.
"""
from __future__ import annotations

import csv
import json
import os
import statistics as st
import sys
from pathlib import Path

REG = Path(os.environ.get("ALPHABET_REGISTRE", "registre")) / "cartes"
SOURCE = REG / "ucdp-pays-mois.csv"
SORTIE = REG / "ucdp-etats.json"
ETATS = ["calme", "bas", "moyen", "haut"]
SEUILS = "calme 0 ; bas 1-24 ; moyen 25-999 ; haut 1 000 et plus (morts par mois, meilleure estimation)"
FIN_HISTORIQUE = "2025-12"


def etat(morts: float) -> int:
    return 0 if morts <= 0 else 1 if morts < 25 else 2 if morts < 1000 else 3


def mois_suivant(m: str) -> str:
    a, b = int(m[:4]), int(m[5:7])
    return f"{a + (b == 12)}-{(b % 12) + 1:02d}"


def suite_mois(m0: str, m1: str) -> list[str]:
    out, m = [], m0
    while m <= m1:
        out.append(m)
        m = mois_suivant(m)
    return out


TYPES = {"1": "étatique", "2": "non étatique", "3": "contre des civils"}


def detail_mois(r: dict | None) -> dict:
    """0.10.472 : matière déjà téléchargée — morts par type de violence, morts civiles, régions touchées, acteurs."""
    if not r:
        return {}
    out = {}
    par_type = {TYPES[k]: float(r[f"somme_categorie_{k}"]) for k in TYPES if r.get(f"somme_categorie_{k}") not in (None, "")}
    if par_type:
        out["par_type"] = par_type
    if r.get("morts_civils") not in (None, ""):
        out["morts_civils"] = float(r["morts_civils"])
    if r.get("distincts_regions") not in (None, ""):
        out["regions"] = int(r["distincts_regions"])
    if r.get("principaux"):
        out["acteurs"] = [a for a in r["principaux"].split(" ; ") if a and a.lower() != "civilians"]
    return out


def analyser_vpp(lignes: list[dict]) -> dict:
    """Manifestations politiques violentes (VPP GED) : par pays et par année, événements et morts ; dernière année."""
    par = {}
    for r in lignes:
        iso = r["iso3"] or r["pays_source"]
        a = r["mois"][:4]
        d = par.setdefault(iso, {"nom": r["pays_source"], "annees": {}})
        x = d["annees"].setdefault(a, [0, 0.0])
        x[0] += int(r["evenements"] or 0)
        x[1] += float(r["somme"] or 0)
    annees = sorted({a for d in par.values() for a in d["annees"]})
    if not annees:
        return {}
    der = annees[-1]
    pays = [{"iso3": iso, "nom": d["nom"], "evenements": d["annees"].get(der, [0, 0])[0],
             "morts": d["annees"].get(der, [0, 0.0])[1],
             "serie_evenements": [d["annees"].get(a, [0, 0])[0] for a in annees]}
            for iso, d in par.items()]
    pays = [p for p in pays if p["evenements"] > 0]
    pays.sort(key=lambda p: -p["evenements"])
    return {"annees": [annees[0], der], "derniere_annee": der, "pays_actifs": len(pays), "pays": pays[:30],
            "par_pays": {iso: d["annees"].get(der, [0, 0])[0] for iso, d in par.items()}}


def analyser_onset(lignes: list[dict]) -> dict:
    """Déclenchements (Onset, niveau pays) : dernier déclenchement de chaque pays, ceux des dernières années, taux annuel."""
    if not lignes:
        return {}
    cols = [c for c in lignes[0] if c.endswith("_reprise_1") or c.endswith("_nouveau")]
    annees = sorted({r["annee"] for r in lignes})
    der = annees[-1]
    dernier, recents, n_obs, n_dec = {}, [], 0, 0
    for r in lignes:
        iso = r["iso3"] or r["pays_source"]
        n_obs += 1
        types = [c.split("_reprise")[0].split("_nouveau")[0] for c in cols if float(r.get(c) or 0) > 0]
        types = sorted(set(types))
        if not types:
            continue
        n_dec += 1
        if r["annee"] >= dernier.get(iso, {}).get("annee", ""):
            dernier[iso] = {"annee": r["annee"], "types": types, "nom": r["pays_source"]}
        if r["annee"] > str(int(der) - 5):
            recents.append({"iso3": iso, "nom": r["pays_source"], "annee": r["annee"], "types": types})
    recents.sort(key=lambda x: (x["annee"], x["nom"]), reverse=True)
    return {"annees": [annees[0], der], "derniere_annee": der, "taux_annuel": round(n_dec / n_obs, 4) if n_obs else 0,
            "recents": recents, "dernier_par_pays": dernier,
            "definition": "année qui ouvre un conflit nouveau ou une reprise après plus d'un an sans conflit actif "
                          "(au moins 25 morts au combat dans l'année)"}


def analyser(lignes: list[dict]) -> dict:
    morts, noms, detail = {}, {}, {}
    for r in lignes:
        iso = r["iso3"] or r["pays_source"]
        morts.setdefault(iso, {})[r["mois"]] = float(r["somme"] or 0)
        noms[iso] = r["pays_source"]
        detail.setdefault(iso, {})[r["mois"]] = r
    tous = sorted({r["mois"] for r in lignes})
    if not tous:
        return {}
    hist = suite_mois(tous[0], min(FIN_HISTORIQUE, tous[-1]))
    mat = [[0] * 4 for _ in range(4)]
    durees = []
    for iso, s in morts.items():
        seq = [etat(s.get(m, 0)) for m in hist]
        for a, b in zip(seq, seq[1:]):
            mat[a][b] += 1
        k = 0
        for e in seq:
            if e >= 2:
                k += 1
            elif k:
                durees.append(k)
                k = 0
        if k:
            durees.append(k)
    proba = [[round(c / sum(l), 4) if sum(l) else 0 for c in l] for l in mat]
    dernier = tous[-1]
    recents = suite_mois(max(tous[0], suite_mois(tous[0], dernier)[-13]), dernier)
    pays = []
    for iso, s in morts.items():
        serie = [s.get(m, 0) for m in recents]
        e = etat(serie[-1])
        mediane = st.median(serie[:-1]) if len(serie) > 1 else 0
        pays.append({"iso3": iso, "nom": noms[iso], "etat": ETATS[e], "morts_mois": serie[-1], "serie": serie,
                     "mediane_12": mediane, "proba_mois_suivant": dict(zip(ETATS, proba[e])),
                     **detail_mois(detail[iso].get(recents[-1]))})
    pays.sort(key=lambda p: -p["morts_mois"])
    return {"seuils": SEUILS, "historique": [hist[0], hist[-1]], "dernier_mois": dernier, "mois_recents": recents,
            "transitions": {"etats": ETATS, "comptes": mat, "probabilites": proba},
            "episodes_moyen_ou_plus": {"nombre": len(durees), "duree_mediane_mois": st.median(durees) if durees else 0,
                                       "duree_q90_mois": sorted(durees)[int(.9 * len(durees))] if durees else 0},
            "pays": pays}


def principal() -> int:
    if not SOURCE.exists():
        print("::warning::analyse des cartes : pas de registre UCDP ; rien à faire.")
        return 0
    a = analyser(list(csv.DictReader(SOURCE.open(encoding="utf-8"))))
    fv, fo = REG / "ucdp-vpp-pays-mois.csv", REG / "ucdp-onset-pays-annee.csv"
    if fv.exists():
        a["vpp"] = analyser_vpp(list(csv.DictReader(fv.open(encoding="utf-8"))))
    if fo.exists():
        a["declenchements"] = analyser_onset(list(csv.DictReader(fo.open(encoding="utf-8"))))
        for p_ in a["pays"]:
            d = a["declenchements"]["dernier_par_pays"].get(p_["iso3"])
            if d:
                p_["dernier_declenchement"] = d
    if a.get("vpp"):
        for p_ in a["pays"]:
            p_["vpp_derniere_annee"] = a["vpp"]["par_pays"].get(p_["iso3"], 0)
    SORTIE.write_text(json.dumps(a, ensure_ascii=False, indent=1), encoding="utf-8")
    p = a["transitions"]["probabilites"]
    print(f"analyse UCDP : historique {a['historique']}, dernier mois {a['dernier_mois']}, {len(a['pays'])} pays ; "
          f"persistance calme {p[0][0]}, bas {p[1][1]}, moyen {p[2][2]}, haut {p[3][3]}")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
