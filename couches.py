"""Le brief en deux couches (plan validé par l'auteur le 2026-11-27, 23 h 36 ; claude/plan-brief-visible-invisible-2026-11-27.md).

Couche visible : les briefs traités (brief.py). Couche non visible : tous les autres articles du puits, en métadonnées
seules (lien, titre, source, pays, noms, matières ; jamais le texte). Ce module travaille sur la couche non visible :

1. Nuage de mots : les termes des métadonnées des articles NON traités du jour (noms, pays, matières), chacun avec ses
   articles (titre, lien, source). Décision de l'auteur : un nuage cliquable sur la page des briefs, pour remonter aux
   sources des articles non visibles.
2. Détecteurs de signaux faibles (critères retenus par l'auteur) — EN OMBRE : ils écrivent leurs alertes dans
   registre/signaux-faibles.jsonl et sur la page (seules les alertes sont affichées, décision de l'auteur), sans rien
   remonter dans les briefs tant que la période d'observation (deux semaines) n'est pas finie :
   - montée anormale : un terme dans nettement plus de titres que d'habitude ;
   - signal isolé : un seul article du jour touche un compartiment relié à une question ouverte ;
   - source inattendue : une source parle d'une famille de situation qu'elle n'a jamais traitée dans son historique.
3. Classement en ombre : les articles que le classement (source primaire, utilité, une histoire une fois, nouveauté)
   aurait choisis, comparés à ceux que le tour de rôle actuel a choisis (registre/classement-ombre.jsonl).

Seuils fixés AVANT toute donnée (2026-11-27, 23 h 50) : voir les constantes ci-dessous. Aucun modèle de langue, aucun crédit.

    uv run python couches.py [--jour AAAA-MM-JJ]     (par défaut : la veille, jour UTC complet)
"""
from __future__ import annotations

import argparse
import collections
import csv
import json
import re
from datetime import date, timedelta
from pathlib import Path

import puits

ICI = Path(__file__).resolve().parent
REG = ICI / "registre"
SORTIE = REG / "couche-invisible.json"
JOURNAL_ALERTES = REG / "signaux-faibles.jsonl"
JOURNAL_CLASSEMENT = REG / "classement-ombre.jsonl"

# --- seuils, fixés avant toute donnée (ne pas modifier sans amendement daté) ---
HISTO_JOURS = 14          # fenêtre de référence
HISTO_MIN_JOURS = 7       # en dessous : « chauffe », aucune alerte de montée
MONTEE_MIN = 3            # au moins 3 titres distincts le jour J
MONTEE_RAPPORT = 4.0      # et au moins 4 fois la moyenne quotidienne de référence
MONTEE_PLANCHER = 0.25    # moyenne de référence plancher (un terme jamais vu compte comme 0,25 par jour)
INATTENDUE_MIN_HISTO = 20  # une source doit avoir au moins 20 articles d'historique
NUAGE_TERMES = 40
NUAGE_ARTICLES = 20
FIN_OMBRE = "2026-12-12"  # fin de la période d'observation des détecteurs (deux semaines) ; décision de l'auteur ensuite
PLACES_RESERVEES = 2      # places de brief réservées aux signaux faibles (validé par l'auteur), actives après FIN_OMBRE

POIDS_TYPE = {"primaire_officielle": 4, "agence": 3, "ong_analyse": 3, "centre_recherche": 3, "presse_specialisee": 2,
              "revue_specialisee": 2, "media_public": 2, "presse_generaliste": 1, "blog_entreprise": 1,
              "agregateur": 0, "media_d_etat": 0}


def etiquettes() -> dict[str, dict]:
    f = REG / "sources-etiquettes.csv"
    try:
        with f.open(encoding="utf-8") as h:
            return {r["domaine"]: r for r in csv.DictReader(h)}
    except OSError:
        return {}


def _etiquette(dom: str, et: dict) -> dict:
    while dom and dom not in et and "." in dom:
        dom = dom.split(".", 1)[1]        # sous-domaine → domaine (feeds.bbci.co.uk → bbci.co.uk)
    return et.get(dom, {})


def traites(jour: str) -> set[str]:
    """Liens des briefs réussis du jour (couche visible)."""
    f = ICI / "briefs" / "journal.jsonl"
    out = set()
    try:
        for l in f.open(encoding="utf-8"):
            try:
                x = json.loads(l)
            except ValueError:
                continue
            if x.get("jour") == jour and x.get("statut", "ok") == "ok" and x.get("url"):
                out.add(x["url"])
    except OSError:
        pass
    return out


