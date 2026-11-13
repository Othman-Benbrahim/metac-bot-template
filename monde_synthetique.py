"""Monde synthétique : mesurer le lecteur contre une vérité connue (bot 0.10.14 ; skill §43, d'après LLMMatrix,
J. Prokopets 2026).

Pour chaque situation :
  1. le skill tire un ensemble de cartes présentes selon la loi a priori de son programme génératif
     (`moteur.tirer_situation`, tirage exact, graine fixée) : c'est la vérité ;
  2. un modèle-narrateur écrit quelques dépêches FICTIVES (pays, acteurs et sites inventés) qui montrent les cartes
     présentes par des faits observables, SANS les nommer, et n'évoquent pas les cartes absentes de la liste ;
  3. le lecteur ordinaire (même consigne que pour une vraie question : `consigne_dossier`) lit ces dépêches sur des
     candidates qui mêlent cartes présentes et absentes ;
  4. on compte : carte présente ancrée en F ou en f (sensibilités), carte absente ancrée (faux positifs), et on les
     compare aux paramètres stipulés du lecteur dans le programme génératif (sens_F, sens_f, fp_F, fp_f).

Sans contamination par construction : la situation n'existe nulle part ailleurs. Réserve : narrateur et lecteur de la
même famille donnent une borne OPTIMISTE de la sensibilité (le narrateur écrit pour être lu). Rien n'est modifié :
le résultat va dans registre/monde-synthetique-<date>.json ; les valeurs mesurées ne remplacent les paramètres stipulés
que par décision d'auteur datée.

    python monde_synthetique.py          # MONDE_SITUATIONS (12 par défaut), MONDE_STRATE (7), MONDE_NARRATEUR,
                                         # MONDE_GRAINE (par défaut : à la suite des passages précédents)
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
import random
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import alphabet_pipeline as ap


# 0.10.24 : version de la consigne du narrateur ; les passages de versions différentes ne se cumulent pas
# (1 : jusqu'à 0.10.22, fiches complètes et une dépêche par carte ; 2 : 0.10.23, marqueurs seuls, une situation ;
# 3 : 0.10.26, canevas imposé, domaine imposé, réécriture guidée par le vérificateur ;
# 4 : 0.10.28, skill 0.7.69 (marqueurs complets), deux États, contexte sans passé ni instance ;
# 5 : 0.10.31, médias imposés, moitié des faits corroborés par deux médias, plus de réécriture ;
# 6 : depuis 0.10.34, dépêches parasites dans la moitié des situations, lecture sans noms en parallèle)
PROTOCOLE_MONDE = 11  # 0.10.64 : tiers de POLARITÉ, période constatée (skill 0.7.76) ; 10 : 0.10.55 : liaisons, place des types (une strate / entre strates) ; 9 : 0.10.52 : consigne du lecteur changée en 0.10.51 (liaisons, corroboration, extraits) et 0.10.52 (averti)


def nom_strate(s: int) -> str:
    t = ap.lire_ref("references/strates.md")
    m = re.search(rf"^### {s} · (.+)$", t, re.M)
    return m.group(1).strip() if m else f"strate {s}"


def marqueurs(abr: str) -> list[str]:
    """Les « Marqueurs observables » de la fiche d'une carte (sans définition ni structure mathématique). Un marqueur
    peut tenir sur plusieurs lignes : les lignes de suite sont recollées."""
    t = ap.fiches([abr])
    i = t.find("**Marqueurs observables**")
    if i < 0:
        return []
    out: list[str] = []
    for ligne in t[i:].split("\n")[1:]:
        if not ligne.strip():
            if out:
                break
            continue
        if ligne.lstrip().startswith("- "):
            out.append(ligne.strip()[2:])
        elif out:
            out[-1] += " " + ligne.strip()
        else:
            break
    # 0.10.28 : la mention de version en fin de liste (« *(0.7.69, …)* ») ne fait pas partie du marqueur
    return [re.sub(r"\*\*", "", re.sub(r"\s*\*\(0\.\d+\.\d+[^)]*\)\*", "", x)).strip().rstrip(" ;.") for x in out]


def _bloc_marqueurs(cles: list[str]) -> str:
    m = ap._moteur()
    out = []
    for k in cles:
        a = k.split("@")[0]
        out.append(f"[{a}] " + " ; ".join(marqueurs(a)))
    return "\n".join(out)


ETATS = ["Aurinia", "Velania", "Morsanie", "Telkhoun", "Valsnie", "Draven", "Ostara", "Kessaria", "Brenthie", "Norven",
         "Calvarie", "Istrane", "Doramie", "Félisie", "Granvie", "Lusarne"]
ORGANISATIONS = ["l'Union du Détroit de Kossmar", "le Conseil des États riverains du Reth",
                 "l'Organisation pour la sécurité du Plateau de Senne", "la Ligue commerciale d'Ostrave",
                 "le Pacte de défense de Corvus", "l'Agence régionale de l'énergie de Velhaven"]
DOMAINE = {7: "relations entre États et organisations internationales : diplomatie, traités, sanctions, alliances, "
              "frontières, forces armées, commerce d'État. Rien d'autre (ni météo, ni faits divers, ni cérémonies).",
           # 0.10.67 : domaines des « accords » des triplets durs (mêmes cartes, autre strate, autre vocabulaire)
           13: "vie politique intérieure d'un seul État : gouvernement, partis, parlement, élections, syndicats, "
               "manifestations, justice. Rien d'autre (ni relations avec l'étranger, ni météo, ni faits divers).",
           6: "économie d'un seul pays : entreprises, banques, marchés, prix, salaires, budget de l'État, commerce. "
              "Rien d'autre (ni diplomatie, ni armée, ni faits divers)."}

# 0.10.67 : les acteurs imposés selon la strate (en 7, deux États et, au besoin, une organisation)
ACTEURS_STRATE = {13: "le gouvernement de {a}, deux partis politiques de {a} aux noms inventés, son parlement, ses "
                      "syndicats et ses électeurs",
                  6: "deux grandes entreprises de {a} aux noms inventés, sa banque centrale, son ministère des finances, "
                     "ses syndicats et ses consommateurs"}


MEDIAS = ["agence-meridia", "courrier-du-reth", "observateur-ostrave", "gazette-de-corvus", "depeche-continentale",
          "journal-de-velhaven", "le-veilleur-du-nord", "tribune-de-kossmar", "presse-libre-de-senne", "echo-des-capitales"]


def canevas(presentes: list[str], strate: int, graine: int, aujourdhui: str) -> dict:
    """0.10.26 : le CANEVAS imposé au narrateur (décision d'auteur du 2026-11-11 : contraindre plus le narrateur, plutôt
    que changer de modèle). Acteurs, dates et, pour chaque carte présente, UN marqueur précis à remplir, tirés de la
    graine. 0.10.28 : DEUX États seulement ; l'organisation n'entre que si RÉSEAU ou COMMUNAUTÉ doivent être montrés.
    0.10.31 : chaque dépêche a son MÉDIA imposé ; pour la moitié des cartes présentes (tirage), le fait est rapporté par
    DEUX médias distincts à deux dates (« corroboré ») : l'ancrage F, qui exige deux sources indépendantes, devient
    possible, et sa sensibilité mesurable."""
    import random
    rnd = random.Random(f"canevas:{strate}:{graine}")
    a, b = rnd.sample(ETATS, 2)
    org = rnd.choice(ORGANISATIONS)
    avec_org = any(k.split("@")[0] in ("RES", "COM") for k in presentes)
    ordre = list(presentes)
    rnd.shuffle(ordre)
    corrobores = sorted(k for k in ordre if rnd.random() < 0.5)
    n = 1 + len(ordre) + len(corrobores)
    fin = date.fromisoformat(aujourdhui)
    dates = sorted({(fin - timedelta(days=rnd.randrange(1, 61))).isoformat() for _ in range(n * 3)})[:n]
    while len(dates) < n:
        dates.append(fin.isoformat())
    dates.sort()
    medias = rnd.sample(MEDIAS, min(len(MEDIAS), n)) + [MEDIAS[i % len(MEDIAS)] for i in range(max(0, n - len(MEDIAS)))]
    items = [{"date": dates[0], "carte": None, "marqueur": None, "media": medias[0], "reprise": False}]
    k_ = 1
    for c in ordre:
        mq = marqueurs(c.split("@")[0])
        marq = rnd.choice(mq) if mq else None
        items.append({"date": dates[k_], "carte": c, "marqueur": marq, "media": medias[k_], "reprise": False})
        k_ += 1
        if c in corrobores:
            items.append({"date": dates[k_], "carte": c, "marqueur": marq, "media": medias[k_], "reprise": True})
            k_ += 1
    # 0.10.34 (Lv et al., ICML 2026 : « information noyée ») : dans la moitié des situations, deux dépêches PARASITES,
    # sans rapport avec la situation, dans un troisième pays ; la vérité ne change pas
    parasites = 2 if rnd.random() < 0.5 else 0
    tiers = rnd.choice([e for e in ETATS if e not in (a, b)])
    for _ in range(parasites):
        items.append({"date": (fin - timedelta(days=rnd.randrange(1, 61))).isoformat(), "carte": None, "marqueur": None,
                      "media": rnd.choice(MEDIAS), "reprise": False, "parasite": True})
    items = [items[0]] + sorted(items[1:], key=lambda x: x["date"])
    return {"etats": [a, b], "organisation": org if avec_org else None, "corrobores": corrobores, "depeches": items,
            "parasites": parasites, "pays_tiers": tiers}


def consigne_narrateur(presentes: list[str], absentes: list[str], strate: int, aujourdhui: str, graine: int = 0,
                       leurre: str | None = None) -> str:
    """0.10.26 : consigne à CANEVAS. Le narrateur écrit exactement les dépêches du canevas, dans l'ordre : la première
    pose le contexte sans aucun marqueur ; chacune des suivantes remplit UN marqueur imposé, et aucun autre de la liste
    interdite. Domaine imposé. Plus de choix libres : c'est la liberté laissée au modèle qui le faisait errer."""
    cv = canevas(presentes, strate, graine, aujourdhui)
    a, b = cv["etats"]
    acteurs = f"{a}, {b}" + (f" et {cv['organisation']}" if cv["organisation"] else "")
    if strate in ACTEURS_STRATE:
        acteurs = ACTEURS_STRATE[strate].format(a=a)
    lignes = []
    for i, d in enumerate(cv["depeches"], 1):
        if d.get("parasite"):
            lignes.append(f"{i}. [{d['date']}] (média : {d['media']}) Un fait SANS RAPPORT avec la situation : sport, "
                          f"culture, météo ou fait divers en {cv['pays_tiers']} ; aucun des acteurs imposés, aucun des "
                          "marqueurs ci-dessous.")
        elif d["carte"] is None:
            lignes.append(f"{i}. [{d['date']}] (média : {d['media']}) CONTEXTE : présente {acteurs} et leurs dirigeants actuels, par des faits "
                          "neutres du moment ; AUCUNE référence au passé (ni traité ancien, ni date antérieure à la "
                          "période), AUCUNE instance qui préside ou valide, aucun des marqueurs ci-dessous.")
        elif d["reprise"]:
            lignes.append(f"{i}. [{d['date']}] (média : {d['media']}) Le MÊME fait que la dépêche sur « {d['marqueur']} », "
                          "rapporté indépendamment par ce second média, avec un détail vérifiable différent (un chiffre, "
                          "une déclaration citée) ; pas de reprise mot pour mot.")
        elif d["carte"] == leurre:
            # 0.10.67 (triplets durs) : le LEURRE garde les mots du marqueur mais ne le remplit pas
            lignes.append(f"{i}. [{d['date']}] (média : {d['media']}) Un fait, entre ces mêmes acteurs, qui EMPLOIE le "
                          f"vocabulaire de ce marqueur SANS le remplir : « {d['marqueur']} ». La chose est évoquée, "
                          "annoncée, approchée, envisagée ou démentie, mais elle N'A PAS LIEU dans les faits rapportés. "
                          "Exemple de la différence : « le ministre annonce qu'un plafond de 2 % POURRAIT être fixé "
                          "l'an prochain » ou « le taux s'approche du seuil sans l'atteindre » (le marqueur n'est PAS "
                          "rempli) ; contre « le taux franchit le seuil de 2 % le 3 mars » (le marqueur EST rempli, "
                          "interdit ici). Aucun chiffre, aucune date ni aucun acte ne doit montrer la chose accomplie.")
        else:
            lignes.append(f"{i}. [{d['date']}] (média : {d['media']}) Un fait, entre ces mêmes acteurs, qui remplit "
                          f"EXACTEMENT ce marqueur : « {d['marqueur']} ».")
    return f"""Tu écris des dépêches de presse FICTIVES pour un exercice de mesure.

DOMAINE IMPOSÉ : {DOMAINE.get(strate, nom_strate(strate))}
ACTEURS IMPOSÉS, les seuls : {acteurs}, et leurs gouvernements, ministres, armées, diplomates.
Une seule situation qui évolue d'une dépêche à l'autre.

ÉCRIS EXACTEMENT {len(cv['depeches'])} DÉPÊCHES, dans cet ordre, aux dates indiquées :
{chr(10).join(lignes)}

AUCUN fait, dans AUCUNE dépêche, ne doit remplir les marqueurs suivants (ni explicitement, ni par un détail) :
{_bloc_marqueurs(absentes) or "(aucun)"}

Règles d'écriture :
- uniquement des faits observables : qui a fait quoi, quand, combien ; chiffres, actes, déclarations citées ;
  AUCUNE phrase qui explique, résume ou analyse (pas de « ainsi », « ce qui montre », pas de commentaire) ;
  ne nomme aucune structure ; aucun nom réel ; adresses en https://….example/… ;
- 60 à 110 mots par dépêche ; format exact, blocs séparés par une ligne vide :
[AAAA-MM-JJ] Titre — https://<média imposé>.example/chemin
Texte de la dépêche.

Rends uniquement les dépêches."""


