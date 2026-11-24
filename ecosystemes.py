"""Modélisation par écosystèmes : une fiche compartimentée par thème, et le schéma d'interrelations qui les relie.

Décision de l'auteur, 2026-11-19, 3 h 44 : « une fiche compartimentée pour l'ensemble des sujets traités, chaque facteur
compris à son niveau d'action ; chaque thème a sa compartimentation, ses relations et ses ponts avec des thèmes
connexes ; par un schéma d'interrelation nourri, on schématisera petit à petit quelque chose de cohérent ».
Principe (2026-11-19, 3 h 39) : chaque fiche est UN écosystème — un découpage déclaré par un observateur pour un but —,
pas L'écosystème. Les fiches se superposent et se partagent des éléments ; aucune n'est « la bonne ».

Fiches : ecosystemes/<theme>.yaml (format dans ecosystemes/LISEZMOI.md). Ce module les valide, déduit ce qui peut
l'être (forme d'une relation à partir des deux effets), assemble le schéma global et écrit :
- registre/ecosystemes-schema.json : nœuds (thème:compartiment), relations, ponts ;
- registre/ecosystemes-a-faire.md : ponts vers des thèmes encore sans fiche, compartiments sans trace, relations à
  vérifier — la liste de travail.
Aucun appel réseau, aucun modèle ; rien n'entre dans le bot.

    python ecosystemes.py            # valide et assemble
    python ecosystemes.py --mermaid ormuz   # schéma Mermaid d'une fiche
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import yaml

DOSSIER = Path("ecosystemes")
NIVEAUX = DOSSIER / "niveaux.yaml"
SCHEMA = Path("registre/ecosystemes-schema.json")
A_FAIRE = Path("registre/ecosystemes-a-faire.md")

AXES = ("espace", "temps", "vitesse", "taille")
EFFETS = ("+", "-", "0", "±")
FORMES = ("competition", "predation", "mutualisme", "commensalisme", "amensalisme", "neutralisme", "forcage",
          "contrainte", "ambivalent")
STYLES = ("donnant-donnant", "rancunier", "conciliant", "indifferent", "inconnu")
STATUTS = ("a_verifier", "verifie", "conteste", "ombre")
# 0.10.338 (décision d'auteur du 2026-11-19, 12 h 00) : « ombre » = mécanisme supposé, à étudier, que la carte garde
# HORS de la propagation et de la simulation (Carte(ombre=True) pour l'inclure) ; calibrer.py le mesure quand même.
TRACES = ("collecte", "a_brancher", "fermee", "inconnue")
FORCES = ("faible", "moyenne", "forte", "inconnue")
# 0.10.315 (idée de l'auteur, 2026-11-19, 3 h 56) : l'INTENSITÉ. La force d'une relation n'est pas fixe : plus
# l'intensité du moment est forte (tension, chaleur, rareté, attention), plus la relation transmet. On distingue :
# - force : ce que la relation transmet d'ordinaire (structurel) ;
# - intensite.mesure : ce qui dit l'intensité du moment (une trace) ;
# - intensite.regle : comment la force varie avec l'intensité.
REGLES_INTENSITE = ("proportionnelle", "seuil", "saturation", "hysteresis", "masse_critique", "inconnue")
# 0.10.326 (Schelling, Micromotives and Macrobehavior) : « masse_critique » — chacun agit quand assez d'autres agissent,
# et les seuils individuels sont DISTRIBUÉS (moyenne mu, dispersion sigma, en unités d'intensité |z|). La réponse
# collective suit la fonction de répartition de ces seuils : une courbe en S, dont le « seuil » net est le cas limite
# (sigma → 0). Paramètres de la relation : mu, sigma (calibrés par calibrer.py).


# 0.10.317 (rappel de l'auteur, 2026-11-19, 4 h 34) : les quatre axes doivent être lisibles par le code, et SURTOUT la
# taille : tous les acteurs n'agissent pas à la même échelle. Chaque axe écrit en mots est lu en grandeur ordonnée.
TAILLES = {"micro": 1, "méso": 2, "meso": 2, "macro": 3}
NOMS_TAILLE = {1: "micro", 2: "méso", 3: "macro"}
ESPACES = ((1, ("site", "local", "navire", "parcelle", "raffinerie", "plateforme")),
           (2, ("détroit", "golfe", "bassin", "région", "théâtre", "couloir", "abords", "route", "pôle", "juridiction")),
           (3, ("état", "pays", "national", "iran", "producteur", "cartel")),
           (4, ("continent", "asie", "europe", "économies")),
           (5, ("mondial", "mondiaux", "monde", "planète", "global")))
VITESSES = (("seconde", 0.0), ("minute", 0.001), ("heure", 0.05), ("jour", 1), ("semaine", 7), ("mois", 30),
            ("trimestre", 90), ("saison", 90), ("année", 365), ("an ", 365), ("décennie", 3650), ("siècle", 36500))


def _plage(valeurs: list[float]) -> list[float] | None:
    return [min(valeurs), max(valeurs)] if valeurs else None


def axes(niveau: dict) -> dict:
    """Les quatre axes en grandeurs : taille 1 (micro) à 3 (macro), espace 1 (site) à 5 (monde), vitesse en jours
    (temps caractéristique de changement), temps gardé en mots (calendrier, mémoire). Une plage si le texte en donne
    une (« micro à macro » → [1, 3])."""
    tx = {k: str(niveau.get(k) or "").lower() for k in AXES}
    taille = _plage([v for m, v in TAILLES.items() if re.search(rf"\b{m}", tx["taille"])])
    espace = _plage([n for n, mots in ESPACES if any(m in tx["espace"] for m in mots)])
    vitesse = _plage([j for m, j in VITESSES if m in tx["vitesse"] + " "])
    return {"taille": taille, "espace": espace, "vitesse_jours": vitesse, "temps": niveau.get("temps")}


def forme_deduite(effet: str, retour: str | None) -> str:
    """Forme écologique d'après l'effet de la source sur la cible et le retour de la cible sur la source.
    Sans retour (élément non vivant, influence à sens unique) : forçage."""
    if retour is None:
        return "forcage"
    paire = (effet, retour)
    table = {("-", "-"): "competition", ("+", "+"): "mutualisme", ("+", "0"): "commensalisme",
             ("0", "+"): "commensalisme", ("-", "0"): "amensalisme", ("0", "-"): "amensalisme",
             ("0", "0"): "neutralisme", ("-", "+"): "predation", ("+", "-"): "predation"}
    return table.get(paire, "ambivalent")


def niveaux(fichier: Path = NIVEAUX) -> dict:
    """Catalogue des niveaux d'organisation et des facettes d'acteurs (ecosystemes/niveaux.yaml)."""
    d = yaml.safe_load(fichier.read_text(encoding="utf-8")) if fichier.exists() else {}
    return {"niveaux": {n["id"]: n for n in d.get("niveaux") or []}, "facettes": d.get("facettes") or {}}


def odd(fichier: Path | None = None) -> dict[str, str]:
    """Codes officiels des indicateurs ODD vérifiés (ecosystemes/odd.yaml) : code -> libellé."""
    f = fichier or NIVEAUX.parent / "odd.yaml"
    d = yaml.safe_load(f.read_text(encoding="utf-8")) if f.exists() else {}
    return {str(k): v for k, v in (d.get("indicateurs") or {}).items()}


TRANSVERSAUX = "ponts-transversaux.yaml"


def ponts_transversaux(dossier: Path = DOSSIER) -> tuple[list[dict], dict[str, str]]:
    """0.10.435 (décision de l'auteur, 2026-11-22, 6 h 08) : ponts entre fiches écrits à part, chacun avec son CANAL
    (le mécanisme qui transmet). Rend (entrées, canaux)."""
    f = dossier / TRANSVERSAUX
    if not f.exists():
        return [], {}
    d = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
    return list(d.get("ponts") or []), dict(d.get("canaux") or {})


def erreurs_transversaux(fiches: dict[str, dict], dossier: Path = DOSSIER) -> list[str]:
    """Chaque pont transversal relie deux compartiments existants de deux fiches, par un canal déclaré."""
    ponts, canaux = ponts_transversaux(dossier)
    ids = {f"{t}:{c['id']}" for t, x in fiches.items() for c in x.get("compartiments") or []}
    err = []
    for p in ponts:
        de, vers = str(p.get("de", "")), str(p.get("vers", ""))
        for ref in (de, vers):
            if ref not in ids:
                err.append(f"pont transversal {de} → {vers} : « {ref} » n'existe pas")
        if de.split(":")[0] == vers.split(":")[0]:
            err.append(f"pont transversal {de} → {vers} : même fiche (c'est une relation, pas un pont)")
        if p.get("canal") not in canaux:
            err.append(f"pont transversal {de} → {vers} : canal inconnu {p.get('canal')!r}")
        if p.get("type", "influence") not in TYPES_PONT:
            err.append(f"pont transversal {de} → {vers} : type {p.get('type')!r} hors de {TYPES_PONT}")
    return err


def charger(dossier: Path = DOSSIER, transversaux: bool = True) -> dict[str, dict]:
    out = {}
    for f in sorted(dossier.glob("*.yaml")):
        if f.name == "niveaux.yaml" or f.name.startswith("branchements"):
            continue
        d = yaml.safe_load(f.read_text(encoding="utf-8"))
        if not isinstance(d, dict) or "theme" not in d:        # un fichier qui n'est pas une fiche ne casse rien
            continue
        out[d["theme"]] = d
    if transversaux:
        # ajoutés aux ponts de la fiche de départ (sans doublon) ; les entrées fautives sont laissées de côté ici et
        # signalées par erreurs_transversaux (test du dépôt)
        ids = {f"{t}:{c['id']}" for t, x in out.items() for c in x.get("compartiments") or []}
        for p in ponts_transversaux(dossier)[0]:
            de, vers = str(p.get("de", "")), str(p.get("vers", ""))
            t, _, cid = de.partition(":")
            if de not in ids or vers not in ids or t == vers.split(":")[0]:
                continue
            liste = out[t].setdefault("ponts", []) or []
            out[t]["ponts"] = liste
            if any(q.get("depuis") == cid and q.get("vers") == vers for q in liste):
                continue
            liste.append({"depuis": cid, "vers": vers, "nature": p.get("nature", ""),
                          "type": p.get("type", "influence"), "canal": p.get("canal")})
    return out


# 0.10.492 (décision de l'auteur, 2026-11-24, 14 h 52) : « événements comptés » d'un compartiment : pour un type
# d'événement que les questions demandent, la série qui le compte et le seuil d'occurrence. Gabarits de série :
# {ISO3}, {ISO2}, {ISO2_A}, {ISO2_B}, {ISO3_A}, {ISO3_B} (pays cités dans la question, dans l'ordre). Seuil : nombre (valeur ≥ seuil sur un
# pas = une occurrence) ou qNN (quantile NN des 365 jours, ou 12 mois, qui précèdent la date de la question).
CLES_EVENEMENT = {"type", "termes", "serie", "seuil", "pas", "occurrence", "statut", "note"}
CLES_PERMISES = {
    "niveau": set(AXES), "trace": {"source", "statut", "fichier", "adaptateur", "habitude", "odd"},
    "acteur": {"nom", "taille", "espace", "vitesse", "organisation", "facette"},
    "relation": {"de", "vers", "effet", "retour", "forme", "style", "delai", "force", "intensite", "coupure", "statut", "source", "texte",
                 "module", "parametres", "series", "verification"},
    "pont": {"depuis", "vers", "nature", "type", "canal"}}
# 0.10.319 : un pont dit soit que deux fiches lisent le MÊME phénomène (type: meme, transmission entière et immédiate),
# soit qu'un compartiment INFLUE sur l'autre fiche (type: influence, par défaut : transmission partielle, avec retard).
# 0.10.443 (décision de l'auteur, 2026-11-22, 7 h 27 - 7 h 33, filtre « causes ») : trois sortes de ponts, nommées sur
# la carte « cause », « même chose », « lien de voisinage ». influence = CAUSE, la flèche va de la cause vers l'effet
# (sens relu pour chaque pont le 2026-11-22 ; les ponts écrits à l'envers ont été retournés) ; voisinage = les deux
# compartiments se touchent (partie d'un tout, lieu, calendrier, même acteur) sans cause établie : il sert à naviguer
# et ne transmet rien dans la simulation.
TYPES_PONT = ("meme", "influence", "voisinage")


# 0.10.326 (Schelling, ch. 2, « les mathématiques inéluctables des chaises musicales ») : une IDENTITÉ comptable tient
# quels que soient les motifs : variation(total) = Σ coefficient × variation(terme). Clé de fiche « identites ».
CLES_IDENTITE = {"total", "termes", "texte"}


# 0.10.461 (conception validée par l'auteur, 2026-11-22, 17 h 48 et 17 h 52) : une fiche peut déclarer ses CYCLES et ses
# TENSIONS (le seuil est rangé dans la tension). Facultatif. Principe de l'auteur : on part du mécanisme pour l'expliquer,
# l'identification (période, source) vient ensuite (« l'état précède l'essence ») : un cycle doit décrire son mécanisme ;
# sa période et ses sources sont facultatives, et son statut dit où l'on en est (mecanisme puis identifie).
SORTES_CYCLE = ("force", "endogene", "conventionnel")
STATUTS_CYCLE = ("mecanisme", "identifie")
FORMES_TENSION = ("cumulative", "oppositionnelle", "desynchronisation")
HYSTERESIS = ("oui", "non", "inconnu")
CLES_CYCLE = {"id", "nom", "sorte", "mecanisme", "periode", "phase_vulnerable", "compartiments", "sources", "statut"}
CLES_TENSION = {"id", "nom", "forme", "entre", "stock", "module_par", "mesure", "seuil", "statut", "texte", "tampons"}
# 0.10.462 (veille Harish, « The Problem of No Problem », validée par l'auteur à 18 h 03) : ce qui absorbe les
# perturbations sans être vu ; leur usure est une tension cachée, qui n'apparaît qu'à leur épuisement
CLES_TAMPON = {"nom", "niveau", "mesure"}
CLES_SEUIL = {"habitus", "indicateurs_lents", "bascule", "hysteresis"}


def erreurs_cycles_tensions(fiche: dict, ids: set[str]) -> list[str]:
    t, err = fiche.get("theme", "?"), []
    cycles = fiche.get("cycles") or []
    ids_cycles = set()
    for c in cycles:
        lab = f"{t} cycle {c.get('id')!r}"
        for k in set(c) - CLES_CYCLE:
            err.append(f"{lab} : clé inconnue {k!r}")
        ids_cycles.add(c.get("id"))
        if c.get("sorte") not in SORTES_CYCLE:
            err.append(f"{lab} : sorte {c.get('sorte')!r} hors de {SORTES_CYCLE}")
        if not str(c.get("mecanisme") or "").strip():
            err.append(f"{lab} : le mécanisme doit être décrit (on l'explique avant de l'identifier)")
        if c.get("statut", "mecanisme") not in STATUTS_CYCLE:
            err.append(f"{lab} : statut {c.get('statut')!r} hors de {STATUTS_CYCLE}")
        if c.get("statut") == "identifie" and not (c.get("periode") and c.get("sources")):
            err.append(f"{lab} : un cycle « identifie » porte sa période et ses sources")
        for x in c.get("compartiments") or []:
            if x not in ids:
                err.append(f"{lab} : « {x} » n'est pas un compartiment de la fiche")
    for x in fiche.get("tensions") or []:
        lab = f"{t} tension {x.get('id')!r}"
        for k in set(x) - CLES_TENSION:
            err.append(f"{lab} : clé inconnue {k!r}")
        if x.get("forme") not in FORMES_TENSION:
            err.append(f"{lab} : forme {x.get('forme')!r} hors de {FORMES_TENSION}")
        entre = x.get("entre") or []
        if len(entre) != 2:
            err.append(f"{lab} : « entre » nomme exactement deux pôles")
        for pole in entre:
            if ":" not in str(pole) and pole not in ids:
                err.append(f"{lab} : pôle « {pole} » absent de la fiche (écrire theme:compartiment pour un autre écosystème)")
        if x.get("forme") == "cumulative" and x.get("stock") not in entre:
            err.append(f"{lab} : une tension cumulative désigne son stock (« stock », l'un des deux pôles)")
        for m in x.get("module_par") or []:
            if ":" not in str(m) and m not in ids_cycles:
                err.append(f"{lab} : « {m} » n'est pas un cycle de la fiche (écrire theme:cycle pour un autre écosystème)")
        for tp in x.get("tampons") or []:
            if not isinstance(tp, dict) or not tp.get("nom"):
                err.append(f"{lab} : chaque tampon est un dictionnaire avec au moins « nom »")
            else:
                for k in set(tp) - CLES_TAMPON:
                    err.append(f"{lab} tampon : clé inconnue {k!r}")
        sl = x.get("seuil") or {}
        for k in set(sl) - CLES_SEUIL:
            err.append(f"{lab} seuil : clé inconnue {k!r}")
        if sl and sl.get("hysteresis", "inconnu") not in HYSTERESIS:
            err.append(f"{lab} seuil : hysteresis {sl.get('hysteresis')!r} hors de {HYSTERESIS}")
    return err


def cles_inconnues(fiche: dict) -> list[str]:
    """Une virgule non protégée dans une ligne YAML { … } fabrique une clé parasite et tronque le texte : on la refuse."""
    t, err = fiche.get("theme", "?"), []
    def voir(objet, sorte, ou):
        if isinstance(objet, dict):
            for k in set(objet) - CLES_PERMISES[sorte]:
                err.append(f"{t} {ou} : clé inconnue {k!r} (virgule à mettre entre guillemets ?)")
    for c in fiche.get("compartiments") or []:
        voir(c.get("niveau"), "niveau", f"{c.get('id')}.niveau")
        for x in c.get("traces") or []:
            voir(x, "trace", f"{c.get('id')}.traces")
        for x in c.get("acteurs") or []:
            voir(x, "acteur", f"{c.get('id')}.acteurs")
    for r in fiche.get("relations") or []:
        voir(r, "relation", f"relation {r.get('de')} → {r.get('vers')}")
    for p in fiche.get("ponts") or []:
        voir(p, "pont", "ponts")
    for x in fiche.get("identites") or []:
        for k in set(x) - CLES_IDENTITE:
            err.append(f"{t} identites : clé inconnue {k!r}")
    return err


def valider(fiche: dict) -> list[str]:
    err = cles_inconnues(fiche)
    t = fiche.get("theme", "?")
    for k in ("theme", "nom", "declaration", "compartiments", "relations"):
        if k not in fiche:
            err.append(f"{t} : clé « {k} » absente")
    dec = fiche.get("declaration") or {}
    for k in ("but", "limites", "observateur", "date") + AXES:
        if k not in dec:
            err.append(f"{t} : déclaration sans « {k} » (un écosystème est un découpage déclaré)")
    ids = [c.get("id") for c in fiche.get("compartiments") or []]
    if len(ids) != len(set(ids)):
        err.append(f"{t} : identifiants de compartiments en double")
    for c in fiche.get("compartiments") or []:
        for a in AXES:
            if a not in (c.get("niveau") or {}):
                err.append(f"{t}:{c.get('id')} : niveau d'action sans « {a} »")
        g = c.get("geopolitique")
        if g is not None and (not isinstance(g, dict) or set(g) - {"pays"} or
                              not all(isinstance(x, str) and re.fullmatch(r"[A-Z]{3}", x) for x in g.get("pays") or [])):
            err.append(f"{t}:{c.get('id')} : « geopolitique » attend {{pays: [codes ISO3]}}")
        for e in c.get("evenements") or []:
            if not isinstance(e, dict) or set(e) - CLES_EVENEMENT or not {"type", "termes", "serie", "seuil", "pas"} <= set(e):
                err.append(f"{t}:{c.get('id')} : événement compté mal formé ({e}) ; clés {sorted(CLES_EVENEMENT)}")
                continue
            if e["pas"] not in ("jour", "mois") or not (isinstance(e["seuil"], (int, float)) or re.fullmatch(r"q\d\d", str(e["seuil"]))):
                err.append(f"{t}:{c.get('id')} : événement {e['type']!r} : pas jour|mois, seuil nombre ou qNN")
        cat = niveaux()
        if c.get("organisation") is not None and c["organisation"] not in cat["niveaux"]:
            err.append(f"{t}:{c.get('id')} : niveau d'organisation inconnu {c['organisation']!r} (voir ecosystemes/niveaux.yaml)")
        for a in c.get("acteurs") or []:
            if a.get("organisation") is not None and a["organisation"] not in cat["niveaux"]:
                err.append(f"{t}:{c.get('id')} : acteur {a.get('nom')!r}, niveau d'organisation inconnu {a['organisation']!r}")
            if a.get("facette") is not None and a["facette"] not in cat["facettes"]:
                err.append(f"{t}:{c.get('id')} : acteur {a.get('nom')!r}, facette inconnue {a['facette']!r}")
        if (c.get("niveau") or {}).get("taille") and axes(c["niveau"])["taille"] is None:
            err.append(f"{t}:{c.get('id')} : taille illisible (écrire micro, méso ou macro, ou une plage)")
        for a in c.get("acteurs") or []:
            if not a.get("nom") or axes({"taille": a.get("taille")})["taille"] is None:
                err.append(f"{t}:{c.get('id')} : acteur sans nom ou sans taille lisible ({a})")
        for tr in c.get("traces") or []:
            if tr.get("statut") not in TRACES:
                err.append(f"{t}:{c.get('id')} : statut de trace inconnu {tr.get('statut')!r}")
            # 0.10.420 : code officiel d'indicateur des ODD, vérifié dans ecosystemes/odd.yaml
            for code in tr.get("odd") or []:
                if str(code) not in odd():
                    err.append(f"{t}:{c.get('id')} : code ODD {code!r} absent de ecosystemes/odd.yaml")
    for f in fiche.get("faits") or []:       # 2026-11-21 : faits datés, au moins deux sources indépendantes
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", str(f.get("date", ""))):
            err.append(f"{t} : fait sans date lisible ({str(f.get('fait', ''))[:40]})")
        if f.get("compartiment") not in ids:
            err.append(f"{t} : fait rattaché à un compartiment inconnu {f.get('compartiment')!r}")
        if len([s for s in f.get("sources") or [] if (s or {}).get("url")]) < 2 or f.get("statut") != "recoupe":
            err.append(f"{t} : fait non recoupé par deux sources ({str(f.get('fait', ''))[:40]})")
    for i, r in enumerate(fiche.get("relations") or []):
        lab = f"{t} relation {i + 1} ({r.get('de')} → {r.get('vers')})"
        for bout in ("de", "vers"):
            if r.get(bout) not in ids:
                err.append(f"{lab} : « {r.get(bout)} » n'est pas un compartiment de la fiche")
        if r.get("effet") not in EFFETS:
            err.append(f"{lab} : effet {r.get('effet')!r} hors de {EFFETS}")
        if r.get("retour") is not None and r.get("retour") not in EFFETS:
            err.append(f"{lab} : retour {r.get('retour')!r} hors de {EFFETS}")
        if r.get("forme") is not None and r.get("forme") not in FORMES:
            err.append(f"{lab} : forme {r.get('forme')!r} hors de {FORMES}")
        if r.get("style") is not None and r.get("style") not in STYLES:
            err.append(f"{lab} : style {r.get('style')!r} hors de {STYLES}")
        if r.get("statut") not in STATUTS:
            err.append(f"{lab} : statut {r.get('statut')!r} hors de {STATUTS}")
        if r.get("force", "inconnue") not in FORCES:
            err.append(f"{lab} : force {r.get('force')!r} hors de {FORCES}")
        it = r.get("intensite")
        if it is not None:
            if not isinstance(it, dict) or not it.get("mesure"):
                err.append(f"{lab} : intensité sans « mesure » (ce qui dit l'intensité du moment)")
            elif it.get("regle") not in REGLES_INTENSITE:
                err.append(f"{lab} : règle d'intensité {it.get('regle')!r} hors de {REGLES_INTENSITE}")
        # 0.10.325 : une relation de MODULATION ne transmet rien d'elle-même ; elle abaisse le seuil d'une autre
        # relation de la fiche, écrite « de>vers » (Sapolsky : l'hormone sensibilise, le milieu déclenche)
        mod = r.get("module")
        if mod is not None:
            de, _, vers = str(mod).partition(">")
            cible = [x for x in fiche.get("relations") or [] if x.get("de") == de and x.get("vers") == vers]
            if not cible:
                err.append(f"{lab} : module {mod!r} ne désigne aucune relation de la fiche (écrire de>vers)")
            elif (cible[0].get("intensite") or {}).get("regle") not in ("seuil", "masse_critique"):
                err.append(f"{lab} : module {mod!r} vise une relation sans règle « seuil » ni « masse_critique » (rien à abaisser)")
        # 0.10.325 : « series » impose les deux séries de calibration [source, cible], prises parmi les traces des
        # deux compartiments, pour que la mesure compare le même lieu aux deux bouts
        ser = r.get("series")
        if ser is not None:
            comp = {c.get("id"): c for c in fiche.get("compartiments") or []}
            ok = isinstance(ser, list) and len(ser) == 2 and all(
                any(tr.get("adaptateur") == a for tr in (comp.get(b) or {}).get("traces") or [])
                for a, b in zip(ser, (r.get("de"), r.get("vers"))))
            if not ok:
                err.append(f"{lab} : series {ser!r} doit nommer [adaptateur de la source, adaptateur de la cible]")
        par = r.get("parametres")
        if par is not None and not (isinstance(par, dict) and all(isinstance(v, (int, float)) for v in par.values())):
            err.append(f"{lab} : parametres doit être un dictionnaire nom → valeur de départ (nombre)")
    for x in fiche.get("identites") or []:
        termes = x.get("termes") or {}
        if x.get("total") not in ids or not termes or any(k not in ids for k in termes) \
                or not all(isinstance(v, (int, float)) and v != 0 for v in termes.values()):
            err.append(f"{t} identité {x.get('total')!r} : total et termes doivent être des compartiments, coefficients non nuls")
    err += erreurs_cycles_tensions(fiche, ids)
    for p in fiche.get("ponts") or []:
        if p.get("depuis") not in ids:
            err.append(f"{t} pont : « {p.get('depuis')} » n'est pas un compartiment de la fiche")
        if ":" not in str(p.get("vers", "")):
            err.append(f"{t} pont : « vers » doit s'écrire theme:compartiment")
        if p.get("type", "influence") not in TYPES_PONT:
            err.append(f"{t} pont : type {p.get('type')!r} hors de {TYPES_PONT}")
    return err


def assembler(fiches: dict[str, dict]) -> dict:
    noeuds, liens, ponts = [], [], []
    for t, f in fiches.items():
        for c in f["compartiments"]:
            noeuds.append({"id": f"{t}:{c['id']}", "theme": t, "nom": c.get("nom", c["id"]), "niveau": c["niveau"],
                           "organisation": c.get("organisation"),
                           # 0.10.473 (décision de l'auteur, 2026-11-23, 8 h 15 - 8 h 35) : pays concernés, sous le champ
                           # « geopolitique » (codes ISO3) ; sert de point d'attache aux cartes géopolitiques (UCDP)
                           "geopolitique": c.get("geopolitique") or {},
                           "evenements": c.get("evenements") or [],
                           "axes": axes(c["niveau"]), "traces": c.get("traces") or [],
                           "acteurs": [dict(a, axes=axes({"taille": a.get("taille"), "espace": a.get("espace"),
                                                          "vitesse": a.get("vitesse")})) for a in c.get("acteurs") or []]})
        for r in f["relations"]:
            forme = r.get("forme") or forme_deduite(r["effet"], r.get("retour"))
            liens.append({"de": f"{t}:{r['de']}", "vers": f"{t}:{r['vers']}", "forme": forme,
                          "forme_ecrite": r.get("forme") is not None, **{k: r.get(k) for k in
                          ("effet", "retour", "style", "delai", "force", "intensite", "coupure", "statut", "source", "texte",
                           "parametres", "series")},
                          "module": (f"{t}:{r['module'].split('>')[0]}>{t}:{r['module'].split('>')[1]}" if r.get("module") else None)})
        for p in f.get("ponts") or []:
            cible_theme, cible_comp = str(p["vers"]).split(":", 1)
            existe = cible_theme in fiches and any(c["id"] == cible_comp for c in fiches[cible_theme]["compartiments"])
            ponts.append({"de": f"{t}:{p['depuis']}", "vers": p["vers"], "nature": p.get("nature"), "resolu": existe,
                          "type": p.get("type", "influence")})
    identites = [{"total": f"{t}:{x['total']}", "termes": {f"{t}:{k}": v for k, v in x["termes"].items()},
                  "texte": x.get("texte")} for t, f in fiches.items() for x in f.get("identites") or []]
    cycles = [{"theme": t, **c} for t, f in fiches.items() for c in f.get("cycles") or []]
    tensions = [{"theme": t, **x} for t, f in fiches.items() for x in f.get("tensions") or []]
    return {"themes": sorted(fiches), "noeuds": noeuds, "relations": liens, "ponts": ponts, "identites": identites,
            "cycles": cycles, "tensions": tensions,
            "bilan": {"themes": len(fiches), "compartiments": len(noeuds), "relations": len(liens), "ponts": len(ponts),
                      "ponts_en_attente": sum(not p["resolu"] for p in ponts),
                      "relations_a_verifier": sum(l["statut"] == "a_verifier" for l in liens),
                      "relations_avec_intensite": sum(bool(l.get("intensite")) for l in liens),
                      "compartiments_sans_trace_collectee": sum(not any(tr.get("statut") == "collecte" for tr in n["traces"])
                                                               for n in noeuds)}}


def a_faire(s: dict) -> str:
    l = ["# Écosystèmes : liste de travail (écrite par ecosystemes.py, ne pas retoucher)", "",
         f"Bilan : {s['bilan']}", "", "## Thèmes à écrire (ponts en attente)"]
    attente: dict[str, list[str]] = {}
    for p in s["ponts"]:
        if not p["resolu"]:
            attente.setdefault(p["vers"].split(":")[0], []).append(f"{p['de']} → {p['vers']} ({p.get('nature') or ''})")
    for t in sorted(attente, key=lambda t: -len(attente[t])):
        l.append(f"- **{t}** ({len(attente[t])} pont(s)) : " + " ; ".join(attente[t]))
    l += ["", "## Compartiments sans trace collectée (à notre portée ? ou oubliés ?)"]
    for n in s["noeuds"]:
        if not any(tr.get("statut") == "collecte" for tr in n["traces"]):
            prop = [f"{tr.get('source')} ({tr.get('statut')})" for tr in n["traces"]]
            l.append(f"- {n['id']} : " + (", ".join(prop) if prop else "aucune trace connue"))
    l += ["", "## Relations à vérifier sur une source relue"]
    for r in s["relations"]:
        if r["statut"] == "a_verifier":
            l.append(f"- {r['de']} → {r['vers']} [{r['forme']}] {r.get('texte') or ''}")
    return "\n".join(l) + "\n"


def mermaid(fiche: dict) -> str:
    l = ["flowchart LR",
         "  classDef micro fill:#fff7e6,stroke:#d48806", "  classDef meso fill:#e6f4ff,stroke:#1677ff",
         "  classDef macro fill:#f0e6ff,stroke:#722ed1,stroke-width:3px"]
    for c in fiche["compartiments"]:
        ax = axes(c["niveau"])
        ta = ax["taille"] or [2, 2]
        echelle = NOMS_TAILLE[ta[0]] + ("" if ta[0] == ta[1] else f"–{NOMS_TAILLE[ta[1]]}")
        acteurs = "".join(f"<br/>· {a['nom']} ({a.get('taille')})" for a in c.get("acteurs") or [])
        l.append(f'  {c["id"]}["<b>{c.get("nom", c["id"])}</b><br/><i>{echelle} · {c["niveau"].get("vitesse", "")}</i>{acteurs}"]')
        l.append(f'  class {c["id"]} {"micro" if ta[1] == 1 else "macro" if ta[0] == 3 else "meso"}')
    fleche = {"competition": "<-.->", "mutualisme": "<==>", "predation": "-->", "forcage": "==>", "contrainte": "-.->"}
    for r in fiche["relations"]:
        forme = r.get("forme") or forme_deduite(r["effet"], r.get("retour"))
        etiquette = f'{forme} {r["effet"]}' + (f'/{r["retour"]}' if r.get("retour") is not None else "")
        if r.get("intensite"):
            etiquette += f' · intensité ({r["intensite"].get("regle")})'
        l.append(f'  {r["de"]} {fleche.get(forme, "-->")}|"{etiquette}"| {r["vers"]}')
    return "\n".join(l)


def mermaid_themes(fiches: dict[str, dict]) -> str:
    """Vue d'ensemble : un nœud par fiche (taille dominante en couleur), une arête par paire de fiches reliées par des
    ponts (épaisseur = nombre de ponts) ; thèmes sans fiche en pointillés."""
    s = assembler(fiches)
    l = ["flowchart LR", "  classDef ecrite fill:#f0e6ff,stroke:#722ed1,stroke-width:2px",
         "  classDef attente fill:#ffffff,stroke:#999,stroke-dasharray: 4 4"]
    ident = lambda t: t.replace("-", "_")
    for t, f in fiches.items():
        l.append(f'  {ident(t)}["<b>{f.get("nom", t)}</b><br/>{len(f["compartiments"])} compartiments · {len(f["relations"])} relations"]')
        l.append(f"  class {ident(t)} ecrite")
    paires: dict[tuple[str, str], int] = {}
    for p in s["ponts"]:
        a, b = p["de"].split(":")[0], p["vers"].split(":")[0]
        if a != b:
            k = tuple(sorted((a, b)))
            paires[k] = paires.get(k, 0) + 1
    for a, b in paires:
        for x in (a, b):
            if x not in fiches:
                l.append(f'  {ident(x)}["{x}"]')
                l.append(f"  class {ident(x)} attente")
    for (a, b), n in sorted(paires.items()):
        l.append(f"  {ident(a)} {'===' if n > 1 else '---'} {ident(b)}")
    return "\n".join(dict.fromkeys(l))


def principal(args) -> int:
    fiches = charger()
    erreurs = [e for f in fiches.values() for e in valider(f)]
    if erreurs:
        print("\n".join(erreurs))
        return 1
    if args.mermaid:
        print(mermaid_themes(fiches) if args.mermaid == "themes" else mermaid(fiches[args.mermaid]))
        return 0
    s = assembler(fiches)
    SCHEMA.write_text(json.dumps(s, ensure_ascii=False, indent=1), encoding="utf-8")
    A_FAIRE.write_text(a_faire(s), encoding="utf-8")
    print(json.dumps(s["bilan"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("--mermaid")
    sys.exit(principal(a.parse_args()))