def termes(r: dict) -> list[tuple[str, str]]:
    return ([(n, "nom") for n in r.get("n") or []] + [(p, "pays") for p in r.get("p") or []]
            + [(m, "matiere") for m in r.get("m") or []])


# ---------- 1. nuage ----------

def nuage(rows: list[dict], visibles: set[str]) -> list[dict]:
    par = collections.defaultdict(dict)
    for r in rows:
        if r["u"] in visibles:
            continue
        for t, ty in termes(r):
            par[(t, ty)].setdefault(r["u"], {"titre": r["t"], "lien": r["u"], "source": r.get("d", "")})
    tri = sorted(par.items(), key=lambda x: (-len(x[1]), x[0][0]))[:NUAGE_TERMES]
    return [{"terme": t, "type": ty, "n": len(arts), "articles": list(arts.values())[:NUAGE_ARTICLES]}
            for (t, ty), arts in tri]


# ---------- 2. détecteurs ----------

def montee(rows_jour: list[dict], histo: list[dict], jour: str) -> list[dict]:
    jours = {r["j"] for r in histo}
    if len(jours) < HISTO_MIN_JOURS:
        return []
    ref = collections.Counter()
    for r in histo:
        for t, ty in set(termes(r)):
            ref[(t, ty)] += 1
    auj = collections.defaultdict(dict)
    for r in rows_jour:
        for t, ty in set(termes(r)):
            auj[(t, ty)][r["t"].lower()] = r      # titres distincts
    out = []
    for (t, ty), titres in auj.items():
        n = len(titres)
        moy = max(ref[(t, ty)] / len(jours), MONTEE_PLANCHER)
        if n >= MONTEE_MIN and n >= MONTEE_RAPPORT * moy:
            ex = list(titres.values())[0]
            out.append({"detecteur": "montee", "terme": t, "type": ty, "n_jour": n, "moyenne_ref": round(moy, 2),
                        "titre": ex["t"], "lien": ex["u"], "source": ex.get("d", "")})
    return sorted(out, key=lambda a: -a["n_jour"] / a["moyenne_ref"])


def _rattacher(titre: str) -> set:
    try:
        import dossier_interne as di
        return set(di.rattachement(titre)[0])
    except Exception:
        return set()


def compartiments_ouverts(jour: str) -> set:
    try:
        import briefs_questions as bq
        out = set()
        for q in bq.questions_ouvertes(jour).values():
            out |= _rattacher(q["titre"])
        return out
    except Exception:
        return set()


def isole(rows_jour: list[dict], ouverts: set) -> list[dict]:
    if not ouverts:
        return []
    par_comp = collections.defaultdict(list)
    for r in rows_jour:
        for c in _rattacher(r["t"]) & ouverts:
            par_comp[c].append(r)
    return [{"detecteur": "isole", "terme": c, "type": "compartiment", "titre": rs[0]["t"], "lien": rs[0]["u"],
             "source": rs[0].get("d", "")} for c, rs in par_comp.items() if len(rs) == 1]


def _famille(titre: str) -> str:
    try:
        from familles_situation import familles
        fs = familles(titre)
        return fs[0] if fs else ""
    except Exception:
        return ""


def inattendue(rows_jour: list[dict], histo: list[dict]) -> list[dict]:
    hist = collections.defaultdict(collections.Counter)
    for r in histo:
        hist[r.get("d", "")][_famille(r["t"])] += 1
    out = []
    for r in rows_jour:
        d, fam = r.get("d", ""), _famille(r["t"])
        h = hist.get(d)
        if fam and h and sum(h.values()) >= INATTENDUE_MIN_HISTO and h[fam] == 0:
            out.append({"detecteur": "inattendue", "terme": fam, "type": "famille", "titre": r["t"], "lien": r["u"],
                        "source": d})
    return out


# ---------- 3. classement en ombre ----------

_MOT = re.compile(r"[^\W\d_]{4,}", re.U)


def _cle_histoire(r: dict) -> frozenset:
    return frozenset(r.get("n") or []) or frozenset(w.lower() for w in _MOT.findall(r["t"])[:6])


