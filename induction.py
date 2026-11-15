"""Observatoire inductif des indicateurs (0.10.134, décision d'auteur du 2026-11-15 : « réfléchir par induction plutôt
que par déduction »). AUCUN modèle de langue, aucun paramètre appris, rien de posté.

Chaque jeu ForecastBench est un lot indépendant. Pour chaque indicateur × famille d'événements × état de l'indicateur
(au-dessus / au-dessous de la normale, durci / inchangé…), on compare dans chaque lot les OUI observés aux OUI
attendus sous B corrigé. Une régularité n'est signalée comme CANDIDATE que si l'écart garde le même sens dans au moins
3 lots sur 4, sur au moins 4 lots et 20 questions (même règle que le garde-fou sur B). Une candidate n'est pas un
résultat : elle se pré-enregistre (sens fixé) et se juge sur les jeux suivants.

    python induction.py          (registre/banc-indicateurs-frais.jsonl, + registre/indicateurs-niche.jsonl)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

FICHIER = Path("registre") / "banc-indicateurs-frais.jsonl"
ETATS = {
    "pluie": (("au-dessus de la normale", lambda v: v > 0.5), ("au-dessous de la normale", lambda v: v < -0.5)),
    "fcdo": (("durci", lambda v: v > 0), ("inchangé", lambda v: v == 0)),
    "ioda": (("coupures", lambda v: v > 0), ("aucune coupure", lambda v: v == 0)),
    "wiki": (("attention en hausse", lambda v: v > 0.2), ("attention en baisse", lambda v: v < -0.2)),
    # 0.10.138 : indicateurs de niche (indicateurs_niche.py)
    "wikimodif": (("modifications politiques en hausse", lambda v: v > 0.3), ("modifications politiques en baisse", lambda v: v < -0.3)),
    "prix_alim": (("prix alimentaires en hausse (> 10 % sur un an)", lambda v: v > 0.10),
                  ("prix alimentaires stables ou en baisse", lambda v: v <= 0.02)),
    "vols": (("vols en baisse (> 20 %)", lambda v: v < -0.22), ("vols stables ou en hausse", lambda v: v > -0.05)),
}
NICHE = Path("registre") / "indicateurs-niche.jsonl"


def joindre_niche(lignes: list[dict]) -> list[dict]:
    """Ajoute aux lignes les indicateurs de niche mesurés pour le même pays et le même jeu."""
    if not NICHE.exists():
        return lignes
    n = {}
    for l in NICHE.read_text(encoding="utf-8").splitlines():
        if l.strip():
            x = json.loads(l)
            n[(x["pays"], x["jeu"])] = {**n.get((x["pays"], x["jeu"]), {}), **x}   # lignes complémentaires fusionnées
    out = []
    for x in lignes:
        m = n.get((x.get("pays"), x.get("jeu")))
        if m:
            x = dict(x, presents=dict(x.get("presents") or {}))
            for k in ("wikimodif", "prix_alim", "vols"):
                if (m.get(k) or {}).get("present"):
                    x[k] = m[k]["valeur"]
                    x["presents"][k] = True
        out.append(x)
    return out
LOTS_MIN, N_MIN, MEME_SENS = 4, 20, 0.75


def observer(lignes: list[dict]) -> dict:
    cases = {}
    for x in lignes:
        if x.get("issue") not in (0, 1) or x.get("p_B") is None:
            continue
        for k, etats in ETATS.items():
            if not (x.get("presents") or {}).get(k):
                continue
            for nom, test in etats:
                if test(float(x[k])):
                    c = cases.setdefault((k, x.get("famille", "?"), nom), {})
                    lot = c.setdefault(x["jeu"], [0, 0, 0.0])
                    lot[0] += 1
                    lot[1] += x["issue"]
                    lot[2] += float(x["p_B"])
    out, candidates = {}, []
    for (k, fam, nom), lots in sorted(cases.items()):
        n = sum(v[0] for v in lots.values())
        oui = sum(v[1] for v in lots.values())
        att = sum(v[2] for v in lots.values())
        signe = 1 if oui >= att else -1
        meme = sum(1 for v in lots.values() if (v[1] - v[2]) * signe > 0) / len(lots)
        cle = f"{k} {nom} → {fam}"
        out[cle] = {"lots": len(lots), "n": n, "oui": oui, "attendus_B": round(att, 1),
                    "sens": "plus que B" if signe > 0 else "moins que B", "meme_sens": round(meme, 2)}
        if len(lots) >= LOTS_MIN and n >= N_MIN and meme >= MEME_SENS:
            candidates.append(f"{cle} : {oui} oui pour {att:.1f} attendus ({out[cle]['sens']}), même sens dans "
                              f"{meme:.0%} de {len(lots)} lots, {n} questions")
    return {"regle": f"même sens dans ≥ {MEME_SENS:.0%} des lots, ≥ {LOTS_MIN} lots, ≥ {N_MIN} questions",
            "candidates": candidates, "cases": out}


def principal() -> int:
    if not FICHIER.exists():
        print("Aucun registre.")
        return 0
    r = observer(joindre_niche([json.loads(l) for l in FICHIER.read_text(encoding="utf-8").splitlines() if l.strip()]))
    print(f"Observatoire inductif ({r['regle']}) :")
    for c in r["candidates"] or ["aucune régularité répétée"]:
        print(" • " + c)
    print("\nToutes les cases :")
    for k, v in r["cases"].items():
        print(f"  {k:55s} {v['n']:3d} q, {v['oui']:2d} oui / {v['attendus_B']:5.1f} attendus, {v['sens']:12s}, "
              f"même sens {v['meme_sens']:.0%} de {v['lots']} lots")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
