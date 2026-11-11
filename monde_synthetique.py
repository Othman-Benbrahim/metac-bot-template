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

    python monde_synthetique.py          # MONDE_SITUATIONS (12 par défaut), MONDE_STRATE (7), MONDE_GRAINE (0)
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


def consigne_narrateur(presentes: list[str], absentes: list[str], strate: int, aujourdhui: str) -> str:
    m = ap._moteur()
    abr = lambda k: k.split("@")[0]
    noms = [m.NOMS[abr(k)] for k in presentes]
    montrer = (f"Les dépêches doivent MONTRER, chacune par au moins un fait observable et daté qui remplit l'un de ses "
               f"« Marqueurs observables », les structures suivantes : {', '.join(noms)}."
               if presentes else
               "Aucune structure de la liste ci-dessous ne doit être montrée : décris une actualité ordinaire, sans "
               "dynamique marquante.")
    return f"""Tu écris des dépêches de presse FICTIVES pour un exercice de mesure. Domaine : {nom_strate(strate)}.

{montrer}

Fiches des structures à montrer (ne les nomme JAMAIS, ni par leur nom ni par un synonyme savant ; montre-les par des
faits : qui fait quoi, quand, combien) :
{ap.fiches([abr(k) for k in presentes]) if presentes else "(aucune)"}

Structures à NE PAS évoquer, même indirectement : {', '.join(m.NOMS[abr(k)] for k in absentes) or "(aucune)"}.

Contraintes :
- pays, villes, personnes, organisations et sites de presse INVENTÉS (aucun nom réel) ; adresses en https://….example/… ;
- trois à cinq dépêches, datées entre {(date.fromisoformat(aujourdhui) - timedelta(days=60)).isoformat()} et {aujourdhui} ;
- ton factuel, sans interprétation ni conclusion ; 60 à 120 mots par dépêche ;
- format exact, une dépêche par bloc, blocs séparés par une ligne vide :
[AAAA-MM-JJ] Titre — https://site-invente.example/chemin
Texte de la dépêche.

Rends uniquement les dépêches."""


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
    return {"situations": len(rows), "lues": len(lues),
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


async def lancer(narrateur, lecteur, n: int, strate: int = 7, graine0: int = 0, aujourdhui: str | None = None) -> dict:
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
            "reserve": "narrateur et lecteur de la même famille : borne optimiste de la sensibilité (§43)",
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
    strate = int(os.environ.get("MONDE_STRATE") or 7)
    if strate not in ap.strates_chiffrees():
        print(f"Strate {strate} non chiffrée (L7) : la mesure reste possible mais hors du périmètre posté.")
    r = await lancer(llm, llm, int(os.environ.get("MONDE_SITUATIONS") or 12), strate,
                     int(os.environ.get("MONDE_GRAINE") or 0))
    ap.REGISTRE.mkdir(parents=True, exist_ok=True)
    f = ap.REGISTRE / f"monde-synthetique-{r['calcule_le'][:10]}.json"
    f.write_text(json.dumps(r, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    x = r["resultat"]
    print(f"Monde synthétique : {x['lues']}/{x['situations']} lues ; mesuré {x['mesure']} ; stipulé {x['stipule']} → {f.name}")
    return 0 if x["lues"] else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(principal()))
