"""Banc de couverture de l'alphabet sur des situations non vues (bot 0.10.308, descriptif).

Décision d'auteur du 2026-11-19, 1 h 46. Idée : Axiom, corpus CFSG (la valeur d'une bibliothèque se mesure à ce qu'elle
porte hors de l'ouvrage qui l'a fait naître). Préenregistrement : preenregistrements/couverture-alphabet.md.
Aucune issue, aucun essai, rien dans le bot.

    python banc_couverture_alphabet.py --budget 1 --budget-bedrock 1
"""
from __future__ import annotations

import argparse
import asyncio
import json
import random
import sys
from pathlib import Path

import alphabet_pipeline as ap
import cartes_ancrees as ca

FICHIER = Path("registre/banc-couverture-alphabet.jsonl")
RESUME = Path("registre/banc-couverture-alphabet.json")
# 0.10.311 : cinq cartes candidates en ombre (preenregistrements/cartes-candidates-ombre.md), situations neuves
FICHIER_ETENDU = Path("registre/banc-couverture-etendue.jsonl")
RESUME_ETENDU = Path("registre/banc-couverture-etendue.json")
GRAINE_ETENDUE = 1
CANDIDATES = {
    "CMP": "COMPÉTITION : plusieurs parties visent une même ressource ou une même position qui ne peut pas revenir à "
           "toutes ; ce que l'une obtient réduit ce que les autres peuvent obtenir, selon une règle d'attribution (vote, "
           "score, classement, combat, enchère) (compétition au sens écologique ; jeux à somme nulle ou constante)",
    "ITN": "INTENTION : l'issue dépend du choix discrétionnaire d'un acteur identifiable qui a le pouvoir de la produire "
           "ou de l'empêcher, et que les règles en place ne dictent pas (théorie de la décision ; choix sous contrainte)",
    "CAP": "CAPACITÉ : l'issue dépend des moyens d'un acteur — forces, ressources, compétences, logistique — rapportés à "
           "ce que l'action exige (rapport moyens / exigences ; fonction de production)",
    "MAR": "MARCHÉ : une valeur se forme par la rencontre décentralisée d'offres et de demandes et s'ajuste aux chocs et "
           "aux anticipations (équilibre offre-demande ; formation des prix)",
    "CNV": "CONVENTION : un fait n'existe que parce qu'une collectivité ou une autorité l'accepte ou le déclare (statut, "
           "titre, statistique officielle, frontière, reconnaissance) ; il peut changer par décision sans que rien de "
           "matériel ne bouge (faits institutionnels : « X compte comme Y dans le contexte C », Searle 1995)",
}
PAR_PLATEFORME = 30
GRAINE = 0
MIN_ANCRE = 3
SEUIL_COUVERTURE = 0.8
SEUIL_RESTE = 0.05
CODEURS = {"gpt": "azure_ai/gpt-5-mini", "haiku": "bedrock/global.anthropic.claude-haiku-4-5-20251001-v1:0"}


def q(qid: str) -> str:
    return ":".join(qid.split(":")[:2])


def situations(etendu: bool = False) -> list[dict]:
    import banc_jugement as bj
    import banc_jugement_alphabet as bja
    vues = {q(x["question_id"]) for x in bja.lignes()}
    if etendu:
        vues |= {q(x["qid"]) for x in lignes()}
    xs = [json.loads(l) for l in bj.REGISTRE.read_text(encoding="utf-8").splitlines() if l.strip()]
    premieres: dict[str, dict] = {}
    for x in sorted(xs, key=lambda x: x["jeu"]):
        k = f'{x["source"]}:{x["id"]}'
        if k not in premieres:
            premieres[k] = x
    par: dict[str, list[dict]] = {}
    for k, x in sorted(premieres.items()):
        if x["jeu"] >= ("2025-01-01" if etendu else "2026-01-01") and k not in vues and x.get("titre"):
            par.setdefault(x["source"], []).append({"qid": f'{k}:{x["jeu"]}', "titre": x["titre"], "source": x["source"]})
    rnd = random.Random(GRAINE_ETENDUE if etendu else GRAINE)
    out = []
    for s in sorted(par):
        l = par[s][:]
        rnd.shuffle(l)
        out += l[:PAR_PLATEFORME]
    return out


