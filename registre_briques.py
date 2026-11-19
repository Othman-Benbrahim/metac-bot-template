"""Registre des briques : structure × axe d'échelle × tranche (bot 0.10.369, ombre).

Préenregistrement : preenregistrements/registre-briques.md. Une brique ne vaut que pour des cas homologues À LA MÊME
ÉCHELLE ; l'axe d'échelle dépend de la structure (vitesse pour le seuil, taille pour la course). Statut par case :
valide, nuit, non tranché, insuffisant (la brique s'abstient). Aucun modèle de langue ; rien n'entre dans le bot.

    python registre_briques.py     # écrit registre/briques.json
"""
from __future__ import annotations

import json
import math
import re
import sys
from datetime import date
from pathlib import Path

REG = Path("registre")
SORTIE = REG / "briques.json"
MIN_N = 30
GRILLE_SIGMA = (2.5, 4.0, 6.0, 9.0, 13.0, 20.0)


def pl(p: float, y: int) -> float:
    p = min(0.98, max(0.02, p))
    return -math.log(p if y else 1 - p)


def statut(lignes: list[dict], risque: float) -> dict:
    """lignes : {id, issue, p_brique, p_ref}. Écart brique − référence, bootstrap par question (essais.py)."""
    import banc_jugement as bj
    n = len(lignes)
    if n < MIN_N:
        return {"n": n, "statut": "insuffisant"}
    ec = [(l["id"], pl(l["p_brique"], l["issue"]) - pl(l["p_ref"], l["issue"])) for l in lignes]
    bas, haut = bj.cb.bootstrap(ec, risque)
    m = lambda k: round(sum(pl(l[k], l["issue"]) for l in lignes) / n, 4)
    return {"n": n, "perte_brique": m("p_brique"), "perte_reference": m("p_ref"),
            "ecart": round(sum(e for _, e in ec) / n, 4), "intervalle": [round(bas, 4), round(haut, 4)],
            "statut": "valide" if haut < 0 else "nuit" if bas > 0 else "non tranché"}


# ---------------------------------------------------------------- seuil (axe : vitesse)

def tranche_seuil(x: dict) -> str | None:
    e = (x.get("ombre_b_echeance") or {}).get("ecart_median_jours")
    if e is None:
        return None
    freq = "quotidienne" if e <= 4 else "hebdomadaire" if e <= 10 else "mensuelle_ou_plus"
    h = (date.fromisoformat(x["question_id"].rsplit(":", 1)[1]) - date.fromisoformat(x["jeu"])).days
    return f"{freq}|{'h<=7' if h <= 7 else 'h>7'}"


def seuil() -> list[dict]:
    f = REG / "banc-echeance.jsonl"
    xs = [json.loads(l) for l in f.read_text(encoding="utf-8").splitlines() if l.strip()]
    xs = [x for x in xs if x.get("p_B") is not None and x.get("issue") in (0, 1)]
    out = []
    for x in xs:
        avant = [y for y in xs if y["jeu"] < x["jeu"] and y["source_question"] == x["source_question"]]
        ref = (sum(y["issue"] for y in avant) + 0.5) / (len(avant) + 1) if avant else 0.5
        out.append({"id": x["question_id"], "jeu": x["jeu"], "issue": x["issue"], "p_brique": x["p_B"], "p_ref": ref,
                    "tranche": tranche_seuil(x)})
    return out


# ---------------------------------------------------------------- course (axe : taille)

def tranche_course(titre: str) -> str:
    t = titre.lower()
    if re.search(r"primary|nominat|primaries", t):
        return "primaire"
    if re.search(r"governor|gubernatorial|mayor|state election|state parliament|province|regional|city|"
                 r"rhineland|sachsen|saxony|berlin state|bahia|minas gerais|rio de janeiro|quebec|seoul|ulsan|gangwon|"
                 r"welsh|scottish", t):
        return "infranational"
    return "national"


def course() -> list[dict]:
    import banc_scrutin as bs
    arch = bs.lire_archives()
    xs = [x for x in bs.questions() if x["forme"]]
    cas = []
    for x in xs:
        a = arch.get((x["forme"]["election"], x["jeu"]))
        if not a or not a.get("tableaux"):
            continue
        tabs = [{"colonnes": t["colonnes"], "lignes": [(date.fromisoformat(d), v) for d, v in t["lignes"]]} for t in a["tableaux"]]
        parts = bs.moyenne_sondages(tabs, date.fromisoformat(x["jeu"]), x["forme"]["sujet"])
        if not parts:
            continue
        fin = a.get("date_scrutin") or x.get("resolue_le") or x["jeu"]
        jr = (date.fromisoformat(fin[:10]) - date.fromisoformat(x["jeu"])).days
        cas.append({"x": x, "parts": parts, "jr": jr, "tranche": tranche_course(x["titre"]),
                    "p_sigma": {s: bs.probabilite(parts, x["forme"], jr, s) for s in GRILLE_SIGMA}})
    out = []
    for c in cas:
        x = c["x"]
        fin_c = lambda d: max(d["x"]["resolue_le"], d["x"].get("cloture", ""))
        passe = [d for d in cas if fin_c(d) < x["jeu"]]
        meme = [d for d in passe if d["tranche"] == c["tranche"]]
        base = meme if len(meme) >= 10 else passe if len(passe) >= 10 else None
        if base:
            sigma = min(GRILLE_SIGMA, key=lambda s: sum(pl(d["p_sigma"][s], d["x"]["issue"]) for d in base))
        else:
            sigma = 2.5
        out.append({"id": f'{x["source"]}:{x["id"]}:{x["jeu"]}', "jeu": x["jeu"], "issue": x["issue"],
                    "p_brique": c["p_sigma"][sigma], "p_ref": x["p_S"], "tranche": c["tranche"], "sigma": sigma})
    return out


def principal() -> int:
    import essais as es
    risque = es.risque_corrige(1)
    r = {"note": "perte log, plus bas = mieux ; ombre ; statut : valide | nuit | non tranché | insuffisant (< 30)",
         "risque_corrige": risque, "structures": {}}
    for nom, axe, lignes in (("seuil", "vitesse", seuil()), ("course", "taille", course())):
        cases = {}
        for t in sorted({l["tranche"] for l in lignes if l["tranche"]}):
            cases[t] = statut([l for l in lignes if l["tranche"] == t], risque)
        r["structures"][nom] = {"axe": axe, "ensemble": statut(lignes, risque), "tranches": cases}
        if nom == "course":
            r["structures"][nom]["sigma_retenus"] = {t: sorted({l["sigma"] for l in lignes if l["tranche"] == t}) for t in cases}
    SORTIE.write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(r, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(principal())
