"""Pipeline de l'alphabet situationnel pour une question binaire Metaculus.

Indépendant de forecasting-tools : il reçoit deux fonctions asynchrones, `llm(prompt) -> str` et
`chercher(requete) -> str`, ce qui permet de le tester hors ligne avec des fonctions simulées.

Trois bras par question (audit des concurrents, §6.3) :
  A  le modèle seul, sans le skill (calculé avant, et scellé, par le bot) ;
  B  la classe de référence seule (vue extérieure, posée avant toute carte, sur ses propres recherches) ;
  C  l'alphabet complet (moteur.py, la fréquence de B passée en référence : C - B = l'apport des cartes).

Le moteur reste juge : un dossier refusé ou une probabilité « non estimée » ne sont jamais remplacés par un
chiffre inventé. Le bot poste alors le bras A, et le registre garde la trace du refus. Un état nul (aucune
carte ancrée) n'ajuste pas le taux de base : le bot poste alors le bras B.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import tempfile
import unicodedata
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Awaitable, Callable

VERSION_BOT = "0.9.1"

DOSSIER_SKILL = Path(os.environ.get("ALPHABET_SKILL_DIR", Path(__file__).parent / "alphabet-situationnel")).resolve()
MOTEUR = DOSSIER_SKILL / "scripts" / "moteur.py"
REGISTRE = Path(os.environ.get("ALPHABET_REGISTRE", Path(__file__).parent / "registre")).resolve()
VRAI_REGISTRE = (Path(__file__).parent / "registre").resolve()


class RegistreInterdit(RuntimeError):
    """0.8.0 (audit B-01) : écriture refusée dans le vrai registre depuis un test."""


def sous_test() -> bool:
    return (bool(os.environ.get("ALPHABET_TESTS")) or "pytest" in sys.modules
            or "unittest" in Path(sys.argv[0] if sys.argv else "").as_posix())


def registre_ecrivable(dossier: Path | None = None) -> Path:
    """Le répertoire du registre, après la garde : AUCUNE écriture dans le vrai registre quand un test tourne
    (des lignes fictives y avaient été écrites puis publiées, 0.6.3 à 0.7.3). Tout point d'écriture passe ici."""
    d = Path(dossier or REGISTRE).resolve()
    if sous_test() and (d == VRAI_REGISTRE or VRAI_REGISTRE in d.parents):
        raise RegistreInterdit(f"écriture dans le vrai registre refusée pendant un test ({d})")
    d.mkdir(parents=True, exist_ok=True)
    return d
MAX_RECHERCHES = int(os.environ.get("ALPHABET_MAX_RECHERCHES", "12"))
MAX_CORRECTIONS = int(os.environ.get("ALPHABET_MAX_CORRECTIONS", "2"))

TYPES = ("apparait", "persiste", "disparait")
SEMANTIQUES = {"apparait": ("presence", "au-moins-une-fois"),
               "persiste": ("presence", "continue"),
               "disparait": ("presence", "au-moins-une-fois")}
FAMILLES = ("observation", "discrimination", "contradiction")

Llm = Callable[[str], Awaitable[str]]
Chercheur = Callable[[str], Awaitable[str]]
# 0.3.0 : questions Metaculus RÉSOLUES et comparables, pour la classe de référence du bras B. Rend une liste de
# {"titre", "issue" (yes/no), "resolue_le"} : les issues seulement, jamais les prévisions de la communauté (§26).
Historique = Callable[[list[str], str], Awaitable[list[dict]]]
NB_VUES = max(1, int(os.environ.get("ALPHABET_VUES") or "3"))
CLASSE_FIGEE = os.environ.get("ALPHABET_CLASSE_FIGEE", "1") != "0"   # 0.4.0 : définir la classe avant de compter
MAX_HISTORIQUE = int(os.environ.get("ALPHABET_MAX_HISTORIQUE") or "15")
PUITS = os.environ.get("ALPHABET_PUITS", "1") != "0"   # 0.7.0 : puits de données (alphabet_puits.py)
MAX_APPELS_PUITS = int(os.environ.get("ALPHABET_PUITS_MAX") or "3")


# --------------------------------------------------------------------------- moteur et références

def _moteur():
    """Le module du moteur, importé depuis le skill (noms des cartes, version)."""
    sys.path.insert(0, str(MOTEUR.parent))
    import moteur  # noqa: E402
    return moteur


def noms_cartes() -> dict[str, str]:
    return dict(_moteur().NOMS)


def version_skill() -> str:
    return _moteur().P["version"]


def strates_chiffrees() -> list[int]:
    """Strates où le skill accepte de chiffrer (décision L7 ; critère de levée : validation.md §27)."""
    return list(_moteur().P["strates_prevision"])


POIDS = {"F": 3, "M": 2, "f": 1}
CATEGORIES_REJET = ("aucun_fait", "marqueur_non_rempli", "contredit", "non_cherchee")
# 0.2.2 : catégories qui disent « on n'a pas regardé » plutôt que « il n'y a rien » : un état nul qui en contient est un
# ANGLE MORT possible, relancé une fois par des recherches ciblées avant d'être accepté.
ANGLES_MORTS = ("aucun_fait", "non_cherchee")
STRUCTURE_ABSENTE = ("contredit", "marqueur_non_rempli")
MAX_RECHERCHES_RELANCE = int(os.environ.get("ALPHABET_MAX_RECHERCHES_RELANCE", "6"))
RELANCE_ETAT_NUL = os.environ.get("ALPHABET_RELANCE_ETAT_NUL", "1") != "0"
MIN_SOURCES = 2  # candidates exigées parmi les cartes qui, selon la matrice, agissent sur l'événement « apparait »


def sources_matrice(cible: str) -> list[tuple[str, str]]:
    """Cartes qui agissent sur la carte `cible` selon la matrice des dynamiques du skill, la plus forte d'abord."""
    m = _moteur().P["matrice"]
    s = [(a, v[cible]) for a, v in m.items() if cible in v and a != cible]
    return sorted(s, key=lambda x: (-POIDS.get(x[1], 0), x[0]))


def table_matrice() -> str:
    noms = noms_cartes()
    return "\n".join(f"{ab} {noms[ab]} ← " + ", ".join(f"{a}({w})" for a, w in sources_matrice(ab)) for ab in noms)


LECTURE_HORS_STRATE = os.environ.get("ALPHABET_LECTURE_HORS_STRATE", "") in ("1", "oui", "true")
# 0.9.0 (décision d'auteur du 2026-11-08 ; skill validation.md §29) : hors strate 7, l'alphabet lit et le moteur chiffre
# avec --exploratoire. Le chiffre est scellé (C.exploratoire), jamais posté, scoré à part. « 0 » pour couper.
EXPLORATOIRE = os.environ.get("ALPHABET_EXPLORATOIRE", "1") not in ("0", "non", "false")
ERREURS_STRUCTURELLES = ("limitée aux strates",)  # refus qu'aucune correction de la lecture ne peut lever


def lire_ref(rel: str) -> str:
    return (DOSSIER_SKILL / rel).read_text(encoding="utf-8")


def fiches(cartes: list[str]) -> str:
    """Les fiches complètes de `cartes.md` pour les cartes citées (noms ou abréviations)."""
    noms = noms_cartes()
    voulues = {noms.get(c, c).replace("·", " · ").replace("  ", " ") for c in cartes} | {noms.get(c, c) for c in cartes}
    texte = lire_ref("references/cartes.md")
    blocs = re.split(r"(?m)^## ", texte)
    gardes = [b for b in blocs if b.split("\n", 1)[0].strip() in voulues]
    return "\n".join("## " + b.strip() for b in gardes)


def equivalences(strates: list[int]) -> str:
    out = []
    for s in sorted(set(strates)):
        f = DOSSIER_SKILL / "references" / "equivalences" / f"strate-{s:02}.md"
        if f.is_file():
            out.append(f.read_text(encoding="utf-8"))
    return "\n\n".join(out)


def appeler_moteur(dossier: dict, etat: str, evenement: str, semantique: str, date_info: str, vue: dict,
                   temporalite: str = "generique", exploratoire: bool = False) -> dict:
    """Lance `moteur.py calculer --dossier` ; la fréquence de la vue extérieure entre comme référence (--fref)."""
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(dossier, f, ensure_ascii=False)
        chemin = f.name
    cmd = [sys.executable, str(MOTEUR), "calculer", "--etat", etat, "--evenement", evenement,
           "--temporalite", temporalite, "--semantique", semantique, "--dossier", chemin,
           "--date-information", date_info, "--fref", str(vue["frequence"]),
           "--source-ref", str(vue.get("source", "")), "--periode-ref", str(vue.get("periode", "")),
           "--disponible-ref", str(vue.get("disponible_le", date_info)),
           "--definition-ref", str(vue.get("classe_de_reference", "")), "--json"] + (["--exploratoire"] if exploratoire else [])
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=300, cwd=str(DOSSIER_SKILL))
    finally:
        os.unlink(chemin)
    try:
        return json.loads(r.stdout)
    except json.JSONDecodeError:
        return {"erreur": (r.stderr or r.stdout or "sortie illisible").strip()[-1500:], "code": r.returncode}


# --------------------------------------------------------------------------- données

@dataclass
class Question:
    id: int | str
    url: str
    titre: str
    contexte: str
    criteres: str
    precisions: str
    resolution: date  # date de résolution prévue


@dataclass
class Resultat:
    p_A: float | None
    p_B: float | None
    p_C: float | None
    bras_poste: str
    p_poste: float | None
    commentaire: str
    ligne: dict = field(default_factory=dict)


