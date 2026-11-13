"""Deux tâches du modèle refaites par le code, EN OMBRE (0.10.73, décision d'auteur du 2026-11-13).

Rien ici ne change ce que lit le modèle ni le p calculé. Chaque fonction rend une mesure, gardée au registre, qui
dira plus tard si le code peut prendre la tâche sans perte. Les règles sont fixées ICI, avant toute mesure, et ne
sont pas ajustées sur les issues.

1. filtrage des recherches : ce que le code retirerait des résultats avant la lecture (doublons, passages sans aucun
   mot de la question), et si la lecture aurait perdu un de ses faits ancrés ;
2. ancrage par les séries : quatre cartes dont un marqueur se mesure dans une série de données (CROISSANCE,
   PÉRIODICITÉ, SEUIL, INCERTITUDE), lues par le code dans les relevés des puits, comparées à la lecture du modèle.
"""
from __future__ import annotations

import re
import statistics
import unicodedata

VIDES = set("""le la les un une des du de d l et ou en au aux a à dans sur par pour avec sans que qui quoi dont est sont
sera ce cet cette ces son sa ses leur leurs plus moins pas ne se il elle ils elles on nous vous the of and or in on at
to for by with from is are was were be will would this that these those it its as an than not no yes if what which who
when how between before after into over under about during will have has had do does did question resolve resolves
resolution date criteria""".split())


