"""Test de reconstruction de la matrice (bot 0.10.8 ; Wong et al. 2023, §4.2 « construire un modèle de zéro »).

Un modèle reçoit les seules DÉFINITIONS des 16 cartes (index du skill : définition et structure mathématique ; ni les
voisines, ni la matrice, ni aucun λ) et dit, pour chaque carte A, quelles cartes B sa présence rend plus probables au pas
suivant, avec une force (F, M, f). On compare à la matrice du skill (66 arêtes sur 240 paires ordonnées).

Lecture :
  - accord fort (κ élevé) : la matrice dit surtout ce que les définitions suggèrent déjà ; son information propre est
    faible, et les λ n'apportent que leur valeur numérique ;
  - accord faible ou localisé : les arêtes en désaccord sont à réexaminer — ni la matrice ni le modèle n'ont raison
    par principe ; c'est une liste de travail, pas un verdict.
Plusieurs essais indépendants (RECONSTRUCTION_ESSAIS, 3 par défaut) ; une arête est « reconstruite » si la majorité des
essais la donne. Rien n'est modifié : le résultat va dans registre/reconstruction-matrice-<date>.json.

    python reconstruction_matrice.py                 # lance (modèle principal de ALPHABET_LLM) et enregistre
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
from datetime import datetime, timezone

import alphabet_pipeline as ap

FORCES = ("F", "M", "f")


def definitions() -> list[dict]:
    """Lignes de cartes-index.md : carte, définition, structure mathématique. Les voisines sont exclues (A6 est un
    jugement sur la ressemblance, proche de la matrice)."""
    texte = ap.lire_ref("references/cartes-index.md")
    out = []
    for ligne in texte.splitlines():
        cols = [c.strip() for c in ligne.strip().strip("|").split("|")]
        if len(cols) >= 5 and cols[0] not in ("Carte", "---") and not set(cols[0]) <= {"-"}:
            out.append({"carte": cols[0], "definition": re.sub(r"\*\*", "", cols[2]), "structure": cols[3]})
    return out


def consigne(defs: list[dict]) -> str:
    lignes = "\n".join(f"- {d['carte']} : {d['definition']} (structure : {d['structure']})" for d in defs)
    noms = ", ".join(d["carte"] for d in defs)
    return f"""Voici seize structures qui peuvent être présentes dans une situation sociale, politique ou économique,
chacune définie en une phrase.

{lignes}

Pour chaque structure A, indique quelles autres structures B la PRÉSENCE de A rend nettement plus probables comme
APPARITION au pas de temps suivant, dans le même domaine, et avec quelle force :
  F = fortement, M = moyennement, f = faiblement. N'indique rien si l'effet est nul, incertain ou seulement possible.
Ne mets pas A dans sa propre liste. Sois sélectif : une structure en produit typiquement entre zéro et six autres.

