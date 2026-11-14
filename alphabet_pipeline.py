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
import statistics
import tempfile
import unicodedata
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Awaitable, Callable

VERSION_BOT = "0.10.88"

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
# 0.10.7 (skill 0.7.60, §37) : traducteur de lecture probabiliste, un appel de plus par question lue, en ombre.
TRADUCTION = os.environ.get("ALPHABET_TRADUCTION", "0") in ("1", "oui", "true")
# 0.10.11 (skill 0.7.62, §39) : test d'invariance du lecteur, sur une part des questions (deux lectures de plus).
try:
    INVARIANCE_TAUX = max(0.0, min(1.0, float(os.environ.get("ALPHABET_INVARIANCE_TAUX") or 0)))
except ValueError:
    INVARIANCE_TAUX = 0.0
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


# 0.9.8 (skill 0.7.55, validation §32) : équivalents de données pour les jetons, chargés seulement si ce réglage est
# activé (banc alphabet-chaine). Le bot Metaculus ne l'active pas avant une décision d'auteur datée.
EQUIV_DONNEES = os.environ.get("ALPHABET_EQUIV_DONNEES", "") in ("1", "oui", "true")


def equivalences(strates: list[int]) -> str:
    out = []
    for s in sorted(set(strates)):
        f = DOSSIER_SKILL / "references" / "equivalences" / f"strate-{s:02}.md"
        if f.is_file():
            out.append(f.read_text(encoding="utf-8"))
    if EQUIV_DONNEES and 6 in set(strates):
        f = DOSSIER_SKILL / "references" / "equivalences" / "donnees-chaine.md"
        if f.is_file():
            out.append(f.read_text(encoding="utf-8"))
    return "\n\n".join(out)


def appeler_moteur(dossier: dict, etat: str, evenement: str, semantique: str, date_info: str, vue: dict,
                   temporalite: str = "generique", exploratoire: bool = False, toutes_liaisons: bool = False) -> dict:
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
    # 0.10.52 (skill 0.7.75, §51) : seules les liaisons « averti » vont au calcul, où elles n'ouvrent que l'ombre
    # mixte_averti ; les autres types restent au dossier (les passer changerait le p publié : décision non prise)
    for li in dossier.get("liaisons") or []:
        if isinstance(li, str) and len(li.split()) == 3 and (toutes_liaisons or li.split()[1].strip("—-→>") == "averti"):
            cmd += ["--liaison", li]
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


_SECRETS = re.compile(r"((?:api_?key|apikey|key|token|access_?token|appid|app_key|secret)=)[^&\s'\"\\]+", re.I)


def sans_cles(obj):
    """0.10.17 : copie de l'objet où toute clé d'API passée dans une URL (« api_key=… », « token=… ») est masquée. Le
    registre est public : appliqué avant le scellement de chaque ligne et de chaque dossier."""
    return json.loads(_SECRETS.sub(r"\1***", json.dumps(obj, ensure_ascii=False, default=str)))


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


def empreinte(texte: str) -> str:
    """0.10.56 : SHA-256 du texte d'un résultat de recherche, tel que reçu. Le texte reste hors registre (droits des
    pages) ; l'empreinte permet de prouver plus tard qu'un passage cité figurait dans ce que la recherche a ramené, et
    de voir si la page a changé depuis (idée reprise du reçu de NightFalcon, Intuit)."""
    return hashlib.sha256(str(texte or "").encode("utf-8")).hexdigest()


def sans_resultat(r: dict) -> dict:
    """Une recherche pour le registre : sans son texte, avec son empreinte et sa longueur s'il y en a un."""
    out = {k: v for k, v in r.items() if k != "resultat"}
    if r.get("resultat"):
        out.update(empreinte=empreinte(r["resultat"]), longueur=len(str(r["resultat"])))
    return out


def empreintes_passages(dossier: dict, executees: list[dict]) -> list[dict]:
    """0.10.56 : pour chaque mot qui cite un passage, l'empreinte du résultat de recherche qui contient l'extrait
    (comparaison normalisée, sur les 120 premiers caractères) ; None si aucun résultat ne le contient."""
    sources = [(empreinte(r["resultat"]), _normal(r["resultat"])) for r in executees if r.get("resultat")]
    out = []
    for m in (dossier or {}).get("mots") or []:
        if not isinstance(m, dict):
            continue
        ps = m.get("passage")
        ps = ps if isinstance(ps, list) else [ps]          # un passage, ou une liste de passages
        for p_ in ps:
            ex = p_.get("extrait") if isinstance(p_, dict) else None
            if not isinstance(ex, str) or not ex.strip():
                continue
            cle_ = _normal(ex)[:120]
            h = next((h for h, t in sources if cle_ and cle_ in t), None)
            out.append({"mot": f"{m.get('carte')}@{m.get('strate')}", "empreinte": h})
    return out


def est_panne(e: BaseException) -> bool:
    """0.10.54 : une panne du HARNAIS (réseau, service, délai, aucun modèle disponible), pas une faute du lecteur. Un
    JSON illisible lève ValueError (JSONDecodeError en hérite) ; tout le reste est une panne. Une panne est exclue des
    taux et la question reste à refaire (« Who Validates the Validators? », trois issues au lieu de deux)."""
    return not isinstance(e, (ValueError, KeyError, TypeError, AttributeError, IndexError))


async def json_avec_reprise(llm: Llm, consigne: str, trace: dict | None = None, etape: str = "") -> dict:
    """0.10.25 : une sortie dont le JSON est illisible a UNE seconde chance : la consigne est renvoyée avec l'erreur.
    Le premier échec reste compté (trace["reprises_json"][etape]) : le score des sorties illisibles le voit."""
    try:
        return extraire_json(await llm(consigne))
    except Exception as e:
        if est_panne(e):      # 0.10.54 : une panne n'est pas un JSON invalide ; pas de reprise sous ce prétexte
            raise
        if trace is not None:
            r = trace.setdefault("reprises_json", {})
            r[etape] = r.get(etape, 0) + 1
        return extraire_json(await llm(
            consigne + f"\n\nTA RÉPONSE PRÉCÉDENTE N'ÉTAIT PAS UN JSON VALIDE ({type(e).__name__}: {str(e)[:200]}). "
            "Rends UNIQUEMENT l'objet JSON demandé, complet et bien formé, sans texte autour."))


# 0.10.70 : ombre « absence », hypothèse enregistrée le 2026-11-13 (décision d'auteur), AVANT toute question qui la
# jugera. Constat qui l'a fait naître (banc ForecastBench, jeu du 2026-10-25, exploratoire) : sur 11 états nuls
# d'absence, 1 OUI pour 3,9 attendus par B, alors que B est calibré sur l'ensemble (60 OUI pour 59,5). Hypothèse : sur
# les états nuls d'absence À VENIR, B avec sa cote multipliée par 0,5 bat B en perte log. Le facteur est fixé ici et
# n'est jamais ajusté sur les données ; les lignes d'avant 0.10.70 ne comptent pas. L'ombre n'est jamais postée : un
# état nul poste B, et l'ombre le reste jusqu'à une décision d'auteur datée.
OMBRE_ABSENCE = {"natures": ("structure_absente", "carte_visee_absente"), "facteur_cote": 0.5,
                 "depuis_version": "0.10.70", "enregistree_le": "2026-11-13"}


