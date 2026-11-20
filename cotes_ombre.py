"""Cotes Polymarket relevées EN OMBRE pour les questions binaires (0.10.408, preenregistrements/cotes-ombre.md).

Rien ici ne touche la prévision postée : la cote est relevée APRÈS le calcul de la prévision et scellée dans
registre/journal-cotes.jsonl. Appariement strict : dans le doute, aucun marché.

    python cotes_ombre.py --sonde      # questions binaires ouvertes du journal → registre/sonde-cotes.json
    python cotes_ombre.py --suivi      # bilan des questions résolues → registre/suivi-cotes.json
"""
from __future__ import annotations

import json
import math
import re
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path

import httpx

import politesse

API = "https://gamma-api.polymarket.com"
MISE_MIN = 50_000.0
JACCARD_MIN = 0.6
ECART_JOURS = 31
REG = Path("registre")

_VIDES = set("""a an the of in on at to by for from with will be is are was were has have had it its this that
these those as or and if than then there their what which who whom whose when where how do does did any
during between into over under up down out per via vs versus""".split())
_CONTRAIRES = {"not", "no", "never", "fail", "fails", "remain", "remains", "stay", "stays", "leave", "leaves",
               "lose", "loses", "without", "before", "after", "above", "below", "less", "more", "fewer",
               "under", "over", "least", "most", "exceed", "exceeds"}
_NB = re.compile(r"\d[\d,]*(?:\.\d+)?")
_MOT = re.compile(r"[a-z][a-z'\-]*")


def nombres(t: str) -> set[str]:
    out = set()
    for n in _NB.findall(t or ""):
        x = n.replace(",", "")
        x = x.rstrip("0").rstrip(".") if "." in x else x
        out.add(x)
    return out


def mots(t: str) -> list[str]:
    return [m.strip("'-") for m in _MOT.findall((t or "").lower())]


def pleins(t: str) -> set[str]:
    return {m[:-1] if len(m) > 3 and m.endswith("s") else m for m in mots(t) if m not in _VIDES and len(m) > 1}


def contraires(t: str) -> set[str]:
    return {m for m in mots(t) if m in _CONTRAIRES}


