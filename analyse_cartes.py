"""Analyse des cartes lues (UCDP) : l'état avant, et l'état du mois — bot 0.10.471, hors cadre.

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


def analyser(lignes: list[dict]) -> dict:
    morts, noms = {}, {}
    for r in lignes:
        iso = r["iso3"] or r["pays_source"]
        morts.setdefault(iso, {})[r["mois"]] = float(r["somme"] or 0)
        noms[iso] = r["pays_source"]
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
                     "mediane_12": mediane, "proba_mois_suivant": dict(zip(ETATS, proba[e]))})
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
    SORTIE.write_text(json.dumps(a, ensure_ascii=False, indent=1), encoding="utf-8")
    p = a["transitions"]["probabilites"]
    print(f"analyse UCDP : historique {a['historique']}, dernier mois {a['dernier_mois']}, {len(a['pays'])} pays ; "
          f"persistance calme {p[0][0]}, bas {p[1][1]}, moyen {p[2][2]}, haut {p[3][3]}")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
