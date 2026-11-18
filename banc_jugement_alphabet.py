"""Questions de jugement Metaculus : le bot standard (A) contre le même bot passé par l'alphabet (M), bot 0.10.243.

Décision d'auteur du 2026-11-17 (21 h 05, « on peut commencer par là, c'est un début »), après le banc des questions
semblables (claude/resultat-jugement-semblables-2026-11-17.md) : la foule (0,360) est loin devant les taux sans
information (0,646) ; ce qu'elle fait, c'est lire l'information propre à chaque question. Question posée : l'alphabet
apporte-t-il une plus-value, même minime, au-dessus de ce que fait la médiane des bots (un modèle qui lit l'actualité) ?
Préenregistrement : preenregistrements/jugement-alphabet.md.

Questions : celles de Metaculus du banc des questions de jugement (registre/jugement-questions.jsonl), cohorte complète
(clôture prévue passée depuis 30 jours), jeux de 2026, ordre fixé par une empreinte de l'identifiant. Taux de base de
départ : les questions semblables (p_S de banc_jugement), adoptées comme point de départ (décision d'auteur, 21 h 05).
La prévision de la communauté (valeur au gel) n'est JAMAIS lue ni transmise ; l'introduction de ForecastBench (qui
parle de marché) n'est pas transmise non plus.
Une recherche bornée avant la date du jeu (alphabet_retro.chercher_avant), puis, sur les mêmes entrées :
  A : le bot standard : question, critères, contexte, taux de base, recherche → probabilité ;
  M : l'alphabet en matriochka : (1) sept notes séparées de 1 à 4, une par carte, sans probabilité ;
      (2) le jugement final, qui voit le taux de base et les notes, plus les extraits bruts.
Critère : perte log M − A, 150 premières questions (second regard à 300), bootstrap par jeu, risque corrigé
(essai jugement_alphabet). Rapportés : B (semblables), discrimination de A et de M.

    python banc_jugement_alphabet.py --n 150 --budget 4
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import alphabet_modeles as am
import alphabet_pipeline as ap
import alphabet_retro as ar
import trace_recherche as tr
import banc_a as ba
import banc_forecastbench as fb
import banc_jugement as bj
import garde_injection as gi

REGISTRE = Path("registre")
FICHIER = REGISTRE / "banc-jugement-alphabet.jsonl"
RESUME = REGISTRE / "banc-jugement-alphabet.json"
MODELE = "azure_ai/gpt-5-mini"

# (clé, carte, ce qu'on note ; 4 = pousse vers OUI, sauf « freins » où 4 = freins forts)
CRITERES = (
    ("tendance", "CROISSANCE", "la direction des développements récents (1 = s'éloignent nettement de OUI, 4 = vont "
                               "nettement vers OUI)"),
    ("engagements", "RÉCIPROCITÉ", "les engagements datés des acteurs qui décident : annonces, promesses, menaces, "
                                   "votes prévus (1 = aucun ou contraires, 4 = nombreux, précis et favorables à OUI)"),
    ("decideurs", "HIÉRARCHIE", "la position de ceux qui ont le pouvoir de produire le OUI (1 = opposés ou inconnus, "
                                "4 = clairement favorables et en mesure d'agir)"),
    ("declencheur", "SEUIL", "un événement prévu avant l'échéance capable de produire le OUI : audience, vote, sommet, "
                             "publication (1 = aucun, 4 = prévu et probable)"),
    ("freins", "CONTRAINTE", "les obstacles : procédure, droit, opposition, coût, délais (1 = faibles, 4 = forts)"),
    ("duree", "PÉRIODICITÉ", "le temps qui reste avant l'échéance comparé au temps qu'il faut d'ordinaire pour ce type "
                             "de changement (1 = bien trop court, 4 = largement suffisant)"),
    ("proportion", "PROPORTION", "la distance entre l'état actuel et ce qu'exige la résolution (1 = très loin, "
                                 "4 = déjà atteint ou tout proche)"),
)
CLES = tuple(c[0] for c in CRITERES)


def rang(x: dict) -> str:
    return hashlib.sha1(f'{x["source"]}:{x["id"]}:{x["jeu"]}'.encode()).hexdigest()


def _entete(q: dict, p_b: float, jeu: str) -> str:
    return f"""QUESTION : {q['titre']}
CRITÈRES DE RÉSOLUTION : {q['criteres'][:2500]}
CONTEXTE : {q['contexte'][:3000]}
ÉCHÉANCE PRÉVUE DE LA QUESTION : {q['cloture']}

TAUX DE BASE (part de OUI parmi les questions semblables déjà résolues, calculée par le code) : {p_b:.3f}"""


def consigne_a(q: dict, p_b: float, recherche: str, jeu: str) -> str:
    return f"""Tu es un prévisionniste. Nous sommes le {jeu}. Donne la probabilité que la réponse soit OUI.

{_entete(q, p_b, jeu)}

