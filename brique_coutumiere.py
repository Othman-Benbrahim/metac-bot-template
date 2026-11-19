"""Brique « scrutin » coutumière (bot 0.10.372, ombre).

Remplace les deux règles inventées de banc_scrutin.py (approximation du second tour, σ(t) = σ₀·√(1 + t/30)) par les
règles sourcées de ecosystemes/regles-coutumieres.yaml, lues par leur identifiant. Décision d'auteur du 2026-11-19 :
ne pas déduire ; sans règle sourcée pour l'échelle de la question, la brique s'abstient et dit quelle règle manque.

Ce que la brique lit dans la base (identifiant → usage) :
- presidentielles_mode_de_scrutin : deux tours ou un tour, par pays ;
- second_tour_retournement : probabilité que le deuxième du premier tour gagne le second, par région (moins de 30 cas
  → chiffre mondial) ;
- sondages_erreur_comparee : erreur sur la part (dernière semaine) par type d'élection hors États-Unis ;
- us_erreur_sondages_par_echelle : erreur sur l'écart (21 derniers jours) par type d'élection aux États-Unis ;
- us_erreur_selon_temps_restant : erreur selon le temps restant (≈ 2 la veille, 3 à 50 jours, 4 à 150-200 jours) ;
- us_erreur_primaires_d_etat (absence) : primaires d'État → abstention.
Arithmétique (pas des règles) : à deux candidats, l'erreur sur l'écart vaut deux fois l'erreur sur la part ; pour une
loi normale, l'erreur moyenne absolue vaut √(2/π) ≈ 0,8 σ. Ces deux conversions sont celles écrites dans la base.

`python brique_coutumiere.py --couverture` : compte les questions jugées et les abstentions par motif, SANS lire les
issues. `python brique_coutumiere.py` : test préenregistré (preenregistrements/scrutin-coutumier.md), une seule fois.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from datetime import date
from pathlib import Path

import re

import numpy as np

import banc_scrutin as bs
import regles_coutumieres as rc

SORTIE = Path("registre") / "banc-scrutin-coutumier.json"
DETAIL = Path("registre") / "scrutins" / "detail-coutumier.jsonl"

ETATS_US = {"alabama", "alaska", "arizona", "arkansas", "california", "colorado", "connecticut", "delaware", "florida",
            "georgia", "hawaii", "idaho", "illinois", "indiana", "iowa", "kansas", "kentucky", "louisiana", "maine",
            "maryland", "massachusetts", "michigan", "minnesota", "mississippi", "missouri", "montana", "nebraska",
            "nevada", "new hampshire", "new jersey", "new mexico", "new york", "north carolina", "north dakota", "ohio",
            "oklahoma", "oregon", "pennsylvania", "rhode island", "south carolina", "south dakota", "tennessee", "texas",
            "utah", "vermont", "virginia", "washington", "west virginia", "wisconsin", "wyoming"}
# noms de pays → code ISO (faits de nomenclature, pas des règles) ; seulement les pays présents dans les tables de la base
PAYS = {"mongolia": "MN", "mongolian": "MN", "kazakhstan": "KZ", "kyrgyz": "KG", "turkey": "TR", "turkish": "TR",
        "iran": "IR", "iranian": "IR", "nigeria": "NG", "nigerian": "NG", "kenya": "KE", "kenyan": "KE", "senegal": "SN",
        "ivory coast": "CI", "ivorian": "CI", "cote d'ivoire": "CI", "ghana": "GH", "ghanaian": "GH", "zimbabwe": "ZW",
        "mozambique": "MZ", "republic of the congo": "CG", "ecuador": "EC", "ecuadorian": "EC", "bolivia": "BO",
        "germany": "DE", "german": "DE", "netherlands": "NL", "dutch": "NL", "czech": "CZ", "hungar": "HU", "sweden": "SE",
        "swedish": "SE", "norw": "NO", "latvia": "LV", "italy": "IT", "italian": "IT", "greece": "GR", "greek": "GR",
        "spain": "ES", "spanish": "ES", "belgi": "BE", "denmark": "DK", "danish": "DK", "bulgaria": "BG", "slovak": "SK", "uganda": "UG", "ugandan": "UG", "brazil": "BR", "brazilian": "BR", "argentina": "AR",
        "argentine": "AR", "colombia": "CO", "colombian": "CO", "chile": "CL", "chilean": "CL", "peru": "PE",
        "peruvian": "PE", "france": "FR", "french": "FR", "portugal": "PT", "portuguese": "PT", "poland": "PL",
        "polish": "PL", "romania": "RO", "romanian": "RO", "austria": "AT", "austrian": "AT", "indonesia": "ID",
        "indonesian": "ID", "south korea": "KR", "korean": "KR", "taiwan": "TW", "taiwanese": "TW", "philippines": "PH",
        "philippine": "PH", "cameroon": "CM", "tanzania": "TZ", "democratic republic of the congo": "CD", "dr congo": "CD", "mexico": "MX", "mexican": "MX",
        "venezuela": "VE", "russia": "RU", "russian": "RU", "canada": "CA", "canadian": "CA", "australia": "AU",
        "australian": "AU", "venezuelan": "VE", "sri lanka": "LK"}
# région de la règle second_tour_retournement ; TR et l'Asie centrale : rattachement incertain ou trop peu de cas → monde
REGION = {**dict.fromkeys(["NG", "KE", "SN", "CI", "GH", "ZW", "MZ", "UG"], "afrique"),
          **dict.fromkeys(["BR", "AR", "CO", "CL", "PE"], "amerique_latine"),
          **dict.fromkeys(["FR", "PT", "PL", "RO", "AT"], "europe"),
          **dict.fromkeys(["ID", "IR", "MN", "KZ", "KG"], "asie")}


def _p(i: str) -> dict:
    r = {x["id"]: x for x in rc.regles()}[i]
    if r["statut"] != "source":
        raise KeyError(f"{i} : statut {r['statut']}")
    return r["parametres"]


def multiplicateur(jours: float) -> float:
    """us_erreur_selon_temps_restant : ≈ 2 la veille, 3 à 50 jours, 4 à 150-200 jours ; interpolation linéaire."""
    e = _p("us_erreur_selon_temps_restant")["erreur_part_points"]
    xs, ys = [0, 50, 150], [e["veille"], e["j50"], e["j150_200"]]
    return float(np.interp(max(jours, 0), xs, ys))


ECHELLES = {
    "bresil_etats": [bs._norm(x) for x in ("Acre", "Alagoas", "Amapá", "Amazonas", "Bahia", "Ceará", "Federal District",
                     "Espírito Santo", "Goiás", "Maranhão", "Mato Grosso", "Minas Gerais", "Pará", "Paraíba", "Paraná",
                     "Pernambuco", "Piauí", "Rio de Janeiro", "Rio Grande", "Rondônia", "Roraima", "Santa Catarina",
                     "São Paulo", "Sergipe", "Tocantins")],
    "allemagne_lander": ["baden", "bavaria", "berlin state", "brandenburg", "bremen", "hamburg", "hesse", "lower saxony",
                         "mecklenburg", "north rhine", "rhineland", "saarland", "saxony", "sachsen", "schleswig",
                         "thuringia"],
    "canada_provinces": ["alberta", "british columbia", "manitoba", "new brunswick", "newfoundland", "nova scotia",
                         "ontario", "prince edward", "quebec", "saskatchewan"],
}


def _mesure_infra(echelle: str) -> dict | None:
    f = Path("registre") / "erreur-regionale" / "mesures.json"
    if not f.exists():
        return None
    return (json.loads(f.read_text(encoding="utf-8")) or {}).get(echelle)


def echelle_infranationale(e: str, f: dict) -> dict | None:
    """Élections infranationales : erreur MESURÉE (erreur_regionale.py) si l'échelle réunit 30 élections, sinon
    abstention. None = pas une élection infranationale reconnue."""
    titre = (f.get("titre") or "").lower()
    if any(w in e for w in ("mayor", "mayoral", "city council", "municipal")):
        import erreur_regionale as er
        villes_us = {bs._norm(v) for v in er.VILLES} | {"nyc"}
        villes_kr = {bs._norm(v) for v in er.COREE_VILLES}
        echelle = ("etats_unis_villes" if any(s in e for s in ETATS_US | villes_us) or "nyc" in titre
                   else "coree_collectivites" if any(v in e for v in villes_kr) else None)
        if not echelle:
            return {"motif": "élection municipale hors États-Unis : erreur non mesurée"}
    elif ("gubernatorial" in e or "governor" in e or "senate" in e) and any(k in e for k in ECHELLES["bresil_etats"]) \
            and not any(s in e for s in ETATS_US):
        echelle = "bresil_etats"
    elif "gubernatorial" in e and any(bs._norm(p_) in e for p_ in __import__("erreur_regionale").COREE_PROVINCES):
        echelle = "coree_collectivites"
    elif any(k in e for k in ECHELLES["allemagne_lander"]) and ("state" in e or "parliament" in e):
        echelle = "allemagne_lander"
    elif any(k in e for k in ECHELLES["canada_provinces"]) and "general election" in e:
        echelle = "canada_provinces"
    else:
        return None
    m = _mesure_infra(echelle)
    if not m or m.get("statut") != "mesurable":
        return {"motif": f"élection infranationale ({echelle}) : erreur des sondages non mesurée ou moins de 30 élections"}
    if "seats" in titre or "largest party" in titre:
        return {"motif": f"sièges à l'échelle infranationale ({echelle}) : voix → sièges mesuré seulement au niveau national"}
    r = {"sigma": m["sigma"], "fenetre": 7, "type": echelle,
         "regles": ["erreur_infranationale_mesuree", "us_erreur_selon_temps_restant"]}
    if echelle == "bresil_etats" and "senate" not in e and f["evenement"] == "gagne":
        if m.get("taux_retournement") is None:
            return {"motif": "gouverneur brésilien : retournement au second tour non mesuré (moins de 30 seconds tours)"}
        return {**r, "mode": "deux_tours", "retournement": m["taux_retournement"],
                "regles": r["regles"] + ["bresil_gouverneurs_senat"]}
    if echelle == "bresil_etats":
        r["regles"].append("bresil_gouverneurs_senat")
    return {**r, "mode": "un_tour"}


def rattacher(f: dict) -> dict:
    """Forme de la question → règles applicables, ou abstention avec la règle qui manque."""
    e = bs._norm(f["election"])
    us = (any(s in e for s in ETATS_US) or re.search(r"\bus\b", e) is not None
          or any(w in e for w in ("u.s.", "united states", "congress")))
    pays = next((v for k, v in sorted(PAYS.items(), key=lambda kv: -len(kv[0])) if k in e), None)
    infra = echelle_infranationale(e, f)
    if infra is not None:
        return infra
    if "primary" in e or "nomination" in e or f["classe"] == "S3":
        if us and "president" not in e:
            return {"motif": "primaire d'État américaine : us_erreur_primaires_d_etat (absence)"}
        return {"motif": "investiture présidentielle : décidée par les délégués, pas de règle sourcée voix → investiture"}
    if us and pays is None:
        if any(s in e for s in ("georgia", "louisiana")):
            return {"motif": "élection générale en Géorgie ou Louisiane : règle de second tour non inscrite"}
        t = ("presidentielle_generale" if "president" in e else "senat" if "senat" in e
             else "gouverneur" if ("governor" in e or "gubernatorial" in e) else "chambre" if ("house" in e or "district" in e) else None)
        if not t:
            return {"motif": "type d'élection américaine non reconnu"}
        p = _p("us_erreur_sondages_par_echelle")
        return {"mode": "un_tour", "sigma": p["erreur_ecart_points"][t] / p["conversion_sigma_part"], "fenetre": p["fenetre_jours"],
                "regles": ["us_erreur_sondages_par_echelle", "us_erreur_selon_temps_restant"], "type": t}
    if pays is None:
        return {"motif": "pays absent des tables de la base"}
    if "president" not in e:
        import ipu_parlements as ipu
        if ipu.suspendu(pays):
            return {"motif": "parlement suspendu (IPU) : règle d'inertie des régimes fermés, pas une course"}
        if ipu.elue_directement(pays) is False:
            return {"motif": "chambre non élue au suffrage direct (IPU) : les sondages ne s'appliquent pas"}
        sy = ipu.systeme(pays)
        if not sy:
            return {"motif": "élection législative : système électoral absent du relevé IPU"}
        titre = f.get("titre", "").lower()
        if "seats" in titre or "largest party" in titre:
            if not any(k in sy for k in ("List PR", "MMP")):
                return {"motif": f"sièges ({sy}) : voix → sièges mesuré seulement à la proportionnelle"}
            if f["evenement"] != "rang" or f["rang"] != 1:
                return {"motif": "sièges, rang autre que premier : pas de règle mesurée"}
            vs = _p("voix_vers_sieges")
            j = _p("sondages_erreur_comparee")
            return {"mode": "sieges", "sigma": j["erreur_part_points"]["proportionnelle"] / j["conversion_sigma"], "fenetre": 7,
                    "pays": pays, "accord": vs["accord_premier"]["List PR" if "List PR" in sy else "MMP"],
                    "regles": ["parlements_mode_de_scrutin", "voix_vers_sieges", "sondages_erreur_comparee",
                               "us_erreur_selon_temps_restant"], "type": "sieges_proportionnelle"}
        if not (f["evenement"] == "rang" and "votes" in titre):
            return {"motif": f"élection législative ({sy}) : seule la question « le plus de voix » relève d'une course"}
        famille = ("proportionnelle" if any(k in sy for k in ("List PR", "MMP", "STV"))
                   else "uninominal" if any(k in sy for k in ("FPTP", "TRS", "AV", "BV")) else None)
        if not famille:
            return {"motif": f"élection législative ({sy}) : système hors des familles de sondages_erreur_comparee"}
        j = _p("sondages_erreur_comparee")
        return {"mode": "un_tour", "sigma": j["erreur_part_points"][famille] / j["conversion_sigma"], "fenetre": 7, "pays": pays,
                "regles": ["parlements_mode_de_scrutin", "sondages_erreur_comparee", "us_erreur_selon_temps_restant"],
                "type": f"legislative_{famille}"}
    m = _p("presidentielles_mode_de_scrutin")
    mode = "deux_tours" if pays in m["deux_tours"] else "un_tour" if pays in m["un_tour"] else None
    if mode is None:
        return {"motif": "mode de scrutin présidentiel non inscrit (vote supplémentaire ou autre)"}
    j = _p("sondages_erreur_comparee")
    r = {"mode": mode, "sigma": j["erreur_part_points"]["presidentielles"] / j["conversion_sigma"], "fenetre": 7, "pays": pays,
         "regles": ["presidentielles_mode_de_scrutin", "sondages_erreur_comparee", "us_erreur_selon_temps_restant"]}
    if mode == "deux_tours":
        st = _p("second_tour_retournement")
        reg = REGION.get(pays)
        reg = reg if reg and st["seconds_tours_estimes"].get(reg, 0) >= st["minimum_cas"] else "monde"
        r.update(retournement=st["retournement"][reg], region=reg)
        r["regles"].append("second_tour_retournement")
    return r


def probabilite(parts: dict, f: dict, r: dict, jours: int) -> float:
    noms = [k for k in parts if k != "__sujet__"]
    mu = np.array([parts[k] for k in noms], dtype=float)
    i = noms.index(parts["__sujet__"])
    w = r["fenetre"]
    sigma = r["sigma"] * multiplicateur(max(jours, w)) / multiplicateur(w)
    g = np.random.default_rng(bs.GRAINE)
    x = np.clip(mu + g.normal(0, sigma, size=(bs.TIRAGES, len(mu))), 0.01, None)
    x = 100 * x / x.sum(axis=1, keepdims=True)
    rang = (x > x[:, [i]]).sum(axis=1) + 1
    if f["evenement"] == "rang":
        p = (rang == f["rang"]).mean()
    elif f["evenement"] == "qualifie":
        p = (rang <= 2).mean()
    elif r["mode"] == "sieges":
        # voix_vers_sieges : le premier en voix est premier en sièges avec le taux mesuré, selon l'écart des deux premiers
        top = np.sort(x, axis=1)
        ecart = top[:, -1] - top[:, -2]
        a = np.where(ecart < 3, r["accord"]["moins_3"], r["accord"]["plus_3"])
        p = np.where(rang == 1, a, np.where(rang == 2, 1 - a, 0.0)).mean()
    elif r["mode"] == "deux_tours":
        c = r["retournement"]
        p = np.where(x[:, i] > 50, 1.0, np.where(rang == 1, 1 - c, np.where(rang == 2, c, 0.0))).mean()
    else:
        p = (rang == 1).mean()
    return min(0.98, max(0.02, float(p)))


def calculer(lire_issues: bool) -> list[dict]:
    arch = bs.lire_archives()
    lignes = []
    for x in bs.questions():
        f, p, motif, r = x["forme"], None, None, {}
        if not f:
            motif = "hors brique (forme)"
        else:
            f = {**f, "titre": x["titre"]}
            r = rattacher(f)
            motif = r.get("motif")
            if not motif:
                a = arch.get((f["election"], x["jeu"]))
                if not a or not a.get("tableaux"):
                    motif = "pas d'archive ou de tableau"
                else:
                    tabs = [{"colonnes": t["colonnes"], "lignes": [(date.fromisoformat(d), v) for d, v in t["lignes"]]}
                            for t in a["tableaux"]]
                    parts = bs.moyenne_sondages(tabs, date.fromisoformat(x["jeu"]), f["sujet"])
                    if not parts:
                        motif = "aucun sondage du sujet dans les 30 jours"
                    else:
                        fin = a.get("date_scrutin") or x.get("resolue_le") or x["jeu"]
                        p = probabilite(parts, f, r, (date.fromisoformat(fin[:10]) - date.fromisoformat(x["jeu"])).days)
        l = {"id": f'{x["source"]}:{x["id"]}', "jeu": x["jeu"], "titre": x["titre"], "p_C": p, "abstention": motif,
             "regles": r.get("regles"), "mode": r.get("mode")}
        if lire_issues:
            l.update(issue=x["issue"], p_S=x["p_S"])
        lignes.append(l)
    return lignes


def couverture() -> int:
    ls = calculer(lire_issues=False)
    r = {"questions_electorales": len(ls), "jugees": sum(l["p_C"] is not None for l in ls),
         "abstentions": dict(Counter(l["abstention"] for l in ls if l["abstention"]).most_common()),
         "note": "aucune issue lue"}
    print(json.dumps(r, ensure_ascii=False, indent=1))
    return 0


def evaluer() -> int:
    import banc_jugement as bj
    import essais as es
    cb = bj.cb
    ls = calculer(lire_issues=True)
    anc = {l["id"]: l for l in map(json.loads, (Path("registre") / "scrutins" / "detail.jsonl").read_text(encoding="utf-8").splitlines())
           if l.strip()} if (Path("registre") / "scrutins" / "detail.jsonl").exists() else {}
    jug = [l for l in ls if l["p_C"] is not None]
    pm = lambda s, k: round(sum(cb.pl(l[k], l["issue"]) for l in s) / len(s), 4) if s else None
    ec = [(l["id"], cb.pl(l["p_C"], l["issue"]) - cb.pl(l["p_S"], l["issue"])) for l in jug]
    bas = haut = None
    if len(ec) >= 30:
        bas, haut = cb.bootstrap(ec, es.risque_corrige(1))
    communs = [l for l in jug if (anc.get(l["id"]) or {}).get("p_E") is not None]
    for l in communs:
        l["p_E"] = anc[l["id"]]["p_E"]
    r = {"questions_electorales": len(ls), "jugees": len(jug),
         "abstentions": dict(Counter(l["abstention"] for l in ls if l["abstention"]).most_common()),
         "perte": {"semblables": pm(jug, "p_S"), "coutumiere": pm(jug, "p_C")},
         "intervalle_corrige": [round(bas, 4), round(haut, 4)] if bas is not None else None,
         "verdict": ("la brique coutumière aide" if haut is not None and haut < 0 else "la brique coutumière nuit"
                     if bas is not None and bas > 0 else "non tranché" if bas is not None else "insuffisant (moins de 30 questions jugées)"),
         "contre_ancienne_brique": {"n": len(communs), "ancienne": pm(communs, "p_E"), "coutumiere": pm(communs, "p_C")},
         "par_mode": {m: {"n": len(v), "semblables": pm(v, "p_S"), "coutumiere": pm(v, "p_C")}
                      for m in ("un_tour", "deux_tours") for v in [[l for l in jug if l["mode"] == m]] if v},
         "empreinte_sha256": hashlib.sha256(json.dumps([(l["id"], l["jeu"], l["p_C"]) for l in ls], sort_keys=True).encode()).hexdigest(),
         "note": "perte log, plus bas = mieux ; toutes les années ; aucune donnée lue hors des archives ; ombre"}
    SORTIE.write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
    DETAIL.write_text("\n".join(json.dumps(l, ensure_ascii=False) for l in ls) + "\n", encoding="utf-8")
    print(json.dumps(r, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("--couverture", action="store_true")
    sys.exit(couverture() if a.parse_args().couverture else evaluer())
