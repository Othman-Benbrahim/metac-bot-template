"""Dossier interne d'une question, schéma « dossier-1 » (preenregistrements/dossier-interne.md, validé par l'auteur le
2026-11-24 à 22 h 12). Objet à clés fixes, construit par le code seul ; chaque rubrique est un élément ou un silence
codé ; règles d'entrée R-brique, R-prix, R-carte, R-questionneur, R-sonde ; table d'aiguillage par famille.

    python dossier_interne.py "<titre>" <échéance AAAA-MM-JJ>
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import sys
from collections import Counter
from functools import lru_cache
from pathlib import Path

ICI = Path(__file__).resolve().parent
SCHEMA = "dossier-1"
SILENCES = ("aucune_brique", "donnees_anciennes", "hors_domaine", "hors_carte", "rattachement_insuffisant",
            "sonde_inactive", "coefficient_nul", "non_consultee")
MAX_RELATIONS = 5
FORCE = {"forte": 0, "moyenne": 1, "faible": 2}

# Performance hors échantillon des briques branchées (perte de la règle contre la référence ; registre cité).
PERF = {
    "banque_centrale": {"perte_regle": 0.469, "perte_reference": 0.663, "n": 47, "registre": "registre/banque-centrale.json"},
    "cessez_le_feu": {"perte_regle": 0.553, "perte_reference": 0.707, "registre": "registre/accords-etats.json"},
    "tenue": {"perte_regle": 0.719, "perte_reference": 0.857, "registre": "registre/accords-mid.json"},
    "autres_accords": {"perte_regle": 0.425, "perte_reference": 0.475, "registre": "registre/accords-autres.json"},
    "rencontres": {"perte_regle": 0.151, "perte_reference": 0.312, "n": 4, "registre": "registre/rencontres.json"},
    "sommets": {"perte_regle": 0.020, "perte_reference": 1.319, "n": 2, "registre": "registre/sommets.json"},
    "justice": {"perte_regle": 0.226, "perte_reference": 0.815, "n": 2, "registre": "registre/justice.json"},
}

# Table d'aiguillage (§ 4) : rubriques consultées par famille.
AIGUILLAGE = {
    "prix": ("briques", "prix", "carte", "questionneur"),
    "evenements": ("briques", "carte", "questionneur"),
    "maintien": ("briques", "questionneur", "carte"),
    "escalade": ("briques", "carte", "questionneur"),
    "cessez_le_feu": ("briques", "carte", "questionneur"),
    "tenue": ("briques", "carte", "questionneur"),
    "accord_guerre": ("briques", "carte", "questionneur"),
    "autres_accords": ("briques", "carte", "questionneur"),
    "competitions": ("briques", "questionneur"),
    "banque_centrale": ("briques", "questionneur"),
    "rencontres": ("briques", "questionneur"),
    "sommets": ("briques", "questionneur"),
    "justice": ("briques", "questionneur"),
    "sans_famille": ("questionneur", "carte", "sondes"),
}
MENTION_SANS_FAMILLE = "aucune mesure interne : marge réservée aux faits nouveaux sourcés"


def silence(code: str, **x) -> dict:
    assert code in SILENCES, code
    return {"silence": code, **x}


def _p(e: dict):
    p = e.get("p_regle", e.get("p"))
    return p if isinstance(p, (int, float)) else None


# Amendement du 2026-11-26 (A) : ce que chaque brique compte, et ce qu'elle ne compte pas. Recopié dans le dossier
# (briques[].domaine) pour le juge et le contradicteur.
DOMAINES = {
    "prix": "price of a quoted asset above or below a threshold at or before a date, by a random walk on recent volatility; "
            "does not cover decisions, announcements or unquoted indices",
    "evenements": "number of events of a type already counted by a series (measured rate); does not cover a single named event",
    "maintien": "a named leader or office-holder leaving office before a date, by mortality and departure tables (Archigos) "
                "in normal times; blind to an ongoing crisis; does not cover the resignation of a collective government",
    "escalade": "a military strike or attack between named states, by level on the escalation ladder; does not cover "
                "sanctions, verbal threats, counts of targets or conditional questions",
    "competitions": "prior of 1/N for one contender winning a competition; ignores the contenders' strength; does not cover "
                    "reaching a round or individual awards",
    "banque_centrale": "the US Federal Reserve's decision at ONE named FOMC meeting (hike, cut, hold); does not cover a "
                       "whole year or other central banks",
    "cessez_le_feu": "conclusion of a ceasefire in an ongoing war; does not cover conditional questions (if/iff), prizes "
                     "or meetings",
    "tenue": "breakdown of an existing truce before a date",
    "accord_guerre": "a peace agreement during an ongoing war (end of conflict)",
    "rencontres": "an IN-PERSON meeting of heads of state or government; does not count phone or video calls, envoys or "
                  "ministers",
    "sommets": "attendance of a head of state at a NATO summit",
    "justice": "a decision of the US Supreme Court in a case",
    "autres_accords": "an agreement requiring the consent of several parties (treaty, vote, trade deal), by the number of "
                      "consents required; does not cover a unilateral decision",
}


def _briques(titre: str, jour: dt.date, fin: str) -> list[tuple[str, str, dict | None, str | None]]:
    """(famille, mécanisme, sortie ou None, silence éventuel), dans l'ordre de la chaîne du bot."""
    import seuils_prix as spx, evenements_regle as evr, maintien_regle as mr, escalade_regle as es
    import competitions_regle as cp, banque_centrale_regle as bc
    import accords_etats as ae, accords_mid as am, accords_guerre as ag, accords_regle as ar
    import rencontres_regle as rr, sommets_regle as so, justice_regle as jr
    j = jour.isoformat()
    essais = [
        ("prix", "seuils de prix : marche aléatoire log-normale calibrée sur la volatilité à 30 jours (FRED)",
         lambda: spx.estimer(titre, j, spx.echeance(titre, j) or fin)),
        ("evenements", "événements comptés : taux mesuré sur la série du compte", lambda: evr.estimer(titre, j, fin, 0.5)),
        ("maintien", "maintien au pouvoir : tables de mortalité et de départs (Archigos)",
         lambda: mr.estimer(titre, j, fin, 0.5, False)),
        ("escalade", "échelle de l'escalade", lambda: es.estimer(titre, 0.5)),
        ("competitions", "un parmi N", lambda: cp.estimer(titre, 0.5)),
        ("banque_centrale", "inertie de la Fed : chaîne de Markov sur les réunions du FOMC depuis 1994",
         lambda: bc.estimer(titre, jour)),
        ("cessez_le_feu", "conclusion d'un cessez-le-feu : COW (interétatiques, après 1946), ETH/PRIO (internes)",
         lambda: ae.estimer(titre, jour)),
        ("tenue", "tenue d'une trêve : échecs mesurés (MID, ETH/PRIO)", lambda: am.estimer(titre, jour)),
        ("accord_guerre", "accord de paix pendant une guerre : hasards de fin de conflit (UCDP)",
         lambda: ag.estimer(titre, jour)),
        ("rencontres", "rencontre au sommet : fréquence sur 5 ans (COLT)", lambda: rr.estimer(titre, jour)),
        ("sommets", "présence aux sommets de l'OTAN (COLT, liste des sommets)", lambda: so.estimer(titre, jour)),
        ("justice", "Cour suprême des États-Unis (SCDB)", lambda: jr.estimer(titre, jour)),
        ("autres_accords", "autres accords : tranches de consentements requis", lambda: ar.estimer_autres(titre)),
    ]
    out = []
    for fam, meca, f in essais:
        try:
            e = f()
        except Exception:
            e = None
        if e and _p(e) is not None:
            out.append((fam, meca, e, None))
        elif fam == "prix":
            q = spx.lire(titre)
            if q:
                pts = [d for d, _ in spx.points(q["actif"]) if d < j]
                out.append((fam, meca, None, pts[-1] if pts else "absent"))
    return out


