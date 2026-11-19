"""Inventaire des thèmes du tournoi, pour ordonner l'écriture des fiches d'écosystèmes (bot 0.10.314).

Décision de l'auteur, 2026-11-19, 3 h 54 (« c'est un travail de fourmi, mais nécessaire »). Lecture seule côté
Metaculus (liste des questions ouvertes, comme gdelt_bq --mode nuit) ; rien n'est posté, rien n'entre dans le bot.

Chaque question (titre public) est rangée par gpt-5-mini dans un ou deux thèmes : un thème déjà connu (fiches et ponts
de ecosystemes/) ou un thème nouveau qu'il nomme. Les questions déjà rangées ne sont pas reclassées (registre).
Sortie : registre/inventaire-themes.jsonl (une ligne par question) et registre/inventaire-themes.json (thèmes
ordonnés : nombre de questions, ponts qui les appellent, fiche écrite ou non).

    python inventaire_themes.py --budget 0.5
"""
from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from pathlib import Path

import alphabet_pipeline as ap
import ecosystemes as ec

FICHIER = Path("registre/inventaire-themes.jsonl")
RESUME = Path("registre/inventaire-themes.json")
MODELE = "azure_ai/gpt-5-mini"
JOURNAUX = (Path("registre/journal-bot.jsonl"), Path("registre/journal-autres.jsonl"))


def themes_connus() -> dict[str, str]:
    fiches = ec.charger()
    out = {t: f.get("nom", t) for t, f in fiches.items()}
    for f in fiches.values():
        for p in f.get("ponts") or []:
            t = str(p["vers"]).split(":")[0]
            out.setdefault(t, t.replace("-", " "))
    return out


def lignes() -> list[dict]:
    return [json.loads(l) for l in FICHIER.read_text(encoding="utf-8").splitlines() if l.strip()] if FICHIER.exists() else []


def questions_locales() -> list[tuple[str, str]]:
    out = {}
    for j in JOURNAUX:
        if j.exists():
            for l in j.read_text(encoding="utf-8").splitlines():
                if l.strip():
                    x = json.loads(l)
                    if x.get("titre"):
                        out[str(x.get("question_id") or x["titre"])] = x["titre"]
    return list(out.items())


def questions() -> list[tuple[str, str]]:
    import gdelt_bq as g
    vus = dict(questions_locales())
    try:
        for qid, titre in g.questions_tournoi():
            vus.setdefault(str(qid), titre)
    except Exception as e:
        print(f"::warning::liste du tournoi indisponible ({type(e).__name__}) ; journaux seuls.")
    return list(vus.items())


def consigne(titre: str, connus: dict[str, str]) -> str:
    liste = "\n".join(f"- {k} : {v}" for k, v in sorted(connus.items()))
    return f"""Range cette question de prévision dans UN ou DEUX thèmes (des écosystèmes de situations, pas des disciplines).

THÈMES DÉJÀ CONNUS (identifiant : nom) :
{liste}

QUESTION : {titre}

Si aucun thème connu ne convient, crée-en un : identifiant court en français, en minuscules avec des tirets (par exemple
« securite-nucleaire-civile », « faillites-entreprises »), assez large pour accueillir d'autres questions semblables,
assez précis pour avoir ses propres compartiments.
Réponds seulement par un objet JSON : {{"themes": [{{"id": "...", "nom": "...", "nouveau": true ou false}}]}}"""


def propre(t: str) -> str:
    import unicodedata
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9-]+", "-", t.lower().strip()).strip("-")[:48]


def resumer(ls: list[dict], connus: dict[str, str]) -> dict:
    fiches = ec.charger()
    appel: dict[str, int] = {}
    for f in fiches.values():
        for p in f.get("ponts") or []:
            t = str(p["vers"]).split(":")[0]
            appel[t] = appel.get(t, 0) + 1
    th: dict[str, dict] = {}
    for x in ls:
        for t in x.get("themes") or []:
            d = th.setdefault(t["id"], {"nom": t.get("nom") or connus.get(t["id"], t["id"]), "questions": 0, "titres": []})
            d["questions"] += 1
            d["titres"].append(x["titre"][:140])
    for t, n in appel.items():
        th.setdefault(t, {"nom": connus.get(t, t), "questions": 0, "titres": []})
    for t, d in th.items():
        d["ponts_qui_l_appellent"] = appel.get(t, 0)
        d["fiche_ecrite"] = t in fiches
    ordre = sorted(th, key=lambda t: (th[t]["fiche_ecrite"], -th[t]["questions"], -th[t]["ponts_qui_l_appellent"], t))
    return {"version_bot": ap.VERSION_BOT, "questions": len(ls), "themes": len(th),
            "note": "ordre d'écriture proposé : fiches non écrites d'abord, puis par nombre de questions, puis par ponts",
            "ordre": [{"theme": t, **th[t]} for t in ordre]}


async def principal(budget: float) -> int:
    from forecasting_tools import MonetaryCostManager
    import alphabet_modeles as am
    import banc_forecastbench as fb
    connus = themes_connus()
    deja = {x["question_id"] for x in lignes()}
    qs = questions()
    print(f"{len(qs)} question(s) ; {len(deja)} déjà rangée(s).")
    cumul = pire = 0.0
    with FICHIER.open("a", encoding="utf-8") as f:
        for qid, titre in qs:
            if qid in deja:
                continue
            if fb.depasse(cumul, pire, budget):
                print(f"Plafond atteint ({cumul:.2f} $).")
                break
            with MonetaryCostManager() as cm:
                try:
                    r = ap.extraire_json(await am.llm(MODELE, temperature=0.2, timeout=180, allowed_tries=2).invoke(consigne(titre, connus)))
                    ths = [{"id": propre(t.get("id", "")), "nom": str(t.get("nom") or "")[:80], "nouveau": bool(t.get("nouveau"))}
                           for t in (r.get("themes") or [])[:2] if propre(t.get("id", ""))]
                except Exception as e:
                    ths = []
                    print(f"{qid} : {type(e).__name__}")
                c = float(cm.current_usage or 0)
            cumul += c
            pire = max(pire, c)
            for t in ths:
                connus.setdefault(t["id"], t["nom"])          # un thème créé sert aux questions suivantes
            f.write(json.dumps({"question_id": qid, "titre": titre, "themes": ths, "version_bot": ap.VERSION_BOT},
                               ensure_ascii=False) + "\n")
            f.flush()
            print(f"{titre[:60]} → {[t['id'] for t in ths]}", flush=True)
    r = resumer(lignes(), connus)
    RESUME.write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps([{"theme": x["theme"], "questions": x["questions"], "ponts": x["ponts_qui_l_appellent"]}
                      for x in r["ordre"][:25]], ensure_ascii=False, indent=0))
    print(f"Coût : {cumul:.2f} $")
    return 0


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("--budget", type=float, default=0.5)
    sys.exit(asyncio.run(principal(a.parse_args().budget)))
