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
        x["_dossier"] = etat_dossier(registre, x)
        sortie.append(x)
    return sortie


def etat_dossier(registre: Path, x: dict) -> str | None:
    """0.8.0 (audit B-02) : le sceau du dossier est RELU. None = pas de dossier ; « conforme » ; « different » (le
    fichier ne correspond plus au sceau de la ligne : écrasé ou modifié) ; « absent » (fichier disparu)."""
    if not x.get("dossier_fichier"):
        return None
    f = registre / x["dossier_fichier"]
    if not f.is_file():
        return "absent"
    try:
        return "conforme" if ap.sceau(json.loads(f.read_text(encoding="utf-8"))) == x.get("dossier_sha256") else "different"
    except ValueError:
        return "different"


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
    registre = ap.registre_ecrivable(registre)
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
    sortie = ap.registre_ecrivable(registre) / "issues-autres.jsonl"
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
    """Écart maximal possible entre deux bras quelconques sur une question, en points : les probabilités sont bornées."""
    return 100 * math.log(ap.BORNE_HAUTE / ap.BORNE_BASSE)


def borne_gain_C_B() -> float:
    """0.4.1 : écart maximal entre C et B. Le moteur plafonne le produit des multiplicateurs à plafond_LR (10) et rend
    « non estimé » tout a priori dont la cote s'écarte de plus de ce facteur de celle du taux de base déclaré : la cote
    de C reste dans un facteur 10 de celle de B, donc |ln p_C − ln p_B| ≤ ln 10 sur chaque issue (≈ 230 points). Borne
    structurelle du skill gelé ; le score vérifie qu'elle tient (borne_depassee), sinon il retombe sur la borne générale."""
    try:
        r = float(ap._moteur().P["plafond_LR"])
    except Exception:
        r = 10.0
    return 100 * math.log(r)


def _mises_adaptatives(gains: list[float], m: float, plafond: float = 0.9) -> float:
    """Pari à mise prévisible (type aGRAPA, Waudby-Smith et Ramdas) : la mise de chaque question se fixe sur les
    questions PRÉCÉDENTES seulement, ce qui garde la validité ; elle grandit quand l'écart observé est net."""
    k, s1, s2, n = 1.0, 0.0, 0.0, 0
    for d in gains:
        x = max(-1.0, min(1.0, d / m))
        moy = s1 / n if n else 0.0
        var = (s2 / n - moy * moy) if n else 0.25
        lam = max(0.0, min(plafond, moy / (var + moy * moy))) if n and (var + moy * moy) > 0 else 0.0
        k *= 1 + lam * x
        s1, s2, n = s1 + x, s2 + x * x, n + 1
    return k


def e_valeur(gains: list[float], m: float | None = None) -> float:
    """Test séquentiel valide à tout instant d'arrêt de H0 « le bras ne fait pas mieux, en moyenne, que sa
    référence ». Les écarts sont bornés par m, donc chaque ∏(1 + λₜ·d/m) à mise prévisible est une surmartingale sous
    H0, et leur moyenne aussi. Rejet au niveau α quand e ≥ 1/α, quel que soit le moment où l'on regarde.
    0.4.1 : moyenne à parts égales d'une grille de mises fixes (0.4.0) et d'une mise adaptative, plus puissante."""
    m = m or borne_gain()
    grille = []
    for lam in LAMBDAS:
        k = 1.0
        for d in gains:
            k *= 1 + lam * max(-1.0, min(1.0, d / m))
        grille.append(k)
    return 0.5 * sum(grille) / len(grille) + 0.5 * _mises_adaptatives(gains, m)


def intervalle_sequentiel(gains: list[float], m: float, alpha: float = ALPHA) -> tuple[float, float] | None:
    """0.5.1 : séquence de confiance (valide à tout moment de consultation) sur le gain MOYEN, par inversion du test
    par pari : μ est gardé tant qu'aucun des deux tests unilatéraux « moyenne ≤ μ » et « moyenne ≥ μ » ne le rejette
    au niveau α/2. Les écarts décalés de μ restent bornés par m + |μ|."""
    if not gains:
        return None

    def e_dessus(mu):   # contre « moyenne ≤ μ »
        return e_valeur([d - mu for d in gains], m + abs(mu))

    def e_dessous(mu):  # contre « moyenne ≥ μ »
        return e_valeur([mu - d for d in gains], m + abs(mu))
    seuil = 2 / alpha
    bas, haut = -m, m
    for _ in range(40):                       # plus petit μ non rejeté par le test « ≤ μ » (e décroît avec μ)
        mil = (bas + haut) / 2
        bas, haut = (mil, haut) if e_dessus(mil) >= seuil else (bas, mil)
    borne_basse = haut
    bas, haut = -m, m
    for _ in range(40):                       # plus grand μ non rejeté par le test « ≥ μ » (e croît avec μ)
        mil = (bas + haut) / 2
        bas, haut = (bas, mil) if e_dessous(mil) >= seuil else (mil, haut)
    return borne_basse, bas


def _questions_sequentiel(delta: float, sigma: float, m: float, essais: int = 60, n_max: int = 1500,
                          graine: int = 7) -> int | None:
    """Questions nécessaires pour que le test séquentiel conclue dans 80 % des cas, par simulation (écarts normaux
    d'écart-type sigma, tronqués à ±m). None si au-delà de n_max."""
    import random
    rnd = random.Random(graine)
    temps = []
    for _ in range(essais):
        g, atteint = [], None
        for n in range(1, n_max + 1):
            g.append(max(-m, min(m, rnd.gauss(delta, sigma))))
            if n % 10 == 0 and e_valeur(g, m) >= 1 / ALPHA:
                atteint = n
                break
        temps.append(atteint or n_max + 1)
    temps.sort()
    q80 = temps[int(0.8 * len(temps)) - 1]
    return None if q80 > n_max else q80


