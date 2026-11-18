"""Banc « la question nomme un acteur » : correctif de NIVEAU du taux de base (bot 0.10.288).

Décision d'auteur du 2026-11-18, 19 h 49 (« ok, on le fait »). Idée née APRÈS les données du banc de la crédibilité
(run 44373402637 : les questions de 2026 qui nomment un acteur se résolvent OUI plus souvent que ne le dit R1 ; le
gain de C était un gain de calibrage). Préenregistrement : preenregistrements/acteur-nomme.md. Elle est donc jugée
sur d'AUTRES questions : celles de 2025 (aucune ne figurait dans le banc de la crédibilité). Aucun modèle, aucune cote.

Règle : p_N = (oui des questions de la même classe, closes et résolues avant le jeu + K·R1) / (n + K), K = 5, avec
deux classes seulement : acteur reconnu (banc_credibilite.categorie ≠ « aucun ») ou non.

    python banc_acteur_nomme.py
"""
from __future__ import annotations

import json
from pathlib import Path

import alphabet_pipeline as ap
import banc_credibilite as bc
import banc_jugement as bj

RESUME = Path("registre/banc-acteur-nomme.json")
DEBUT, FIN = "2025-01-01", "2026-01-01"          # questions jugées : jeux de 2025


def classe(titre: str) -> str:
    return "acteur" if bc.categorie(titre) != "aucun" else "aucun"


def calculer_n(xs: list[dict]) -> None:
    for x in xs:
        x["classe_n"] = classe(x["titre"])
    for x in xs:
        cle = f'{x["source"]}:{x["id"]}'
        prec = [y for y in xs if y["classe_n"] == x["classe_n"] and f'{y["source"]}:{y["id"]}' != cle
                and max(y["resolue_le"], y.get("cloture", "")) < x["jeu"]]
        x["n_classe"] = len(prec)
        x["p_N"] = (sum(y["issue"] for y in prec) + bc.K * x["p_R1"]) / (len(prec) + bc.K)


def distinctes(xs: list[dict], filtre) -> list[dict]:
    vus, out = set(), []
    for x in sorted(xs, key=lambda x: x["jeu"]):
        cle = f'{x["source"]}:{x["id"]}'
        if cle in vus:
            continue
        vus.add(cle)
        if DEBUT <= x["jeu"] < FIN and filtre(x):
            out.append(dict(x, question_id=f'{cle}:{x["jeu"]}'))
    return out


def resumer(xs: list[dict]) -> dict:
    import profil_erreurs as pe
    import score_registre as sr
    acteurs = distinctes(xs, lambda x: x["classe_n"] == "acteur")
    toutes = distinctes(xs, lambda x: True)
    out = {"version_bot": ap.VERSION_BOT, "questions_acteur": len(acteurs), "questions_toutes": len(toutes),
           "note": "questions distinctes de 2025 ; N (classe acteur / aucun) contre R1"}
    if len(acteurs) < 10:
        return dict(out, verdict="en attente")
    pl = bc._pl
    for nom, ls in (("acteur", acteurs), ("toutes", toutes)):
        n = len(ls)
        out[f"perte_{nom}"] = {k: round(sum(pl(x[f"p_{k}"], x["issue"]) for x in ls) / n, 4) for k in ("R1", "S", "N")}
        out[f"oui_{nom}"] = round(sum(x["issue"] for x in ls) / n, 3)
    out["critere"] = sr.critere_ombre_b([dict(x, p_B=x["p_R1"], o={"p": x["p_N"]}) for x in acteurs], "o",
                                        "acteur_nomme", exclure_vus=False, bloc_par="question", tout_juger=True)
    out["secondaire_toutes"] = sr.critere_ombre_b([dict(x, p_B=x["p_R1"], o={"p": x["p_N"]}) for x in toutes], "o",
                                                  "acteur_nomme", exclure_vus=False, bloc_par="question",
                                                  tout_juger=True)
    out["profils_acteur"] = pe.profils(acteurs, {"R1": "p_R1", "S": "p_S", "N": "p_N"})
    out["unites"] = pe.unites(acteurs)
    return out


def principal() -> int:
    xs = bj.cohorte_complete([json.loads(l) for l in bj.REGISTRE.read_text(encoding="utf-8").splitlines() if l.strip()])
    bj.calculer(xs)
    calculer_n(xs)
    r = resumer(xs)
    RESUME.write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(r, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(principal())
