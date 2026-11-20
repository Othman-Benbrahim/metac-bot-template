"""Brique « occurrence dans une fenêtre » (bot 0.10.378, ombre).

Préenregistrement : preenregistrements/brique-fenetre.md (essai brique_fenetre). Structure qui couvre environ 70 % des
questions résolues de Metaculus (registre/structures-questions.md) : « tel fait se produira-t-il avant telle date ? ».
Règles de l'auteur (2026-11-19) : un écosystème est fait d'acteurs placés sur quatre axes ; une brique ne vaut que pour
des cas homologues À LA MÊME ÉCHELLE. Ici : l'acteur qui doit agir (axe taille, avec sa vitesse propre) et la longueur
de la fenêtre (axe vitesse). Le taux de « oui » est MESURÉ, case par case, sur les seules questions passées (résolues et
closes avant la date jugée) ; une case de moins de 30 questions passées n'est pas utilisée (on remonte à l'acteur, puis
au taux de base). Aucun modèle de langue ; rien n'entre dans le bot.

    python brique_fenetre.py --couverture    # cases et effectifs, sans lire les issues
    python brique_fenetre.py [--foule]       # test préenregistré, une seule fois (--foule : repère descriptif)
"""
from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

import numpy as np

import structures_questions as sq

REG = Path("registre")
SORTIE = REG / "banc-brique-fenetre.json"
MIN_N = 30
M = 5.0
OCCURRENCE = {"autre", "procédure (décision, vote, accord)", "événement rare", "maintien"}

# acteur qui doit agir, du plus rapide au plus lent ; premier motif reconnu (règles écrites, ordre fixe)
ACTEURS = [
    ("militaire", r"\b(attack|strike|strikes|invade|invasion|capture|troops|military|missile|drone|bomb|airstrike|"
                  r"ground operation|blockade|offensive|occupy|seize|attacks|invades|war|nuclear test|test a nuclear)\b"),
    ("judiciaire", r"\b(court|judge|ruling|rule|indict|indicted|trial|convict|convicted|sentenced|lawsuit|pardon|"
                   r"supreme court|charged|charges|arrest|arrested|extradit)\b"),
    ("legislatif", r"\b(congress|senate|house of|parliament|bill|law|legislat|referendum|assembly|knesset|duma|"
                   r"bundestag|vote on|pass the|impeach|impeached)\b"),
    ("international", r"\b(treaty|agreement|ceasefire|cease-fire|peace|summit|talks|negotiat|sanction|un security|"
                      r"nato|united nations|g7|g20|opec|bilateral|trade deal|deal|normalize|diplomatic|iaea|recogni[sz]e)\b"),
    ("chef", r"\b(trump|putin|xi jinping|zelensky|zelenskyy|netanyahu|modi|erdogan|khamenei|macron|starmer|merz|"
             r"president|prime minister|chancellor|king|pope|supreme leader|musk|leader|out as)\b"),
    ("executif", r"\b(administration|department|agency|ministry|government|fda|epa|fed|federal reserve|central bank|"
                 r"commission|white house|pentagon|cabinet|executive order|tariff|tariffs)\b"),
    ("entreprise", r"\b(company|companies|inc|ipo|launch|release|openai|anthropic|google|apple|tesla|spacex|meta|"
                   r"microsoft|nvidia|amazon|starlink|waymo|ceo|ai model|deepseek|alibaba|moonshot|xai|grok|gpt|llm|"
                   r"video game|gta|spotify|netflix|disney)\b"),
    ("etat", r"\b(us|u\.s\.|united states|america|russia|russian|china|chinese|ukraine|ukrainian|iran|iranian|israel|"
             r"israeli|india|indian|uk|united kingdom|britain|british|france|french|germany|german|japan|japanese|"
             r"north korea|south korea|taiwan|saudi|turkey|turkish|brazil|mexico|canada|canadian|eu|european union|"
             r"venezuela|cuba|syria|syrian|gaza|hamas|hezbollah|houthi|pakistan|egypt|poland|italy|spain|spanish|"
             r"argentina|colombia|nigeria|south africa|australia|lebanon|iraq|afghanistan|qatar|uae)\b"),
    ("nature", r"\b(earthquake|hurricane|storm|temperature|degrees|virus|outbreak|pandemic|flood|wildfire|eruption|"
               r"cases)\b"),
]


def acteur(titre: str) -> str:
    t = sq.DATES.sub(" ", titre or "").lower()
    return next((n for n, r in ACTEURS if re.search(r, t)), "autre")


def fenetre(h: int | None) -> str:
    if h is None:
        return "?"
    return "<=7" if h <= 7 else "8-30" if h <= 30 else "31-90" if h <= 90 else "91-180" if h <= 180 else ">180"


def cohorte() -> list[dict]:
    import banc_jugement as bj
    import banc_proxemie as bp
    xs = [json.loads(l) for l in bj.REGISTRE.read_text(encoding="utf-8").splitlines() if l.strip()]
    xs = [x for x in xs if not bp.COMBINEE.search(x.get("titre") or "")]
    xs = bj.cohorte_complete(xs)
    for x in xs:
        x["structure"] = sq.structure(x["titre"])
        x["acteur"], x["fenetre"] = acteur(x["titre"]), fenetre(x["horizon"])
    return xs


