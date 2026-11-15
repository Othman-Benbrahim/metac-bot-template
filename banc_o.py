"""Banc des motifs ordinaux (0.10.108, décision d'auteur du 2026-11-15 : « l'état précède l'essence » — un alphabet
DÉCOUVERT dans les états plutôt que stipulé). Aucun modèle de langue, aucun coût.

Méthode publiée, réglages usuels (pré-enregistrement : preenregistrements/motifs-ordinaux.md) :
- motifs ordinaux de Bandt et Pompe (Phys. Rev. Lett. 88, 174102, 2002), ordre d = 3, délai 1, sur les observations
  natives de la série, 5 ans strictement avant la date d'information D (même fenêtre que B) ; égalités départagées par
  l'ordre d'apparition ;
- O_local : parmi les instants passés t de la MÊME série où le motif des 3 dernières valeurs est celui qui précède D,
  part de ceux suivis d'une hausse à l'horizon h (premier point à t + h ou après, t + h < D) : (k + ½)/(n + 1) ; au
  moins 5 occurrences, sinon pas de valeur ;
- O_transversal : la même part comptée sur TOUTES les autres séries du même jeu (même D, donc aucune donnée postérieure
  à D), sans la série elle-même : un motif appris ailleurs, dans d'autres domaines ;
- entropie de permutation normalisée (log 6) de chaque série, mesure de prévisibilité (Garland, James et Bradley,
  Phys. Rev. E 90, 052910, 2014).
Comparaisons : perte logarithmique (règle propre, Gneiting et Raftery, JASA 2007) ; écart apparié avec intervalle
bootstrap par blocs « jeu × source » (règle d'adoption commune) et statistique de Diebold et Mariano (JBES 1995), erreur
type robuste par blocs. Avec le bras A (registre/banc-a.jsonl) là où il existe : A, ½A + ½B, et ⅓A + ⅓B + ⅓O_transversal
(moyennes de logits, poids fixés d'avance).

    python banc_o.py
"""
from __future__ import annotations

import asyncio
import json
import math
import sys
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path

import alphabet_pipeline as ap
import banc_forecastbench as fb

REGISTRE = Path("registre")
FICHIER = REGISTRE / "banc-o.jsonl"
RESUME = REGISTRE / "banc-o.json"
SOURCES = ("fred", "dbnomics")
APRES = "2026-07-01"
JEUX_VUS = {"2026-09-27", "2026-10-11", "2026-10-25"}
D_ORDRE, N_MIN = 3, 5


def motif(vals: list[float]) -> tuple[int, ...]:
    """Motif ordinal de Bandt et Pompe : l'ordre des valeurs (égalités départagées par l'ordre d'apparition)."""
    return tuple(sorted(range(len(vals)), key=lambda i: (vals[i], i)))


def preparer(points: list[dict], avant: date, annees: int = 5) -> list[tuple[date, float]]:
    pts = sorted((date.fromisoformat(p["date"][:10]), float(p["valeur"])) for p in points
                 if p.get("date") and p.get("valeur") is not None and p["date"][:10] < avant.isoformat())
    return [p for p in pts if p[0] >= avant - timedelta(days=365 * annees)]


def paires(pts: list[tuple[date, float]], h: int, avant: date) -> list[tuple[tuple, int]]:
    """(motif finissant en t, hausse à t + h) pour chaque t dont l'issue est connue avant D."""
    out, j = [], 0
    for i in range(D_ORDRE - 1, len(pts)):
        t, v = pts[i]
        cible = t + timedelta(days=h)
        if cible >= avant:
            break
        while j < len(pts) and pts[j][0] < cible:
            j += 1
        if j >= len(pts):
            break
        out.append((motif([x[1] for x in pts[i - D_ORDRE + 1:i + 1]]), int(pts[j][1] > v)))
    return out


def entropie_permutation(pts: list[tuple[date, float]]) -> float | None:
    m = Counter(motif([x[1] for x in pts[i - D_ORDRE + 1:i + 1]]) for i in range(D_ORDRE - 1, len(pts)))
    n = sum(m.values())
    if n < 30:
        return None
    return -sum(c / n * math.log(c / n) for c in m.values()) / math.log(math.factorial(D_ORDRE))


def jeffreys(k: int, n: int) -> float | None:
    return (k + 0.5) / (n + 1) if n >= N_MIN else None


