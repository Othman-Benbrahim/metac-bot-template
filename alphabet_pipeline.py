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
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Awaitable, Callable

VERSION_BOT = "0.1.2"

DOSSIER_SKILL = Path(os.environ.get("ALPHABET_SKILL_DIR", Path(__file__).parent / "alphabet-situationnel")).resolve()
MOTEUR = DOSSIER_SKILL / "scripts" / "moteur.py"
REGISTRE = Path(os.environ.get("ALPHABET_REGISTRE", Path(__file__).parent / "registre")).resolve()
MAX_RECHERCHES = int(os.environ.get("ALPHABET_MAX_RECHERCHES", "12"))
MAX_CORRECTIONS = int(os.environ.get("ALPHABET_MAX_CORRECTIONS", "2"))

TYPES = ("apparait", "persiste", "disparait")
SEMANTIQUES = {"apparait": ("presence", "au-moins-une-fois"),
               "persiste": ("presence", "continue"),
               "disparait": ("presence", "au-moins-une-fois")}
FAMILLES = ("observation", "discrimination", "contradiction")

Llm = Callable[[str], Awaitable[str]]
Chercheur = Callable[[str], Awaitable[str]]


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


def appeler_moteur(dossier: dict, etat: str, evenement: str, semantique: str, date_info: str, vue: dict) -> dict:
    """Lance `moteur.py calculer --dossier` ; la fréquence de la vue extérieure entre comme référence (--fref)."""
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(dossier, f, ensure_ascii=False)
        chemin = f.name
    cmd = [sys.executable, str(MOTEUR), "calculer", "--etat", etat, "--evenement", evenement,
           "--temporalite", "generique", "--semantique", semantique, "--dossier", chemin,
           "--date-information", date_info, "--fref", str(vue["frequence"]),
           "--source-ref", str(vue.get("source", "")), "--periode-ref", str(vue.get("periode", "")),
           "--disponible-ref", str(vue.get("disponible_le", date_info)),
           "--definition-ref", str(vue.get("classe_de_reference", "")), "--json"]
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


def extraire_json(texte: str) -> dict:
    """Le premier objet JSON complet d'une réponse de modèle (bloc ```json``` ou accolades)."""
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", texte, re.S)
    brut = m.group(1) if m else texte[texte.find("{"): texte.rfind("}") + 1]
    if not brut:
        raise ValueError("aucun objet JSON dans la réponse")
    return json.loads(brut)


def borner(p: float) -> float:
    return max(0.01, min(0.99, float(p)))


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