def calculer(xs: list[dict]) -> None:
    """p_F : taux de « oui » de la case acteur × fenêtre parmi les questions d'occurrence passées (≥ 30), sinon de
    l'acteur (≥ 30), sinon le taux de base p_R1 ; chaque niveau rétréci vers le niveau supérieur (poids M)."""
    occ = [x for x in xs if x["structure"] in OCCURRENCE]
    fin = np.array([max(x["resolue_le"], x.get("cloture", "")) for x in occ])
    ids = np.array([f'{x["source"]}:{x["id"]}' for x in occ])
    y = np.array([x["issue"] for x in occ], dtype=float)
    act = np.array([x["acteur"] for x in occ])
    fen = np.array([x["fenetre"] for x in occ])
    for i, x in enumerate(occ):
        ok = (fin < x["jeu"]) & (ids != ids[i])
        p, niveau = x["p_R1"], "base"
        a = ok & (act == x["acteur"])
        if a.sum() >= MIN_N:
            p, niveau = (y[a].sum() + M * p) / (a.sum() + M), "acteur"
            c = a & (fen == x["fenetre"])
            if c.sum() >= MIN_N:
                p, niveau = (y[c].sum() + M * p) / (c.sum() + M), "acteur×fenêtre"
        x["p_F"], x["niveau_F"] = float(min(0.98, max(0.02, p))), niveau


def couverture() -> int:
    xs = cohorte()
    import banc_jugement as bj
    occ = [x for x in xs if x["structure"] in OCCURRENCE]
    conf = [x for x in occ if x["jeu"] >= bj.COUPURE]
    cases = Counter((x["acteur"], x["fenetre"]) for x in occ)
    r = {"questions": len(xs), "occurrence": len(occ), "occurrence_confirmation": len(conf),
         "par_acteur": dict(Counter(x["acteur"] for x in occ).most_common()),
         "par_fenetre": dict(Counter(x["fenetre"] for x in occ).most_common()),
         "cases_de_30_ou_plus": sum(1 for n in cases.values() if n >= MIN_N), "cases": len(cases),
         "note": "aucune issue lue ; effectifs totaux (le test n'utilise que les questions passées à chaque date)"}
    print(json.dumps(r, ensure_ascii=False, indent=1))
    return 0


def evaluer(avec_foule: bool) -> int:
    import banc_jugement as bj
    import essais as es
    cb = bj.cb
    foule = {}
    if avec_foule:
        _, foule = asyncio.run(bj.recolter(date(2024, 7, 1)))
    xs = cohorte()
    bj.calculer(xs)
    calculer(xs)
    conf = [x for x in xs if x["structure"] in OCCURRENCE and x["jeu"] >= bj.COUPURE]
    pm = lambda s, k: round(sum(cb.pl(x[k], x["issue"]) for x in s) / len(s), 4) if s else None
    ec = [(f'{x["source"]}:{x["id"]}', cb.pl(x["p_F"], x["issue"]) - cb.pl(x["p_S"], x["issue"])) for x in conf]
    eb = [(f'{x["source"]}:{x["id"]}', cb.pl(x["p_F"], x["issue"]) - cb.pl(x["p_R1"], x["issue"])) for x in conf]
    risque = es.risque_corrige(1)
    bas, haut = cb.bootstrap(ec, risque)
    bas_b, haut_b = cb.bootstrap(eb, risque)
    verdict = lambda b, h, nom: (f"la brique bat {nom}" if h < 0 else f"la brique perd contre {nom}" if b > 0 else "non tranché")
    groupe = lambda cle: {k: {"n": len(v), "part_oui": round(sum(x["issue"] for x in v) / len(v), 3),
                              "perte_base": pm(v, "p_R1"), "perte_semblables": pm(v, "p_S"), "perte_brique": pm(v, "p_F")}
                          for k in sorted({x[cle] for x in conf}) for v in [[x for x in conf if x[cle] == k]]}
    fc = [(x, foule[(x["source"], x["id"], x["jeu"])]) for x in conf if (x["source"], x["id"], x["jeu"]) in foule]
    r = {"n_confirmation": len(conf), "questions_distinctes": len({k for k, _ in ec}),
         "perte": {"taux_de_base": pm(conf, "p_R1"), "semblables": pm(conf, "p_S"), "brique": pm(conf, "p_F")},
         "contre_semblables": {"ecart": round(sum(e for _, e in ec) / len(ec), 4), "intervalle_corrige": [round(bas, 4), round(haut, 4)],
                               "verdict": verdict(bas, haut, "les semblables")},
         "contre_taux_de_base": {"ecart": round(sum(e for _, e in eb) / len(eb), 4), "intervalle_corrige": [round(bas_b, 4), round(haut_b, 4)],
                                 "verdict": verdict(bas_b, haut_b, "le taux de base")},
         "foule_descriptif": ({"n": len(fc), "perte_foule": round(sum(cb.pl(f, x["issue"]) for x, f in fc) / len(fc), 4),
                               "perte_brique_memes": round(sum(cb.pl(x["p_F"], x["issue"]) for x, _ in fc) / len(fc), 4)}
                              if fc else None),
         "niveaux": dict(Counter(x["niveau_F"] for x in conf)),
         "par_acteur": groupe("acteur"), "par_fenetre": groupe("fenetre"),
         "risque_corrige": risque,
         "note": "perte log, plus bas = mieux ; questions d'occurrence ; la foule n'est qu'un repère descriptif, jamais une entrée ; ombre"}
    SORTIE.write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(r, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("--couverture", action="store_true")
    a.add_argument("--foule", action="store_true")
    o = a.parse_args()
    sys.exit(couverture() if o.couverture else evaluer(o.foule))
