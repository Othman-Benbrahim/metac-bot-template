"""Bancs de l'attention GDELT : tendance (piste « avenir déjà présent ») et sursauts (piste « réponse aux chocs »).

Bot 0.10.281. Décision d'auteur du 2026-11-18, 18 h 25 (« fais les trois »). Préenregistrements :
preenregistrements/tendance-attention.md et preenregistrements/sursauts-attention.md. Aucun appel à un modèle : tout est
calculé par le code à partir des comptes d'articles GDELT (registre/gdelt-bq-comptes.json, gdelt_bq.py --mode comptes)
et des prévisions M déjà enregistrées (registre/banc-jugement-alphabet.jsonl).

    python banc_attention_gdelt.py
"""
from __future__ import annotations

import json
import math
from datetime import date, timedelta
from pathlib import Path

import alphabet_pipeline as ap
import banc_jugement_alphabet as bja
import psychometrie_alphabet as ps

COMPTES = Path("registre/gdelt-bq-comptes.json")
RESUME = Path("registre/banc-attention-gdelt.json")
FENETRE, RECENT = 90, 10                     # jours avant le jeu ; les 10 derniers forment la période récente
GRILLE_BETA = [round(-1 + 0.05 * i, 2) for i in range(41)]
GRILLE_LAMBDA = [round(0.05 * i, 2) for i in range(21)]


def Q(qid: str) -> str:
    return ":".join(qid.split(":")[:2])


def serie(entree: dict) -> list[int] | None:
    """90 comptes quotidiens, du jour J−90 au jour J−1 ; None si la question n'a pas pu être filtrée."""
    if not entree.get("filtrable", True):
        return None
    fin = date.fromisoformat(entree["fin"])
    j = entree.get("jours") or {}
    return [int(j.get((fin - timedelta(days=FENETRE - 1 - i)).isoformat(), 0)) for i in range(FENETRE)]


def tendance(s: list[int] | None) -> float:
    """ln((récent/10 + 0,1) / (ancien/80 + 0,1)) ; 0 sans article (aucun ajustement)."""
    if not s or sum(s) == 0:
        return 0.0
    r, a = sum(s[-RECENT:]) / RECENT, sum(s[:-RECENT]) / (FENETRE - RECENT)
    return math.log((r + 0.1) / (a + 0.1))


def sans_pics_isoles(s: list[int]) -> list[float]:
    """0.10.284 (décision d'auteur du 2026-11-18, 19 h 16 ; repris du filtre de cohérence de J. Landrevie,
    physical-tracking) : un jour INTÉRIEUR au-dessus de 5 × base, dont la veille ET le lendemain restent sous 2 × base,
    est ramené à la médiane (base = max(médiane des 90 jours, 1)). Les deux jours du bord ne sont pas touchés : un pic
    à J−1 ne peut pas être confirmé."""
    import statistics as st_
    med = float(st_.median(s))
    base = max(med, 1.0)
    out = [float(v) for v in s]
    for i in range(1, len(s) - 1):
        if s[i] > 5 * base and s[i - 1] <= 2 * base and s[i + 1] <= 2 * base:
            out[i] = med
    return out


def sursaut(s: list[int] | None, filtre: bool = True) -> float | None:
    """Indice de sursaut de Goh et Barabási, (σ − μ) / (σ + μ), entre −1 (régulier) et 1 (rafales) ; None sans article."""
    if not s or sum(s) == 0:
        return None
    if filtre:
        s = sans_pics_isoles(s)
        if sum(s) == 0:
            return None
    mu = sum(s) / len(s)
    sd = math.sqrt(sum((v - mu) ** 2 for v in s) / len(s))
    return (sd - mu) / (sd + mu)


def _pl(p: float, y: int) -> float:
    p = min(max(p, 1e-3), 1 - 1e-3)
    return -math.log(p if y else 1 - p)


def _logit(p: float) -> float:
    p = min(max(p, 1e-3), 1 - 1e-3)
    return math.log(p / (1 - p))


def ajuste_tendance(p: float, t: float, beta: float) -> float:
    return 1 / (1 + math.exp(-(_logit(p) + beta * t)))


def ajuste_sursaut(p: float, b: float | None, lam: float) -> float:
    if b is None:
        return p
    return 0.5 + (p - 0.5) * (1 - lam * max(0.0, b))


