"""Banc des jugements intermédiaires (0.10.124, décision d'auteur du 2026-11-15, d'après la thèse d'Olivier Sibony,
Paris-Dauphine 2017, chap. 5 cas n° 5 ; Kahneman, Lovallo et Sibony, HBR 2019).

Sur les questions de conflits (ACLED) jamais lues, une seule recherche bornée avant la date d'information, puis sur les
mêmes entrées :
- A' : la consigne du bras A, inchangée ;
- M  : (1) sept notes de 1 à 4, chacune par rapport à l'ordinaire du pays sur l'année passée, sans probabilité ;
       (2) le jugement final, qui voit le taux de base, la série et les notes, mais plus les extraits bruts.
Critère : preenregistrements/jugements-intermediaires.md. Registre : registre/banc-m.jsonl ; résumé : banc-m.json.

    python banc_m.py --n 150 --budget 3
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import alphabet_modeles as am
import alphabet_pipeline as ap
import alphabet_retro as ar
import banc_a as ba
import banc_forecastbench as fb

REGISTRE = Path("registre")
FICHIER = REGISTRE / "banc-m.jsonl"
RESUME = REGISTRE / "banc-m.json"
MODELE = "azure_ai/gpt-5-mini"
VUS = Path("preenregistrements/silence-vus.txt")
PLATT = (-1.354, 0.775)          # figé dans silence-et-calibrage.md

# (clé, carte de l'alphabet, ce qu'on note ; 1 = nettement sous l'ordinaire, 4 = nettement au-dessus)
CRITERES = (
    ("tendance", "CROISSANCE", "la dynamique récente de ce type d'événement dans ce pays (1 = en net recul, 4 = en nette hausse)"),
    ("engagements", "RÉCIPROCITÉ", "les engagements datés qui poussent vers l'événement : annonces, menaces, appels à "
                                   "manifester, ultimatums (1 = aucun, 4 = nombreux et précis)"),
    ("couverture", "TRACE·MÉMOIRE", "le volume et la fraîcheur des informations disponibles sur ce pays et ce type "
                                    "d'événement (1 = presque rien, 4 = abondant et récent)"),
    ("declencheur", "SEUIL", "un choc récent ou une échéance proche capable de faire basculer la situation "
                             "(1 = aucun, 4 = net et imminent)"),
    ("freins", "CONTRAINTE", "les forces qui retiennent : forces de l'ordre, accords, épuisement, riposte probable de "
                             "l'adversaire (1 = faibles, 4 = fortes)"),
    ("calendrier", "PÉRIODICITÉ", "la période à venir est-elle habituellement plus active que la moyenne "
                                  "(1 = nettement moins, 4 = nettement plus)"),
    ("proportion", "PROPORTION", "la distance entre le niveau actuel et le seuil fixé par la question "
                                 "(1 = seuil très loin, 4 = seuil déjà atteint ou tout proche)"),
)
CLES = tuple(c[0] for c in CRITERES)


def _donnees(vue: dict | None, releve: list[dict], jeu: str) -> str:
    pts = "\n".join(f"{p['date'][:10]} : {p['valeur']}" for p in releve[-30:]) or "(aucun relevé)"
    base = (f"{vue['frequence']:.3f} — {vue.get('classe_de_reference')} ; calcul : {vue.get('calcul')}"
            if vue and vue.get("frequence") is not None else "(non calculé)")
    return f"TAUX DE BASE CALCULÉ PAR LE CODE : {base}\nDERNIERS POINTS DE LA SÉRIE (avant le {jeu}) :\n{pts}"


def consigne_notes(x: dict, vue: dict | None, releve: list[dict], recherche: str, jeu: str) -> str:
    liste = "\n".join(f"- \"{k}\" : {quoi}" for k, _, quoi in CRITERES)
    return f"""Nous sommes le {jeu}. Tu prépares un comité de prévision. Tu NE DONNES PAS de probabilité : tu notes
seulement des critères séparés, un par un, sans te demander encore quelle sera la réponse.

QUESTION : {x['titre']}
CRITÈRES DE RÉSOLUTION : {x['criteres']}
CONTEXTE : {x['contexte'][:3000]}

{_donnees(vue, releve, jeu)}

RÉSULTATS DE RECHERCHE (antérieurs au {jeu}) :
{recherche[:6000] or "(aucun)"}

Note chaque critère de 1 à 4 PAR RAPPORT À L'ORDINAIRE de ce pays pour ce type d'événement sur l'année passée
(2 ou 3 = ordinaire). Juge chaque critère pour lui-même, sans laisser les autres l'influencer. Si l'information
manque, dis-le dans la justification et note 2.
{liste}
Rends UNIQUEMENT un objet JSON : {{"notes": {{"tendance": {{"note": 1-4, "pourquoi": "une phrase"}}, ...}},
"connait_issue": true ou false}}"""


def consigne_finale(x: dict, vue: dict | None, releve: list[dict], notes: dict, jeu: str) -> str:
    lignes = "\n".join(f"- {carte} ({k}) : {notes[k]['note']}/4 — {notes[k].get('pourquoi', '')}"
                       for k, carte, _ in CRITERES if k in notes)
    return f"""Tu es un prévisionniste. Nous sommes le {jeu}. Donne la probabilité que la réponse soit OUI.

