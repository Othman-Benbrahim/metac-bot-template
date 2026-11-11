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

import alphabet_pipeline as ap


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
    return [re.sub(r"\*\*", "", x).strip().rstrip(" ;.") for x in out]


def _bloc_marqueurs(cles: list[str]) -> str:
    m = ap._moteur()
    out = []
    for k in cles:
        a = k.split("@")[0]
        out.append(f"[{a}] " + " ; ".join(marqueurs(a)))
    return "\n".join(out)


def consigne_narrateur(presentes: list[str], absentes: list[str], strate: int, aujourdhui: str) -> str:
    """0.10.23 (calibrage après le premier passage) : le narrateur ne reçoit que les MARQUEURS observables (plus les
    définitions, qu'il paraphrasait : « le rythme progresse avec la longueur déjà posée ») ; il raconte UNE situation
    (mêmes acteurs, même pays) et non une dépêche par structure ; il reçoit aussi les marqueurs des absentes, à ne
    remplir par aucun fait ; aucune phrase d'explication ou d'analyse."""
    debut = (date.fromisoformat(aujourdhui) - timedelta(days=60)).isoformat()
    a_montrer = (f"Chacun des groupes de marqueurs suivants doit être rempli par AU MOINS UN fait daté (un seul marqueur "
                 f"du groupe suffit) :\n{_bloc_marqueurs(presentes)}" if presentes else
                 "Aucun des groupes de marqueurs ci-dessous ne doit être rempli : une actualité ordinaire, sans dynamique "
                 "marquante.")
    return f"""Tu écris des dépêches de presse FICTIVES pour un exercice de mesure. Domaine : {nom_strate(strate)}.

Elles racontent UNE SEULE situation : les mêmes acteurs (un ou deux pays inventés, leurs institutions, leurs
dirigeants), qui évolue d'une dépêche à l'autre.

{a_montrer}

AUCUN fait ne doit remplir les marqueurs suivants (ni explicitement, ni par un détail en passant) :
{_bloc_marqueurs(absentes) or "(aucun)"}

Règles d'écriture :
- uniquement des faits observables : qui a fait quoi, quand, combien ; des chiffres, des actes, des déclarations
  citées ; AUCUNE phrase qui explique, résume ou analyse le mécanisme (pas de « ainsi », « ce qui montre », « en
  retour », pas de commentaire d'analyste) ; ne nomme aucune structure, ni par un mot savant ;
- pays, villes, personnes, organisations et sites de presse INVENTÉS (aucun nom réel) ; adresses en https://….example/… ;
- trois à cinq dépêches, datées entre {debut} et {aujourdhui} ; 60 à 120 mots par dépêche ;
- format exact, une dépêche par bloc, blocs séparés par une ligne vide :
[AAAA-MM-JJ] Titre — https://site-invente.example/chemin
Texte de la dépêche.

Rends uniquement les dépêches."""


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


def ancrees(lecture: dict, strate: int) -> dict[str, str]:
    m = ap._moteur()
    out = {}
    for x in (lecture or {}).get("mots") or []:
        try:
            k = f"{m.carte_id(str(x.get('carte')))}@{int(x.get('strate'))}"
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
        verifiee = {"situations": len(ver),
                    "erreurs_narrateur": {"absentes_montrees": sum(len(r["verification"]["absentes_montrees"]) for r in ver),
                                          "presentes_non_montrees": sum(len(r["verification"]["presentes_non_montrees"])
                                                                        for r in ver)},
                    "sens_F": taux(pres_v, "F"), "sens_f": taux(pres_v, "f"),
                    "sens": round(sum(1 for _, v in pres_v if v) / len(pres_v), 4) if pres_v else None,
                    "fp_F": taux(abs_v, "F"), "fp_f": taux(abs_v, "f"),
                    "fp": round(sum(1 for _, v in abs_v if v) / len(abs_v), 4) if abs_v else None}
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


