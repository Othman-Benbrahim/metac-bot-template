"""Premier apprentissage de la STRUCTURE de l'arbre : réseau bayésien entre les notes de cartes et l'issue (0.10.291).

Décision d'auteur du 2026-11-18, 20 h 31 (« je valide, ça fait avancer nos recherches »). Source de la méthode :
Kochenderfer, Wheeler, Wray, Algorithms for Decision Making (MIT Press, 2022), ch. 5 (fiche de projet
claude/reference-kochenderfer-algorithms-decision-making.md). Préenregistrement : preenregistrements/structure-arbre.md.

Banc DESCRIPTIF (aucune adoption, aucun essai) ; aucun appel à un modèle ; code écrit ici, sans bibliothèque de plus
(score BDeu de Cooper-Herskovits/Heckerman, recherche K2), pour que chaque étape soit lisible.

Données : les 7 notes de cartes (1 à 4) déjà données par gpt-5-mini au banc du jugement (une ligne par question
distincte, première date de jeu), plus l'issue. Réplique : les notes de Claude Haiku (banc des variantes).

    python banc_structure_arbre.py
"""
from __future__ import annotations

import json
import math
import random
from itertools import product
from pathlib import Path

import alphabet_pipeline as ap

RESUME = Path("registre/banc-structure-arbre.json")
CLES = ("tendance", "engagements", "decideurs", "declencheur", "freins", "duree", "proportion")
ISSUE = "issue"
ETATS = {**{c: (1, 2, 3, 4) for c in CLES}, ISSUE: (0, 1)}
ESS = 1.0                 # taille d'échantillon équivalente du prior BDeu (fixée)
MAX_PARENTS = 2
TIRAGES = 500
ORDRES = 20
SEUIL_STABLE = 0.7
GRAINE = 0


def bdeu(donnees: list[dict], noeud: str, parents: tuple[str, ...]) -> float:
    """Score BDeu local : log P(données du nœud | parents), prior de Dirichlet α = ESS / (q·r)."""
    r = len(ETATS[noeud])
    configs = list(product(*(ETATS[p] for p in parents))) if parents else [()]
    q = len(configs)
    a_jk, a_j = ESS / (q * r), ESS / q
    comptes: dict[tuple, dict] = {}
    for x in donnees:
        comptes.setdefault(tuple(x[p] for p in parents), {}).setdefault(x[noeud], 0)
        comptes[tuple(x[p] for p in parents)][x[noeud]] += 1
    s = 0.0
    for cfg in configs:
        m = comptes.get(cfg, {})
        n_j = sum(m.values())
        s += math.lgamma(a_j) - math.lgamma(a_j + n_j)
        s += sum(math.lgamma(a_jk + m.get(k, 0)) - math.lgamma(a_jk) for k in ETATS[noeud])
    return s


def k2(donnees: list[dict], ordre: list[str]) -> dict[str, tuple[str, ...]]:
    """K2 : chaque nœud prend, parmi ceux qui le précèdent dans l'ordre, le parent qui améliore le plus le score,
    tant qu'il y a amélioration et au plus MAX_PARENTS parents."""
    parents = {n: () for n in ordre}
    for i, n in enumerate(ordre):
        courant = bdeu(donnees, n, ())
        while len(parents[n]) < MAX_PARENTS:
            cands = [(bdeu(donnees, n, parents[n] + (p,)), p) for p in ordre[:i] if p not in parents[n]]
            if not cands:
                break
            meilleur, p = max(cands)
            if meilleur <= courant:
                break
            courant, parents[n] = meilleur, parents[n] + (p,)
    return parents


def aretes(parents: dict[str, tuple[str, ...]]) -> set[tuple[str, str]]:
    return {(p, n) for n, ps in parents.items() for p in ps}


def une_par_question(lignes: list[dict], lire) -> list[dict]:
    """Une ligne par question distincte (première date de jeu), notes complètes, issue connue."""
    out, vus = [], set()
    for x in sorted(lignes, key=lambda x: x["question_id"].split(":")[-1]):
        q = ":".join(x["question_id"].split(":")[:2])
        notes = lire(x)
        if q in vus or x.get("issue") not in (0, 1) or not notes or any(notes.get(c) not in (1, 2, 3, 4) for c in CLES):
            continue
        vus.add(q)
        out.append({**{c: notes[c] for c in CLES}, ISSUE: x["issue"], "question_id": x["question_id"]})
    return out