def _sans_accents(x: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", x) if unicodedata.category(c) != "Mn")


def mots(texte: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]{4,}", _sans_accents(str(texte or "").lower())) if w not in VIDES}


def _jaccard(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if a | b else 0.0


# ---------------------------------------------------------------------------------------------------------------
# 1. Filtrage des recherches
# ---------------------------------------------------------------------------------------------------------------
def filtrer(executees: list[dict], question: str) -> dict:
    """Règles (fixées le 2026-11-13) : les résultats sont coupés en passages (paragraphes) ; un passage est retiré
    s'il double un passage déjà gardé (mêmes mots à 90 % ou plus) ou s'il ne partage AUCUN mot de 4 lettres ou plus
    avec la question. Les relevés des puits (données) ne sont jamais retirés."""
    q = mots(question)
    gardes, retires = [], []
    vus: list[set] = []
    for r in executees:
        if not r.get("executee") or not r.get("resultat"):
            continue
        puits = str(r.get("moteur") or "").startswith("puits")
        for p in re.split(r"\n\s*\n", str(r["resultat"])):
            if not p.strip():
                continue
            m = mots(p)
            if puits:
                gardes.append(p)
                vus.append(m)
                continue
            if any(_jaccard(m, v) >= 0.9 for v in vus):
                retires.append((p, "doublon"))
            elif not (m & q):
                retires.append((p, "hors_question"))
            else:
                gardes.append(p)
                vus.append(m)
    return {"gardes": gardes, "retires": retires}


def mesurer_filtrage(executees: list[dict], question: str, mots_ancres: list[dict]) -> dict:
    """Ce que le filtre aurait coûté : caractères retirés, et faits ancrés dont le passage source (le plus proche en
    mots) aurait été retiré. Un fait perdu est la mesure qui compte : le filtre ne doit rien enlever d'utile."""
    f = filtrer(executees, question)
    n_g = sum(len(p) for p in f["gardes"])
    n_r = sum(len(p) for p, _ in f["retires"])
    perdus = []
    for m in mots_ancres or []:
        if not isinstance(m, dict):
            continue
        fm = mots(m.get("fait")) | mots(m.get("extrait"))
        if not fm:
            continue
        meilleur_g = max((_jaccard(fm, mots(p)) for p in f["gardes"]), default=0.0)
        meilleur_r = max((_jaccard(fm, mots(p)) for p, _ in f["retires"]), default=0.0)
        if meilleur_r > meilleur_g:
            perdus.append(f"{m.get('carte')}@{m.get('strate')}")
    motifs: dict[str, int] = {}
    for _, mo in f["retires"]:
        motifs[mo] = motifs.get(mo, 0) + 1
    return {"caracteres": n_g + n_r, "retires": n_r, "part_retiree": round(n_r / (n_g + n_r), 3) if n_g + n_r else None,
            "passages_retires": motifs, "faits_ancres": len([m for m in mots_ancres or [] if isinstance(m, dict)]),
            "faits_perdus": perdus}


# ---------------------------------------------------------------------------------------------------------------
# 2. Ancrage par les séries
# ---------------------------------------------------------------------------------------------------------------
def _valeurs(releve: dict) -> list[float]:
    return [float(p["valeur"]) for p in releve.get("points") or []
            if isinstance(p.get("valeur"), (int, float)) and not isinstance(p.get("valeur"), bool)]


def croissance(v: list[float]) -> bool:
    """CROISSANCE en f (consigne §30 : « une hausse mesurée qui s'accélère suffit ») : sur les 7 derniers points, au
    moins 4 pas positifs, et la moyenne des 3 derniers pas au-dessus de celle des 3 précédents, elle-même positive."""
    if len(v) < 7:
        return False
    d = [b - a for a, b in zip(v[-7:], v[-6:])]
    return sum(x > 0 for x in d) >= 4 and statistics.mean(d[3:]) > statistics.mean(d[:3]) > 0


def periodicite(v: list[float]) -> bool:
    """PÉRIODICITÉ constatée (skill §52 : au moins trois occurrences datées, jamais postulée) : au moins 4 sommets
    locaux (donc 3 intervalles), espacés régulièrement (coefficient de variation des écarts ≤ 0,25), et une
    autocorrélation des pas positive (≥ 0,3) au décalage médian."""
    if len(v) < 12:
        return False
    pics = [i for i in range(1, len(v) - 1) if v[i] > v[i - 1] and v[i] >= v[i + 1]]
    if len(pics) < 4:
        return False
    e = [b - a for a, b in zip(pics, pics[1:])]
    if statistics.mean(e) <= 1 or statistics.pstdev(e) / statistics.mean(e) > 0.25:
        return False
    k = int(statistics.median(e))
    d = [b - a for a, b in zip(v, v[1:])]
    if len(d) <= k + 2:
        return False
    m = statistics.mean(d)
    den = sum((x - m) ** 2 for x in d)
    return den > 0 and sum((d[i] - m) * (d[i + k] - m) for i in range(len(d) - k)) / den >= 0.3


def seuil(v: list[float], s: float | None) -> bool:
    """SEUIL : un seuil déclaré par la question (spec du compte) a été franchi dans un sens ou dans l'autre sur les
    10 derniers points. Sans seuil déclaré, la règle ne se prononce pas (False)."""
    if s is None or len(v) < 2:
        return False
    w = v[-10:]
    return any((a - s) * (b - s) < 0 or (b == s and a != s) for a, b in zip(w, w[1:]))


def incertitude(v: list[float]) -> bool:
    """INCERTITUDE : volatilité récente (écart-type des 10 derniers pas) au moins 1,5 fois celle de l'ensemble."""
    d = [b - a for a, b in zip(v, v[1:])]
    if len(d) < 20:
        return False
    tout, recent = statistics.pstdev(d), statistics.pstdev(d[-10:])
    return tout > 0 and recent >= 1.5 * tout


REGLES = {"CRO": croissance, "PER": periodicite, "INC": incertitude}


def ancrer_series(releves: list[dict], seuil_question: float | None = None) -> dict[str, bool]:
    """Carte → vue par le code dans AU MOINS un relevé."""
    out = {k: False for k in (*REGLES, "SEU")}
    for r in releves or []:
        v = _valeurs(r)
        for k, f in REGLES.items():
            out[k] = out[k] or f(v)
        out["SEU"] = out["SEU"] or seuil(v, seuil_question)
    return out


def comparer_series(releves: list[dict], seuil_question: float | None, mots_ancres: list[dict]) -> dict | None:
    """Accord carte par carte entre le code et la lecture du modèle (carte ancrée dans une strate quelconque)."""
    if not releves:
        return None
    code = ancrer_series(releves, seuil_question)
    import alphabet_pipeline as ap
    lu = set()
    for m in mots_ancres or []:
        if isinstance(m, dict):
            try:
                lu.add(ap.code_carte(m.get("carte")))
            except Exception:
                continue
    return {"code": code, "modele": {k: k in lu for k in code}, "accord": {k: code[k] == (k in lu) for k in code},
            "releves": len(releves), "seuil_question": seuil_question}
