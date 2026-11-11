"""Puissance du test C contre B selon la qualité du lecteur (bot 0.10.29 ; suggestion d'une relecture du bot par Mistral,
retenue par l'auteur le 2026-11-11).

Le test principal compare C (l'alphabet joué par CE lecteur) à B. Un lecteur qui manque des cartes présentes et en lit
d'absentes réduit le gain que l'alphabet pourrait apporter, donc allonge le nombre de questions nécessaires pour le
détecter. Ce script le chiffre, sans aucun appel à un modèle :

  1. monde : le programme génératif du skill (strate 7) tire une situation (`tirer_situation`) ; la probabilité de
     l'événement, sachant les vraies cartes, est celle du même programme (lecteur parfait, absentes rejetées) ;
  2. lecteur simulé : chaque candidate présente est lue F ou f avec les sensibilités, chaque absente avec les taux de
     faux positifs (candidates : les présentes et autant d'absentes, au moins trois, comme dans le monde synthétique) ;
  3. C = le calcul publié (f × produit des λ des cartes lues ayant une arête vers la cible, plafonné) ; B = f ;
  4. gain par question = 100 × (ln p_C(issue) − ln p_B(issue)), puis questions nécessaires pour que le test
     séquentiel du score conclue dans 80 % des cas.

RÉSERVE MAJEURE : le monde simulé EST le modèle du skill (matrice et λ supposés vrais). Le gain obtenu est la promesse
interne de l'alphabet, une borne haute ; si la matrice se trompe, le gain réel est plus faible. Ce que le calcul dit
sûrement, c'est l'effet RELATIF du lecteur : combien de questions coûte chaque point de sensibilité ou de faux positif.

    python puissance_lecteur.py            # écrit registre/puissance-lecteur-<date>.json
"""
from __future__ import annotations

import json
import math
import random
from datetime import datetime, timezone

import alphabet_pipeline as ap
import score_registre as sr

SCENARIOS = {
    "parfait": {"sens_F": 1.0, "sens_f": 0.0, "fp_F": 0.0, "fp_f": 0.0},
    "stipule": None,                                                       # paramètres du génératif
    "mesure": {"sens_F": 0.26, "sens_f": 0.32, "fp_F": 0.0, "fp_f": 0.17},  # monde synthétique, protocole 3, vérifié
    "mesure_sensibilite_stipulee": {"sens_F": 0.5, "sens_f": 0.3, "fp_F": 0.0, "fp_f": 0.17},
    "mesure_faux_positifs_stipules": {"sens_F": 0.26, "sens_f": 0.32, "fp_F": 0.01, "fp_f": 0.05},
}


def _verite(m, vraies: list[str], cible: str, f: float, cartes: list[str], strate: int) -> float:
    params = dict(m.P["generatif"], sens_F=0.999, sens_f=0.0, fp_F=0.001, fp_f=0.0)
    etat = {"mots": [{"c": k.split("@")[0], "s": strate, "i": "F", "q": []} for k in vraies]}
    rejets = {f"{c}@{strate}": "contredit" for c in cartes if f"{c}@{strate}" not in vraies and f"{c}@{strate}" != cible}
    src, _ = m.sources_de({"mots": etat["mots"], "date": "2026-11", "fenetre": "3 mois"}, cible, (), (), ())
    return m.p0_generatif(etat, cible, f, src, params, rejets)


def _c_publie(m, lues: dict[str, str], cible: str, f: float, strate: int) -> float:
    etat = {"mots": [{"c": k.split("@")[0], "s": strate, "i": i, "q": []} for k, i in lues.items()],
            "date": "2026-11", "fenetre": "3 mois"}
    src, _ = m.sources_de(etat, cible, (), (), ())
    lr = min(math.prod(x["lambda"] for x in src), m.P["plafond_LR"])
    return m.odds_module(f, lr)