async def verifier(verificateur, texte: str, cles: list[str], s: dict, strate: int) -> dict:
    m = ap._moteur()
    try:
        v = await ap.json_avec_reprise(verificateur, consigne_verification(texte, cles))
        oui = {f"{m.carte_id(str(k))}@{strate}" for k, x in v.items() if str(x).lower().startswith("o")}
        return {"absentes_montrees": sorted(oui & set(s["absentes"])),
                "presentes_non_montrees": sorted(set(s["presentes"]) - oui), "_cles": sorted(cles)}
    except Exception as e:
        return {"erreur": f"{type(e).__name__}: {e}"[:200]}


def consigne_verification(texte: str, cles: list[str]) -> str:
    """0.10.23 : contrôle INDÉPENDANT du texte du narrateur, par un autre modèle que le lecteur : quels groupes de
    marqueurs un fait du texte remplit-il ? Sert à séparer l'erreur du narrateur de celle du lecteur."""
    return f"""Voici des dépêches et des groupes de marqueurs observables. Pour chaque groupe, dis si AU MOINS UN fait
des dépêches remplit au moins un de ses marqueurs (oui) ou non (non). Juge sur les faits écrits, pas sur ce qu'ils
pourraient suggérer.

DÉPÊCHES :
{texte}

GROUPES :
{_bloc_marqueurs(cles)}

Réponds par un seul objet JSON : {{"ABR": "oui" | "non", ...}} avec les abréviations entre crochets."""