def consigne(titre: str, cartes: dict[str, str]) -> str:
    defs = "\n".join(f"- {k} = {v}" for k, v in cartes.items())
    return f"""Codage structurel d'une situation, pour un banc d'évaluation d'un alphabet de {len(cartes)} cartes.

LES {len(cartes)} CARTES (abréviation = nom : définition (structure formelle)) :
{defs}

SITUATION (titre d'une question de prévision) :
{titre}

Indique les cartes dont la STRUCTURE est réellement présente dans cette situation. Pour chacune, recopie mot pour mot
le passage du titre qui l'ancre. Ne mets pas une carte par simple ressemblance de mots ; aucune carte est une réponse
admise. Puis dis si une structure ESSENTIELLE de la situation n'est saisie par aucune carte.

Réponds seulement par un objet JSON :
{{"cartes": [{{"carte": "ABR", "passage": "texte recopié du titre"}}], "reste": "la structure manquante en une phrase, ou null", "reste_essentiel": true ou false}}"""


def ancrees(r: dict, titre: str, valides: set[str]) -> list[str]:
    out = []
    tn = ca._norm(titre)
    for c in r.get("cartes") or []:
        if not isinstance(c, dict):
            continue
        k = str(c.get("carte") or "").strip().upper()[:3]
        p = ca._norm(str(c.get("passage") or "")).strip(" .\"'")
        if k in valides and len(p) >= MIN_ANCRE and p in tn and k not in out:
            out.append(k)
    return out


def kappa(a: list[bool], b: list[bool]) -> float | None:
    n = len(a)
    if not n:
        return None
    po = sum(x == y for x, y in zip(a, b)) / n
    pa, pb = sum(a) / n, sum(b) / n
    pe = pa * pb + (1 - pa) * (1 - pb)
    return None if pe >= 1 else round((po - pe) / (1 - pe), 3)


def glouton_80(ensembles: list[set[str]]) -> int | None:
    codees = [e for e in ensembles if e]
    if not codees:
        return None
    reste, n = list(codees), 0
    cible = SEUIL_COUVERTURE * len(codees)
    couvert = 0
    while couvert < cible and reste:
        freq: dict[str, int] = {}
        for e in reste:
            for c in e:
                freq[c] = freq.get(c, 0) + 1
        meilleure = max(sorted(freq), key=lambda c: freq[c])
        couvert += freq[meilleure]
        reste = [e for e in reste if meilleure not in e]
        n += 1
    return n


def resumer(ls: list[dict], toutes: list[str]) -> dict:
    out = {"version_bot": ap.VERSION_BOT, "situations": len(ls),
           "note": "descriptif ; titres de questions de 2026 jamais vues par un banc de l'alphabet ; cartes ancrées mot pour mot"}
    ok = [x for x in ls if all(x.get(c, {}).get("ok") for c in CODEURS)]
    out["codees_par_les_deux"] = len(ok)
    if not ok:
        return out
    for c in CODEURS:
        ens = [set(x[c]["cartes"]) for x in ok]
        freq = {k: sum(k in e for e in ens) for k in toutes}
        out[c] = {"couverture": round(sum(not x[c]["reste_essentiel"] for x in ok) / len(ok), 3),
                  "sans_aucune_carte": sum(not e for e in ens),
                  "cartes_par_situation": round(sum(len(e) for e in ens) / len(ok), 2),
                  "charge": dict(sorted(freq.items(), key=lambda t: -t[1])),
                  "jamais_utilisees": [k for k, v in freq.items() if v == 0],
                  "cartes_pour_80_pourcent": glouton_80(ens),
                  "cartes_hors_liste_ou_non_ancrees": sum(x[c]["rejetees"] for x in ok)}
    out["couverture_les_deux"] = round(sum(not x["gpt"]["reste_essentiel"] and not x["haiku"]["reste_essentiel"] for x in ok) / len(ok), 3)
    kap = {k: kappa([k in x["gpt"]["cartes"] for x in ok], [k in x["haiku"]["cartes"] for x in ok]) for k in toutes}
    vals = [v for v in kap.values() if v is not None]
    out["accord"] = {"kappa_par_carte": kap, "kappa_moyen": round(sum(vals) / len(vals), 3) if vals else None,
                     "jaccard_moyen": round(sum(len(set(x["gpt"]["cartes"]) & set(x["haiku"]["cartes"])) /
                                                max(1, len(set(x["gpt"]["cartes"]) | set(x["haiku"]["cartes"])))
                                                for x in ok) / len(ok), 3)}
    out["restes"] = [{"qid": x["qid"], "titre": x["titre"][:160], "gpt": x["gpt"].get("reste"), "haiku": x["haiku"].get("reste"),
                      "essentiel": [c for c in CODEURS if x[c]["reste_essentiel"]]}
                     for x in ok if any(x[c].get("reste") for c in CODEURS)]
    out["regle_candidate"] = (f"structure nommée par les deux codeurs, chacun dans au moins {SEUIL_RESTE:.0%} des situations ; "
                              "regroupement des restes fait à la main, puis soumis à l'auteur")
    return out


