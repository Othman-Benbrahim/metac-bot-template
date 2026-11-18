"""Banc de la crédibilité des acteurs (piste « confiance » de la confrontation Complex Systems Frameworks).

Bot 0.10.281. Décision d'auteur du 2026-11-18, 18 h 25 (« fais les trois »). Préenregistrement :
preenregistrements/credibilite-acteurs.md. Aucun appel à un modèle, aucune cote ni prévision de foule : seulement les
TITRES et les ISSUES des questions résolues (registre/jugement-questions.jsonl, ForecastBench, CC BY-SA 4.0).

Question posée : savoir QUI agit (banque centrale, exécutif, parlement ou tribunal, entreprise, organisation
internationale) et QUEL GENRE d'acte est attendu (annonce, acte concret) apporte-t-il quelque chose au taux de base
forme × horizon (R1) ? C'est une approximation grossière de la crédibilité : l'historique d'une CATÉGORIE d'acteurs,
pas celui d'un acteur nommé (trop peu de questions par acteur).

    python banc_credibilite.py
"""
from __future__ import annotations

import json
import math
import re
from pathlib import Path

import alphabet_pipeline as ap
import banc_jugement as bj

RESUME = Path("registre/banc-credibilite.json")
K = 5.0                                    # poids du taux R1 dans le rétrécissement (même valeur que bj.M)

SIGLES = [  # sensibles à la casse
    ("banque_centrale", r"\b(ECB|FOMC|PBOC|RBI|BoE|BoJ|SNB)\b"),
    ("organisation_internationale", r"\b(UN|EU|NATO|WHO|IMF|WTO|IAEA|OPEC\+?|G7|G20|ICC|ICJ|ASEAN|BRICS)\b"),
]
MOTS = [   # en minuscules, dans cet ordre (le premier trouvé l'emporte)
    ("banque_centrale", r"\b(fed|federal reserve|central bank|bank of england|bank of japan|bank of canada|"
                        r"reserve bank|people's bank of china)\b"),
    ("organisation_internationale", r"\b(united nations|security council|european union|european commission|"
                                    r"world bank|world health organization|african union)\b"),
    ("entreprise", r"\b(inc|corp|corporation|company|ltd|plc|openai|anthropic|google|alphabet|apple|microsoft|"
                   r"amazon|tesla|nvidia|spacex|xai|tsmc|samsung|boeing|netflix|intel|amd|deepseek|byd|tiktok|"
                   r"bytedance|starlink)\b"),
    ("legislatif_judiciaire", r"\b(congress|senate|house of representatives|parliament|court|judge|legislature|"
                              r"bundestag|knesset|duma|national assembly)\b"),
    ("executif", r"\b(president|prime minister|government|administration|white house|kremlin|minister|chancellor|"
                 r"trump|biden|putin|xi jinping|zelensky|zelenskyy|netanyahu|modi|macron|starmer|erdogan|erdoğan|"
                 r"khamenei|maduro|milei|lula|merz|carney|sheinbaum|ishiba|takaichi)\b"),
]
ACTIONS = [
    ("annonce", r"\b(announce|announces|announced|declare|declares|confirm|confirms|pledge|pledges|promise|"
                r"promises|commit|commits|publicly|state that|say that)\b"),
    ("acte", r"\b(sign|signs|pass|passes|ratify|ratifies|approve|approves|launch|launches|release|releases|cut|cuts|"
             r"raise|raises|hike|hikes|lower|lowers|impose|imposes|implement|implements|meet|meets|visit|visits|"
             r"withdraw|withdraws|join|joins|leave|leaves|deploy|deploys|invade|invades|strike|strikes|attack|"
             r"attacks|resign|resigns|fire|fires|nominate|nominates|veto|vetoes|issue|issues|ban|bans|sanction|"
             r"sanctions|recognize|recognizes|extend|extends|lift|lifts)\b"),
]


def categorie(titre: str) -> str:
    for nom, rx in SIGLES:
        if re.search(rx, titre or ""):
            return nom
    t = (titre or "").lower()
    for nom, rx in MOTS:
        if re.search(rx, t):
            return nom
    return "aucun"


def action(titre: str) -> str:
    t = (titre or "").lower()
    for nom, rx in ACTIONS:
        if re.search(rx, t):
            return nom
    return "autre"


def cellule(titre: str) -> str:
    return f"{categorie(titre)}|{action(titre)}"


def calculer_c(xs: list[dict]) -> None:
    """p_C : taux de « oui » des questions de la même cellule, CLOSES ET RÉSOLUES avant la date de jeu (autre
    question), rétréci vers R1 : (oui + K·R1) / (n + K). Sans fuite par construction."""
    for x in xs:
        x["cellule"] = cellule(x["titre"])
    for x in xs:
        cle = f'{x["source"]}:{x["id"]}'
        prec = [y for y in xs if y["cellule"] == x["cellule"] and f'{y["source"]}:{y["id"]}' != cle
                and max(y["resolue_le"], y.get("cloture", "")) < x["jeu"]]
        x["n_cellule"] = len(prec)
        x["p_C"] = (sum(y["issue"] for y in prec) + K * x["p_R1"]) / (len(prec) + K)


def _pl(p: float, y: int) -> float:
    p = min(max(p, 1e-3), 1 - 1e-3)
    return -math.log(p if y else 1 - p)


def donnees() -> list[dict]:
    xs = bj.cohorte_complete([json.loads(l) for l in bj.REGISTRE.read_text(encoding="utf-8").splitlines() if l.strip()])
    bj.calculer(xs)
    calculer_c(xs)
    return xs


def resumer(xs: list[dict]) -> dict:
    import profil_erreurs as pe
    import score_registre as sr
    vus, test = set(), []
    for x in sorted(xs, key=lambda x: x["jeu"]):
        cle = f'{x["source"]}:{x["id"]}'
        if cle in vus:
            continue
        vus.add(cle)                                 # première date de jeu de chaque question distincte
        if x["jeu"] >= bj.COUPURE and x["cellule"].split("|")[0] != "aucun":
            test.append(dict(x, question_id=f'{cle}:{x["jeu"]}'))
    out = {"version_bot": ap.VERSION_BOT, "questions_test": len(test),
           "note": "questions distinctes de 2026 dont l'acteur est reconnu ; C contre R1 (forme × horizon)"}
    if len(test) < 10:
        return dict(out, verdict="en attente")
    n = len(test)
    out["perte"] = {k: round(sum(_pl(x[f"p_{k}"], x["issue"]) for x in test) / n, 4) for k in ("R1", "S", "C")}
    cel: dict[str, list[int]] = {}
    for x in test:
        cel.setdefault(x["cellule"], []).append(x["issue"])
    out["cellules_test"] = {c: {"n": len(v), "oui": round(sum(v) / len(v), 3)} for c, v in sorted(cel.items())}
    out["critere"] = sr.critere_ombre_b([dict(x, p_B=x["p_R1"], o={"p": x["p_C"]}) for x in test], "o",
                                        "credibilite_acteurs", exclure_vus=False, bloc_par="question", tout_juger=True)
    out["secondaire_contre_S"] = sr.critere_ombre_b([dict(x, p_B=x["p_S"], o={"p": x["p_C"]}) for x in test], "o",
                                                    "credibilite_acteurs", exclure_vus=False, bloc_par="question",
                                                    tout_juger=True)
    out["profils"] = pe.profils(test, {"R1": "p_R1", "S": "p_S", "C": "p_C"})
    out["unites"] = pe.unites(test)
    return out


def principal() -> int:
    r = resumer(donnees())
    RESUME.write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(r, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(principal())
