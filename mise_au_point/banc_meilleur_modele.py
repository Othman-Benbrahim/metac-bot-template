"""Passage unique de la brique « meilleur modèle d'IA à une date » (preenregistrements/meilleur-modele-ia.md ;
décision de l'auteur du 2026-11-26, 14 h 55 : « oui »). Aucun modèle de langue."""
from __future__ import annotations

import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ICI = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ICI))
from mise_au_point.procedure_inertie import groupe, ll  # noqa: E402

RX = re.compile(r"Will (\w[\w\. ]*?) have the (top|best) AI model (?:on|at the end of) (.+?)\??$", re.I)


def principal():
    Q = []
    for l in open(ICI / "registre/jugement-questions.jsonl", encoding="utf-8"):
        d = json.loads(l)
        m = RX.search(d["titre"])
        if m and d.get("issue") in (0, 1) and d.get("resolue_le"):
            Q.append({**d, "labo": m.group(1).strip()})
    # dédoublonnage par titre et échéance (la même question peut figurer plusieurs fois)
    vus, U = set(), []
    for d in sorted(Q, key=lambda d: d["jeu"]):
        k = (d["titre"], d["resolue_le"])
        if k not in vus:
            vus.add(k)
            U.append(d)
    leader = {}
    for d in U:
        if d["issue"] == 1:
            leader[d["resolue_le"]] = d["labo"]
    echeances = sorted(leader)
    trans = [(echeances[i], echeances[i + 1]) for i in range(len(echeances) - 1)]
    print(f"{len(U)} questions distinctes ; {len(echeances)} échéances à leader connu : "
          f"{[(e, leader[e]) for e in echeances]} ; {len(trans)} transitions")
    if len(trans) < 8:
        print("moins de 8 transitions exploitables : on ne calcule pas (règle écrite avant)")
        return
    R = []
    for d in U:
        avant = [e for e in echeances if e < d["jeu"] and e < d["resolue_le"]]
        if not avant:
            continue
        connu = leader[avant[-1]]
        T = [(a, b) for a, b in trans if b < d["jeu"]]           # transitions entièrement connues à la date de jeu
        if len(T) < 2:
            continue
        maintien = sum(leader[a] == leader[b] for a, b in T) / len(T)
        nouveaux = Counter(leader[b] for a, b in T if leader[a] != leader[b])
        labos_ech = {x["labo"] for x in U if x["resolue_le"] == d["resolue_le"]}
        if d["labo"].lower() == connu.lower():
            p = maintien
        else:
            part = (nouveaux[d["labo"]] / sum(nouveaux.values())) if sum(nouveaux.values()) else 0
            if part == 0:
                part = 1 / max(1, len(labos_ech) - 1)
            p = (1 - maintien) * part
        R.append({**d, "p": min(max(p, 0.02), 0.98), "connu": connu, "maintien": round(maintien, 3), "n_trans": len(T)})
    # référence : part de oui de la famille hors groupe
    for r in R:
        autres = [x["issue"] for x in U if groupe(x["titre"]) != groupe(r["titre"])]
        r["ref"] = sum(autres) / len(autres)
        mix = 1 / (1 + math.exp(-(0.75 * math.log(r["ref"] / (1 - r["ref"])) +
                                  0.25 * math.log(r["p"] / (1 - r["p"])))))
        r["melange"] = min(max(mix, r["ref"] - 0.15), r["ref"] + 0.15)
    def moy(L, k):
        return round(sum(ll(x[k], x["issue"]) for x in L) / len(L), 4) if L else None
    a26 = [r for r in R if r["jeu"] >= "2026"]
    res = {"n": len(R), "regle": moy(R, "p"), "reference": moy(R, "ref"), "melange": moy(R, "melange"),
           "n_2026": len(a26), "regle_2026": moy(a26, "p"), "reference_2026": moy(a26, "ref"),
           "oui": sum(r["issue"] for r in R), "echeances": [(e, leader[e]) for e in echeances]}
    res["branchable"] = bool(R) and res["regle"] < res["reference"] and res["melange"] < res["reference"] and \
        (res["regle_2026"] is None or res["regle_2026"] < res["reference_2026"])
    json.dump({"resultat": res, "lignes": [{k: r[k] for k in ("titre", "jeu", "resolue_le", "issue", "p", "ref", "connu",
                                                                 "maintien", "n_trans")} for r in R]},
              open(ICI / "registre/meilleur-modele-ia.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(res, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    principal()