def fuites(texte: str) -> list[str]:
    """Noms de cartes écrits en capitales dans le texte du narrateur (il ne devait pas les nommer)."""
    m = ap._moteur()
    return sorted({n for n in m.NOMS.values() if re.search(rf"(?<![A-ZÀ-Ý]){re.escape(n)}(?![A-ZÀ-Ý])", texte)})


def situation(strate: int, graine: int, cartes: list[str]) -> dict:
    m = ap._moteur()
    presentes = m.tirer_situation(strate, graine)
    absentes_toutes = [f"{c}@{strate}" for c in cartes if f"{c}@{strate}" not in presentes]
    rng = random.Random(f"monde:{strate}:{graine}")
    rng.shuffle(absentes_toutes)
    # 0.10.21 : au moins une carte absente reste hors des candidates pour servir d'événement (le premier passage, le
    # 2026-11-11, a perdu 2 situations sur 12 à 8 cartes présentes)
    k = min(max(3, len(presentes)), len(absentes_toutes) - 1)
    absentes, reste = sorted(absentes_toutes[:k]), absentes_toutes[k:]
    evenement = reste[0] if reste else None
    return {"graine": graine, "presentes": presentes, "absentes": absentes, "evenement": evenement}


def plan_de(s: dict, strate: int) -> dict:
    cands = sorted(s["presentes"] + s["absentes"])
    ev = s["evenement"].split("@")[0]
    return {"strates": [strate], "candidats": cands, "contre_candidate": [], "semantique": "au-moins-une-fois",
            "evenement": {"carte": ev, "strate": strate, "type": "apparait"}, "recherches": []}


def table_effacement(graine: int) -> dict[str, str]:
    """0.10.34 (Lv et al., ICML 2026 : « ancrage symbolique ») : chaque carte reçoit un identifiant neutre (C01 à C16),
    tiré de la graine. Si la lecture change quand seuls les NOMS changent, le lecteur s'appuie sur le vocabulaire des
    noms et non sur les marqueurs des fiches."""
    m = ap._moteur()
    abrs = sorted(m.NOMS)
    ids = [f"C{i + 1:02d}" for i in range(len(abrs))]
    random.Random(f"effacement:{graine}").shuffle(ids)
    return dict(zip(abrs, ids))


def effacer_noms(texte: str, table: dict[str, str]) -> str:
    """Remplace dans la consigne les noms des cartes (« TRACE · MÉMOIRE », « SEUIL ») et leurs abréviations (« SEU »)
    par les identifiants neutres ; les définitions et les marqueurs restent tels quels."""
    m = ap._moteur()
    paires = [(m.NOMS[a], i) for a, i in table.items()] + [(a, i) for a, i in table.items()]
    for nom, i in sorted(paires, key=lambda x: -len(x[0])):
        texte = re.sub(rf"(?<![A-Za-zÀ-ÿ0-9_]){re.escape(nom)}(?![A-Za-zÀ-ÿ0-9_])", i, texte)
    return texte


def ancrees(lecture: dict, strate: int, inverse: dict[str, str] | None = None) -> dict[str, str]:
    m = ap._moteur()
    out = {}
    for x in (lecture or {}).get("mots") or []:
        try:
            c = str(x.get("carte"))
            c = (inverse or {}).get(c.upper(), c)
            k = f"{m.carte_id(c)}@{int(x.get('strate'))}"
        except (ValueError, TypeError):
            continue
        if k.endswith(f"@{strate}"):
            out[k] = "F" if x.get("intensite") == "F" else "f"
    return out