RÉSULTATS DE RECHERCHE (antérieurs au {jeu}) :
{gi.bloc(recherche, 6000)}

Pars du taux de base, puis ajuste selon ce que montrent les recherches. Si tu connais déjà l'issue réelle de cette
question (elle est passée pour toi), dis-le honnêtement.
Rends UNIQUEMENT un objet JSON : {{"p": nombre entre 0,01 et 0,99, "raison": "une phrase", "connait_issue": true ou false}}"""


def consigne_notes(q: dict, p_b: float, recherche: str, jeu: str) -> str:
    liste = "\n".join(f"- \"{k}\" ({carte}) : {quoi}" for k, carte, quoi in CRITERES)
    return f"""Nous sommes le {jeu}. Tu prépares un comité de prévision. Tu NE DONNES PAS de probabilité : tu décomposes
la question en situations simples et tu notes chacune séparément, sans te demander encore quelle sera la réponse.

{_entete(q, p_b, jeu)}

RÉSULTATS DE RECHERCHE (antérieurs au {jeu}) :
{gi.bloc(recherche, 6000)}

Note chaque critère de 1 à 4, pour lui-même, sans laisser les autres l'influencer. Si l'information manque, dis-le
dans la justification et note 2.
{liste}
Rends UNIQUEMENT un objet JSON : {{"notes": {{"tendance": {{"note": 1-4, "pourquoi": "une phrase"}}, ...}},
"connait_issue": true ou false}}"""


def consigne_finale(q: dict, p_b: float, notes: dict, recherche: str, jeu: str) -> str:
    lignes = "\n".join(f"- {carte} ({k}) : {notes[k]['note']}/4 — {notes[k].get('pourquoi', '')}"
                       for k, carte, _ in CRITERES if k in notes)
    return f"""Tu es un prévisionniste. Nous sommes le {jeu}. Donne la probabilité que la réponse soit OUI.

{_entete(q, p_b, jeu)}

LE COMITÉ A NOTÉ SÉPARÉMENT CES SITUATIONS (1 à 4 ; pour « freins », 4 = obstacles forts) :
{lignes}

RÉSULTATS DE RECHERCHE (antérieurs au {jeu}) :
{gi.bloc(recherche, 4000)}