def puissance_a_priori(gains: list[float], m: float | None = None, simuler: bool = True) -> dict:
    """Questions appariées nécessaires pour détecter un gain moyen de 5, 10 ou 20 points (α = 5 %, puissance 80 %),
    avec l'écart-type observé (dès 5 questions) ou supposé. 0.4.1 : deux colonnes, car elles diffèrent d'un facteur
    allant jusqu'à 10 : le test classique à effectif fixé (à ne lire qu'une fois, à la fin) et le test séquentiel
    réellement utilisé (lisible chaque semaine), estimé par simulation."""
    m = m or borne_gain()
    if len(gains) >= 5:
        moy = sum(gains) / len(gains)
        sigma, origine = math.sqrt(sum((g - moy) ** 2 for g in gains) / (len(gains) - 1)), "observé"
    else:
        sigma, origine = ECART_TYPE_SUPPOSE, "supposé (moins de 5 questions appariées)"
    sortie = {"ecart_type": sigma, "origine": origine, "borne": m,
              "test_classique": {f"{d} points": math.ceil(((1.645 + 0.842) * sigma / d) ** 2) for d in (5, 10, 20)}}
    if simuler:
        sortie["test_sequentiel"] = {f"{d} points": (_questions_sequentiel(d, sigma, m) or "> 1500") for d in (5, 10, 20)}
    sortie["lecture"] = ("le test séquentiel est celui que le score applique ; le test classique n'est valide que si "
                         "l'on fixe le nombre de questions d'avance et qu'on ne regarde qu'une fois")
    return sortie


def biais_C(apparies: list) -> dict | None:
    """0.4.2 : le sens unique de C. Avec des multiplicateurs tous ≥ 1 (décision d'auteur 9 du skill), C ne peut que
    monter au-dessus de B : il gagne sur les OUI et perd sur les NON. Mesure : déplacement moyen de C par rapport à B
    (en logit), gain de C sur B séparé selon l'issue, et taux de OUI observé contre la moyenne de B et de C. Si C est
    au-dessus du taux de OUI réel alors que B y est, le biais est établi et c'est la décision 9 qu'il faut rouvrir."""
    if not apparies:
        return None
    deplacement = [_logit(p["C"]) - _logit(p["B"]) for p, _ in apparies]
    oui = [gain_pair(p["C"], p["B"], y) for p, y in apparies if y == 1]
    non = [gain_pair(p["C"], p["B"], y) for p, y in apparies if y == 0]
    n = len(apparies)
    return {"n": n, "deplacement_logit_moyen": sum(deplacement) / n,
            "part_C_au_dessus_de_B": sum(d > 1e-9 for d in deplacement) / n,
            "gain_sur_les_OUI": {"n": len(oui), "moyen": sum(oui) / len(oui) if oui else None},
            "gain_sur_les_NON": {"n": len(non), "moyen": sum(non) / len(non) if non else None},
            "taux_de_OUI": sum(y for _, y in apparies) / n,
            "B_moyen": sum(p["B"] for p, _ in apparies) / n, "C_moyen": sum(p["C"] for p, _ in apparies) / n,
            "lecture": "C_moyen au-dessus du taux de OUI quand B_moyen en est proche : C surestime (biais à la hausse)"}


