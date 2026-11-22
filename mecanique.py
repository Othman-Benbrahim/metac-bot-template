"""La mécanique de bascule en temps réel, en OMBRE — bot 0.10.464 (étape 1 : étincelles, journal, calcul).

Décision de l'auteur, 2026-11-22, 20 h 51 - 20 h 57 : mettre en place, sur la carte et dans le bot, toute la mécanique
issue de la réflexion du jour (grammaire de bascule, seuil / tension / étincelle, cycles, rapport des forces, émetteur
et acte de langage, temps du texte, propagation, niveau de mesure, H2 signal × terrain, boucle), pour PRODUIRE des
prédictions. Rien n'entre dans les prévisions Metaculus avant qu'un score réel le justifie.

Étape 1 (ce fichier) :
- lit les manifestations GDELT par pays et par semaine (registre/gdelt-manifestations-recentes.csv, mode court de
  gdelt_bq.py ; sinon le relevé complet) ;
- repère les ÉTINCELLES de la dernière semaine complète (définitions validées par l'auteur le 22 novembre à 20 h 07) :
  part des manifestations ≥ 2 × niveau habituel (médiane des 52 semaines précédentes), après 4 semaines sous ce seuil ;
- prédit pour chacune la probabilité qu'elle PRENNE dans les 8 semaines (part ≥ 1,5 × niveau habituel au moins
  4 semaines sur 8) ;
- inscrit chaque prédiction dans un journal à AJOUT SEUL, constate les issues 8 semaines plus tard, calcule le score.

Calcul : log-cote de départ = taux observé sur 2015-2021 (31,5 % des 2 539 étincelles prennent, cas intermédiaires
compris) ; chaque MODULE de la mécanique ajoute un déplacement dans le sens fixé par l'auteur, de force w apprise sur les
issues réelles (la boucle). À l'étape 1, aucun module n'est encore branché : la prédiction est le taux de départ.
Étapes suivantes : signaux (lecteur-local, rang, acte, temps du fait), terrain (fiches, Banque mondiale), échéances.
"""
from __future__ import annotations

import csv
import json
import math
import os
import statistics as st
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

REG = Path(os.environ.get("ALPHABET_REGISTRE", "registre"))
RECENTES = REG / "gdelt-manifestations-recentes.csv"
COMPLET = REG / "gdelt-manifestations-semaines.csv"
JOURNAL = REG / "mecanique-journal.csv"
ISSUES = REG / "mecanique-issues.csv"
POIDS = REG / "mecanique-poids.json"
SCORE = REG / "mecanique-score.json"
CODES = Path("ecosystemes/codes-pays-fips.csv")
VERSION = "0.10.464"

MIN_EVENEMENTS = 200          # semaines plus petites ignorées (bruit)
FENETRE, MIN_VALIDES = 52, 40
SEUIL_ETINCELLE, SEUIL_ELEVE, CALME = 2.0, 1.5, 4
HORIZON, PREND_MIN = 8, 4
TAUX_DEPART = 0.315           # observation 2015-2021 (claude/observation-h2-terrain-… dans le projet)

COLS_JOURNAL = ["id", "inscrit_le", "pays", "iso3", "semaine", "part", "niveau_habituel", "rapport", "p_prend",
                "version", "modules"]
COLS_ISSUES = ["id", "constate_le", "prend", "semaines_elevees"]


def logit(p: float) -> float:
    return math.log(p / (1 - p))


def sigmo(x: float) -> float:
    return 1 / (1 + math.exp(-x))


def lire_series(chemin: Path) -> dict[str, list[tuple[str, float | None]]]:
    """{pays FIPS: [(semaine, part ou None)]}, triées, avec les semaines manquantes comblées (part None)."""
    brut: dict[str, dict[str, tuple[int, int]]] = {}
    for r in csv.DictReader(chemin.open(encoding="utf-8")):
        brut.setdefault(r["pays"], {})[r["semaine"]] = (int(r["evenements"]), int(r["manifs"]))
    out = {}
    for p, d in brut.items():
        s0, s1 = date.fromisoformat(min(d)), date.fromisoformat(max(d))
        l, s = [], s0
        while s <= s1:
            e, m = d.get(s.isoformat(), (0, 0))
            l.append((s.isoformat(), m / e if e >= MIN_EVENEMENTS else None))
            s += timedelta(weeks=1)
        out[p] = l
    return out


def niveau(l: list, i: int) -> float | None:
    base = [w for _, w in l[max(0, i - FENETRE):i] if w is not None]
    if len(base) < MIN_VALIDES:
        return None
    b = st.median(base)
    return b if b > 0 else None


def etincelle(l: list, i: int) -> tuple[float, float] | None:
    """(part, niveau habituel) si la semaine i est une étincelle, sinon None."""
    s, v = l[i]
    if v is None or i < FENETRE:
        return None
    b = niveau(l, i)
    if b is None or v < SEUIL_ETINCELLE * b:
        return None
    if any(w is None or w >= SEUIL_ETINCELLE * b for _, w in l[i - CALME:i]):
        return None
    return v, b


def lire_csv(chemin: Path) -> list[dict]:
    return list(csv.DictReader(chemin.open(encoding="utf-8"))) if chemin.exists() else []