Rends UNIQUEMENT un objet JSON :
{{
 "strates": [entiers, 1 ou 2 strates selon le mécanisme des faits],
 "candidats": ["ABR@strate", ...]  (2 à 4 par strate, abréviations : {", ".join(noms_cartes())}),
 "contre_candidate": ["ABR@strate", ...]  (au moins une par strate, parmi les candidats),
 "evenement": {{"carte": "ABR", "strate": n, "type": "apparait|persiste|disparait"}},
 "semantique": "presence|au-moins-une-fois|continue",
 "pourquoi_evenement": "en quoi le OUI de la question correspond à cet événement de carte",
 "recherches_reference": ["requête", ...]  (1 à {MAX_RECHERCHES_REFERENCE} requêtes pour trouver la FRÉQUENCE HISTORIQUE
     d'événements comparables : combien de fois, sur quelle période, dans quelle population de cas),
 "recherches": [{{"famille": "observation|discrimination|contradiction", "cartes": ["ABR@s", ...], "requete": "..."}}]
}}
Règles : « apparait » vise une carte ABSENTE de l'état actuel, « persiste » ou « disparait » une carte PRÉSENTE.
Sémantiques admises : apparait → presence ou au-moins-une-fois ; persiste → presence ou continue ;
disparait → presence ou au-moins-une-fois. Si le OUI ne correspond à aucun événement de carte, mets
"evenement": null et explique-le dans "pourquoi_evenement" (le bot s'abstiendra d'utiliser l'alphabet).
Recherches : pour chaque candidate, une requête de chaque famille ; pour chaque paire de candidates d'une même strate,
une requête de discrimination. Au plus {MAX_RECHERCHES} requêtes au total. Une requête se forme sur le phénomène
observable, l'objet et la période, JAMAIS sur le nom d'une carte, ni sur une prémisse.
"""


def consigne_vue(q: Question, plan: dict, references: list[dict], aujourdhui: str, jours: int) -> str:
    res = "\n\n".join(f"[R{i + 1}] « {r['requete']} »\n{r['resultat'][:3000]}" for i, r in enumerate(references))
    return f"""Étape 2 : la VUE EXTÉRIEURE, avant toute carte. Elle ne doit pas être choisie d'après l'état présent.

QUESTION : {q.titre}
CRITÈRES DE RÉSOLUTION : {q.criteres}
PRÉCISIONS : {q.precisions}
DATE D'INFORMATION : {aujourdhui} ; fenêtre : {jours} jours (jusqu'au {q.resolution.isoformat()}).

RÉSULTATS DES RECHERCHES SUR LE TAUX DE BASE :
{res or "(aucun)"}

La fréquence se tire, au choix : (a) des résultats ci-dessus (cite [R1], [R2]…) ; (b) d'un registre historique
notoire et vérifiable, que tu NOMMES précisément (ex. « liste des retraits de l'Union européenne depuis 1957 : un seul,
le Royaume-Uni en 2020 »). Compte des cas sur une période, puis ramène à une fenêtre de {jours} jours. N'invente
aucun chiffre : si aucune base honnête n'existe, mets "frequence": null et explique-le dans "motif".

Rends UNIQUEMENT un objet JSON :
{{
 "frequence": nombre dans ]0, 1[ ou null,
 "classe_de_reference": "les cas comptés, dans le vocabulaire de la source, SANS aucun nom de carte de l'alphabet",
 "source": "base, étude ou registre nommé",
 "fondement": "recherche [Rn] | registre historique",
 "periode": "AAAA-AAAA",
 "disponible_le": "AAAA-MM-JJ (au plus tard le {aujourdhui})",
 "calcul": "comptage et mise à l'échelle de la fenêtre",
 "classe_alternative": {{"frequence": …, "classe_de_reference": "…", "source": "…", "pourquoi_ecartee": "…"}} ou null,
 "motif_sans_alternative": "si classe_alternative est null",
 "ecart_critere": "en quoi la classe compte autre chose que le critère de résolution, ou « identique : … »",
 "resolution": "ce qui fera dire OUI, en une phrase",
 "source_resolution": {{"emetteur": "nommé, jamais « la presse »", "document": "…", "regle_ambiguite": "…"}},
 "motif": "si frequence est null"
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
- rejets : pour chaque candidate non ancrée, le motif.
- questions : au moins une question ouverte et datée qui départagerait la lecture (si_oui, si_non, resolution, statut).
- Ne cite que des faits trouvés dans les résultats de recherche fournis ; n'invente ni source, ni URL, ni date.
- ÉTAT NUL ADMIS : si aucun fait ne remplit le marqueur d'une carte, "mots" est une liste vide et chaque candidate va
  dans rejets. C'est une lecture légitime (« aucune structure lue »), jamais un échec : ne force pas une carte.
"""


def consigne_dossier(q: Question, plan: dict, resultats: list[dict], aujourdhui: str, jours: int) -> str:
    cartes = [c.split("@")[0] for c in plan.get("candidats", [])]
    exemple = json.loads(lire_ref("assets/dossier.exemple.json"))
    exemple = {k: exemple[k] for k in CLES_LECTURE if k in exemple}
    res = "\n\n".join(f"[{i + 1}] ({r['famille']}, {', '.join(r['cartes'])}) « {r['requete']} »\n{r['resultat'][:3000]}"
                      for i, r in enumerate(resultats))
    ev = plan["evenement"]
    return f"""Étape 3 : la lecture (mots ancrés) pour la question ci-dessous. La vue extérieure est déjà posée.

QUESTION : {q.titre}
CRITÈRES DE RÉSOLUTION : {q.criteres}
PRÉCISIONS : {q.precisions}
DATE D'INFORMATION : {aujourdhui} ; fenêtre : {jours} jours (jusqu'au {q.resolution.isoformat()}).
PLAN RETENU : {json.dumps({k: v for k, v in plan.items() if k != "recherches_reference"}, ensure_ascii=False)}

RÉSULTATS DES RECHERCHES EXÉCUTÉES :
{res}

{regles_dossier()}

FICHES DES CANDIDATES :
{fiches(cartes)}

ÉQUIVALENTS LOCAUX DES STRATES :
{equivalences(plan.get("strates", []))}

FORMAT (exemple fictif, à suivre pour la structure seulement) :
{json.dumps(exemple, ensure_ascii=False, indent=1)}

Rends UNIQUEMENT un objet JSON avec les clés : {", ".join(CLES_LECTURE)}.
L'événement prévu est {ev['carte']}@{ev['strate']} {ev['type']} : {"cette carte ne doit PAS figurer dans les mots" if ev['type'] == "apparait" else "cette carte doit figurer dans les mots"}."""


def consigne_correction(lecture: dict, erreur: str) -> str:
    return f"""Le moteur du skill a refusé cette lecture. Corrige-la sans inventer de fait, de source ni d'URL : si un
élément manque, descends l'intensité à f, ou retire le mot et motive-le dans rejets. Une lecture sans aucun mot (état
nul) est admise si rien ne tient.

ERREUR DU MOTEUR : {erreur}

LECTURE :
{json.dumps(lecture, ensure_ascii=False, indent=1)}

Rends UNIQUEMENT l'objet JSON corrigé, avec les clés : {", ".join(CLES_LECTURE)}."""


# --------------------------------------------------------------------------- assemblage

CLES_LECTURE = ("candidats", "contre_candidate", "rejets", "mots", "liaisons", "questions")
MAX_RECHERCHES_REFERENCE = int(os.environ.get("ALPHABET_MAX_RECHERCHES_REFERENCE", "3"))


def etat_depuis(mots: list[dict], aujourdhui: str, jours: int) -> str:
    noms = noms_cartes()
    corps = " + ".join(f"{noms.get(m['carte'], m['carte'])}@{m['strate']}[{m['intensite']}]" for m in mots)
    return f"[{aujourdhui} | {jours} jours] {corps}" if corps else ""


def evenement_depuis(plan: dict, vue: dict) -> tuple[dict, str]:
    """La partie « événement » du dossier, construite par le bot : une correction ne peut pas l'effacer."""
    noms = noms_cartes()
    ev = plan["evenement"]
    evenement = f"{noms.get(ev['carte'], ev['carte'])}@{ev['strate']} {ev['type']}"
    champs = ("frequence", "classe_de_reference", "source", "periode", "disponible_le", "classe_alternative",
              "motif_sans_alternative", "ecart_critere")
    ve = {k: vue.get(k) for k in champs if vue.get(k) is not None or k == "classe_alternative"}
    if ve.get("classe_alternative") is None:
        ve["motif_sans_alternative"] = vue.get("motif_sans_alternative") or "aucune classe alternative honnête trouvée"
    return {"evenement": evenement, "semantique": plan["semantique"], "temporalite": "generique",
            "resolution": vue.get("resolution") or "", "source_resolution": vue.get("source_resolution") or {},
            "vue_exterieure": ve}, evenement


def assembler(lecture: dict, plan: dict, executees: list[dict], evt: dict, aujourdhui: str, jours: int) -> dict:
    d = {k: lecture.get(k, [] if k in ("mots", "liaisons", "questions", "candidats", "contre_candidate") else {})
         for k in CLES_LECTURE}
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
    return None


def controle_vue(vue: dict) -> str | None:
    f = vue.get("frequence")
    if not isinstance(f, (int, float)) or isinstance(f, bool) or not 0 < f < 1:
        return vue.get("motif") or "vue extérieure sans fréquence"
    for k in ("classe_de_reference", "source", "periode", "disponible_le"):
        if not vue.get(k):
            return f"vue extérieure incomplète : {k} manquant"
    return None


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
        if len(sortie) >= plafond:
            break
        try:
            texte = await chercher(req)
        except Exception as e:  # une recherche qui échoue est consignée, non lancée
            texte, ok = f"(échec : {e})", False
        else:
            ok = recherche_reelle
        sortie.append({"famille": r.get("famille", "reference"), "cartes": r.get("cartes", []), "requete": req,
                       "resultat": texte or "", "executee": ok})
    return sortie


async def executer_recherches(plan: dict, chercher: Chercheur, recherche_reelle: bool) -> list[dict]:
    return await executer_requetes([r for r in plan.get("recherches", []) if r.get("famille") in FAMILLES],
                                   chercher, recherche_reelle, MAX_RECHERCHES)


async def alphabet(q: Question, recherche: str, llm: Llm, chercher: Chercheur, recherche_reelle: bool,
                   aujourdhui: str, jours: int) -> dict:
    """Bras B et C. statut : estime | etat_nul | non_estime | refuse | sans_vue | hors_alphabet."""
    trace: dict = {"statut": "refuse", "tentatives": 0}
    try:
        plan = extraire_json(await llm(consigne_plan(q, recherche, aujourdhui)))
    except Exception as e:
        return dict(trace, motif=f"plan illisible : {e}")
    trace["plan"] = plan
    motif = controle_plan(plan)
    if motif:
        return dict(trace, statut="hors_alphabet", motif=motif)

    # 1. Vue extérieure d'abord, sur ses propres recherches (bras B).
    refs = await executer_requetes([{"requete": x} for x in (plan.get("recherches_reference") or []) if isinstance(x, str)],
                                   chercher, recherche_reelle, MAX_RECHERCHES_REFERENCE)
    trace["recherches_reference"] = [{k: v for k, v in r.items() if k != "resultat"} for r in refs]
    try:
        vue = extraire_json(await llm(consigne_vue(q, plan, refs, aujourdhui, jours)))
    except Exception as e:
        return dict(trace, statut="sans_vue", motif=f"vue extérieure illisible : {e}")
    trace["vue"] = vue
    motif = controle_vue(vue)
    if motif:
        return dict(trace, statut="sans_vue", motif=motif)
    trace["p_B"] = float(vue["frequence"])
    evt, evenement = evenement_depuis(plan, vue)

    # 2. Lecture (bras C).
    executees = await executer_recherches(plan, chercher, recherche_reelle)
    trace["recherches"] = [{k: v for k, v in r.items() if k != "resultat"} for r in executees]
    try:
        lecture = extraire_json(await llm(consigne_dossier(q, plan, executees, aujourdhui, jours)))
    except Exception as e:
        return dict(trace, motif=f"lecture illisible : {e}")
    dossier = None
    for tentative in range(MAX_CORRECTIONS + 1):
        trace["tentatives"] = tentative + 1
        dossier = assembler(lecture, plan, executees, evt, aujourdhui, jours)
        if not dossier["mots"]:
            # État nul : aucune carte ancrée. Le moteur ne calcule pas un état vide ; sans carte, pas d'ajustement :
            # le bot postera le taux de base (bras B).
            trace.update(dossier=dossier, statut="etat_nul", evenement=evenement, semantique=plan["semantique"],
                         motif="aucune carte ancrée : pas d'ajustement du taux de base")
            return trace
        erreur = controle_etat(dossier, plan)
        sortie = None
        if not erreur:
            sortie = appeler_moteur(dossier, dossier["etat"], evenement, plan["semantique"], aujourdhui,
                                    evt["vue_exterieure"])
            erreur = sortie.get("erreur")
        if not erreur:
            trace.update(dossier=dossier, etat=dossier["etat"], evenement=evenement, semantique=plan["semantique"],
                         p_C=sortie.get("p"), p_sans_cartes=sortie.get("p_sans_cartes"),
                         drapeaux=sortie.get("drapeaux", []), rho=sortie.get("rho"))
            trace["statut"] = "estime" if sortie.get("p") is not None else "non_estime"
            if sortie.get("p") is None:
                trace["motif"] = next((x for x in sortie.get("drapeaux", []) if x.startswith("Non estimé")), "non estimé")
            return trace
        trace["derniere_erreur"] = erreur
        if tentative == MAX_CORRECTIONS:
            break
        try:
            lecture = extraire_json(await llm(consigne_correction({k: dossier[k] for k in CLES_LECTURE}, erreur)))
        except Exception as e:
            trace["derniere_erreur"] = f"correction illisible : {e}"
            break
    trace["dossier"] = dossier
    trace["motif"] = trace.get("derniere_erreur")
    return trace


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
                  "is not adjusted.",
                  *[f"- {k}: {str(v)[:300]}" for k, v in list(rejets.items())[:4]],
                  ligne_b,
                  f"Arm A, model alone, sealed before the alphabet: {p_A:.3f}."]
        return "\n".join(x for x in lignes if x)
    motif = c.get("motif") or "unknown"
    return f"{tete}\nAlphabet not used on this question ({c.get('statut')}: {motif}).\n\nModel-alone reasoning:\n{a_raison}"


def ecrire_registre(ligne: dict, dossier: dict | None) -> None:
    REGISTRE.mkdir(parents=True, exist_ok=True)
    if dossier is not None:
        d = REGISTRE / "dossiers"
        d.mkdir(exist_ok=True)
        nom = f"{ligne['question_id']}-{ligne['date_information']}.json"
        (d / nom).write_text(json.dumps(dossier, ensure_ascii=False, indent=1), encoding="utf-8")
        ligne["dossier_fichier"] = f"dossiers/{nom}"
        ligne["dossier_sha256"] = sceau(dossier)
    ligne["sceau"] = sceau(ligne)
    with open(REGISTRE / "journal-bot.jsonl", "a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(ligne, ensure_ascii=False, sort_keys=True) + "\n")


async def prevoir_binaire(q: Question, recherche: str, p_A: float, a_raison: str, llm: Llm, chercher: Chercheur,
                          recherche_reelle: bool, maintenant: datetime | None = None) -> Resultat:
    maintenant = maintenant or datetime.now(timezone.utc)
    aujourdhui = maintenant.date().isoformat()
    jours = max(1, (q.resolution - maintenant.date()).days)
    bras_a = {"p": p_A, "horodatage": maintenant.isoformat(timespec="seconds")}
    bras_a["sceau"] = sceau({"question": str(q.id), "date": aujourdhui, **bras_a})  # A scellé avant l'alphabet
    c = await alphabet(q, recherche, llm, chercher, recherche_reelle, aujourdhui, jours)
    poste, p_poste = choisir_bras(c, p_A)
    vue = c.get("vue") or {}
    ligne = {"version_bot": VERSION_BOT, "version_skill": version_skill(), "question_id": str(q.id), "url": q.url,
             "titre": q.titre, "date_information": aujourdhui, "resolution_prevue": q.resolution.isoformat(),
             "fenetre_jours": jours, "recherche_reelle": recherche_reelle,
             "bras": {"A": bras_a,
                      "B": {"p": c.get("p_B"), **{k: vue.get(k) for k in ("classe_de_reference", "source", "fondement",
                                                                         "periode", "calcul") if vue.get(k)},
                            "recherches": c.get("recherches_reference")},
                      "C": {k: c.get(k) for k in ("statut", "p_C", "etat", "evenement", "semantique", "drapeaux",
                                                     "rho", "motif", "tentatives", "recherches")}},
             "bras_poste": poste, "p_poste": p_poste}
    ecrire_registre(ligne, c.get("dossier"))
    return Resultat(p_A, c.get("p_B"), c.get("p_C"), poste, p_poste, commentaire(q, p_A, a_raison, c, poste), ligne)