Pars du taux de base. Si plusieurs situations convergent nettement dans le même sens, n'hésite pas à t'en écarter
franchement ; si elles se contredisent ou manquent d'information, reste près du taux de base.
Rends UNIQUEMENT un objet JSON : {{"p": nombre entre 0,01 et 0,99, "raison": "une phrase"}}"""


def lire_notes(r: dict) -> dict:
    out = {}
    for k in CLES:
        v = (r.get("notes") or {}).get(k)
        try:
            n = int(round(float(v["note"] if isinstance(v, dict) else v)))
        except (TypeError, ValueError, KeyError):
            continue
        if 1 <= n <= 4:
            out[k] = {"note": n, "pourquoi": str(v.get("pourquoi", ""))[:300] if isinstance(v, dict) else ""}
    return out


def lignes() -> list[dict]:
    if not FICHIER.exists():
        return []
    return [json.loads(l) for l in FICHIER.read_text(encoding="utf-8").splitlines() if l.strip()]


def candidates() -> list[dict]:
    """Questions Metaculus de 2026, cohorte complète, avec leur taux de base « semblables » ; ordre fixé."""
    xs = bj.cohorte_complete([json.loads(l) for l in bj.REGISTRE.read_text(encoding="utf-8").splitlines() if l.strip()])
    bj.calculer(xs)
    out = [x for x in xs if x["source"] == "metaculus" and x["jeu"] >= bj.COUPURE]
    return sorted(out, key=rang)


def resumer(ls: list[dict]) -> dict:
    import score_registre as sr
    pl = sr.log_score
    ok = [x for x in ls if x.get("issue") in (0, 1) and x.get("p_A") is not None and x.get("p_M") is not None
          and not x.get("exclue")]
    out = {"version_bot": ap.VERSION_BOT, "n": len(ok), "note": "perte log, plus bas = mieux ; A et M sur les mêmes entrées"}
    if not ok:
        return out
    n = len(ok)
    moy = lambda k: round(sum(pl(x[k], x["issue"]) for x in ok) / n, 4)

    def disc(k):
        o = [x[k] for x in ok if x["issue"] == 1]
        z = [x[k] for x in ok if x["issue"] == 0]
        return round(sum(o) / len(o) - sum(z) / len(z), 3) if o and z else None
    out.update({"B_semblables": moy("p_B"), "A": moy("p_A"), "M": moy("p_M"),
                "discrimination": {"B": disc("p_B"), "A": disc("p_A"), "M": disc("p_M")},
                "oui": round(sum(x["issue"] for x in ok) / n, 3),
                "critere": sr.critere_ombre_b([dict(x, p_B=x["p_A"], o={"p": x["p_M"]}) for x in ok], "o",
                                              "jugement_alphabet", exclure_vus=False)})
    return out


async def principal(n: int, budget: float) -> int:
    from forecasting_tools import MonetaryCostManager
    if not ar.recherche_bornee_disponible():
        print("Il faut une recherche bornable dans le temps (EXA_API_KEY ou TINYFISH_API_KEY). Rien n'est lancé.")
        return 1
    deja = {x["question_id"] for x in lignes()}
    cand = candidates()
    print(f"{len(cand)} questions Metaculus candidates (2026, cohorte complète).")
    textes: dict[str, dict] = {}
    REGISTRE.mkdir(exist_ok=True)
    faites, cumul, pire = 0, 0.0, 0.0
    with FICHIER.open("a", encoding="utf-8") as f:
        for x in cand:
            qid = f'{x["source"]}:{x["id"]}:{x["jeu"]}'
            if faites >= n:
                break
            if qid in deja:
                continue
            if fb.depasse(cumul, pire, budget):
                print(f"Plafond atteint : {cumul:.2f} $. Arrêt.")
                break
            if x["jeu"] not in textes:
                try:
                    qs = await fb._json(f"{fb.DEPOT}/question_sets/{x['jeu']}-llm.json")
                    textes[x["jeu"]] = {str(q["id"]): q for q in qs.get("questions", [])}
                except Exception:
                    textes[x["jeu"]] = {}
            src = textes[x["jeu"]].get(x["id"])
            if not src:
                continue
            q = {"titre": x["titre"], "cloture": x["cloture"],
                 "criteres": str(src.get("market_info_resolution_criteria") or src.get("resolution_criteria") or ""),
                 "contexte": str(src.get("background") or "")}       # jamais freeze_datetime_value ni source_intro
            p_b = float(x["p_S"])
            with MonetaryCostManager() as cm:
                info = datetime.fromisoformat(x["jeu"]).replace(tzinfo=timezone.utc)
                # 0.10.258 : recherche gelée par question (cache) et tracée (trace_recherche.py)
                rech, du_cache = await tr.chercher_fige(qid, x["titre"], info, ar.chercher_avant)
                res, exclue = {"recherche": {**tr.tracer(rech, x["jeu"]), "cache": du_cache}}, False
                try:
                    r = ap.extraire_json(await am.llm(MODELE, temperature=0.2, timeout=300, allowed_tries=2).invoke(
                        consigne_a(q, p_b, rech, x["jeu"])))
                    res["p_A"] = min(0.99, max(0.01, float(r["p"])))
                    exclue = bool(r.get("connait_issue"))
                except Exception as e:
                    res["erreur_A"] = f"{type(e).__name__}: {e}"[:200]
                try:
                    r = ap.extraire_json(await am.llm(MODELE, temperature=0.2, timeout=300, allowed_tries=2).invoke(
                        consigne_notes(q, p_b, rech, x["jeu"])))
                    res["notes"] = lire_notes(r)
                    exclue = exclue or bool(r.get("connait_issue"))
                    r = ap.extraire_json(await am.llm(MODELE, temperature=0.2, timeout=300, allowed_tries=2).invoke(
                        consigne_finale(q, p_b, res["notes"], rech, x["jeu"])))
                    res["p_M"] = min(0.99, max(0.01, float(r["p"])))
                    res["raison_M"] = str(r.get("raison", ""))[:300]
                except Exception as e:
                    res["erreur_M"] = f"{type(e).__name__}: {e}"[:200]
                cout = float(cm.current_usage or 0)
            ligne = {"type": "banc_jugement_alphabet", "jeu": x["jeu"], "question_id": qid, "source_question": "metaculus",
                     "version_bot": ap.VERSION_BOT, "titre": x["titre"], "forme": x["forme"], "issue": x["issue"],
                     "p_B": p_b, **res, "exclue": exclue, "modele": MODELE, "cout_usd": round(cout, 4),
                     "licence": "ForecastBench, Forecasting Research Institute, CC BY-SA 4.0"}
            f.write(json.dumps(ligne, ensure_ascii=False) + "\n")
            f.flush()
            deja.add(qid)
            cumul += cout
            pire = max(pire, cout)
            if res.get("p_A") is not None and res.get("p_M") is not None:
                faites += 1
            print(f"{qid[:50]} : A {res.get('p_A')} · M {res.get('p_M')} · B {p_b:.3f} · issue {x['issue']} · {cout:.4f} $")
    r = resumer(lignes())
    RESUME.write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{faites} question(s) ; coût {cumul:.2f} $ (plafond {budget:.2f} $).")
    print(json.dumps(r, ensure_ascii=False, indent=1)[:2500])
    return 0


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("--n", type=int, default=150)
    a.add_argument("--budget", type=float, default=4.0)
    o = a.parse_args()
    sys.exit(asyncio.run(principal(o.n, o.budget)))