async def lancer(narrateur, lecteur, n: int, strate: int = 7, graine0: int = 0, aujourdhui: str | None = None,
                 verificateur=None) -> dict:
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
            texte = str(await narrateur(consigne_narrateur(s["presentes"], s["absentes"], strate, aujourdhui))).strip()
            if not texte:
                raise ValueError("texte vide")
        except Exception as e:
            rows.append(dict(s, statut="narrateur_illisible", motif=f"{type(e).__name__}: {e}"[:200]))
            continue
        plan = plan_de(s, strate)
        q = ap.Question(id=f"monde-{strate}-{g}", url="", titre=f"Situation synthétique {g} ({nom_strate(strate)}) : "
                        "quelles structures les faits montrent-ils ?", contexte="", criteres="Exercice de mesure du "
                        "lecteur ; aucune résolution.", precisions="Les dépêches sont fictives et seules sources.",
                        resolution=date.fromisoformat(aujourdhui) + timedelta(days=90))
        executees = [{"famille": "situation", "cartes": plan["candidats"], "requete": "dépêches du monde synthétique",
                      "resultat": texte, "executee": True}]
        row = dict(s, texte=texte, fuites=fuites(texte))
        if verificateur is not None:     # 0.10.23 : le texte montre-t-il bien les présentes, et seulement elles ?
            try:
                v = ap.extraire_json(await verificateur(consigne_verification(texte, plan["candidats"])))
                oui = {f"{m.carte_id(str(k))}@{strate}" for k, x in v.items() if str(x).lower().startswith("o")}
                row["verification"] = {"absentes_montrees": sorted(oui & set(s["absentes"])),
                                       "presentes_non_montrees": sorted(set(s["presentes"]) - oui)}
            except Exception as e:
                row["verification"] = {"erreur": f"{type(e).__name__}: {e}"[:200]}
        try:
            lec = ap.extraire_json(await lecteur(ap.consigne_dossier(q, plan, executees, aujourdhui, 90)))
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
        rows.append(dict(row, statut="lue", ancrees=ancrees(lec, strate), rejets_categories=cats_n))
    return {"calcule_le": datetime.now(timezone.utc).isoformat(timespec="seconds"), "version_skill": ap.version_skill(),
            "version_bot": ap.VERSION_BOT, "modele": (ap.modeles_actifs() or {}).get("principal"), "strate": strate,
            "graines": [graine0, graine0 + n - 1],
            "consigne_lecteur_sha256": hashlib.sha256(ap.regles_dossier().encode()).hexdigest(),
            "reserve": "si narrateur et lecteur sont de la même famille : borne optimiste de la sensibilité (§43)",
            "resultat": mesurer(rows), "situations": rows}


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
    verificateur = None                  # 0.10.23 : contrôle du narrateur par le petit modèle (autre que le lecteur)
    if choix.get("petit") and choix.get("petit") != choix.get("principal"):
        from forecasting_tools import GeneralLlm
        modele_v = GeneralLlm(model=choix["petit"], temperature=0, timeout=120, allowed_tries=2)

        async def verificateur(c: str) -> str:
            return await modele_v.invoke(c)
    r = await lancer(narrateur, llm, int(os.environ.get("MONDE_SITUATIONS") or 12), strate, graine0,
                     verificateur=verificateur)
    r["verificateur"] = choix.get("petit") if verificateur else None
    r["narrateur"] = nom_n or r.get("modele")
    r["meme_famille"] = not nom_n
    # cumul des passages de même strate ET même narrateur (un narrateur de la même famille ne se mélange pas à un autre)
    meme = [d for d in deja + [r] if d.get("strate") == strate
            and (d.get("narrateur") or d.get("modele")) == r["narrateur"]]
    r["cumul"] = {"passages": len(meme), "narrateur": r["narrateur"],
                  **mesurer([s for d in meme for s in d.get("situations") or []])}
    r["cumul"].pop("par_carte", None)
    ap.REGISTRE.mkdir(parents=True, exist_ok=True)
    f = ap.REGISTRE / f"monde-synthetique-{r['calcule_le'][:16].replace(':', '')}.json"
    f.write_text(json.dumps(r, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    x = r["resultat"]
    print(f"Monde synthétique : {x['lues']}/{x['situations']} lues ; narrateur {r['narrateur']} ; mesuré {x['mesure']} ; "
          f"stipulé {x['stipule']} → {f.name}")
    print(f"Mesure vérifiée (erreurs du narrateur retirées) : {x.get('mesure_verifiee')}")
    print(f"Cumul ({r['cumul']['passages']} passages, {r['cumul']['lues']} situations lues) : {r['cumul']['mesure']}")
    return 0 if x["lues"] else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(principal()))
