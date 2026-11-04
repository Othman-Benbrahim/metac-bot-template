"""Score du registre du bot : score logarithmique (règle de Metaculus) des bras A, B et C sur les questions résolues.

    python score_registre.py --metaculus               # récupère les issues sur Metaculus (METACULUS_TOKEN)
    python score_registre.py --metaculus --enregistrer # et les garde : registre/issues.jsonl, registre/score.json
    python score_registre.py --resolutions issues.json # {"<question_id>": 0 ou 1, ...}, hors ligne

0.2.1 : la base, pour Metaculus, est le score logarithmique (scores de pair = différences de scores log). Le gain de C
sur B se lit comme un score de pair entre bras : 100 × moyenne(ln p_C − ln p_B) sur l'issue réelle ; positif = C
meilleur. Le Brier apparié reste calculé : c'est le critère de levée de L7 du skill (validation.md §27), qui ne dépend
pas du règlement de Metaculus ; borné, il dit aussi si un résultat en log tient à une ou deux questions extrêmes.

Le test qui compte est C contre B (l'apport des cartes au taux de base) et C contre A (l'alphabet contre le modèle
seul), sur les mêmes questions : seules les questions où les trois bras existent entrent dans la comparaison appariée.
Chaque ligne est vérifiée (sceau) avant d'être scorée ; une ligne retouchée est écartée et signalée.

0.2.0 (audit) : une QUESTION compte une fois (dernière ligne publiée) ; les passages à blanc et la zone de test sont
exclus par défaut (--inclure-essais pour les compter) ; chaque probabilité est bornée à [0,001 ; 0,999], les bornes
du bot ; une issue introuvable est signalée, jamais avalée en silence.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import os
from pathlib import Path

import alphabet_pipeline as ap

MODES_ESSAI = {"test_questions"}
MIN_RECALIBRATION = 20                   # en dessous, une recalibration n'apprend que du bruit
PLAFOND_ETUDIE = (0.02, 0.98)            # plafonnement de la valeur postée : étudié, PAS appliqué (décision réservée)
RAPPEL_PLAFONNEMENT = 30                 # questions résolues à partir desquelles le score rappelle cette décision
GRILLE_PLAFONDS = (0.01, 0.02, 0.03, 0.05)
ALPHA = 0.05
LAMBDAS = (0.01, 0.02, 0.05, 0.1, 0.2, 0.3, 0.5, 0.7, 0.9)
ECART_TYPE_SUPPOSE = 40.0                 # points de score de pair par question, tant que le registre n'en dit rien


def lignes(registre: Path) -> list[dict]:
    sortie = []
    for brut in (registre / "journal-bot.jsonl").read_text(encoding="utf-8").splitlines():
        if not brut.strip():
            continue
        x = json.loads(brut)
        s = x.pop("sceau", None)
        x["_intacte"] = s == ap.sceau(x)
        sortie.append(x)
    return sortie


def question_metaculus(client, qid: str, url: str):
    """0.2.0 (audit, B2) : une URL de groupe rend une LISTE de sous-questions ; on garde celle dont l'identifiant
    est celui de la ligne. Rend None si aucune ne correspond."""
    q = client.get_question_by_url(url, group_question_mode="unpack_subquestions")
    candidates = q if isinstance(q, list) else [q]
    for c in candidates:
        if str(getattr(c, "id_of_question", None)) == str(qid):
            return c
    return candidates[0] if len(candidates) == 1 else None


def issues_metaculus(ids_urls: list[tuple[str, str]], erreurs: list | None = None) -> dict[str, int]:
    from forecasting_tools import MetaculusClient
    client, out = MetaculusClient(), {}
    erreurs = [] if erreurs is None else erreurs
    for qid, url in ids_urls:
        try:
            q = question_metaculus(client, qid, url)
        except Exception as e:  # signalée, pas avalée
            erreurs.append({"question_id": qid, "url": url, "erreur": f"{type(e).__name__}: {e}"[:300]})
            continue
        if q is None:
            erreurs.append({"question_id": qid, "url": url, "erreur": "aucune sous-question à cet identifiant"})
            continue
        r = (q.resolution_string or "").lower()
        if r in ("yes", "no"):
            out[qid] = 1 if r == "yes" else 0
    return out


def issues_enregistrees(registre: Path) -> dict[str, int]:
    f = registre / "issues.jsonl"
    if not f.is_file():
        return {}
    return {x["question_id"]: int(x["issue"]) for x in map(json.loads, f.read_text(encoding="utf-8").splitlines()) if x}


def enregistrer(registre: Path, nouvelles: dict[str, int], score: dict) -> int:
    """Ajoute les issues nouvelles (jamais de réécriture d'une issue déjà notée) et remplace registre/score.json."""
    from datetime import datetime, timezone
    deja = issues_enregistrees(registre)
    maintenant = datetime.now(timezone.utc).isoformat(timespec="seconds")
    ajout = {k: v for k, v in nouvelles.items() if k not in deja}
    with open(registre / "issues.jsonl", "a", encoding="utf-8", newline="\n") as f:
        for k, v in sorted(ajout.items()):
            f.write(json.dumps({"question_id": k, "issue": v, "constatee_le": maintenant}, sort_keys=True) + "\n")
    (registre / "score.json").write_text(json.dumps(dict(score, calcule_le=maintenant), ensure_ascii=False, indent=2) + "\n",
                                          encoding="utf-8")
    return len(ajout)


def issues_autres(registre: Path, erreurs: list | None = None) -> int:
    """Questions hors alphabet : leur issue brute (texte de Metaculus : yes/no, une valeur, une option…) dans
    registre/issues-autres.jsonl, jamais réécrite. Le score de ces questions reste celui de Metaculus."""
    from datetime import datetime, timezone
    from forecasting_tools import MetaculusClient
    f = registre / "journal-autres.jsonl"
    if not f.is_file():
        return 0
    sortie = registre / "issues-autres.jsonl"
    deja = {json.loads(x)["question_id"] for x in sortie.read_text(encoding="utf-8").splitlines() if x.strip()} \
        if sortie.is_file() else set()
    client, n = MetaculusClient(), 0
    erreurs = [] if erreurs is None else erreurs
    maintenant = datetime.now(timezone.utc).isoformat(timespec="seconds")
    vus = set()
    for x in map(json.loads, f.read_text(encoding="utf-8").splitlines()):
        qid = x["question_id"]
        if qid in deja or qid in vus:
            continue
        vus.add(qid)
        try:
            q = question_metaculus(client, qid, x["url"])
        except Exception as e:
            erreurs.append({"question_id": qid, "url": x["url"], "erreur": f"{type(e).__name__}: {e}"[:300]})
            continue
        r = q.resolution_string if q is not None else None
        if r:
            with open(sortie, "a", encoding="utf-8", newline="\n") as g:
                g.write(json.dumps({"question_id": qid, "type": x["type"], "issue": r, "constatee_le": maintenant},
                                   ensure_ascii=False, sort_keys=True) + "\n")
            n += 1
    return n


def brier(p: float, y: int) -> float:
    return (p - y) ** 2


def log_score(p: float, y: int) -> float:
    """Perte logarithmique (plus bas = mieux), en logarithme naturel, comme les scores de pair de Metaculus."""
    p = ap.borner(p)
    return -math.log(p if y == 1 else 1 - p)


def score_reference(p: float, y: int) -> float:
    """Score de référence (« baseline ») de Metaculus pour une question binaire : 100 × (log2 p + 1) ; 0 = pile ou face,
    100 = certitude juste. Plus haut = mieux."""
    p = ap.borner(p)
    return 100 * (math.log2(p if y == 1 else 1 - p) + 1)


def gain_pair(p_x: float, p_ref: float, y: int) -> float:
    """Écart de type « score de pair » entre deux bras sur une question : 100 × (ln p_x − ln p_ref) sur l'issue
    réelle. Positif = x meilleur que ref."""
    return 100 * (log_score(p_ref, y) - log_score(p_x, y))


def borne_gain() -> float:
    """Écart maximal possible entre deux bras sur une question, en points : les probabilités sont bornées."""
    return 100 * math.log(ap.BORNE_HAUTE / ap.BORNE_BASSE)


def e_valeur(gains: list[float]) -> float:
    """0.4.0 : test séquentiel valide à tout instant d'arrêt (pari, mélange de mises) de H0 « le bras ne fait pas
    mieux, en moyenne, que sa référence ». Les écarts sont bornés, donc ∏(1 + λ·d/M) est une surmartingale sous H0 ;
    la moyenne sur une grille de λ fixée d'avance l'est aussi. Rejet au niveau α quand e ≥ 1/α, quel que soit le moment
    où l'on regarde : on peut consulter le score chaque semaine sans tricher."""
    m = borne_gain()
    richesses = []
    for lam in LAMBDAS:
        k = 1.0
        for d in gains:
            k *= 1 + lam * max(-1.0, min(1.0, d / m))
        richesses.append(k)
    return sum(richesses) / len(richesses)


def puissance_a_priori(gains: list[float]) -> dict:
    """Questions appariées nécessaires pour détecter un gain moyen donné (test unilatéral α = 5 %, puissance 80 %),
    avec l'écart-type observé si le registre en a assez, sinon une hypothèse déclarée. Ordre de grandeur seulement :
    le test séquentiel, plus prudent, en demande davantage."""
    if len(gains) >= 5:
        moy = sum(gains) / len(gains)
        sigma, origine = math.sqrt(sum((g - moy) ** 2 for g in gains) / (len(gains) - 1)), "observé"
    else:
        sigma, origine = ECART_TYPE_SUPPOSE, "supposé (moins de 5 questions appariées)"
    return {"ecart_type": sigma, "origine": origine,
            "questions_necessaires": {f"{d} points": math.ceil(((1.645 + 0.842) * sigma / d) ** 2) for d in (5, 10, 20)}}


def comparer(apparies: list, x: str, ref: str) -> dict:
    g = [gain_pair(p[x], p[ref], y) for p, y in apparies]
    d_brier = [brier(p[x], y) - brier(p[ref], y) for p, y in apparies]
    total = sum(g)
    pire = min(g)
    return {"gain_log_moyen": total / len(g),            # LA mesure (unités de score de pair Metaculus)
            "questions_gagnees": sum(v > 0 for v in g), "questions_perdues": sum(v < 0 for v in g),
            "test_sequentiel": {"e_mieux": e_valeur(g), "e_moins_bien": e_valeur([-v for v in g]),
                                "seuil": 1 / ALPHA,
                                "lecture": f"e ≥ {1 / ALPHA:g} : écart établi au niveau {ALPHA:g}, valide à tout moment "
                                           "de consultation ; en dessous, rien n'est établi dans un sens ni dans l'autre"},
            "puissance": puissance_a_priori(g),
            "fragilite": {"pire_question": pire,
                          "gain_sans_pire_question": (total - pire) / (len(g) - 1) if len(g) > 1 else None,
                          "lecture": "diagnostic d'influence, pas un test"},
            "brier_critere_L7": {"ecart_moyen": sum(d_brier) / len(d_brier),   # négatif = x meilleur (§27)
                               "accord_avec_log": (total > 0) == (sum(d_brier) < 0)}}


def _logit(p: float) -> float:
    p = ap.borner(p)
    return math.log(p / (1 - p))


def _sigmoide(z: float) -> float:
    return 1 / (1 + math.exp(-z)) if z >= 0 else math.exp(z) / (1 + math.exp(z))


def ajuster_recalibration(paires: list[tuple[float, int]], rappel: float = 1.0) -> tuple[float, float]:
    """Recalibration logistique p' = σ(a·logit p + b), par Newton, avec un rappel vers l'identité (a = 1, b = 0) :
    deux paramètres seulement, et sur peu de questions on reste près de « ne rien changer »."""
    a, b = 1.0, 0.0
    for _ in range(50):
        ga, gb = rappel * (a - 1), rappel * b
        haa, hab, hbb = rappel, 0.0, rappel
        for p, y in paires:
            x = _logit(p)
            q = _sigmoide(a * x + b)
            ga += (q - y) * x
            gb += q - y
            w = q * (1 - q)
            haa += w * x * x
            hab += w * x
            hbb += w
        det = haa * hbb - hab * hab
        if det <= 1e-12:
            break
        da, db = (hbb * ga - hab * gb) / det, (haa * gb - hab * ga) / det
        a, b = a - da, b - db
        if abs(da) + abs(db) < 1e-9:
            break
    return a, b


def recalibration(paires: list[tuple[float, int]]) -> dict | None:
    """Ce que gagnerait une recalibration logistique, mesuré HORS échantillon (on ajuste sans la question, on la
    prévoit, pour chaque question). Rapport seulement : rien n'est appliqué aux prévisions."""
    if len(paires) < MIN_RECALIBRATION:
        return None
    a, b = ajuster_recalibration(paires)
    gains = []
    for i, (p, y) in enumerate(paires):
        ai, bi = ajuster_recalibration(paires[:i] + paires[i + 1:])
        gains.append(gain_pair(_sigmoide(ai * _logit(p) + bi), p, y))
    return {"n": len(paires), "a": a, "b": b, "gain_hors_echantillon": sum(gains) / len(gains),
            "lecture": "a < 1 : prévisions trop tranchées ; a > 1 : trop timides ; b ≠ 0 : biais vers OUI ou NON. "
                       "Le gain hors échantillon (points de score de pair) dit si la correction vaudrait d'être "
                       "appliquée."}


def _effet_plafond(resolues: list[dict], issues: dict, bas: float, haut: float) -> tuple[list[float], int]:
    gains, touchees = [], 0
    for x in resolues:
        p = x.get("p_poste")
        if p is None:
            continue
        y = issues[x["question_id"]]
        pc = min(max(p, bas), haut)
        touchees += pc != p
        gains.append(gain_pair(pc, p, y))
    return gains, touchees


def plafonnement_etudie(resolues: list[dict], issues: dict) -> dict | None:
    """Ce qu'aurait changé un plafonnement de la valeur POSTÉE (étude, pas application), pour le plafond de référence
    et pour une grille de plafonds (0.4.0) : la décision devient un choix chiffré sur le registre."""
    gains, touchees = _effet_plafond(resolues, issues, *PLAFOND_ETUDIE)
    if not gains:
        return None
    grille = {}
    for b in GRILLE_PLAFONDS:
        g, k = _effet_plafond(resolues, issues, b, 1 - b)
        grille[f"{b:g}–{1 - b:g}"] = {"gain_moyen": sum(g) / len(g), "questions_touchees": k}
    return {"bornes": list(PLAFOND_ETUDIE), "n": len(gains), "questions_touchees": touchees,
            "gain_moyen": sum(gains) / len(gains), "grille": grille,
            "lecture": "positif = le plafonnement aurait amélioré le score posté. Étude seulement : la décision de "
                       "plafonner est réservée à Othman."}


def stabilite_strate(tout: list[dict]) -> dict:
    """0.4.0 : la strate de l'événement est posée par le modèle et commande le droit de chiffrer (L7). Sur les
    questions passées plusieurs fois (essais compris), part des passages qui reprennent la strate du premier."""
    par_q = {}
    for x in tout:
        ev = x["bras"]["C"].get("evenement")
        m = re.search(r"@(\d+)", ev) if isinstance(ev, str) else None
        if m:
            par_q.setdefault(x["question_id"], []).append(int(m.group(1)))
    repetees = {q: s for q, s in par_q.items() if len(s) > 1}
    paires = [(s[0], v) for s in repetees.values() for v in s[1:]]
    return {"questions_repetees": len(repetees),
            "accord": (sum(a == b for a, b in paires) / len(paires)) if paires else None,
            "strates_par_question": repetees,
            "lecture": "accord bas : l'étiquette de strate, donc le droit de chiffrer, dépend du tirage"}


def est_essai(x: dict) -> bool:
    """Passage à blanc (publie=False) ou zone de test. Les lignes antérieures à 0.2.0 n'ont pas ces champs :
    elles comptent (le registre d'avant 0.2.0 ne contient que des passages publiés)."""
    return x.get("publie") is False or x.get("mode") in MODES_ESSAI


def une_par_question(tout: list[dict]) -> list[dict]:
    """0.2.0 (audit, B4) : la dernière ligne intacte de chaque question (ordre du journal = ordre chronologique)."""
    derniere = {}
    for x in tout:
        derniere[x["question_id"]] = x
    return list(derniere.values())


def scorer(registre: Path, issues: dict[str, int], inclure_essais: bool = False) -> dict:
    tout = lignes(registre)
    retouchees = [x["question_id"] for x in tout if not x["_intacte"]]
    retenues = [x for x in tout if x["_intacte"] and (inclure_essais or not est_essai(x))]
    questions = une_par_question(retenues)
    resolues = [x for x in questions if x["question_id"] in issues]
    par_bras = {b: [] for b in "ABC"}
    apparies = []
    for x in resolues:
        y = issues[x["question_id"]]
        p = {"A": x["bras"]["A"].get("p"), "B": x["bras"]["B"].get("p"), "C": x["bras"]["C"].get("p_C")}
        p = {b: (ap.borner(v) if v is not None else None) for b, v in p.items()}
        for b, v in p.items():
            if v is not None:
                par_bras[b].append((v, y))
        if all(v is not None for v in p.values()):
            apparies.append((p, y))

    def resume(paires):
        if not paires:
            return None
        n = len(paires)
        return {"n": n, "log": sum(log_score(p, y) for p, y in paires) / n,
                "score_reference_metaculus": sum(score_reference(p, y) for p, y in paires) / n,
                "brier": sum(brier(p, y) for p, y in paires) / n}

    comp = None
    if apparies:
        comp = {"n": len(apparies), "C_sur_B": comparer(apparies, "C", "B"), "C_sur_A": comparer(apparies, "C", "A"),
                "lecture": "gain_log_moyen positif = C meilleur, en points de score de pair Metaculus "
                           "(100 × écart de ln p). Si gain_sans_pire_question change de signe, le résultat tient à une "
                           "seule question. brier_critere_L7 : le critère du skill (§27, C − B ≤ 0) ; s'il contredit le "
                           "log, regarder les questions extrêmes. Sur moins de quelques dizaines de questions, aucune "
                           "conclusion."}
    # 0.2.2 : l'état nul n'est PAS compté comme C = B. Il est suivi à part, par nature : le taux de base tient-il quand
    # l'alphabet dit « pas de structure » sur pièces, et quand il le dit par angle mort ?
    etats_nuls = {}
    for x in resolues:
        cx = x["bras"]["C"]
        if cx.get("statut") != "etat_nul" or x["bras"]["B"].get("p") is None:
            continue
        nat = cx.get("nature_etat_nul") or "non_renseignee"
        etats_nuls.setdefault(nat, []).append((ap.borner(x["bras"]["B"]["p"]), issues[x["question_id"]],
                                               x["bras"]["A"].get("p")))
    suivi_nuls = {nat: {"n": len(v), "log_B": sum(log_score(p, y) for p, y, _ in v) / len(v),
                        "gain_B_sur_A": (sum(gain_pair(p, a, y) for p, y, a in v if a is not None)
                                         / max(1, sum(a is not None for _, _, a in v)))}
                  for nat, v in etats_nuls.items()}
    statuts, motifs = {}, {}
    for x in questions:
        s = x["bras"]["C"].get("statut")
        statuts[s] = statuts.get(s, 0) + 1
        for cat in (x["bras"]["C"].get("rejets_classes") or {}).values():
            motifs[cat] = motifs.get(cat, 0) + 1
    return {"lignes": len(tout), "lignes_essai_exclues": 0 if inclure_essais else sum(est_essai(x) for x in tout),
            "questions": len(questions), "resolues": len(resolues), "retouchees": retouchees,
            "bras": {b: resume(v) for b, v in par_bras.items()}, "apparie_ABC": comp,
            "recalibration_etudiee": {b: recalibration(v) for b, v in par_bras.items()},
            "plafonnement_etudie": plafonnement_etudie(resolues, issues),
            "stabilite_strate": stabilite_strate(tout),
            **({"rappel": f"{len(resolues)} questions résolues : décider du plafonnement de la valeur postée "
                          f"(voir plafonnement_etudie et README-alphabet.md, « Décisions en attente »)."}
               if len(resolues) >= RAPPEL_PLAFONNEMENT else {}),
            "statuts_alphabet": statuts,
            "etats_nuls": {"par_nature": suivi_nuls,
                           "lecture": "structure_absente = candidates écartées sur pièces ; angle_mort = au moins une "
                                      "candidate non vraiment cherchée, même après relance. gain_B_sur_A positif : le "
                                      "« pas de structure » de l'alphabet a mieux valu que le modèle seul."},
            "motifs_rejet": {"compte": motifs,
                             "lecture": "aucun_fait = recherche ; marqueur_non_rempli = marqueur ou vraie absence ; "
                                        "contredit = vraie absence de structure (seul motif qui renseigne sur l'alphabet)"},
            "bras_poste": {b: sum(x["bras_poste"] == b for x in questions) for b in "ABC"}}


if __name__ == "__main__":
    a = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    g = a.add_mutually_exclusive_group(required=True)
    g.add_argument("--metaculus", action="store_true")
    g.add_argument("--resolutions")
    a.add_argument("--registre", default=os.environ.get("ALPHABET_REGISTRE", str(ap.REGISTRE)))
    a.add_argument("--enregistrer", action="store_true", help="garder les issues et le score dans le registre")
    a.add_argument("--inclure-essais", action="store_true", help="compter aussi passages à blanc et zone de test")
    args = a.parse_args()
    reg = Path(args.registre)
    connues = issues_enregistrees(reg)
    if args.metaculus:
        a_chercher = {(x["question_id"], x["url"]) for x in lignes(reg) if x["question_id"] not in connues}
        erreurs = []
        iss = dict(connues, **issues_metaculus(sorted(a_chercher), erreurs))
    else:
        iss = dict(connues, **{str(k): int(v) for k, v in json.loads(Path(args.resolutions).read_text(encoding="utf-8")).items()})
    s = scorer(reg, iss, args.inclure_essais)
    if args.enregistrer:
        s["issues_ajoutees"] = enregistrer(reg, iss, s)
        if args.metaculus:
            s["issues_autres_ajoutees"] = issues_autres(reg, erreurs)
    if args.metaculus:
        s["issues_introuvables"] = erreurs
    print(json.dumps(s, ensure_ascii=False, indent=2))