def ombre_absence(p_B: float | None, nature: str | None) -> float | None:
    """B dont la cote est multipliée par OMBRE_ABSENCE["facteur_cote"], pour un état nul d'absence ; sinon None."""
    if p_B is None or nature not in OMBRE_ABSENCE["natures"]:
        return None
    p = borner(float(p_B))
    o = p / (1 - p) * OMBRE_ABSENCE["facteur_cote"]
    return borner(o / (1 + o))


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
 "programmation": {{"qui": "qui a la capacité de fixer l'événement", "engagement": "à quoi voit-on qu'il s'y est engagé
     (texte, calendrier publié)"}}  (OBLIGATOIRE si temporalite = programmee ; sans réponse, l'événement n'est pas
     programmé et sera traité comme generique),
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


def bloc_compte_echoue(echec: dict | None) -> str:
    """0.10.34 (d'après Lv et al., ICML 2026 : un agent qui reçoit une erreur doit en tenir compte, pas l'ignorer) :
    le compte des données prévu n'a pas pu être fait ; la vue le sait et le dit."""
    if not echec:
        return ""
    return f"""
COMPTE PRÉVU, MAIS IMPOSSIBLE : le code devait compter sur « {echec.get('source') or '?'} », et cela a échoué
({echec.get('motif') or 'motif inconnu'}). Ta fréquence ne vient donc PAS de ce compte : dis-le dans "motif" ou
"calcul", appuie-toi sur une autre base nommée, et si aucune n'est honnête, mets "frequence": null.
"""


def consigne_vue(q: Question, plan: dict, references: list[dict], aujourdhui: str, jours: int,
                 historique: list[dict] | None = None, classe: dict | None = None,
                 ancrage: dict | None = None, sources_prises: list[str] | None = None,
                 compte_echoue: dict | None = None) -> str:
    res = "\n\n".join(f"[R{i + 1}] « {r['requete']} »\n{r['resultat'][:3000]}" for i, r in enumerate(references))
    hist = "\n".join(f"[M{i + 1}] {h['titre']} → {str(h['issue']).upper()} (résolue le {h.get('resolue_le', '?')})"
                     for i, h in enumerate(historique or []))
    imposee = ("" if not classe else
               "\nCLASSE DE RÉFÉRENCE IMPOSÉE (définie avant toi ; compte SUR ELLE, sans la changer ni l'élargir ; "
               "recopie-la dans classe_de_reference ; si elle ne permet aucun comptage honnête, mets frequence null) :\n"
               + json.dumps(classe, ensure_ascii=False, indent=1) + "\n")
    return f"""Étape 2 : la VUE EXTÉRIEURE, avant toute carte. Elle ne doit pas être choisie d'après l'état présent.
{imposee}{bloc_compte_echoue(compte_echoue)}
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
SÉRIE EN CROISSANCE (0.10.19) : si la question demande qu'une grandeur qui croît avec le temps (dépenses, PIB, dette, prix, population, puissance de calcul…) dépasse un NIVEAU, ne compte pas combien de fois ce niveau a été dépassé dans le passé (jamais, s'il est nouveau : la fréquence serait fausse) ; compte combien de fois, sur des fenêtres de même durée, la grandeur a progressé d'au moins le rapport seuil / dernière valeur connue (en %). Même chose à la baisse.

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
- ANCRAGE f (skill 0.7.53, validation §30 : le marqueur décide de l'INTENSITÉ, pas de l'existence) : un fait daté et
  sourcé qui montre le mécanisme de la DÉFINITION de la carte et remplit AU MOINS UN de ses « Marqueurs observables »
  ancre la carte en f (test "cerceau" ou "paille"). N'exige PAS la forme complète de l'« attendu » pour f : par exemple,
  pour CROISSANCE, une hausse mesurée qui s'accélère suffit pour f, sans trois mesures ni saturation nommée.
- F exige un fait SUFFISANT : test "pistolet" ou "double". La forme complète de l'attendu, corroborée, sert à F.
- Les « Marqueurs observables » d'une fiche, et le « marqueur local » d'un équivalent, sont des ALTERNATIVES : un seul
  rempli suffit pour f (avec la définition). Ne réclame pas les autres lignes de la liste pour f. Quand un équivalent
  local donne un marqueur précis (par exemple un seuil chiffré), le remplir suffit pour f.
- L'ancrage d'une carte ne dépend PAS de l'objet de la question : une carte s'ancre si la situation la montre, même si
  le fait porte sur une autre grandeur que celle que vise la question. C'est le moteur, par la matrice, qui décide de
  son effet sur l'événement ; ne rejette jamais une carte parce qu'elle « ne porte pas sur » l'objet de la question.
- F exige corroboration "independantes" (deux sources nommées séparées par « ; », et independance {critere origine|
  producteur|transmission, motif}) ou "unique" pour une source primaire. Deux relais d'une même origine = une source.
  Avec "independantes", ajoute source_urls : [URL de la 1re source, URL de la 2e], dans l'ordre des sources, chacune
  copiée telle quelle des RÉSULTATS (jamais reconstruite ni devinée).
- liaisons : « ABR@s TYPE ABR@s », TYPE parmi : echo, independance, transfert, conflit, renforcement, inclusion,
  appui, reproduction, tension, averti (aucun autre mot).
- dans UNE strate : renforcement, conflit, inclusion, appui, reproduction, independance, tension ; ENTRE deux strates :
  transfert, echo, conflit seulement ; averti dans les deux cas. transfert et echo ne relient JAMAIS deux cartes de la
  même strate (« CTR@6 transfert HIE@6 » est faux : dans une strate, écris appui, renforcement…).
- candidats : recopie TOUTES les cartes du plan (ses candidates ET ses contre-candidates), car les recherches les
  visent ; une carte du plan que tu n'ancres pas reçoit un motif de rejet.
- preuves_liaisons : une liste, UNE preuve par liaison, dans le même ordre (le fait daté qui établit le lien) ; une
  liaison sans preuve est retirée. Une liaison relie deux mots ANCRÉS (sauf averti, qui peut viser l'événement).
- averti : « A averti B » quand OBSERVER A renseigne sur B SANS QUE A AGISSE SUR B (précurseur, symptôme, ou effet
  d'une même cause) ; un fait daté de A et un précédent où A a précédé B. Seule liaison qui peut viser l'événement
  (ex. « POL@13 averti SEU@13 ») ; A doit être un mot ancré. Si A agit sur B par un mécanisme nommé : transfert.
- corroboration "independantes" : le champ source nomme AU MOINS DEUX sources séparées par « ; » ; sinon "unique".
- POLARITÉ (POL) : cherche le TIERS, ce qui se tient hors des deux camps sans en former un troisième, et ajoute au mot
  « tiers » : {"type": "mediateur"|"arbitre"|"abstention"|"aucun", "qui": "…", "fait": "fait daté"} ("aucun" : cherché,
  rien trouvé ; "qui" et "fait" alors facultatifs). Un TROISIÈME PÔLE STABLE contredit POLARITÉ : ne l'ancre pas.
- PÉRIODICITÉ (PER) : une période se CONSTATE (au moins trois occurrences datées), elle ne se postule pas ; un cycle ne
  désigne jamais un état « normal » auquel la situation devrait revenir.
- extrait d'un passage : 300 caractères au plus. Toute pièce et toute garantie sont disponibles AU PLUS TARD à la
  date d'information (jamais une page publiée après).
- ÉCRITURE : carte = l'ABRÉVIATION (POL, pas POLARITÉ) ; strate = un ENTIER (13, pas « 13_portee… ») ; toute
  référence à une carte ailleurs (candidats, rejets, liaisons, questions) s'écrit ABR@strate (POL@6).
- a6 (pour F) : « CARTE@s : VOISINE → (pourquoi écartée) ; … » pour TOUTES les voisines listées plus bas (VOISINES À
  PASSER), chacune avec → ou +, et une raison entre parenthèses ; jamais « ? » ni « ← ». Si tu ne peux pas trancher
  toutes les voisines, note f (sans a6).
- test : exactement l'un de "paille", "cerceau", "pistolet", "double" (F exige "pistolet" ou "double").
- contre_observation : la plus forte trouvée DANS la situation ; portee OBLIGATOIRE POUR CHAQUE MOT, même s'il n'y en a
  pas ("aucune"). La portée fixe la force (A7) :
    "aucune" ou "marginale" → intensité inchangée ;
    "substantielle" sur une lecture F → noter "intensite": "f" et "force_initiale": "F" ;
    "substantielle" sur une lecture déjà f → NE PAS coder le mot : la carte va dans rejets_classes, "contredit" ;
    "dominante" → NE PAS coder le mot : rejets_classes, "contredit".
  "force_initiale" n'apparaît qu'avec une portée substantielle.
- contredirait ≠ attendu, sans nommer la carte. option : un fait qui ne change l'espace d'action de personne ne s'ancre pas.
- rejets_classes : pour chaque candidate non ancrée, {"categorie": …, "motif": …}, catégorie au choix :
  "aucun_fait" (aucun fait pertinent dans les résultats), "marqueur_non_rempli" (des faits pertinents existent mais
  n'en remplissent AUCUN marqueur observable), "contredit" (un fait de la situation dit le CONTRAIRE de ce que la carte
  rend attendu, ou réalise ce que nomme « contredirait »), "non_cherchee" (ses requêtes n'ont pas été lancées).
  CONTREDIT ≠ MARQUEUR NON REMPLI : un fait qui nie ou dément le mécanisme est « contredit », même s'il est formulé
  négativement. Exemples (question « le pays X sortira-t-il de l'UE ? ») : « le droit de l'UE ne rend pas la sortie
  impossible » contredit une CONTRAINTE qui bloquerait la sortie ; « aucun autre pays n'a choisi de partir » contredit
  une CONTAGION. En revanche, un attendu seulement INCOMPLET (une mesure au lieu de trois) n'est pas contredit : la
  carte reste en f si la définition et un marqueur sont là. Choisis la catégorie d'après les résultats de recherche,
  pas d'après ton intuition. Ajoute
  "fait_attendu" (une phrase : ce que dirait un fait qui remplirait le marqueur ici) et "extrait_proche" (le passage
  le plus proche trouvé, avec son numéro [n], ou null).
- questions : au moins une question ouverte et datée qui départagerait la lecture, exactement sous cette forme :
  {"question": "…", "si_oui": "ABR@s", "si_non": "ABR@s" ou "indetermine", "resolution": "quelle observation, dans
  quelle source, répondrait", "justification": {"oui": "pourquoi « oui » établit si_oui", "non": "pourquoi « non »
  établit si_non"}, "statut": "ouverte"}. si_oui ≠ si_non ; l'une des deux au moins est un mot de l'état ; « non A »
  ne vaut pas « B » : si « non » ne désigne aucune carte, écris "indetermine".
- Ne cite que des faits trouvés dans les résultats de recherche fournis ; n'invente ni source, ni URL, ni date.
- ÉTAT NUL ADMIS : si aucun fait ne remplit la définition et au moins un marqueur d'une carte, "mots" est une liste vide et chaque candidate va
  dans rejets. C'est une lecture légitime (« aucune structure lue »), jamais un échec : ne force pas une carte.
- dynamique_observee (seulement si "mots" est vide) : en une ou deux phrases, la dynamique que les faits trouvés
  montrent malgré tout (qui agit, sur quoi, dans quel sens), SANS nommer aucune carte ni structure de l'alphabet ;
  "aucune" si les faits ne montrent aucune dynamique. Elle n'entre pas dans le calcul : elle sert à chercher plus tard
  une structure qui manquerait à l'alphabet.
"""


def voisines_a_passer(cartes: list[str]) -> str:
    """0.10.49 : la liste exacte des voisines que la ligne a6 d'un mot F doit trancher (moteur, cartes.md)."""
    try:
        m = _moteur()
        v = m.voisines()
        return " ; ".join(f"{c} : {', '.join(sorted(v.get(c, set()))) or 'aucune'}" for c in dict.fromkeys(cartes))
    except Exception:
        return "voir les fiches"


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

VOISINES À PASSER (ligne a6 d'un mot F) : {voisines_a_passer(cartes)}

FICHES DES CANDIDATES :
{fiches(cartes)}

ÉQUIVALENTS LOCAUX DES STRATES :
{equivalences(plan.get("strates", []))}

FORMAT (exemple fictif, à suivre pour la structure seulement) :
{json.dumps(exemple, ensure_ascii=False, indent=1)}

Rends UNIQUEMENT un objet JSON avec les clés : {", ".join(CLES_LECTURE)} (et dynamique_observee si "mots" est vide).
L'événement prévu est {ev['carte']}@{ev['strate']} {ev['type']} : {"cette carte ne doit PAS figurer dans les mots" if ev['type'] == "apparait" else "cette carte doit figurer dans les mots"}.
Au plus 4 cartes ancrées par strate (carte de l'événement comprise) : chaque carte ancrée est une candidate, et le moteur
refuse plus de 4 candidates dans une strate."""


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

FICHES DES CANDIDATES (la définition + au moins un marqueur observable suffisent pour f) :
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


from alphabet_attribution import _chiffres, _normal, controle_attribution  # noqa: E402,F401  (0.9.3)
from alphabet_provenance import provenance_F  # noqa: E402  (0.10.38)


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
    relance["recherches"] = [sans_resultat(r) for r in nouvelles]
    if not any(r.get("executee") for r in nouvelles):
        return lecture, executees, dict(relance, echec="aucune recherche de relance exécutée")
    toutes = executees + nouvelles
    try:
        relue = extraire_json(await llm(consigne_dossier(q, plan, toutes, aujourdhui, jours)))
    except Exception as e:
        return lecture, executees, dict(relance, echec=f"relecture illisible : {e}")
    relance["mots_apres"] = len(relue.get("mots") or [])
    return relue, toutes, relance


async def nouveau_depart_ombre(q: "Question", plan: dict, executees: list, aujourdhui: str, jours: int, evt: dict,
                              evenement: str, hors_strate, llm, erreur: str, trace: dict) -> dict:
    """0.10.83, EN OMBRE (billet « idea basins », Bespoke Labs, 2026-11 ; registre : une deuxième correction n'a jamais
    sauvé un dossier, 0 sur 12). Au moment où la boucle demande sa deuxième correction, une lecture NEUVE est faite à
    contexte vide : la consigne de lecture d'origine, plus une ligne qui nomme la règle enfreinte, sans l'historique des
    tentatives. Elle passe le même réparateur, les mêmes contrôles et le moteur ; son statut et son p sont gardés à
    part. La boucle officielle continue inchangée : rien n'est posté de l'ombre, et les données de l'apprentissage des
    liens (dernière lecture officielle) ne bougent pas."""
    consigne = (consigne_dossier(q, plan, executees, aujourdhui, jours)
                + "\n\nRAPPEL : une lecture précédente de cette question a été refusée par le moteur pour la raison "
                  f"suivante ; lis la situation à neuf et évite ce défaut : {str(erreur)[:300]}")
    lec = await json_avec_reprise(llm, consigne, {}, "nouveau_depart")
    trace["_rejeu"]["lecture_nouveau_depart"] = json.loads(json.dumps(lec, ensure_ascii=False, default=str))
    d = assembler(lec, json.loads(json.dumps(plan, ensure_ascii=False, default=str)), executees, evt, aujourdhui, jours)
    retirer_faits_futurs(d, trace.get("_textes") or "", aujourdhui, jours)
    if not d["mots"]:
        return {"statut": "etat_nul", "nature_etat_nul": nature_etat_nul(d.get("_categories_rejet"))}
    e2 = controle_etat(d, plan)
    if e2 and e2.startswith(f"événement « {plan['evenement']['type']} » sur une carte absente"):
        return {"statut": "etat_nul", "nature_etat_nul": "carte_visee_absente"}
    if e2:
        return {"statut": "refuse", "motif": str(e2)[:200]}
    s = appeler_moteur({**{k: v for k, v in d.items() if not k.startswith("_")},
                        "rejets_categories": dict(d.get("_categories_rejet") or {})}, d["etat"], evenement,
                       plan["semantique"], aujourdhui, evt["vue_exterieure"], evt["temporalite"], exploratoire=hors_strate)
    if s.get("erreur"):
        return {"statut": "refuse", "motif": str(s["erreur"])[:200]}
    return {"statut": "estime" if s.get("p") is not None else "non_estime", "p_C": s.get("p"),
            "mots": len(d["mots"])}


def consigne_correction(lecture: dict, erreur: str) -> str:
    return f"""Le moteur du skill a refusé cette lecture. Corrige-la sans inventer de fait, de source ni d'URL : si un
élément manque, descends l'intensité à f, ou retire le mot et motive-le dans rejets. Une lecture sans aucun mot (état
nul) est admise si rien ne tient.

ERREUR DU MOTEUR : {erreur}

LECTURE :
{json.dumps(lecture, ensure_ascii=False, indent=1)}

Rends UNIQUEMENT l'objet JSON corrigé, avec les clés : {", ".join(CLES_LECTURE)}."""


# --------------------------------------------------------------------------- assemblage

CLES_LECTURE = ("candidats", "contre_candidate", "rejets_classes", "mots", "liaisons", "preuves_liaisons", "questions")


def cle_rejet(x: dict) -> str | None:
    """0.10.55 : la carte d'un rejet rendu en liste. Le lecteur la range sous des noms variés (carte, candidate, mot…),
    ou sépare carte et strate ; sinon on cherche une valeur « ABR@s ». Sans carte lisible : None (le rejet est
    ignoré ; la candidate reçoit plus loin « non cherchée »). Avant, une clé « ?0 » partait au moteur, qui refusait
    tout le dossier (banc ForecastBench du 2026-11-12 : « carte inconnue : '?0' », deux fois)."""
    for k in ("carte", "candidate", "candidat", "mot", "cle", "clé", "id", "code", "nom"):
        v = x.get(k)
        if isinstance(v, str) and v.strip():
            s_ = x.get("strate")
            if "@" not in v and s_ is not None:
                v = f"{v}@{s_}"
            return cle_normale(v)
    for v in x.values():
        if isinstance(v, str) and re.fullmatch(r"\s*[A-Za-zÀ-ÿ·]+@\d+\s*", v):
            return cle_normale(v.strip())
    return None


def details_rejets(lecture: dict) -> dict:
    """0.4.0 : pour chaque candidate écartée, ce qu'aurait dit un fait suffisant et l'extrait le plus proche trouvé.
    Mesure qui départage « le modèle sait mais n'ancre pas » (écart d'exécution) et « la recherche n'a rien ramené »."""
    brut = lecture.get("rejets_classes") or {}
    if isinstance(brut, list):
        brut = {cle_rejet(x): x for x in brut if isinstance(x, dict) and cle_rejet(x)}
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
        brut = {cle_rejet(x): x for x in brut if isinstance(x, dict) and cle_rejet(x)}   # 0.10.55
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


def programmation_valide(plan: dict) -> bool:
    pg = plan.get("programmation")
    return isinstance(pg, dict) and all(isinstance(pg.get(c), str) and pg[c].strip() for c in ("qui", "engagement"))


def temporalite_de(plan: dict) -> str:
    """0.2.0 (audit, B11) : la temporalité est déclarée par le plan ; « programmee » (échéance fixée d'avance) ou
    « duree_de_vie » rendent le moteur « non estimé » sans référence propre, comme le veut le skill."""
    t_ = plan.get("temporalite")
    if t_ == "programmee" and not programmation_valide(plan):
        # 0.10.45 : la règle du skill (0.7.16, Copley) : sans « qui » ni « engagement », l'événement n'est PAS programmé.
        # Il est traité comme générique, au lieu de faire refuser tout le dossier (aucune proposition).
        return "generique"
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
    evt = {"evenement": evenement, "semantique": plan["semantique"], "temporalite": temporalite_de(plan),
           "resolution": vue.get("resolution") or "", "source_resolution": vue.get("source_resolution") or {},
           "vue_exterieure": ve}
    if evt["temporalite"] == "programmee":
        evt["programmation"] = {"qui": plan["programmation"]["qui"], "engagement": plan["programmation"]["engagement"]}
    elif plan.get("temporalite") == "programmee":
        evt["programmation_absente"] = True   # 0.10.45 : déclarée programmée sans qui ni engagement : traitée générique
    return evt, evenement


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
"annee" pour sommer d'abord les valeurs (morts par mois, par exemple), sinon null. "bornes" : [0, 100] si la
grandeur est un pourcentage ou une part (taux de chômage, part de voix, taux d'approbation…), [0, 1] pour une
proportion, sinon null.

Rends UNIQUEMENT un objet JSON :
{{
 "appels": [{{"source": "nom du catalogue", "params": {{...}}, "pourquoi": "ce que l'appel mesure ici"}}],
 "compte": null ou {{"appel": indice (0 pour le premier appel), "mode": "evenement|atteint|franchit",
     "seuil": nombre ou null, "sens": ">=|>|<=|<", "agregation": null | "mois" | "annee",
     "bornes": null | [min, max], "correspondance": "exacte|proche",
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
            trace["appels"].append(dict(journal, statut="echec",
                                        motif=apz.masquer(f"{type(e).__name__}: {e}")[:200]))
            continue
        if not r["points"]:
            trace["appels"].append(dict(journal, statut="vide"))
            continue
        releves[i] = (r, rang_premier + len(resultats), src)
        trace.setdefault("_releves", []).append(r)      # 0.10.73 : pour l'ombre « ancrage par les séries »
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
            bornes = spec.get("bornes")       # 0.10.19 : série bornée (pourcentage), déclarée par le modèle
            bornes = (tuple(float(x) for x in bornes) if isinstance(bornes, (list, tuple)) and len(bornes) == 2
                      and all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in bornes) else None)
            res = apz.compter(r, jours, str(spec.get("mode") or "atteint"), seuil, str(spec.get("sens") or ">="),
                              spec.get("agregation"), fin=avant, nature=apz.CATALOGUE[src].get("nature"),
                              bornes=bornes)
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


MOIS = {m: i for i, ms in enumerate((("janvier", "january", "jan"), ("février", "fevrier", "february", "feb"),
                                     ("mars", "march", "mar"), ("avril", "april", "apr"), ("mai", "may"),
                                     ("juin", "june", "jun"), ("juillet", "july", "jul"), ("août", "aout", "august", "aug"),
                                     ("septembre", "september", "sep", "sept"), ("octobre", "october", "oct"),
                                     ("novembre", "november", "nov"), ("décembre", "decembre", "december", "dec")), 1)
        for m in ms}


def dates_citees(texte: str) -> list[str]:
    """Dates complètes citées dans un texte (AAAA-MM-JJ, « 11 novembre 2026 », « November 11, 2026 »), en ISO."""
    t = str(texte or "")
    sortie = [f"{a}-{m}-{j}" for a, m, j in re.findall(r"\b(\d{4})-(\d{2})-(\d{2})", t)]
    for j, mo, a in re.findall(r"\b(\d{1,2})(?:er)?\s+([A-Za-zéûô]+)\.?\s+(\d{4})\b", t):
        if mo.lower() in MOIS:
            sortie.append(f"{a}-{MOIS[mo.lower()]:02d}-{int(j):02d}")
    for mo, j, a in re.findall(r"\b([A-Za-z]+)\.?\s+(\d{1,2}),?\s+(\d{4})\b", t):
        if mo.lower() in MOIS:
            sortie.append(f"{a}-{MOIS[mo.lower()]:02d}-{int(j):02d}")
    return sortie


def retirer_faits_futurs(dossier: dict, textes: str, aujourdhui: str, jours: int) -> list[str]:
    """0.10.2 (Paleka et al., ICLR 2026, fuites temporelles ; banc sans texte, 10/11 : le lecteur de secours a ancré
    l'issue elle-même comme fait). Un mot dont le fait cite une date POSTÉRIEURE à la date d'information, absente des
    résultats fournis, est une invention : il est retiré, et le retrait est consigné. Une date future qui figure dans
    les résultats (un vote prévu, une échéance annoncée) reste admise : c'est un fait présent sur l'avenir."""
    corpus = set(dates_citees(textes))
    gardes, retires = [], []
    for m in dossier.get("mots") or []:
        futures = [d for d in dates_citees(m.get("fait")) if d[:10] > aujourdhui and d not in corpus]
        if futures:
            cle = f"{m.get('carte')}@{m.get('strate')}"
            retires.append(cle)
            dossier.setdefault("rejets", {})[cle] = (f"[non_classe] fait daté après la date d'information "
                                                     f"({', '.join(sorted(set(futures)))}) et absent des résultats : retiré")
            dossier.setdefault("_categories_rejet", {})[cle] = "non_classe"
            continue
        gardes.append(m)
    if retires:
        dossier["mots"] = gardes
        dossier["etat"] = etat_depuis(gardes, aujourdhui, jours)
    return retires


def _sans_accents(x: str) -> str:
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFD", x) if unicodedata.category(c) != "Mn")


def code_carte(x) -> str:
    """0.10.44 : « POL », « POLARITÉ », « polarite », « POL@6 » → « POL » (le lecteur écrit parfois le nom entier ou
    colle la strate au code ; banc ForecastBench du 2026-11-11 : « carte inconnue : POL@6 »)."""
    t = str(x or "").strip().split("@")[0].strip()
    noms = noms_cartes()
    if t in noms:
        return t
    cle = re.sub(r"[^A-Z]", "", _sans_accents(t).upper())
    for abr, nom in noms.items():
        if cle in (abr, re.sub(r"[^A-Z]", "", _sans_accents(nom).upper())):
            return abr
    return t


def entier_strate(v) -> int:
    """0.10.44 : « 13 », 13, « 13_portee_substantielle », « strate 6 » → l'entier ; sinon ValueError explicite."""
    m = re.search(r"\d+", str(v if v is not None else ""))
    if not m:
        raise ValueError(f"strate illisible : {v!r} (un entier de 1 à 13 est attendu)")
    return int(m.group(0))


def cle_normale(x) -> str:
    """« POLARITÉ@13_portee » → « POL@13 » ; une clé sans strate garde seulement le code."""
    t = str(x or "")
    if "@" not in t:
        return code_carte(t)
    c, reste = t.split("@", 1)
    try:
        return f"{code_carte(c)}@{entier_strate(reste)}"
    except ValueError:
        return t


def normaliser_plan(plan: dict) -> dict:
    ev = plan.get("evenement")
    if isinstance(ev, dict):
        brut = str(ev.get("carte") or "")
        if "@" in brut and not ev.get("strate"):
            ev["strate"] = brut.split("@", 1)[1]
        ev["carte"] = code_carte(brut)
        try:
            ev["strate"] = entier_strate(ev.get("strate"))
        except ValueError:
            pass
    if isinstance(plan.get("candidats"), list):
        plan["candidats"] = [cle_normale(c) for c in plan["candidats"]]
    return plan


def normaliser_lecture(lecture: dict) -> dict:
    """0.10.44 : les champs du lecteur ramenés à la forme attendue par le moteur, AVANT validation : codes de carte,
    strates entières, clés « CARTE@n ». Le sens ne change pas : seule l'écriture est corrigée (les erreurs Python
    « invalid literal for int() » et « not enough values to unpack » du banc ForecastBench venaient de là)."""
    for k in ("candidats", "contre_candidate"):
        v = lecture.get(k)
        if isinstance(v, list):
            lecture[k] = [cle_normale(x) if isinstance(x, str) else x for x in v]
        elif isinstance(v, str):
            lecture[k] = cle_normale(v)
    for m in lecture.get("mots") or []:
        if isinstance(m, dict):
            brut = str(m.get("carte") or "")
            if "@" in brut and not m.get("strate"):
                m["strate"] = brut.split("@", 1)[1]
            m["carte"] = code_carte(brut)
            try:
                m["strate"] = entier_strate(m.get("strate"))
            except ValueError:
                pass
    rc = lecture.get("rejets_classes")
    if isinstance(rc, dict):
        lecture["rejets_classes"] = {cle_normale(k): v for k, v in rc.items()}
    for li in lecture.get("liaisons") or []:
        if isinstance(li, dict):
            for k, v in list(li.items()):
                if isinstance(v, str) and "@" in v and len(v) < 60:
                    li[k] = cle_normale(v)
    return lecture


def assembler(lecture: dict, plan: dict, executees: list[dict], evt: dict, aujourdhui: str, jours: int) -> dict:
    normaliser_lecture(lecture)
    d = {k: lecture.get(k, []) for k in ("candidats", "contre_candidate", "mots", "liaisons", "preuves_liaisons", "questions")}
    d["rejets"], d["_categories_rejet"] = rejets_moteur(lecture)
    d["_details_rejet"] = details_rejets(lecture)
    d["etat"] = etat_depuis(d.get("mots") or [], aujourdhui, jours)
    d["disponible_le"] = aujourdhui
    d["recherches"] = [{"famille": r["famille"], "cartes": r["cartes"], "requete": r["requete"],
                        "executee": r["executee"], **({"date_execution": aujourdhui} if r["executee"] else {})}
                       for r in executees]
    d["evenements"] = [evt]
    d["_reparations"] = reparer_dossier(d, plan, aujourdhui)
    # 0.10.57 : une réparation peut affaiblir un mot (F → f) ; l'état doit le suivre, sinon le moteur refuse le dossier
    # (« force contradictoire », révélé par le premier rejeu du banc le 2026-11-12 ; en vrai, une correction du
    # lecteur, payée, rattrapait l'écart)
    d["etat"] = etat_depuis(d.get("mots") or [], aujourdhui, jours)
    return d


LIAISONS_ADMISES = ("echo", "écho", "independance", "indépendance", "transfert", "conflit", "renforcement",
                    "inclusion", "appui", "reproduction", "tension", "averti")   # 0.10.52 : averti (skill 0.7.75, §51)


def reparer_dossier(d: dict, plan: dict, aujourdhui: str | None = None) -> list[str]:
    """0.10.44 : réparations de FORME, faites par le code et tracées (banc ForecastBench du 2026-11-11 : 8 lectures
    exploratoires sur 14 refusées pour la forme, non pour le fond). Rien n'est inventé : une liaison illisible est
    retirée (les liaisons sont facultatives) ; une carte à la fois ancrée et rejetée garde son ancrage (le fait cité
    l'emporte sur le rejet) ; une strate de l'état qui n'a pas ses 2 candidates reçoit celles du plan, rejet « non
    cherchée » (effort 0 : le modèle génératif n'en apprend rien)."""
    notes: list[str] = []
    st_ev = str(((plan.get("evenement") or {}).get("strate")) or "")
    # 0. une clé sans strate prend celle de l'événement (« not enough values to unpack » du moteur)
    def avec_strate(k):
        k2 = cle_normale(k)
        if "@" not in k2 and st_ev:
            notes.append(f"strate de l'événement ajoutée à {k}")
            return f"{k2}@{st_ev}"
        return k2
    # 0 (0.10.77, test par propriétés) : un mot dont la strate reste illisible après normalisation (absente, vide,
    # « x ») faisait planter le réparateur, et toute la lecture avec lui. Il est retiré, tracé : rien n'est deviné.
    lisibles = []
    for m in d.get("mots") or []:
        if isinstance(m, dict):
            # 0.10.81 (banc du 2026-11-14, Mistral) : source_url rendue comme une liste d'une adresse, ou avec des
            # espaces autour : remise en forme, sans rien inventer (une liste de plusieurs adresses garde la première,
            # les autres vont dans source_urls si le champ est vide)
            u = m.get("source_url")
            if isinstance(u, list):
                adr = [str(x).strip() for x in u if isinstance(x, str) and str(x).strip()]
                if adr:
                    m["source_url"] = adr[0]
                    if len(adr) > 1 and not m.get("source_urls"):
                        m["source_urls"] = adr
                    notes.append(f"{m.get('carte')} : source_url donnée en liste → première adresse")
            elif isinstance(u, str) and u != u.strip():
                m["source_url"] = u.strip()
            try:
                int(str(m.get("strate")).strip())
            except ValueError:
                notes.append(f"{m.get('carte')} : strate illisible ({m.get('strate')!r}) → mot retiré")
                continue
        lisibles.append(m)
    if "mots" in d:
        d["mots"] = lisibles
    d["candidats"] = [avec_strate(c) for c in d.get("candidats") or [] if isinstance(c, str)]
    cc = d.get("contre_candidate")
    d["contre_candidate"] = [avec_strate(c) for c in (cc if isinstance(cc, list) else [cc]) if isinstance(c, str)]
    if isinstance(d.get("rejets"), dict):
        cats = d.get("_categories_rejet") or {}
        d["rejets"] = {avec_strate(k): v for k, v in d["rejets"].items()}
        d["_categories_rejet"] = {avec_strate(k): v for k, v in cats.items()}
    # 0 bis (0.10.48). Les règles d'ancrage du skill (A7, A6, test, garantie), appliquées avec LEUR conséquence écrite,
    # au lieu de faire refuser tout le dossier : on ne renforce jamais une lecture, on ne fait que l'affaiblir.
    #   A7 : portée absente → mot non retenu (contre-observation non évaluée) ; dominante → rejet ; substantielle sur F →
    #   f avec force_initiale F ; substantielle sur f (sans origine F) → rejet. F dont l'A6, le test ou la garantie ne
    #   passent pas → f (« au plus f »). Un test ou une garantie mal formés sur un f sont retirés (facultatifs).
    try:
        M = _moteur()
    except Exception:
        M = None
    if M is not None:
        garde_m = []
        for m in d.get("mots") or []:
            if not isinstance(m, dict):
                continue
            k = f"{m.get('carte')}@{m.get('strate')}"
            # 0.10.64 (skill 0.7.76, §52) : le tiers d'une POLARITÉ. Mal formé ou hors de POL → retiré ; un troisième
            # pôle stable contredit la garantie de la carte → POLARITÉ n'est pas ancrée (conséquence écrite)
            if "tiers" in m and hasattr(M, "controle_tiers"):
                err_t = M.controle_tiers(cle_normale(k), m)
                if err_t:
                    t_ = m.get("tiers")
                    if isinstance(t_, dict) and t_.get("type") == "troisieme_pole" and cle_normale(k).startswith("POL@"):
                        notes.append(f"{k} : troisième pôle stable → POLARITÉ non ancrée (§52)")
                        continue
                    m.pop("tiers", None)
                    notes.append(f"{k} : tiers retiré ({err_t[0][:90]})")
            # 0.10.51 : corroboration et pièces, par leur conséquence écrite (jamais un renforcement)
            n_src = len([x for x in str(m.get("source") or "").split(";") if x.strip()])
            if m.get("corroboration") == "independantes" and n_src < 2:
                m["corroboration"] = "unique"
                m.pop("independance", None)
                notes.append(f"{k} : « independantes » avec une seule source nommée → « unique »")
            elif m.get("corroboration") != "independantes" and "independance" in m:
                m.pop("independance", None)
                notes.append(f"{k} : independance retirée (source unique)")
            pas = m.get("passage")
            for x in (pas if isinstance(pas, list) else [pas]):
                if isinstance(x, dict) and isinstance(x.get("extrait"), str):
                    if not x["extrait"].strip():
                        x.pop("extrait")
                    elif len(x["extrait"]) > 300:
                        x["extrait"] = x["extrait"][:297].rstrip() + "…"
                        notes.append(f"{k} : extrait ramené à 300 caractères")
            if isinstance(m.get("garantie"), dict):
                try:
                    eg = M.controle_garantie(k, m, False) + M.controle_support(k, m, False, aujourdhui)
                except Exception as ex:
                    eg = [str(ex)]
                if eg:
                    m.pop("garantie", None)
                    m.pop("option", None)
                    notes.append(f"{k} : garantie retirée ({eg[0][:110]})")
            po, fi = m.get("portee"), m.get("force_initiale")
            motif_rejet = None
            if po not in M.PORTEES:
                motif_rejet = "[non_classe] A7 : portée de la contre-observation non évaluée par le lecteur ; mot non retenu"
            elif po == "dominante":
                motif_rejet = "[contredit] A7 : contre-observation dominante"
            elif po == "substantielle":
                if m.get("intensite") == "F":
                    m["intensite"], m["force_initiale"] = "f", "F"
                    notes.append(f"{k} : A7 substantielle sur F → f (force_initiale F)")
                elif fi != "F":
                    motif_rejet = "[contredit] A7 : contre-observation substantielle sur une lecture f"
            elif fi is not None:
                m.pop("force_initiale", None)
                notes.append(f"{k} : force_initiale retirée (portée {po})")
            if motif_rejet:
                d.setdefault("rejets", {})[k] = motif_rejet
                d.setdefault("_categories_rejet", {})[k] = motif_rejet[1:motif_rejet.index("]")]
                notes.append(f"{k} : mot non retenu ({motif_rejet})")
                continue
            if m.get("intensite") == "F":
                try:
                    e = (M.controle_a6(k, m.get("a6") or "") + M.controle_garantie(k, m, True) + M.controle_support(k, m, True, aujourdhui)
                         + M.controle_test(k, m, "F", True))
                except Exception as ex:
                    e = [str(ex)]
                if e:
                    m["intensite"] = "f"
                    notes.append(f"{k} : F → f ({e[0][:120]})")
            if m.get("intensite") == "f":
                try:
                    if M.controle_test(k, m, "f", False):
                        m.pop("test", None)
                        notes.append(f"{k} : test mal formé retiré")
                    if M.controle_garantie(k, m, False):
                        m.pop("garantie", None)
                        m.pop("option", None)
                        notes.append(f"{k} : garantie mal formée retirée")
                except Exception:
                    pass
            garde_m.append(m)
        d["mots"] = garde_m
    # 0 quater (0.10.84, banc du 2026-11-14 : cinq cartes ancrées en strate 7, refus maintenu sur trois lectures). Le
    #    moteur exige 2 à 4 candidates par strate et chaque carte ancrée est une candidate : au-delà de 4 ancrées dans
    #    une strate, le dossier est refusé en entier. Le réparateur retire les ancrées en surnombre (affaiblir : une
    #    source de moins, jamais une de plus). On garde d'abord la carte de l'événement (persiste / disparaît), puis
    #    les F, puis les contre-candidates, les cartes visées par une recherche, celles du plan, dans l'ordre du
    #    lecteur. Les liaisons et questions qui visaient une carte retirée tombent aux étapes suivantes (mot absent).
    ev_ = plan.get("evenement") or {}
    try:
        k_ev = cle_normale(f"{ev_.get('carte')}@{ev_.get('strate')}") if ev_.get("type") != "apparait" else None
    except Exception:
        k_ev = None
    cc0 = set()
    for c in (d.get("contre_candidate") if isinstance(d.get("contre_candidate"), list) else []):
        try:
            cc0.add(cle_normale(c))
        except Exception:
            pass
    rech0 = set()
    for r in d.get("recherches") if isinstance(d.get("recherches"), list) else []:
        for c in (r.get("cartes") or []) if isinstance(r, dict) else []:
            try:
                rech0.add(cle_normale(c))
            except Exception:
                pass
    plan0 = set()
    for c in plan.get("candidats") or []:
        try:
            plan0.add(cle_normale(c))
        except Exception:
            pass
    par_strate: dict[str, list[tuple[int, str]]] = {}
    for i, m in enumerate(d.get("mots") or []):
        if isinstance(m, dict):
            try:
                k = cle_normale(f"{m.get('carte')}@{m.get('strate')}")
            except Exception:
                continue
            par_strate.setdefault(k.split("@")[1], []).append((i, k))
    retirer_i = set()
    for st, lst in par_strate.items():
        if len({k for _, k in lst}) <= 4:
            continue
        mots_ = d["mots"]
        ordre = sorted(lst, key=lambda t: (t[1] != k_ev, mots_[t[0]].get("intensite") != "F", t[1] not in cc0,
                                           t[1] not in rech0, t[1] not in plan0, t[0]))
        vus_ = []
        for i, k in ordre:
            if k in vus_ or len(vus_) >= 4:
                if k not in vus_:
                    retirer_i.add(i)
                    notes.append(f"{k} : mot retiré (plus de 4 cartes ancrées dans la strate {st})")
                continue
            vus_.append(k)
    if retirer_i:
        d["mots"] = [m for i, m in enumerate(d["mots"]) if i not in retirer_i]
        partis = {n_.split(" :")[0] for n_ in notes if "plus de 4 cartes ancrées" in n_}
        d["candidats"] = [c for c in d.get("candidats") or [] if not (isinstance(c, str) and c in partis)]
    fm = {f"{m.get('carte')}@{m.get('strate')}" for m in d.get("mots") or [] if isinstance(m, dict)}
    # 0 ter (0.10.48). Questions de discrimination (exigées au premier état d'un cas réel) : réparées dans la forme,
    # jamais dans le fond. Branches normalisées (CARTE@strate) ; deux branches vers la même carte → « non » mène à
    # « indetermine » (non A ne vaut pas B) ; justification manquante inscrite comme telle, par le bot. Une question
    # irréparable est retirée ; s'il n'en reste aucune qui départage, le bot en pose une sur la carte ancrée, signalée.
    if M is not None:
        bot = "non fournie par le lecteur (inscrite par le bot, 0.10.48)"
        qs = []
        for q in d.get("questions") if isinstance(d.get("questions"), list) else []:
            if not isinstance(q, dict):
                continue
            q = dict(q)
            if q.get("type") != "documentation":
                for b_ in ("si_oui", "si_non"):
                    v_ = str(q.get(b_) or "")
                    if v_ != M.INDETERMINE:
                        q[b_] = avec_strate(v_) if v_ else M.INDETERMINE
                if q.get("si_oui") == q.get("si_non"):
                    q["si_non"] = M.INDETERMINE
                    notes.append(f"question « {str(q.get('question'))[:40]} » : branche non → indetermine (décorative)")
                j_ = q.get("justification") if isinstance(q.get("justification"), dict) else {}
                for rep_ in ("oui", "non"):
                    if not (isinstance(j_.get(rep_), str) and j_[rep_].strip()):
                        j_[rep_] = f"{bot} : « {rep_} » mène à {q.get('si_' + rep_)}"
                q["justification"] = j_
                if not (isinstance(q.get("resolution"), str) and q["resolution"].strip()):
                    q["resolution"] = f"{bot} : l'observation datée qui trancherait entre {q.get('si_oui')} et {q.get('si_non')}"
            try:
                ok = not M.controle_questions([q], fm, False, True)
            except Exception:
                ok = False
            if ok:
                qs.append(q)
            else:
                notes.append(f"question irréparable retirée : {str(q.get('question'))[:60]}")
        if fm and not any(q.get("type") != "documentation" for q in qs):
            k0 = sorted(fm)[0]
            qs.append({"question": f"Un fait suffisant établit-il {k0} dans la fenêtre ? (question inscrite par le bot)",
                       "si_oui": k0, "si_non": M.INDETERMINE,
                       "resolution": "une source primaire datée qui remplit un marqueur de la carte",
                       "justification": {"oui": f"{bot} : un fait suffisant établit {k0}",
                                         "non": f"{bot} : sans ce fait, le codage reste ouvert"}})
            notes.append(f"question de discrimination inscrite par le bot sur {k0}")
        d["questions"] = qs
    # 1. liaisons : « A@s type B@s » ; un objet {de, type, vers} est réécrit, le reste retiré
    # 0.10.52 : le moteur exige une preuve par liaison (preuves_liaisons, même ordre) ; aucune consigne ne la demandait,
    # donc tout dossier qui gardait une liaison aurait été refusé. Une preuve vient de preuves_liaisons[i] ou du champ
    # « preuve » d'un objet ; une liaison sans preuve est retirée (conséquence écrite de la règle), avec sa trace.
    preuves_in = d.get("preuves_liaisons") if isinstance(d.get("preuves_liaisons"), list) else []
    presentes_ = {cle_normale(f"{m.get('carte')}@{m.get('strate')}") for m in d.get("mots") or [] if isinstance(m, dict)}
    garde, preuves = [], []
    for i, li in enumerate(d.get("liaisons") or []):
        pr = preuves_in[i] if i < len(preuves_in) else None
        if isinstance(li, dict):
            pr = li.get("preuve") or pr
            a, t, b = (li.get(k) for k in ("de", "type", "vers"))
            if not all(isinstance(x, str) and x.strip() for x in (a, t, b)):
                a, t, b = (li.get(k) for k in ("a", "type", "b"))
            if all(isinstance(x, str) and x.strip() for x in (a, t, b)):
                li = f"{cle_normale(a)} {t.strip()} {cle_normale(b)}"
        if not (isinstance(li, str) and len(li.split()) == 3 and li.split()[1].strip("—-→>") in LIAISONS_ADMISES):
            notes.append(f"liaison illisible retirée : {str(li)[:80]}")
            # 0.10.52 (§51) : une liaison hors liste est gardée à part, jamais calculée : un verbe qui revient, chez
            # plusieurs lecteurs, est un symbole candidat ; on ne le traduit pas (ce serait l'interpréter à sa place)
            if isinstance(li, str) and len(li.split()) == 3:
                d.setdefault("_liaisons_hors_liste", []).append(li)
            continue
        a_, t_, b_ = li.split()
        averti = t_.strip("—-→>") == "averti"
        # 0.10.55 : types d'une même strate et types entre strates (grammaire G3) ; un type hors de sa place est retiré
        # (banc du 2026-11-12 : « TRC@6 tension POL@7 », refus du dossier entier)
        sa_, sb_ = cle_normale(a_).partition("@")[2], cle_normale(b_).partition("@")[2]
        meme_ = sa_ == sb_
        t0_ = t_.strip("—-→>").replace("echo", "écho")
        if not averti and ((meme_ and t0_ in ("transfert", "écho")) or (not meme_ and t0_ not in ("transfert", "écho", "conflit"))):
            notes.append(f"liaison retirée, type incompatible avec ses strates : {li[:80]}")
            continue
        # une liaison relie des mots de l'état ; seule « averti » peut viser l'événement (sa source reste un mot)
        if cle_normale(a_) not in presentes_ or (cle_normale(b_) not in presentes_ and not averti):
            notes.append(f"liaison retirée, mot absent de l'état : {li[:80]}")
            continue
        if not (isinstance(pr, str) and pr.strip()):
            notes.append(f"liaison retirée, sans preuve : {li[:80]}")
            continue
        garde.append(li)
        preuves.append(pr.strip()[:300])
    d["liaisons"] = garde
    if garde:
        d["preuves_liaisons"] = preuves
    else:
        d.pop("preuves_liaisons", None)
    # 1 bis. un rejet sans motif (0.10.47) : « non examinée », catégorie non cherchée (effort 0)
    for k, v in list((d.get("rejets") or {}).items()):
        if not re.sub(r"^\[[^\]]*\]", "", str(v or "")).strip():
            d["rejets"][k] = "[non_cherchee] motif non donné par le lecteur : candidate non examinée"
            d.setdefault("_categories_rejet", {})[k] = "non_cherchee"
            notes.append(f"rejet sans motif complété : {k}")
    # 2. une carte ancrée n'est pas rejetée
    for k in [k for k in d.get("rejets") or {} if cle_normale(k) in fm]:
        d["rejets"].pop(k, None)
        (d.get("_categories_rejet") or {}).pop(k, None)
        notes.append(f"rejet retiré pour {k} : la carte est ancrée dans l'état")
    # 3. candidates : chaque mot en est une ; 2 au moins par strate de l'état, prises dans le plan
    cand = [cle_normale(c) for c in d.get("candidats") or [] if isinstance(c, str)]
    for k in sorted(fm - set(cand)):
        cand.append(k)
        notes.append(f"candidate ajoutée : {k} (mot de l'état)")
    for st in sorted({k.split("@")[1] for k in fm}):
        dans = [c for c in cand if c.endswith(f"@{st}")]
        for c in [cle_normale(x) for x in plan.get("candidats") or [] if isinstance(x, str)]:
            if len(dans) >= 2:
                break
            if c.endswith(f"@{st}") and c not in cand:
                cand.append(c)
                dans.append(c)
                d.setdefault("rejets", {})[c] = "[non_cherchee] candidate du plan, non examinée par le lecteur (ajoutée par le bot)"
                d.setdefault("_categories_rejet", {})[c] = "non_cherchee"
                notes.append(f"candidate ajoutée : {c} (plan), rejet « non cherchée »")
    # 3 bis (0.10.51) : si le plan n'a pas de candidate dans la strate, une voisine de la carte ancrée (fiche du skill)
    if M is not None:
        try:
            vois = M.voisines()
        except Exception:
            vois = {}
        for st in sorted({k.split("@")[1] for k in fm}):
            dans = [c for c in cand if c.endswith(f"@{st}")]
            for k in sorted(x for x in fm if x.endswith(f"@{st}")):
                for v_ in sorted(vois.get(k.split("@")[0], ())):
                    c = f"{v_}@{st}"
                    if len(dans) >= 2:
                        break
                    if c not in cand and not M.hors_domaine(c):
                        cand.append(c)
                        dans.append(c)
                        d.setdefault("rejets", {})[c] = "[non_cherchee] voisine de la carte ancrée, non examinée (ajoutée par le bot)"
                        d.setdefault("_categories_rejet", {})[c] = "non_cherchee"
                        notes.append(f"candidate ajoutée : {c} (voisine de {k})")
    # 3 ter (0.10.78, banc du 2026-11-13 : 5 candidates déclarées dans une strate, dossier refusé). Au plus 4 par
    #    strate : on garde d'abord les cartes ancrées, puis les contre-candidates, puis les cartes visées par une
    #    recherche, puis celles du plan, dans l'ordre du lecteur ; les autres sortent, avec leur rejet éventuel (tracé).
    cc_ = {cle_normale(c) for c in d.get("contre_candidate") or [] if isinstance(c, str)}
    rech_ = set()
    for r in d.get("recherches") or []:
        for c in r.get("cartes") or []:
            try:
                rech_.add(cle_normale(c))
            except Exception:
                pass
    plan_ = {cle_normale(c) for c in plan.get("candidats") or [] if isinstance(c, str)}
    for st in sorted({c.split("@")[1] for c in cand if "@" in c}):
        dans = [c for c in cand if c.endswith(f"@{st}")]
        if len(dans) <= 4:
            continue
        rang = {c: i for i, c in enumerate(dans)}
        ordre = sorted(dans, key=lambda c: (c not in fm, c not in cc_, c not in rech_, c not in plan_, rang[c]))
        garder = set(ordre[:max(4, sum(1 for c in dans if c in fm))])
        for c in dans:
            if c not in garder:
                cand.remove(c)
                (d.get("rejets") or {}).pop(c, None)
                (d.get("_categories_rejet") or {}).pop(c, None)
                notes.append(f"candidate écartée : {c} (plus de 4 candidates dans la strate {st})")
    # 4. un rejet porte sur une candidate : la carte rejetée entre dans les candidates s'il reste de la place (4 par
    #    strate), sinon le rejet est retiré (le moteur refuse un rejet hors des candidates)
    for k in list((d.get("rejets") or {}).keys()):
        if k in cand or "@" not in k:
            continue
        if sum(1 for c in cand if c.endswith("@" + k.split("@")[1])) < 4:
            cand.append(k)
            notes.append(f"candidate ajoutée : {k} (rejetée par le lecteur)")
        else:
            d["rejets"].pop(k)
            (d.get("_categories_rejet") or {}).pop(k, None)
            notes.append(f"rejet retiré pour {k} : hors des candidates, strate pleine")
    # 4 bis (0.10.68, banc multi-lecteurs : Mistral Medium, 10 dossiers refusés sur 20). Une recherche consignée vise
    #    des cartes du plan ; le moteur exige qu'elles soient candidates. Une carte visée hors des candidates de la
    #    lecture sort de la recherche (elle n'y entre pas : la classer « non cherchée » ferait d'un état nul un angle
    #    mort et relancerait des recherches) ; une recherche sans carte sort du dossier (couverture A7 perdue → dossier
    #    Spéculatif). La réparation retire, elle n'ajoute rien.
    gardees = []
    for r in d.get("recherches") or []:
        ks = []
        for c in r.get("cartes") or []:
            try:
                k = cle_normale(c)
            except Exception:
                continue
            if k in cand and k not in ks:
                ks.append(k)
        ks = ks[:2]
        if ks:
            if ks != r.get("cartes"):
                notes.append(f"recherche « {str(r.get('requete'))[:40]} » : cartes ramenées à {', '.join(ks)}")
            gardees.append(dict(r, cartes=ks))
        else:
            notes.append(f"recherche retirée (cartes hors des candidates) : « {str(r.get('requete'))[:40]} »")
    if "recherches" in d:
        d["recherches"] = gardees
    d["candidats"] = cand
    # 5. une contre-candidate par strate de l'état, prise parmi les candidates (de préférence non ancrée)
    contre = [c for c in d.get("contre_candidate") or [] if c in cand]
    for st in sorted({k.split("@")[1] for k in fm}):
        if not any(c.endswith(f"@{st}") for c in contre):
            choix = [c for c in cand if c.endswith(f"@{st}") and c not in fm] or [c for c in cand if c.endswith(f"@{st}")]
            if choix:
                contre.append(choix[0])
                notes.append(f"contre-candidate ajoutée : {choix[0]}")
    d["contre_candidate"] = contre
    # 6 (0.10.51). Toute candidate non ancrée a un motif de rejet (sinon « texte renseigné requis »)
    for c in cand:
        if c not in fm and not str((d.get("rejets") or {}).get(c) or "").strip():
            d.setdefault("rejets", {})[c] = "[non_cherchee] motif non donné par le lecteur : candidate non examinée"
            d.setdefault("_categories_rejet", {})[c] = "non_cherchee"
            notes.append(f"rejet ajouté pour {c} (candidate sans motif)")
    return notes


def controle_plan(plan: dict) -> str | None:
    normaliser_plan(plan)
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
    present = any(m["carte"] == ev["carte"] and entier_strate(m["strate"]) == entier_strate(ev["strate"])
                  for m in dossier.get("mots", []))
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
SÉRIE EN CROISSANCE (0.10.19) : si la question demande qu'une grandeur qui croît avec le temps (dépenses, PIB, dette, prix, population, puissance de calcul…) dépasse un NIVEAU, ne compte pas combien de fois ce niveau a été dépassé dans le passé (jamais, s'il est nouveau : la fréquence serait fausse) ; compte combien de fois, sur des fenêtres de même durée, la grandeur a progressé d'au moins le rapport seuil / dernière valeur connue (en %). Même chose à la baisse.

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
                           vue_calculee: dict | None = None, ancrage: dict | None = None,
                           compte_echoue: dict | None = None) -> tuple[dict | None, dict]:
    """0.3.0 : NB_VUES estimations indépendantes du taux de base ; on garde la vue MÉDIANE (une vraie vue, avec sa
    source : aucun chiffre n'est fabriqué par moyenne). La dispersion est journalisée : c'est la mesure de stabilité
    de B demandée avant toute autre décision sur B."""
    # 0.8.0 (audit M-01) : chaque vue sur une source différente des précédentes. (M-03) : un compte « proche » n'ancre
    # que la PREMIÈRE vue ; les autres restent aveugles, ce qui garde une mesure de B indépendante du compte.
    valides, refus, sources = [], [], []
    for i in range(NB_VUES):
        anc = ancrage if i == 0 else None
        try:
            v = extraire_json(await llm(consigne_vue(q, plan, refs, aujourdhui, jours, hist, classe, anc, sources,
                                                     compte_echoue)))
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


def methode_B(c: dict) -> str:
    """0.10.19 : comment B a été obtenu : compte des puits (et sa méthode), vue fixée par le banc, ou vue du modèle."""
    vue = c.get("vue") or {}
    if (c.get("vues") or {}).get("fixee"):
        return "fixee"
    if vue.get("compte_calcule"):
        return "compte_" + str((((c.get("puits") or {}).get("compte")) or {}).get("methode") or "fenetres")
    if vue and c.get("compte_echoue"):
        return "vue_modele_compte_echoue"        # 0.10.34 : distinguée au score (B_par_methode)
    return "vue_modele" if vue else "aucune"


def discordance(p_B: float | None, p_A: float | None, methode: str | None = None) -> dict | None:
    """0.10.19 : alarme de discordance. Le bras A (modèle seul) sert de témoin : si B et A diffèrent de plus d'un
    facteur 4 sur les cotes, la question est marquée « B discordant ». Ne change rien à ce qui est posté."""
    if p_B is None or p_A is None:
        return None
    lo = lambda p: math.log(min(0.999, max(0.001, p)) / (1 - min(0.999, max(0.001, p))))
    ecart = lo(p_B) - lo(p_A)
    return {"rapport_cotes": round(math.exp(abs(ecart)), 2), "sens": "B_plus_bas" if ecart < 0 else "B_plus_haut",
            "alarme": abs(ecart) > math.log(4), "methode_B": methode}


def repetition_A(ps: list[float]) -> dict:
    """0.10.5 (skill 0.7.58, §35) : K essais indépendants du bras A (Murphy 2026 : la moyenne simple de 5 essais
    améliore le score, un peu plus que la moyenne des logits). En ombre : sert de référence honnête pour C."""
    ps = [borner(float(x)) for x in ps if isinstance(x, (int, float))]
    lg = [math.log(x / (1 - x)) for x in ps]
    return {"n": len(ps), "p": ps, "moyenne": sum(ps) / len(ps),
            "moyenne_logit": 1 / (1 + math.exp(-sum(lg) / len(lg))),
            "ecart_type": statistics.pstdev(ps) if len(ps) > 1 else 0.0}


def _domaine_url(ligne: str) -> str | None:
    m = re.search(r"https?://(?:www\.)?([^/\s?#]+)", ligne or "")
    return m.group(1).lower() if m else None


def vues_disjointes(executees: list[dict]) -> tuple[list[dict], list[dict], dict]:
    """0.10.11 (§39) : deux « bonnes vues » de la même situation (Balestriero & LeCun 2026) : les mêmes requêtes, mais
    des SOURCES disjointes. Chaque résultat est découpé en items (« [date] titre — url », séparés par une ligne vide) ;
    un item va à la vue A ou B selon l'empreinte de son domaine, donc un même site ne nourrit jamais les deux vues."""
    a, b, n = [], [], {"A": 0, "B": 0, "sans_domaine": 0}
    for r in executees:
        if not r.get("executee") or not r.get("resultat"):
            continue
        items = [x for x in re.split(r"\n\s*\n", str(r["resultat"])) if x.strip()]
        va, vb = [], []
        for it in items:
            d = _domaine_url(it.splitlines()[0] if it.splitlines() else it)
            if d is None:
                n["sans_domaine"] += 1
                continue
            (va if int(hashlib.sha256(d.encode()).hexdigest(), 16) % 2 == 0 else vb).append(it)
        n["A"] += len(va); n["B"] += len(vb)
        a.append(dict(r, resultat="\n\n".join(va), executee=bool(va)))
        b.append(dict(r, resultat="\n\n".join(vb), executee=bool(vb)))
    return a, b, n


def accord_vues(plan: dict, lec_a: dict, lec_b: dict) -> dict:
    """0.10.11 (§39) : sur les candidates du plan, ancrée ou non dans chaque vue ; Jaccard des ensembles ancrés, accord
    par candidate, intensités comparées là où les deux vues ancrent."""
    def ancres(lec):
        return {f"{m.get('carte')}@{m.get('strate')}": m.get("intensite") for m in (lec or {}).get("mots") or []}
    noms = noms_cartes()
    norm = lambda k: k if "@" not in k else f"{noms.get(k.split('@')[0], k.split('@')[0])}@{k.split('@')[1]}"
    xa = {norm(k): v for k, v in ancres(lec_a).items()}
    xb = {norm(k): v for k, v in ancres(lec_b).items()}
    cands = [norm(c) for c in plan.get("candidats") or []]
    union = set(xa) | set(xb)
    m_ = _moteur()
    code = lambda k: f"{m_.carte_id(k.split('@')[0])}@{k.split('@')[1]}"
    try:   # 0.10.13 (skill 0.7.65, §42) : accord au niveau de la famille (carte et voisines A6)
        famille = m_.accord_deux_niveaux([code(k) for k in xa], [code(k) for k in xb])["accord_famille"]
    except (ValueError, IndexError):
        famille = None
    return {"ancrees_A": sorted(xa), "ancrees_B": sorted(xb), "accord_famille": famille,
            "jaccard": (len(set(xa) & set(xb)) / len(union)) if union else 1.0,
            "candidates": [{"carte": c, "A": c in xa, "B": c in xb} for c in cands],
            "meme_intensite": sum(1 for k in set(xa) & set(xb) if xa[k] == xb[k]),
            "communes": len(set(xa) & set(xb))}


try:
    NEGATION_TAUX = max(0.0, min(1.0, float(os.environ.get("ALPHABET_NEGATION_TAUX") or 0)))
except ValueError:
    NEGATION_TAUX = 0.0


def tirage_negation(qid) -> bool:
    """0.10.34 : sélection déterministe d'une part NEGATION_TAUX des questions binaires."""
    return NEGATION_TAUX > 0 and int(hashlib.sha256(f"negation:{qid}".encode()).hexdigest()[:8], 16) / 0xFFFFFFFF < NEGATION_TAUX


def consigne_negation(titre: str, criteres: str, precisions: str) -> str:
    """0.10.34 (d'après Lv et al., ICML 2026 : l'inversion logique fait chuter les agents) : réécrire la question en
    son CONTRAIRE exact, critères compris ; « oui » à la question niée = « non » à l'originale."""
    return f"""Réécris cette question de prévision en son CONTRAIRE EXACT : la réponse « oui » à ta question doit
correspondre exactement à la réponse « non » à l'originale, et inversement. Garde la langue, les dates, les seuils et
la source de résolution ; inverse seulement l'événement (« X arrivera-t-il ? » → « X n'arrivera-t-il pas ? » ; « au
moins N » → « moins de N »). Réécris aussi les critères et les précisions dans le même sens.

TITRE : {titre}
CRITÈRES : {criteres[:3000]}
PRÉCISIONS : {precisions[:2000]}

Rends un seul objet JSON : {{"titre": "...", "criteres": "...", "precisions": "..."}}"""


def coherence_negation(p: float, p_niee: float) -> dict:
    """Écart à la cohérence : p(question) + p(question niée) devrait valoir 1."""
    return {"p_A": round(p, 4), "p_A_niee": round(p_niee, 4), "somme": round(p + p_niee, 4),
            "incoherence": round(abs(p + p_niee - 1), 4)}


FIDELITE = os.environ.get("ALPHABET_FIDELITE", "0") in ("1", "oui", "true")
TYPES_ECART = ("evenement_plus_facile", "evenement_plus_difficile", "autre_evenement", "negation", "mauvaise_fenetre",
               "mauvaise_semantique", "autre")


def consigne_fidelite(q: Question, plan: dict, jours: int) -> str:
    """0.10.35 (décision d'auteur du 2026-11-11, d'après Humanize, arXiv 2610.13632 : un succès apparent peut cacher
    une lecture affaiblie de la tâche, que le vérificateur formel ne voit pas) : un relecteur qui ne voit QUE la
    question et sa formalisation (événement, sémantique, fenêtre), pas le raisonnement du planificateur, dit si la
    formalisation est fidèle."""
    import preselection
    ev = plan.get("evenement") or {}
    try:
        defin = preselection.textes_cartes().get(_moteur().carte_id(str(ev.get("carte"))), "")
    except ValueError:
        defin = ""
    return f"""Tu es RELECTEUR DE FIDÉLITÉ. Une question de prévision a été traduite en un événement formel, que le
calcul va estimer. Tu ne vois pas le raisonnement de celui qui a traduit : seulement la question et la traduction.
Dis si la traduction est FIDÈLE : « oui » à l'événement formel doit correspondre à « oui » à la question, dans la même
fenêtre, ni plus facile, ni plus difficile, ni à l'envers.

QUESTION : {q.titre}
CRITÈRES DE RÉSOLUTION : {q.criteres[:3000]}
PRÉCISIONS : {q.precisions[:1500]}
RÉSOLUTION : {q.resolution.isoformat()} (fenêtre de {jours} jours)

TRADUCTION FORMELLE :
  événement : la carte {ev.get('carte')} « {ev.get('type')} » dans la strate {ev.get('strate')}
  définition de la carte : {defin}
  sémantique : {plan.get('semantique')}

Écarts possibles : {", ".join(TYPES_ECART)}.
Rends UNIQUEMENT un objet JSON :
{{"fidele": "oui" | "partiel" | "non", "ecarts": [{{"type": "...", "motif": "une phrase"}}]}}"""


async def relire_fidelite(q: Question, plan: dict, jours: int, llm: Llm) -> dict:
    try:
        r = await json_avec_reprise(llm, consigne_fidelite(q, plan, jours))
        f = str(r.get("fidele") or "").lower()
        ecarts = [{"type": str(e.get("type"))[:40], "motif": str(e.get("motif"))[:300]}
                  for e in (r.get("ecarts") or []) if isinstance(e, dict)][:5]
        return {"statut": "relu", "fidele": f if f in ("oui", "partiel", "non") else "illisible", "ecarts": ecarts}
    except Exception as e:  # une relecture en ombre qui échoue ne bloque rien
        return {"statut": "erreur", "motif": f"{type(e).__name__}: {e}"[:200]}


def tirage_invariance(qid) -> bool:
    """Sélection déterministe d'une part INVARIANCE_TAUX des questions (empreinte de l'identifiant)."""
    return INVARIANCE_TAUX > 0 and int(hashlib.sha256(f"invariance:{qid}".encode()).hexdigest()[:8], 16) / 0xFFFFFFFF < INVARIANCE_TAUX


async def tester_invariance(q: Question, plan: dict, executees: list[dict], llm: Llm, aujourdhui: str, jours: int) -> dict:
    """0.10.11 (§39), en ombre : le même lecteur, la même consigne, sur deux vues aux sources disjointes. Si les cartes
    ancrées diffèrent, le lecteur lit le registre des sources, pas la situation. Ne touche ni C ni le dossier."""
    va, vb, n = vues_disjointes(executees)
    if not n["A"] or not n["B"]:
        return {"statut": "non_teste", "motif": "une vue sans source", "items": n}
    try:
        la = extraire_json(await llm(consigne_dossier(q, plan, va, aujourdhui, jours)))
        lb = extraire_json(await llm(consigne_dossier(q, plan, vb, aujourdhui, jours)))
    except Exception as e:
        return {"statut": "erreur", "motif": f"{type(e).__name__}: {e}"[:200], "items": n}
    return {"statut": "teste", "items": n, **accord_vues(plan, la, lb)}


def consigne_traduction(q: Question, plan: dict, lecture: dict, textes: str) -> str:
    """0.10.7 (skill §37, Wong et al. 2023) : le TRADUCTEUR. Il ne lit pas la situation et ne chiffre rien : il traduit
    en instructions ce que les textes AFFIRMENT des liens entre structures dans CE cas. Appel séparé, après la lecture :
    la consigne de lecture, donc C, ne change pas."""
    ev = plan["evenement"]
    noms = noms_cartes()
    s = ev["strate"]
    cible = f"{noms.get(ev['carte'], ev['carte'])}@{s}"
    ancrees = [f"{m.get('carte')}@{m.get('strate')}" for m in lecture.get("mots") or []]
    rejetees = list((lecture.get("rejets") or {}).keys()) if isinstance(lecture.get("rejets"), dict) else []
    cartes = ", ".join(f"{n}@{s}" for c, n in sorted(noms.items()) if c != ev["carte"])
    return f"""Tu es un TRADUCTEUR, pas un analyste. Une lecture structurelle a été faite ; tu ne la refais pas, tu ne
donnes aucune probabilité. Tu traduis seulement, en instructions, ce que les TEXTES CI-DESSOUS affirment explicitement
des liens entre structures dans ce cas précis.

Question : {q.titre}
Événement visé (la cible) : {cible} ({ev['type']})
Cartes ancrées par la lecture : {", ".join(ancrees) or "aucune"}
Cartes examinées et rejetées : {", ".join(rejetees) or "aucune"}
Cartes de la strate : {cartes}

Trois instructions possibles, et seulement celles-ci :
- {{"instruction": "lien", "de": "CARTE@{s}", "vers": "CARTE@{s}" ou "cible", "extrait": "..."}} : le texte dit que
  l'une produit l'autre (ou mène à l'événement) DANS CE CAS ;
- {{"instruction": "bloque", "de": "CARTE@{s}", "extrait": "..."}} : le texte dit que la voie de cette structure vers
  l'événement est coupée ou neutralisée DANS CE CAS ;
- {{"instruction": "exclut", "a": "CARTE@{s}", "b": "CARTE@{s}", "extrait": "..."}} : le texte dit que les deux ne
  peuvent coexister DANS CE CAS.

Règles : chaque instruction cite un « extrait » recopié MOT POUR MOT des textes, et « source » : l'adresse (URL) du
résultat d'où vient l'extrait si elle figure dans les textes, sinon "" ; aucune instruction sans phrase qui l'affirme ;
une connaissance générale n'est pas une affirmation du texte ; zéro instruction est une réponse normale.

Réponds par un seul objet JSON : {{"programme": [ ... ]}}

TEXTES :
{textes[:12000]}"""


def extrait_retrouve(extrait: str, textes: str) -> bool:
    """0.10.7 : même règle que le contrôle d'attribution (0.5.2) : l'extrait est dans les textes, ou 70 % au moins de
    ses mots de quatre lettres ou plus y figurent."""
    ne, corpus = _normal(extrait), _normal(textes)
    if not ne:
        return False
    longs = [w for w in ne.split() if len(w) >= 4]
    mots = set(corpus.split())
    return ne in corpus or bool(longs and sum(w in mots for w in longs) / len(longs) >= 0.7)


async def traduire(q: Question, plan: dict, lecture: dict, textes: str, llm: Llm) -> dict:
    """0.10.7 : un appel, en ombre. Les instructions dont l'extrait n'est pas retrouvé dans les textes sont écartées
    ici, sans modèle ; le moteur trie ensuite la forme (programme_valide). Toute erreur rend un programme vide."""
    try:
        brut = extraire_json(await llm(consigne_traduction(q, plan, lecture, textes))).get("programme")
    except Exception as e:
        return {"programme": [], "ecartees": [], "erreur": f"{type(e).__name__}: {e}"[:200]}
    garde, ecartees = [], []
    for x in brut if isinstance(brut, list) else []:
        if isinstance(x, dict) and extrait_retrouve(str(x.get("extrait") or ""), textes):
            garde.append(x)
        else:
            ecartees.append({"instruction": x, "motif": "extrait non retrouvé dans les textes"})
    return {"programme": garde, "ecartees": ecartees}


def ombre_causale(sortie: dict) -> dict | None:
    """0.10.3 (skill 0.7.56, validation §33) : deux sondes du moteur, en ombre, jamais publiées. `p_mediation` : p
    sous la règle des médiateurs (arête lue comme effet total ; le médiateur est écarté) ; `ablation` : p quand chaque
    carte est retirée seule (contraste dans le modèle, pas contrefactuel)."""
    sb = (sortie or {}).get("sensibilite") or {}
    if not sb:
        return None
    med = sb.get("mediation") or {}
    # 0.10.4 (skill 0.7.57, §34) : cartes lues comme des causes (noisy-or), et borne de ce qu'une carte de plus
    # pourrait changer (« arret » : la recherche aurait pu s'arrêter ; elle ne s'arrête pas, le nombre de tours est fixe).
    vi = sb.get("valeur_information") or {}
    return {"p_mediation": med.get("p"), "mediateurs_retires": med.get("mediateurs_retires"),
            "ablation": sb.get("ablation"), "p_noisy_or": (sb.get("noisy_or") or {}).get("p"),
            # 0.10.52 (skill 0.7.75, §51) : indices déclarés « averti » en produit, autres sources en noisy-or
            "p_mixte_averti": (sb.get("mixte_averti") or {}).get("p"),
            "indices_averti": (sb.get("mixte_averti") or {}).get("indices"),
            "valeur_information": {k: vi.get(k) for k in ("borne", "seuil", "arret", "plus_influentes")} if vi else None,
            "tempere": sb.get("tempere"),
            # 0.10.6 (skill 0.7.59, §36) : programme génératif conditionné sur ancrages ET rejets ; bande sur π et le lecteur
            "generatif": ({k: (sb.get("generatif") or {}).get(k) for k in ("p", "bande", "rejets_utilises",
                                                                           "rejets_categories", "surprise")}
                          if sb.get("generatif") else None),
            # 0.10.7 (skill 0.7.60, §37) : lecture probabiliste (traducteur → instructions → programme génératif)
            "lecture_probabiliste": sb.get("lecture_probabiliste"),
            "sans_plafond": sb.get("sans_plafond"),
            "avec_freins": sb.get("avec_freins")}   # 0.10.42 (skill 0.7.73, §49) : les freins, en ombre   # 0.10.9 (§38) : le même calcul sans troncature   # 0.10.5 (§35) : p pour α fixés d'avance ; α = 0,5 est la comparaison principale


async def alphabet(q: Question, recherche: str, llm: Llm, chercher: Chercheur, recherche_reelle: bool,
                   aujourdhui: str, jours: int, historique: Historique | None = None,
                   critique: Llm | None = None, vue_fixee: dict | None = None,
                   donnees_fixees: str | None = None) -> dict:
    """0.9.0 : hors strate 7, la lecture exploratoire est rangée dans « exploratoire » et le statut reste
    « hors_strate » : la règle de publication ne voit rien (A posté, jamais B ni C), le registre garde tout.
    0.9.7 : `vue_fixee` et `donnees_fixees` servent le banc « sans texte » (alphabet-chaine) : le taux de base vient
    du banc et les faits sont des relevés de données, cités par source ; le bot Metaculus ne les passe jamais."""
    c = await _alphabet(q, recherche, llm, chercher, recherche_reelle, aujourdhui, jours, historique, critique,
                        vue_fixee, donnees_fixees)
    try:
        c["symetrique"] = symetrique(c)        # 0.9.1 : en ombre, partout où c'est calculable
    except Exception as e:
        c["symetrique"] = {"erreur": f"{type(e).__name__}: {e}"[:200]}
    if not c.pop("_explo", False):
        return c
    strate = ((c.get("plan") or {}).get("evenement") or {}).get("strate")
    explo = {k: c.get(k) for k in ("statut", "p_C", "p_sans_cartes", "motif", "nature_etat_nul", "rho", "tentatives",
                                   "reprises_json", "etat", "drapeaux", "ombre_causale", "derniere_erreur",
                                   "empreintes_passages", "tiers_polarite", "ombre_filtrage", "ombre_series",
                                   "ombre_nouveau_depart")
             if c.get(k) is not None}
    if (c.get("dossier") or {}).get("_liaisons_hors_liste"):      # 0.10.52 (§51) : verbes inventés par le lecteur
        explo["liaisons_hors_liste"] = c["dossier"]["_liaisons_hors_liste"]
    if explo.get("statut") == "refuse":     # 0.10.46 : le dossier refusé est gardé, pour qu'un refus se diagnostique
        d_ = c.get("dossier") or {}
        explo["dossier_refuse"] = {k: d_.get(k) for k in ("candidats", "contre_candidate", "mots", "rejets", "liaisons", "questions",
                                                          "_reparations", "_liaisons_hors_liste") if k in d_}
    explo["strate"] = strate
    explo["p_C_corrige"] = corriger_C(explo.get("p_C"), correction_retro())   # 0.9.1 : la correction en ombre aussi
    explo["p_C_symetrique"] = (c.get("symetrique") or {}).get("p")
    for k in ("p_C", "p_sans_cartes", "rho", "nature_etat_nul", "ombre_causale"):
        c.pop(k, None)
    c.update(statut="hors_strate", exploratoire=explo,
             motif=f"strate {strate} non chiffrée (L7) : lecture exploratoire scellée, non postée "
                   f"({explo.get('statut')})")
    return c


async def _alphabet(q: Question, recherche: str, llm: Llm, chercher: Chercheur, recherche_reelle: bool,
                    aujourdhui: str, jours: int, historique: Historique | None = None,
                    critique: Llm | None = None, vue_fixee: dict | None = None,
                    donnees_fixees: str | None = None) -> dict:
    """Bras B et C. statut : estime | etat_nul | non_estime | refuse | sans_vue | hors_alphabet | hors_strate
    | lu_non_chiffre (et « erreur », posé par prevoir_binaire si une exception échappe)."""
    trace: dict = {"statut": "refuse", "tentatives": 0}
    try:
        plan = await json_avec_reprise(llm, consigne_plan(q, recherche, aujourdhui), trace, "plan")
    except Exception as e:
        if est_panne(e):
            return dict(trace, statut="panne", motif=f"panne au plan : {type(e).__name__}: {e}"[:300])
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
            if est_panne(e):
                return dict(trace, plan=plan, statut="panne", motif=f"panne au plan : {type(e).__name__}: {e}"[:300])
            return dict(trace, plan=plan, motif=f"plan corrigé illisible : {e}")
        motif = controle_plan(plan)
    trace["plan"] = plan
    if motif:
        return dict(trace, statut="refuse" if plan_corrigeable(motif) else "hors_alphabet", motif=motif)
    import preselection   # 0.10.15 : présélection des cartes par plongement multilingue, en ombre
    if preselection.ACTIVE:
        trace["preselection"] = await asyncio.to_thread(preselection.preselectionner, q, plan)
    if FIDELITE and vue_fixee is None:   # 0.10.35 : relecteur de fidélité du plan, en ombre (contradicteur s'il existe)
        trace["fidelite_plan"] = await relire_fidelite(q, plan, jours, critique or llm)

    if vue_fixee is not None:          # 0.9.7 : banc sans texte, taux de base fourni par le banc
        motif = controle_vue(vue_fixee, aujourdhui)
        if motif:
            return dict(trace, plan=plan, statut="sans_vue", motif=motif)
        vue, trace["vues"] = vue_fixee, {"fixee": True}
    else:
        vue, trace = await _vue_par_recherche(q, plan, llm, chercher, recherche_reelle, aujourdhui, jours,
                                              historique, trace)
        if vue is None:
            return trace
    trace["vue"] = vue
    trace["p_B"] = float(vue["frequence"])
    return await _lecture(q, plan, vue, llm, chercher, recherche_reelle, aujourdhui, jours, critique, trace,
                          donnees_fixees)


async def _vue_par_recherche(q: Question, plan: dict, llm: Llm, chercher: Chercheur, recherche_reelle: bool,
                             aujourdhui: str, jours: int, historique: Historique | None,
                             trace: dict) -> tuple[dict | None, dict]:
    # 1. Vue extérieure d'abord, sur ses propres recherches (bras B).
    refs = await executer_requetes([{"requete": x} for x in (plan.get("recherches_reference") or []) if isinstance(x, str)],
                                   chercher, recherche_reelle, MAX_RECHERCHES_REFERENCE)
    trace["recherches_reference"] = [{k: v for k, v in r.items() if k != "resultat"} for r in refs]
    vue_calc = None
    if PUITS:                        # 0.7.0 : bases ouvertes, bornées à la date d'information
        trace["puits"], donnees, vue_calc = await puits(q, plan, llm, aujourdhui, jours, len(refs) + 1)
        trace["_releves"] = trace["puits"].pop("_releves", [])      # hors registre (volumineux)
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
    # 0.10.34 : un compte prévu et impossible (source en erreur, appel absent) est dit à chaque vue
    echec = None
    cp = (trace.get("puits") or {}).get("compte") if isinstance(trace.get("puits"), dict) else None
    if vue_calc is None and ancrage is None and isinstance(cp, dict) and cp.get("motif"):
        spec = cp.get("spec") or {}
        appels = (trace.get("puits") or {}).get("appels") or []
        rang = spec.get("appel")
        app = appels[rang - 1] if isinstance(rang, int) and 0 < rang <= len(appels) else {}
        echec = {"source": app.get("source") or spec.get("source"),
                 "motif": f"{cp['motif']} ; {app.get('motif')}" if app.get("motif") else cp["motif"]}
        trace["compte_echoue"] = echec
    vue, trace["vues"] = await vues_exterieures(q, plan, refs, hist, llm, aujourdhui, jours, classe, vue_calc, ancrage,
                                                echec)
    if vue is None:
        refus = trace["vues"]["refus"]
        return None, dict(trace, statut="sans_vue", motif=(refus[0] if refus else "vue extérieure absente"))
    return vue, trace


async def _lecture(q: Question, plan: dict, vue: dict, llm: Llm, chercher: Chercheur, recherche_reelle: bool,
                   aujourdhui: str, jours: int, critique: Llm | None, trace: dict,
                   donnees_fixees: str | None = None) -> dict:
    evt, evenement = evenement_depuis(plan, vue)
    hors_strate = entier_strate(plan["evenement"]["strate"]) not in strates_chiffrees()
    if hors_strate and EXPLORATOIRE:
        trace["_explo"] = True
    if hors_strate and not (LECTURE_HORS_STRATE or EXPLORATOIRE):
        return dict(trace, statut="hors_strate", evenement=evenement, semantique=plan["semantique"],
                    motif=f"strate {plan['evenement']['strate']} non chiffrée (L7 : {strates_chiffrees()}) ; "
                          "vue extérieure enregistrée, lecture non lancée")

    # 2. Lecture (bras C).
    if donnees_fixees is not None:      # 0.9.7 : les faits sont les relevés fournis ; ni recherche ni relance
        plan["_donnees"] = donnees_fixees
        executees = []
    else:
        executees = await executer_recherches(plan, chercher, recherche_reelle)
    trace["recherches"] = [sans_resultat(r) for r in executees]
    try:
        lecture = await json_avec_reprise(llm, consigne_dossier(q, plan, executees, aujourdhui, jours), trace, "lecture")
    except Exception as e:
        if est_panne(e):
            return dict(trace, statut="panne", motif=f"panne à la lecture : {type(e).__name__}: {e}"[:300])
        return dict(trace, motif=f"lecture illisible : {e}")
    relance = None
    if donnees_fixees is None:
        lecture, executees, relance = await relancer_angles_morts(q, plan, executees, lecture, llm, chercher,
                                                                  recherche_reelle, aujourdhui, jours)
    # 0.5.2 : le texte des résultats, gardé hors registre pour le contrôle d'attribution (controle_attribution).
    trace["_textes"] = "\n".join(str(r.get("resultat") or "") for r in executees if r.get("executee")) + (
        "\n" + plan["_donnees"] if plan.get("_donnees") else "")
    if relance:
        trace["relance"] = relance
        trace["recherches"] = [sans_resultat(r) for r in executees]
    if donnees_fixees is None and tirage_invariance(q.id):      # 0.10.11 (§39) : test d'invariance, en ombre
        trace["invariance"] = await tester_invariance(q, plan, executees, llm, aujourdhui, jours)
    programme = None
    if TRADUCTION and isinstance(lecture, dict) and (lecture.get("mots") or lecture.get("rejets")):
        tr = await traduire(q, plan, lecture, trace.get("_textes") or "", llm)
        trace["traduction"] = tr
        programme = tr.get("programme") or None
    dossier = None
    # 0.10.54 : de quoi REJOUER la lecture sans le modèle (lectures brutes, plan, événement), pour mesurer une version
    # du réparateur ou du moteur sur les mêmes lectures. Les textes des résultats restent hors registre : le rejeu
    # saute le retrait des faits futurs.
    trace["_rejeu"] = {"lectures": [], "plan": json.loads(json.dumps(plan, ensure_ascii=False, default=str)),
                       "recherches": [{k: r.get(k) for k in ("famille", "cartes", "requete", "executee")}
                                      | ({"empreinte": empreinte(r["resultat"])} if r.get("resultat") else {})
                                      for r in executees],
                       "evt": json.loads(json.dumps(evt, ensure_ascii=False, default=str)), "evenement": evenement,
                       "semantique": plan["semantique"], "aujourdhui": aujourdhui, "jours": jours,
                       "hors_strate": bool(hors_strate), "version_bot": VERSION_BOT,
                       # 0.10.57 : les dates présentes dans les résultats (pas le texte) : le rejeu applique ainsi le
                       # retrait des faits futurs comme le vrai passage
                       "dates_corpus": sorted(set(dates_citees(trace.get("_textes") or "")))}
    for tentative in range(MAX_CORRECTIONS + 1):
        trace["tentatives"] = tentative + 1
        trace["_rejeu"]["lectures"].append(json.loads(json.dumps(lecture, ensure_ascii=False, default=str)))
        dossier = assembler(lecture, plan, executees, evt, aujourdhui, jours)
        # 0.10.64 (§52) : les tiers de POLARITÉ relevés, pour les mesurer sur les issues (aucun effet sur p)
        trace["tiers_polarite"] = [{"mot": f"{m.get('carte')}@{m.get('strate')}", **m["tiers"]}
                                   for m in dossier.get("mots") or [] if isinstance(m, dict)
                                   and isinstance(m.get("tiers"), dict)] or None
        try:                       # traçabilité seulement : une erreur ici ne doit jamais coûter la lecture
            trace["empreintes_passages"] = empreintes_passages(dossier, executees)
        except Exception as e:
            trace["empreintes_passages"] = {"erreur": f"{type(e).__name__}: {e}"[:200]}
        try:                       # 0.10.73 : tâches refaites par le code, EN OMBRE (aucun effet sur la lecture ni sur p)
            import ombres_auto as oa
            trace["ombre_filtrage"] = oa.mesurer_filtrage(executees, f"{q.titre} {q.criteres}", dossier.get("mots"))
            s_ = ((trace.get("puits") or {}).get("compte") or {}).get("spec") or {}
            s_ = s_.get("seuil") if isinstance(s_.get("seuil"), (int, float)) and not isinstance(s_.get("seuil"), bool) else None
            trace["ombre_series"] = oa.comparer_series(trace.get("_releves") or [], s_, dossier.get("mots"))
        except Exception as e:
            trace["ombre_filtrage"] = {"erreur": f"{type(e).__name__}: {e}"[:200]}
        if programme:
            dossier["programme"] = programme      # 0.10.7 : lu par le moteur en ombre seulement (§37)
        futurs = retirer_faits_futurs(dossier, trace.get("_textes") or "", aujourdhui, jours)
        if futurs:
            trace["faits_futurs_retires"] = futurs
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
        if erreur and erreur.startswith(f"événement « {plan['evenement']['type']} » sur une carte absente"):
            # 0.10.44 : on demande si une structure PERSISTE (ou disparaît) et le lecteur ne la trouve pas dans l'état :
            # ce n'est pas une erreur de forme à corriger, c'est une lecture. Sans la carte visée, pas d'ajustement : B.
            trace.update(dossier=dossier, statut="etat_nul", nature_etat_nul="carte_visee_absente", evenement=evenement,
                         semantique=plan["semantique"],
                         motif=f"la carte visée {plan['evenement']['carte']} n'est pas ancrée : pas d'ajustement du taux de base")
            return trace
        if not erreur and hors_strate and not EXPLORATOIRE:
            # Lecture scellée, non chiffrée (mode LIRE ; validation.md §27) : chiffrable après une levée de L7.
            trace.update(dossier=dossier, etat=dossier["etat"], evenement=evenement, semantique=plan["semantique"],
                         statut="lu_non_chiffre",
                         motif=f"strate {plan['evenement']['strate']} non chiffrée (L7) : lecture scellée sans chiffre")
            return trace
        sortie = None
        if not erreur:
            # 0.10.9 (skill 0.7.61, §38) : les catégories de rejet vont au moteur (ombre générative : un rejet pèse selon
            # l'effort de recherche) ; elles ne touchent ni la validation du dossier ni le p publié.
            sortie = appeler_moteur({**{k: v for k, v in dossier.items() if not k.startswith("_")},
                                     "rejets_categories": dict(dossier.get("_categories_rejet") or {})}, dossier["etat"],
                                    evenement, plan["semantique"], aujourdhui, evt["vue_exterieure"], evt["temporalite"],
                                    exploratoire=hors_strate)
            erreur = sortie.get("erreur")
        if not erreur:
            trace.update(dossier=dossier, etat=dossier["etat"], evenement=evenement, semantique=plan["semantique"],
                         p_C=sortie.get("p"), p_sans_cartes=sortie.get("p_sans_cartes"),
                         drapeaux=sortie.get("drapeaux", []), rho=sortie.get("rho"),
                         ombre_causale=ombre_causale(sortie))
            # 0.10.53 : ombre « avec liaisons » (décision d'auteur du 2026-11-12). Le même dossier recalculé avec TOUTES
            # ses liaisons (transfert : pas de décote entre strates ; inclusion, renforcement : une seule des cartes
            # redondantes). Le p publié reste celui sans liaisons ; on comparera sur les issues.
            if sortie.get("p") is not None and any(isinstance(li, str) and len(li.split()) == 3
                                                   and li.split()[1].strip("—-→>") != "averti"
                                                   for li in dossier.get("liaisons") or []):
                s2 = appeler_moteur({**{k: v for k, v in dossier.items() if not k.startswith("_")},
                                     "rejets_categories": dict(dossier.get("_categories_rejet") or {})}, dossier["etat"],
                                    evenement, plan["semantique"], aujourdhui, evt["vue_exterieure"], evt["temporalite"],
                                    exploratoire=hors_strate, toutes_liaisons=True)
                oc = trace.get("ombre_causale") or {}
                oc["p_avec_liaisons"] = s2.get("p")
                if s2.get("erreur"):
                    oc["erreur_avec_liaisons"] = str(s2["erreur"])[:200]
                trace["ombre_causale"] = oc
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
        if tentative == 1:         # 0.10.83 : avant la deuxième correction, un nouveau départ à contexte vide, en ombre
            try:
                trace["ombre_nouveau_depart"] = await nouveau_depart_ombre(
                    q, plan, executees, aujourdhui, jours, evt, evenement, hors_strate, llm, erreur, trace)
            except Exception as e:
                trace["ombre_nouveau_depart"] = {"statut": "erreur", "motif": f"{type(e).__name__}: {e}"[:200]}
        try:
            lecture = await json_avec_reprise(llm, consigne_correction(
                {k: dossier[k] for k in CLES_LECTURE if k in dossier}
                | {"rejets_classes": {c: {"categorie": dossier["_categories_rejet"].get(c), "motif": m}
                                      for c, m in dossier["rejets"].items()}}, erreur), trace, "correction")
        except Exception as e:
            if est_panne(e):
                return dict(trace, dossier=dossier, statut="panne",
                            motif=f"panne à la correction : {type(e).__name__}: {e}"[:300])
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

CARTES ANCRÉES (intensité F = fait suffisant, test « pistolet » ou « double » ; f = fait qui montre la définition
de la carte et au moins un marqueur observable, test « cerceau » ou « paille », sans exiger la forme complète de
l'attendu) :
{json.dumps(mots, ensure_ascii=False, indent=1)[:12000]}

RÉSULTATS DE RECHERCHE (seule base admise) :
{(textes or "(aucun)")[:14000]}

Pour chaque carte, décide :
- "maintenir" : le fait figure dans les résultats, daté, et il porte bien l'intensité déclarée ;
- "affaiblir" : le fait figure, mais il n'est pas suffisant (on l'observerait aussi sans la structure) : F devient f ;
- "retirer" : le fait ne figure pas dans les résultats, ou il est contredit, ou il ne remplit AUCUN marqueur
  observable de la carte (un attendu seulement incomplet ne justifie pas un retrait d'un f).
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
    pl_ = d.get("preuves_liaisons") or []
    gl_ = [(x, pl_[i] if i < len(pl_) else None) for i, x in enumerate(d.get("liaisons") or [])
           if not any(r_ in json.dumps(x, ensure_ascii=False) for r_ in retires)]
    d["liaisons"] = [x for x, _ in gl_]
    if gl_:
        d["preuves_liaisons"] = [p_ for _, p_ in gl_]       # 0.10.52 : les preuves suivent leurs liaisons
    else:
        d.pop("preuves_liaisons", None)
    d["questions"] = [x for x in (d.get("questions") or [])
                      if any(c_ in json.dumps(x, ensure_ascii=False) for c_ in presentes)]
    d["etat"] = etat_depuis(mots, aujourdhui, jours)
    r = appeler_moteur(d, d["etat"], evenement, semantique, aujourdhui, evt["vue_exterieure"], evt["temporalite"])
    if r.get("erreur"):
        return dict(sortie_, statut="refuse", motif=str(r["erreur"])[:300])
    return dict(sortie_, statut="estime" if r.get("p") is not None else "non_estime", p_C_critique=r.get("p"))


# 0.10.82 : décision d'auteur du 2026-11-14. Au banc, en strate 7, C a une perte log de 0,87 contre 0,59 pour B
# (27 questions ACLED) ; la levée de C au-dessus de B ne porte pas d'information (diagnostic du 2026-11-14). Jusqu'à la
# fin de l'apprentissage empirique des liens (protocole du 2026-11-14), B est posté là où C est estimé ; C reste calculé,
# scellé et journalisé, en ombre. La règle sera revue au vu du critère enregistré, par décision d'auteur datée.
POSTER_C = False


def choisir_bras(c: dict, p_A: float) -> tuple[str, float]:
    """B si l'alphabet est estimé (C en ombre, POSTER_C) ou si l'état est nul (sans carte, pas d'ajustement) ; A sinon."""
    if c.get("statut") == "estime":
        if POSTER_C:
            return "C", borner(c["p_C"])
        if c.get("p_B") is not None:
            return "B", borner(c["p_B"])
        return "A", borner(p_A)
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
                  f"Arm C, alphabet: {c['p_C']:.3f} (base rate adjusted by the cards read in the state; a propensity "
                  "read from structural indicators, not a causal claim).",
                  f"Arm A, model alone, sealed before the alphabet: {p_A:.3f}.",
                  "Engine flags (French): " + " | ".join(x if len(x) <= 220 else x[:217] + "…" for x in c.get("drapeaux", [])[:4])]
        return "\n".join(x for x in lignes if x)
    if poste == "B" and c.get("statut") == "estime":
        lignes = [tete,
                  f"State read on {c['dossier']['disponible_le']}: {c['etat']}",
                  f"Event: {c['evenement']} ({c['semantique']}).",
                  ligne_b,
                  f"Arm C, alphabet, computed and sealed but NOT posted: {c['p_C']:.3f}. Until an empirical calibration "
                  "of the card-to-event links concludes, the base rate is posted (author decision, 2026-11-14).",
                  f"Arm A, model alone, sealed before the alphabet: {p_A:.3f}."]
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
                       f"scope; recorded for measurement, NOT the posted forecast; a propensity, not a causal "
                       f"claim): {val}.")
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
    # 0.10.18 : le motif de la lecture elle-même (ex), pas l'étiquette « strate non chiffrée » posée par-dessus ; et la
    # dernière erreur du moteur, pour savoir POURQUOI un dossier est refusé.
    sortie = {"derivee": derivee, "statut": ex.get("statut") or c.get("statut"),
              "motif": (ex.get("motif") or c.get("motif") or "")[:300],
              "derniere_erreur": (str(c.get("derniere_erreur") or "")[:300] or None), "tentatives": c.get("tentatives"),
              # 0.10.19 : seuil = médiane du modèle seul, donc p_A = 0,5 par construction ; un B loin de 0,5 est suspect
              "methode_B": methode_B(c), "discordance_A": discordance(c.get("p_B"), derivee.get("p_A"), methode_B(c)),
              "preselection": c.get("preselection"), "reprises_json": c.get("reprises_json"),
              "strate": ((c.get("plan") or {}).get("evenement") or {}).get("strate"),
              "p_B": c.get("p_B"), "p_C": p_c, "p_C_corrige": corriger_C(p_c, correction_retro()),
              "p_C_symetrique": (c.get("symetrique") or {}).get("p"), "symetrique": c.get("symetrique"),
              "nature_etat_nul": c.get("nature_etat_nul") or ex.get("nature_etat_nul"), "modeles": modeles_actifs(),
              "puits": c.get("puits"), "compte_calcule": bool((c.get("vue") or {}).get("compte_calcule")),
              "p_compte": c.get("p_compte"), "rejets_classes": (c.get("dossier") or {}).get("rejets_classes"),
              "ombre_causale": c.get("ombre_causale") or ex.get("ombre_causale")}
    dossier = c.get("dossier")
    if dossier is not None:
        d = sans_cles({k: v for k, v in dossier.items() if not str(k).startswith("_")})
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
    propre = sans_cles(ligne)
    ligne.clear()
    ligne.update(propre)
    dossier = sans_cles(dossier) if dossier is not None else None
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
                          critique: Llm | None = None, essais_A: list[float] | None = None,
                          negation: dict | None = None) -> Resultat:
    maintenant = maintenant or datetime.now(timezone.utc)
    aujourdhui = maintenant.date().isoformat()
    jours = max(1, (q.resolution - maintenant.date()).days)
    bras_a = {"p": p_A, "horodatage": maintenant.isoformat(timespec="seconds")}
    if essais_A:   # 0.10.5 (skill §35, Murphy 2026) : K essais du modèle seul, en ombre ; le premier reste le bras A
        bras_a["essais"] = repetition_A([p_A] + list(essais_A))
    if negation:   # 0.10.34 : test de négation, en ombre (la question niée, posée au même modèle seul)
        bras_a["negation"] = negation
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
                            "methode": methode_B(c), "discordance_A": discordance(c.get("p_B"), p_A, methode_B(c)),
                            "p_sans_ancre": (c.get("vues") or {}).get("p_sans_ancre")},
                      "C": {**{k: c.get(k) for k in ("statut", "p_C", "etat", "evenement", "semantique", "drapeaux",
                                                        "rho", "motif", "tentatives", "reprises_plan", "recherches",
                                                        "exploratoire", "symetrique", "ombre_causale", "traduction",
                                                        "invariance", "preselection", "reprises_json", "compte_echoue", "fidelite_plan",
                                                        "nature_etat_nul", "relance", "dynamique_observee",
                                                        "empreintes_passages", "tiers_polarite", "ombre_filtrage",
                                                        "ombre_series", "ombre_nouveau_depart")},
                            "ombre_absence": ombre_absence(c.get("p_B"), c.get("nature_etat_nul")),
                            "rejets_classes": (c.get("dossier") or {}).get("_categories_rejet"),
                            "rejets_details": (c.get("dossier") or {}).get("_details_rejet"),
                            "p_C_corrige": corriger_C(c.get("p_C"), corr),
                            "attribution": controle_attribution(c.get("dossier"), c.get("_textes")),
                            # 0.10.38 : provenance des F « independantes » vérifiée hors du modèle (en ombre)
                            "provenance_F": provenance_F(c.get("dossier"), c.get("_textes")),
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
