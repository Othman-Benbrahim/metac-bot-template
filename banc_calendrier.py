"""Banc « le calendrier tient-il ? » (preenregistrements/calendrier-etapes.md). Une passe, Claude Haiku 4.5."""
from __future__ import annotations

import asyncio
import datetime as dt
import json
import math
import random
import re
from collections import defaultdict

import alphabet_modeles as am
import structures_questions as sq

MODELE = "anthropic/claude-haiku-4-5"
COUPURE = "2025-08-01"
CONSIGNE = """Today is {jour}. Question: "{titre}"
The question resolves YES only if the event happens by {echeance} ({jours} days from today).

Think about what concretely has to happen for YES (steps: decisions, votes, procedures, construction, announcements...)
and the usual MINIMUM time those steps take. Then answer with ONE JSON object and nothing else:
{{"etapes": ["...", "..."], "duree_min_jours": <integer>, "verdict": "tient" | "ne_tient_pas" | "sans_objet"}}
- "tient": the necessary steps can fit in the remaining time;
- "ne_tient_pas": even at the fastest usual pace, they cannot fit;
- "sans_objet": nothing has to be accomplished (status quo, staying in office, market level, natural event...)."""


def borne(p):
    return min(max(p, 0.02), 0.98)


def ll(p, y):
    return -math.log(p if y else 1 - p)


async def principal():
    Q = [json.loads(l) for l in open("registre/jugement-questions.jsonl", encoding="utf-8")]
    M = [q for q in Q if q["source"] == "metaculus" and q.get("issue") in (0, 1) and q.get("horizon") not in (None, "")]
    avant = [q for q in M if (q.get("resolue_le") or "") < COUPURE]
    elig = [q for q in M if (q.get("resolue_le") or "") >= COUPURE]
    jeu = random.Random(20261126).sample(sorted(elig, key=lambda q: q["id"]), 200)
    f = defaultdict(list)
    for q in avant:
        f[sq.structure(q["titre"])].append(q["issue"])
    g = sum(q["issue"] for q in avant) / len(avant)
    ref = lambda q: borne(sum(f[sq.structure(q["titre"])]) / len(f[sq.structure(q["titre"])])) if f.get(sq.structure(q["titre"])) else borne(g)
    m = am.llm(MODELE, temperature=0, timeout=120, allowed_tries=2, max_tokens=600)
    R = []
    for i, q in enumerate(jeu):
        j0 = dt.date.fromisoformat(q["jeu"])
        ech = j0 + dt.timedelta(days=int(float(q["horizon"])))
        try:
            rep = await m.invoke(CONSIGNE.format(jour=j0, titre=q["titre"], echeance=ech, jours=int(float(q["horizon"]))))
            x = json.loads(re.search(r"\{.*\}", rep, re.S).group(0))
            v = x.get("verdict") if x.get("verdict") in ("tient", "ne_tient_pas", "sans_objet") else "sans_objet"
        except Exception as e:
            x, v = {"erreur": type(e).__name__}, "sans_objet"
        R.append({"id": q["id"], "titre": q["titre"], "y": q["issue"], "verdict": v, "ref": ref(q),
                  "duree_min_jours": x.get("duree_min_jours"), "jours": int(float(q["horizon"]))})
        if i % 20 == 0:
            print(i, v, q["titre"][:80], flush=True)
    N = [r for r in R if r["verdict"] == "ne_tient_pas"]
    for r in R:
        if r["verdict"] != "ne_tient_pas":
            r["adj"] = r["ref"]
            continue
        autres = [x["y"] for x in N if x is not r]
        w = len(autres) / (len(autres) + 10)
        taux = sum(autres) / len(autres) if autres else r["ref"]
        r["adj"] = borne(w * taux + (1 - w) * r["ref"])
    d = [ll(r["ref"], r["y"]) - ll(r["adj"], r["y"]) for r in R]
    rnd = random.Random(20261126)
    boot = sorted(sum(rnd.choice(d) for _ in d) / len(d) for _ in range(1000))
    classes = {k: {"n": sum(r["verdict"] == k for r in R), "oui": sum(r["y"] for r in R if r["verdict"] == k),
                   "ref_moy": round(sum(r["ref"] for r in R if r["verdict"] == k) / max(1, sum(r["verdict"] == k for r in R)), 3)}
               for k in ("tient", "ne_tient_pas", "sans_objet")}
    nt = classes["ne_tient_pas"]
    res = {"modele": MODELE, "n": len(R), "classes": classes, "gain": round(sum(d) / len(d), 4),
           "ic90_gain": [round(boot[50], 4), round(boot[949], 4)],
           "perte_ref": round(sum(ll(r["ref"], r["y"]) for r in R) / len(R), 4),
           "perte_adj": round(sum(ll(r["adj"], r["y"]) for r in R) / len(R), 4)}
    res["retenu"] = (nt["n"] >= 15 and nt["oui"] / max(1, nt["n"]) <= nt["ref_moy"] / 2 and res["gain"] >= 0.005
                     and res["ic90_gain"][0] > 0)
    json.dump({"resultat": res, "lignes": R}, open("banc_calendrier.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(res, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    asyncio.run(principal())