def logit(p: float) -> float:
    p = min(max(p, 1e-3), 1 - 1e-3)
    return math.log(p / (1 - p))


def moyenne_logits(ps: list[float]) -> float:
    return 1 / (1 + math.exp(-sum(logit(p) for p in ps) / len(ps)))


def perte(p: float, y: int) -> float:
    p = min(max(p, 1e-3), 1 - 1e-3)
    return -math.log(p if y else 1 - p)


def diebold_mariano(lignes: list[dict], cle: str, ref: str) -> dict | None:
    """Écart moyen de perte (cle − ref), erreur type robuste par blocs « jeu × source » ; z et p bilatéral (normale)."""
    d = [(f"{x['jeu']}:{x['source_question']}", perte(x[cle], x["issue"]) - perte(x[ref], x["issue"])) for x in lignes]
    if len(d) < 10:
        return None
    moy = sum(e for _, e in d) / len(d)
    blocs: dict[str, float] = defaultdict(float)
    for b, e in d:
        blocs[b] += e - moy
    g = len(blocs)
    var = sum(s * s for s in blocs.values()) / len(d) ** 2 * (g / (g - 1) if g > 1 else 1)
    if var <= 0:
        return {"ecart": moy, "blocs": g}
    z = moy / math.sqrt(var)
    return {"ecart": round(moy, 4), "z": round(z, 3), "p_bilateral": round(math.erfc(abs(z) / math.sqrt(2)), 4),
            "blocs": g, "n": len(d)}


async def collecter() -> list[dict]:
    jeux = [j for j in sorted(fb.jeux_candidats(date.today(), date.fromisoformat(APRES), n_max=26)) if j not in JEUX_VUS]
    out = []
    for j in jeux:
        try:
            qs = await fb._json(f"{fb.DEPOT}/question_sets/{j}-llm.json")
            rs = await fb._json(f"{fb.DEPOT}/resolution_sets/{j}_resolution_set.json")
        except Exception as e:
            print(f"Jeu {j} indisponible : {type(e).__name__}")
            continue
        items = sorted((fb.construire(i, j) for i in fb.apparier(qs, rs, SOURCES)), key=lambda x: x["qid"])
        n0 = len(out)
        for x in items:
            try:
                vue = await fb.vue_calculee(x, x["_q"], j)
            except Exception:
                vue = None
            if not vue or vue.get("frequence") is None:
                continue
            d0 = date.fromisoformat(j)
            out.append({"jeu": j, "question_id": x["qid"], "source_question": x["source"], "serie": f"{x['source']}:{x['_q']['id']}",
                        "issue": x["issue"], "p_B": float(vue["frequence"]), "h": (date.fromisoformat(x["resolution"]) - d0).days,
                        "_pts": preparer((x.get("_releve") or {}).get("points") or [], d0)})
        print(f"Jeu {j} : {len(out) - n0} questions avec B et série.")
    return out


def calculer(qs: list[dict]) -> list[dict]:
    # tables transversales par (jeu, h) : comptes par motif et par série, pour retirer la série elle-même
    groupes: dict[tuple, list[dict]] = defaultdict(list)
    for q in qs:
        groupes[(q["jeu"], q["h"])].append(q)
    sortie = []
    for (j, h), membres in groupes.items():
        d0 = date.fromisoformat(j)
        par_serie = {}
        total: dict[tuple, list[int]] = defaultdict(lambda: [0, 0])
        for q in membres:
            if q["serie"] in par_serie:
                continue
            c: dict[tuple, list[int]] = defaultdict(lambda: [0, 0])
            for m, y in paires(q["_pts"], h, d0):
                c[m][0] += y
                c[m][1] += 1
            par_serie[q["serie"]] = c
            for m, (k, n) in c.items():
                total[m][0] += k
                total[m][1] += n
        for q in membres:
            pts = q["_pts"]
            ligne = {k: v for k, v in q.items() if not k.startswith("_")}
            ligne["version_bot"] = ap.VERSION_BOT
            if len(pts) < D_ORDRE:
                sortie.append(dict(ligne, p_O_local=None, p_O_trans=None))
                continue
            cur = motif([x[1] for x in pts[-D_ORDRE:]])
            k_l, n_l = par_serie[q["serie"]].get(cur, [0, 0])
            k_t, n_t = total.get(cur, [0, 0])
            k_t, n_t = k_t - k_l, n_t - n_l
            ligne.update(motif=list(cur), n_local=n_l, n_trans=n_t, p_O_local=jeffreys(k_l, n_l),
                         p_O_trans=jeffreys(k_t, n_t), entropie_permutation=entropie_permutation(pts))
            sortie.append(ligne)
    return sorted(sortie, key=lambda x: (x["jeu"], x["question_id"]))


