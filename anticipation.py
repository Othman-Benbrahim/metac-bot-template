"""Veille anticipée des questions (décision de l'auteur, 2026-11-26, 16 h 46-16 h 50, voie 2 : prospective).

Idée de l'auteur : le biais du questionneur est régulier ; les questions naissent de l'actualité des jours précédents.
Si l'on voit monter un acteur ou un domaine, on peut préparer mécanismes et séries AVANT la question.

1. Comptes (collecte_rss) : pour chaque article nouveau du jour, les noms propres de son TITRE (suites de 1 à 3 mots à
   majuscule, hors mots vides et mois) sont comptés : registre/anticipation/entites.csv (jour, entite, articles).
   Aucun titre n'est gardé : seulement des noms et des nombres.
2. Liste du jour : entités dont les comptes des 3 derniers jours dépassent nettement leur habitude (14 jours d'avant) ;
   registre/anticipation/liste-<jour>.md.
3. Mesure : pour chaque question du tournoi journalisée, ses noms propres figuraient-ils dans une liste des 7 jours
   précédant sa date ? registre/anticipation/mesure.json (taux de réussite, et taille moyenne des listes pour juger la
   précision : une liste de mille noms « réussit » toujours).
"""
from __future__ import annotations

import csv
import json
import re
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

DOS = Path("registre") / "anticipation"
VIDES = set("""The A An And Or Of In On At To For With By From As Is Are Was Were Be Will Would Can Could May Might
Should Has Have Had Not No New How Why What When Where Who Which This That These Those It Its After Before Over Under
Amid Says Said Say Report Reports Live Update Updates Watch Video Photos Opinion Analysis Exclusive Breaking News
Le La Les Un Une Des Du De Et Ou En Au Aux Pour Par Sur Dans Avec Sans Est Sont Selon Mais Qui Que Quoi Comment
January February March April May June July August September October November December
Monday Tuesday Wednesday Thursday Friday Saturday Sunday
Janvier Février Mars Avril Mai Juin Juillet Août Septembre Octobre Novembre Décembre
Lundi Mardi Mercredi Jeudi Vendredi Samedi Dimanche""".split())
NOM = re.compile(r"\b[A-ZÀ-Ý][\w'’-]+(?:\s+(?:[A-ZÀ-Ý][\w'’-]+)){0,2}")


def noms(titre: str) -> set[str]:
    out = set()
    for m in NOM.finditer(titre or ""):
        mots = [w for w in m.group(0).split() if w not in VIDES]
        if mots and (len(mots) > 1 or len(mots[0]) > 3):
            out.add(" ".join(mots))
    return out


def ecrire_comptes(c: dict[tuple[str, str], int]) -> None:
    """Ajoute les comptes (jour, entité) du passage ; un même couple s'additionne."""
    DOS.mkdir(parents=True, exist_ok=True)
    f = DOS / "entites.csv"
    tout: dict[tuple[str, str], int] = {}
    if f.exists():
        for x in csv.DictReader(f.open(encoding="utf-8")):
            tout[(x["jour"], x["entite"])] = int(x["articles"])
    for k, v in c.items():
        tout[k] = tout.get(k, 0) + v
    lim = (date.today() - timedelta(days=120)).isoformat()
    with f.open("w", encoding="utf-8", newline="\n") as g:
        w = csv.writer(g)
        w.writerow(["jour", "entite", "articles"])
        for (j, e), v in sorted(tout.items()):
            if j >= lim:
                w.writerow([j, e, v])


def lire_comptes() -> dict[str, dict[str, int]]:
    f = DOS / "entites.csv"
    par = defaultdict(dict)
    if f.exists():
        for x in csv.DictReader(f.open(encoding="utf-8")):
            par[x["entite"]][x["jour"]] = int(x["articles"])
    return par


def liste(jour: str, par=None, n_max: int = 40) -> list[tuple[str, int, float]]:
    """Entités qui montent : comptes des 3 derniers jours contre la moyenne des 14 jours d'avant (rapport, plancher 5)."""
    par = par if par is not None else lire_comptes()
    j = date.fromisoformat(jour)
    recent = [(j - timedelta(days=i)).isoformat() for i in range(3)]
    avant = [(j - timedelta(days=i)).isoformat() for i in range(3, 17)]
    out = []
    for e, d in par.items():
        r = sum(d.get(x, 0) for x in recent)
        if r < 5:
            continue
        b = sum(d.get(x, 0) for x in avant) / 14 * 3
        out.append((e, r, round((r + 1) / (b + 1), 2)))
    out.sort(key=lambda z: (-z[2], -z[1]))
    return out[:n_max]


def ecrire_liste(jour: str) -> list:
    L = liste(jour)
    DOS.mkdir(parents=True, exist_ok=True)
    (DOS / f"liste-{jour}.md").write_text(
        f"# Acteurs et domaines qui montent ({jour})\n\n| entité | articles (3 j) | rapport à l'habitude |\n|---|---|---|\n"
        + "".join(f"| {e} | {r} | {x} |\n" for e, r, x in L), encoding="utf-8")
    return L


def mesurer() -> dict:
    """Pour chaque question du tournoi journalisée : un de ses noms propres était-il dans une liste des 7 jours d'avant ?"""
    par = lire_comptes()
    f = Path("registre") / "journal-bot.jsonl"
    R = []
    vus = set()
    for l in (f.read_text(encoding="utf-8").splitlines() if f.exists() else []):
        q = json.loads(l)
        if q.get("mode") != "tournament" or q["question_id"] in vus:
            continue
        vus.add(q["question_id"])
        j = date.fromisoformat(q["date_information"][:10])
        if not par or min(min(d) for d in par.values()) > (j - timedelta(days=17)).isoformat():
            continue                                    # pas encore assez d'historique pour cette date
        N = {n.lower() for n in noms(q["titre"])}
        listes = set()
        tailles = []
        for i in range(1, 8):
            L = liste((j - timedelta(days=i)).isoformat(), par)
            tailles.append(len(L))
            listes |= {e.lower() for e, _, _ in L}
        touche = sorted(n for n in N if any(n in e or e in n for e in listes))
        R.append({"question_id": q["question_id"], "titre": q["titre"], "jour": j.isoformat(), "noms": sorted(N),
                  "trouves": touche, "reussite": bool(touche), "taille_moyenne_listes": sum(tailles) / len(tailles)})
    res = {"questions": len(R), "reussites": sum(r["reussite"] for r in R), "lignes": R}
    DOS.mkdir(parents=True, exist_ok=True)
    (DOS / "mesure.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    return res


if __name__ == "__main__":
    j = date.today().isoformat()
    L = ecrire_liste(j)
    m = mesurer()
    print(f"liste du {j} : {len(L)} entités ; mesure : {m['reussites']}/{m['questions']} questions anticipées")
