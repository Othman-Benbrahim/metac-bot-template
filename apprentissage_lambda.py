"""Apprendre les forces des cartes (λ) sur les données, EN OMBRE (bot 0.10.30 ; décision d'auteur du 2026-11-11, skill
validation.md §47, après le calcul de puissance : la force que le modèle prête aux cartes, stipulée, est le premier
goulot du test C contre B).

Modèle, le même que le calcul publié sans plafond :  logit p = logit f + Σ_classes n_classe · ln λ_classe,
où n_classe compte les cartes LUES ayant une arête de cette classe (F, M, f de la matrice) vers la cible, et f est le
taux de base B de la question. On estime ln λ_F, ln λ_M, ln λ_f par maximum a posteriori (régression logistique à
décalage), avec un a priori normal centré sur les valeurs stipulées (écart-type 0,5 en ln λ : un facteur 1,6) : avec
peu de questions, l'estimation reste près du stipulé ; elle ne s'en écarte que si les issues le demandent.

Rien ne change dans le calcul publié : les λ appris sont écrits dans registre/lambda-appris-<date>.json, avec leur
incertitude, le nombre de questions et la perte log comparée (stipulés contre appris, en validation croisée). Une
adoption ne se fait que par décision d'auteur datée.

Données : les questions RÉSOLUES du registre du bot (bras C et lectures exploratoires, événement « apparaît »), et, si
on lui donne son dossier, le registre du banc alphabet-chaine (questions résolues en 24 heures).

    python apprentissage_lambda.py [--chaine ../alphabet-chaine/registre] [--enregistrer]
"""
from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import alphabet_pipeline as ap

CLASSES = ("F", "M", "f", "I")   # 0.10.41 : I = frein (skill 0.7.72, §48)
SD_PRIOR = 0.5


def _logit(p: float) -> float:
    p = min(0.999, max(0.001, p))
    return math.log(p / (1 - p))


def compte_sources(m, etat_txt: str, cible: str) -> dict[str, int] | None:
    try:
        etat = m.lire_etat(etat_txt)
        cible = m.cle_valide(cible)
    except (ValueError, KeyError, TypeError, SystemExit):
        return None
    # 0.10.42 : les freins (skill §49) sont en ombre, mais λ_I s'apprend sur les mêmes issues : on les compte
    _f = getattr(m, "FREINS", False)
    m.FREINS = True
    try:
        src, _ = m.sources_de(etat, cible, (), (), ())
    finally:
        m.FREINS = _f
    n = {c: 0 for c in CLASSES}
    for x in src:
        n[x["intensite"]] = n.get(x["intensite"], 0) + 1
    return n


def lignes_bot(reg: Path) -> list[dict]:
    m = ap._moteur()
    issues = {}
    f_ = reg / "issues.jsonl"
    if f_.is_file():
        for brut in f_.read_text(encoding="utf-8").splitlines():
            try:
                x = json.loads(brut)
                issues[str(x.get("question_id"))] = x.get("issue")
            except (json.JSONDecodeError, AttributeError):
                continue
    out = []
    j = reg / "journal-bot.jsonl"
    if not j.is_file():
        return out
    for brut in j.read_text(encoding="utf-8").splitlines():
        try:
            ligne = json.loads(brut)
        except json.JSONDecodeError:
            continue
        qid = str(ligne.get("question_id"))
        y = issues.get(qid)
        if y not in (0, 1):
            continue
        c = (ligne.get("bras") or {}).get("C") or {}
        p_b = ((ligne.get("bras") or {}).get("B") or {}).get("p")
        for bloc in (c, c.get("exploratoire") or {}):
            ev = str(bloc.get("evenement") or "")
            if not bloc.get("etat") or " apparait" not in ev or p_b is None:
                continue
            n = compte_sources(m, bloc["etat"], ev.split(" ")[0])
            if n is not None:
                out.append({"source": "bot", "question_id": qid, "f": float(p_b), "y": int(y), "n": n})
                break
    return out


