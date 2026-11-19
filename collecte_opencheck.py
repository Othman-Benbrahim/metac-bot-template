"""Collecte OpenCheck : qui possède les groupes de médias et les plateformes (bot 0.10.353, ombre).

Demande de l'auteur du 2026-11-19 (13 h 44) : relier les médias et les plateformes aux humains qui sont derrière. OpenCheck
(api.opencheck.world) : API gratuite, sans clé, lecture seule, réponses au standard BODS v0.4 rattachées au LEI.
Budget : dix vérifications (/lookup) par minute et par adresse ; la recherche (/search) ne le consomme pas. On fait
une recherche puis une vérification par groupe, avec une pause de 8 s.

Ce qu'on garde (registre/opencheck-proprietaires.json) :
- pour chaque groupe : le LEI retenu et le nom de la société trouvée (à relire : la recherche par nom peut se tromper) ;
- les SOCIÉTÉS qui le détiennent ou le contrôlent, avec la part quand le registre la donne ;
- les PERSONNES seulement si elles figurent déjà comme propriétaires de contrôle dans notre table publique
  (donnees/medias/*.csv) ; les autres ne sont que comptées, sans nom (règle : personnalités publiques par leurs faits
  publics, aucune personne privée) ;
- le nombre de signaux de risque par catégorie, et les avis de licence des sources.
"""
from __future__ import annotations

import csv
import json
import sys
import time
from pathlib import Path

import httpx

import politesse

BASE = "https://api.opencheck.world"
SORTIE = Path("registre") / "opencheck-proprietaires.json"
TABLES = Path("donnees") / "medias"
PAUSE = 8.0
GROUPES = ["LVMH Moet Hennessy Louis Vuitton", "Bollore SE", "Vivendi SE", "Louis Hachette Group", "Lagardere SA",
           "Canal+ SA", "Bouygues", "Television Francaise 1", "CMA CGM", "Bertelsmann SE", "RTL Group",
           "Metropole Television", "Altice France", "Artemis", "Groupe Industriel Marcel Dassault", "Societe du Figaro",
           "Czech Media Invest", "Banque Federative du Credit Mutuel", "Rossel", "NRJ Group", "Prisma Media",
           "Le Monde SA", "Alphabet Inc", "Meta Platforms", "Microsoft Corporation", "Amazon.com", "Apple Inc",
           "ByteDance", "X Corp"]


def noms_publics() -> set[str]:
    """Personnes déjà nommées comme propriétaires de contrôle dans nos tables publiques (minuscules)."""
    out = set()
    for f in TABLES.glob("*.csv"):
        for r in csv.DictReader(f.open(encoding="utf-8")):
            for champ in ("proprietaire_de_controle", "proprietaire"):
                for morceau in (r.get(champ) or "").replace(" et ", ";").replace(",", ";").split(";"):
                    m = morceau.split("(")[0].strip().lower()
                    if m:
                        out.add(m)
    return out


def enregistrements(obj) -> list[dict]:
    """Les enregistrements BODS d'une réponse, où qu'ils soient (liste de dicts portant recordType ou statementType)."""
    if isinstance(obj, list) and obj and isinstance(obj[0], dict) and ("recordType" in obj[0] or "statementType" in obj[0]):
        return obj
    if isinstance(obj, dict):
        for v in obj.values():
            r = enregistrements(v)
            if r:
                return r
    if isinstance(obj, list):
        for v in obj:
            r = enregistrements(v)
            if r:
                return r
    return []


def nom_de(e: dict) -> str:
    d = e.get("recordDetails") or e
    if d.get("name"):
        return str(d["name"])
    noms = d.get("names") or []
    return str((noms[0] or {}).get("fullName", "")) if noms else ""


def detenteurs(stmts: list[dict], publics: set[str]) -> dict:
    """Sociétés et personnes qui détiennent ou contrôlent, selon les relations BODS v0.4."""
    par_id = {s.get("recordId") or s.get("statementId"): s for s in stmts}
    societes, personnes, anonymes = [], [], 0
    for s in stmts:
        if (s.get("recordType") or s.get("statementType")) not in ("relationship", "ownershipOrControlStatement"):
            continue
        d = s.get("recordDetails") or s
        ip = d.get("interestedParty")
        cible = par_id.get(ip if isinstance(ip, str) else None)
        if not cible:
            continue
        parts = [i.get("share", {}).get("exact") for i in d.get("interests") or [] if isinstance(i.get("share"), dict)]
        part = next((p for p in parts if p is not None), None)
        nom = nom_de(cible)
        if (cible.get("recordType") or cible.get("statementType")) in ("person", "personStatement"):
            if nom.lower() in publics:
                personnes.append({"nom": nom, "part": part})
            else:
                anonymes += 1
        else:
            societes.append({"nom": nom, "part": part})
    return {"societes": societes, "personnes_publiques": personnes, "autres_personnes": anonymes}


def principal() -> int:
    publics = noms_publics()
    out = {}
    with httpx.Client(headers={"User-Agent": politesse.UA, "Accept": "application/json"}, timeout=120) as c:
        if not politesse.autorise(c, BASE + "/lookup"):
            print("::warning::OpenCheck : refusé par robots.txt ; rien collecté.")
            return 0
        for g in GROUPES:
            try:
                r = c.get(BASE + "/search", params={"q": g, "kind": "entity"})
                r.raise_for_status()
                cands = [x for x in (r.json().get("results") or r.json().get("hits") or []) if isinstance(x, dict)]
                cand = next((x for x in cands if x.get("lei")), None)
                if not cand:
                    out[g] = {"lei": None, "note": "aucun candidat avec LEI"}
                    print(f"{g} : aucun LEI", flush=True)
                    continue
                lei = cand["lei"]
                for essai in range(3):
                    lr = c.get(BASE + "/lookup", params={"lei": lei, "deepen_top": 3})
                    if lr.status_code == 429:
                        time.sleep(float((lr.json() or {}).get("retry_after_s", 60)))
                        continue
                    break
                lr.raise_for_status()
                corps = lr.json()
                d = detenteurs(enregistrements(corps), publics)
                signaux = corps.get("risk_signals") or []
                out[g] = {"lei": lei, "trouve": cand.get("name") or cand.get("legal_name"), **d,
                          "signaux": {k: sum(1 for s in signaux if s.get("kind") == k) for k in ("risk", "context")},
                          "sources_degradees": len(corps.get("degraded_sources") or []),
                          "licences": corps.get("license_notices")}
                print(f"{g} → {out[g]['trouve']} ({lei}) : {len(d['societes'])} sociétés détentrices, "
                      f"{len(d['personnes_publiques'])} personnes publiques, {d['autres_personnes']} autres", flush=True)
            except Exception as e:
                out[g] = {"erreur": type(e).__name__}
                print(f"::warning::OpenCheck {g} : {type(e).__name__}", flush=True)
            time.sleep(PAUSE)
    if not any(v.get("lei") for v in out.values()):
        print("::warning::OpenCheck : rien de reconnu ; rien écrit.")
        return 0
    SORTIE.parent.mkdir(parents=True, exist_ok=True)
    SORTIE.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