def sceau(obj: dict) -> str:
    return hashlib.sha256(json.dumps(obj, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def modeles_actifs() -> dict | None:
    """0.6.0 : modèles retenus pour ce passage, par rôle (alphabet_modeles.appliquer)."""
    try:
        return json.loads(os.environ["ALPHABET_MODELES"])
    except Exception:
        return None


def correction_retro() -> dict | None:
    """0.5.0 : le décalage de C appris sur les tests rétrospectifs (registre/correction-retro.json, écrit par
    score_registre.py --retro --enregistrer). None s'il n'existe pas encore."""
    f = REGISTRE / "correction-retro.json"
    try:
        c = json.loads(f.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(c.get("decalage_logit"), (int, float)):
        return None
    # 0.8.0 (audit m-15) : une correction a une durée de vie (VALIDITE_CORRECTION jours) ; au-delà, il faut la
    # réestimer sur de nouveaux tests rétrospectifs.
    try:
        age = (datetime.now(timezone.utc) - datetime.fromisoformat(c["calcule_le"])).days
    except (KeyError, ValueError, TypeError):
        return None
    return c if age <= VALIDITE_CORRECTION else None


VALIDITE_CORRECTION = int(os.environ.get("ALPHABET_VALIDITE_CORRECTION") or "120")


def symetrique(c: dict) -> dict | None:
    """0.9.1 (décision d'auteur du 2026-11-08 : « normaliser » le biais à la hausse). Le moteur ne fait que MONTER la
    probabilité (multiplicateurs ≥ 1, décision 9 du skill) : une lecture ne peut pas dire « les faits vont contre ».
    Or elle le dit déjà : une candidate écartée parce que les faits la CONTREDISENT (catégorie « contredit ») est une
    preuve contre l'événement. Version symétrique, en ombre : chaque candidate contredite DIVISE la cote par le λ
    qu'elle aurait apporté si elle avait été ancrée (mêmes multiplicateurs, même matrice, même plafond, lus dans le
    skill). Hypothèse déclarée : la symétrie des preuves (qui reste à mesurer).

    Calculée pour tout événement « apparait » qui a un taux de base, y compris en état nul : sans carte ancrée mais
    avec des candidates contredites, la lecture ABAISSE B ; sans carte ni contredite, pas de chiffre (pas de C = B)."""
    ev = (c.get("plan") or {}).get("evenement") or {}
    p_b = c.get("p_B")
    if ev.get("type") != "apparait" or p_b is None:
        return None
    cats = (c.get("dossier") or {}).get("_categories_rejet") or {}
    contre = sorted(k for k, v in cats.items() if v == "contredit" and "@" in str(k))
    p_c = c.get("p_C")
    if p_c is None and not contre:
        return None
    M = _moteur()
    mots = [{"c": k.split("@")[0], "s": int(k.split("@")[1])} for k in contre if k.split("@")[1].isdigit()]
    src, _ = M.sources_de({"mots": mots}, f"{ev['carte']}@{ev['strate']}", [], set(), set())
    lr_contre = math.prod(x["lambda"] for x in src) if src else 1.0
    cote = lambda q: q / (1 - q)
    b = borner(p_b)
    lr_pour = cote(borner(p_c)) / cote(b) if p_c is not None else 1.0
    plafond = float(M.P["plafond_LR"])
    lr = min(plafond, max(1 / plafond, lr_pour / lr_contre))
    o = cote(b) * lr
    p = o / (1 + o)
    if p > b:
        p = min(p, max(b, float(M.P["plafond_p0"])))
    return {"p": borner(p), "lr_pour": lr_pour, "lr_contre": lr_contre, "lr": lr,
            "contredites": [x["mot"] for x in src], "contredites_sans_action": sorted(set(contre) - {x["mot"] for x in src}),
            "hypothese": "symétrie : une candidate contredite par les faits divise la cote par le λ qu'elle aurait apporté"}


def corriger_C(p_C: float | None, corr: dict | None) -> float | None:
    """C corrigé du biais à la hausse : logit p' = logit p + b (b ≤ 0 attendu). Scellé au registre, JAMAIS posté :
    la règle de postage ne change pas avant la levée de L7."""
    if p_C is None or corr is None:
        return None
    p = borner(p_C)
    z = math.log(p / (1 - p)) + float(corr["decalage_logit"])
    return borner(1 / (1 + math.exp(-z)))


def extraire_json(texte: str) -> dict:
    """Le premier objet JSON complet d'une réponse de modèle (bloc ```json``` ou accolades). 0.8.0 (audit m-01) :
    lecture par raw_decode (un second objet ou du texte après ne gênent plus) ; virgules finales tolérées."""
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", texte, re.S)
    brut = m.group(1) if m else texte[texte.find("{"):] if "{" in texte else ""
    if not brut:
        raise ValueError("aucun objet JSON dans la réponse")
    dec = json.JSONDecoder()
    try:
        return dec.raw_decode(brut)[0]
    except json.JSONDecodeError:
        return dec.raw_decode(re.sub(r",\s*([}\]])", r"\1", brut))[0]


BORNE_BASSE, BORNE_HAUTE = 0.001, 0.999  # bornes de l'API Metaculus pour une question binaire


def borner(p: float) -> float:
    """0.2.0 (audit, B1) : les bornes de l'API (0,001–0,999), et non 0,01–0,99, qui effaçait C − B sur les événements
    rares (A = B = C = 0,01)."""
    return max(BORNE_BASSE, min(BORNE_HAUTE, float(p)))


# --------------------------------------------------------------------------- consignes

def consigne_plan(q: Question, recherche: str, aujourdhui: str) -> str:
    return f"""Tu appliques le skill « alphabet situationnel » à une question de prévision. Étape 1 : le plan.

Interdit : utiliser des cotes de marché, des prévisions de plateformes (Metaculus, Polymarket, Kalshi…) ou des avis
de prévisionnistes publiés. Seuls des faits datés au plus tard le {aujourdhui} comptent.

QUESTION : {q.titre}
CONTEXTE : {q.contexte}
CRITÈRES DE RÉSOLUTION : {q.criteres}
PRÉCISIONS : {q.precisions}
RÉSOLUTION PRÉVUE : {q.resolution.isoformat()}
DATE D'INFORMATION : {aujourdhui}

RECHERCHE GÉNÉRALE :
{recherche[:6000]}

STRATES : 1 Matière, 2 Vivant, 3 Psyché, 4 Relations, 5 Organisations, 6 Économie, 7 Géopolitique, 8 Droit,
9 Culture, 10 Technique, 11 Climat, 12 Histoire longue (plus d'un siècle), 13 Politique intérieure.

INDEX DES CARTES :
{lire_ref("references/cartes-index.md")}

MATRICE DES DYNAMIQUES (carte visée ← cartes qui la font apparaître, poids F fort, M moyen, f faible) :
{table_matrice()}

Rends UNIQUEMENT un objet JSON :
{{
 "strates": [entiers, 1 ou 2 strates selon le mécanisme des faits],
 "candidats": ["ABR@strate", ...]  (2 à 4 par strate, abréviations : {", ".join(noms_cartes())}),
 "contre_candidate": ["ABR@strate", ...]  (au moins une par strate, parmi les candidats),
 "evenement": {{"carte": "ABR", "strate": n, "type": "apparait|persiste|disparait"}},
 "semantique": "presence|au-moins-une-fois|continue",
 "temporalite": "generique (l'événement peut survenir à tout moment) | programmee (échéance fixée d'avance : vote, sommet, date
     légale) | duree_de_vie (l'objet a une durée de vie propre)",
 "pourquoi_evenement": "en quoi le OUI de la question correspond à cet événement de carte",
 "recherches_reference": ["requête", ...]  (1 à {MAX_RECHERCHES_REFERENCE} requêtes pour trouver la FRÉQUENCE HISTORIQUE
     d'événements comparables : combien de fois, sur quelle période, dans quelle population de cas),
 "recherches_historique": ["2 à 4 mots-clés en anglais", ...]  (pour retrouver des questions de prévision DÉJÀ
     RÉSOLUES portant sur des événements du même type : acteurs ou types d'acte, sans date),
 "recherches": [{{"famille": "observation|discrimination|contradiction", "cartes": ["ABR@s", ...], "requete": "..."}}]
}}
Choisis la strate de l'événement d'après le mécanisme des faits, et seulement d'après lui.
Règles : « apparait » vise une carte ABSENTE de l'état actuel, « persiste » ou « disparait » une carte PRÉSENTE.
Sémantiques admises : apparait → presence ou au-moins-une-fois ; persiste → presence ou continue ;
disparait → presence ou au-moins-une-fois. Si le OUI ne correspond à aucun événement de carte, mets
"evenement": null et explique-le dans "pourquoi_evenement" (le bot s'abstiendra d'utiliser l'alphabet).
Candidates : pour un événement « apparait », le moteur ne déplace le taux de base QUE par les cartes présentes qui,
d'après la matrice ci-dessus, agissent sur la carte visée. Choisis donc au moins {MIN_SOURCES} candidates parmi ces cartes
(les plus fortes d'abord, si les faits s'y prêtent), plus une contre-candidate. Ne mets pas la carte visée elle-même
parmi les candidates d'un événement « apparait ».
Recherches : pour chaque candidate, une requête de chaque famille ; pour chaque paire de candidates d'une même strate,
une requête de discrimination. Au plus {MAX_RECHERCHES} requêtes au total. Une requête se forme sur le phénomène
observable, l'objet et la période, JAMAIS sur le nom d'une carte, ni sur une prémisse.
"""


def controle_references(vue: dict, n_refs: int, n_hist: int) -> str | None:
    """0.8.3 (synthèse du 4 novembre, O1) : fondement_memoire() ne testait que la PRÉSENCE d'une étiquette [Rn] ou
    [Mn] ; un [R7] inventé quand quatre résultats ont été fournis faisait passer une vue pour sourcée. Toute étiquette
    citée doit désigner un résultat ou une question réellement fournis."""
    texte = f"{vue.get('fondement', '')} {vue.get('calcul', '')} {vue.get('source', '')}"
    for genre, i in re.findall(r"\[([RM])(\d+)\]", texte):
        borne = n_refs if genre == "R" else n_hist
        if not 1 <= int(i) <= borne:
            return f"vue extérieure : référence [{genre}{i}] inexistante ({borne} fournie(s))"
    return None


def source_reprise(vue: dict, sources: list[str]) -> str | None:
    """0.8.1 : la consigne « une autre source » n'a pas suffi (passage 42489373511 : trois vues de 43332 sur le même
    registre). Contrôle sans modèle : une source dont les mots significatifs recouvrent à 60 % ceux d'une source déjà
    prise est refusée."""
    def mots(x):
        return {w for w in _normal(x).split() if len(w) >= 4}
    m = mots(vue.get("source"))
    for s_ in sources:
        a = mots(s_)
        if m and a and len(m & a) / min(len(m), len(a)) >= 0.6:
            return f"vue extérieure : source déjà utilisée ({str(vue.get('source'))[:80]})"
    return None


def bloc_sources_prises(sources: list[str] | None) -> str:
    """0.8.0 (audit M-01) : trois appels du même prompt donnaient trois fois le même chiffre (dispersion 0). Chaque vue
    après la première doit compter sur une AUTRE source : trois mesures, pas trois tirages."""
    if not sources:
        return ""
    return ("\nSOURCES DÉJÀ UTILISÉES par d'autres estimations (ne les reprends pas : compte sur une AUTRE source "
            "indépendante ; s'il n'en existe aucune d'honnête, mets \"frequence\": null et \"motif\": "
            "\"source unique\") :\n" + "\n".join(f"  - {x}" for x in sources) + "\n")


def bloc_ancrage(ancrage: dict | None) -> str:
    """0.7.2 : un compte calculé sur une série PROCHE du critère : chaque vue part de lui et dit ce qu'elle en fait."""
    if not ancrage:
        return ""
    return f"""
COMPTE CALCULÉ PAR LE CODE sur une série PROCHE du critère (pas identique) :
  {ancrage['fondement']} · {ancrage['source']}
  {ancrage['calcul']} → fréquence {ancrage['frequence']:.4g} sur {ancrage['periode']}
  écart déclaré avec le critère : {ancrage.get('ecart_critere')}
PARS DE CE COMPTE. Trois choix, à dire dans "usage_compte" : « retenu » (l'écart est négligeable : ta fréquence est
celle du compte), « ajuste » (corrige-le dans le sens de l'écart nommé, et dis dans "calcul" de combien et pourquoi),
« ecarte » (une meilleure base existe ci-dessous : dis laquelle et pourquoi le compte ne vaut pas ici).
"""


def consigne_vue(q: Question, plan: dict, references: list[dict], aujourdhui: str, jours: int,
                 historique: list[dict] | None = None, classe: dict | None = None,
                 ancrage: dict | None = None, sources_prises: list[str] | None = None) -> str:
    res = "\n\n".join(f"[R{i + 1}] « {r['requete']} »\n{r['resultat'][:3000]}" for i, r in enumerate(references))
    hist = "\n".join(f"[M{i + 1}] {h['titre']} → {str(h['issue']).upper()} (résolue le {h.get('resolue_le', '?')})"
                     for i, h in enumerate(historique or []))
    imposee = ("" if not classe else
               "\nCLASSE DE RÉFÉRENCE IMPOSÉE (définie avant toi ; compte SUR ELLE, sans la changer ni l'élargir ; "
               "recopie-la dans classe_de_reference ; si elle ne permet aucun comptage honnête, mets frequence null) :\n"
               + json.dumps(classe, ensure_ascii=False, indent=1) + "\n")
    return f"""Étape 2 : la VUE EXTÉRIEURE, avant toute carte. Elle ne doit pas être choisie d'après l'état présent.
{imposee}
QUESTION : {q.titre}
CRITÈRES DE RÉSOLUTION : {q.criteres}
PRÉCISIONS : {q.precisions}
DATE D'INFORMATION : {aujourdhui} ; fenêtre : {jours} jours (jusqu'au {q.resolution.isoformat()}).

RÉSULTATS DES RECHERCHES SUR LE TAUX DE BASE :
{res or "(aucun)"}

QUESTIONS DE PRÉVISION DÉJÀ RÉSOLUES, d'apparence voisine (issue seulement) :
{hist or "(aucune)"}
{bloc_ancrage(ancrage)}{bloc_sources_prises(sources_prises)}
La fréquence se tire, au choix : (a) des résultats ci-dessus (cite [R1], [R2]…) ; (a') des questions résolues
ci-dessus, en ne gardant que celles qui comptent le MÊME type d'événement sur une fenêtre comparable (cite [M1]… ;
fréquence = OUI / questions gardées, ramenée à la fenêtre ; moins de 5 questions gardées : ne l'utilise pas seule) ;
(b) d'un registre historique
notoire et vérifiable, que tu NOMMES précisément (ex. « liste des retraits de l'Union européenne depuis 1957 : un seul,
le Royaume-Uni en 2020 »). Compte des cas sur une période, puis ramène à une fenêtre de {jours} jours. N'invente
aucun chiffre : si aucune base honnête n'existe, mets "frequence": null et explique-le dans "motif".

Rends UNIQUEMENT un objet JSON :
{{
 "frequence": nombre dans ]0, 1[ ou null,
 "classe_de_reference": "les cas comptés, dans le vocabulaire de la source, SANS aucun nom de carte de l'alphabet",
 "source": "base, étude ou registre nommé",
 "fondement": "recherche [Rn] | questions résolues [Mn] | registre historique",
 "periode": "AAAA-AAAA",
 "disponible_le": "AAAA-MM-JJ (au plus tard le {aujourdhui})",
 "calcul": "comptage et mise à l'échelle de la fenêtre, en mots",
 "expression": "le MÊME calcul en arithmétique pure, que le code refera (nombres, + - * / ** et parenthèses ;
     ex. « 1 - (1 - 3/40) ** (120/365) ») ; il doit redonner frequence",
 "classe_alternative": {{"frequence": …, "classe_de_reference": "…", "source": "…", "pourquoi_ecartee": "…"}} ou null,
 "motif_sans_alternative": "si classe_alternative est null",
 "ecart_critere": "en quoi la classe compte autre chose que le critère de résolution, ou « identique : … »",
 "resolution": "ce qui fera dire OUI, en une phrase",
 "source_resolution": {{"emetteur": "nommé, jamais « la presse »", "document": "…", "regle_ambiguite": "…"}},
 "motif": "si frequence est null"{', "usage_compte": "retenu|ajuste|ecarte"' if ancrage else ""}
}}"""


def regles_dossier() -> str:
    return """RÈGLES DU DOSSIER (résumé du protocole du skill ; en cas de doute, rester en f, jamais forcer F) :
- Chaque mot : carte (abréviation), strate, intensite F ou f, fait précis daté, objet, source nommée, source_url,
  date_consultation, classe_source ("contemporain"), passage (localisation + relation "soutient"), test, contre_observation
  + portee, garantie {mecanisme, support {type texte|loi|donnee|cas, reference, disponible_le}, attendu, contredirait},
  option {acteur, avant, apres}, corroboration, et pour F une ligne a6.
- F exige un fait SUFFISANT : test "pistolet" ou "double". Un fait qui remplit seulement le marqueur est un "cerceau" : f.
- F exige corroboration "independantes" (deux sources nommées séparées par « ; », et independance {critere origine|
  producteur|transmission, motif}) ou "unique" pour une source primaire. Deux relais d'une même origine = une source.
- a6 (pour F) : « CARTE@s : VOISINE → (pourquoi écartée) ; … » pour TOUTES les voisines de la fiche, sans « ? ».
- contre_observation : la plus forte trouvée DANS la situation ; portee marginale|substantielle|dominante|aucune.
- contredirait ≠ attendu, sans nommer la carte. option : un fait qui ne change l'espace d'action de personne ne s'ancre pas.
- rejets_classes : pour chaque candidate non ancrée, {"categorie": …, "motif": …}, catégorie au choix :
  "aucun_fait" (aucun fait pertinent dans les résultats), "marqueur_non_rempli" (des faits existent mais ne remplissent
  pas le marqueur local), "contredit" (un fait de la situation contredit la carte), "non_cherchee" (ses requêtes n'ont
  pas été lancées). Choisis la catégorie d'après les résultats de recherche, pas d'après ton intuition. Ajoute
  "fait_attendu" (une phrase : ce que dirait un fait qui remplirait le marqueur ici) et "extrait_proche" (le passage
  le plus proche trouvé, avec son numéro [n], ou null).
- questions : au moins une question ouverte et datée qui départagerait la lecture (si_oui, si_non, resolution, statut).
- Ne cite que des faits trouvés dans les résultats de recherche fournis ; n'invente ni source, ni URL, ni date.
- ÉTAT NUL ADMIS : si aucun fait ne remplit le marqueur d'une carte, "mots" est une liste vide et chaque candidate va
  dans rejets. C'est une lecture légitime (« aucune structure lue »), jamais un échec : ne force pas une carte.
- dynamique_observee (seulement si "mots" est vide) : en une ou deux phrases, la dynamique que les faits trouvés
  montrent malgré tout (qui agit, sur quoi, dans quel sens), SANS nommer aucune carte ni structure de l'alphabet ;
  "aucune" si les faits ne montrent aucune dynamique. Elle n'entre pas dans le calcul : elle sert à chercher plus tard
  une structure qui manquerait à l'alphabet.
"""


def consigne_dossier(q: Question, plan: dict, resultats: list[dict], aujourdhui: str, jours: int) -> str:
    cartes = [c.split("@")[0] for c in plan.get("candidats", [])]
    exemple = json.loads(lire_ref("assets/dossier.exemple.json"))
    exemple = {k: exemple[k] for k in CLES_LECTURE if k in exemple}
    lancees = [r for r in resultats if not r.get("non_lancee")]
    res = "\n\n".join(f"[{i + 1}] ({r['famille']}, {', '.join(r['cartes'])}) « {r['requete']} »\n{r['resultat'][:3000]}"
                      for i, r in enumerate(lancees))
    coupees = [r for r in resultats if r.get("non_lancee")]
    if coupees:
        res += ("\n\nREQUÊTES NON LANCÉES (plafond de recherches) : "
                + " ; ".join(f"« {r['requete']} » ({', '.join(r['cartes'])})" for r in coupees)
                + ". Une candidate qui n'a pas été cherchée se classe « non_cherchee », jamais « aucun_fait ».")
    ev = plan["evenement"]
    return f"""Étape 3 : la lecture (mots ancrés) pour la question ci-dessous. La vue extérieure est déjà posée.

QUESTION : {q.titre}
CRITÈRES DE RÉSOLUTION : {q.criteres}
PRÉCISIONS : {q.precisions}
DATE D'INFORMATION : {aujourdhui} ; fenêtre : {jours} jours (jusqu'au {q.resolution.isoformat()}).
PLAN RETENU : {json.dumps({k: v for k, v in plan.items() if k != "recherches_reference" and not k.startswith("_")}, ensure_ascii=False)}

RÉSULTATS DES RECHERCHES EXÉCUTÉES :
{res}
{donnees_puits(plan)}
{regles_dossier()}

FICHES DES CANDIDATES :
{fiches(cartes)}

ÉQUIVALENTS LOCAUX DES STRATES :
{equivalences(plan.get("strates", []))}

FORMAT (exemple fictif, à suivre pour la structure seulement) :
{json.dumps(exemple, ensure_ascii=False, indent=1)}

Rends UNIQUEMENT un objet JSON avec les clés : {", ".join(CLES_LECTURE)} (et dynamique_observee si "mots" est vide).
L'événement prévu est {ev['carte']}@{ev['strate']} {ev['type']} : {"cette carte ne doit PAS figurer dans les mots" if ev['type'] == "apparait" else "cette carte doit figurer dans les mots"}."""


def consigne_relance(q: Question, plan: dict, cibles: dict, deja: list[dict], aujourdhui: str) -> str:
    """0.2.2 : demande de requêtes nouvelles pour les candidates écartées faute de recherche (angles morts)."""
    cartes = sorted({c.split("@")[0] for c in cibles})
    lignes_ = "\n".join(f"- {c} : [{v}]" for c, v in cibles.items())
    return f"""Étape 3 bis : la lecture n'a ancré aucune carte, mais certaines candidates ont été écartées faute de
recherche, pas faute de structure. Avant d'accepter l'état nul, propose des requêtes NOUVELLES pour elles.

QUESTION : {q.titre}
CRITÈRES DE RÉSOLUTION : {q.criteres}
DATE D'INFORMATION : {aujourdhui}
CANDIDATES À RECHERCHER (catégorie de rejet) :
{lignes_}
REQUÊTES DÉJÀ LANCÉES (ne pas les répéter ni les paraphraser) :
{chr(10).join("- " + r["requete"] for r in deja)}

FICHES DES CANDIDATES (marqueurs à remplir) :
{fiches(cartes)}

Règles : au plus {MAX_RECHERCHES_RELANCE} requêtes au total, 1 ou 2 par candidate ; chacune formée sur le PHÉNOMÈNE
observable que décrit le marqueur, avec les acteurs et la période de la question, jamais sur le nom d'une carte.
Interdit : cotes de marché, prévisions de plateformes, avis de prévisionnistes. Seuls des faits datés au plus tard
le {aujourdhui} comptent.

Rends UNIQUEMENT un objet JSON : {{"recherches": [{{"cartes": ["CARTE@strate"], "requete": "..."}}]}}"""


def dynamique_observee(lecture: dict) -> dict | None:
    """0.2.3 : la dynamique décrite par le lecteur dans un état nul, hors calcul, pour chercher plus tard une structure
    manquante. Une description qui nomme une carte est gardée mais signalée (elle ne vaut pas description neutre)."""
    texte = lecture.get("dynamique_observee")
    if not isinstance(texte, str) or not texte.strip():
        return None
    texte = texte.strip()[:600]
    bas = texte.lower()
    nommees = sorted({code for code, nom in noms_cartes().items()
                      if re.search(rf"\b{re.escape(code)}\b", texte) or str(nom).lower() in bas})
    return {"texte": texte, "cartes_nommees": nommees}


def _normal(texte: str) -> str:
    t = unicodedata.normalize("NFD", str(texte or "")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", t).strip()


def _chiffres(texte: str) -> list[str]:
    """Nombres d'au moins deux chiffres, séparateurs de milliers retirés (« 2 295 », « 2,295 » → 2295). 0.8.0 (audit
    m-02) : les décimales sont gardées et normalisées (« 10,4 » et « 10.4 » → 10.4 ; « 6,3 » → 6.3)."""
    t = re.sub(r"(?<=\d)[\s\u00a0\u202f.,](?=\d{3}\b)", "", str(texte or ""))
    t = re.sub(r"(?<=\d),(?=\d)", ".", t)
    nombres = set()
    for n in re.findall(r"\d+(?:\.\d+)?", t):
        n = n.rstrip("0").rstrip(".") if "." in n else n
        if len(n.replace(".", "")) >= 2:
            nombres.add(n)
    return sorted(nombres)


def controle_attribution(dossier: dict | None, textes: str | None) -> dict | None:
    """0.5.2, idée reprise d'EnVrai (contrôles locaux du repérage) : vérifier SANS modèle que ce que la lecture cite
    vient bien des résultats de recherche. Pour chaque mot ancré : (1) chaque extrait du passage se retrouve-t-il dans
    les résultats (70 % au moins de ses mots de quatre lettres ou plus) ? (2) chaque nombre du fait y figure-t-il ?
    Diagnostic scellé au registre : il ne change ni la lecture ni le calcul. Un mot sans extrait retrouvé, ou avec un
    nombre absent des résultats, est « non attribué » : la règle « ne cite que des faits trouvés » n'est pas tenue."""
    if not dossier or not dossier.get("mots") or textes is None:
        return None
    corpus = _normal(textes)
    mots_corpus = set(corpus.split())
    chiffres_corpus = set(_chiffres(textes))
    textes_bas = str(textes).lower()
    detail, non_attribues, non_verifiables = {}, 0, 0
    # 0.8.0 (audit M-04) : il ne suffit plus que les extraits existent et que les nombres du fait figurent QUELQUE
    # PART : les nombres du fait doivent être dans les extraits CITÉS, et le fait lui-même doit se retrouver dans le
    # corpus (la moitié au moins de ses mots de quatre lettres ou plus).
    for m in dossier["mots"]:
        cle = f"{m.get('carte')}@{m.get('strate')}"
        extraits = [x.get("extrait") for x in (m.get("passage") or []) if isinstance(x, dict) and x.get("extrait")]
        retrouves = 0
        for e in extraits:
            ne = _normal(e)
            longs = [w for w in ne.split() if len(w) >= 4]
            if (ne and ne in corpus) or (longs and sum(w in mots_corpus for w in longs) / len(longs) >= 0.7):
                retrouves += 1
        nombres = _chiffres(m.get("fait"))
        absents = [c for c in nombres if c not in chiffres_corpus]
        chiffres_cites = set(_chiffres(" ".join(extraits)))
        hors_extraits = [c for c in nombres if c not in chiffres_cites] if extraits else []
        url = str(m.get("source_url") or "").strip()
        cle_url = re.sub(r"^https?://(www\.)?", "", url).split("#")[0].split("?")[0].rstrip("/").lower()
        url_retrouvee = (cle_url in textes_bas) if cle_url else None     # 0.8.3 (O1) : l'URL citée a-t-elle été vue ?
        mots_fait = [w for w in _normal(m.get("fait")).split() if len(w) >= 4]
        part_fait = sum(w in mots_corpus for w in mots_fait) / len(mots_fait) if mots_fait else None
        if not extraits and not nombres:
            attribue = None                    # rien de littéral à retrouver : non vérifiable, pas « attribué »
            non_verifiables += 1
        else:
            attribue = ((not extraits or retrouves > 0) and not absents and not hors_extraits
                        and (part_fait is None or part_fait >= 0.5))
            non_attribues += not attribue
        detail[cle] = {"extraits": len(extraits), "extraits_retrouves": retrouves, "chiffres_absents": absents,
                       "chiffres_hors_extraits": hors_extraits, "url_retrouvee": url_retrouvee,
                       "part_fait_retrouvee": round(part_fait, 2) if part_fait is not None else None,
                       "attribue": attribue}
    return {"mots": len(dossier["mots"]), "non_attribues": non_attribues, "non_verifiables": non_verifiables,
            "detail": detail,
            "lecture": "diagnostic sans modèle ; un faux positif est possible quand la recherche résume au lieu de citer"}


def nature_etat_nul(categories: dict) -> str:
    """structure_absente : chaque candidate a été regardée et écartée sur pièces (contredit, marqueur non rempli) ;
    angle_mort : au moins une candidate n'a pas été vraiment cherchée ; indetermine : rejets non classés."""
    cats = set((categories or {}).values())
    if cats & set(ANGLES_MORTS):
        return "angle_mort"
    if cats and cats <= set(STRUCTURE_ABSENTE):
        return "structure_absente"
    return "indetermine"


async def relancer_angles_morts(q: Question, plan: dict, executees: list[dict], lecture: dict, llm: Llm,
                                chercher: Chercheur, recherche_reelle: bool, aujourdhui: str,
                                jours: int) -> tuple[dict, list[dict], dict | None]:
    """0.2.2 : un état nul n'est accepté qu'après une relance ciblée sur ses angles morts (une seule). Rend
    (lecture, recherches, trace de la relance ou None). La règle de postage ne change pas : si la relance ancre des
    cartes, le moteur juge comme d'habitude."""
    rejets, cats = rejets_moteur(lecture)
    mots = lecture.get("mots") or []
    cibles = {c: k for c, k in cats.items() if k in ANGLES_MORTS}
    if not RELANCE_ETAT_NUL or mots or not cibles:
        return lecture, executees, None
    relance = {"cibles": cibles}
    try:
        demande = extraire_json(await llm(consigne_relance(q, plan, cibles, executees, aujourdhui)))
        # Famille « observation » (seules familles admises par le moteur) ; l'origine est gardée dans « relance ».
        reqs = [{"famille": "observation", "relance": True, "cartes": r.get("cartes") or [], "requete": r.get("requete")}
                for r in (demande.get("recherches") or []) if isinstance(r, dict)]
    except Exception as e:
        return lecture, executees, dict(relance, echec=f"requêtes de relance illisibles : {e}")
    deja = {r["requete"].lower() for r in executees}
    reqs = [r for r in reqs if isinstance(r["requete"], str) and r["requete"].strip().lower() not in deja]
    nouvelles = await executer_requetes(reqs, chercher, recherche_reelle, MAX_RECHERCHES_RELANCE)
    relance["recherches"] = [{k: v for k, v in r.items() if k != "resultat"} for r in nouvelles]
    if not any(r.get("executee") for r in nouvelles):
        return lecture, executees, dict(relance, echec="aucune recherche de relance exécutée")
    toutes = executees + nouvelles
    try:
        relue = extraire_json(await llm(consigne_dossier(q, plan, toutes, aujourdhui, jours)))
    except Exception as e:
        return lecture, executees, dict(relance, echec=f"relecture illisible : {e}")
    relance["mots_apres"] = len(relue.get("mots") or [])
    return relue, toutes, relance


def consigne_correction(lecture: dict, erreur: str) -> str:
    return f"""Le moteur du skill a refusé cette lecture. Corrige-la sans inventer de fait, de source ni d'URL : si un
élément manque, descends l'intensité à f, ou retire le mot et motive-le dans rejets. Une lecture sans aucun mot (état
nul) est admise si rien ne tient.

ERREUR DU MOTEUR : {erreur}

LECTURE :
{json.dumps(lecture, ensure_ascii=False, indent=1)}

Rends UNIQUEMENT l'objet JSON corrigé, avec les clés : {", ".join(CLES_LECTURE)}."""


# --------------------------------------------------------------------------- assemblage

CLES_LECTURE = ("candidats", "contre_candidate", "rejets_classes", "mots", "liaisons", "questions")


def details_rejets(lecture: dict) -> dict:
    """0.4.0 : pour chaque candidate écartée, ce qu'aurait dit un fait suffisant et l'extrait le plus proche trouvé.
    Mesure qui départage « le modèle sait mais n'ancre pas » (écart d'exécution) et « la recherche n'a rien ramené »."""
    brut = lecture.get("rejets_classes") or {}
    if isinstance(brut, list):
        brut = {str(x.get("carte") or x.get("candidate") or f"?{i}"): x for i, x in enumerate(brut) if isinstance(x, dict)}
    if not isinstance(brut, dict):
        return {}
    return {k: {"fait_attendu": str(v.get("fait_attendu") or "")[:300] or None,
                "extrait_proche": str(v.get("extrait_proche") or "")[:400] or None}
            for k, v in brut.items() if isinstance(v, dict) and (v.get("fait_attendu") or v.get("extrait_proche"))}


def rejets_moteur(lecture: dict) -> tuple[dict, dict]:
    """(rejets au format du moteur : {carte: motif}, catégories : {carte: catégorie}). Un rejet non classé reste admis
    (catégorie « non_classe ») : le moteur ne lit que le motif."""
    brut = lecture.get("rejets_classes") or lecture.get("rejets") or {}
    if isinstance(brut, list):
        # 0.1.7 (passage du 2026-11-04) : le modèle rend parfois une liste [{"carte": …, "categorie": …, "motif": …}].
        brut = {str(x.get("carte") or x.get("candidate") or x.get("cle") or x.get("id") or f"?{i}"): x
                for i, x in enumerate(brut) if isinstance(x, dict)}
    if not isinstance(brut, dict):
        brut = {}
    rejets, cats = {}, {}
    for k, v in brut.items():
        if isinstance(v, dict):
            cat = v.get("categorie") if v.get("categorie") in CATEGORIES_REJET else "non_classe"
            rejets[k] = f"[{cat}] {v.get('motif') or ''}".strip()
        else:
            cat, rejets[k] = "non_classe", str(v)
        cats[k] = cat
    return rejets, cats
MAX_RECHERCHES_REFERENCE = int(os.environ.get("ALPHABET_MAX_RECHERCHES_REFERENCE", "3"))


def etat_depuis(mots: list[dict], aujourdhui: str, jours: int) -> str:
    noms = noms_cartes()
    corps = " + ".join(f"{noms.get(m['carte'], m['carte'])}@{m['strate']}[{m['intensite']}]" for m in mots)
    return f"[{aujourdhui} | {jours} jours] {corps}" if corps else ""


TEMPORALITES = ("generique", "programmee", "duree_de_vie")


def temporalite_de(plan: dict) -> str:
    """0.2.0 (audit, B11) : la temporalité est déclarée par le plan ; « programmee » (échéance fixée d'avance) ou
    « duree_de_vie » rendent le moteur « non estimé » sans référence propre, comme le veut le skill."""
    t_ = plan.get("temporalite")
    return t_ if t_ in TEMPORALITES else "generique"


def evenement_depuis(plan: dict, vue: dict) -> tuple[dict, str]:
    """La partie « événement » du dossier, construite par le bot : une correction ne peut pas l'effacer."""
    noms = noms_cartes()
    ev = plan["evenement"]
    evenement = f"{noms.get(ev['carte'], ev['carte'])}@{ev['strate']} {ev['type']}"
    champs = ("frequence", "classe_de_reference", "source", "periode", "disponible_le", "classe_alternative",
              "motif_sans_alternative", "ecart_critere")
    ve = {k: vue.get(k) for k in champs if vue.get(k) is not None or k == "classe_alternative"}
    if ve.get("classe_alternative") is None:
        ve["motif_sans_alternative"] = (vue.get("motif_sans_alternative")
                                        or "non fourni par le modèle (champ vide ; inscrit par le bot, 0.2.0)")
    return {"evenement": evenement, "semantique": plan["semantique"], "temporalite": temporalite_de(plan),
            "resolution": vue.get("resolution") or "", "source_resolution": vue.get("source_resolution") or {},
            "vue_exterieure": ve}, evenement


def donnees_puits(plan: dict) -> str:
    """0.7.0 : les relevés des bases ouvertes, citables comme source d'un fait (avec leur URL)."""
    t = plan.get("_donnees")
    return ("\nDONNÉES DATÉES DES BASES OUVERTES (citables comme source d'un fait, avec leur nom et leur URL ; "
            "aucun nombre ne s'invente à partir d'elles) :\n" + t + "\n") if t else ""


def consigne_puits(q: Question, plan: dict, aujourdhui: str, jours: int, catalogue: str) -> str:
    return f"""Étape 1b : les BASES DE DONNÉES OUVERTES. Choisis au plus {MAX_APPELS_PUITS} appels dans le catalogue
ci-dessous, et seulement ceux qui mesurent ce que demande la question ou son contexte. Aucun appel est une réponse
admise : rends alors "appels": [].

QUESTION : {q.titre}
CRITÈRES DE RÉSOLUTION : {q.criteres}
PRÉCISIONS : {q.precisions}
DATE D'INFORMATION : {aujourdhui} ; fenêtre : {jours} jours (jusqu'au {q.resolution.isoformat()}).
ÉVÉNEMENT DU PLAN : {json.dumps(plan.get("evenement"), ensure_ascii=False)}

CATALOGUE (source : usage ; paramètres) :
{catalogue}

Le COMPTE (facultatif) sert le taux de base : le code comptera lui-même, sur un appel « comptable », combien de
fenêtres de {jours} jours ont vu la condition remplie. Propose-le dès qu'une série mesure la grandeur du critère de
résolution OU une grandeur proche (autre pays, autre mesure de la même chose, série plus large qui la contient), et
déclare honnêtement la correspondance : "exacte" (même grandeur, même source ou équivalente) ou "proche" (une grandeur
voisine : dis l'écart dans "ecart_critere"). Le seuil se prend dans le critère (converti dans l'unité de la série si
besoin, en le disant), jamais ailleurs. Modes : "evenement" (au moins un
événement dans la fenêtre, éventuellement filtré par le seuil), "atteint" (au moins une valeur remplit la condition),
"franchit" (la condition n'était pas remplie au début de la fenêtre et l'est ensuite). "agregation" : "mois" ou
"annee" pour sommer d'abord les valeurs (morts par mois, par exemple), sinon null.

Rends UNIQUEMENT un objet JSON :
{{
 "appels": [{{"source": "nom du catalogue", "params": {{...}}, "pourquoi": "ce que l'appel mesure ici"}}],
 "compte": null ou {{"appel": indice (0 pour le premier appel), "mode": "evenement|atteint|franchit",
     "seuil": nombre ou null, "sens": ">=|>|<=|<", "agregation": null | "mois" | "annee",
     "correspondance": "exacte|proche",
     "classe_de_reference": "les fenêtres comptées, sans nom de carte",
     "ecart_critere": "en quoi ce compte diffère du critère de résolution, ou « identique : … »",
     "resolution": "ce qui fera dire OUI, en une phrase",
     "source_resolution": {{"emetteur": "…", "document": "…", "regle_ambiguite": "…"}}}}
}}"""


async def puits(q: Question, plan: dict, llm: Llm, aujourdhui: str, jours: int,
                rang_premier: int) -> tuple[dict, list[dict], dict | None]:
    """0.7.0 : appels aux bases ouvertes, bornés à la date d'information. Rend (trace, résultats à joindre aux
    recherches du taux de base, vue calculée ou None). Le texte des relevés est aussi gardé dans plan["_donnees"]
    pour la lecture. `rang_premier` : numéro [Rn] du premier relevé dans la consigne de la vue extérieure."""
    import alphabet_puits as apz
    cat = apz.catalogue_texte()
    trace: dict = {"appels": [], "compte": None}
    try:
        demande = extraire_json(await llm(consigne_puits(q, plan, aujourdhui, jours, cat)))
    except Exception as e:
        return dict(trace, erreur=f"plan des données illisible : {e}"[:200]), [], None
    avant = date.fromisoformat(aujourdhui)
    resultats, releves = [], {}
    for i, a in enumerate([x for x in (demande.get("appels") or []) if isinstance(x, dict)][:MAX_APPELS_PUITS]):
        src, params = str(a.get("source") or ""), a.get("params") if isinstance(a.get("params"), dict) else {}
        journal = {"source": src, "params": params}
        try:
            r = await apz.appeler(src, params, avant)
        except apz.SansCle as e:
            trace["appels"].append(dict(journal, statut="sans_cle", motif=str(e)))
            continue
        except Exception as e:
            trace["appels"].append(dict(journal, statut="echec", motif=f"{type(e).__name__}: {e}"[:200]))
            continue
        if not r["points"]:
            trace["appels"].append(dict(journal, statut="vide"))
            continue
        releves[i] = (r, rang_premier + len(resultats), src)
        trace["appels"].append(dict(journal, statut="ok", points=len(r["points"]), url=r["url"],
                                    premier=r["points"][0]["date"], dernier=r["points"][-1]["date"]))
        resultats.append({"famille": "reference", "cartes": [], "requete": f"puits : {src} {json.dumps(params, ensure_ascii=False)}",
                          "resultat": apz.texte_releve(r), "executee": True, "moteur": f"puits-{src}"})
    plan["_donnees"] = "\n\n".join(x["resultat"] for x in resultats)
    spec, vue = demande.get("compte"), None
    if isinstance(spec, dict) and isinstance(spec.get("appel"), int) and spec["appel"] in releves:
        r, rang, src = releves[spec["appel"]]
        if not apz.CATALOGUE[src]["comptable"]:
            trace["compte"] = {"spec": spec, "motif": f"{src} n'est pas comptable"}
        else:
            seuil = spec.get("seuil")
            seuil = float(seuil) if isinstance(seuil, (int, float)) and not isinstance(seuil, bool) else None
            res = apz.compter(r, jours, str(spec.get("mode") or "atteint"), seuil, str(spec.get("sens") or ">="),
                              spec.get("agregation"), fin=avant, nature=apz.CATALOGUE[src].get("nature"))
            trace["compte"] = {"spec": spec, **res}
            if res.get("frequence") is not None:
                a0, a1 = res["periode"][:4], res["periode"][11:15]
                vue = {"frequence": res["frequence"],
                       "classe_de_reference": spec.get("classe_de_reference") or f"fenêtres de {jours} jours ({r['titre']})",
                       "source": f"{r['source']} — {r['titre']} ({r['url']})",
                       "fondement": f"[R{rang}] compte calculé par le code (puits de données)",
                       "periode": f"{a0}-{a1}", "disponible_le": res["dernier_point"],
                       "calcul": (f"{res['k']} fenêtre(s) sur {res['n']} de {jours} jours, disjointes, mode {res['mode']}"
                                  + (f", seuil {res['sens']} {res['seuil']:g}" if res.get("seuil") is not None else "")
                                  + (f", agrégation par {res['agregation']}" if res.get("agregation") else "")),
                       "classe_alternative": None,
                       "motif_sans_alternative": "compte calculé sur une seule série du catalogue ; pas de seconde classe",
                       "ecart_critere": spec.get("ecart_critere") or "non précisé",
                       "resolution": spec.get("resolution") or "", "source_resolution": spec.get("source_resolution") or {},
                       "compte_calcule": True,
                       "correspondance": "exacte" if spec.get("correspondance") == "exacte" else "proche"}
    elif spec is not None:
        trace["compte"] = {"spec": spec, "motif": "appel du compte absent ou en échec"}
    return trace, resultats, vue


def assembler(lecture: dict, plan: dict, executees: list[dict], evt: dict, aujourdhui: str, jours: int) -> dict:
    d = {k: lecture.get(k, []) for k in ("candidats", "contre_candidate", "mots", "liaisons", "questions")}
    d["rejets"], d["_categories_rejet"] = rejets_moteur(lecture)
    d["_details_rejet"] = details_rejets(lecture)
    d["etat"] = etat_depuis(d.get("mots") or [], aujourdhui, jours)
    d["disponible_le"] = aujourdhui
    d["recherches"] = [{"famille": r["famille"], "cartes": r["cartes"], "requete": r["requete"],
                        "executee": r["executee"], **({"date_execution": aujourdhui} if r["executee"] else {})}
                       for r in executees]
    d["evenements"] = [evt]
    return d


def controle_plan(plan: dict) -> str | None:
    ev = plan.get("evenement")
    if not ev:
        return plan.get("pourquoi_evenement") or "aucun événement de carte ne correspond au OUI de la question"
    if ev.get("carte") not in noms_cartes():
        return f"carte inconnue : {ev.get('carte')}"
    if ev.get("type") not in TYPES:
        return f"type d'événement non pris en charge : {ev.get('type')}"
    if plan.get("semantique") not in SEMANTIQUES[ev["type"]]:
        return f"sémantique {plan.get('semantique')} incompatible avec {ev['type']}"
    if ev["type"] == "apparait":
        src = {a for a, _ in sources_matrice(ev["carte"])}
        cand = {str(c).split("@")[0] for c in plan.get("candidats", [])}
        if len(cand & src) < MIN_SOURCES:
            return (f"candidates : au moins {MIN_SOURCES} parmi les cartes qui agissent sur {ev['carte']} selon la matrice "
                    f"({', '.join(a for a, _ in sources_matrice(ev['carte']))}) ; reçu : {', '.join(sorted(cand)) or 'aucune'}")
        if ev["carte"] in cand:
            return f"la carte visée {ev['carte']} ne peut pas être candidate d'un événement « apparait »"
    return None


def plan_corrigeable(motif: str) -> bool:
    return motif.startswith("candidates :") or motif.startswith("la carte visée")


def controle_vue(vue: dict, aujourdhui: str | None = None) -> str | None:
    f = vue.get("frequence")
    if not isinstance(f, (int, float)) or isinstance(f, bool) or not 0 < f < 1:
        return vue.get("motif") or "vue extérieure sans fréquence"
    for k in ("classe_de_reference", "source", "periode", "disponible_le"):
        if not vue.get(k):
            return f"vue extérieure incomplète : {k} manquant"
    # 0.4.0 : une source qui se déclare elle-même de mémoire n'est pas une source (règle de sourçage).
    declaree = f"{vue.get('source', '')} {vue.get('fondement', '')}"
    if re.search(r"registre mental|mental regist|sans consultation|without (?:online )?consult|from memory|"
                 r"de m[ée]moire|general knowledge|connaissances? g[ée]n[ée]rales?", declaree, re.I):
        return "vue extérieure : source déclarée de mémoire, non vérifiable"
    if aujourdhui:  # 0.2.0 (audit, B6) : une source postérieure à la date d'information ne fonde pas un taux de base
        d = str(vue["disponible_le"])[:10]
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", d):
            return f"vue extérieure : disponible_le illisible ({vue['disponible_le']})"
        if d > aujourdhui:
            return f"vue extérieure : disponible_le {d} postérieur à la date d'information {aujourdhui}"
    return controle_calcul(vue)


ECART_CALCUL = 0.20     # 0.8.0 (audit M-07) : écart relatif admis entre la fréquence déclarée et son expression


def evaluer_expression(expr: str) -> float:
    """Évalue SANS eval() une expression arithmétique (nombres, + - * / **, parenthèses)."""
    import ast
    import operator as op
    ops = {ast.Add: op.add, ast.Sub: op.sub, ast.Mult: op.mul, ast.Div: op.truediv, ast.Pow: op.pow}

    def ev(n):
        if isinstance(n, ast.Expression):
            return ev(n.body)
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)) and not isinstance(n.value, bool):
            return float(n.value)
        if isinstance(n, ast.UnaryOp) and isinstance(n.op, (ast.USub, ast.UAdd)):
            v = ev(n.operand)
            return -v if isinstance(n.op, ast.USub) else v
        if isinstance(n, ast.BinOp) and type(n.op) in ops:
            a, b = ev(n.left), ev(n.right)
            if isinstance(n.op, ast.Pow) and abs(b) > 1e4:
                raise ValueError("exposant trop grand")
            return ops[type(n.op)](a, b)
        raise ValueError(f"élément non admis : {type(n).__name__}")
    texte = str(expr).replace("×", "*").replace("^", "**").replace("−", "-").replace(",", ".")
    return float(ev(ast.parse(texte, mode="eval")))


def controle_calcul(vue: dict) -> str | None:
    """0.8.0 (audit M-07) : l'arithmétique du taux de base est REFAITE par le code. La vue rend « expression » (ex.
    « 1 - (1 - 3/40) ** (120/365) ») ; la fréquence retenue est TOUJOURS celle de l'expression (0.8.1) ; un écart de
    plus de 20 % avec la fréquence déclarée est marqué « calcul_corrige ». Une expression absente ou illisible fait
    refuser la vue. Une vue calculée par le code (compte des puits) est exemptée."""
    if vue.get("compte_calcule"):
        return None
    expr = vue.get("expression")
    if not expr:
        return "vue extérieure : calcul sans expression reproductible"
    try:
        f = evaluer_expression(expr)
    except (ValueError, SyntaxError, ZeroDivisionError, OverflowError, TypeError) as e:
        return f"vue extérieure : expression illisible ({type(e).__name__})"
    d = float(vue["frequence"])
    if not 0 < f < 1:
        return f"vue extérieure : l'expression donne {f:.4g}, hors de ]0, 1["
    # 0.8.1 : passage réel 42489373511, les trois vues de 43329 refusées pour une erreur d'ARITHMÉTIQUE (le modèle écrit
    # la bonne formule et se trompe en la calculant). La formule est le raisonnement explicite ; le chiffre déclaré, un
    # calcul de tête. On retient donc la valeur de la formule, et l'écart est scellé (« calcul_corrige »).
    vue["frequence_declaree"], vue["frequence"] = d, f
    vue["calcul_corrige"] = abs(f - d) > ECART_CALCUL * max(f, d)
    return None


def fondement_memoire(vue: dict) -> bool:
    """La vue s'appuie-t-elle sur un registre cité de mémoire plutôt que sur un résultat de recherche [Rn] ?"""
    return not re.search(r"\[[RM]\d+\]", f"{vue.get('fondement', '')} {vue.get('calcul', '')} {vue.get('source', '')}")


def controle_etat(dossier: dict, plan: dict) -> str | None:
    ev = plan["evenement"]
    present = any(m["carte"] == ev["carte"] and int(m["strate"]) == int(ev["strate"]) for m in dossier.get("mots", []))
    if ev["type"] == "apparait" and present:
        return "événement « apparait » sur une carte déjà présente dans l'état : retirer ce mot ou changer d'événement"
    if ev["type"] != "apparait" and dossier.get("mots") and not present:
        return f"événement « {ev['type']} » sur une carte absente de l'état"
    return None


async def executer_requetes(requetes: list[dict], chercher: Chercheur, recherche_reelle: bool, plafond: int) -> list[dict]:
    vues, sortie = set(), []
    for r in requetes:
        req = (r.get("requete") or "").strip()
        if not req or req.lower() in vues:
            continue
        vues.add(req.lower())
        if sum(1 for x in sortie if not x.get("non_lancee")) >= plafond:
            # 0.2.0 (audit, B10) : une requête coupée par le plafond est consignée, non lancée, avec son motif ; une
            # candidate qui n'a pas été cherchée ne doit pas passer pour « aucun_fait ».
            sortie.append({"famille": r.get("famille", "reference"), "cartes": r.get("cartes", []), "requete": req,
                           **({"relance": True} if r.get("relance") else {}),
                           "resultat": "", "executee": False, "non_lancee": "plafond"})
            continue
        try:
            texte = await chercher(req)
        except Exception as e:  # une recherche qui échoue est consignée, non lancée
            texte, ok = f"(échec : {e})", False
        else:
            ok = recherche_reelle
        moteur = re.match(r"\[moteur : ([\w-]+)\]", texte or "")   # 0.6.1 : quel moteur a servi la requête
        sortie.append({"famille": r.get("famille", "reference"), "cartes": r.get("cartes", []), "requete": req,
                           **({"relance": True} if r.get("relance") else {}),
                       **({"moteur": moteur.group(1)} if moteur else {}),
                       "resultat": texte or "", "executee": ok})
    return sortie


async def executer_recherches(plan: dict, chercher: Chercheur, recherche_reelle: bool) -> list[dict]:
    return await executer_requetes([r for r in plan.get("recherches", []) if r.get("famille") in FAMILLES],
                                   chercher, recherche_reelle, MAX_RECHERCHES)


async def chercher_historique(plan: dict, historique: Historique | None, aujourdhui: str) -> tuple[list[dict], dict]:
    """Questions résolues comparables (issues seules), dédoublonnées, résolues AVANT la date d'information."""
    cles = [x for x in (plan.get("recherches_historique") or []) if isinstance(x, str) and x.strip()][:4]
    if historique is None or not cles:
        return [], {"cles": cles, "trouvees": 0}
    try:
        brut = await historique(cles, aujourdhui)
    except Exception as e:
        return [], {"cles": cles, "trouvees": 0, "erreur": f"{type(e).__name__}: {e}"[:200]}
    vus, garde = set(), []
    for h in brut:
        issue = str(h.get("issue") or "").lower()
        if issue not in ("yes", "no") or h.get("titre") in vus or str(h.get("resolue_le") or "9999")[:10] >= aujourdhui:
            continue
        vus.add(h.get("titre"))
        garde.append({"titre": h["titre"], "issue": issue, "resolue_le": str(h.get("resolue_le") or "")[:10]})
    return garde[:MAX_HISTORIQUE], {"cles": cles, "trouvees": len(garde[:MAX_HISTORIQUE])}


def consigne_classe(q: Question, plan: dict, references: list[dict], aujourdhui: str, jours: int,
                    historique: list[dict] | None = None) -> str:
    """0.4.0 : la classe de référence est DÉFINIE une fois, avant tout comptage : trois vues qui comptent trois
    classes différentes ne donnent pas une médiane, mais un tirage (constat du registre : facteur 5 à 10 sur B)."""
    res = "\n\n".join(f"[R{i + 1}] « {r['requete']} »\n{r['resultat'][:2000]}" for i, r in enumerate(references))
    hist = "\n".join(f"[M{i + 1}] {h['titre']} → {str(h['issue']).upper()}" for i, h in enumerate(historique or []))
    return f"""Étape 2a : DÉFINIR la classe de référence (sans encore compter). Elle ne doit pas être choisie d'après l'état
présent de la situation, mais d'après le TYPE d'événement que demande la question.

QUESTION : {q.titre}
CRITÈRES DE RÉSOLUTION : {q.criteres}
FENÊTRE : {jours} jours (du {aujourdhui} au {q.resolution.isoformat()}).

RÉSULTATS DES RECHERCHES SUR LE TAUX DE BASE :
{res or "(aucun)"}

QUESTIONS DÉJÀ RÉSOLUES, d'apparence voisine (issue seulement) :
{hist or "(aucune)"}

Rends UNIQUEMENT un objet JSON :
{{
 "classe_de_reference": "les cas comptés, dans le vocabulaire de la source, SANS aucun nom de carte de l'alphabet",
 "unite": "ce qui compte pour UN cas (et ce qui n'en est pas un)",
 "population": "sur quoi on compte : quels acteurs ou quelles périodes forment le dénominateur",
 "periode": "AAAA-AAAA",
 "mise_a_l_echelle": "comment passer de la période à une fenêtre de {jours} jours",
 "sources_visees": "où se trouvent les cas : [Rn], [Mn] ou registre nommé"
}}"""


async def definir_classe(q: Question, plan: dict, refs: list[dict], hist: list[dict], llm: Llm, aujourdhui: str,
                         jours: int) -> dict | None:
    try:
        c = extraire_json(await llm(consigne_classe(q, plan, refs, aujourdhui, jours, hist)))
    except Exception:
        return None
    return c if isinstance(c, dict) and c.get("classe_de_reference") and c.get("unite") else None


async def vues_exterieures(q: Question, plan: dict, refs: list[dict], hist: list[dict], llm: Llm, aujourdhui: str,
                           jours: int, classe: dict | None = None,
                           vue_calculee: dict | None = None, ancrage: dict | None = None) -> tuple[dict | None, dict]:
    """0.3.0 : NB_VUES estimations indépendantes du taux de base ; on garde la vue MÉDIANE (une vraie vue, avec sa
    source : aucun chiffre n'est fabriqué par moyenne). La dispersion est journalisée : c'est la mesure de stabilité
    de B demandée avant toute autre décision sur B."""
    # 0.8.0 (audit M-01) : chaque vue sur une source différente des précédentes. (M-03) : un compte « proche » n'ancre
    # que la PREMIÈRE vue ; les autres restent aveugles, ce qui garde une mesure de B indépendante du compte.
    valides, refus, sources = [], [], []
    for i in range(NB_VUES):
        anc = ancrage if i == 0 else None
        try:
            v = extraire_json(await llm(consigne_vue(q, plan, refs, aujourdhui, jours, hist, classe, anc, sources)))
        except Exception as e:
            refus.append(f"illisible : {e}"[:200])
            continue
        m = controle_vue(v, aujourdhui) or controle_references(v, len(refs), len(hist or [])) or source_reprise(v, sources)
        if m:
            refus.append(m)
            continue
        v["_ancree"] = anc is not None
        valides.append(v)
        sources.append(str(v.get("source"))[:200])
    calc = None
    if vue_calculee is not None:
        m = controle_vue(vue_calculee, aujourdhui)
        calc = {"frequence": vue_calculee.get("frequence"), "refus": m}
    freqs = sorted(float(v["frequence"]) for v in valides)

    def mediane(vs):
        vs = sorted(vs, key=lambda v: float(v["frequence"]))
        return vs[(len(vs) - 1) // 2] if vs else None     # médiane basse si nombre pair
    aveugles = [v for v in valides if not v["_ancree"]]
    suivi = {"demandees": NB_VUES, "valides": len(valides), "frequences": freqs, "refus": refus,
             "dispersion": (freqs[-1] - freqs[0]) if len(freqs) > 1 else None,
             "dispersion_nulle": len(freqs) > 1 and freqs[-1] == freqs[0],
             "sources": sources, "vue_calculee": calc,
             **({"usages_compte": [v.get("usage_compte") for v in valides if v["_ancree"]],
                 "p_sans_ancre": float(mediane(aveugles)["frequence"]) if aveugles else None} if ancrage else {})}
    choisie = mediane(valides)
    if vue_calculee is not None and not calc["refus"]:
        # 0.8.0 (audit M-02) : un compte EXACT ne se glisse plus dans une médiane de vues d'une autre nature : il EST
        # le taux de base (calculé par le code sur la grandeur même du critère). La médiane du modèle reste en ombre.
        suivi["p_modele"] = float(choisie["frequence"]) if choisie else None
        choisie = vue_calculee
    for v in valides:
        v.pop("_ancree", None)
    return choisie, suivi


async def alphabet(q: Question, recherche: str, llm: Llm, chercher: Chercheur, recherche_reelle: bool,
                   aujourdhui: str, jours: int, historique: Historique | None = None,
                   critique: Llm | None = None) -> dict:
    """0.9.0 : hors strate 7, la lecture exploratoire est rangée dans « exploratoire » et le statut reste
    « hors_strate » : la règle de publication ne voit rien (A posté, jamais B ni C), le registre garde tout."""
    c = await _alphabet(q, recherche, llm, chercher, recherche_reelle, aujourdhui, jours, historique, critique)
    try:
        c["symetrique"] = symetrique(c)        # 0.9.1 : en ombre, partout où c'est calculable
    except Exception as e:
        c["symetrique"] = {"erreur": f"{type(e).__name__}: {e}"[:200]}
    if not c.pop("_explo", False):
        return c
    strate = ((c.get("plan") or {}).get("evenement") or {}).get("strate")
    explo = {k: c.get(k) for k in ("statut", "p_C", "p_sans_cartes", "motif", "nature_etat_nul", "rho", "tentatives",
                                   "etat", "drapeaux") if c.get(k) is not None}
    explo["strate"] = strate
    explo["p_C_corrige"] = corriger_C(explo.get("p_C"), correction_retro())   # 0.9.1 : la correction en ombre aussi
    explo["p_C_symetrique"] = (c.get("symetrique") or {}).get("p")
    for k in ("p_C", "p_sans_cartes", "rho", "nature_etat_nul"):
        c.pop(k, None)
    c.update(statut="hors_strate", exploratoire=explo,
             motif=f"strate {strate} non chiffrée (L7) : lecture exploratoire scellée, non postée "
                   f"({explo.get('statut')})")
    return c


async def _alphabet(q: Question, recherche: str, llm: Llm, chercher: Chercheur, recherche_reelle: bool,
                    aujourdhui: str, jours: int, historique: Historique | None = None,
                    critique: Llm | None = None) -> dict:
    """Bras B et C. statut : estime | etat_nul | non_estime | refuse | sans_vue | hors_alphabet | hors_strate
    | lu_non_chiffre (et « erreur », posé par prevoir_binaire si une exception échappe)."""
    trace: dict = {"statut": "refuse", "tentatives": 0}
    try:
        plan = extraire_json(await llm(consigne_plan(q, recherche, aujourdhui)))
    except Exception as e:
        return dict(trace, motif=f"plan illisible : {e}")
    motif = controle_plan(plan)
    # 0.8.0 (audit M-12, m-03) : jusqu'à deux corrections du plan (le refus du plan était la seule cause de refus
    # observée en 0.7.x), comptées dans « reprises_plan ».
    trace["reprises_plan"] = 0
    while motif and plan_corrigeable(motif) and trace["reprises_plan"] < 2:
        trace["reprises_plan"] += 1
        try:
            plan = extraire_json(await llm(consigne_plan(q, recherche, aujourdhui)
                                           + f"\n\nTON PLAN PRÉCÉDENT A ÉTÉ REFUSÉ : {motif}\nPLAN REFUSÉ : "
                                           + json.dumps(plan, ensure_ascii=False)))
        except Exception as e:
            return dict(trace, plan=plan, motif=f"plan corrigé illisible : {e}")
        motif = controle_plan(plan)
    trace["plan"] = plan
    if motif:
        return dict(trace, statut="refuse" if plan_corrigeable(motif) else "hors_alphabet", motif=motif)

    # 1. Vue extérieure d'abord, sur ses propres recherches (bras B).
    refs = await executer_requetes([{"requete": x} for x in (plan.get("recherches_reference") or []) if isinstance(x, str)],
                                   chercher, recherche_reelle, MAX_RECHERCHES_REFERENCE)
    trace["recherches_reference"] = [{k: v for k, v in r.items() if k != "resultat"} for r in refs]
    vue_calc = None
    if PUITS:                        # 0.7.0 : bases ouvertes, bornées à la date d'information
        trace["puits"], donnees, vue_calc = await puits(q, plan, llm, aujourdhui, jours, len(refs) + 1)
        refs = refs + donnees
    hist, trace["historique"] = await chercher_historique(plan, historique, aujourdhui)
    classe = await definir_classe(q, plan, refs, hist, llm, aujourdhui, jours) if CLASSE_FIGEE else None
    trace["classe"] = classe
    # 0.4.1 : distinguer au registre « classe figée », « échec de la définition » et « étape désactivée ».
    trace["classe_statut"] = "desactivee" if not CLASSE_FIGEE else ("figee" if classe else "echec")
    # 0.7.2 : un compte « exact » rejoint les vues ; un compte « proche » les ancre, et reste scellé en ombre (p_compte).
    ancrage = None
    if vue_calc is not None:
        trace["p_compte"], trace["correspondance"] = vue_calc["frequence"], vue_calc["correspondance"]
        if vue_calc["correspondance"] != "exacte":
            ancrage, vue_calc = vue_calc, None
    vue, trace["vues"] = await vues_exterieures(q, plan, refs, hist, llm, aujourdhui, jours, classe, vue_calc, ancrage)
    if vue is None:
        refus = trace["vues"]["refus"]
        return dict(trace, statut="sans_vue", motif=(refus[0] if refus else "vue extérieure absente"))
    trace["vue"] = vue
    trace["p_B"] = float(vue["frequence"])
    evt, evenement = evenement_depuis(plan, vue)
    hors_strate = int(plan["evenement"]["strate"]) not in strates_chiffrees()
    if hors_strate and EXPLORATOIRE:
        trace["_explo"] = True
    if hors_strate and not (LECTURE_HORS_STRATE or EXPLORATOIRE):
        return dict(trace, statut="hors_strate", evenement=evenement, semantique=plan["semantique"],
                    motif=f"strate {plan['evenement']['strate']} non chiffrée (L7 : {strates_chiffrees()}) ; "
                          "vue extérieure enregistrée, lecture non lancée")

    # 2. Lecture (bras C).
    executees = await executer_recherches(plan, chercher, recherche_reelle)
    trace["recherches"] = [{k: v for k, v in r.items() if k != "resultat"} for r in executees]
    try:
        lecture = extraire_json(await llm(consigne_dossier(q, plan, executees, aujourdhui, jours)))
    except Exception as e:
        return dict(trace, motif=f"lecture illisible : {e}")
    lecture, executees, relance = await relancer_angles_morts(q, plan, executees, lecture, llm, chercher,
                                                              recherche_reelle, aujourdhui, jours)
    # 0.5.2 : le texte des résultats, gardé hors registre pour le contrôle d'attribution (controle_attribution).
    trace["_textes"] = "\n".join(str(r.get("resultat") or "") for r in executees if r.get("executee")) + (
        "\n" + plan["_donnees"] if plan.get("_donnees") else "")
    if relance:
        trace["relance"] = relance
        trace["recherches"] = [{k: v for k, v in r.items() if k != "resultat"} for r in executees]
    dossier = None
    for tentative in range(MAX_CORRECTIONS + 1):
        trace["tentatives"] = tentative + 1
        dossier = assembler(lecture, plan, executees, evt, aujourdhui, jours)
        if not dossier["mots"]:
            # État nul : aucune carte ancrée. Le moteur ne calcule pas un état vide ; sans carte, pas d'ajustement :
            # le bot postera le taux de base (bras B).
            nature = nature_etat_nul(dossier.get("_categories_rejet"))
            trace.update(dossier=dossier, statut="etat_nul", nature_etat_nul=nature, evenement=evenement,
                         dynamique_observee=dynamique_observee(lecture),
                         semantique=plan["semantique"],
                         motif=f"aucune carte ancrée ({nature.replace('_', ' ')}) : pas d'ajustement du taux de base")
            return trace
        erreur = controle_etat(dossier, plan)
        if not erreur and hors_strate and not EXPLORATOIRE:
            # Lecture scellée, non chiffrée (mode LIRE ; validation.md §27) : chiffrable après une levée de L7.
            trace.update(dossier=dossier, etat=dossier["etat"], evenement=evenement, semantique=plan["semantique"],
                         statut="lu_non_chiffre",
                         motif=f"strate {plan['evenement']['strate']} non chiffrée (L7) : lecture scellée sans chiffre")
            return trace
        sortie = None
        if not erreur:
            sortie = appeler_moteur({k: v for k, v in dossier.items() if not k.startswith("_")}, dossier["etat"],
                                    evenement, plan["semantique"], aujourdhui, evt["vue_exterieure"], evt["temporalite"],
                                    exploratoire=hors_strate)
            erreur = sortie.get("erreur")
        if not erreur:
            trace.update(dossier=dossier, etat=dossier["etat"], evenement=evenement, semantique=plan["semantique"],
                         p_C=sortie.get("p"), p_sans_cartes=sortie.get("p_sans_cartes"),
                         drapeaux=sortie.get("drapeaux", []), rho=sortie.get("rho"))
            trace["statut"] = "estime" if sortie.get("p") is not None else "non_estime"
            if sortie.get("p") is None:
                trace["motif"] = next((x for x in sortie.get("drapeaux", []) if x.startswith("Non estimé")), "non estimé")
            if critique is not None and trace["statut"] == "estime":   # 0.6.0 : contradicteur, en ombre
                cr = await critiquer(q, dossier, trace.get("_textes"), critique, evenement, plan["semantique"],
                                     aujourdhui, jours, evt, trace.get("p_B"))
                trace["critique"] = dict(cr, modele=(modeles_actifs() or {}).get("contradicteur"))
            return trace
        trace["derniere_erreur"] = erreur
        if tentative == MAX_CORRECTIONS or any(x in erreur for x in ERREURS_STRUCTURELLES):
            break
        try:
            lecture = extraire_json(await llm(consigne_correction(
                {k: dossier[k] for k in CLES_LECTURE if k in dossier}
                | {"rejets_classes": {c: {"categorie": dossier["_categories_rejet"].get(c), "motif": m}
                                      for c, m in dossier["rejets"].items()}}, erreur)))
        except Exception as e:
            trace["derniere_erreur"] = f"correction illisible : {e}"
            break
    trace["dossier"] = dossier
    trace["motif"] = trace.get("derniere_erreur")
    return trace


def consigne_critique(q: Question, dossier: dict, textes: str) -> str:
    """0.6.0 : le contradicteur, d'une autre famille de modèle que le lecteur. Il ne peut que CONTESTER : maintenir,
    affaiblir (F → f) ou retirer une carte ancrée. Il n'ajoute rien, ne renforce rien, ne donne aucun chiffre :
    le moteur reste juge et recalcule."""
    mots = [{k: m.get(k) for k in ("carte", "strate", "intensite", "fait", "source", "test", "corroboration",
                                   "contre_observation", "passage")} for m in dossier.get("mots") or []]
    return f"""Tu es le CONTRADICTEUR d'une lecture structurelle. Une autre IA a ancré les cartes ci-dessous dans des
faits. Ton seul travail : vérifier chaque ancrage contre les RÉSULTATS DE RECHERCHE, et le contester s'il ne tient pas.

QUESTION : {q.titre}

CARTES ANCRÉES (intensité F = fait suffisant, test « pistolet » ou « double » ; f = fait qui remplit seulement le
marqueur, test « cerceau ») :
{json.dumps(mots, ensure_ascii=False, indent=1)[:12000]}

RÉSULTATS DE RECHERCHE (seule base admise) :
{(textes or "(aucun)")[:14000]}

Pour chaque carte, décide :
- "maintenir" : le fait figure dans les résultats, daté, et il porte bien l'intensité déclarée ;
- "affaiblir" : le fait figure, mais il n'est pas suffisant (on l'observerait aussi sans la structure) : F devient f ;
- "retirer" : le fait ne figure pas dans les résultats, ou il est contredit, ou il ne remplit pas le marqueur.
Tu ne peux NI ajouter une carte, NI renforcer une intensité, NI donner une probabilité. Dans le doute, maintiens.

Rends UNIQUEMENT un objet JSON :
{{"verdicts": {{"CARTE@strate": {{"decision": "maintenir|affaiblir|retirer", "motif": "une phrase, avec [n] si un
résultat le justifie"}}}}}}"""


async def critiquer(q: Question, dossier: dict, textes: str, critique: Llm, evenement: str, semantique: str,
                    aujourdhui: str, jours: int, evt: dict, p_B: float | None) -> dict:
    """Applique les verdicts du contradicteur à une COPIE du dossier et refait calculer le moteur. En ombre : rien de
    ce qui est posté ne change. Statuts : estime, etat_nul (toutes les cartes retirées : la règle donnerait B),
    inchange, refuse (le moteur refuse le dossier contesté), illisible."""
    import copy
    try:
        brut = extraire_json(await critique(consigne_critique(q, dossier, textes)))
        verdicts = brut.get("verdicts") or {}
        if not isinstance(verdicts, dict):
            raise ValueError("verdicts absents")
    except Exception as e:
        return {"statut": "illisible", "motif": f"{type(e).__name__}: {e}"[:200]}
    d = copy.deepcopy({k: v for k, v in dossier.items() if not k.startswith("_")})
    mots, retires, affaiblis = [], [], []
    for m in d.get("mots") or []:
        cle = f"{m.get('carte')}@{m.get('strate')}"
        dec = str((verdicts.get(cle) or {}).get("decision") or "maintenir").lower()
        if dec == "retirer":
            retires.append(cle)
            d.setdefault("rejets", {})[cle] = "[contredit] retiré par le contradicteur : " + str(
                (verdicts.get(cle) or {}).get("motif") or "")[:300]
            continue
        if dec == "affaiblir" and m.get("intensite") == "F":
            m["intensite"], m["test"] = "f", "cerceau"
            affaiblis.append(cle)
        mots.append(m)
    sortie_ = {"verdicts": {k: v for k, v in verdicts.items() if isinstance(v, dict)}, "retires": retires,
               "affaiblis": affaiblis}
    if not retires and not affaiblis:
        return dict(sortie_, statut="inchange")
    if not mots:
        return dict(sortie_, statut="etat_nul", p_C_critique=p_B)
    d["mots"] = mots
    # Une liaison qui touche une carte retirée n'a plus d'objet ; une question ne garde son objet que si elle porte
    # encore sur une carte présente. Si plus aucune question ne départage, le moteur refuse : c'est consigné.
    presentes = {f"{m.get('carte')}@{m.get('strate')}" for m in mots}
    d["liaisons"] = [x for x in (d.get("liaisons") or [])
                     if not any(r_ in json.dumps(x, ensure_ascii=False) for r_ in retires)]
    d["questions"] = [x for x in (d.get("questions") or [])
                      if any(c_ in json.dumps(x, ensure_ascii=False) for c_ in presentes)]
    d["etat"] = etat_depuis(mots, aujourdhui, jours)
    r = appeler_moteur(d, d["etat"], evenement, semantique, aujourdhui, evt["vue_exterieure"], evt["temporalite"])
    if r.get("erreur"):
        return dict(sortie_, statut="refuse", motif=str(r["erreur"])[:300])
    return dict(sortie_, statut="estime" if r.get("p") is not None else "non_estime", p_C_critique=r.get("p"))


def choisir_bras(c: dict, p_A: float) -> tuple[str, float]:
    """C si l'alphabet est estimé ; B si l'état est nul (sans carte, pas d'ajustement) ; A sinon."""
    if c.get("statut") == "estime":
        return "C", borner(c["p_C"])
    if c.get("statut") == "etat_nul" and c.get("p_B") is not None:
        return "B", borner(c["p_B"])
    return "A", borner(p_A)


def commentaire(q: Question, p_A: float, a_raison: str, c: dict, poste: str) -> str:
    """Le commentaire publié : il dit quel bras a été posté et pourquoi (règle FutureEval : refléter le raisonnement)."""
    libelle = {"C": "C, structural alphabet", "B": "B, reference-class base rate (no structure read)",
               "A": "A, model alone (outside the alphabet)"}[poste]
    tete = ("Situational-alphabet bot (experimental; no predictive performance established). "
            f"Posted arm: {libelle}.")
    vue = c.get("vue") or {}
    ligne_b = (f"Arm B, reference class: {c['p_B']:.3f} — {vue.get('classe_de_reference')} "
               f"({vue.get('source')}; {vue.get('calcul') or 'count over the period, scaled to the window'})."
               if c.get("p_B") is not None else None)
    if poste == "C":
        lignes = [tete,
                  f"State read on {c['dossier']['disponible_le']}: {c['etat']}",
                  f"Event: {c['evenement']} ({c['semantique']}).",
                  ligne_b,
                  f"Arm C, alphabet: {c['p_C']:.3f} (base rate adjusted by the cards read in the state).",
                  f"Arm A, model alone, sealed before the alphabet: {p_A:.3f}.",
                  "Engine flags (French): " + " | ".join(x if len(x) <= 220 else x[:217] + "…" for x in c.get("drapeaux", [])[:4])]
        return "\n".join(x for x in lignes if x)
    if poste == "B":
        rejets = c["dossier"].get("rejets") or {}
        lignes = [tete,
                  f"Candidate patterns examined for {c['evenement']}: none anchored in the facts found, so the base rate "
                  "is not adjusted."
                  + {"structure_absente": " Each candidate was checked against the facts and set aside on evidence.",
                     "angle_mort": " Caution: some candidates could not be checked against facts, even after a targeted "
                                   "second search (blind spot).",
                     }.get(c.get("nature_etat_nul"), ""),
                  *[f"- {k}: {str(v)[:300]}" for k, v in list(rejets.items())[:4]],
                  ligne_b,
                  f"Arm A, model alone, sealed before the alphabet: {p_A:.3f}."]
        return "\n".join(x for x in lignes if x)
    motif = c.get("motif") or "unknown"
    ex = c.get("exploratoire") or {}
    if ex:
        # 0.9.0 : le chiffre exploratoire est horodaté ici aussi (§29), avec la mention qu'il n'est PAS posté.
        val = (f"{ex['p_C']:.3f}" if isinstance(ex.get("p_C"), (int, float)) else f"no number ({ex.get('statut')})")
        explo_ligne = (f"Exploratory alphabet reading (stratum {ex.get('strate')}, outside the engine's validated "
                       f"scope; recorded for measurement, NOT the posted forecast): {val}.")
        return (f"{tete}\nAlphabet not used for the posted forecast ({c.get('statut')}).\n{explo_ligne}\n"
                + (f"{ligne_b}\n" if ligne_b else "") + f"\nModel-alone reasoning:\n{a_raison}")
    return f"{tete}\nAlphabet not used on this question ({c.get('statut')}: {motif}).\n\nModel-alone reasoning:\n{a_raison}"


# --------------------------------------------------------------------------- 0.9.1 : non binaires, en exploratoire

EXPLORATOIRE_AUTRES = os.environ.get("ALPHABET_EXPLORATOIRE_AUTRES", "1") not in ("0", "non", "false")


def mediane_percentiles(pcts: list[tuple[float, float]]) -> float | None:
    """La médiane d'une distribution donnée par percentiles [(0,1 ; v), …] (interpolation linéaire)."""
    pts = sorted((float(a), float(b)) for a, b in pcts)
    for (p0, v0), (p1, v1) in zip(pts, pts[1:]):
        if p0 <= 0.5 <= p1:
            return v0 if p1 == p0 else v0 + (v1 - v0) * (0.5 - p0) / (p1 - p0)
    return None


def question_derivee(genre: str, titre: str, criteres: str, prediction, unite: str = "") -> dict | None:
    """0.9.1 (décision d'auteur du 2026-11-08) : une question non binaire ramenée à UNE question binaire, au point le
    plus informatif de la prévision du bras A : la médiane (numérique, date : « strictement au-dessus / après ? »,
    p_A = 0,5) ou l'option la plus probable (choix multiple : « sera-ce elle ? », p_A = sa probabilité). Elle se
    résout sans ambiguïté à partir de l'issue de la question d'origine."""
    if genre in ("numerique", "date"):
        pcts = [(x["percentile"], x["value"]) for x in (prediction or {}).get("declared_percentiles") or []]
        t = mediane_percentiles(pcts)
        if t is None:
            return None
        if genre == "date":
            from datetime import datetime as _dt
            jour = _dt.fromtimestamp(t, tz=timezone.utc).date().isoformat()
            return {"genre": genre, "seuil": t, "seuil_lisible": jour, "sens": ">", "p_A": 0.5,
                    "titre": f"Derived from: « {titre} » — will the date that resolves this question be strictly after {jour}?",
                    "criteres": f"YES if the resolving date is after {jour}; NO otherwise. Original criteria: {criteres}"}
        return {"genre": genre, "seuil": t, "seuil_lisible": f"{t:g} {unite}".strip(), "sens": ">", "p_A": 0.5,
                "titre": f"Derived from: « {titre} » — will the resolved value be strictly greater than {t:g} {unite}?".strip(),
                "criteres": f"YES if the resolving value is > {t:g} {unite}; NO otherwise. Original criteria: {criteres}"}
    if genre == "choix_multiple":
        opts = [(o["option_name"], float(o["probability"])) for o in (prediction or {}).get("predicted_options") or []]
        if not opts:
            return None
        nom, pr = max(opts, key=lambda x: x[1])
        return {"genre": genre, "option": nom, "p_A": pr,
                "titre": f"Derived from: « {titre} » — will the outcome be « {nom} »?",
                "criteres": f"YES if the question resolves to « {nom} »; NO otherwise. Original criteria: {criteres}"}
    return None


def issue_derivee(derivee: dict, issue: str) -> int | None:
    """L'issue (0/1) de la question dérivée, à partir de l'issue brute de la question d'origine ; None si annulée."""
    i = str(issue or "").strip()
    if i.lower() in ("annulled", "ambiguous", ""):
        return None
    if derivee["genre"] == "choix_multiple":
        return int(i == derivee["option"])
    if i.lower() in ("above_upper_bound", "below_lower_bound"):
        return int(i.lower() == "above_upper_bound")
    if derivee["genre"] == "date":
        try:
            t = datetime.fromisoformat(i.replace("Z", "+00:00"))
        except ValueError:
            return None
        t = t if t.tzinfo else t.replace(tzinfo=timezone.utc)
        return int(t.timestamp() > float(derivee["seuil"]))
    try:
        return int(float(i) > float(derivee["seuil"]))
    except ValueError:
        return None


async def explorer_derivee(derivee: dict, ident: str, url: str, contexte: str, precisions: str, resolution: date,
                           recherche: str, llm: Llm, chercher: Chercheur, recherche_reelle: bool,
                           historique: Historique | None = None) -> dict:
    """Le pipeline complet (B, puits, lecture, moteur) sur la question dérivée. TOUT y est exploratoire, quelle que
    soit la strate : rien n'est posté. Le dossier est scellé à part (dossiers-explo/)."""
    maintenant = datetime.now(timezone.utc)
    aujourdhui = maintenant.date().isoformat()
    jours = max(1, (resolution - maintenant.date()).days)
    q = Question(id=f"{ident}-derivee", url=url, titre=derivee["titre"], contexte=contexte, criteres=derivee["criteres"],
                 precisions=precisions, resolution=resolution)
    try:
        c = await alphabet(q, recherche, llm, chercher, recherche_reelle, aujourdhui, jours, historique)
    except Exception as e:
        return {"derivee": derivee, "statut": "erreur", "motif": f"{type(e).__name__}: {e}"[:300]}
    ex = c.get("exploratoire") or {}
    p_c = c.get("p_C") if c.get("p_C") is not None else ex.get("p_C")
    sortie = {"derivee": derivee, "statut": ex.get("statut") or c.get("statut"), "motif": (c.get("motif") or "")[:300],
              "strate": ((c.get("plan") or {}).get("evenement") or {}).get("strate"),
              "p_B": c.get("p_B"), "p_C": p_c, "p_C_corrige": corriger_C(p_c, correction_retro()),
              "p_C_symetrique": (c.get("symetrique") or {}).get("p"), "symetrique": c.get("symetrique"),
              "nature_etat_nul": c.get("nature_etat_nul") or ex.get("nature_etat_nul"), "modeles": modeles_actifs()}
    dossier = c.get("dossier")
    if dossier is not None:
        d = {k: v for k, v in dossier.items() if not str(k).startswith("_")}
        rep = registre_ecrivable() / "dossiers-explo"
        rep.mkdir(exist_ok=True)
        nom = f"{ident}-{maintenant.strftime('%Y-%m-%dT%H%M%SZ')}.json"
        (rep / nom).write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
        sortie.update(dossier_fichier=f"dossiers-explo/{nom}", dossier_sha256=sceau(d))
    return sortie


def ligne_exploratoire_autre(ex: dict) -> str:
    """La ligne ajoutée au commentaire posté : le chiffre exploratoire est horodaté, et dit NON posté."""
    d = ex.get("derivee") or {}
    v = ex.get("p_C")
    cible = d.get("option") or d.get("seuil_lisible")
    return (f"\n\nExploratory alphabet reading (derived binary question at {cible}; recorded for measurement, NOT the "
            f"posted forecast): " + (f"{v:.3f}" if isinstance(v, (int, float)) else f"no number ({ex.get('statut')})")
            + (f"; base rate B {ex['p_B']:.3f}" if isinstance(ex.get("p_B"), (int, float)) else "") + ".")


def ecrire_registre(ligne: dict, dossier: dict | None) -> None:
    reg = registre_ecrivable()
    if dossier is not None:
        d = reg / "dossiers"
        d.mkdir(exist_ok=True)
        # 0.2.0 (audit, B8) : horodatage dans le nom ; deux passages le même jour n'écrasent plus une preuve scellée.
        nom = f"{ligne['question_id']}-{ligne['bras']['A']['horodatage'].replace(':', '').replace('+0000', 'Z')}.json"
        (d / nom).write_text(json.dumps(dossier, ensure_ascii=False, indent=1), encoding="utf-8")
        ligne["dossier_fichier"] = f"dossiers/{nom}"
        ligne["dossier_sha256"] = sceau(dossier)
    ligne["sceau"] = sceau(ligne)
    with open(reg / "journal-bot.jsonl", "a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(ligne, ensure_ascii=False, sort_keys=True) + "\n")


async def prevoir_binaire(q: Question, recherche: str, p_A: float, a_raison: str, llm: Llm, chercher: Chercheur,
                          recherche_reelle: bool, maintenant: datetime | None = None, publie: bool = True,
                          mode: str | None = None, historique: Historique | None = None,
                          critique: Llm | None = None) -> Resultat:
    maintenant = maintenant or datetime.now(timezone.utc)
    aujourdhui = maintenant.date().isoformat()
    jours = max(1, (q.resolution - maintenant.date()).days)
    bras_a = {"p": p_A, "horodatage": maintenant.isoformat(timespec="seconds")}
    bras_a["sceau"] = sceau({"question": str(q.id), "date": aujourdhui, **bras_a})  # A scellé avant l'alphabet
    try:
        c = await alphabet(q, recherche, llm, chercher, recherche_reelle, aujourdhui, jours, historique, critique)
    except Exception as e:  # 0.1.7 : une erreur de l'alphabet laisse quand même sa ligne au registre (bras A posté)
        c = {"statut": "erreur", "motif": f"{type(e).__name__} : {str(e)[:300]}"}
    poste, p_poste = choisir_bras(c, p_A)
    vue = c.get("vue") or {}
    corr = correction_retro()
    modeles = modeles_actifs()
    ligne = {"version_bot": VERSION_BOT, "version_skill": version_skill(), "question_id": str(q.id), "url": q.url,
             "titre": q.titre, "date_information": aujourdhui, "resolution_prevue": q.resolution.isoformat(),
             "fenetre_jours": jours, "recherche_reelle": recherche_reelle,
             "publie": publie, "mode": mode or os.environ.get("ALPHABET_MODE"),
             "modeles": modeles,
             "bras": {"A": bras_a,
                      "B": {"p": c.get("p_B"), **{k: vue.get(k) for k in ("classe_de_reference", "source", "fondement",
                                                                         "periode", "calcul", "disponible_le") if vue.get(k)},
                            "fondement_memoire": fondement_memoire(vue) if vue else None,
                            "recherches": c.get("recherches_reference"),
                            "vues": c.get("vues"), "historique": c.get("historique"), "classe": c.get("classe"),
                            "classe_statut": c.get("classe_statut"),
                            "compte_calcule": bool(vue.get("compte_calcule")), "puits": c.get("puits"),
                            "p_compte": c.get("p_compte"), "correspondance": c.get("correspondance"),
                            "p_modele": (c.get("vues") or {}).get("p_modele"),
                            "p_sans_ancre": (c.get("vues") or {}).get("p_sans_ancre")},
                      "C": {**{k: c.get(k) for k in ("statut", "p_C", "etat", "evenement", "semantique", "drapeaux",
                                                        "rho", "motif", "tentatives", "reprises_plan", "recherches",
                                                        "exploratoire", "symetrique",
                                                        "nature_etat_nul", "relance", "dynamique_observee")},
                            "rejets_classes": (c.get("dossier") or {}).get("_categories_rejet"),
                            "rejets_details": (c.get("dossier") or {}).get("_details_rejet"),
                            "p_C_corrige": corriger_C(c.get("p_C"), corr),
                            "attribution": controle_attribution(c.get("dossier"), c.get("_textes")),
                            "critique": c.get("critique"),
                            "correction": ({k: corr.get(k) for k in ("decalage_logit", "n", "calcule_le")}
                                           if corr and c.get("p_C") is not None else None)}},
             "bras_poste": poste, "p_poste": p_poste}
    texte = commentaire(q, p_A, a_raison, c, poste)
    if not publie:  # 0.2.0 (audit, B5) : un passage à blanc ne prétend pas avoir posté
        texte = texte.replace("Posted arm:", "Arm selected (dry run, not posted):", 1)
    # 0.5.1 : le commentaire envoyé est scellé avec la prévision (identifiant de question, bras, texte).
    ligne["commentaire"] = texte
    ecrire_registre(ligne, c.get("dossier"))
    return Resultat(p_A, c.get("p_B"), c.get("p_C"), poste, p_poste, texte, ligne)