def lignes_retro(reg: Path) -> list[dict]:
    """0.10.43 : tests rétrospectifs, dont le banc ForecastBench (registre/retro.jsonl), C estimé à la date d'information."""
    m = ap._moteur()
    out = []
    f_ = reg / "retro.jsonl"
    if not f_.is_file():
        return out
    for brut in f_.read_text(encoding="utf-8").splitlines():
        try:
            x = json.loads(brut)
        except json.JSONDecodeError:
            continue
        ev = str(x.get("evenement") or "")
        if x.get("issue") not in (0, 1) or x.get("p_B") is None or not x.get("etat") or " apparait" not in ev:
            continue
        n = compte_sources(m, x["etat"], ev.split(" ")[0])
        if n is not None:
            out.append({"source": x.get("banc") or "retro", "question_id": x.get("question_id"), "f": float(x["p_B"]),
                        "y": int(x["issue"]), "n": n})
    return out


def lignes_chaine(reg: Path) -> list[dict]:
    m = ap._moteur()
    prev = {}
    for nom, cible in (("previsions.jsonl", prev),):
        f_ = reg / nom
        if f_.is_file():
            for brut in f_.read_text(encoding="utf-8").splitlines():
                try:
                    x = json.loads(brut)
                    cible[x["id"]] = x
                except (json.JSONDecodeError, KeyError):
                    continue
    out = []
    f_ = reg / "issues.jsonl"
    if not f_.is_file():
        return out
    for brut in f_.read_text(encoding="utf-8").splitlines():
        try:
            i = json.loads(brut)
        except json.JSONDecodeError:
            continue
        p = prev.get(i.get("id"))
        if not p or i.get("issue") not in ("oui", "non"):
            continue
        c, b = p["bras"].get("C") or {}, p["bras"].get("B") or {}
        ev = c.get("evenement") or {}
        if not c.get("etat") or ev.get("type") != "apparait" or b.get("p") is None:
            continue
        n = compte_sources(m, c["etat"], f"{ev.get('carte')}@{ev.get('strate')}")
        if n is not None:
            out.append({"source": "chaine", "question_id": i["id"], "f": float(b["p"]),
                        "y": 1 if i["issue"] == "oui" else 0, "n": n})
    return out


def ajuster(rows: list[dict], prior: dict[str, float]) -> dict:
    """MAP par Newton-Raphson ; rend β (ln λ), écarts-types (inverse de la hessienne), itérations."""
    k = len(CLASSES)
    mu = [math.log(prior[c]) for c in CLASSES]
    b = list(mu)
    for it in range(50):
        g = [-(b[j] - mu[j]) / SD_PRIOR ** 2 for j in range(k)]
        H = [[(-1 / SD_PRIOR ** 2 if i == j else 0.0) for j in range(k)] for i in range(k)]
        for r in rows:
            x = [r["n"][c] for c in CLASSES]
            z = _logit(r["f"]) + sum(x[j] * b[j] for j in range(k))
            p = 1 / (1 + math.exp(-z))
            for i in range(k):
                g[i] += (r["y"] - p) * x[i]
                for j in range(k):
                    H[i][j] -= p * (1 - p) * x[i] * x[j]
        # résoudre H·d = −g (élimination de Gauss)
        A = [row[:] + [-g[i]] for i, row in enumerate(H)]
        for c_ in range(k):
            piv = max(range(c_, k), key=lambda r_: abs(A[r_][c_]))
            A[c_], A[piv] = A[piv], A[c_]
            for r_ in range(k):
                if r_ != c_ and A[c_][c_]:
                    fac = A[r_][c_] / A[c_][c_]
                    A[r_] = [a - fac * bb for a, bb in zip(A[r_], A[c_])]
        d = [A[i][k] / A[i][i] for i in range(k)]
        b = [b[i] + d[i] for i in range(k)]
        if max(abs(x) for x in d) < 1e-8:
            break
    # écarts-types : diagonale de (−H)⁻¹ (H diagonale dominante par l'a priori)
    M = [[-H[i][j] for j in range(k)] for i in range(k)]
    inv = [[float(i == j) for j in range(k)] for i in range(k)]
    for c_ in range(k):
        piv = M[c_][c_]
        M[c_] = [x / piv for x in M[c_]]
        inv[c_] = [x / piv for x in inv[c_]]
        for r_ in range(k):
            if r_ != c_:
                fac = M[r_][c_]
                M[r_] = [a - fac * bb for a, bb in zip(M[r_], M[c_])]
                inv[r_] = [a - fac * bb for a, bb in zip(inv[r_], inv[c_])]
    return {"beta": b, "sd": [math.sqrt(max(0.0, inv[i][i])) for i in range(k)], "iterations": it + 1}


