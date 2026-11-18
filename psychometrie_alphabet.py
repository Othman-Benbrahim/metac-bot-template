"""Examen psychométrique des cartes de l'alphabet (le « comité » du bras M), bot 0.10.244.

Décision d'auteur du 2026-11-17 (21 h 15) : examiner l'alphabet comme un instrument de mesure (d'après le skill de
relecture psychométrique pgmj/psychometrics-skill, CC0) ; AUCUNE carte ne sort de l'alphabet ; chaque carte reçoit un
statut PAR TYPE DE QUESTION (démontrée, non démontrée, trompeuse), revu à chaque nouveau lot. Préenregistrement :
preenregistrements/psychometrie-alphabet.md (écrit avant que le banc n'ait rendu ses notes).

Entrée : registre/banc-jugement-alphabet.jsonl (notes de 1 à 4 des sept cartes, issue de la question).
  1. Monotonie, par carte et par type (forme) : part de « oui » des notes 3-4 moins celle des notes 1-2 (sens inversé
     pour « freins ») ; p par permutation (2 000 mélanges des notes à l'intérieur du type, graine 0), unilatéral dans
     chaque sens ; seuil 0,05 / 7 par type. Démontrée : bon sens et p < seuil ; trompeuse : mauvais sens et p < seuil ;
     sinon non démontrée (dont « trop peu » si un groupe a moins de 5 questions).
  2. Redondance : corrélation de Spearman entre cartes ; |ρ| > 0,7 signalée (les deux restent).
  3. Unidimensionnalité : part de variance de la première composante principale des sept notes (freins inversés).
  4. Invariance : les tests 1 faits par type (élection, échéance, seuil, justice, autre) et pour tout.
  5. Fiabilité (option --fiabilite N, coût ≈ 0,01 $ par question) : le même modèle renote N questions ; accord par carte
     (kappa pondéré quadratique) ; une carte sous 0,4 est « peu fiable », quels que soient les tests 1 à 4.
Sortie : registre/psychometrie-alphabet.json.

    python psychometrie_alphabet.py [--fiabilite 50 --budget 1]
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

ENTREE = Path("registre") / "banc-jugement-alphabet.jsonl"
FIABILITE = Path("registre") / "psychometrie-fiabilite.jsonl"
SORTIE = Path("registre") / "psychometrie-alphabet.json"
CARTES = ("tendance", "engagements", "decideurs", "declencheur", "freins", "duree", "proportion")
INVERSEES = {"freins"}
TIRAGES = 2000
N_MIN = 5


def charger(chemin: Path = ENTREE) -> list[dict]:
    if not chemin.exists():
        return []
    out = []
    for l in chemin.read_text(encoding="utf-8").splitlines():
        if not l.strip():
            continue
        x = json.loads(l)
        if x.get("issue") in (0, 1) and isinstance(x.get("notes"), dict) and not x.get("exclue"):
            out.append(x)
    return out


def effet(notes: list[int], issues: list[int], inverse: bool) -> tuple[float | None, int, int]:
    hauts = [y for n, y in zip(notes, issues) if n >= 3]
    bas = [y for n, y in zip(notes, issues) if n <= 2]
    if not hauts or not bas:
        return None, len(hauts), len(bas)
    e = sum(hauts) / len(hauts) - sum(bas) / len(bas)
    return (-e if inverse else e), len(hauts), len(bas)


def statut_carte(xs: list[dict], carte: str, seuil: float, graine: int = 0) -> dict:
    paires = [(x["notes"][carte]["note"], x["issue"]) for x in xs if carte in x["notes"]]
    notes, issues = [p[0] for p in paires], [p[1] for p in paires]
    e, nh, nb = effet(notes, issues, carte in INVERSEES)
    r = {"n": len(paires), "n_haut": nh, "n_bas": nb, "effet": None if e is None else round(e, 3)}
    if e is None or nh < N_MIN or nb < N_MIN:
        return dict(r, statut="non démontrée (trop peu)")
    rnd = random.Random(graine)
    plus = moins = 0
    for _ in range(TIRAGES):
        m = notes[:]
        rnd.shuffle(m)
        em, _, _ = effet(m, issues, carte in INVERSEES)
        plus += em is not None and em >= e
        moins += em is not None and em <= e
    p_bon, p_mauvais = (plus + 1) / (TIRAGES + 1), (moins + 1) / (TIRAGES + 1)
    r.update(p_bon_sens=round(p_bon, 4), p_mauvais_sens=round(p_mauvais, 4))
    if e > 0 and p_bon < seuil:
        return dict(r, statut="démontrée")
    if e < 0 and p_mauvais < seuil:
        return dict(r, statut="trompeuse")
    return dict(r, statut="non démontrée")


def spearman(a: list[float], b: list[float]) -> float | None:
    def rangs(v):
        o = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        i = 0
        while i < len(o):
            j = i
            while j + 1 < len(o) and v[o[j + 1]] == v[o[i]]:
                j += 1
            for k in range(i, j + 1):
                r[o[k]] = (i + j) / 2
            i = j + 1
        return r
    if len(a) < 3:
        return None
    ra, rb = rangs(a), rangs(b)
    ma, mb = sum(ra) / len(ra), sum(rb) / len(rb)
    num = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    den = (sum((x - ma) ** 2 for x in ra) * sum((y - mb) ** 2 for y in rb)) ** 0.5
    return None if den == 0 else num / den


def complets(xs: list[dict]) -> list[list[float]]:
    return [[(5 - x["notes"][c]["note"]) if c in INVERSEES else x["notes"][c]["note"] for c in CARTES]
            for x in xs if all(c in x["notes"] for c in CARTES)]


def premiere_composante(m: list[list[float]]) -> float | None:
    import numpy as np
    if len(m) < 10:
        return None
    a = np.array(m, dtype=float)
    sd = a.std(axis=0)
    a = (a - a.mean(axis=0)) / np.where(sd > 0, sd, 1)
    v = np.linalg.eigvalsh(np.cov(a, rowvar=False))
    return float(v[-1] / v.sum()) if v.sum() > 0 else None


def kappa_pondere(a: list[int], b: list[int], k: int = 4) -> float | None:
    if len(a) < 5:
        return None
    n = len(a)
    obs = [[0.0] * k for _ in range(k)]
    for x, y in zip(a, b):
        obs[x - 1][y - 1] += 1 / n
    pa = [sum(obs[i]) for i in range(k)]
    pb = [sum(obs[i][j] for i in range(k)) for j in range(k)]
    w = lambda i, j: ((i - j) ** 2) / ((k - 1) ** 2)
    do = sum(w(i, j) * obs[i][j] for i in range(k) for j in range(k))
    de = sum(w(i, j) * pa[i] * pb[j] for i in range(k) for j in range(k))
    return None if de == 0 else 1 - do / de


def une_par_question(xs: list[dict]) -> list[dict]:
    """0.10.267 : une seule ligne par question distincte (la première date de jeu). Les bancs de jugement reprennent
    la même question à plusieurs dates (309 lignes = 119 questions) : compter chaque répétition comme une observation
    indépendante gonflait la significativité des cartes (examens du 2026-11-17 et du 2026-11-18, corrigés)."""
    if not xs or "question_id" not in xs[0]:
        return xs
    vu = {}
    for x in sorted(xs, key=lambda x: str(x["question_id"]).split(":")[-1]):
        vu.setdefault(":".join(str(x["question_id"]).split(":")[:2]), x)
    return list(vu.values())


def examiner(xs: list[dict], fiab: list[dict] | None = None) -> dict:
    n_lignes = len(xs)
    xs = une_par_question(xs)
    seuil = 0.05 / len(CARTES)
    formes = sorted({x.get("forme", "autre") for x in xs})
    statuts = {"tout": {c: statut_carte(xs, c, seuil) for c in CARTES}}
    for f in formes:
        sous = [x for x in xs if x.get("forme", "autre") == f]
        statuts[f] = {c: statut_carte(sous, c, seuil) for c in CARTES}
    m = complets(xs)
    red = []
    for i in range(len(CARTES)):
        for j in range(i + 1, len(CARTES)):
            rho = spearman([r[i] for r in m], [r[j] for r in m])
            if rho is not None:
                red.append({"paire": f"{CARTES[i]} × {CARTES[j]}", "rho": round(rho, 3), "redondante": abs(rho) > 0.7})
    out = {"n": len(xs), "n_lignes": n_lignes, "oui": round(sum(x["issue"] for x in xs) / len(xs), 3) if xs else None,
           "seuil_par_type": round(seuil, 4), "statuts": statuts,
           "redondance": sorted(red, key=lambda r: -r["rho"]),
           "premiere_composante": None if not m else round(premiere_composante(m) or 0, 3)}
    if fiab:
        par = {}
        for c in CARTES:
            a = [(x["notes1"][c], x["notes2"][c]) for x in fiab if c in x.get("notes1", {}) and c in x.get("notes2", {})]
            k = kappa_pondere([p[0] for p in a], [p[1] for p in a])
            par[c] = {"n": len(a), "kappa": None if k is None else round(k, 3), "peu_fiable": k is not None and k < 0.4}
        out["fiabilite"] = par
    return out


async def renoter(n: int, budget: float) -> None:
    """Le même modèle renote n questions déjà notées (mêmes consignes ; la recherche est refaite, bornée à la même date)."""
    from datetime import datetime, timezone
    from forecasting_tools import MonetaryCostManager
    import alphabet_modeles as am
    import alphabet_pipeline as ap
    import alphabet_retro as ar
    import banc_forecastbench as fb
    import banc_jugement_alphabet as bja
    deja = {json.loads(l)["question_id"] for l in FIABILITE.read_text(encoding="utf-8").splitlines() if l.strip()} \
        if FIABILITE.exists() else set()
    xs = sorted(charger(), key=lambda x: x["question_id"])
    cand = {f'{x["source"]}:{x["id"]}:{x["jeu"]}': x for x in bja.candidates()}
    textes, cumul, pire, faites = {}, 0.0, 0.0, 0
    with FIABILITE.open("a", encoding="utf-8") as f:
        for x in xs:
            if faites >= n or x["question_id"] in deja or x["question_id"] not in cand:
                continue
            if fb.depasse(cumul, pire, budget):
                break
            c = cand[x["question_id"]]
            if c["jeu"] not in textes:
                qs = await fb._json(f"{fb.DEPOT}/question_sets/{c['jeu']}-llm.json")
                textes[c["jeu"]] = {str(q["id"]): q for q in qs.get("questions", [])}
            src = textes[c["jeu"]].get(c["id"]) or {}
            q = {"titre": c["titre"], "cloture": c["cloture"],
                 "criteres": str(src.get("market_info_resolution_criteria") or src.get("resolution_criteria") or ""),
                 "contexte": str(src.get("background") or "")}
            with MonetaryCostManager() as cm:
                rech = await ar.chercher_avant(c["titre"], datetime.fromisoformat(c["jeu"]).replace(tzinfo=timezone.utc))
                r = ap.extraire_json(await am.llm(bja.MODELE, temperature=0.2, timeout=300, allowed_tries=2).invoke(
                    bja.consigne_notes(q, float(x["p_B"]), rech, c["jeu"])))
                cout = float(cm.current_usage or 0)
            n2 = bja.lire_notes(r)
            f.write(json.dumps({"question_id": x["question_id"], "notes1": {k: v["note"] for k, v in x["notes"].items()},
                                "notes2": {k: v["note"] for k, v in n2.items()}, "cout_usd": round(cout, 4)},
                               ensure_ascii=False) + "\n")
            f.flush()
            cumul += cout
            pire = max(pire, cout)
            faites += 1


def principal(fiabilite: int, budget: float) -> int:
    if fiabilite:
        import asyncio
        asyncio.run(renoter(fiabilite, budget))
    xs = charger()
    if not xs:
        print("Aucune note : le banc jugement alphabet n'a pas encore rendu ses résultats.")
        return 1
    fiab = [json.loads(l) for l in FIABILITE.read_text(encoding="utf-8").splitlines() if l.strip()] if FIABILITE.exists() else None
    r = examiner(xs, fiab)
    SORTIE.write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(r, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("--fiabilite", type=int, default=0)
    a.add_argument("--budget", type=float, default=1.0)
    o = a.parse_args()
    sys.exit(principal(o.fiabilite, o.budget))
