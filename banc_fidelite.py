"""Banc de fidélité des synthèses de recherche (bot 0.10.215, mesure seule, ne change rien au bot).

Décision d'auteur du 2026-11-17 (0 h 45). Origine : May, Nunan, Marshall & Palace, « A Taxonomy of Bullshit »
(Policing, 2026 ; Chroniques de la Recherche n° 28, Veille Magazine) : trois familles d'erreurs des modèles de langue,
chacune avec sa ressource minimale de détection. L'erreur de FIDÉLITÉ (la synthèse dit autre chose que sa source) se
détecte en comparant la source et la production, sans jugement de modèle.

Question : à quelle fréquence le modèle met-il, dans une synthèse de résultats de recherche, des nombres ou des dates
qui ne figurent nulle part dans ce qu'il a lu ? Les rapports archivés du bot ne gardent pas le texte des recherches
(seulement les requêtes) : la mesure ne peut pas être rétrospective. On la fait donc sur un banc à part.

Pour chaque question de série ForecastBench déjà résolue (comme le banc du bras A) : recherche bornée à la date
d'information, puis synthèse par le modèle des faits datés et chiffrés utiles. Contrôle par le code : chaque nombre de
la synthèse (au moins deux chiffres, ou décimal) doit figurer dans le corpus lu (question, critères, contexte, date du
jeu, résultats de recherche tels que montrés au modèle).

C'est une BORNE HAUTE des erreurs de fidélité : un nombre non trouvé peut aussi être un calcul légitime (« trois sur dix »
→ « 30 % »), une conversion d'unité (« 1,2 million » ↔ « 1 200 000 ») ou une connaissance du modèle (fuite plutôt
qu'erreur). Les cas non trouvés sont gardés avec un court extrait de la SYNTHÈSE (jamais de la source) pour relecture.

Registre : registre/banc-fidelite.jsonl ; résumé : registre/banc-fidelite.json.
Usage : python banc_fidelite.py --n 30 --budget 1
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path

REGISTRE = Path("registre")
FICHIER = REGISTRE / "banc-fidelite.jsonl"
RESUME = REGISTRE / "banc-fidelite.json"
SOURCES = ("fred", "dbnomics", "acled")
APRES = "2026-07-01"
_NOMBRE = re.compile(r"\d+(?:[.,   ]\d+)*")


def formes(jeton: str) -> set[str]:
    """Formes canoniques possibles d'un nombre écrit (séparateurs de milliers ou décimale, à la française ou à
    l'anglaise). « 1,234 » → {"1234", "1.234"} ; « 3,5 » → {"3.5"} ; « 1 200 000 » → {"1200000"}."""
    t = re.sub(r"[   ]", "", jeton)
    out = set()
    if re.fullmatch(r"\d+", t):
        out.add(t.lstrip("0") or "0")
        return out
    if re.fullmatch(r"\d{1,3}([.,]\d{3})+", t):                      # séparateurs de milliers
        out.add(re.sub(r"[.,]", "", t).lstrip("0") or "0")
    m = re.fullmatch(r"(\d+(?:[.,]\d{3})*)[.,](\d+)", t)             # une décimale (avec milliers éventuels)
    if m:
        entier = (re.sub(r"[.,]", "", m.group(1)).lstrip("0") or "0")
        dec = m.group(2).rstrip("0")
        out.add(entier + ("." + dec if dec else ""))
    return out


def jetons(texte: str) -> list[str]:
    """Nombres d'un texte ; une date pointée (12.10.2026) est coupée en ses parties."""
    out = []
    for j in _NOMBRE.findall(texte or ""):
        j = j.strip()
        if j.count(".") >= 2 and not re.search(r"\d{1,3}(\.\d{3}){2,}$", j):
            out += [p for p in j.split(".") if p]
        else:
            out.append(j)
    return out


def significatif(jeton: str) -> bool:
    """Au moins deux chiffres, ou un décimal : un chiffre isolé (« 3 pays ») trouverait presque toujours un écho."""
    t = re.sub(r"[   ]", "", jeton)
    return len(re.sub(r"\D", "", t)) >= 2 or bool(re.search(r"[.,]\d", t))