def mesurer(rows: list[dict]) -> dict:
    lues = [r for r in rows if r.get("statut") == "lue"]
    pres = [(k, r["ancrees"].get(k)) for r in lues for k in r["presentes"]]
    abs_ = [(k, r["ancrees"].get(k)) for r in lues for k in r["absentes"]]
    taux = lambda xs, i: round(sum(1 for _, v in xs if v == i) / len(xs), 4) if xs else None
    manquees: dict[str, int] = {}
    for r in lues:
        for k in r["presentes"]:
            if k not in r["ancrees"]:
                c = (r.get("rejets_categories") or {}).get(k) or "non_rejetee"
                manquees[c] = manquees.get(c, 0) + 1
    par_carte: dict[str, dict] = {}
    for r in lues:
        for k in r["presentes"] + r["absentes"]:
            d = par_carte.setdefault(k.split("@")[0], {"presente": 0, "lue_si_presente": 0, "absente": 0,
                                                       "lue_si_absente": 0})
            if k in r["presentes"]:
                d["presente"] += 1
                d["lue_si_presente"] += k in r["ancrees"]
            else:
                d["absente"] += 1
                d["lue_si_absente"] += k in r["ancrees"]
    g = ap._moteur().P["generatif"]
    # 0.10.23 : mesure VÉRIFIÉE : on retire les cartes où le narrateur s'est trompé, selon le contrôle indépendant
    # (présente non montrée, absente montrée) ; l'écart restant est celui du lecteur.
    ver = [r for r in lues if isinstance(r.get("verification"), dict) and "erreur" not in r["verification"]]
    pres_v = [(k, r["ancrees"].get(k)) for r in ver for k in r["presentes"]
              if k not in r["verification"]["presentes_non_montrees"]]
    abs_v = [(k, r["ancrees"].get(k)) for r in ver for k in r["absentes"]
             if k not in r["verification"]["absentes_montrees"]]
    verifiee = None
    if ver:
        # 0.10.31 : sensibilité selon que le fait est corroboré (deux médias : F possible) ou non (F impossible)
        cor = [(k, r["ancrees"].get(k)) for r in ver for k in r["presentes"]
               if k not in r["verification"]["presentes_non_montrees"] and k in (r.get("canevas") or {}).get("corrobores", [])]
        sim = [(k, r["ancrees"].get(k)) for r in ver for k in r["presentes"]
               if k not in r["verification"]["presentes_non_montrees"]
               and k not in (r.get("canevas") or {}).get("corrobores", [])]
        verifiee = {"situations": len(ver),
                    "corrobores": {"cartes": len(cor), "sens_F": taux(cor, "F"), "sens_f": taux(cor, "f"),
                                   "sens": round(sum(1 for _, v in cor if v) / len(cor), 4) if cor else None},
                    "source_unique": {"cartes": len(sim), "sens_F": taux(sim, "F"), "sens_f": taux(sim, "f"),
                                      "sens": round(sum(1 for _, v in sim if v) / len(sim), 4) if sim else None},
                    "erreurs_narrateur": {"absentes_montrees": sum(len(r["verification"]["absentes_montrees"]) for r in ver),
                                          "presentes_non_montrees": sum(len(r["verification"]["presentes_non_montrees"])
                                                                        for r in ver)},
                    "sens_F": taux(pres_v, "F"), "sens_f": taux(pres_v, "f"),
                    "sens": round(sum(1 for _, v in pres_v if v) / len(pres_v), 4) if pres_v else None,
                    "fp_F": taux(abs_v, "F"), "fp_f": taux(abs_v, "f"),
                    "fp": round(sum(1 for _, v in abs_v if v) / len(abs_v), 4) if abs_v else None}
    # 0.10.34 : perturbations (Lv et al., ICML 2026), sur les cartes vérifiées
    def _sens_fp(rs, cle=None):
        lire = (lambda r: r.get("ancrees") or {}) if cle is None else (lambda r: (r.get(cle) or {}).get("ancrees") or {})
        p_ = [(k, lire(r).get(k)) for r in rs for k in r["presentes"] if k not in r["verification"]["presentes_non_montrees"]]
        a_ = [(k, lire(r).get(k)) for r in rs for k in r["absentes"] if k not in r["verification"]["absentes_montrees"]]
        return {"situations": len(rs), "sens": round(sum(1 for _, v in p_ if v) / len(p_), 4) if p_ else None,
                "sens_F": taux(p_, "F"), "fp": round(sum(1 for _, v in a_ if v) / len(a_), 4) if a_ else None}
    perturbations = {}
    eff = [r for r in ver if isinstance((r.get("lecture_sans_noms") or {}).get("ancrees"), dict)]
    if eff:
        jac = []
        for r in eff:
            a1, a2 = set(r["ancrees"]), set(r["lecture_sans_noms"]["ancrees"])
            jac.append(len(a1 & a2) / len(a1 | a2) if a1 | a2 else 1.0)
        perturbations["effacement_des_noms"] = {
            "avec_noms": _sens_fp(eff), "sans_noms": _sens_fp(eff, "lecture_sans_noms"),
            "accord_jaccard_moyen": round(sum(jac) / len(jac), 4),
            "lecture": "lecture qui change sans les noms : le lecteur s'appuie sur le vocabulaire, pas sur les marqueurs"}
    refl = [r for r in ver if isinstance((r.get("lecture_reflechie") or {}).get("ancrees"), dict)]
    if refl:
        jac = []
        for r in refl:
            a1, a2 = set(r["ancrees"]), set(r["lecture_reflechie"]["ancrees"])
            jac.append(len(a1 & a2) / len(a1 | a2) if a1 | a2 else 1.0)
        perturbations["reflexion"] = {
            "sans_reflexion": _sens_fp(refl), "avec_reflexion": _sens_fp(refl, "lecture_reflechie"),
            "accord_jaccard_moyen": round(sum(jac) / len(jac), 4),
            "lecture": "si la réflexion baisse les faux positifs ou monte la sensibilité, une partie des erreurs vient "
                       "de la lecture en une passe, sans retour possible (Goedecke 2025)"}
    avec_p = [r for r in ver if (r.get("canevas") or {}).get("parasites")]
    sans_p = [r for r in ver if not (r.get("canevas") or {}).get("parasites")]
    if avec_p and sans_p:
        perturbations["depeches_parasites"] = {"avec": _sens_fp(avec_p), "sans": _sens_fp(sans_p)}
    if verifiee is not None:
        verifiee["perturbations"] = perturbations or None
    return {"situations": len(rows), "lues": len(lues), "mesure_verifiee": verifiee,
            "illisibles": {"narrateur": sum(r.get("statut") == "narrateur_illisible" for r in rows),
                           "lecteur": sum(r.get("statut") == "lecture_illisible" for r in rows)},
            "avec_fuite": sum(bool(r.get("fuites")) for r in rows),
            "cartes_presentes": len(pres), "cartes_absentes": len(abs_),
            "mesure": {"sens_F": taux(pres, "F"), "sens_f": taux(pres, "f"),
                       "sens": round(sum(1 for _, v in pres if v) / len(pres), 4) if pres else None,
                       "fp_F": taux(abs_, "F"), "fp_f": taux(abs_, "f"),
                       "fp": round(sum(1 for _, v in abs_ if v) / len(abs_), 4) if abs_ else None},
            "stipule": {k: g.get(k) for k in ("sens_F", "sens_f", "fp_F", "fp_f")},
            "presentes_manquees_par_categorie": manquees,
            "etats_nuls_justes": sum(1 for r in lues if not r["presentes"] and not r["ancrees"]),
            "situations_vides": sum(1 for r in lues if not r["presentes"]),
            "par_carte": dict(sorted(par_carte.items()))}


BUDGET_REFLEXION = 4000


def options_reflexion(modele: str) -> dict:
    """0.10.36 : la réflexion étendue du lecteur (Goedecke 2025 : sans retour possible, la tâche est un calcul, pas un
    raisonnement). Claude : `thinking` (température 1 imposée, max_tokens au-dessus du budget) ; autres familles :
    `reasoning_effort` de litellm."""
    nom = str(modele or "").lower()
    if "claude" in nom or "anthropic" in nom:
        return {"thinking": {"type": "enabled", "budget_tokens": BUDGET_REFLEXION}, "temperature": 1,
                "max_tokens": BUDGET_REFLEXION + 8000}
    return {"reasoning_effort": "medium"}


def situations_codables(passages: list[dict], protocole: int | None = None) -> list[dict]:
    """Situations lues, vérifiées sans erreur, du protocole le plus récent présent (ou celui demandé)."""
    protos = [d.get("protocole_monde") for d in passages if d.get("protocole_monde")]
    protocole = protocole or (max(protos) if protos else None)
    out = []
    for d in passages:
        if d.get("protocole_monde") != protocole:
            continue
        for r in d.get("situations") or []:
            v = r.get("verification")
            if r.get("statut") == "lue" and isinstance(v, dict) and "erreur" not in v and r.get("texte"):
                out.append(dict(r, _passage=d.get("calcule_le"), _strate=d.get("strate")))
    return out