def lignes(fichier: Path = FICHIER) -> list[dict]:
    return [json.loads(l) for l in fichier.read_text(encoding="utf-8").splitlines() if l.strip()] if fichier.exists() else []


def resumer_etendu(ls: list[dict], base: list[str]) -> dict:
    """Mêmes situations codées avec 16 puis 21 cartes ; lecture fixée dans le préenregistrement."""
    a = resumer([{**x, "gpt": x["gpt16"], "haiku": x["haiku16"]} for x in ls if "gpt16" in x], base)
    b = resumer([{**x, "gpt": x["gpt21"], "haiku": x["haiku21"]} for x in ls if "gpt21" in x], sorted(set(base) | set(CANDIDATES)))
    out = {"version_bot": ap.VERSION_BOT, "note": "mêmes situations neuves, codées avec 16 puis 21 cartes (5 candidates en ombre)",
           "seize": {k: v for k, v in a.items() if k != "restes"}, "vingt_et_une": {k: v for k, v in b.items() if k != "restes"},
           "restes_21": b.get("restes", [])}
    n = b.get("codees_par_les_deux") or 0
    if not n:
        return out
    cand = {}
    for k in CANDIDATES:
        g, h = b["gpt"]["charge"].get(k, 0), b["haiku"]["charge"].get(k, 0)
        kap = b["accord"]["kappa_par_carte"].get(k)
        cand[k] = {"gpt": g, "haiku": h, "kappa": kap,
                   "passe": g >= SEUIL_RESTE * n and h >= SEUIL_RESTE * n and kap is not None and kap >= 0.2}
    out["candidates"] = cand
    monte = all(b[c]["couverture"] > a[c]["couverture"] for c in CODEURS)
    ka, kb = (a.get("accord") or {}).get("kappa_moyen"), (b.get("accord") or {}).get("kappa_moyen")
    out["ensemble"] = {"couverture_monte_pour_les_deux": monte, "kappa_moyen_16": ka, "kappa_moyen_21": kb,
                       "passe": bool(monte and ka is not None and kb is not None and kb >= ka)}
    return out


async def coder(modele: str, titre: str, cartes: dict[str, str]) -> dict:
    import alphabet_modeles as am
    try:
        r = ap.extraire_json(await am.llm(modele, temperature=0.2, timeout=300, allowed_tries=2).invoke(consigne(titre, cartes)))
        k = ancrees(r, titre, set(cartes))
        return {"ok": True, "cartes": k, "rejetees": len(r.get("cartes") or []) - len(k),
                "reste": (str(r["reste"])[:300] if r.get("reste") not in (None, "", "null") else None),
                "reste_essentiel": bool(r.get("reste_essentiel"))}
    except Exception as e:
        return {"ok": False, "erreur": f"{type(e).__name__}: {e}"[:200]}