@lru_cache(1)
def _taux_structure():
    import structures_questions as sq
    vus, n, o, d = set(), Counter(), Counter(), []
    for l in (ICI / "registre" / "jugement-questions.jsonl").read_text(encoding="utf-8").splitlines():
        q = json.loads(l)
        if q["titre"] in vus or str(q.get("issue")) not in ("0", "1"):
            continue
        vus.add(q["titre"])
        s = sq.structure(q["titre"])
        n[s] += 1
        o[s] += str(q["issue"]) == "1"
        d.append(q.get("resolue_le") or q.get("jeu") or "")
    d = sorted(x[:10] for x in d if x)
    return n, o, len(vus), sum(o.values()), (d[0], d[-1]) if d else (None, None)


@lru_cache(1)
def _lecteurs():
    sys.path.insert(0, str(ICI))
    from mise_au_point.lecture_mecanique import Carte
    import sondes
    return Carte(), sondes.Sondes()


def rattachement(titre: str) -> tuple[set, list]:
    """Compartiments rattachés par les termes d'un titre (jamais par le pays seul) et pays reconnus ; partagé par
    R-carte et par le signalement des questions touchées par les briefs (briefs_questions.py, 2026-11-25)."""
    carte, _ = _lecteurs()
    theme = set()
    for m, rs in carte.mt:
        x = m.search(titre)
        if x and not _est_pays(x.group(0)):           # un nom de pays ou un gentilé ne rattache jamais seul
            theme |= {r for r in rs if r in carte.ids}
    pays = sorted({i for m, i in carte.mp if m.search(titre)})
    if pays:                                          # même filtre que la lecture : thème lié à d'autres pays écarté
        geo = set().union(*carte.par_pays.values())
        lies = set().union(*(carte.par_pays[p] for p in pays))
        theme = {c for c in theme if c not in geo or c in lies}
    return theme, pays