def exporter_humain(passages: list[dict], dossier: Path, n: int = 20, graine: int = 0,
                    protocole: int | None = None) -> dict:
    """0.10.36 : référence humaine (Goedecke 2025 : sans comparaison humaine, on ne sait pas si 0,66 est mauvais).
    Écrit trois fichiers : le cahier (dépêches + fiches des candidates, sans la vérité), la grille à remplir (CSV : F, f
    ou vide pour chaque candidate) et la clé, à NE PAS ouvrir avant d'avoir rempli la grille. Les candidates sont
    présentées dans le même ordre alphabétique que pour le lecteur ; aucun nom de carte n'apparaît dans les dépêches."""
    import csv
    cands = situations_codables(passages, protocole)
    random.Random(f"humain:{graine}").shuffle(cands)
    cands = cands[:n]
    m = ap._moteur()
    dossier.mkdir(parents=True, exist_ok=True)
    cahier = ["# Monde synthétique — cahier du codeur humain", "",
              "Pour chaque situation : lire les dépêches, puis, pour chaque carte candidate, décider d'après sa "
              "définition et ses marqueurs seulement : **F** (fait corroboré par deux médias qui remplit un marqueur), "
              "**f** (un marqueur rempli, une seule source ou partiellement), ou **rien** (la carte n'est pas montrée). "
              "Remplir `grille.csv`, colonne `lecture`. Ne pas ouvrir `cle.json` avant d'avoir fini.", ""]
    lignes, cle, vues = [], {"protocole_monde": None, "situations": {}}, set()
    for i, r in enumerate(cands, 1):
        sid = f"S{i:02d}"
        strate = r["_strate"]
        cartes = sorted(r["presentes"] + r["absentes"])
        cahier += [f"## {sid}", "", r["texte"].strip(), "", "**Cartes candidates** (fiches en annexe) : "
                   + ", ".join(m.NOMS.get(k.split("@")[0], k) for k in cartes), ""]
        vues.update(k.split("@")[0] for k in cartes)
        for k in cartes:
            lignes.append({"situation": sid, "carte": m.NOMS.get(k.split("@")[0], k), "cle": k, "lecture": ""})
        cle["situations"][sid] = {"passage": r["_passage"], "graine": r.get("graine"), "presentes": r["presentes"],
                                  "absentes": r["absentes"], "verification": r["verification"],
                                  "corrobores": (r.get("canevas") or {}).get("corrobores", []),
                                  "lecteur": r.get("ancrees") or {},
                                  "lecteur_reflechi": (r.get("lecture_reflechie") or {}).get("ancrees")}
    protos = [d.get("protocole_monde") for d in passages if d.get("protocole_monde")]
    cle["protocole_monde"] = protocole or (max(protos) if protos else None)
    cahier += ["# Annexe — fiches des cartes", "", ap.fiches(sorted(vues))]
    (dossier / "cahier.md").write_text("\n".join(cahier) + "\n", encoding="utf-8")
    with open(dossier / "grille.csv", "w", newline="", encoding="utf-8") as f_:
        w = csv.DictWriter(f_, fieldnames=["situation", "carte", "cle", "lecture"])
        w.writeheader()
        w.writerows(lignes)
    (dossier / "cle.json").write_text(json.dumps(cle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"situations": len(cands), "cartes": len(lignes), "dossier": str(dossier)}


def noter_humain(dossier: Path) -> dict:
    """Compare la grille remplie à la vérité VÉRIFIÉE (mêmes exclusions que `mesure_verifiee`) et au lecteur sur les
    mêmes cartes : sensibilité et faux positifs de l'humain, du lecteur, et accord humain–lecteur."""
    import csv
    cle = json.loads((dossier / "cle.json").read_text(encoding="utf-8"))["situations"]
    hum: dict[str, dict[str, str]] = {}
    with open(dossier / "grille.csv", encoding="utf-8") as f_:
        for x in csv.DictReader(f_):
            v = (x.get("lecture") or "").strip()
            if v in ("F", "f"):
                hum.setdefault(x["situation"], {})[x["cle"]] = v
    def stats(lire):
        p_, a_ = [], []
        for sid, c in cle.items():
            ver = c["verification"]
            p_ += [(lire(sid, c).get(k)) for k in c["presentes"] if k not in ver["presentes_non_montrees"]]
            a_ += [(lire(sid, c).get(k)) for k in c["absentes"] if k not in ver["absentes_montrees"]]
        r = lambda xs, f: round(sum(1 for v in xs if f(v)) / len(xs), 4) if xs else None
        return {"sens": r(p_, bool), "sens_F": r(p_, lambda v: v == "F"), "fp": r(a_, bool),
                "fp_F": r(a_, lambda v: v == "F"), "presentes": len(p_), "absentes": len(a_)}
    out = {"situations": len(cle), "humain": stats(lambda sid, c: hum.get(sid, {})),
           "lecteur": stats(lambda sid, c: c.get("lecteur") or {})}
    if all(c.get("lecteur_reflechi") is not None for c in cle.values()):
        out["lecteur_reflechi"] = stats(lambda sid, c: c.get("lecteur_reflechi") or {})
    acc = []
    for sid, c in cle.items():
        a1, a2 = set(hum.get(sid, {})), set(c.get("lecteur") or {})
        acc.append(len(a1 & a2) / len(a1 | a2) if a1 | a2 else 1.0)
    out["accord_humain_lecteur_jaccard"] = round(sum(acc) / len(acc), 4) if acc else None
    out["lecture"] = ("humain proche du lecteur : les erreurs viennent des fiches ou des textes ; humain nettement "
                      "meilleur : elles viennent du lecteur")
    return out


def abreviations(ancrees_: dict[str, str]) -> set[str]:
    return {k.split("@")[0] for k in ancrees_}


def montrees(v: dict | None, s: dict) -> set[str] | None:
    """0.10.72 : les cartes qu'un texte montre selon le vérificateur (abréviations), à partir de son écart avec la
    situation voulue s ; None si le vérificateur n'a rien rendu."""
    if not isinstance(v, dict) or "erreur" in v or "absentes_montrees" not in v:
        return None
    return abreviations((set(s["presentes"]) - set(v.get("presentes_non_montrees") or []))
                        | set(v.get("absentes_montrees") or []))


def validite_relative(vu_ancre: set[str] | None, vu_accord: set[str] | None, vu_leurre: set[str] | None,
                      x: str, cles: set[str]) -> dict:
    """0.10.72 : un triplet se juge sur ce que le vérificateur VOIT dans les trois textes, pas sur ce que le narrateur
    devait écrire (même règle que la mesure vérifiée des ancres). Comparaison sur les cartes contrôlées dans l'ancre.
    - accord valide : il montre les mêmes cartes que l'ancre (transposées dans l'autre strate) ;
    - leurre valide : la carte x est vue dans l'ancre, pas dans le leurre, et le reste est identique.
    « souple » tolère une carte d'écart (rapporté à part, jamais compté dans le taux)."""
    out = {}
    if vu_ancre is None:
        return out
    a = vu_ancre & cles
    if vu_accord is not None:
        d = len(a ^ (vu_accord & cles))
        out.update(accord_valide=d == 0, accord_souple=d <= 1)
    if vu_leurre is not None:
        x_ = x.split("@")[0]
        d = len((a - {x_}) ^ ((vu_leurre & cles) - {x_}))
        ok = x_ in a and x_ not in vu_leurre
        out.update(leurre_valide=ok and d == 0, leurre_souple=ok and d <= 1)
    return out


def mesurer_triplets(rows: list[dict]) -> dict | None:
    """0.10.67 (Blair, Procaccia et Tambe, NeurIPS 2026 : triplets durs). Pour chaque situation lue : ANCRE (le texte
    ordinaire), ACCORD (mêmes cartes cachées, autre strate et autre vocabulaire), LEURRE (même domaine, mêmes acteurs,
    une carte présente remplacée par un fait qui en garde les mots sans la réaliser). Un lecteur qui lit la structure
    code l'accord comme l'ancre et le leurre autrement ; un lecteur qui suit la surface fait l'inverse. Réussite d'un
    triplet : |ancre △ accord| < |ancre △ leurre| (½ en cas d'égalité ; ensembles d'abréviations ancrées). À part, la
    carte du leurre : vue dans l'ancre et pas dans le leurre (discrimine), vue dans les deux (suit la surface)."""
    T0 = [r for r in rows if r.get("statut") == "lue" and isinstance(r.get("triplet"), dict)
          and "ancrees_accord" in r["triplet"] and "ancrees_leurre" in r["triplet"]]
    # mesure vérifiée : un triplet dont le narrateur a raté l'accord ou le leurre n'est pas compté contre le lecteur.
    # 0.10.72 : validité RELATIVE (ce que le vérificateur voit dans les trois textes) quand elle est calculée ; sinon
    # l'ancien critère absolu (lignes d'avant 0.10.72).
    def valide(t: dict) -> bool:
        if "accord_valide" in t or "leurre_valide" in t:
            return bool(t.get("accord_valide")) and bool(t.get("leurre_valide"))
        return not t.get("leurre_rate_par_narrateur") and not t.get("accord_rate_par_narrateur")
    T = [r for r in T0 if valide(r["triplet"])]
    reecr = [r["triplet"].get("reecritures") or {} for r in T0]
    bilan_reecr = {"leurre": sum(1 for x in reecr if "leurre" in x), "leurre_sauve": sum(1 for x in reecr if x.get("leurre")),
                   "accord": sum(1 for x in reecr if "accord" in x), "accord_sauve": sum(1 for x in reecr if x.get("accord"))}
    souples = sum(1 for r in T0 if r["triplet"].get("accord_souple") and r["triplet"].get("leurre_souple"))
    if not T:
        return ({"n": 0, "ecartes_erreur_narrateur": len(T0), "valides_a_une_carte_pres": souples,
                 "reecritures": bilan_reecr} if T0 else None)
    reussite, disc, surf, invar = 0.0, 0, 0, []
    for r in T:
        A = abreviations(r["ancrees"])
        Acc = abreviations(r["triplet"]["ancrees_accord"])
        L = abreviations(r["triplet"]["ancrees_leurre"])
        d1, d2 = len(A ^ Acc), len(A ^ L)
        reussite += 1.0 if d1 < d2 else 0.5 if d1 == d2 else 0.0
        x = r["triplet"]["carte_leurre"].split("@")[0]
        disc += x in A and x not in L
        surf += x in A and x in L
        invar.append(len(A & Acc) / len(A | Acc) if A | Acc else 1.0)
    return {"n": len(T), "ecartes_erreur_narrateur": len(T0) - len(T), "valides_a_une_carte_pres": souples,
            "reecritures": bilan_reecr,
            "triplets_reussis": round(reussite, 1), "taux": round(reussite / len(T), 3),
            "leurre_discrimine": disc, "leurre_suit_la_surface": surf,
            "invariance_jaccard_moyenne": round(sum(invar) / len(invar), 3),
            "lecture": "triplets réussis / n : 0,5 = hasard ; le leurre doit être discriminé, pas suivi"}


def motif_reecriture(role: str, x: str | None, vu: set[str], voulu: set[str], noms: dict) -> str:
    """0.10.72 : ce que le vérificateur a vu de travers, dit au narrateur pour UNE réécriture."""
    trop = sorted(vu - voulu)
    manque = sorted(voulu - vu)
    lignes = ["", "CORRECTION : une première version a été refusée par un relecteur indépendant."]
    if trop:
        lignes.append("Des faits y remplissaient des marqueurs INTERDITS : " + ", ".join(noms.get(c, c) for c in trop)
                      + ". Supprime tout fait, chiffre ou acte qui les remplit.")
    if manque:
        lignes.append("Des marqueurs IMPOSÉS n'y étaient pas remplis : " + ", ".join(noms.get(c, c) for c in manque)
                      + ". Écris le fait exact qui les remplit.")
    if role == "leurre" and x:
        lignes.append(f"Rappel : le marqueur de {noms.get(x, x)} doit être évoqué SANS avoir lieu.")
    return "\n".join(lignes)


async def triplet(narrateur, lecteur, s: dict, strate: int, g: int, aujourdhui: str, texte: str,
                  verificateur=None, verif_ancre: dict | None = None) -> dict:
    """0.10.67 : l'ACCORD et le LEURRE d'une situation déjà lue (l'ancre). L'accord est écrit dans une autre strate
    (13, sinon 6) par d'autres acteurs (autre graine de canevas) ; le leurre reprend le canevas de l'ancre."""
    m = ap._moteur()
    rnd = random.Random(f"triplet:{strate}:{g}")
    out: dict = {}
    s2 = next((x for x in (13, 6) if x != strate and not any(m.hors_domaine(f"{k.split('@')[0]}@{x}")
                                                              for k in s["presentes"] + s["absentes"])), None)
    if not s["presentes"]:
        return {"erreur": "aucune carte présente : pas de leurre possible"}
    x = rnd.choice(sorted(s["presentes"]))
    out["carte_leurre"] = x
    # LEURRE : même canevas, la carte x écrite en quasi-réalisation (et non réalisée)
    noms = {k: v for k, v in m.NOMS.items()}
    vu_ancre = montrees(verif_ancre, s)
    cles = abreviations(s["presentes"] + s["absentes"])
    if verif_ancre is not None and isinstance(verif_ancre, dict):
        # l'ancre n'est contrôlée que sur ses candidates : la comparaison se limite à elles
        cles = abreviations(set(s["presentes"]) | set(verif_ancre.get("absentes_montrees") or [])
                            | set(verif_ancre.get("_cles") or [])) or cles
    s_l = {"presentes": [k for k in s["presentes"] if k != x], "absentes": sorted(s["absentes"] + [x])}
    vu_l = None
    try:
        consigne_l = consigne_narrateur(s["presentes"], s["absentes"], strate, aujourdhui, g, leurre=x)
        t_l = str(await narrateur(consigne_l)).strip()
        if verificateur is not None:    # le narrateur a-t-il bien écrit x SANS le réaliser ?
            v = await verifier(verificateur, t_l, sorted(s["presentes"] + s["absentes"]), s_l, strate)
            vu_l = montrees(v, s_l)
            voulu = (vu_ancre - {x.split("@")[0]}) if vu_ancre is not None else abreviations(s_l["presentes"])
            if vu_l is not None and (vu_l & cles) != (voulu & cles):
                # 0.10.72 : UNE réécriture, avec ce que le vérificateur a vu de travers
                out.setdefault("reecritures", {})["leurre"] = False
                t2 = str(await narrateur(consigne_l + motif_reecriture("leurre", x.split("@")[0], vu_l & cles,
                                                                        voulu & cles, noms))).strip()
                v2 = await verifier(verificateur, t2, sorted(s["presentes"] + s["absentes"]), s_l, strate)
                vu2 = montrees(v2, s_l)
                if vu2 is not None and (vu2 & cles) == (voulu & cles):
                    out["reecritures"]["leurre"] = True
                if vu2 is not None and len((vu2 & cles) ^ (voulu & cles)) < len((vu_l & cles) ^ (voulu & cles)):
                    t_l, v, vu_l = t2, v2, vu2          # on garde la meilleure des deux versions
            out["verification_leurre"] = v
            out["leurre_rate_par_narrateur"] = x in (v.get("absentes_montrees") or [])
        out["ancrees_leurre"] = await _lire(lecteur, s, strate, g, aujourdhui, t_l, "leurre")
        out["texte_leurre"] = t_l
    except Exception as e:
        out["erreur_leurre"] = f"{type(e).__name__}: {e}"[:200]
    # ACCORD : mêmes cartes, autre strate, autre vocabulaire, autres acteurs
    if s2 is None:
        out["erreur_accord"] = "aucune strate d'accord admissible"
        return out
    s_acc = {"presentes": [f"{k.split('@')[0]}@{s2}" for k in s["presentes"]],
             "absentes": [f"{k.split('@')[0]}@{s2}" for k in s["absentes"]],
             "evenement": f"{s['evenement'].split('@')[0]}@{s2}"}
    vu_a = None
    try:
        consigne_a = consigne_narrateur(s_acc["presentes"], s_acc["absentes"], s2, aujourdhui, g + 100000)
        t_a = str(await narrateur(consigne_a)).strip()
        if verificateur is not None:    # l'accord montre-t-il les mêmes cartes que l'ancre ?
            v = await verifier(verificateur, t_a, sorted(s_acc["presentes"] + s_acc["absentes"]), s_acc, s2)
            vu_a = montrees(v, s_acc)
            voulu = vu_ancre if vu_ancre is not None else abreviations(s_acc["presentes"])
            if vu_a is not None and (vu_a & cles) != (voulu & cles):
                out.setdefault("reecritures", {})["accord"] = False
                t2 = str(await narrateur(consigne_a + motif_reecriture("accord", None, vu_a & cles, voulu & cles,
                                                                        noms))).strip()
                v2 = await verifier(verificateur, t2, sorted(s_acc["presentes"] + s_acc["absentes"]), s_acc, s2)
                vu2 = montrees(v2, s_acc)
                if vu2 is not None and (vu2 & cles) == (voulu & cles):
                    out["reecritures"]["accord"] = True
                if vu2 is not None and len((vu2 & cles) ^ (voulu & cles)) < len((vu_a & cles) ^ (voulu & cles)):
                    t_a, v, vu_a = t2, v2, vu2
            out["verification_accord"] = v
            out["accord_rate_par_narrateur"] = bool(v.get("presentes_non_montrees") or v.get("absentes_montrees"))
        out["ancrees_accord"] = await _lire(lecteur, s_acc, s2, g, aujourdhui, t_a, "accord")
        out["strate_accord"] = s2
        out["texte_accord"] = t_a
    except Exception as e:
        out["erreur_accord"] = f"{type(e).__name__}: {e}"[:200]
    out.update(validite_relative(vu_ancre, vu_a, vu_l, x, cles))
    return out


async def _lire(lecteur, s: dict, strate: int, g: int, aujourdhui: str, texte: str, role: str) -> dict[str, str]:
    if not texte:
        raise ValueError("texte vide")
    plan = plan_de(s, strate)
    q = ap.Question(id=f"monde-{strate}-{g}-{role}", url="", titre=f"Situation synthétique {g} ({nom_strate(strate)}) : "
                    "quelles structures les faits montrent-ils ?", contexte="", criteres="Exercice de mesure du "
                    "lecteur ; aucune résolution.", precisions="Les dépêches sont fictives et seules sources.",
                    resolution=date.fromisoformat(aujourdhui) + timedelta(days=90))
    executees = [{"famille": "situation", "cartes": plan["candidats"], "requete": "dépêches du monde synthétique",
                  "resultat": texte, "executee": True}]
    lec = await ap.json_avec_reprise(lecteur, ap.consigne_dossier(q, plan, executees, aujourdhui, 90))
    return ancrees(lec, strate)


async def lancer(narrateur, lecteur, n: int, strate: int = 7, graine0: int = 0, aujourdhui: str | None = None,
                 verificateur=None, effacement: bool = False, reflechi=None, triplets: bool = False,
                 partiel: Path | None = None) -> dict:
    m = ap._moteur()
    aujourdhui = aujourdhui or date.today().isoformat()
    cartes = [c for c in sorted(m.NOMS) if not m.hors_domaine(f"{c}@{strate}")]
    rows = []
    for g in range(graine0, graine0 + n):
        s = situation(strate, g, cartes)
        if not s["evenement"]:
            rows.append(dict(s, statut="sans_evenement"))
            continue
        try:
            texte = str(await narrateur(consigne_narrateur(s["presentes"], s["absentes"], strate, aujourdhui,
                                                           g))).strip()
            if not texte:
                raise ValueError("texte vide")
        except Exception as e:
            rows.append(dict(s, statut="narrateur_illisible", motif=f"{type(e).__name__}: {e}"[:200]))
            continue
        plan = plan_de(s, strate)
        # 0.10.31 : plus de réécriture guidée (elle n'a rien corrigé en trois passages : 15 → 18 erreurs au dernier) ;
        # la mesure vérifiée retire les erreurs du narrateur.
        q = ap.Question(id=f"monde-{strate}-{g}", url="", titre=f"Situation synthétique {g} ({nom_strate(strate)}) : "
                        "quelles structures les faits montrent-ils ?", contexte="", criteres="Exercice de mesure du "
                        "lecteur ; aucune résolution.", precisions="Les dépêches sont fictives et seules sources.",
                        resolution=date.fromisoformat(aujourdhui) + timedelta(days=90))
        executees = [{"famille": "situation", "cartes": plan["candidats"], "requete": "dépêches du monde synthétique",
                      "resultat": texte, "executee": True}]
        row = dict(s, texte=texte, fuites=fuites(texte), canevas=canevas(s["presentes"], strate, g, aujourdhui))
        if verificateur is not None:     # le texte montre-t-il bien les présentes, et seulement elles ?
            row["verification"] = await verifier(verificateur, texte, plan["candidats"], s, strate)
        reprises: dict = {}
        try:
            lec = await ap.json_avec_reprise(lecteur, ap.consigne_dossier(q, plan, executees, aujourdhui, 90), reprises,
                                             "lecture")
            if reprises:
                row["reprises_json"] = reprises["reprises_json"]
        except Exception as e:
            rows.append(dict(row, statut="lecture_illisible", motif=f"{type(e).__name__}: {e}"[:200]))
            continue
        _, cats = ap.rejets_moteur(lec if isinstance(lec, dict) else {})
        cats_n = {}
        for k, v in cats.items():
            try:
                cats_n[f"{m.carte_id(k.split('@')[0])}@{k.split('@')[1] if '@' in k else strate}"] = v
            except ValueError:
                continue
        row = dict(row, statut="lue", ancrees=ancrees(lec, strate), rejets_categories=cats_n)
        if effacement:       # 0.10.34 : même texte, même consigne, cartes renommées en identifiants neutres
            table = table_effacement(g)
            inverse = {i: a for a, i in table.items()}
            try:
                lec2 = await ap.json_avec_reprise(lecteur, effacer_noms(ap.consigne_dossier(q, plan, executees, aujourdhui,
                                                                                             90), table))
                row["lecture_sans_noms"] = {"ancrees": ancrees(lec2, strate, inverse)}
            except Exception as e:
                row["lecture_sans_noms"] = {"erreur": f"{type(e).__name__}: {e}"[:200]}
        if triplets:               # 0.10.67 : l'accord et le leurre de cette ancre (triplets durs)
            row["triplet"] = await triplet(narrateur, lecteur, s, strate, g, aujourdhui, texte, verificateur,
                                           row.get("verification"))
        if reflechi is not None:   # 0.10.36 : même modèle, même consigne, mais le droit de réfléchir avant de répondre
            try:
                lec3 = await ap.json_avec_reprise(reflechi, ap.consigne_dossier(q, plan, executees, aujourdhui, 90))
                row["lecture_reflechie"] = {"ancrees": ancrees(lec3, strate)}
            except Exception as e:
                row["lecture_reflechie"] = {"erreur": f"{type(e).__name__}: {e}"[:200]}
        rows.append(row)
        # 0.10.72 : une ligne par situation, et les situations déjà faites écrites au fur et à mesure (un arrêt du
        # passage ne perd plus tout ; le fichier partiel n'entre dans aucun cumul)
        t_ = row.get("triplet") or {}
        print(f"situation {g} ({len(rows)}/{n}) : {row.get('statut')} ; ancrées {sorted(row.get('ancrees') or [])}"
              + (f" ; triplet accord {t_.get('accord_valide')} leurre {t_.get('leurre_valide')}" if t_ else ""),
              flush=True)
        if partiel is not None:
            try:
                partiel.write_text(json.dumps({"graines": [graine0, g], "situations": rows}, ensure_ascii=False) + "\n",
                                   encoding="utf-8")
            except OSError:
                pass
    return {"calcule_le": datetime.now(timezone.utc).isoformat(timespec="seconds"), "version_skill": ap.version_skill(),
            "version_bot": ap.VERSION_BOT, "modele": (ap.modeles_actifs() or {}).get("principal"), "strate": strate,
            "graines": [graine0, graine0 + n - 1],
            "consigne_lecteur_sha256": hashlib.sha256(ap.regles_dossier().encode()).hexdigest(),
            "reserve": "si narrateur et lecteur sont de la même famille : borne optimiste de la sensibilité (§43)",
            "resultat": mesurer(rows), "triplets": mesurer_triplets(rows), "situations": rows}


async def principal() -> int:
    import alphabet_bot as ab
    import alphabet_modeles as am
    choix, _ = await am.choisir()
    if not choix.get("principal"):
        print("Aucun modèle principal disponible. Rien n'est lancé.")
        return 1
    am.appliquer(choix)
    modele = ab.configuration().get("default")

    async def llm(c: str) -> str:
        return await modele.invoke(c)
    # 0.10.22 : narrateur d'une AUTRE famille que le lecteur (MONDE_NARRATEUR : un identifiant de modèle, ou
    # « contradicteur » pour reprendre le modèle de ce rôle) : sans lui, narrateur et lecteur partagent leurs habitudes
    # et la sensibilité mesurée est trop flatteuse.
    choix_n = (os.environ.get("MONDE_NARRATEUR") or "").strip()
    nom_n = choix.get("contradicteur") if choix_n == "contradicteur" else (choix_n or None)
    if choix_n and not nom_n:
        # 0.10.24 : un narrateur demandé mais indisponible arrête le passage, au lieu de retomber EN SILENCE sur le
        # lecteur (passage du 2026-11-11 à 03 h 55 : « contradicteur » demandé, Sonnet employé)
        print(f"Narrateur « {choix_n} » demandé mais indisponible (variable ALPHABET_CONTRADICTEUR ?). Rien n'est lancé.")
        return 1
    narrateur = llm
    if nom_n:
        from forecasting_tools import GeneralLlm
        modele_n = GeneralLlm(model=nom_n, temperature=0.7, timeout=180, allowed_tries=2)

        async def narrateur(c: str) -> str:
            return await modele_n.invoke(c)
    strate = int(os.environ.get("MONDE_STRATE") or 7)
    if strate not in ap.strates_chiffrees():
        print(f"Strate {strate} non chiffrée (L7) : la mesure reste possible mais hors du périmètre posté.")
    precedents = sorted(ap.REGISTRE.glob("monde-synthetique-*.json")) if ap.REGISTRE.is_dir() else []
    deja = []
    for f_ in precedents:
        try:
            deja.append(json.loads(f_.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError):
            continue
    # graines nouvelles par défaut : un passage de plus ajoute des situations au lieu de rejouer les mêmes
    graine0 = os.environ.get("MONDE_GRAINE")
    graine0 = int(graine0) if graine0 else 1 + max([d.get("graines", [0, -1])[1] for d in deja] or [-1])
    # 0.10.25 : le vérificateur doit être d'une TROISIÈME famille (ni celle du lecteur, ni celle du narrateur), sinon
    # il voit ce que voit le lecteur et les faux positifs vérifiés sont trop flatteurs. MONDE_VERIFICATEUR : un
    # identifiant de modèle ; vide = le petit modèle (signalé comme de même famille). Il est sondé avant le passage.
    nom_v = (os.environ.get("MONDE_VERIFICATEUR") or "").strip() or choix.get("petit")
    verificateur = None
    if nom_v:
        sonde = await am.sonder(nom_v)
        if not sonde.get("json_ok"):
            print(f"Vérificateur « {nom_v} » indisponible ({sonde.get('erreur')}). Rien n'est lancé.")
            return 1
        from forecasting_tools import GeneralLlm
        modele_v = GeneralLlm(model=nom_v, temperature=0, timeout=180, allowed_tries=2)

        async def verificateur(c: str) -> str:
            return await modele_v.invoke(c)
    reflechi = None
    if os.environ.get("MONDE_REFLEXION", "1") != "0":
        from forecasting_tools import GeneralLlm
        modele_r = GeneralLlm(model=choix["principal"], timeout=300, allowed_tries=2, **options_reflexion(choix["principal"]))

        async def reflechi(c: str) -> str:
            return await modele_r.invoke(c)
    ap.REGISTRE.mkdir(parents=True, exist_ok=True)
    partiel = ap.REGISTRE / "partiel-monde-synthetique.json"
    r = await lancer(narrateur, llm, int(os.environ.get("MONDE_SITUATIONS") or 12), strate, graine0,
                     verificateur=verificateur, effacement=os.environ.get("MONDE_EFFACEMENT", "1") != "0",
                     reflechi=reflechi, triplets=os.environ.get("MONDE_TRIPLETS", "0") not in ("0", "", "non"),
                     partiel=partiel)
    partiel.unlink(missing_ok=True)
    if r.get("triplets"):
        print("Triplets durs :", json.dumps(r["triplets"], ensure_ascii=False))
    r["reflexion"] = options_reflexion(choix["principal"]) if reflechi else None
    r["verificateur"] = nom_v if verificateur else None
    fam = lambda nom: next((f for f in ("claude", "deepseek", "mistral", "qwen", "llama", "nova", "gpt", "glm", "kimi")
                            if f in str(nom or "").lower()), str(nom))
    r["verificateur_famille_distincte"] = bool(verificateur) and fam(nom_v) not in (fam(r.get("modele")),
                                                                                   fam(r.get("narrateur")))
    r["narrateur"] = nom_n or r.get("modele")
    r["meme_famille"] = not nom_n or nom_n == r.get("modele")
    r["protocole_monde"] = PROTOCOLE_MONDE
    # cumul des passages de même strate ET même narrateur (un narrateur de la même famille ne se mélange pas à un autre)
    meme = [d for d in deja + [r] if d.get("strate") == strate and d.get("protocole_monde", 1) == PROTOCOLE_MONDE
            and (d.get("narrateur") or d.get("modele")) == r["narrateur"] and d.get("verificateur") == r["verificateur"]]
    r["cumul"] = {"passages": len(meme), "narrateur": r["narrateur"], "protocole_monde": PROTOCOLE_MONDE,
                  **mesurer([s for d in meme for s in d.get("situations") or []])}
    r["cumul"].pop("par_carte", None)
    ap.REGISTRE.mkdir(parents=True, exist_ok=True)
    f = ap.REGISTRE / f"monde-synthetique-{r['calcule_le'][:16].replace(':', '')}.json"
    f.write_text(json.dumps(r, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    x = r["resultat"]
    print(f"Monde synthétique : {x['lues']}/{x['situations']} lues ; narrateur {r['narrateur']} ; mesuré {x['mesure']} ; "
          f"stipulé {x['stipule']} → {f.name}")
    print(f"Mesure vérifiée par {r['verificateur']} (famille distincte : {r['verificateur_famille_distincte']}) : "
          f"{x.get('mesure_verifiee')}")
    print(f"Perturbations : {(x.get('mesure_verifiee') or {}).get('perturbations')}")
    print(f"Cumul ({r['cumul']['passages']} passages, {r['cumul']['lues']} situations lues) : {r['cumul']['mesure']}")
    return 0 if x["lues"] else 1


def _charger_passages() -> list[dict]:
    out = []
    for f_ in sorted(ap.REGISTRE.glob("monde-synthetique-*.json")) if ap.REGISTRE.is_dir() else []:
        try:
            out.append(json.loads(f_.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError):
            continue
    return out


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "exporter-humain":
        # python monde_synthetique.py exporter-humain [N] [DOSSIER]
        n = int(sys.argv[2]) if len(sys.argv) > 2 else 20
        d = Path(sys.argv[3]) if len(sys.argv) > 3 else ap.REGISTRE / f"codeur-humain-{date.today().isoformat()}"
        print(json.dumps(exporter_humain(_charger_passages(), d, n), ensure_ascii=False))
        raise SystemExit(0)
    if len(sys.argv) > 2 and sys.argv[1] == "noter-humain":
        print(json.dumps(noter_humain(Path(sys.argv[2])), ensure_ascii=False, indent=2))
        raise SystemExit(0)
    raise SystemExit(asyncio.run(principal()))