def donnees() -> list[dict]:
    """Une ligne par question distincte : la prévision M de la date de jeu des comptes (ou la plus proche APRÈS)."""
    cpt = json.loads(COMPTES.read_text(encoding="utf-8")) if COMPTES.exists() else {}
    par_q = {Q(k): (k.split(":")[-1], v) for k, v in cpt.items()}
    out, vus = [], set()
    for x in sorted(bja.lignes(), key=lambda x: x["question_id"].split(":")[-1]):
        q = Q(x["question_id"])
        if q in vus or q not in par_q or x.get("exclue") or x.get("issue") not in (0, 1) or x.get("p_M") is None:
            continue
        jeu_c, entree = par_q[q]
        if x["question_id"].split(":")[-1] < jeu_c:          # la fenêtre doit finir avant la date de jeu de M
            continue
        vus.add(q)
        s = serie(entree)
        out.append({"question_id": x["question_id"], "jeu": x["question_id"].split(":")[-1], "issue": x["issue"],
                    "p_M": x["p_M"], "articles": sum(s) if s else 0, "tendance": tendance(s), "sursaut": sursaut(s),
                    "sursaut_brut": sursaut(s, filtre=False),
                    "pics_retires": sum(1 for a, b in zip(s, sans_pics_isoles(s)) if a != b) if s and sum(s) else 0})
    return out


def loo(ls: list[dict], ajuste, cle: str, grille: list[float]) -> list[float]:
    """Paramètre appris SANS la question jugée (une question = une ligne) : minimum de perte log sur la grille."""
    out = []
    for i, x in enumerate(ls):
        autres = ls[:i] + ls[i + 1:]
        best = min(grille, key=lambda g: (sum(_pl(ajuste(y["p_M"], y[cle], g), y["issue"]) for y in autres), abs(g)))
        out.append(ajuste(x["p_M"], x[cle], best))
    return out


def resumer(ls: list[dict]) -> dict:
    import profil_erreurs as pe
    import score_registre as sr
    out = {"version_bot": ap.VERSION_BOT, "questions": len(ls),
           "avec_articles": sum(1 for x in ls if x["articles"] > 0),
           "note": "une ligne par question distincte ; paramètre appris en laissant la question jugée de côté"}
    if len(ls) < 10:
        return dict(out, verdict="en attente (comptes GDELT absents : gdelt_bq.py --mode comptes)")
    avec = [x for x in ls if x["articles"] > 0]
    out["descriptif"] = {
        "spearman_tendance_issue": round(ps.spearman([x["tendance"] for x in avec], [x["issue"] for x in avec]), 3)
        if len(avec) >= 10 else None,
        "spearman_sursaut_issue": round(ps.spearman([x["sursaut"] for x in avec], [x["issue"] for x in avec]), 3)
        if len(avec) >= 10 else None,
        "sursaut_moyen_rates": _moy([x["sursaut"] for x in avec if x["issue"] == 1 and x["p_M"] < 0.3]),
        "sursaut_moyen_autres": _moy([x["sursaut"] for x in avec if not (x["issue"] == 1 and x["p_M"] < 0.3)]),
        "pics_isoles_retires": {"jours": sum(x["pics_retires"] for x in ls),
                                "questions_touchees": sum(1 for x in ls if x["pics_retires"])},
        "spearman_sursaut_brut_issue": round(ps.spearman([x["sursaut_brut"] for x in avec], [x["issue"] for x in avec]), 3)
        if len(avec) >= 10 else None,
    }
    for nom, ajuste, cle, grille, essai in (("tendance", ajuste_tendance, "tendance", GRILLE_BETA, "tendance_attention"),
                                            ("sursaut", ajuste_sursaut, "sursaut", GRILLE_LAMBDA, "sursauts_attention")):
        ps_ = loo(ls, ajuste, cle, grille)
        lignes = [dict(x, p_B=x["p_M"], o={"p": p}) for x, p in zip(ls, ps_)]
        n = len(ls)
        tout = min(grille, key=lambda g: (sum(_pl(ajuste(y["p_M"], y[cle], g), y["issue"]) for y in ls), abs(g)))
        out[nom] = {"perte_M": round(sum(_pl(x["p_M"], x["issue"]) for x in ls) / n, 4),
                    "perte_ajustee": round(sum(_pl(p, x["issue"]) for x, p in zip(ls, ps_)) / n, 4),
                    "parametre_sur_tout": tout,
                    "critere": sr.critere_ombre_b(lignes, "o", essai, exclure_vus=False, bloc_par="question",
                                                  tout_juger=True),
                    "profils": pe.profils([dict(x, p_aj=p) for x, p in zip(ls, ps_)], {"M": "p_M", "ajuste": "p_aj"})}
    return out


def _moy(v: list) -> float | None:
    v = [a for a in v if a is not None]
    return round(sum(v) / len(v), 3) if v else None


def principal() -> int:
    r = resumer(donnees())
    RESUME.write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(r, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(principal())