def comparer(apparies: list, x: str, ref: str, borne: float | None = None, principal: bool = False) -> dict:
    g = [gain_pair(p[x], p[ref], y) for p, y in apparies]
    d_brier = [brier(p[x], y) - brier(p[ref], y) for p, y in apparies]
    total = sum(g)
    pire = min(g)
    m = borne or borne_gain()
    depassee = any(abs(v) > m + 1e-9 for v in g)
    if depassee:  # la borne structurelle ne tient pas : on retombe sur la borne générale, toujours vraie
        m = borne_gain()
    # 0.5.1 : plusieurs comparaisons sur les mêmes questions. Seule l'hypothèse pré-enregistrée (C fait mieux que
    # B) est testée au niveau α ; les trois autres (C moins bien que B, C contre A dans les deux sens) au niveau α/3.
    e_mieux, e_moins = e_valeur(g, m), e_valeur([-v for v in g], m)
    s_mieux, s_moins = (1 / ALPHA, 3 / ALPHA) if principal else (3 / ALPHA, 3 / ALPHA)
    cs = intervalle_sequentiel(g, m)
    verdict = ("meilleur (établi)" if e_mieux >= s_mieux else "moins bon (établi)" if e_moins >= s_moins
               else "indéterminé")
    return {"gain_log_moyen": total / len(g),            # LA mesure (unités de score de pair Metaculus)
            "questions_gagnees": sum(v > 0 for v in g), "questions_perdues": sum(v < 0 for v in g),
            "verdict": f"{x} {verdict} par rapport à {ref}",
            "intervalle_sequentiel_95": cs,
            "test_sequentiel": {"e_mieux": e_mieux, "e_moins_bien": e_moins,
                                "seuil_mieux": s_mieux, "seuil_moins_bien": s_moins,
                                "hypothese_principale": principal, "borne": m, "borne_depassee": depassee,
                                "lecture": f"e ≥ {1 / ALPHA:g} : écart établi au niveau {ALPHA:g}, valide à tout moment "
                                           "de consultation ; en dessous, rien n'est établi dans un sens ni dans l'autre"},
            "puissance": puissance_a_priori(g, m),
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


def invariance_lecteur(lignes: list[dict]) -> dict | None:
    """0.10.11 (§39) : accord du lecteur avec lui-même sur deux vues aux sources disjointes. Jaccard moyen des cartes
    ancrées, part des questions où les deux vues ancrent exactement les mêmes cartes, et κ de Cohen sur les décisions
    « ancrée / non ancrée » de toutes les candidates. Descriptif ; ne dépend d'aucune issue."""
    tests = [x for x in lignes if x.get("statut") == "teste"]
    if not tests:
        return None
    paires = [(c["A"], c["B"]) for t in tests for c in t.get("candidates") or []]
    n = len(paires)
    kappa = None
    if n:
        po = sum(a == b for a, b in paires) / n
        pa, pb = sum(a for a, _ in paires) / n, sum(b for _, b in paires) / n
        pe = pa * pb + (1 - pa) * (1 - pb)
        kappa = None if pe == 1 else (po - pe) / (1 - pe)
    fam = [t["accord_famille"] for t in tests if isinstance(t.get("accord_famille"), (int, float))]
    return {"questions": len(tests), "jaccard_moyen": round(sum(t["jaccard"] for t in tests) / len(tests), 4),
            "accord_famille_moyen": round(sum(fam) / len(fam), 4) if fam else None,   # 0.10.13 (§42)
            "part_identiques": round(sum(set(t["ancrees_A"]) == set(t["ancrees_B"]) for t in tests) / len(tests), 4),
            "kappa_candidates": None if kappa is None else round(kappa, 4), "decisions": n,
            "lecture": "κ faible : le lecteur suit le registre des sources plus que la situation (§39)"}


ETAPES_ILLISIBLES = (("plan corrigé illisible", "plan_corrige"), ("plan illisible", "plan"),
                     ("lecture illisible", "lecture"), ("correction illisible", "correction"))


def sorties_illisibles(lignes: list[dict]) -> dict | None:
    """0.10.14 (d'après LLMMatrix, Prokopets 2026) : part des sorties de modèle illisibles (JSON non extrait), par
    modèle principal et par étape (plan, lecture, correction du dossier, critique, test d'invariance). Une lecture
    illisible n'est ni un état nul ni une erreur du moteur : c'est un échec de format, compté à part. Descriptif."""
    if not lignes:
        return None
    par: dict[str, dict] = {}
    for x in lignes:
        c = ((x.get("bras") or {}).get("C")) or {}
        d = par.setdefault(modele_principal(x), {"lignes": 0, "illisibles": 0, "etapes": {}})
        d["lignes"] += 1
        textes = f"{c.get('motif') or ''} || {c.get('derniere_erreur') or ''}"
        etapes = [e for motif, e in ETAPES_ILLISIBLES if motif in textes]
        if "plan_corrige" in etapes and "plan" in etapes:
            etapes.remove("plan")
        if (c.get("critique") or {}).get("statut") == "illisible":
            etapes.append("critique")
        inv = c.get("invariance") or {}
        if inv.get("statut") == "erreur" and "JSON" in str(inv.get("motif") or "").upper():
            etapes.append("invariance")
        for e in etapes:
            d["etapes"][e] = d["etapes"].get(e, 0) + 1
        d["illisibles"] += bool(etapes)
    for d in par.values():
        d["part"] = round(d["illisibles"] / d["lignes"], 4)
    tot = sum(d["lignes"] for d in par.values())
    ill = sum(d["illisibles"] for d in par.values())
    return {"lignes": tot, "illisibles": ill, "part": round(ill / tot, 4), "par_modele": par,
            "lecture": "part élevée : le modèle échoue au format ; ces lignes n'ont pas de lecture, ce n'est pas un état nul"}


def preselection_ombre(lignes: list[dict]) -> dict | None:
    """0.10.15 : recouvrement entre les k cartes que le plongement multilingue range en tête et les cartes retenues
    par le planificateur ; rang moyen de la carte de l'événement. Descriptif, sans issue."""
    p = [((x.get("bras") or {}).get("C") or {}).get("preselection") for x in lignes]
    p = [y for y in p if isinstance(y, dict)]
    if not p:
        return None
    ok = [y for y in p if y.get("statut") == "calcule" and y.get("recouvrement") is not None]
    moy = lambda v: round(sum(v) / len(v), 4) if v else None
    rangs = [y["rang_evenement"] for y in ok if isinstance(y.get("rang_evenement"), int)]
    return {"questions": len(p), "calculees": len(ok), "indisponibles": len(p) - len(ok),
            "recouvrement_moyen": moy([y["recouvrement"] for y in ok]),
            "jaccard_moyen": moy([y["jaccard"] for y in ok]),
            "rang_moyen_evenement": moy(rangs),
            "modeles": sorted({str(y.get("modele")) for y in p}),
            "lecture": "recouvrement haut et stable : la présélection retrouve le choix du planificateur ; bas : le "
                       "planificateur voit autre chose que le texte de la question"}


def diversite_lectures(lignes: list[dict]) -> dict | None:
    """0.10.12 : surveiller l'« effondrement » du lecteur (l'équivalent d'une JEPA qui rend la même sortie pour tout) :
    part des états nuls, nombre d'états distincts, entropie normalisée des cartes ancrées, part de la carte la plus
    fréquente. Descriptif, sans issue."""
    import math as _m
    c = [((x.get("bras") or {}).get("C") or {}) for x in lignes]
    c = [b for b in c if b.get("statut") in ("estime", "non_estime", "etat_nul", "lu_non_chiffre")]
    if not c:
        return None
    nuls = sum(1 for b in c if b.get("statut") == "etat_nul")
    etats = [str(b.get("etat") or "") for b in c if b.get("etat")]
    cartes: dict[str, int] = {}
    for e in etats:
        for m_ in re.findall(r"([A-ZÀ-Ý ·]+)@\d+", e.split("]", 1)[-1]):
            k = m_.strip()
            cartes[k] = cartes.get(k, 0) + 1
    tot = sum(cartes.values())
    h = -sum(v / tot * _m.log(v / tot) for v in cartes.values()) if tot else 0.0
    return {"lectures": len(c), "part_etats_nuls": round(nuls / len(c), 4), "etats_distincts": len(set(etats)),
            "entropie_normalisee": round(h / _m.log(16), 4) if tot else None,
            "carte_la_plus_frequente": (max(cartes, key=cartes.get) if cartes else None),
            "part_carte_la_plus_frequente": round(max(cartes.values()) / tot, 4) if tot else None,
            "lecture": "entropie basse, états distincts rares ou états nuls quasi constants : le lecteur s'effondre"}


def c_selon_surprise(paires: list[tuple[float, float, int]]) -> dict | None:
    """0.10.12 (§40) : Brier de C selon la surprise relative de la lecture (au-dessus et au-dessous de la médiane).
    Descriptif : une surprise forte devrait annoncer un C moins fiable."""
    if len(paires) < 4:
        return None
    med = sorted(s for s, _, _ in paires)[len(paires) // 2]
    haut = [(p - y) ** 2 for s, p, y in paires if s >= med]
    bas = [(p - y) ** 2 for s, p, y in paires if s < med]
    return {"mediane_surprise": round(med, 4),
            "surprise_forte": {"questions": len(haut), "brier_C": round(sum(haut) / len(haut), 4) if haut else None},
            "surprise_faible": {"questions": len(bas), "brier_C": round(sum(bas) / len(bas), 4) if bas else None}}


def calibration_queues(paires: list[tuple[float, int]], seuil: float = 0.1) -> dict:
    """0.10.10 : calibration dans les QUEUES (p < 0,1 et p > 0,9). Epoch AI (méthode bayésienne de l'ECI, nov. 2026)
    trouve sa couverture la plus faible près des bornes (80,5 % contre 90 % visés sous 0,05) ; au score logarithmique,
    c'est là qu'une erreur coûte le plus. Descriptif : fréquence observée contre p moyen, et effectif."""
    out = {}
    for nom, garde in (("bas", lambda p: p < seuil), ("haut", lambda p: p > 1 - seuil)):
        q = [(p, y) for p, y in paires if garde(p)]
        out[nom] = ({"n": len(q), "p_moyen": round(sum(p for p, _ in q) / len(q), 4),
                     "frequence_observee": round(sum(y for _, y in q) / len(q), 4)} if q else {"n": 0})
    return out


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
    questions passées plusieurs fois (essais compris), part des passages qui reprennent la strate du premier.
    0.4.1 : comparaison À VERSION ÉGALE seulement (un changement de consigne n'est pas une instabilité) ; la base de
    comparaison repart donc à zéro avec chaque version."""
    par_q = {}
    for x in tout:
        ev = x["bras"]["C"].get("evenement")
        m = re.search(r"@(\d+)", ev) if isinstance(ev, str) else None
        if m:
            par_q.setdefault(f"{x['question_id']} ({x.get('version_bot', '?')})", []).append(int(m.group(1)))
    repetees = {q: s for q, s in par_q.items() if len(s) > 1}
    paires = [(s[0], v) for s in repetees.values() for v in s[1:]]
    return {"questions_repetees": len(repetees),
            "accord": (sum(a == b for a, b in paires) / len(paires)) if paires else None,
            "strates_par_question": repetees,
            "lecture": "accord bas : l'étiquette de strate, donc le droit de chiffrer, dépend du tirage"}


def _compter(valeurs: list) -> dict:
    d: dict = {}
    for v in valeurs:
        d[str(v)] = d.get(str(v), 0) + 1
    return d


def statuts_par_version(tout: list[dict]) -> dict:
    """0.4.1 : statuts de l'alphabet par version du bot, essais compris. Effets attendus après 0.4.0, à vérifier :
    hors_strate devrait monter (strate à l'aveugle) ; si sans_vue monte en même temps que la dispersion de B baisse,
    la classe figée est trop étroite."""
    out = {}
    for x in tout:
        v = x.get("version_bot", "?")
        s = x["bras"]["C"].get("statut")
        d = out.setdefault(v, {"lignes": 0, "statuts": {}, "dispersion_B": [], "classe": {}})
        d["lignes"] += 1
        d["statuts"][s] = d["statuts"].get(s, 0) + 1
        disp = (x["bras"]["B"].get("vues") or {}).get("dispersion")
        if disp is not None:
            d["dispersion_B"].append(disp)
        att = x["bras"]["C"].get("attribution") or {}
        d["mots_ancres"] = d.get("mots_ancres", 0) + (att.get("mots") or 0)
        d["mots_non_attribues"] = d.get("mots_non_attribues", 0) + (att.get("non_attribues") or 0)
        cs = x["bras"]["B"].get("classe_statut")
        if cs:
            d["classe"][cs] = d["classe"].get(cs, 0) + 1
    for d in out.values():
        disp = d.pop("dispersion_B")
        d["dispersion_B_moyenne"] = sum(disp) / len(disp) if disp else None
    return out


MIN_CORRECTION = 15   # tests rétrospectifs (C chiffré) avant d'écrire une correction


def ajuster_decalage(paires: list[tuple[float, int]], rappel: float = 1.0) -> float:
    """Décalage seul, b dans logit p' = logit p + b (pente fixée à 1) : la correction d'un biais global de niveau,
    et rien d'autre. Newton à une dimension, rappel vers b = 0."""
    b = 0.0
    for _ in range(50):
        g, h = rappel * b, rappel
        for p, y in paires:
            q = _sigmoide(_logit(p) + b)
            g += q - y
            h += q * (1 - q)
        pas = g / h
        b -= pas
        if abs(pas) < 1e-10:
            break
    return b


def lignes_retro(registre: Path) -> list[dict]:
    f = registre / "retro.jsonl"
    if not f.is_file():
        return []
    sortie = []
    for brut in f.read_text(encoding="utf-8").splitlines():
        if brut.strip():
            x = json.loads(brut)
            s = x.pop("sceau", None)
            x["_intacte"] = s == ap.sceau(x)
            sortie.append(x)
    return sortie


def scorer_explo_autres(registre: Path) -> dict | None:
    """0.9.1 (décision d'auteur) : les questions non binaires lues en exploratoire, via leur question binaire dérivée.
    À PART de tout verdict : C exploratoire contre B et contre A (la probabilité que A donnait au même seuil)."""
    f, fi = registre / "journal-autres.jsonl", registre / "issues-autres.jsonl"
    if not f.is_file():
        return None
    issues = {}
    if fi.is_file():
        for x in map(json.loads, filter(str.strip, fi.read_text(encoding="utf-8").splitlines())):
            issues[x["question_id"]] = x["issue"]
    derniere = {}
    for x in map(json.loads, filter(str.strip, f.read_text(encoding="utf-8").splitlines())):
        s_ = x.pop("sceau", None)
        if s_ == ap.sceau(x) and not est_essai(x) and (x.get("exploratoire") or {}).get("derivee"):
            derniere[x["question_id"]] = x
    statuts, paires_b, paires_a, paires_s = {}, [], [], []
    for qid, x in derniere.items():
        ex = x["exploratoire"]
        statuts[str(ex.get("statut"))] = statuts.get(str(ex.get("statut")), 0) + 1
        y = ap.issue_derivee(ex["derivee"], issues.get(qid)) if qid in issues else None
        if y is None:
            continue
        if isinstance(ex.get("p_C"), (int, float)) and isinstance(ex.get("p_B"), (int, float)):
            paires_b.append(({"C_exploratoire": ap.borner(ex["p_C"]), "B": ap.borner(ex["p_B"])}, y))
        if isinstance(ex.get("p_C"), (int, float)):
            paires_a.append(({"C_exploratoire": ap.borner(ex["p_C"]), "A": ap.borner(ex["derivee"]["p_A"])}, y))
        if isinstance(ex.get("p_C_symetrique"), (int, float)) and isinstance(ex.get("p_B"), (int, float)):
            paires_s.append(({"C_symetrique": ap.borner(ex["p_C_symetrique"]), "B": ap.borner(ex["p_B"])}, y))
    return {"note": "hors verdict ; questions non binaires ramenées à une question binaire dérivée (§29)",
            "questions": len(derniere), "statuts": statuts, "resolues_chiffrees": len(paires_b),
            "C_exploratoire_sur_B": comparer(paires_b, "C_exploratoire", "B", borne_gain_C_B()) if paires_b else None,
            "C_exploratoire_sur_A": comparer(paires_a, "C_exploratoire", "A") if paires_a else None,
            "C_symetrique_sur_B": comparer(paires_s, "C_symetrique", "B", borne_gain_C_B()) if paires_s else None}


def scorer_retro(registre: Path) -> dict:
    """0.5.0 : biais de C mesuré sur les tests rétrospectifs, et décalage qui le corrige (évalué hors échantillon).
    La correction n'est proposée qu'à partir de MIN_CORRECTION questions et si elle gagne hors échantillon."""
    tout = lignes_retro(registre)
    intactes = [x for x in tout if x["_intacte"]]
    statuts = {}
    for x in intactes:
        statuts[x.get("statut")] = statuts.get(x.get("statut"), 0) + 1
    # 0.9.1 : le biais à corriger est celui du MOTEUR, le même en strate 7 et hors strate 7 : les C exploratoires des
    # tests rétrospectifs servent aussi à l'apprendre (comptés à part : n_exploratoires).
    def p_c(x):
        if x.get("p_C") is not None:
            return x["p_C"]
        ex = x.get("exploratoire") or {}
        return ex.get("p_C") if ex.get("statut") == "estime" else None
    chiffres = [x for x in intactes if p_c(x) is not None and x.get("p_B") is not None and x.get("issue") in (0, 1)]
    apparies = [({"C": ap.borner(p_c(x)), "B": ap.borner(x["p_B"])}, x["issue"]) for x in chiffres]
    syms = [({"C_symetrique": ap.borner(x["symetrique"]["p"]), "B": ap.borner(x["p_B"])}, x["issue"])
            for x in intactes if (x.get("symetrique") or {}).get("p") is not None and x.get("p_B") is not None
            and x.get("issue") in (0, 1)]
    paires_c = [(p["C"], y) for p, y in apparies]
    sortie = {"lignes": len(tout), "retouchees": [x["question_id"] for x in tout if not x["_intacte"]],
              "statuts": statuts, "n_chiffres": len(apparies),
              "n_exploratoires": sum(x.get("p_C") is None for x in chiffres), "biais_C": biais_C(apparies),
              "C_symetrique_sur_B": comparer(syms, "C_symetrique", "B", borne_gain_C_B()) if syms else None,
              "C_sur_B": comparer(apparies, "C", "B", borne_gain_C_B()) if apparies else None,
              "correction": None}
    if len(paires_c) >= 2:
        b = ajuster_decalage(paires_c)
        gains = []
        for i, (p, y) in enumerate(paires_c):
            bi = ajuster_decalage(paires_c[:i] + paires_c[i + 1:])
            gains.append(gain_pair(_sigmoide(_logit(p) + bi), p, y))
        hors = sum(gains) / len(gains)
        # 0.8.0 (audit O-06) : « hors > 0 » passe une fois sur deux sous l'absence d'effet. On exige aussi que la borne
        # basse unilatérale à 95 % du gain hors échantillon soit positive.
        et = (sum((g - hors) ** 2 for g in gains) / max(1, len(gains) - 1)) ** 0.5
        basse = hors - 1.645 * et / len(gains) ** 0.5
        sortie["correction"] = {"decalage_logit": b, "n": len(paires_c), "gain_hors_echantillon": hors,
                                "borne_basse_95": basse,
                                "proposee": len(paires_c) >= MIN_CORRECTION and hors > 0 and basse > 0,
                                "lecture": f"b < 0 : C surestime ; proposée à partir de {MIN_CORRECTION} questions et "
                                           "si elle gagne hors échantillon ; elle ne touche que C_corrige, jamais le "
                                           "bras posté"}
    return sortie


def enregistrer_correction(registre: Path, s: dict) -> bool:
    c = s.get("correction")
    if not c or not c["proposee"]:
        return False
    from datetime import datetime, timezone
    registre = ap.registre_ecrivable(registre)
    (registre / "correction-retro.json").write_text(json.dumps(
        {"decalage_logit": c["decalage_logit"], "n": c["n"], "gain_hors_echantillon": c["gain_hors_echantillon"],
         "calcule_le": datetime.now(timezone.utc).isoformat(timespec="seconds")}, indent=2) + "\n", encoding="utf-8")
    return True


def est_essai(x: dict) -> bool:
    """Passage à blanc (publie=False) ou zone de test. Les lignes antérieures à 0.2.0 n'ont pas ces champs :
    elles comptent (le registre d'avant 0.2.0 ne contient que des passages publiés)."""
    return x.get("publie") is False or x.get("mode") in MODES_ESSAI


def une_par_question(tout: list[dict]) -> list[dict]:
    """0.2.0 (audit, B4) : la dernière ligne de chaque question. 0.8.0 (audit Azrivo) : « dernière » selon
    l'horodatage scellé du bras A, pas selon l'ordre du fichier (qu'un rebase git pourrait inverser)."""
    derniere = {}
    for i, x in enumerate(tout):
        cle = ((x.get("bras") or {}).get("A") or {}).get("horodatage") or "", i
        if x["question_id"] not in derniere or cle >= derniere[x["question_id"]][0]:
            derniere[x["question_id"]] = (cle, x)
    return [x for _, x in derniere.values()]


def modele_principal(x: dict) -> str:
    """0.6.0 : le codeur d'une ligne. Les lignes antérieures ne le disent pas."""
    return ((x.get("modeles") or {}).get("principal")) or "non_renseigne (avant 0.6.0)"


def scorer(registre: Path, issues: dict[str, int], inclure_essais: bool = False, modele: str | None = None) -> dict:
    """0.6.0 : `modele` restreint le score aux lignes d'un seul modèle principal : changer de modèle, c'est changer de
    codeur, et deux codeurs ne se mélangent pas dans une même mesure."""
    tout = [x for x in lignes(registre) if modele is None or modele_principal(x) == modele]
    retouchees = [x["question_id"] for x in tout if not x["_intacte"]]
    # 0.8.0 (audit B-02) : une ligne dont le dossier ne correspond plus à son sceau perd sa preuve : hors score.
    dossiers_non_conformes = [{"question_id": x["question_id"], "fichier": x.get("dossier_fichier"),
                               "etat": x["_dossier"]} for x in tout if x["_dossier"] in ("different", "absent")]
    retenues = [x for x in tout if x["_intacte"] and x["_dossier"] not in ("different", "absent")
                and (inclure_essais or not est_essai(x))]
    publiees = [x for x in tout if x["_intacte"] and (inclure_essais or not est_essai(x))]
    questions = une_par_question(retenues)
    resolues = [x for x in questions if x["question_id"] in issues]
    par_bras = {b: [] for b in "ABC"}
    apparies, corriges, critiques, comptes, explos = [], [], [], [], []
    symetriques, explos_corr, mediations = [], [], []
    noisy, arrets = [], {True: [], False: []}   # 0.10.4 (§34), en ombre
    temperes, a_moyens, c_sur_a_moyen = [], [], []   # 0.10.5 (§35), en ombre
    generatifs = []                                   # 0.10.6 (§36), en ombre
    surprises = []                                    # 0.10.12 (§40), en ombre
    lectures_proba = []                               # 0.10.7 (§37), en ombre
    sans_plafond = []                                 # 0.10.9 (§38), en ombre
    for x in resolues:
        y = issues[x["question_id"]]
        cr = x["bras"]["C"].get("critique") or {}
        if cr.get("p_C_critique") is not None and x["bras"]["C"].get("p_C") is not None:   # 0.6.0 : en ombre
            critiques.append(({"C_critique": ap.borner(cr["p_C_critique"]), "C": ap.borner(x["bras"]["C"]["p_C"])}, y))
        bx = x["bras"]["B"]
        ex = x["bras"]["C"].get("exploratoire") or {}
        sy = (x["bras"]["C"].get("symetrique") or {}).get("p")
        if sy is not None and bx.get("p") is not None:      # 0.9.1 : version symétrique, en ombre
            symetriques.append(({"C_symetrique": ap.borner(sy), "B": ap.borner(bx["p"]),
                                 "_canal": "exploratoire" if ex else "strate_7"}, y))
        om = x["bras"]["C"].get("ombre_causale") or ex.get("ombre_causale") or {}   # 0.10.3 (§33), en ombre
        pc_ = x["bras"]["C"].get("p_C") if x["bras"]["C"].get("p_C") is not None else ex.get("p_C")
        if isinstance(om.get("p_mediation"), (int, float)) and isinstance(pc_, (int, float)):
            mediations.append(({"C_mediation": ap.borner(om["p_mediation"]), "C": ap.borner(pc_)}, y))
        if isinstance(om.get("p_noisy_or"), (int, float)) and isinstance(pc_, (int, float)):   # 0.10.4 (§34)
            noisy.append(({"C_noisy_or": ap.borner(om["p_noisy_or"]), "C": ap.borner(pc_)}, y))
        t5 = [t_ for t_ in (om.get("tempere") or []) if t_.get("alpha") == 0.5 and isinstance(t_.get("p"), (int, float))]
        if t5 and isinstance(pc_, (int, float)):   # 0.10.5 (§35) : α = 0,5, fixé d'avance
            temperes.append(({"C_tempere": ap.borner(t5[0]["p"]), "C": ap.borner(pc_)}, y))
        su_ = ((om.get("generatif") or {}).get("surprise") or {}).get("surprise_relative")
        if isinstance(su_, (int, float)) and isinstance(pc_, (int, float)):   # 0.10.12 (§40)
            surprises.append((su_, ap.borner(pc_), y))
        g_ = (om.get("generatif") or {}).get("p")
        if isinstance(g_, (int, float)) and isinstance(pc_, (int, float)):   # 0.10.6 (§36)
            generatifs.append(({"C_generatif": ap.borner(g_), "C": ap.borner(pc_)}, y))
        lp_ = (om.get("lecture_probabiliste") or {}).get("p")
        if isinstance(lp_, (int, float)) and isinstance(pc_, (int, float)):   # 0.10.7 (§37)
            lectures_proba.append(({"C_lecture_probabiliste": ap.borner(lp_), "C": ap.borner(pc_)}, y))
        sp_ = (om.get("sans_plafond") or {}).get("p")
        if isinstance(sp_, (int, float)) and isinstance(pc_, (int, float)):   # 0.10.9 (§38)
            sans_plafond.append(({"C_sans_plafond": ap.borner(sp_), "C": ap.borner(pc_)}, y))
        ea_ = x["bras"]["A"].get("essais") or {}
        if isinstance(ea_.get("moyenne"), (int, float)) and x["bras"]["A"].get("p") is not None:
            a_moyens.append(({"A_moyen": ap.borner(ea_["moyenne"]), "A": ap.borner(x["bras"]["A"]["p"])}, y))
            if isinstance(pc_, (int, float)):
                c_sur_a_moyen.append(({"C": ap.borner(pc_), "A_moyen": ap.borner(ea_["moyenne"])}, y))
        vi_ = om.get("valeur_information") or {}
        if isinstance(vi_.get("arret"), bool) and isinstance(pc_, (int, float)):
            arrets[vi_["arret"]].append(((ap.borner(pc_) - (1 if y else 0)) ** 2))
        if isinstance(ex.get("p_C_corrige"), (int, float)) and bx.get("p") is not None:
            explos_corr.append(({"C_exploratoire_corrige": ap.borner(ex["p_C_corrige"]), "B": ap.borner(bx["p"])}, y))
        if isinstance(ex.get("p_C"), (int, float)) and bx.get("p") is not None:   # 0.9.0 (§29) : à part, par strate
            explos.append(({"C_exploratoire": ap.borner(ex["p_C"]), "B": ap.borner(bx["p"]), "_strate": ex.get("strate")}, y))
        pk = bx.get("p_compte")
        # 0.8.0 (audit M-02, M-03) : le compte se juge contre une mesure qui ne le contient pas : la médiane du modèle
        # (compte exact, devenu B) ou la médiane des vues non ancrées (compte proche).
        if bx.get("correspondance") == "exacte":
            ref = bx.get("p_modele") if bx.get("compte_calcule") else bx.get("p")
        else:
            ref = bx.get("p_sans_ancre") if bx.get("p_sans_ancre") is not None else bx.get("p")
        if pk is not None and ref is not None:
            comptes.append(({"compte": ap.borner(pk), "B": ap.borner(ref), "_corr": bx.get("correspondance")}, y))
        pcc, pb = x["bras"]["C"].get("p_C_corrige"), x["bras"]["B"].get("p")
        if pcc is not None and pb is not None:   # 0.5.0 : C corrigé du biais, scellé, jamais posté
            corriges.append(({"C": ap.borner(pcc), "B": ap.borner(pb)}, y))
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
        comp = {"n": len(apparies), "biais_C": biais_C(apparies),
                "C_sur_B": comparer(apparies, "C", "B", borne_gain_C_B(), principal=True),
                "C_sur_A": comparer(apparies, "C", "A"),
                "C_corrige_sur_B": comparer(corriges, "C", "B") if corriges else None,
                "C_critique_sur_C": comparer(critiques, "C_critique", "C") if critiques else None,
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
    # 0.8.0 (audit M-09) : les diagnostics comptent TOUTES les lignes publiées (pas dédoublonnées) : un refus suivi
    # d'une reprise réussie reste visible. Le dédoublonnage ne sert qu'au score.
    statuts, motifs = {}, {}
    for x in publiees:
        s = x["bras"]["C"].get("statut")
        statuts[s] = statuts.get(s, 0) + 1
        for cat in (x["bras"]["C"].get("rejets_classes") or {}).values():
            motifs[cat] = motifs.get(cat, 0) + 1
    princ = sorted({modele_principal(x) for x in resolues})
    return {"lignes": len(tout), "lignes_essai_exclues": 0 if inclure_essais else sum(est_essai(x) for x in tout),
            "questions": len(questions), "resolues": len(resolues), "retouchees": retouchees,
            "dossiers_non_conformes": dossiers_non_conformes,
            # 0.8.0 (audit m-07, m-08, m-09) : avertissements de lecture.
            "avertissements": {
                "modeles_melanges": (f"{len(princ)} modèles principaux dans ce score : verdict MÉLANGÉ, lire par_modele"
                                     if len(princ) > 1 else None),
                "erreur_familiale_max": "10 % (α = 5 % pour C mieux que B, α/3 pour chacune des trois autres)",
                "unites": "score_reference_metaculus : 100 × (log2 p + 1) ; gain_log_moyen et gain_pair : 100 × écart "
                          "de ln p (points de score de pair). Ne pas comparer les deux."},
            "bras": {b: resume(v) for b, v in par_bras.items()}, "apparie_ABC": comp,
            "recalibration_etudiee": {b: recalibration(v) for b, v in par_bras.items()},
            "calibration_queues": {b: calibration_queues(v) for b, v in par_bras.items()},   # 0.10.10
            "invariance_lecteur": invariance_lecteur([(x["bras"]["C"].get("invariance") or {}) for x in publiees]),
            "diversite_lectures": diversite_lectures(publiees),                 # 0.10.12
            "sorties_illisibles": sorties_illisibles(publiees),                 # 0.10.14
            "preselection_ombre": preselection_ombre(publiees),                 # 0.10.15
            "C_selon_surprise": c_selon_surprise(surprises),                    # 0.10.12 (§40)
            "plafonnement_etudie": plafonnement_etudie(resolues, issues),
            "stabilite_strate": stabilite_strate(publiees),
            "statuts_par_version": statuts_par_version(publiees),
            "effectifs_diagnostics": {"lignes_publiees": len(publiees), "questions_scorees": len(questions)},
            **({"rappel": f"{len(resolues)} questions résolues : décider du plafonnement de la valeur postée "
                          f"(voir plafonnement_etudie et README-alphabet.md, « Décisions en attente »)."}
               if len(resolues) >= RAPPEL_PLAFONNEMENT else {}),
            # 0.9.0 (décision d'auteur, skill validation.md §29) : le bras C exploratoire, hors strate 7, jamais posté.
            # Section À PART : hors verdict principal, hors correction, hors recalibration, hors condition 1 du §27.
            "statuts_exploratoires": _compter([((x["bras"]["C"].get("exploratoire") or {}).get("statut"))
                                               for x in publiees if x["bras"]["C"].get("exploratoire")]),
            "C_exploratoire_sur_B": ({"note": "hors verdict ; lecture hors strate 7, chiffre scellé non posté (§29)",
                                      "n": len(explos),
                                      "tous": comparer(explos, "C_exploratoire", "B", borne_gain_C_B()),
                                      "par_strate": {str(st): dict(n=sum(p_["_strate"] == st for p_, _ in explos),
                                                                   **comparer([(p_, y_) for p_, y_ in explos if p_["_strate"] == st],
                                                                              "C_exploratoire", "B", borne_gain_C_B()))
                                                     for st in sorted({p_["_strate"] for p_, _ in explos}, key=str)}}
                                     if explos else None),
            "exploratoire_non_binaire": scorer_explo_autres(registre),
            "C_symetrique_sur_B": ({"note": "en ombre : candidates contredites comptées CONTRE l'événement (symétrie)",
                                    "n": len(symetriques),
                                    "tous": comparer(symetriques, "C_symetrique", "B", borne_gain_C_B()),
                                    "par_canal": {k: comparer([(p_, y_) for p_, y_ in symetriques if p_["_canal"] == k],
                                                              "C_symetrique", "B", borne_gain_C_B())
                                                  for k in ("strate_7", "exploratoire")
                                                  if any(p_["_canal"] == k for p_, _ in symetriques)}}
                                   if symetriques else None),
            "C_mediation_sur_C": ({"note": "en ombre (§33) : règle des médiateurs contre le calcul actuel, mêmes questions",
                                   **comparer(mediations, "C_mediation", "C")} if mediations else None),
            "C_noisy_or_sur_C": ({"note": "en ombre (§34) : cartes lues comme des causes (noisy-or) contre le produit, mêmes questions",
                                  **comparer(noisy, "C_noisy_or", "C")} if noisy else None),
            "C_tempere_sur_C": ({"note": "en ombre (§35) : produit des λ à la puissance 0,5, fixée d'avance, contre C",
                                 **comparer(temperes, "C_tempere", "C")} if temperes else None),
            "C_generatif_sur_C": ({"note": "en ombre (§36) : programme génératif (lecteur bruité, rejets comme preuves) contre C",
                                   **comparer(generatifs, "C_generatif", "C")} if generatifs else None),
            "C_lecture_probabiliste_sur_C": ({"note": "en ombre (§37) : programme génératif modifié par les instructions "
                                                      "traduites des textes (Wong et al. 2023) contre C",
                                              **comparer(lectures_proba, "C_lecture_probabiliste", "C")}
                                             if lectures_proba else None),
            "C_sans_plafond_sur_C": ({"note": "en ombre (§38) : le même calcul sans troncature du score contre C",
                                      **comparer(sans_plafond, "C_sans_plafond", "C")} if sans_plafond else None),
            "A_moyen_sur_A": ({"note": "en ombre (§35) : moyenne de K essais du modèle seul contre le premier essai",
                               **comparer(a_moyens, "A_moyen", "A")} if a_moyens else None),
            "C_sur_A_moyen": ({"note": "en ombre (§35) : C contre A moyenné, la référence qui retire le bruit d'un tirage",
                               **comparer(c_sur_a_moyen, "C", "A_moyen")} if c_sur_a_moyen else None),
            "C_selon_arret_vdi": ({"note": "en ombre (§34) : Brier de C selon que la borne de valeur de l'information "
                                           "était sous le seuil (arret) ou non ; descriptif, pas un test",
                                   **{("arret" if k else "non_arret"): {"questions": len(v), "brier_C": sum(v) / len(v)}
                                      for k, v in arrets.items() if v}} if arrets[True] or arrets[False] else None),
            "C_exploratoire_corrige_sur_B": (comparer(explos_corr, "C_exploratoire_corrige", "B", borne_gain_C_B())
                                             if explos_corr else None),
            "compte_sur_B": ({c: comparer([(p, y) for p, y in comptes if c == "tous" or p["_corr"] == c], "compte", "B")
                              for c in ("tous", "exacte", "proche")
                              if any(c == "tous" or p["_corr"] == c for p, _ in comptes)} or None),
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
    g.add_argument("--retro", action="store_true", help="tests rétrospectifs : biais de C et correction")
    a.add_argument("--registre", default=os.environ.get("ALPHABET_REGISTRE", str(ap.REGISTRE)))
    a.add_argument("--enregistrer", action="store_true", help="garder les issues et le score dans le registre")
    a.add_argument("--inclure-essais", action="store_true", help="compter aussi passages à blanc et zone de test")
    a.add_argument("--modele", help="ne scorer que les lignes de ce modèle principal (0.6.0)")
    args = a.parse_args()
    reg = Path(args.registre)
    a_modele = getattr(args, "modele", None)
    if args.retro:
        s = scorer_retro(reg)
        if args.enregistrer:
            s["correction_ecrite"] = enregistrer_correction(reg, s)
        print(json.dumps(s, ensure_ascii=False, indent=2))
        raise SystemExit(0)
    connues = issues_enregistrees(reg)
    if args.metaculus:
        a_chercher = {(x["question_id"], x["url"]) for x in lignes(reg) if x["question_id"] not in connues}
        erreurs = []
        iss = dict(connues, **issues_metaculus(sorted(a_chercher), erreurs))
    else:
        iss = dict(connues, **{str(k): int(v) for k, v in json.loads(Path(args.resolutions).read_text(encoding="utf-8")).items()})
    s = scorer(reg, iss, args.inclure_essais, a_modele)
    s["par_modele"] = {}
    for m_ in sorted({modele_principal(x) for x in lignes(reg)}):
        sm = scorer(reg, iss, args.inclure_essais, m_)
        sm_c = (sm.get("apparie_ABC") or {}).get("C_sur_B") or {}
        s["par_modele"][m_] = {"questions": sm["questions"], "resolues": sm["resolues"],
                               "C_sur_B_gain_log_moyen": sm_c.get("gain_log_moyen"), "C_sur_B_verdict": sm_c.get("verdict")}
    if args.enregistrer:
        s["issues_ajoutees"] = enregistrer(reg, iss, s)
        if args.metaculus:
            s["issues_autres_ajoutees"] = issues_autres(reg, erreurs)
    if args.metaculus:
        s["issues_introuvables"] = erreurs
    print(json.dumps(s, ensure_ascii=False, indent=2))