def controler(synthese: str, corpus: str) -> dict:
    """Nombres significatifs de la synthèse absents du corpus, avec un extrait de la synthèse (pas de la source)."""
    lus = set()
    for j in jetons(corpus):
        lus |= formes(j)
    vus, absents = 0, []
    for m in _NOMBRE.finditer(synthese or ""):
        for j in jetons(m.group(0)):
            if not significatif(j):
                continue
            vus += 1
            if not (formes(j) & lus):
                debut = max(0, m.start() - 60)
                absents.append({"nombre": j, "extrait_synthese": synthese[debut:m.end() + 40].replace("\n", " ")})
    return {"nombres": vus, "absents": len(absents), "cas": absents[:12]}


def consigne(x: dict, recherche_bornee: str, jeu: str) -> str:
    return f"""Nous sommes le {jeu}. Voici une question de prévision et des résultats de recherche.

QUESTION : {x['titre']}
CRITÈRES DE RÉSOLUTION : {x['criteres']}
CONTEXTE : {x['contexte'][:3000]}

RÉSULTATS DE RECHERCHE (antérieurs au {jeu}) :
{recherche_bornee}

Résume en 5 à 8 phrases les faits datés et chiffrés des résultats de recherche qui sont utiles pour répondre à la
question (valeurs, dates, tendances). Ne donne pas de probabilité. Rends UNIQUEMENT un objet JSON :
{{"synthese": "…"}}"""


def rang(qid: str) -> str:
    return hashlib.sha1(qid.encode()).hexdigest()


def lignes() -> list[dict]:
    if not FICHIER.exists():
        return []
    return [json.loads(l) for l in FICHIER.read_text(encoding="utf-8").splitlines() if l.strip()]


def resumer(ls: list[dict]) -> dict:
    out = {"note": ("borne haute des erreurs de fidélité : nombres (au moins deux chiffres, ou décimal) de la synthèse "
                    "absents du corpus lu ; un absent peut être un calcul, une conversion ou une connaissance du modèle")}
    par: dict[str, list[dict]] = {}
    for x in ls:
        if x.get("controle"):
            par.setdefault(x["modele"], []).append(x)
    for m, xs in sorted(par.items()):
        n_nb = sum(x["controle"]["nombres"] for x in xs)
        n_abs = sum(x["controle"]["absents"] for x in xs)
        avec = sum(1 for x in xs if x["controle"]["absents"] > 0)
        out[m] = {"syntheses": len(xs), "nombres": n_nb, "absents": n_abs,
                  "part_nombres_absents": round(n_abs / n_nb, 4) if n_nb else None,
                  "part_syntheses_avec_absent": round(avec / len(xs), 4),
                  "par_source": {s: {"syntheses": len(ys), "part_nombres_absents":
                                     round(sum(y["controle"]["absents"] for y in ys) /
                                           max(1, sum(y["controle"]["nombres"] for y in ys)), 4)}
                                 for s in sorted({x["source_question"] for x in xs})
                                 for ys in [[y for y in xs if y["source_question"] == s]]}}
    return out