def _echantillonneur(m, strate: int):
    """Les poids exacts de la loi a priori du génératif (comme `moteur.tirer_situation`), calculés une fois."""
    import bisect
    params = m.P["generatif"]
    cartes = [c for c in sorted(m.NOMS) if not m.hors_domaine(f"{c}@{strate}")]
    n = len(cartes)
    idx = {c: i for i, c in enumerate(cartes)}
    lp, la = math.log(params["pi_presence"]), math.log(1 - params["pi_presence"])
    couple = {}
    for a_, d in m.P["matrice"].items():
        for b_, I in d.items():
            if a_ in idx and b_ in idx:
                k_ = tuple(sorted((idx[a_], idx[b_])))
                couple[k_] = max(couple.get(k_, 0.0), math.log(m.P["lambda"][I]))
    cum, acc = [], 0.0
    for e in range(1 << n):
        lw = sum(lp if e >> i & 1 else la for i in range(n))
        lw += sum(l for (i, j), l in couple.items() if e >> i & 1 and e >> j & 1)
        acc += math.exp(lw)
        cum.append(acc)

    def tirer(rnd: random.Random) -> list[str]:
        e = bisect.bisect_left(cum, rnd.random() * acc)
        return sorted(f"{cartes[i]}@{strate}" for i in range(n) if e >> i & 1)
    return tirer, cartes


def monde(n: int = 1000, strate: int = 7, graine: int = 11) -> list[dict]:
    """Les questions simulées, tirées UNE fois et partagées par tous les scénarios de lecteur."""
    m = ap._moteur()
    rnd = random.Random(graine)
    tirer, cartes = _echantillonneur(m, strate)
    qs = []
    while len(qs) < n:
        vraies = tirer(rnd)
        absentes = [f"{c}@{strate}" for c in cartes if f"{c}@{strate}" not in vraies]
        if len(absentes) < 2:
            continue
        rnd.shuffle(absentes)
        cible = absentes[0]
        k = min(max(3, len(vraies)), len(absentes) - 1)
        f = 1 / (1 + math.exp(-rnd.uniform(math.log(0.05 / 0.95), 0.0)))
        p_vrai = _verite(m, vraies, cible, f, cartes, strate)
        qs.append({"vraies": vraies, "cible": cible, "absentes": absentes[1:1 + k], "f": f, "p_vrai": p_vrai,
                   "y": 1 if rnd.random() < p_vrai else 0})
    return qs


def simuler(lecteur: dict, qs: list[dict], strate: int = 7, graine: int = 13, generatif: bool = False) -> list[float]:
    m = ap._moteur()
    rnd = random.Random(graine)
    gains = []
    for q in qs:
        lues = {}
        for c in q["vraies"]:
            u = rnd.random()
            if u < lecteur["sens_F"]:
                lues[c] = "F"
            elif u < lecteur["sens_F"] + lecteur["sens_f"]:
                lues[c] = "f"
        for c in q["absentes"]:
            u = rnd.random()
            if u < lecteur["fp_F"]:
                lues[c] = "F"
            elif u < lecteur["fp_F"] + lecteur["fp_f"]:
                lues[c] = "f"
        if generatif:     # l'ombre générative (§36) : lit aussi les candidates NON ancrées comme des absences probables
            etat = {"mots": [{"c": k.split("@")[0], "s": strate, "i": i, "q": []} for k, i in lues.items()],
                    "date": "2026-11", "fenetre": "3 mois"}
            src, _ = m.sources_de(etat, q["cible"], (), (), ())
            rej = {c: "marqueur_non_rempli" for c in q["vraies"] + q["absentes"] if c not in lues}
            lec = {k: min(0.998, max(0.001, v)) for k, v in lecteur.items()}     # le génératif exige ]0, 1[
            for a_, b_ in (("sens_F", "sens_f"), ("fp_F", "fp_f")):
                if lec[a_] + lec[b_] > 0.998:
                    lec[b_] = max(0.001, 0.998 - lec[a_])
            p_c = ap.borner(m.p0_generatif(etat, q["cible"], q["f"], src, dict(m.P["generatif"], **lec), rej))
        else:
            p_c = ap.borner(_c_publie(m, lues, q["cible"], q["f"], strate))
        p_b = ap.borner(q["f"])
        y = q["y"]
        gains.append(100 * (math.log(p_c if y else 1 - p_c) - math.log(p_b if y else 1 - p_b)))
    return gains