def classement(rows_jour: list[dict], ouverts: set, deja: set[str], et: dict, n: int) -> list[dict]:
    """Une histoire = des titres qui partagent au moins deux noms (ou mots) ; on garde la meilleure source de chaque
    histoire. Score : type de source + 3 si compartiment relié à une question ouverte + 1 par source indépendante en plus
    (propriétaires différents, au plus +3) − 3 si le lien a déjà été traité."""
    histoires: list[list[dict]] = []
    for r in rows_jour:
        k = _cle_histoire(r)
        for h in histoires:
            if len(k & _cle_histoire(h[0])) >= 2:
                h.append(r)
                break
        else:
            histoires.append([r])
    out = []
    for h in histoires:
        def s(r):
            e = _etiquette(r.get("d", ""), et)
            return POIDS_TYPE.get(e.get("type", ""), 1)
        best = max(h, key=s)
        proprios = {(_etiquette(r.get("d", ""), et).get("proprietaire_ou_financeur") or r.get("d", "")) for r in h}
        score = s(best) + (3 if _rattacher(best["t"]) & ouverts else 0) + min(len(proprios) - 1, 3) \
            - (3 if best["u"] in deja else 0)
        out.append({"lien": best["u"], "titre": best["t"], "source": best.get("d", ""), "score": score,
                    "sources_independantes": len(proprios)})
    return sorted(out, key=lambda x: -x["score"])[:n]


# ---------- principal ----------

def _ajouter_journal(f: Path, lignes: list[dict], jour: str) -> None:
    deja = set()
    try:
        deja = {json.loads(l).get("cle") for l in f.open(encoding="utf-8")}
    except OSError:
        pass
    with f.open("a", encoding="utf-8") as h:
        for l in lignes:
            cle = f"{jour}|{l.get('detecteur', 'classement')}|{l.get('lien')}|{l.get('terme', '')}"
            if cle not in deja:
                h.write(json.dumps({"jour": jour, "cle": cle, **l}, ensure_ascii=False) + "\n")


def principal(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jour", default=(date.today() - timedelta(days=1)).isoformat())
    a = ap.parse_args(argv)
    j = date.fromisoformat(a.jour)
    rows_jour = puits.charger(j, j)
    histo = puits.charger(j - timedelta(days=HISTO_JOURS), j - timedelta(days=1))
    visibles = traites(a.jour)
    ouverts = compartiments_ouverts(a.jour)
    alertes = montee(rows_jour, histo, a.jour) + isole(rows_jour, ouverts) + inattendue(rows_jour, histo)
    # 2026-11-28 : alertes de la veille des trêves (treves.py), affichées avec les signaux faibles ; seules celles que
    # le garde-fou du modèle garde « à vérifier » (ou qu'il n'a pas pu filtrer) sont montrées.
    try:
        tr = json.loads((REG / "treves-alertes.json").read_text(encoding="utf-8"))
        for x in tr.get("alertes", []):
            if x.get("statut") in ("a_verifier", "non_filtree"):
                ex = next((t for t in x.get("titres", []) if t.get("classe") == "treve_declaree"), None) or {}
                alertes.append({"detecteur": "treve", "terme": x["guerre"], "type": "guerre_suivie",
                                "titre": ex.get("titre") or f"trêve possible ({', '.join(x.get('sources', {}))}) : table des guerres à vérifier",
                                "lien": ex.get("lien", ""), "source": x["statut"]})
    except (OSError, ValueError, KeyError):
        pass
    et = etiquettes()
    deja = {u for k in range(1, 8) for u in traites((j - timedelta(days=k)).isoformat())}
    ombre = classement(rows_jour, ouverts, deja, et, max(len(visibles), 16))
    res = {"jour": a.jour, "articles": len(rows_jour), "traites": len(visibles),
           "historique_jours": len({r["j"] for r in histo}), "en_ombre_jusqu_au": FIN_OMBRE,
           "seuils": {"montee": f">= {MONTEE_MIN} titres et >= {MONTEE_RAPPORT} x la moyenne des {HISTO_JOURS} jours "
                                f"(au moins {HISTO_MIN_JOURS} jours d'historique)",
                      "isole": "un seul article du jour sur un compartiment relié à une question ouverte",
                      "inattendue": f"famille jamais traitée par la source (au moins {INATTENDUE_MIN_HISTO} articles d'historique)"},
           "alertes": alertes, "nuage": nuage(rows_jour, visibles),
           "classement_ombre": {"choisis": len(ombre), "communs_avec_les_briefs": len({x['lien'] for x in ombre} & visibles)}}
    SORTIE.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    _ajouter_journal(JOURNAL_ALERTES, [{**x, "remonte": False} for x in alertes], a.jour)
    _ajouter_journal(JOURNAL_CLASSEMENT, [{**x, "dans_les_briefs": x["lien"] in visibles} for x in ombre], a.jour)
    print(f"{a.jour} : {len(rows_jour)} articles, {len(visibles)} traités, {len(alertes)} alertes "
          f"({collections.Counter(x['detecteur'] for x in alertes)}), classement en ombre : {len(ombre)} choisis, "
          f"{res['classement_ombre']['communs_avec_les_briefs']} en commun avec les briefs")
    return 0


if __name__ == "__main__":
    raise SystemExit(principal())