QUESTION : {x['titre']}
CRITÈRES DE RÉSOLUTION : {x['criteres']}

{_donnees(vue, releve, jeu)}

LE COMITÉ A NOTÉ SÉPARÉMENT CES CRITÈRES (1 à 4, par rapport à l'ordinaire du pays ; 2 ou 3 = ordinaire) :
{lignes}

Pars du taux de base. Les notes ne sont pas toutes dans le même sens : pèse les points forts ET les points faibles,
et n'ajuste que si les notes s'écartent nettement de l'ordinaire.
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


def vus() -> set[str]:
    if not VUS.exists():
        return set()
    return {l.strip() for l in VUS.read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("#")}


def lignes() -> list[dict]:
    if not FICHIER.exists():
        return []
    return [json.loads(l) for l in FICHIER.read_text(encoding="utf-8").splitlines() if l.strip()]


def recal(p: float) -> float:
    return ba.sigmoide(PLATT[0] + PLATT[1] * ba.logit(p))


def lineaire_lojo(ls: list[dict]) -> list[dict]:
    """Descriptif : logit p = w0 + w1·logit(B) + Σ βk·(note_k − 2,5), un jeu laissé de côté, a priori normal."""
    import banc_indicateurs as bi
    sd = [1.0, 1.0] + [0.5] * len(CLES)
    moy = [0.0, 1.0] + [0.0] * len(CLES)
    feats = lambda x: [1.0, ba.logit(x["p_B"])] + [x["notes"][k]["note"] - 2.5 for k in CLES]
    out = []
    for j in sorted({x["jeu"] for x in ls}):
        w = bi.ajuster([(feats(x), x["issue"]) for x in ls if x["jeu"] != j], sd, moy)
        for x in ls:
            if x["jeu"] == j:
                out.append(dict(x, p_lin=ba.sigmoide(sum(a * b for a, b in zip(w, feats(x))))))
    return out


def resumer(ls: list[dict]) -> dict:
    import score_registre as sr
    pl = sr.log_score
    ok = sorted((x for x in ls if x.get("issue") in (0, 1) and x.get("p_A") is not None and x.get("p_M") is not None and ba.version(x) >= (0, 10, 127)
                 and not x.get("exclue")), key=lambda x: x["ordre"])
    out = {"version_bot": ap.VERSION_BOT, "n": len(ok), "note": "perte log, plus bas = mieux ; A' et M sur les mêmes entrées"}
    if not ok:
        return out
    n = len(ok)
    moy = lambda f: round(sum(pl(f(x), x["issue"]) for x in ok) / n, 4)
    out.update({"A": moy(lambda x: x["p_A"]), "M": moy(lambda x: x["p_M"]), "B": moy(lambda x: x["p_B"]),
                "A_recalibre": moy(lambda x: recal(x["p_A"])),
                "p_moyenne": {"A": round(sum(x["p_A"] for x in ok) / n, 3), "M": round(sum(x["p_M"] for x in ok) / n, 3),
                              "observe": round(sum(x["issue"] for x in ok) / n, 3)},
                "critere": sr.critere_ombre_b([dict(x, p_B=x["p_A"], o={"p": x["p_M"]}) for x in ok], "o",
                                              "jugements_intermediaires", exclure_vus=False)})
    # amendement du 2026-11-15 (16 h 33) : critère sur les questions « une fois » seulement, versions ≥ 0.10.136
    une = [x for x in ok if "ten times" not in x.get("titre", "") and ba.version(x) >= (0, 10, 136)]
    if une:
        out["une_fois"] = {"n": len(une), "A": round(sum(pl(x["p_A"], x["issue"]) for x in une) / len(une), 4),
                           "M": round(sum(pl(x["p_M"], x["issue"]) for x in une) / len(une), 4),
                           "B": round(sum(pl(x["p_B"], x["issue"]) for x in une) / len(une), 4),
                           "critere": sr.critere_ombre_b([dict(x, p_B=x["p_A"], o={"p": x["p_M"]}) for x in une], "o",
                                                         "jugements_intermediaires", exclure_vus=False)}
    complets = [x for x in ok if all(k in (x.get("notes") or {}) for k in CLES)]
    if len({x["jeu"] for x in complets}) >= 2:
        cv = lineaire_lojo(complets)
        out["lineaire_descriptif"] = {"n": len(cv), "lineaire": round(sum(pl(x["p_lin"], x["issue"]) for x in cv) / len(cv), 4),
                                      "A_meme_questions": round(sum(pl(x["p_A"], x["issue"]) for x in cv) / len(cv), 4)}
    import audit_b                       # 0.10.130 : garde-fou sur B, par forme de question
    out["audit_b"] = audit_b.pour_resume(ls)
    return out


async def principal(n: int, budget: float) -> int:
    from forecasting_tools import MonetaryCostManager
    if not ar.recherche_bornee_disponible():
        print("Il faut une recherche bornable dans le temps (EXA_API_KEY ou TINYFISH_API_KEY). Rien n'est lancé.")
        return 1
    exclus = vus()
    deja = {x["question_id"] for x in lignes()}
    jeux = sorted(fb.jeux_candidats(date.today(), date.fromisoformat(ba.APRES), n_max=26))
    tous = []
    for j in jeux:
        if j in ba.JEUX_VUS:
            continue
        try:
            qs = await fb._json(f"{fb.DEPOT}/question_sets/{j}-llm.json")
            rs = await fb._json(f"{fb.DEPOT}/resolution_sets/{j}_resolution_set.json")
        except Exception as e:
            print(f"Jeu {j} indisponible : {type(e).__name__}")
            continue
        items = sorted((fb.construire(i, j) for i in fb.apparier(qs, rs, ("acled",))), key=lambda x: ba.rang(x["qid"]))
        tous += [(r, j, x) for r, x in enumerate(items) if x["qid"] not in exclus]
    tous.sort(key=lambda t: (t[0], t[1]))
    print(f"{len(tous)} questions ACLED jamais lues, entrelacées.")
    REGISTRE.mkdir(exist_ok=True)
    faites, cumul, pire = 0, 0.0, 0.0
    with FICHIER.open("a", encoding="utf-8") as f:
        for r_, j, x in tous:
            if faites >= n:
                break
            if x["qid"] in deja:
                continue
            if fb.depasse(cumul, pire, budget):
                print(f"Plafond atteint : {cumul:.2f} $. Arrêt.")
                break
            with MonetaryCostManager() as cm:
                vue = await fb.vue_calculee(x, x["_q"], j)
                if not vue or vue.get("frequence") is None:
                    continue
                releve = (x.get("_releve") or {}).get("points") or []
                info = datetime.fromisoformat(j).replace(tzinfo=timezone.utc)
                try:
                    rech = await ar.chercher_avant(x["titre"], info)
                except Exception as e:
                    rech = f"(recherche indisponible : {type(e).__name__})"
                res, exclue = {}, False
                try:
                    r = ap.extraire_json(await am.llm(MODELE, temperature=0.2, timeout=300, allowed_tries=2).invoke(
                        ba.consigne_a(x, vue, releve, rech, j)))
                    res["p_A"] = min(0.99, max(0.01, float(r["p"])))
                    exclue = bool(r.get("connait_issue"))
                except Exception as e:
                    res["erreur_A"] = f"{type(e).__name__}: {e}"[:200]
                try:
                    r = ap.extraire_json(await am.llm(MODELE, temperature=0.2, timeout=300, allowed_tries=2).invoke(
                        consigne_notes(x, vue, releve, rech, j)))
                    res["notes"] = lire_notes(r)
                    exclue = exclue or bool(r.get("connait_issue"))
                    r = ap.extraire_json(await am.llm(MODELE, temperature=0.2, timeout=300, allowed_tries=2).invoke(
                        consigne_finale(x, vue, releve, res["notes"], j)))
                    res["p_M"] = min(0.99, max(0.01, float(r["p"])))
                    res["raison_M"] = str(r.get("raison", ""))[:300]
                except Exception as e:
                    res["erreur_M"] = f"{type(e).__name__}: {e}"[:200]
                cout = float(cm.current_usage or 0)
            ligne = {"type": "banc_m", "jeu": j, "ordre": [r_, j], "question_id": x["qid"], "source_question": "acled",
                     "version_bot": ap.VERSION_BOT, "titre": x["titre"], "issue": x["issue"], "p_B": float(vue["frequence"]),
                     "n_extraits_bruts": rech.count("\n\n") if rech else 0, **res, "exclue": exclue,
                     "modele": MODELE, "cout_usd": round(cout, 4),
                     "licence": "ForecastBench, Forecasting Research Institute, CC BY-SA 4.0"}
            f.write(json.dumps(ligne, ensure_ascii=False) + "\n")
            f.flush()
            deja.add(x["qid"])
            cumul += cout
            pire = max(pire, cout)
            if res.get("p_A") is not None and res.get("p_M") is not None:
                faites += 1
            print(f"{x['qid'][:55]} : A' {res.get('p_A')} · M {res.get('p_M')} · B {vue['frequence']:.3f} · "
                  f"issue {x['issue']} · {cout:.4f} $")
    r = resumer(lignes())
    RESUME.write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{faites} question(s) ; coût {cumul:.2f} $ (plafond {budget:.2f} $).")
    print(json.dumps(r, ensure_ascii=False, indent=1)[:2500])
    return 0


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("--n", type=int, default=150)
    a.add_argument("--budget", type=float, default=3.0)
    o = a.parse_args()
    sys.exit(asyncio.run(principal(o.n, o.budget)))