async def principal(n: int, budget: float) -> int:
    import alphabet_modeles as am
    import alphabet_pipeline as ap
    import alphabet_retro as ar
    import banc_forecastbench as fb
    import garde_injection as gi
    from forecasting_tools import MonetaryCostManager
    modeles = [m.strip() for m in (os.environ.get("ALPHABET_BANC_FIDELITE_MODELES") or "azure_ai/gpt-5-mini").split(",")
               if m.strip()]
    if not ar.recherche_bornee_disponible():
        print("Il faut une recherche bornable dans le temps (EXA_API_KEY ou TINYFISH_API_KEY). Rien n'est lancé.")
        return 1
    am.installer_traceur()
    deja = {(x["question_id"], x["modele"]) for x in lignes()}
    jeux = sorted(fb.jeux_candidats(date.today(), date.fromisoformat(APRES), n_max=26))
    tous = []
    for j in jeux:
        try:
            qs = await fb._json(f"{fb.DEPOT}/question_sets/{j}-llm.json")
            rs = await fb._json(f"{fb.DEPOT}/resolution_sets/{j}_resolution_set.json")
        except Exception as e:
            print(f"Jeu {j} indisponible : {type(e).__name__}")
            continue
        items = sorted((fb.construire(i, j) for i in fb.apparier(qs, rs, SOURCES)), key=lambda x: rang(x["qid"]))
        tous += [(r, j, x) for r, x in enumerate(items)]
    tous.sort(key=lambda t: (t[0], t[1]))
    print(f"{len(tous)} questions candidates, {len(jeux)} jeux ; modèles : {', '.join(modeles)}.")
    REGISTRE.mkdir(exist_ok=True)
    faites, cumul, pire = 0, 0.0, 0.0
    with FICHIER.open("a", encoding="utf-8") as f:
        for _, j, x in tous:
            if faites >= n:
                break
            if all((x["qid"], m) in deja for m in modeles):
                continue
            if fb.depasse(cumul, pire, budget):
                print(f"Plafond atteint : {cumul:.2f} $ + {pire:.2f} $ > {budget:.2f} $. Arrêt.")
                break
            with MonetaryCostManager() as cm:
                info = datetime.fromisoformat(j).replace(tzinfo=timezone.utc)
                try:
                    recherche = await ar.chercher_avant(x["titre"], info)
                except Exception as e:
                    print(f"{x['qid'][:50]} : recherche indisponible ({type(e).__name__})")
                    continue
                if len(re.sub(r"\s", "", recherche)) < 200:
                    continue                                  # rien à résumer : la mesure n'a pas de sens
                bornee = gi.bloc(recherche, 6000)
                corpus = " ".join([j, x["titre"], x["criteres"], x["contexte"][:3000], bornee])
                texte = consigne(x, bornee, j)
                for m in modeles:
                    if (x["qid"], m) in deja:
                        continue
                    ligne = {"type": "banc_fidelite", "jeu": j, "source_question": x["source"], "question_id": x["qid"],
                             "version_bot": ap.VERSION_BOT, "modele": m}
                    try:
                        r = ap.extraire_json(await am.llm(m, temperature=0.2, timeout=300, allowed_tries=2).invoke(texte))
                        synthese = str(r.get("synthese") or "")
                        ligne["controle"] = controler(synthese, corpus)
                        ligne["longueur_synthese"] = len(synthese)
                    except Exception as e:
                        ligne["erreur"] = f"{type(e).__name__}: {e}"[:200]
                    f.write(json.dumps(ligne, ensure_ascii=False) + "\n")
                    f.flush()
                    c = ligne.get("controle") or {}
                    print(f"{x['qid'][:50]} · {m} : {c.get('absents')} absent(s) sur {c.get('nombres')} nombre(s)")
                cout = float(cm.current_usage or 0)
            cumul += cout
            pire = max(pire, cout)
            faites += 1
    r = resumer(lignes())
    RESUME.write_text(json.dumps(r, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    l = ["## Banc de fidélité des synthèses (borne haute)", "", f"{faites} question(s) ce passage, {cumul:.2f} $.", ""]
    for m, v in r.items():
        if isinstance(v, dict):
            l.append(f"- {m} : {v['syntheses']} synthèses, {v['absents']} nombre(s) absent(s) sur {v['nombres']} "
                     f"({v['part_nombres_absents']}) ; synthèses avec au moins un absent : {v['part_syntheses_avec_absent']}")
    print("\n".join(l))
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as fs:
            fs.write("\n".join(l) + "\n")
    return 0


if __name__ == "__main__":
    a_ = argparse.ArgumentParser()
    a_.add_argument("--n", type=int, default=30)
    a_.add_argument("--budget", type=float, default=1.0)
    a = a_.parse_args()
    sys.exit(asyncio.run(principal(a.n, a.budget)))
