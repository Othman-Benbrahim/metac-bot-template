"""Calendrier des échéances connues (décision de l'auteur, 2026-11-26, 16 h 54 : « on peut le faire maintenant »).

Complète la veille anticipée (anticipation.py) : une partie des questions naît d'un CALENDRIER plutôt que d'une montée
dans l'actualité (élection prévue, réunion de la Fed, publication statistique). Sources déjà au dépôt, aucune nouvelle :
registre/elections.csv (élections, Wikidata), ecosystemes/fomc-reunions.csv (Fed), registre/calendrier-nbs.csv
(publications du Bureau national chinois des statistiques).

Écrit registre/anticipation/calendrier-<jour>.md (échéances des 45 jours à venir) ; `mots(…)` donne les mots-clés d'une
échéance pour la mesure (une question est « au calendrier » si un de ses mots y figure).
"""
from __future__ import annotations

import csv
from datetime import date, timedelta
from pathlib import Path

ICI = Path(__file__).resolve().parent
NBS = {"ipc": "China CPI inflation", "ipp": "China PPI producer prices", "pib": "China GDP growth"}


def echeances(debut: date, jours: int = 45) -> list[dict]:
    fin = (debut + timedelta(days=jours)).isoformat()
    d0 = debut.isoformat()
    out = []
    f = ICI / "registre" / "elections.csv"
    if f.exists():
        for r in csv.DictReader(f.open(encoding="utf-8")):
            if d0 <= r["date"] <= fin:
                out.append({"date": r["date"], "type": "élection", "nom": r["nom"], "mots": [r["nom"]]})
    f = ICI / "ecosystemes" / "fomc-reunions.csv"
    if f.exists():
        for r in csv.DictReader(f.open(encoding="utf-8")):
            if d0 <= r["fin"] <= fin:
                out.append({"date": r["fin"], "type": "banque centrale", "nom": "réunion du FOMC (Réserve fédérale)",
                            "mots": ["Federal Reserve", "Fed", "FOMC", "interest rate", "federal funds"]})
    f = ICI / "registre" / "calendrier-nbs.csv"
    if f.exists():
        for r in csv.DictReader(f.open(encoding="utf-8")):
            if d0 <= r["date_prevue"] <= fin:
                out.append({"date": r["date_prevue"], "type": "statistique", "nom": NBS.get(r["publication"], r["publication"]),
                            "mots": ["China", NBS.get(r["publication"], "")]})
    f = ICI / "registre" / "calendrier-consilium.csv"            # 2026-11-26 : Conseil européen et Conseil de l'UE
    if f.exists():
        for r in csv.DictReader(f.open(encoding="utf-8")):
            if d0 <= r["date"] <= fin:
                out.append({"date": r["date"], "type": "Conseil de l'UE", "nom": r["reunion"],
                            "mots": ["European Council", "Council of the EU", "EU leaders", "EU summit", "Council of the European Union"]})
    return sorted(out, key=lambda e: e["date"])


def ecrire(jour: date) -> list[dict]:
    E = echeances(jour)
    d = ICI / "registre" / "anticipation"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"calendrier-{jour.isoformat()}.md").write_text(
        f"# Échéances connues des 45 jours à venir ({jour.isoformat()})\n\n| date | type | échéance |\n|---|---|---|\n"
        + "".join(f"| {e['date']} | {e['type']} | {e['nom']} |\n" for e in E), encoding="utf-8")
    return E


def au_calendrier(titre: str, jour: date) -> list[str]:
    """Échéances des 45 jours suivant `jour` dont un mot-clé figure dans le titre (comparaison sans casse)."""
    t = titre.lower()
    out = []
    for e in echeances(jour):
        for m in e["mots"]:
            m = m.lower().strip()
            if not m:
                continue
            # pour une élection : le pays ou le nom distinctif (mots de plus de 4 lettres hors termes génériques)
            if e["type"] == "élection":
                cles = [w for w in m.replace("–", " ").split() if len(w) > 4 and w not in
                        ("election", "elections", "general", "presidential", "parliamentary", "legislative", "local",
                         "regional", "municipal", "referendum", "state", "round", "council", "councils", "county", "city", "mayor",
                         "magistrate", "national", "assembly", "federal", "senate", "house", "initiative", "union",
                         "european", "parliament", "elections")]
                if any(w in t for w in cles):
                    out.append(e["nom"])
                    break
            elif m in t:
                out.append(e["nom"])
                break
    return sorted(set(out))


if __name__ == "__main__":
    E = ecrire(date.today())
    print(f"{len(E)} échéances dans les 45 jours")
