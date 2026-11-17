"""B par classe de référence pondérée (« noyau »), contre B, sur les questions fabriquées GDELT (bot 0.10.232, ombre).

Décision d'auteur du 2026-11-17 (18 h 39) : « à tenter en ombre, ça ne nous coûte absolument rien ». Inspiration : la
méthode de 0xnici/gta6-twitch-forecast (veille du 2026-11-17) : chaque cas passé de la classe de référence est pondéré
selon sa RESSEMBLANCE avec la cible au moment de la prévision, avec seulement ce qu'on savait alors.
Préenregistrement : preenregistrements/classe-reference.md. Aucun modèle de langue.

B actuel : pour le même pays et le même type, part (lissée) des mois antérieurs « oui », tous pesant 1.
B_noyau : TOUS les pays, même type ; chaque cas passé (pays, mois) dont la fenêtre « après » est finie avant d0 et où la
question se posait pèse
    w = max(0,005 ; exp(−½ (Δz / 1)² − ½ (Δm / 1)²))
  z = ln((avant + 1) / (moyenne des « avant » antérieurs du même pays + 1)) : où en est le pays par rapport à SON normal
      (au moins 3 mois antérieurs, sinon le cas n'entre pas) ;
  m = ln((avant + 1) / (avant du mois précédent + 1)) : l'élan du dernier mois.
  p = (Σ w·issue + 1) / (Σ w + 2) — le même lissage que B quand tous les poids valent 1.
Largeurs (1 ; 1) et plancher 0,005 FIXÉS D'AVANCE ; la grille (0,5 ; 1 ; 2)² n'est rapportée que pour vérifier que le
résultat tient sur un plateau, jamais pour choisir.

Jugement : perte log de B_noyau − B, sur les questions de confirmation (d0 à partir du 2025-11-01), bootstrap par mois,
risque es.risque_corrige(1). Meilleur si la borne haute < 0.

    python banc_classe_reference.py
"""
from __future__ import annotations

import json
import math
import os
import sys
from datetime import date, timedelta
from pathlib import Path

import numpy as np

import combinaisons as cb
import combinaisons_gdelt as cg

SORTIE = Path("registre") / "banc-classe-reference.json"
H_Z, H_M, PLANCHER = 1.0, 1.0, 0.005
GRILLE = (0.5, 1.0, 2.0)
HIST_MIN = 3


def cas(comptes: dict, jm: set[str], jp: set[str], dernier: date) -> list[dict]:
    """Un cas par (type, pays, d0) où la question se pose, avec z, m, issue et B actuel (mêmes règles que cg.questions)."""
    ancres = cg.mois(cg.DEBUT - timedelta(days=62), dernier - timedelta(days=cg.FENETRE))
    out = []
    for (typ, pays), serie in sorted(comptes.items()):
        couverts = jp if typ == "force" else jm
        avants: list[int] = []
        histo: list[tuple[date, int]] = []
        prec = None
        for d0 in ancres:
            avant = cg.somme(serie, d0 - timedelta(days=cg.FENETRE), cg.FENETRE, couverts)
            apres = cg.somme(serie, d0, cg.FENETRE, couverts)
            if avant is None or apres is None:
                prec = None
                continue
            issue = int(apres > avant)
            if avant >= cg.MIN_AVANT[typ] and d0 >= cg.DEBUT:
                connus = [y for fin, y in histo if fin <= d0]
                x = {"jeu": d0.isoformat(), "type": typ, "pays": pays, "issue": issue,
                     "p_B": (sum(connus) + 1) / (len(connus) + 2), "fin": (d0 + timedelta(days=cg.FENETRE)).isoformat()}
                if len(avants) >= HIST_MIN and prec is not None:
                    x["z"] = math.log((avant + 1) / (sum(avants) / len(avants) + 1))
                    x["m"] = math.log((avant + 1) / (prec + 1))
                out.append(x)
                histo.append((d0 + timedelta(days=cg.FENETRE), issue))
            avants.append(avant)
            prec = avant
    return out