def _carte(titre: str, horizon: int) -> dict | list:
    """R-carte : compartiments rattachés par les termes de la question (jamais par le pays seul) ; relations entrantes
    dont le délai tient dans l'horizon ; au plus 5, par force décroissante."""
    from mise_au_point.lecture_mecanique import DELAI_JOURS
    carte, _ = _lecteurs()
    theme, pays = rattachement(titre)
    if not theme:
        return silence("rattachement_insuffisant", pays=pays)
    verif = _verifications()
    rel = []
    for c in sorted(theme):
        for r in carte.entrants.get(c, []):
            d = DELAI_JOURS.get(str(r.get("delai") or "").strip())
            if d is None or d > horizon:
                continue
            rel.append({"de": r["de"], "vers": c, "effet": r.get("effet"), "delai": r.get("delai"),
                        "force": r.get("force"), "phrase": r.get("texte"), "source": r.get("source"),
                        "statut_verification": verif.get((r["de"], c), "non vérifiée"),
                        "regle_entree": "R-carte"})
    rel.sort(key=lambda e: (FORCE.get(e["force"], 3), e["de"]))
    return {"compartiments": sorted(theme), "relations": rel[:MAX_RELATIONS],
            "relations_hors_liste": max(0, len(rel) - MAX_RELATIONS)} if rel else \
        {"compartiments": sorted(theme), "relations": [], "silence_relations": "hors_carte"}


def _est_pays(mot: str) -> bool:
    import re
    import ecosysteme_objet as eo
    carte, _ = _lecteurs()
    if any(m.fullmatch(mot) for m, _ in carte.mp):
        return True
    return any(re.fullmatch(rf"(?:{g})\w*", mot, re.I) for g in eo.GENTILES.values()) or \
        any(re.fullmatch(rf"{re.escape(n)}\w*", mot, re.I) for n in _noms_pays())


@lru_cache(1)
def _noms_pays() -> tuple:
    import csv
    return tuple(r["nom"] for r in csv.DictReader(l for l in (ICI / "ecosystemes" / "codes-pays-fips.csv")
                 .read_text(encoding="utf-8").splitlines() if l and not l.startswith("#")) if r.get("nom"))