def perte(rows: list[dict], lam: dict[str, float]) -> float:
    s = 0.0
    for r in rows:
        z = _logit(r["f"]) + sum(r["n"][c] * math.log(lam[c]) for c in CLASSES)
        p = ap.borner(1 / (1 + math.exp(-z)))
        s += -math.log(p if r["y"] else 1 - p)
    return s / len(rows)


def apprendre(rows: list[dict]) -> dict:
    prior = {c: float(ap._moteur().P["lambda"][c]) for c in CLASSES}
    out = {"calcule_le": datetime.now(timezone.utc).isoformat(timespec="seconds"), "version_bot": ap.VERSION_BOT,
           "version_skill": ap.version_skill(), "questions": len(rows),
           "par_source": {s: sum(1 for r in rows if r["source"] == s) for s in sorted({r["source"] for r in rows})},
           "questions_avec_source": sum(1 for r in rows if any(r["n"].values())),
           "lambda_stipules": prior, "a_priori": f"normal sur ln λ, centré sur le stipulé, écart-type {SD_PRIOR}"}
    if not rows:
        return dict(out, statut="aucune question résolue avec lecture")
    fit = ajuster(rows, prior)
    appris = {c: round(math.exp(fit["beta"][j]), 3) for j, c in enumerate(CLASSES)}
    out["lambda_appris"] = appris
    out["intervalle_95"] = {c: [round(math.exp(fit["beta"][j] - 1.96 * fit["sd"][j]), 3),
                                round(math.exp(fit["beta"][j] + 1.96 * fit["sd"][j]), 3)] for j, c in enumerate(CLASSES)}
    out["exposition"] = {c: sum(r["n"][c] for r in rows) for c in CLASSES}
    # validation croisée en 5 blocs : perte log hors échantillon, stipulés contre appris
    if len(rows) >= 10:
        pl_s, pl_a = [], []
        for b_ in range(5):
            test = [r for i, r in enumerate(rows) if i % 5 == b_]
            train = [r for i, r in enumerate(rows) if i % 5 != b_]
            fb = ajuster(train, prior)
            lam_b = {c: math.exp(fb["beta"][j]) for j, c in enumerate(CLASSES)}
            pl_s.append(perte(test, prior) * len(test))
            pl_a.append(perte(test, lam_b) * len(test))
        out["perte_log_hors_echantillon"] = {"stipules": round(sum(pl_s) / len(rows), 4),
                                             "appris": round(sum(pl_a) / len(rows), 4),
                                             "lecture": "appris < stipulés : les données corrigent utilement les λ"}
    out["statut"] = ("indicatif : trop peu de questions pour s'écarter de l'a priori" if len(rows) < 50
                     else "exploitable pour une décision d'auteur")
    return out


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--chaine", help="dossier registre du banc alphabet-chaine")
    p.add_argument("--enregistrer", action="store_true")
    a = p.parse_args()
    rows = lignes_bot(ap.REGISTRE) + lignes_retro(ap.REGISTRE) + (lignes_chaine(Path(a.chaine)) if a.chaine else [])
    r = apprendre(rows)
    print(json.dumps({k: v for k, v in r.items() if k not in ("calcule_le",)}, ensure_ascii=False))
    if a.enregistrer:
        ap.REGISTRE.mkdir(parents=True, exist_ok=True)
        (ap.REGISTRE / f"lambda-appris-{r['calcule_le'][:10]}.json").write_text(
            json.dumps(r, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