def ajouter(chemin: Path, cols: list[str], lignes: list[dict]) -> None:
    """Ajout seul : on n'écrit que de nouvelles lignes à la fin ; rien d'existant n'est réécrit."""
    neuf = not chemin.exists()
    chemin.parent.mkdir(parents=True, exist_ok=True)
    with chemin.open("a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        if neuf:
            w.writeheader()
        w.writerows(lignes)


def codes_iso3() -> dict[str, str]:
    if not CODES.exists():
        return {}
    lignes = [l for l in CODES.read_text(encoding="utf-8").splitlines() if l and not l.startswith("#")]
    return {r["fips"]: r["iso3"] for r in csv.DictReader(lignes)}


def modules(pays: str, semaine: str, contexte: dict) -> dict[str, float]:
    """Les entrées des mécanismes (x_k), chacune orientée dans le sens fixé par l'auteur (+ pousse vers « prend »).
    Étape 1 : aucun module branché."""
    return {}


def predire(x: dict[str, float], poids: dict[str, float]) -> float:
    z = logit(TAUX_DEPART) + sum(poids.get(k, 0.0) * v for k, v in x.items())
    return sigmo(z)


def inscrire(series: dict, journal: list[dict], aujourd_hui: date, contexte: dict | None = None) -> list[dict]:
    """Étincelles de la DERNIÈRE semaine complète seulement (aucune semaine de la fenêtre de 8 semaines n'est connue au
    moment de la prédiction ; une semaine manquée n'est pas rattrapée, pour ne pas prédire ce qu'on voit déjà)."""
    deja = {(r["pays"], r["semaine"]) for r in journal}
    poids = json.loads(POIDS.read_text(encoding="utf-8")) if POIDS.exists() else {}
    iso = codes_iso3()
    cible = (aujourd_hui - timedelta(days=aujourd_hui.weekday()) - timedelta(weeks=1)).isoformat()
    neuves = []
    for p, l in sorted(series.items()):
        for i, (s, _) in enumerate(l):
            if s != cible or (p, s) in deja:
                continue
            e = etincelle(l, i)
            if not e:
                continue
            x = modules(p, s, contexte or {})
            neuves.append({"id": f"{p}-{s}", "inscrit_le": aujourd_hui.isoformat(), "pays": p, "iso3": iso.get(p, ""),
                           "semaine": s, "part": "%.5f" % e[0], "niveau_habituel": "%.5f" % e[1],
                           "rapport": "%.2f" % (e[0] / e[1]), "p_prend": "%.4f" % predire(x, poids),
                           "version": VERSION, "modules": json.dumps(x, ensure_ascii=False)})
    return neuves


def constater(series: dict, journal: list[dict], issues: list[dict], aujourd_hui: date) -> list[dict]:
    """Issues des étincelles dont les 8 semaines suivantes sont complètes ; une issue n'est jamais réécrite."""
    fait = {r["id"] for r in issues}
    neuves = []
    for r in journal:
        if r["id"] in fait or r["pays"] not in series:
            continue
        l = series[r["pays"]]
        idx = {s: k for k, (s, _) in enumerate(l)}
        i = idx.get(r["semaine"])
        lundi = aujourd_hui - timedelta(days=aujourd_hui.weekday())
        if i is None or i + HORIZON >= len(l) or date.fromisoformat(l[i + HORIZON][0]) + timedelta(days=7) > lundi:
            continue                                        # les 8 semaines suivantes ne sont pas toutes complètes
        b = float(r["niveau_habituel"])
        nxt = [w for _, w in l[i + 1:i + 1 + HORIZON]]
        elev = sum(1 for w in nxt if w is not None and w >= SEUIL_ELEVE * b)
        neuves.append({"id": r["id"], "constate_le": aujourd_hui.isoformat(), "prend": int(elev >= PREND_MIN),
                       "semaines_elevees": elev})
    return neuves


def score(journal: list[dict], issues: list[dict]) -> dict:
    p = {r["id"]: float(r["p_prend"]) for r in journal}
    res = [(p[r["id"]], int(r["prend"])) for r in issues if r["id"] in p]
    out = {"calcule_le": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"), "inscrites": len(journal),
           "constatees": len(res), "ouvertes": len(journal) - len(res), "taux_depart": TAUX_DEPART}
    if res:
        out["brier"] = round(sum((q - y) ** 2 for q, y in res) / len(res), 4)
        out["brier_taux_depart"] = round(sum((TAUX_DEPART - y) ** 2 for _, y in res) / len(res), 4)
        out["part_prend"] = round(sum(y for _, y in res) / len(res), 3)
    return out


def principal() -> int:
    src = RECENTES if RECENTES.exists() else COMPLET
    if not src.exists():
        print("::warning::mécanique : aucun relevé GDELT des manifestations ; rien à faire.")
        return 0
    series = lire_series(src)
    auj = date.today()
    journal = lire_csv(JOURNAL)
    neuves = inscrire(series, journal, auj)
    ajouter(JOURNAL, COLS_JOURNAL, neuves)
    journal += neuves
    issues = lire_csv(ISSUES)
    constats = constater(series, journal, issues, auj)
    ajouter(ISSUES, COLS_ISSUES, constats)
    issues += constats
    sc = score(journal, issues)
    SCORE.write_text(json.dumps(sc, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"mécanique : source {src.name} ; {len(neuves)} étincelle(s) inscrite(s), {len(constats)} issue(s) constatée(s) ; "
          f"{sc}")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