def questions_80(gains: list[float], essais: int = 60, n_max: int = 3000, graine: int = 5) -> int | None:
    """Questions pour que le test séquentiel du score (e-valeur, α = 5 %) conclue dans 80 % des essais, en tirant les
    gains dans la distribution simulée (rééchantillonnage)."""
    m = sr.borne_gain_C_B()
    rnd = random.Random(graine)
    temps = []
    for _ in range(essais):
        g, atteint = [], None
        for k in range(1, n_max + 1):
            g.append(gains[rnd.randrange(len(gains))])
            if k % 10 == 0 and sr.e_valeur(g, m) >= 1 / sr.ALPHA:
                atteint = k
                break
        temps.append(atteint or n_max + 1)
    temps.sort()
    q = temps[int(0.8 * len(temps)) - 1]
    return None if q > n_max else q


N_GENERATIF = 300


def lancer(n: int = 1000) -> dict:
    m = ap._moteur()
    g = m.P["generatif"]
    out = {"calcule_le": datetime.now(timezone.utc).isoformat(timespec="seconds"), "version_bot": ap.VERSION_BOT,
           "version_skill": ap.version_skill(), "questions_simulees": n,
           "reserve": "monde = modèle du skill : gain interne (borne haute) ; l'effet RELATIF du lecteur est le résultat sûr",
           "scenarios": {}}
    qs = monde(n)
    out["gain_si_C_valait_la_verite_points"] = round(sum(
        100 * (math.log(ap.borner(q["p_vrai"]) if q["y"] else 1 - ap.borner(q["p_vrai"]))
               - math.log(ap.borner(q["f"]) if q["y"] else 1 - ap.borner(q["f"]))) for q in qs) / len(qs), 2)
    for nom, lec in SCENARIOS.items():
        lec = lec or {k: g[k] for k in ("sens_F", "sens_f", "fp_F", "fp_f")}
        gains = simuler(lec, qs)
        moy = sum(gains) / len(gains)
        sd = math.sqrt(sum((x - moy) ** 2 for x in gains) / (len(gains) - 1))
        gg = simuler(lec, qs[:N_GENERATIF], generatif=True)      # plus lent (énumération exacte) : sous-échantillon
        out["scenarios"][nom] = {"lecteur": lec, "gain_moyen_points": round(moy, 2), "ecart_type": round(sd, 1),
                                 "questions_80_pourcent": questions_80(gains) or "> 3000",
                                 "C_generatif": {"questions": len(gg), "gain_moyen_points": round(sum(gg) / len(gg), 2),
                                                 "questions_80_pourcent": questions_80(gg) or "> 3000"}}
    return out


def main() -> int:
    r = lancer()
    for nom, s in r["scenarios"].items():
        print(f"{nom:32s} C publié {s['gain_moyen_points']:7.2f} pts (σ {s['ecart_type']}) → "
              f"{s['questions_80_pourcent']} questions ; C génératif {s['C_generatif']['gain_moyen_points']:6.2f} pts → "
              f"{s['C_generatif']['questions_80_pourcent']}")
    print(f"Plafond : si C valait la vraie probabilité du modèle, gain moyen {r['gain_si_C_valait_la_verite_points']} pts")
    ap.REGISTRE.mkdir(parents=True, exist_ok=True)
    (ap.REGISTRE / f"puissance-lecteur-{r['calcule_le'][:10]}.json").write_text(
        json.dumps(r, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