@lru_cache(1)
def _verifications() -> dict:
    try:
        v = json.loads((ICI / "registre" / "verification-relations.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    out = {}
    for x in v.get("relations", v if isinstance(v, list) else []):
        if isinstance(x, dict) and x.get("de") and x.get("vers"):
            f = x.get("fiche", "")
            out[(f"{f}:{x['de']}", f"{f}:{x['vers']}")] = x.get("verdict") or "non vérifiée"
    return out


def construire(titre: str, fin: str, jour: dt.date | None = None, qid: str | None = None) -> dict:
    import sondes
    import structures_questions as sq
    import seuils_prix as spx
    jour = jour or dt.date.today()
    horizon = max(1, (dt.date.fromisoformat(fin) - jour).days)
    B = _briques(titre, jour, fin)
    reconnues = [b for b in B if b[2] is not None]
    famille = (reconnues[0][0] if reconnues else B[0][0] if B else "sans_famille")
    rubriques = AIGUILLAGE[famille]
    D = {"schema": SCHEMA,
         "question": {"id": qid, "titre": titre, "echeance": fin, "horizon_jours": horizon,
                      "date_information": jour.isoformat(), "structure": sq.structure(titre), "famille": famille},
         "briques": None, "prix": None, "carte": None, "questionneur": None, "sondes": None, "a_chercher": [],
         "mention": MENTION_SANS_FAMILLE if famille == "sans_famille" else None}
    # R-brique
    if "briques" in rubriques:
        el = []
        for fam, meca, e, _ in reconnues:
            el.append({"famille": fam, "mecanisme": meca, "domaine": DOMAINES.get(fam), "valeur": round(_p(e), 4),
                       "unite": "probabilité",
                       "date_donnee": e.get("date_prix") or e.get("date_donnee"), "n": e.get("n"),
                       "perf": PERF.get(fam), "regle_entree": "R-brique"})
        ancien = next((x[3] for x in B if x[0] == "prix" and x[2] is None), None)
        qp = spx.lire(titre)
        if not el and qp and qp["actif"] in spx.ACTIONS and not spx.ACTIONS_DANS_LE_BOT:
            D["briques"] = silence("hors_domaine", motif="actions non branchées")
        else:
            D["briques"] = el or (silence("donnees_anciennes", date_donnee=ancien) if ancien else silence("aucune_brique"))
    else:
        D["briques"] = silence("aucune_brique")
    # R-prix
    if "prix" in rubriques:
        q = spx.lire(titre)
        e = next((x[2] for x in B if x[0] == "prix" and x[2]), None)
        ancien = next((x[3] for x in B if x[0] == "prix" and x[2] is None), None)
        if e:
            D["prix"] = {"actif": e["actif"], "valeur": e["dernier_prix"], "date_donnee": e["date_prix"],
                         "volatilite_annuelle_30j": e["sigma_annuel"], "seuil": e["k"], "source": e.get("source_prix", "FRED") + ", " + e["actif"], "source_volatilite": "FRED",
                         "regle_entree": "R-prix"}
        elif q and q["actif"] in spx.ACTIONS and not spx.ACTIONS_DANS_LE_BOT:
            D["prix"] = silence("hors_domaine", actif=q["actif"],
                                motif="actions non branchées (preenregistrements/seuils-de-prix-actions.md)")
            D["a_chercher"].append({"fait": "dernier_cours", "actif": q["actif"],
                                    "consigne": f"dernier cours de clôture connu de {q['actif']} (date et source)"})
        elif q:
            D["prix"] = silence("donnees_anciennes", actif=q["actif"], date_donnee=ancien)
            D["a_chercher"].append({"fait": "dernier_cours", "actif": q["actif"],
                                    "consigne": f"dernier cours de clôture connu de {q['actif']} (date et source)"})
    else:
        D["prix"] = silence("non_consultee")
    # R-carte
    D["carte"] = _carte(titre, horizon) if "carte" in rubriques else silence("non_consultee")
    # R-questionneur (toujours)
    n, o, tot, oui, per = _taux_structure()
    s = D["question"]["structure"]
    if n[s] >= 20:
        D["questionneur"] = {"valeur": round(o[s] / n[s], 4), "unite": "part de oui", "n": n[s], "portee": f"structure « {s} »",
                             "periode": per, "source": "registre/jugement-questions.jsonl", "regle_entree": "R-questionneur"}
    else:
        D["questionneur"] = {"valeur": round(oui / tot, 4), "unite": "part de oui", "n": tot, "portee": "tout le corpus",
                             "periode": per, "source": "registre/jugement-questions.jsonl", "regle_entree": "R-questionneur"}
    # a_chercher par famille
    if famille in ("cessez_le_feu", "tenue", "accord_guerre", "escalade"):
        D["a_chercher"].append({"fait": "etat_des_combats", "consigne": "dernière date de combat sourcée et état des combats"})
    if famille == "maintien":
        D["a_chercher"].append({"fait": "titulaire_en_fonction", "consigne": "le titulaire est-il en fonction (date, source)"})
    # R-sonde
    if "sondes" in rubriques:
        _, S = _lecteurs()
        E = sondes.etat().get("sondes") or {}
        el = []
        for k, v in (S.lire(titre, horizon, jour) or {}).items():
            e = E.get(k, {})
            if not e.get("actif"):
                el.append(silence("sonde_inactive", sonde=k))
            elif not e.get("k"):
                el.append(silence("coefficient_nul", sonde=k))
            else:
                el.append({"sonde": k, "direction": v["d"], "sens_du_oui": v["sens"], "k": e["k"],
                           "plafond": e.get("plafond"), "n": (e.get("etalon") or {}).get("lues"), "regle_entree": "R-sonde"})
        D["sondes"] = el or silence("hors_carte")
    else:
        D["sondes"] = silence("non_consultee")
    D["empreinte"] = empreinte(D)
    return D


def empreinte(D: dict) -> str:
    x = {k: v for k, v in D.items() if k != "empreinte"}
    return hashlib.sha256(json.dumps(x, ensure_ascii=False, sort_keys=True, default=str).encode()).hexdigest()


def pour_recherche(D: dict) -> dict:
    """Ce que reçoit l'étape de recherche (§ 2) : la question et les faits à chercher, aucune valeur interne."""
    return {"question": {k: D["question"][k] for k in ("titre", "echeance")}, "a_chercher": D["a_chercher"]}


if __name__ == "__main__":
    print(json.dumps(construire(sys.argv[1], sys.argv[2]), ensure_ascii=False, indent=1, default=str))
