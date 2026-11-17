"""Observatoire inductif des indicateurs (0.10.134, décision d'auteur du 2026-11-15 : « réfléchir par induction plutôt
que par déduction »). AUCUN modèle de langue, aucun paramètre appris, rien de posté.

Chaque jeu ForecastBench est un lot indépendant. Pour chaque indicateur × famille d'événements × état de l'indicateur
(au-dessus / au-dessous de la normale, durci / inchangé…), on compare dans chaque lot les OUI observés aux OUI
attendus sous B corrigé. Une régularité n'est signalée comme CANDIDATE que si l'écart garde le même sens dans au moins
3 lots sur 4, sur au moins 4 lots et 20 questions (même règle que le garde-fou sur B). Une candidate n'est pas un
résultat : elle se pré-enregistre (sens fixé) et se juge sur les jeux suivants.

    python induction.py          (registre/banc-indicateurs-frais.jsonl, + registre/indicateurs-niche.jsonl)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

FICHIER = Path("registre") / "banc-indicateurs-frais.jsonl"
ETATS = {
    "pluie": (("au-dessus de la normale", lambda v: v > 0.5), ("au-dessous de la normale", lambda v: v < -0.5)),
    "fcdo": (("durci", lambda v: v > 0), ("inchangé", lambda v: v == 0)),
    "ioda": (("coupures", lambda v: v > 0), ("aucune coupure", lambda v: v == 0)),
    "wiki": (("attention en hausse", lambda v: v > 0.2), ("attention en baisse", lambda v: v < -0.2)),
    # 0.10.138 : indicateurs de niche (indicateurs_niche.py)
    "wikimodif": (("modifications politiques en hausse", lambda v: v > 0.3), ("modifications politiques en baisse", lambda v: v < -0.3)),
    "prix_alim": (("prix alimentaires en hausse (> 10 % sur un an)", lambda v: v > 0.10),
                  ("prix alimentaires stables ou en baisse", lambda v: v <= 0.02)),
    "vols": (("vols en baisse (> 20 %)", lambda v: v < -0.22), ("vols stables ou en hausse", lambda v: v > -0.05)),
    "telegram": (("Telegram s'emballe (× 1,5)", lambda v: v > 0.4), ("Telegram se tait (÷ 1,5)", lambda v: v < -0.4)),
    "acaps": (("ACAPS a émis un risque nouveau sur le pays (6 mois)", lambda v: v >= 1),
              ("aucun risque ACAPS nouveau (6 mois)", lambda v: v == 0)),
    "voisins": (("les voisins s'embrasent (manifestations × 1,5)", lambda v: v > 0.4),
                ("les voisins se calment (manifestations ÷ 1,5)", lambda v: v < -0.4)),
    "voisins_emeutes": (("émeutes en hausse chez les voisins (× 1,5)", lambda v: v > 0.4),),
    "gdelt": (("GDELT : plus de manifestations dans la presse (× 1,5)", lambda v: v > 0.4),
              ("GDELT : moins de manifestations dans la presse (÷ 1,5)", lambda v: v < -0.4)),
    "gdelt_emeutes": (("GDELT : plus d'émeutes dans la presse (× 1,5)", lambda v: v > 0.4),
                      ("GDELT : moins d'émeutes dans la presse (÷ 1,5)", lambda v: v < -0.4)),
    "avions_etat": (("visite d'avions d'État de régimes autoritaires", lambda v: v >= 1),
                    ("aucune visite d'avion d'État", lambda v: v == 0)),
    "elections": (("élection nationale dans les 30 jours avant", lambda v: v >= 1),
                  ("aucune élection nationale dans les 30 jours avant", lambda v: v == 0)),
    "elections_apres": (("élection nationale prévue dans les 30 jours après (fuite possible)", lambda v: v >= 1),),
    "sanctions": (("sanctions nouvelles (États-Unis ou Royaume-Uni)", lambda v: v >= 1),
                  ("aucune sanction nouvelle", lambda v: v == 0)),
    "radar": (("Cloudflare signale une coupure d'internet", lambda v: v >= 1),
              ("Cloudflare ne signale aucune coupure", lambda v: v == 0)),
    "radar_etat": (("coupure décidée par l'État ou militaire (Cloudflare)", lambda v: v >= 1),),
    "radar_electricite": (("panne électrique signalée (Cloudflare)", lambda v: v >= 1),),
    "portwatch": (("PortWatch : le trafic du détroit chute (÷ 1,25)", lambda v: v < -0.22),
                  ("PortWatch : le trafic du détroit monte (× 1,25)", lambda v: v > 0.22)),
    "ooni": (("OONI : la censure web monte (+5 points)", lambda v: v > 0.05),
             ("OONI : la censure web baisse (−5 points)", lambda v: v < -0.05)),
    "ooni_messageries": (("OONI : les messageries sont plus bloquées (+10 points)", lambda v: v > 0.10),
                         ("OONI : les messageries sont moins bloquées (−10 points)", lambda v: v < -0.10)),
    "violationswatch": (("Violations Watch signale un incident grave", lambda v: v >= 1),
                        ("Violations Watch ne signale rien de grave", lambda v: v == 0)),
    "rss_presse": (("la presse en parle de plus en plus (× 1,5)", lambda v: v > 0.4), ("la presse se tait (÷ 1,5)", lambda v: v < -0.4)),
    "rss_officiel": (("sources officielles actives (≥ 3 articles)", lambda v: v >= 3), ("sources officielles muettes", lambda v: v == 0)),
    "rss_parlement_ue": (("le Parlement européen s'en saisit", lambda v: v >= 1), ("le Parlement européen n'en parle pas", lambda v: v == 0)),
    "rss_renseignement": (("les lettres de renseignement en parlent", lambda v: v >= 1), ("les lettres de renseignement n'en parlent pas", lambda v: v == 0)),
    "rss_sante": (("l'OMS ou l'ECDC en parlent", lambda v: v >= 1), ("ni l'OMS ni l'ECDC n'en parlent", lambda v: v == 0)),
    "rss_voix_citoyennes": (("Global Voices en parle", lambda v: v >= 1), ("Global Voices n'en parle pas", lambda v: v == 0)),
    "rss_economie": (("la presse économique en parle", lambda v: v >= 1), ("la presse économique n'en parle pas", lambda v: v == 0)),
    "rss_notation": (("une agence de notation est citée", lambda v: v >= 1), ("aucune agence de notation citée", lambda v: v == 0)),
    "recit_russe": (("les sources russes parlent de plus en plus du pays (× 1,5)", lambda v: v > 0.4),
                    ("les sources russes en parlent moins (÷ 1,5)", lambda v: v < -0.4)),          # 0.10.202, M12
    "alignement_rival": (("le pays coopère militairement avec le rival d'une puissance proche (≥ 2 événements GDELT en 14 jours)", lambda v: v >= 2),
                         ("aucune coopération militaire avec un rival d'une puissance proche", lambda v: v == 0)),  # 0.10.222, M17
    "contremesures_chine": (("la Chine a visé le pays par une contre-mesure (≥ 3 événements GDELT en 90 jours)", lambda v: v >= 3),
                            ("aucune contre-mesure chinoise contre le pays", lambda v: v == 0)),       # 0.10.205
    "avis_navigation": (("zone de tir ou d'exercice chinoise annoncée près du pays (14 jours)", lambda v: v >= 1),
                        ("aucun avertissement militaire chinois près du pays", lambda v: v == 0)),     # 0.10.206
    "force_chinoise": (("démonstration de force chinoise visant le pays (≥ 1 événement GDELT en 14 jours)", lambda v: v >= 1),
                       ("aucune démonstration de force chinoise visant le pays", lambda v: v == 0)),  # 0.10.224
    "feux": (("les feux montent dans le pays (× 1,5)", lambda v: v > 0.4),
             ("les feux reculent (÷ 1,5)", lambda v: v < -0.4)),                                      # 0.10.208
    "silence_statistique": (("une publication statistique chinoise prévue manque ou tarde (30 jours)", lambda v: v >= 1),
                            ("toutes les publications chinoises prévues ont paru à temps", lambda v: v == 0)),  # M15
    "prix_alimentaires": (("inflation alimentaire forte (≥ 20 % sur un an)", lambda v: v >= 20),
                          ("inflation alimentaire faible (< 5 % sur un an)", lambda v: v < 5)),          # 0.10.214
    "dates_memoire": (("une date de mémoire tombe dans les 14 jours", lambda v: v >= 1),
                      ("aucune date de mémoire dans les 14 jours", lambda v: v == 0)),                # 0.10.202, M14
    "rss_cyber": (("le CERT-FR nomme le pays", lambda v: v >= 1), ("le CERT-FR ne nomme pas le pays", lambda v: v == 0)),
    "rss_verification": (("désinformation vérifiée sur le pays (≥ 3 vérifications Correctiv)", lambda v: v >= 3),
                         ("aucune vérification Correctiv sur le pays", lambda v: v == 0)),
    "rss_enquete": (("enquête Correctiv sur le pays", lambda v: v >= 1), ("aucune enquête Correctiv sur le pays", lambda v: v == 0)),
    "rss_presse_large": (("la presse en parle de plus en plus, adjectifs compris (× 1,5)", lambda v: v > 0.4),
                         ("la presse se tait, adjectifs compris (÷ 1,5)", lambda v: v < -0.4)),
    "brouillage_gps": (("brouillage GPS présent (≥ 5 % des zones)", lambda v: v >= 0.05), ("aucun brouillage GPS", lambda v: v == 0)),
}
NICHE = Path("registre") / "indicateurs-niche.jsonl"


def joindre_niche(lignes: list[dict]) -> list[dict]:
    """Ajoute aux lignes les indicateurs de niche mesurés pour le même pays et le même jeu."""
    if not NICHE.exists():
        return lignes
    n = {}
    for l in NICHE.read_text(encoding="utf-8").splitlines():
        if l.strip():
            x = json.loads(l)
            ancien = n.get((x["pays"], x["jeu"]), {})
            # lignes complémentaires fusionnées ; une mesure réussie n'est jamais écrasée par un échec plus récent
            n[(x["pays"], x["jeu"])] = {**ancien, **{k: v for k, v in x.items()
                                                     if not (isinstance(v, dict) and not v.get("present")
                                                             and (ancien.get(k) or {}).get("present"))}}
    out = []
    for x in lignes:
        m = n.get((x.get("pays"), x.get("jeu")))
        if m:
            x = dict(x, presents=dict(x.get("presents") or {}))
            for k in ("wikimodif", "prix_alim", "vols", "telegram", "violationswatch", "rss_presse", "rss_officiel", "brouillage_gps", "gdelt", "ooni", "portwatch", "radar", "sanctions", "elections", "avions_etat", "voisins", "acaps", "recit_russe", "dates_memoire", "contremesures_chine", "avis_navigation", "force_chinoise", "feux", "silence_statistique", "prix_alimentaires", "alignement_rival"):
                v = m.get(k) or {}
                if k == "vols" and v.get("arrivees_2j") == 0 and v.get("arrivees_2j_quatre_semaines_avant") == 0:
                    continue                          # 0.10.145 : couverture OpenSky absente, pas une mesure
                if k == "telegram" and v.get("methode") != "canaux":
                    continue                          # 0.10.151 : recherche globale abandonnée (ne remonte pas dans le passé)
                if k == "elections" and v.get("present"):   # 0.10.179
                    x["elections_apres"] = float(v.get("apres_30j") or 0)
                    x["presents"]["elections_apres"] = True
                if k == "radar" and v.get("present"):   # 0.10.177
                    for cle, etat in (("etat_14j", "radar_etat"), ("electricite_14j", "radar_electricite")):
                        x[etat] = float(v.get(cle) or 0)
                        x["presents"][etat] = True
                if k == "ooni" and v.get("present") and v.get("valeur_messageries") is not None:   # 0.10.175
                    x["ooni_messageries"] = float(v["valeur_messageries"])
                    x["presents"]["ooni_messageries"] = True
                if v.get("present") and v.get("valeur") is not None:
                    x[k] = m[k]["valeur"]
                    x["presents"][k] = True
                    if k == "voisins" and v.get("valeur_emeutes") is not None:   # 0.10.186
                        x["voisins_emeutes"] = float(v["valeur_emeutes"])
                        x["presents"]["voisins_emeutes"] = True
                    if k == "gdelt" and v.get("valeur_emeutes") is not None:   # 0.10.173
                        x["gdelt_emeutes"] = float(v["valeur_emeutes"])
                        x["presents"]["gdelt_emeutes"] = True
                    if k == "rss_officiel" and v.get("parlement_ue_14j") is not None:   # 0.10.155
                        x["rss_parlement_ue"] = float(v["parlement_ue_14j"])
                        x["presents"]["rss_parlement_ue"] = True
                    if k == "rss_officiel" and v.get("renseignement_14j") is not None:  # 0.10.156
                        x["rss_renseignement"] = float(v["renseignement_14j"])
                        x["presents"]["rss_renseignement"] = True
                    if k == "rss_officiel" and v.get("sante_14j") is not None:  # 0.10.157
                        x["rss_sante"] = float(v["sante_14j"])
                        x["presents"]["rss_sante"] = True
                    if k == "rss_officiel" and v.get("voix_citoyennes_14j") is not None:  # 0.10.158
                        x["rss_voix_citoyennes"] = float(v["voix_citoyennes_14j"])
                        x["presents"]["rss_voix_citoyennes"] = True
                    if k == "rss_presse" and v.get("valeur_large") is not None:  # 0.10.199
                        x["rss_presse_large"] = float(v["valeur_large"])
                        x["presents"]["rss_presse_large"] = True
                    for cle, etat in (("economie_14j", "rss_economie"), ("notation_14j", "rss_notation"), ("cyber_14j", "rss_cyber"),
                                      ("verification_14j", "rss_verification"), ("enquete_14j", "rss_enquete")):  # 0.10.159
                        if k == "rss_officiel" and v.get(cle) is not None:
                            x[etat] = float(v[cle])
                            x["presents"][etat] = True
        out.append(x)
    return out
LOTS_MIN, N_MIN, MEME_SENS = 4, 20, 0.75


def observer(lignes: list[dict]) -> dict:
    cases = {}
    for x in lignes:
        if x.get("issue") not in (0, 1) or x.get("p_B") is None:
            continue
        for k, etats in ETATS.items():
            if not (x.get("presents") or {}).get(k):
                continue
            for nom, test in etats:
                if test(float(x[k])):
                    c = cases.setdefault((k, x.get("famille", "?"), nom), {})
                    lot = c.setdefault(x["jeu"], [0, 0, 0.0])
                    lot[0] += 1
                    lot[1] += x["issue"]
                    lot[2] += float(x["p_B"])
    out, candidates = {}, []
    for (k, fam, nom), lots in sorted(cases.items()):
        n = sum(v[0] for v in lots.values())
        oui = sum(v[1] for v in lots.values())
        att = sum(v[2] for v in lots.values())
        signe = 1 if oui >= att else -1
        meme = sum(1 for v in lots.values() if (v[1] - v[2]) * signe > 0) / len(lots)
        cle = f"{k} {nom} → {fam}"
        out[cle] = {"lots": len(lots), "n": n, "oui": oui, "attendus_B": round(att, 1),
                    "sens": "plus que B" if signe > 0 else "moins que B", "meme_sens": round(meme, 2)}
        if len(lots) >= LOTS_MIN and n >= N_MIN and meme >= MEME_SENS:
            candidates.append(f"{cle} : {oui} oui pour {att:.1f} attendus ({out[cle]['sens']}), même sens dans "
                              f"{meme:.0%} de {len(lots)} lots, {n} questions")
    return {"regle": f"même sens dans ≥ {MEME_SENS:.0%} des lots, ≥ {LOTS_MIN} lots, ≥ {N_MIN} questions",
            "candidates": candidates, "cases": out}


def principal() -> int:
    if not FICHIER.exists():
        print("Aucun registre.")
        return 0
    r = observer(joindre_niche([json.loads(l) for l in FICHIER.read_text(encoding="utf-8").splitlines() if l.strip()]))
    print(f"Observatoire inductif ({r['regle']}) :")
    for c in r["candidates"] or ["aucune régularité répétée"]:
        print(" • " + c)
    print("\nToutes les cases :")
    for k, v in r["cases"].items():
        print(f"  {k:55s} {v['n']:3d} q, {v['oui']:2d} oui / {v['attendus_B']:5.1f} attendus, {v['sens']:12s}, "
              f"même sens {v['meme_sens']:.0%} de {v['lots']} lots")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