Noms exacts à employer : {noms}.
Réponds par un seul objet JSON : {{"A": {{"B": "F" | "M" | "f", ...}}, ...}} avec les seize structures en clés."""


def normaliser(brut: dict, m) -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    for a, d in (brut or {}).items():
        try:
            ca = m.carte_id(str(a))
        except ValueError:
            continue
        for b, i in (d or {}).items() if isinstance(d, dict) else []:
            try:
                cb = m.carte_id(str(b))
            except ValueError:
                continue
            if cb != ca and i in FORCES:
                out.setdefault(ca, {})[cb] = i
    return out


def kappa(a: list[bool], b: list[bool]) -> float | None:
    n = len(a)
    if not n:
        return None
    po = sum(x == y for x, y in zip(a, b)) / n
    pa, pb = sum(a) / n, sum(b) / n
    pe = pa * pb + (1 - pa) * (1 - pb)
    return None if pe == 1 else (po - pe) / (1 - pe)


def comparer(essais: list[dict], matrice: dict, cartes: list[str]) -> dict:
    paires = [(a, b) for a in cartes for b in cartes if a != b]
    k = len(essais)
    votes = {p: sum(1 for e in essais if e.get(p[0], {}).get(p[1])) for p in paires}
    recon = {p: votes[p] * 2 > k for p in paires}
    vrai = {p: bool(matrice.get(p[0], {}).get(p[1])) for p in paires}
    tp = [p for p in paires if recon[p] and vrai[p]]
    fp = [p for p in paires if recon[p] and not vrai[p]]
    fn = [p for p in paires if not recon[p] and vrai[p]]
    ordre = {"f": 1, "M": 2, "F": 3}

    def force(p):  # force majoritaire parmi les essais qui donnent l'arête
        fs = [e[p[0]][p[1]] for e in essais if e.get(p[0], {}).get(p[1])]
        return max(set(fs), key=fs.count) if fs else None
    meme_force = sum(1 for p in tp if force(p) == matrice[p[0]][p[1]])
    ecart_force = [abs(ordre[force(p)] - ordre[matrice[p[0]][p[1]]]) for p in tp]
    stab = [kappa([bool(e.get(a, {}).get(b)) for a, b in paires], [bool(f.get(a, {}).get(b)) for a, b in paires])
            for i, e in enumerate(essais) for f in essais[i + 1:]]
    return {"paires": len(paires), "aretes_matrice": sum(vrai.values()), "aretes_reconstruites": sum(recon.values()),
            "accord_presence": {"kappa": kappa([recon[p] for p in paires], [vrai[p] for p in paires]),
                                "communes": len(tp), "seulement_modele": len(fp), "seulement_matrice": len(fn),
                                "precision": len(tp) / (len(tp) + len(fp)) if tp or fp else None,
                                "rappel": len(tp) / (len(tp) + len(fn)) if tp or fn else None},
            "accord_force_sur_communes": {"identique": meme_force, "ecart_moyen_crans": (sum(ecart_force) / len(ecart_force)
                                                                                           if ecart_force else None)},
            "stabilite_entre_essais_kappa": stab,
            "a_reexaminer": {
                "dans_la_matrice_jamais_reconstruites": [f"{a}→{b} ({matrice[a][b]})" for a, b in fn if votes[(a, b)] == 0],
                "reconstruites_par_tous_absentes_de_la_matrice": [f"{a}→{b} ({force((a, b))})" for a, b in fp
                                                                  if votes[(a, b)] == k]}}


async def lancer(llm, essais: int) -> dict:
    m = ap._moteur()
    defs = definitions()
    c = consigne(defs)
    bruts, erreurs = [], []
    for _ in range(essais):
        try:
            bruts.append(normaliser(ap.extraire_json(await llm(c)), m))
        except Exception as e:
            erreurs.append(f"{type(e).__name__}: {e}"[:200])
    cartes = sorted(m.NOMS)
    r = {"calcule_le": datetime.now(timezone.utc).isoformat(timespec="seconds"), "version_skill": ap.version_skill(),
         "version_bot": ap.VERSION_BOT, "modele": (ap.modeles_actifs() or {}).get("principal"),
         "consigne_sha256": hashlib.sha256(c.encode()).hexdigest(), "essais_demandes": essais,
         "essais_reussis": len(bruts), "erreurs": erreurs, "essais": bruts}
    if bruts:
        r["comparaison"] = comparer(bruts, m.P["matrice"], cartes)
    return r


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
    r = await lancer(llm, int(os.environ.get("RECONSTRUCTION_ESSAIS") or 3))
    ap.REGISTRE.mkdir(parents=True, exist_ok=True)
    f = ap.REGISTRE / f"reconstruction-matrice-{r['calcule_le'][:10]}.json"
    f.write_text(json.dumps(r, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    cp = (r.get("comparaison") or {}).get("accord_presence") or {}
    print(f"Reconstruction : {r['essais_reussis']}/{r['essais_demandes']} essais ; κ = {cp.get('kappa')} ; "
          f"communes {cp.get('communes')}, modèle seul {cp.get('seulement_modele')}, "
          f"matrice seule {cp.get('seulement_matrice')} → {f.name}")
    return 0 if r["essais_reussis"] else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(principal()))