async def principal_etendu(budget: float, budget_bedrock: float) -> int:
    from forecasting_tools import MonetaryCostManager
    import banc_forecastbench as fb
    import preselection as ps
    c16 = ps.textes_cartes()
    c21 = dict(sorted({**c16, **CANDIDATES}.items()))
    deja = {x["qid"] for x in lignes(FICHIER_ETENDU)}
    cumul = {c: 0.0 for c in CODEURS}
    pire = {c: 0.0 for c in CODEURS}
    plafond = {"gpt": budget, "haiku": budget_bedrock}
    sits = situations(etendu=True)
    print(f"{len(sits)} situations neuves ; {len(deja)} déjà codées.")
    with FICHIER_ETENDU.open("a", encoding="utf-8") as f:
        for s in sits:
            if s["qid"] in deja:
                continue
            if any(fb.depasse(cumul[c], pire[c], plafond[c]) for c in CODEURS):
                print(f"Plafond atteint ({cumul}). Arrêt.")
                break
            ligne = dict(s, type="banc_couverture_etendue", version_bot=ap.VERSION_BOT)
            for c, modele in CODEURS.items():
                with MonetaryCostManager() as cm:
                    ligne[f"{c}16"] = await coder(modele, s["titre"], c16)
                    ligne[f"{c}21"] = await coder(modele, s["titre"], c21)
                    cout = float(cm.current_usage or 0)
                cumul[c] += cout
                pire[c] = max(pire[c], cout)
            f.write(json.dumps(ligne, ensure_ascii=False) + "\n")
            f.flush()
            print(f"{s['qid'][:40]} : gpt21 {ligne['gpt21'].get('cartes')} · haiku21 {ligne['haiku21'].get('cartes')}", flush=True)
    r = resumer_etendu(lignes(FICHIER_ETENDU), sorted(c16))
    RESUME_ETENDU.write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in r.items() if k != "restes_21"}, ensure_ascii=False, indent=1))
    print(f"Coûts : {cumul}")
    return 0


async def principal(budget: float, budget_bedrock: float) -> int:
    from forecasting_tools import MonetaryCostManager
    import alphabet_modeles as am
    import banc_forecastbench as fb
    import preselection as ps
    cartes = ps.textes_cartes()
    deja = {x["qid"] for x in lignes()}
    cumul = {c: 0.0 for c in CODEURS}
    pire = {c: 0.0 for c in CODEURS}
    plafond = {"gpt": budget, "haiku": budget_bedrock}
    sits = situations()
    print(f"{len(sits)} situations tirées ; {len(deja)} déjà codées.")
    with FICHIER.open("a", encoding="utf-8") as f:
        for s in sits:
            if s["qid"] in deja:
                continue
            if any(fb.depasse(cumul[c], pire[c], plafond[c]) for c in CODEURS):
                print(f"Plafond atteint ({cumul}). Arrêt.")
                break
            ligne = dict(s, type="banc_couverture_alphabet", version_bot=ap.VERSION_BOT)
            for c, modele in CODEURS.items():
                with MonetaryCostManager() as cm:
                    try:
                        r = ap.extraire_json(await am.llm(modele, temperature=0.2, timeout=300, allowed_tries=2)
                                             .invoke(consigne(s["titre"], cartes)))
                        k = ancrees(r, s["titre"], set(cartes))
                        ligne[c] = {"ok": True, "cartes": k, "rejetees": len(r.get("cartes") or []) - len(k),
                                    "reste": (str(r["reste"])[:300] if r.get("reste") not in (None, "", "null") else None),
                                    "reste_essentiel": bool(r.get("reste_essentiel"))}
                    except Exception as e:
                        ligne[c] = {"ok": False, "erreur": f"{type(e).__name__}: {e}"[:200]}
                    cout = float(cm.current_usage or 0)
                cumul[c] += cout
                pire[c] = max(pire[c], cout)
            f.write(json.dumps(ligne, ensure_ascii=False) + "\n")
            f.flush()
            print(f"{s['qid'][:40]} : gpt {ligne['gpt'].get('cartes')} · haiku {ligne['haiku'].get('cartes')}", flush=True)
    r = resumer(lignes(), sorted(cartes))
    RESUME.write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in r.items() if k != "restes"}, ensure_ascii=False, indent=1))
    print(f"Coûts : {cumul}")
    return 0


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("--budget", type=float, default=1.0)
    a.add_argument("--budget-bedrock", type=float, default=1.0)
    a.add_argument("--etendu", action="store_true", help="0.10.311 : 16 contre 21 cartes sur des situations neuves")
    x = a.parse_args()
    sys.exit(asyncio.run((principal_etendu if x.etendu else principal)(x.budget, x.budget_bedrock)))