def jaccard(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if a | b else 0.0


def _liste(x):
    if isinstance(x, str):
        try:
            return json.loads(x)
        except ValueError:
            return []
    return x or []


def candidats(reponse: dict) -> list[dict]:
    """Marchés tirés d'une réponse de /public-search (événements → marchés)."""
    out = []
    for ev in reponse.get("events") or []:
        for m in ev.get("markets") or []:
            out.append(m)
    for m in reponse.get("markets") or []:
        out.append(m)
    return out


def apparier(titre: str, resolution: date, marches: list[dict]) -> tuple[dict | None, str]:
    """(marché retenu, motif). Toutes les règles du préenregistrement ; un seul survivant, sinon rien."""
    survivants = []
    for m in marches:
        q = m.get("question") or ""
        issues = [str(x).lower() for x in _liste(m.get("outcomes"))]
        prix = _liste(m.get("outcomePrices"))
        if issues != ["yes", "no"] or len(prix) != 2 or m.get("closed") or m.get("active") is False:
            continue
        try:
            mise = float(m.get("volumeNum") or m.get("volume") or 0)
            p_oui = float(prix[0])
        except (TypeError, ValueError):
            continue
        if mise < MISE_MIN:
            continue
        if nombres(q) != nombres(titre) or contraires(q) != contraires(titre):
            continue
        j = jaccard(pleins(q), pleins(titre))
        if j < JACCARD_MIN:
            continue
        try:
            fin = datetime.fromisoformat(str(m.get("endDate")).replace("Z", "+00:00")).date()
        except ValueError:
            continue
        if abs((fin - resolution).days) > ECART_JOURS:
            continue
        survivants.append({"slug": m.get("slug"), "id": m.get("id"), "question": q, "p_oui": p_oui, "mise": mise,
                           "jaccard": round(j, 3), "fin": fin.isoformat()})
    uniques = {s["id"] or s["slug"]: s for s in survivants}
    if not uniques:
        return None, "aucun marché conforme"
    if len(uniques) > 1:
        return None, f"ambigu ({len(uniques)} marchés conformes)"
    return next(iter(uniques.values())), "apparié"


def chercher(titre: str, resolution: date, client: httpx.Client | None = None) -> dict:
    """Interroge Polymarket et applique l'appariement. Ne lève jamais : rend un statut."""
    propre = client is None
    c = client or httpx.Client(headers={"User-Agent": politesse.UA}, timeout=15)
    try:
        url = f"{API}/public-search"
        if not politesse.autorise(c, url):
            return {"statut": "refusé par robots.txt"}
        requete = " ".join(m for m in mots(titre) if m not in _VIDES)[:120]
        r = c.get(url, params={"q": requete, "limit_per_type": 20, "events_status": "active"})
        if r.status_code != 200:
            return {"statut": f"réponse {r.status_code}"}
        m, motif = apparier(titre, resolution, candidats(r.json()))
        return {"statut": motif, "marche": m} if m else {"statut": motif}
    except Exception as e:
        return {"statut": f"erreur {type(e).__name__}"}
    finally:
        if propre:
            c.close()


def relever(question_id: str, url: str, titre: str, resolution: date, p_poste: float, version: str) -> dict:
    """Relève la cote et la scelle dans registre/journal-cotes.jsonl (après le calcul de la prévision)."""
    import alphabet_pipeline as ap
    res = chercher(titre, resolution)
    ligne = {"version_bot": version, "question_id": str(question_id), "url": url, "titre": titre,
             "releve_le": datetime.now(timezone.utc).isoformat(timespec="seconds"),
             "resolution_prevue": resolution.isoformat(), "p_poste": p_poste, **res}
    ligne["sceau"] = ap.sceau(ligne)
    with open(ap.registre_ecrivable() / "journal-cotes.jsonl", "a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(ligne, ensure_ascii=False, sort_keys=True, default=str) + "\n")
    return ligne


def _perte(p: float, issue: int) -> float:
    p = min(0.99, max(0.01, p))
    return -math.log(p if issue else 1 - p)


def sonde() -> int:
    """Questions binaires encore ouvertes du journal : appariement seul, pour juger la qualité (rien n'est posté)."""
    auj = date.today()
    vues = {}
    for l in (REG / "journal-bot.jsonl").read_text(encoding="utf-8").splitlines():
        try:
            x = json.loads(l)
        except ValueError:
            continue
        try:
            res = date.fromisoformat(str(x.get("resolution_prevue") or x.get("resolution"))[:10])
        except ValueError:
            continue
        if res >= auj and x.get("titre"):
            vues[x.get("question_id")] = (x["titre"], res)
    out = []
    with httpx.Client(headers={"User-Agent": politesse.UA}, timeout=15) as c:
        for qid, (t, res) in sorted(vues.items(), key=lambda z: str(z[0])):
            out.append({"question_id": qid, "titre": t, "resolution": res.isoformat(), **chercher(t, res, c)})
            time.sleep(1)
    (REG / "sonde-cotes.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    n = sum(1 for x in out if x.get("marche"))
    print(f"sonde : {len(out)} questions ouvertes, {n} appariées")
    for x in out:
        if x.get("marche"):
            print(f"- {x['titre'][:90]}\n  = {x['marche']['question'][:90]} (p {x['marche']['p_oui']:.2f}, "
                  f"mise {x['marche']['mise']:,.0f} $, J {x['marche']['jaccard']})")
    motifs = {}
    for x in out:
        motifs[x["statut"]] = motifs.get(x["statut"], 0) + 1
    print("motifs :", motifs)
    return 0


def suivi() -> int:
    import score_registre as sr
    issues = sr.issues_enregistrees(REG)
    f = REG / "journal-cotes.jsonl"
    lignes = [json.loads(l) for l in f.read_text(encoding="utf-8").splitlines() if l.strip()] if f.exists() else []
    derniere = {}
    for x in lignes:
        derniere[x["question_id"]] = x       # dernière relève par question
    res = []
    for qid, x in derniere.items():
        if qid in issues and x.get("marche"):
            i = issues[qid]
            res.append({"question_id": qid, "issue": i, "p_cote": x["marche"]["p_oui"], "p_poste": x["p_poste"],
                        "ecart": _perte(x["marche"]["p_oui"], i) - _perte(x["p_poste"], i)})
    r = {"relevees": len(derniere), "appariees": sum(1 for x in derniere.values() if x.get("marche")),
         "appariees_resolues": len(res),
         "ecart_moyen_perte_log": round(sum(z["ecart"] for z in res) / len(res), 4) if res else None,
         "pire_ecart": max(res, key=lambda z: z["ecart"]) if res else None,
         "note": "écart < 0 : la cote aurait fait mieux que la prévision postée. Descriptif sous 30 questions."}
    (REG / "suivi-cotes.json").write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in r.items() if k != "pire_ecart"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(sonde() if "--sonde" in sys.argv else suivi() if "--suivi" in sys.argv else 0)
