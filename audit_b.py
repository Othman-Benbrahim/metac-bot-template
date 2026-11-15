"""Garde-fou sur le taux de base B (0.10.130, décision d'auteur du 2026-11-15, après l'erreur ACLED « dix fois plus »).

« Institutionnaliser le doute » (P. Sauveton, Opex News, 2026, d'après Clausewitz) : le code qui calcule B a une
autorité que le modèle de langue ne conteste pas (il a repris 74 fois un 31 % impossible). Ce module compare, pour
chaque FORME de question, ce que B annonce à ce qui arrive : nombre de OUI observé contre nombre attendu sous les
probabilités annoncées (loi de Poisson-binomiale, approximation normale). Une forme dont l'écart dépasse 3 écarts-types
sur au moins 20 questions résolues est signalée : soit B est faux pour cette forme, soit la classe de référence est
mauvaise. Ce n'est pas un recalibrage : rien n'est corrigé automatiquement, on regarde le code.

    python audit_b.py            (tous les registres qui portent p_B et une issue)
"""
from __future__ import annotations

import json
import math
import re
import sys
from pathlib import Path

REGISTRES = ("banc-a.jsonl", "banc-b.jsonl", "banc-m.jsonl", "banc-indicateurs-frais.jsonl", "banc-indicateurs.jsonl")
SEUIL_Z = 3.0
N_MIN = 20


def forme(ligne: dict) -> str:
    """Forme de la question : source, puis gabarit du titre (noms propres, nombres et dates effacés)."""
    src = ligne.get("source_question") or ligne.get("source") or "?"
    t = (ligne.get("titre") or "").split("\n")[0]
    if src == "acled" or "ACLED" in t or re.search(r"'[^']+' in .+ for the 30 days", t):
        dix = "dix fois" if "ten times" in t else "une fois"
        m = re.search(r"'([^']+)'", t)
        return f"acled · {dix} · {m.group(1) if m else 'fatalities'}"
    g = re.sub(r"\d{4}-\d{2}-\d{2}", "<date>", t)
    g = re.sub(r"\d+([.,]\d+)?", "<n>", g)
    g = re.sub(r"\"[^\"]*\"|'[^']*'|\([^)]*\)", "<x>", g)
    g = re.sub(r"\b[A-Z][\w&.-]*(\s+[A-Z][\w&.-]*)*", "<Nom>", g)
    return f"{src} · {g[:90]}"


def auditer(lignes: list[dict], seuil_z: float = SEUIL_Z, n_min: int = N_MIN) -> dict:
    groupes: dict[str, list[dict]] = {}
    vus = set()
    for x in lignes:
        if x.get("p_B") is None or x.get("issue") not in (0, 1) or x.get("question_id") in vus:
            continue
        vus.add(x.get("question_id"))
        f = forme(x)
        groupes.setdefault(f, []).append(x)
        if f.startswith("acled · "):                      # niveau regroupé : « dix fois » / « une fois », tous types
            groupes.setdefault(" · ".join(f.split(" · ")[:2]) + " · (tous types)", []).append(x)
    out, alertes, surveiller = {}, [], []
    for f, s in sorted(groupes.items()):
        n = len(s)
        attendu = sum(float(x["p_B"]) for x in s)
        var = sum(float(x["p_B"]) * (1 - float(x["p_B"])) for x in s)
        obs = sum(x["issue"] for x in s)
        z = (obs - attendu) / math.sqrt(var) if var > 0 else 0.0
        # questions d'un même jeu souvent corrélées (un mouvement de marché les fait toutes tomber ensemble) : l'écart
        # doit se retrouver dans au moins 3 jeux, et dans le même sens pour au moins 3 jeux sur 4
        par_jeu: dict[str, float] = {}
        for x in s:
            par_jeu[x.get("jeu", "?")] = par_jeu.get(x.get("jeu", "?"), 0.0) + x["issue"] - float(x["p_B"])
        signe = 1 if obs >= attendu else -1
        meme_sens = sum(1 for v in par_jeu.values() if v * signe > 0) / len(par_jeu)
        out[f] = {"n": n, "jeux": len(par_jeu), "annonce_moyen": round(attendu / n, 3), "observe": round(obs / n, 3),
                  "oui": obs, "oui_attendus": round(attendu, 1), "z": round(z, 2), "jeux_meme_sens": round(meme_sens, 2)}
        if n >= n_min and abs(z) > seuil_z:
            msg = (f"{f} : B annonce {attendu / n:.0%} en moyenne, {obs} oui sur {n} ({obs / n:.0%}), "
                   f"écart {z:+.1f} écarts-types, même sens dans {meme_sens:.0%} de {len(par_jeu)} jeux")
            (alertes if len(par_jeu) >= 3 and meme_sens >= 0.75 else surveiller).append(msg)
    return {"seuil": f"|z| > {seuil_z} sur au moins {n_min} questions, écart répété dans au moins 3 jeux",
            "alertes": alertes, "a_surveiller": surveiller, "formes": out}


def version(x: dict) -> tuple:
    try:
        return tuple(int(t) for t in str(x.get("version_bot", "0")).split("."))
    except ValueError:
        return (0,)


def pour_resume(lignes: list[dict]) -> dict:
    """À placer dans le résumé d'un banc : lignes calculées après la correction du B ACLED (0.10.127) seulement."""
    r = auditer([x for x in lignes if version(x) >= (0, 10, 127)])
    return {"alertes": r["alertes"], "a_surveiller": r["a_surveiller"], "seuil": r["seuil"]}


def lire(chemin: Path) -> list[dict]:
    if not chemin.exists():
        return []
    return [json.loads(l) for l in chemin.read_text(encoding="utf-8").splitlines() if l.strip()]


def titres_complets(lignes: list[dict]) -> list[dict]:
    """Le registre des indicateurs ne garde pas les titres : on les reprend au banc du bras A."""
    a = {x["question_id"]: x for x in lire(Path("registre") / "banc-a.jsonl")}
    return [dict(x, titre=x.get("titre") or a.get(x.get("question_id"), {}).get("titre", ""),
                 source_question=x.get("source_question") or a.get(x.get("question_id"), {}).get("source_question"))
            for x in lignes]


def principal() -> int:
    toutes = []
    for nom in REGISTRES:
        toutes += [dict(x, _registre=nom) for x in lire(Path("registre") / nom)]
    r = auditer(titres_complets(toutes))
    print(f"Garde-fou sur B ({r['seuil']}) :")
    for a in r["alertes"] or ["aucune alerte"]:
        print(" ⚠ " + a if r["alertes"] else " " + a)
    for a in r["a_surveiller"]:
        print(" · à surveiller (peu de jeux ou sens instable, mouvement commun probable) : " + a)
    return 1 if r["alertes"] else 0


if __name__ == "__main__":
    sys.exit(principal())
