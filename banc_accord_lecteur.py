"""Accord du lecteur de l'alphabet : stabilité (même modèle, deux fois) et accord entre modèles, sur dossiers complets.

Décision d'auteur du 2026-11-22, 5 h 10. Préenregistrement : preenregistrements/accord-lecteur.md. Descriptif : rien dans
le bot. Mesure le lecteur réellement employé (les sept notes de la matriochka M, banc_jugement_alphabet.consigne_notes)
sur les mêmes entrées, recherche gelée comprise ; aucune recherche neuve.

    python banc_accord_lecteur.py --n 60 --budget 3 --budget-bedrock 1
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

FICHIER = Path("registre/banc-accord-lecteur.jsonl")
RESUME = Path("registre/banc-accord-lecteur.json")
CODEURS = {"r1": "azure_ai/gpt-5-mini", "r2": "azure_ai/gpt-5-mini",
           "x": "bedrock/global.anthropic.claude-haiku-4-5-20251001-v1:0"}
COMPTE = {"r1": "azure", "r2": "azure", "x": "bedrock"}
SEUILS = {"stable": 0.6, "instable": 0.4, "commun": 0.4, "non_commun": 0.2}


def kappa_pondere(a: list[int], b: list[int], k: int = 4) -> float | None:
    """κ pondéré quadratique (Cohen 1968) pour deux suites de notes 1..k appariées."""
    n = len(a)
    if n == 0 or n != len(b):
        return None
    w = lambda i, j: ((i - j) ** 2) / ((k - 1) ** 2)
    obs = sum(w(x, y) for x, y in zip(a, b)) / n
    pa = [sum(x == i for x in a) / n for i in range(1, k + 1)]
    pb = [sum(y == j for y in b) / n for j in range(1, k + 1)]
    att = sum(pa[i] * pb[j] * w(i + 1, j + 1) for i in range(k) for j in range(k))
    if att == 0:
        return None                 # aucune variation attendue : κ indéfini (tout le monde a mis la même note)
    return round(1 - obs / att, 3)


def comparer(ls: list[dict], u: str, v: str, cles: tuple[str, ...]) -> dict:
    par = {}
    for c in cles:
        paires = [(x[u]["notes"][c], x[v]["notes"][c]) for x in ls
                  if c in (x.get(u) or {}).get("notes", {}) and c in (x.get(v) or {}).get("notes", {})]
        a, b = [p[0] for p in paires], [p[1] for p in paires]
        par[c] = {"n": len(paires), "kappa_pondere": kappa_pondere(a, b),
                  "accord_exact": round(sum(x == y for x, y in paires) / len(paires), 3) if paires else None,
                  "ecart_moyen": round(sum(abs(x - y) for x, y in paires) / len(paires), 3) if paires else None}
    vals = [p["kappa_pondere"] for p in par.values() if p["kappa_pondere"] is not None]
    return {"par_critere": par, "kappa_moyen": round(sum(vals) / len(vals), 3) if vals else None}


def resumer(ls: list[dict], cles: tuple[str, ...], sautees: int = 0) -> dict:
    ok = [x for x in ls if all((x.get(c) or {}).get("notes") for c in ("r1", "r2", "x"))]
    out = {"n_lignes": len(ls), "n_completes": len(ok), "sautees_sans_recherche_gelee": sautees,
           "note": "descriptif ; mêmes entrées pour tous ; notes 1 à 4 des sept critères de la matriochka M"}
    if not ok:
        return out
    st, ac = comparer(ok, "r1", "r2", cles), comparer(ok, "r1", "x", cles)
    out["stabilite_r1_r2"], out["accord_r1_x"] = st, ac
    r0 = [x for x in ok if (x.get("r0") or {}).get("notes")]
    out["descriptif_r0_r1"] = comparer(r0, "r0", "r1", cles) if r0 else None
    out["part_des_2"] = {c: {k: round(sum(x[c]["notes"].get(k) == 2 for x in ok) / len(ok), 3) for k in cles}
                         for c in ("r1", "r2", "x")}
    dp = [abs(x["r1"]["p"] - x["r2"]["p"]) for x in ok if x["r1"].get("p") is not None and x["r2"].get("p") is not None]
    out["probabilite_r1_r2"] = {"n": len(dp), "ecart_moyen": round(sum(dp) / len(dp), 3) if dp else None,
                                "part_ecart_sup_0_10": round(sum(d > 0.10 for d in dp) / len(dp), 3) if dp else None}
    ks, ka = st["kappa_moyen"], ac["kappa_moyen"]
    out["lecture"] = {
        "stabilite": None if ks is None else ("stable" if ks >= SEUILS["stable"] else
                                              "instable" if ks < SEUILS["instable"] else "entre les deux"),
        "accord": None if ka is None else ("lecture commune" if ka >= SEUILS["commun"] else
                                           "pas de langage commun" if ka < SEUILS["non_commun"] else "entre les deux"),
        "criteres_a_reformuler": [k for k, p in st["par_critere"].items()
                                  if p["kappa_pondere"] is not None and p["kappa_pondere"] < SEUILS["instable"]],
        "seuils": SEUILS}
    return out


def lignes() -> list[dict]:
    return [json.loads(l) for l in FICHIER.read_text(encoding="utf-8").splitlines() if l.strip()] if FICHIER.exists() else []


async def _pas_de_recherche_neuve(*_a, **_k):
    raise RuntimeError("banc d'accord : recherche gelée seulement")


async def principal(n: int, budget: float, budget_bedrock: float) -> int:
    from forecasting_tools import MonetaryCostManager
    import alphabet_modeles as am
    import alphabet_pipeline as ap
    import banc_forecastbench as fb
    import banc_jugement_alphabet as bja
    import trace_recherche as tr
    from datetime import datetime, timezone

    faites_m = {x["question_id"]: x for x in bja.lignes()
                if not x.get("exclue") and x.get("p_M") is not None and len(x.get("notes") or {}) == len(bja.CLES)}
    deja = {x["question_id"] for x in lignes()}
    cumul = {"azure": 0.0, "bedrock": 0.0}
    pire = {"azure": 0.0, "bedrock": 0.0}
    plafond = {"azure": budget, "bedrock": budget_bedrock}
    textes: dict[str, dict] = {}
    retenues, sautees = len(deja), 0
    FICHIER.parent.mkdir(exist_ok=True)
    with FICHIER.open("a", encoding="utf-8") as f:
        for x in bja.candidates():
            qid = f'{x["source"]}:{x["id"]}:{x["jeu"]}'
            if retenues >= n:
                break
            if qid not in faites_m or qid in deja:
                continue
            if any(fb.depasse(cumul[c], pire[c], plafond[c]) for c in cumul):
                print(f"Plafond atteint ({cumul}). Arrêt.")
                break
            info = datetime.fromisoformat(x["jeu"]).replace(tzinfo=timezone.utc)
            rech, du_cache = await tr.chercher_fige(qid, x["titre"], info, _pas_de_recherche_neuve)
            if not du_cache:
                sautees += 1
                continue
            if x["jeu"] not in textes:
                try:
                    qs = await fb._json(f"{fb.DEPOT}/question_sets/{x['jeu']}-llm.json")
                    textes[x["jeu"]] = {str(q["id"]): q for q in qs.get("questions", [])}
                except Exception:
                    textes[x["jeu"]] = {}
            src = textes[x["jeu"]].get(x["id"])
            if not src:
                sautees += 1
                continue
            q = {"titre": x["titre"], "cloture": x["cloture"],
                 "criteres": str(src.get("market_info_resolution_criteria") or src.get("resolution_criteria") or ""),
                 "contexte": str(src.get("background") or "")}
            p_b = float(x["p_S"])
            ligne = {"type": "banc_accord_lecteur", "question_id": qid, "jeu": x["jeu"], "titre": x["titre"],
                     "version_bot": ap.VERSION_BOT, "r0": {"notes": {k: v["note"] for k, v in faites_m[qid]["notes"].items()}}}
            for c, modele in CODEURS.items():
                with MonetaryCostManager() as cm:
                    try:
                        r = ap.extraire_json(await am.llm(modele, temperature=0.2, timeout=300, allowed_tries=2).invoke(
                            bja.consigne_notes(q, p_b, rech, x["jeu"])))
                        notes = bja.lire_notes(r)
                        res = {"notes": {k: v["note"] for k, v in notes.items()}}
                        if c in ("r1", "r2") and len(notes) == len(bja.CLES):
                            r = ap.extraire_json(await am.llm(modele, temperature=0.2, timeout=300, allowed_tries=2).invoke(
                                bja.consigne_finale(q, p_b, notes, rech, x["jeu"])))
                            res["p"] = min(0.99, max(0.01, float(r["p"])))
                    except Exception as e:
                        res = {"erreur": f"{type(e).__name__}: {e}"[:200]}
                    cout = float(cm.current_usage or 0)
                compte = COMPTE[c]
                cumul[compte] += cout
                pire[compte] = max(pire[compte], cout)
                ligne[c] = res
            f.write(json.dumps(ligne, ensure_ascii=False) + "\n")
            f.flush()
            retenues += 1
            print(f"{qid[:48]} : r1 {ligne['r1'].get('notes')} · r2 {ligne['r2'].get('notes')} · x {ligne['x'].get('notes')}")
    r = resumer(lignes(), bja.CLES, sautees)
    RESUME.write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"coût : {cumul}")
    print(json.dumps({k: r.get(k) for k in ("n_completes", "lecture", "probabilite_r1_r2")}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("--n", type=int, default=60)
    a.add_argument("--budget", type=float, default=3.0)
    a.add_argument("--budget-bedrock", type=float, default=1.0)
    o = a.parse_args()
    sys.exit(asyncio.run(principal(o.n, o.budget, o.budget_bedrock)))
