"""Ombre « B autorégressif » rejouée sur les questions de séries déjà au registre (0.10.92, sans modèle de langue).

Pour chaque ligne du banc ForecastBench (FRED, DBnomics) qui a une issue, la série est retéléchargée bornée STRICTEMENT
avant la date d'information (millésime ALFRED pour FRED quand il existe, comme pour B), puis `b_ar` est calculé avec la
règle fixée dans `banc_forecastbench.py`. Sortie : perte log de B (enregistré) et de B_AR sur les mêmes questions, écart
apparié avec intervalle bootstrap par blocs « jeu × source » ; détail dans registre/ombre-b-ar-retro.json. Rien n'est
posté ; le registre des prévisions n'est pas modifié.

    python retro_b_ar.py
"""
from __future__ import annotations

import asyncio
import json
import math
import random
import sys
from datetime import date

import alphabet_pipeline as ap
import alphabet_retro as ar
import banc_forecastbench as fb


def perte(p: float, y: int) -> float:
    p = min(max(p, 1e-3), 1 - 1e-3)
    return -math.log(p if y else 1 - p)


async def serie(x: dict, d0: date) -> list[dict]:
    import alphabet_puits as apz
    src = x["question_id"].split(":")[2]
    if src == "fred":
        sid = x["question_id"].split(":")[3]
        try:
            r = await apz.fred(sid, avant=d0)
        except Exception:
            r = {}
        if len(r.get("points") or []) < 20:
            r = await apz.fred(sid)
        return r.get("points") or []
    url = x.get("url") or ""
    if "db.nomics.world/" not in url:
        return []
    r = await apz.dbnomics(url.split("db.nomics.world/", 1)[1], avant=d0)
    return r.get("points") or []


async def principal() -> int:
    f = ap.REGISTRE / ar.RETRO
    L = [json.loads(l) for l in f.read_text(encoding="utf-8").splitlines() if l.strip()] if f.is_file() else []
    vus, items = set(), []
    for x in L:
        qid = x.get("question_id", "")
        if (x.get("banc") != "forecastbench" or x.get("issue") not in (0, 1) or x.get("p_B") is None
                or qid.split(":")[2:3] not in (["fred"], ["dbnomics"]) or qid in vus):
            continue
        vus.add(qid)
        jeu = x.get("jeu") or qid.split(":")[1]
        d0 = date.fromisoformat(jeu)
        h = (date.fromisoformat(x["resolution"]) - d0).days
        try:
            pts = await serie(x, d0)
            o = fb.b_ar(pts, h, d0)
        except Exception as e:
            o = {"erreur": f"{type(e).__name__}: {e}"[:200]}
        items.append({"question_id": qid, "bloc": f"{jeu}:{qid.split(':')[2]}", "issue": x["issue"],
                      "p_B": x["p_B"], "b_ar": o})
        print(f"{qid[:60]:60} B {x['p_B']:.3f}  B_AR {(o or {}).get('p', float('nan')):.3f}  issue {x['issue']}", flush=True)
    ok = [i for i in items if isinstance(i["b_ar"], dict) and i["b_ar"].get("p") is not None]
    rap = {"version": ap.VERSION_BOT, "questions": len(items), "comparables": len(ok)}
    if ok:
        ec = [perte(i["b_ar"]["p"], i["issue"]) - perte(i["p_B"], i["issue"]) for i in ok]
        blocs: dict[str, list[float]] = {}
        for i, e in zip(ok, ec):
            blocs.setdefault(i["bloc"], []).append(e)
        rnd = random.Random(0)
        cles = sorted(blocs)
        boots = sorted((lambda s: sum(s) / len(s))([e for _ in cles for e in blocs[rnd.choice(cles)]]) for _ in range(2000))
        boots_l = sorted(sum(rnd.choice(ec) for _ in ec) / len(ec) for _ in range(2000))
        rap.update(perte_B=sum(perte(i["p_B"], i["issue"]) for i in ok) / len(ok),
                   perte_B_AR=sum(perte(i["b_ar"]["p"], i["issue"]) for i in ok) / len(ok),
                   ecart_moyen=sum(ec) / len(ec), intervalle_90_par_question=[boots_l[100], boots_l[1899]],
                   intervalle_90_par_blocs=[boots[100], boots[1899]], blocs=len(cles),
                   lecture="écart = perte(B_AR) − perte(B) ; négatif : B_AR meilleur")
    (ap.REGISTRE / "ombre-b-ar-retro.json").write_text(json.dumps({"bilan": rap, "questions": items}, ensure_ascii=False,
                                                                 indent=1), encoding="utf-8")
    print(json.dumps(rap, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(principal()))