def analyser(d: list[dict]) -> dict:
    rnd = random.Random(GRAINE)
    ordre = list(CLES) + [ISSUE]
    base = k2(d, ordre)
    freq: dict[tuple[str, str], int] = {}
    for _ in range(TIRAGES):                                   # rééchantillonnage des QUESTIONS
        e = [d[rnd.randrange(len(d))] for _ in d]
        for a in aretes(k2(e, ordre)):
            freq[a] = freq.get(a, 0) + 1
    vers_issue: dict[str, int] = {}
    for _ in range(ORDRES):                                    # ordre des notes tiré au hasard, l'issue reste la fin
        o = list(CLES)
        rnd.shuffle(o)
        for p in k2(d, o + [ISSUE])[ISSUE]:
            vers_issue[p] = vers_issue.get(p, 0) + 1
    # vérification prédictive (affichée, non jugée) : issue | parents appris SANS la question, contre l'issue seule
    pl = lambda p, y: -math.log(min(max(p, 1e-3), 1 - 1e-3) if y else 1 - min(max(p, 1e-3), 1 - 1e-3))
    perte_g = perte_0 = 0.0
    for i, x in enumerate(d):
        autres = d[:i] + d[i + 1:]
        ps = k2(autres, ordre)[ISSUE]
        sous = [y for y in autres if all(y[p] == x[p] for p in ps)]
        perte_g += pl((sum(y[ISSUE] for y in sous) + 0.5) / (len(sous) + 1), x[ISSUE])
        perte_0 += pl((sum(y[ISSUE] for y in autres) + 0.5) / (len(autres) + 1), x[ISSUE])
    tri = sorted(freq.items(), key=lambda t: -t[1])
    return {"questions": len(d), "oui": sum(x[ISSUE] for x in d),
            "parents_issue": list(base[ISSUE]),
            "aretes_echantillon_complet": sorted(f"{a} → {b}" for a, b in aretes(base)),
            "aretes_stables": [f"{a} → {b} ({n / TIRAGES:.0%})" for (a, b), n in tri if n / TIRAGES >= SEUIL_STABLE],
            "aretes_vers_issue_frequence": {f"{a} → issue": round(n / TIRAGES, 3) for (a, b), n in tri if b == ISSUE},
            "aretes_frequentes_top15": [f"{a} → {b} ({n / TIRAGES:.0%})" for (a, b), n in tri[:15]],
            "parents_issue_selon_ordre": {p: f"{n}/{ORDRES}" for p, n in sorted(vers_issue.items(), key=lambda t: -t[1])},
            "verification_predictive": {"perte_issue_par_parents_appris": round(perte_g / len(d), 4),
                                        "perte_issue_seule": round(perte_0 / len(d), 4)}}


def principal() -> int:
    import banc_jugement_alphabet as bja
    import banc_jugement_variantes as bv
    gpt = une_par_question([x for x in bja.lignes() if not x.get("exclue")],
                           lambda x: {k: v.get("note") for k, v in (x.get("notes") or {}).items()})
    haiku = une_par_question([x for x in bv.lignes() if not (x.get("haiku") or {}).get("exclue")],
                             lambda x: {k: v.get("note") for k, v in ((x.get("haiku") or {}).get("notes") or {}).items()})
    import profil_erreurs as pe
    r = {"version_bot": ap.VERSION_BOT,
         "note": ("descriptif ; K2 + score BDeu (ESS 1), au plus 2 parents, ordre : notes dans l'ordre des critères "
                  "puis issue ; stabilité : 500 rééchantillonnages des questions ; lien stable si présent ≥ 70 %"),
         "gpt": analyser(gpt) if len(gpt) >= 30 else "trop peu de questions",
         "haiku": analyser(haiku) if len(haiku) >= 30 else "trop peu de questions",
         "unites": {"gpt": pe.unites(gpt), "haiku": pe.unites(haiku)}}
    RESUME.write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(r, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(principal())