def noyau(xs: list[dict], hz: float = H_Z, hm: float = H_M) -> None:
    """Ajoute p_K (B_noyau) aux cas qui ont z et m ; la classe : même type, tous pays, fenêtre « après » finie avant d0."""
    par_type: dict[str, list[dict]] = {}
    for x in xs:
        if "z" in x:
            par_type.setdefault(x["type"], []).append(x)
    for typ, ls in par_type.items():
        fin = np.array([x["fin"] for x in ls])
        z = np.array([x["z"] for x in ls])
        m = np.array([x["m"] for x in ls])
        y = np.array([x["issue"] for x in ls], dtype=float)
        for x in ls:
            ok = fin <= x["jeu"]
            if not ok.any():
                continue
            w = np.maximum(PLANCHER, np.exp(-0.5 * ((z[ok] - x["z"]) / hz) ** 2 - 0.5 * ((m[ok] - x["m"]) / hm) ** 2))
            x[f"p_K_{hz}_{hm}"] = float((w @ y[ok] + 1) / (w.sum() + 2))
        for x in ls:
            if f"p_K_{hz}_{hm}" in x and (hz, hm) == (H_Z, H_M):
                x["p_K"] = x[f"p_K_{hz}_{hm}"]


def perte(xs: list[dict], cle: str) -> float:
    return sum(cb.pl(x[cle], x["issue"]) for x in xs) / len(xs)


def resumer(xs: list[dict], coupure: str = cg.COUPURE) -> dict:
    import essais as es
    jug = [x for x in xs if "p_K" in x]
    explo = [x for x in jug if x["jeu"] < coupure]
    conf = [x for x in jug if x["jeu"] >= coupure]
    risque = es.risque_corrige(1)
    r = {"note": "perte log, plus bas = mieux ; aucun modèle de langue ; largeurs fixées d'avance",
         "coupure": coupure, "questions": len(xs), "avec_noyau": len(jug), "risque_corrige": round(risque, 6)}
    for nom, ls in (("exploration", explo), ("confirmation", conf)):
        if ls:
            r[nom] = {"n": len(ls), "perte_B": round(perte(ls, "p_B"), 4), "perte_noyau": round(perte(ls, "p_K"), 4),
                      "par_type": {t: {"n": len(s), "perte_B": round(perte(s, "p_B"), 4),
                                       "perte_noyau": round(perte(s, "p_K"), 4)}
                                   for t in sorted({x["type"] for x in ls}) for s in [[x for x in ls if x["type"] == t]]}}
    if len(conf) >= 30:
        ec = [(x["jeu"], cb.pl(x["p_K"], x["issue"]) - cb.pl(x["p_B"], x["issue"])) for x in conf]
        bas, haut = cb.bootstrap(ec, risque)
        r["ecart_moyen"] = round(sum(e for _, e in ec) / len(ec), 4)
        r["intervalle_corrige"] = [round(bas, 4), round(haut, 4)]
        r["verdict"] = "meilleur que B" if haut < 0 else ("moins bon que B" if bas > 0 else "non tranché")
    r["plateau"] = {f"{hz}/{hm}": round(sum(cb.pl(x[f"p_K_{hz}_{hm}"], x["issue"]) for x in conf
                                            if f"p_K_{hz}_{hm}" in x) / max(1, sum(f"p_K_{hz}_{hm}" in x for x in conf)), 4)
                    for hz in GRILLE for hm in GRILLE}
    return r


def principal() -> int:
    comptes, jm, jp = cg.charger()
    dernier = date.fromisoformat(max(jm))
    xs = cas(comptes, jm, jp, dernier)
    for hz in GRILLE:
        for hm in GRILLE:
            noyau(xs, hz, hm)
    r = resumer(xs)
    SORTIE.write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
    texte = json.dumps({k: v for k, v in r.items() if k != "note"}, ensure_ascii=False, indent=1)
    print(texte)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as fo:
            fo.write(f"## Classe de référence pondérée contre B\n\n```\n{texte}\n```\n")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