def resumer(ls: list[dict]) -> dict:
    import score_registre as sr
    out = {"version_bot": ap.VERSION_BOT, "questions": len(ls),
           "note": "perte log, plus bas = mieux ; aucun modèle de langue ; motifs ordinaux d = 3"}

    def bloc(sous: list[dict], cle: str, ref: str) -> dict:
        n = len(sous)
        return {"n": n, cle: round(sum(perte(x[cle], x["issue"]) for x in sous) / n, 4) if n else None,
                ref: round(sum(perte(x[ref], x["issue"]) for x in sous) / n, 4) if n else None,
                "diebold_mariano": diebold_mariano(sous, cle, ref)}
    for cle in ("p_O_local", "p_O_trans"):
        sous = [x for x in ls if x.get(cle) is not None]
        par_source = {s: bloc([x for x in sous if x["source_question"] == s], cle, "p_B") for s in SOURCES}
        out[cle] = {**bloc(sous, cle, "p_B"), "par_source": par_source}
    ent = [x["entropie_permutation"] for x in ls if x.get("entropie_permutation") is not None]
    out["entropie_permutation_moyenne"] = round(sum(ent) / len(ent), 4) if ent else None
    import hashlib
    rang: dict[str, int] = {}
    for j in sorted({x["jeu"] for x in ls}):
        for r_, x in enumerate(sorted((x for x in ls if x["jeu"] == j),
                                      key=lambda x: hashlib.sha1(x["question_id"].encode()).hexdigest())):
            rang[x["question_id"]] = r_
    entrelace = sorted(ls, key=lambda x: (rang[x["question_id"]], x["jeu"]))   # ordre fixé : blocs variés dès le début
    ot = [dict(x, ombre_o={"p": x["p_O_trans"]}) for x in entrelace if x.get("p_O_trans") is not None]
    out["critere_O_trans"] = sr.critere_ombre_b(ot, "ombre_o", "motifs_ordinaux")
    # avec le bras A
    a = {}
    fa = REGISTRE / "banc-a.jsonl"
    if fa.exists():
        for l in fa.read_text(encoding="utf-8").splitlines():
            if l.strip():
                y = json.loads(l)
                if y.get("p_A") is not None and not y.get("exclue"):
                    a.setdefault(y["question_id"], y)
    inter = []
    for x in ls:
        y = a.get(x["question_id"])
        if y and x.get("p_O_trans") is not None:
            inter.append(dict(x, p_A=y["p_A"], p_AB=moyenne_logits([y["p_A"], x["p_B"]]),
                              p_ABO=moyenne_logits([y["p_A"], x["p_B"], x["p_O_trans"]]), ordre=y.get("ordre")))
    inter.sort(key=lambda x: (x.get("ordre") or [10 ** 6, x["jeu"]]))
    if inter:
        n = len(inter)
        out["avec_A"] = {"n": n, **{k: round(sum(perte(x[c], x["issue"]) for x in inter) / n, 4)
                                    for k, c in (("A", "p_A"), ("B", "p_B"), ("O_trans", "p_O_trans"),
                                                 ("AB", "p_AB"), ("ABO", "p_ABO"))},
                         "diebold_mariano_ABO_contre_AB": diebold_mariano(inter, "p_ABO", "p_AB"),
                         "critere_ABO": sr.critere_ombre_b([dict(x, p_B=x["p_AB"], ombre_abo={"p": x["p_ABO"]})
                                                            for x in inter], "ombre_abo", "combo_abo")}
    return out


async def principal() -> int:
    qs = await collecter()
    ls = calculer(qs)
    REGISTRE.mkdir(exist_ok=True)
    FICHIER.write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in ls), encoding="utf-8")
    r = resumer(ls)
    RESUME.write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(r, ensure_ascii=False, indent=1)[:4000])
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(principal()))
