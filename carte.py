"""Carte vivante : le schéma des écosystèmes rendu interprétable par le code (bot 0.10.317).

Décision de l'auteur, 2026-11-19, 4 h 33 : « d'une part les fiches, de l'autre leur adaptation pratique : une carte
globale des relations codée en Python, qu'on enrichira avec les acteurs et les variables qui apparaîtront après
observation ». Outil de COMPRÉHENSION, pas de prévision : les poids sont qualitatifs (faible, moyenne, forte), les
relations sont à vérifier ; rien n'entre dans le bot.

Trois usages :
- état : pour chaque compartiment qui a une trace branchée (adaptateur), sa dernière valeur et son ÉCART à son
  habitude (z : moyenne des 7 derniers jours observés contre les 90 précédents) — l'intensité observée ;
- propagation : un choc sur un ou plusieurs compartiments se transmet le long des relations (forme, signe, force,
  délai, règle d'intensité) et des ponts entre fiches ; on lit ce qui bouge, où, quand, dans quel sens ;
- voisinage : le déroulé d'un compartiment à k pas (la proxémie situationnelle).

    python carte.py --etat
    python carte.py --choc ormuz:navigation=-1 --horizon 120
    python carte.py --voisinage energie-mondiale:prix --pas 2
"""
from __future__ import annotations

import argparse
import heapq
import json
import re
import statistics
import sys
from pathlib import Path

import adaptateurs as ad
import ecosystemes as ec

POIDS_FORCE = {"faible": 0.3, "moyenne": 0.6, "forte": 1.0, "inconnue": 0.4}
SIGNE = {"+": 1.0, "-": -1.0, "0": 0.0, "±": None}            # None : sens indéterminé, seule l'ampleur se transmet
DELAIS = (("permanent", 0), ("minute", 0), ("heure", 0.2), ("jour", 2), ("semaine", 10), ("mois", 45),
          ("trimestre", 90), ("saison", 90), ("an", 365), ("décennie", 3650))
SEUIL_PROPAGATION = 0.05
AMPLEUR_MAX = 2.0          # un seuil franchi amplifie ; sans plafond, les boucles à seuil s'emballent sans fin
# Les axes dans la propagation (rappel de l'auteur, 4 h 34 : « tous les acteurs n'agissent pas à la même échelle »).
# Hypothèses de départ, à calibrer sur nos séries : chaque niveau d'échelle MONTÉ atténue l'effet (un navire ne fait
# pas un marché) sauf si la relation est à seuil (le petit qui fait basculer le grand) ; un effet qui DESCEND
# s'impose sans perte ; un compartiment lent montre le changement avec retard (une fraction de son temps propre).
ATTENUATION_MONTEE = 0.6
PART_TEMPS_PROPRE = 0.25


def delai_jours(texte: str | None) -> float:
    """Délai typique en jours, d'après le PREMIER ordre de grandeur écrit (« jours à semaines » → 2)."""
    t = (texte or "").lower()
    pos = [(t.find(m), j) for m, j in DELAIS if m in t]
    return min(pos)[1] if pos else 7.0


def facteur_echelle(taille_source: list | None, taille_cible: list | None, regle: str | None) -> float:
    """Montée d'échelle : ×0,6 par niveau franchi (de la taille la plus grande de la source à la plus petite de la
    cible), sauf relation à seuil ; descente ou même échelle : ×1."""
    if not taille_source or not taille_cible or regle == "seuil":
        return 1.0
    saut = taille_cible[0] - taille_source[1]
    return ATTENUATION_MONTEE ** saut if saut > 0 else 1.0


def passage_de_niveau(ampleur: float, org_source: str | None, org_cible: str | None, catalogue: dict,
                      regle: str | None) -> float:
    """Entre deux niveaux d'organisation différents, un effet ne passe entier que s'il dépasse l'inertie du niveau
    cible (« assez fort pour y provoquer un changement ») ; sinon il n'en passe qu'un cinquième. Même niveau, niveau
    inconnu ou relation à seuil déjà prise en compte : facteur 1."""
    if not org_source or not org_cible or org_source == org_cible or regle == "seuil":
        return 1.0
    inertie = float((catalogue.get(org_cible) or {}).get("inertie", 0.0))
    return 1.0 if abs(ampleur) >= inertie else 0.2


def retard_propre(vitesse_cible: list | None) -> float:
    """Un compartiment lent met une part de son temps propre à montrer un changement."""
    return PART_TEMPS_PROPRE * vitesse_cible[0] if vitesse_cible else 0.0


def multiplicateur(regle: str | None, intensite: float) -> float:
    """Comment la force d'une relation varie avec l'intensité observée (|z| de la source) ; 1 sans intensité connue."""
    i = abs(intensite)
    if regle == "proportionnelle":
        return 1 + 0.5 * i
    if regle == "seuil":
        return 0.3 if i < 2 else 1.5
    if regle == "saturation":
        return min(1 + 0.5 * i, 2.0)
    if regle == "hysteresis":
        return 1.0                       # demande une mémoire de l'état ; non modélisée en v0
    return 1.0


class Carte:
    def __init__(self, dossier: Path = ec.DOSSIER, reg: Path = ad.REG):
        self.fiches = ec.charger(dossier)
        erreurs = [e for f in self.fiches.values() for e in ec.valider(f)]
        if erreurs:
            raise ValueError("; ".join(erreurs))
        self.s = ec.assembler(self.fiches)
        self.reg = reg
        self.noeuds = {n["id"]: n for n in self.s["noeuds"]}
        self.niveaux = ec.niveaux(dossier / "niveaux.yaml")["niveaux"]
        self.sortants: dict[str, list[dict]] = {}
        for r in self.s["relations"]:
            self.sortants.setdefault(r["de"], []).append(r)
        for p in self.s["ponts"]:
            if not p["resolu"]:
                continue
            if p.get("type") == "meme":           # deux lectures du même phénomène : dans les deux sens, sans perte
                for a, b in ((p["de"], p["vers"]), (p["vers"], p["de"])):
                    self.sortants.setdefault(a, []).append({"de": a, "vers": b, "forme": "pont", "effet": "+",
                                                            "force": "forte", "delai": "permanent", "pont": True})
            else:                                 # influence : un sens, transmission partielle, sens indéterminé
                self.sortants.setdefault(p["de"], []).append({"de": p["de"], "vers": p["vers"], "forme": "pont", "effet": "±",
                                                              "force": "moyenne", "delai": "jours", "pont": "influence"})
        self._etat: dict[str, dict] | None = None

    def etat(self) -> dict[str, dict]:
        if self._etat is not None:
            return self._etat
        out = {}
        for nid, n in self.noeuds.items():
            for tr in n["traces"]:
                if not tr.get("adaptateur"):
                    continue
                try:
                    serie = ad.lire(tr["adaptateur"], self.reg)
                except Exception as e:
                    out.setdefault(nid, {})["erreur"] = f"{tr['adaptateur']} : {type(e).__name__}"
                    continue
                if len(serie) < 20:
                    continue
                v = [x for _, x in serie]
                recent, avant = v[-7:], v[-97:-7]
                sd = statistics.pstdev(avant) or 1e-9
                z = (statistics.mean(recent) - statistics.mean(avant)) / sd
                out[nid] = {"adaptateur": tr["adaptateur"], "dernier_jour": serie[-1][0], "derniere_valeur": round(v[-1], 4),
                            "moyenne_7j": round(statistics.mean(recent), 4), "moyenne_90j": round(statistics.mean(avant), 4),
                            "z": round(z, 2)}
                break
        self._etat = out
        return out

    def intensite(self, nid: str) -> float:
        return float((self.etat().get(nid) or {}).get("z") or 0.0)

    def propager(self, chocs: dict[str, float], horizon: float = 120.0) -> list[dict]:
        """Chocs signés sur des compartiments → effets attendus (compartiment, jour, ampleur, sens, chemin).
        Le sens « ? » veut dire : une relation ± a été traversée, la direction n'est plus déterminée."""
        tas = [(0.0, -abs(a), nid, a, True, [nid]) for nid, a in chocs.items()]
        heapq.heapify(tas)
        vus: dict[str, dict] = {}
        while tas:
            jour, _, nid, ampl, sens_connu, chemin = heapq.heappop(tas)
            if nid in vus or abs(ampl) < SEUIL_PROPAGATION or jour > horizon:
                continue
            vus[nid] = {"compartiment": nid, "jour": round(jour, 1), "ampleur": round(abs(ampl), 3),
                        "taille": self.noeuds.get(nid, {}).get("axes", {}).get("taille"),
                        "sens": ("hausse" if ampl > 0 else "baisse") if sens_connu else "?", "chemin": " → ".join(chemin)}
            for r in self.sortants.get(nid, []):
                s = SIGNE.get(r.get("effet"), None)
                if s == 0.0:
                    continue
                poids = POIDS_FORCE.get(r.get("force") or "inconnue", 0.4)
                regle = (r.get("intensite") or {}).get("regle") if isinstance(r.get("intensite"), dict) else None
                # l'intensité du moment : celle qu'on observe (|z| de la source), ou celle de l'effet qui arrive lui-même
                # (un choc assez fort franchit un seuil même là où aucune trace ne le mesure)
                poids *= multiplicateur(regle, max(abs(self.intensite(nid)), 2 * abs(ampl)))
                src, cib = self.noeuds.get(nid, {}).get("axes", {}), self.noeuds.get(r["vers"], {}).get("axes", {})
                if r.get("pont") is not True:
                    poids *= facteur_echelle(src.get("taille"), cib.get("taille"), regle)
                nouvelle = ampl * poids * (s if s is not None else 1.0)
                nouvelle = max(-AMPLEUR_MAX, min(AMPLEUR_MAX, nouvelle))
                if r.get("pont") is not True:
                    nouvelle *= passage_de_niveau(nouvelle, self.noeuds.get(nid, {}).get("organisation"),
                                                  self.noeuds.get(r["vers"], {}).get("organisation"), self.niveaux, regle)
                arrivee = jour + delai_jours(r.get("delai")) + (0 if r.get("pont") is True else retard_propre(cib.get("vitesse_jours")))
                heapq.heappush(tas, (arrivee, -abs(nouvelle), r["vers"], nouvelle,
                                     sens_connu and s is not None, chemin + [r["vers"]]))
        return sorted(vus.values(), key=lambda x: (x["jour"], -x["ampleur"]))

    def voisinage(self, nid: str, pas: int = 2) -> list[dict]:
        """Le déroulé d'un compartiment : tout ce qui l'atteint ou qu'il atteint en au plus `pas` relations."""
        entrants: dict[str, list[str]] = {}
        for a, rs in self.sortants.items():
            for r in rs:
                entrants.setdefault(r["vers"], []).append(a)
        out, front, vus = [], {nid}, {nid}
        for k in range(1, pas + 1):
            suivant = set()
            for x in front:
                for y in [r["vers"] for r in self.sortants.get(x, [])] + entrants.get(x, []):
                    if y not in vus:
                        vus.add(y)
                        suivant.add(y)
                        out.append({"compartiment": y, "pas": k, "trace": y in self.etat(), "z": self.intensite(y) or None,
                                    "taille": self.noeuds.get(y, {}).get("axes", {}).get("taille"),
                                    "acteurs": [f"{a['nom']} ({a.get('taille')})" for a in self.noeuds.get(y, {}).get("acteurs", [])]})
            front = suivant
        return out


def principal(args) -> int:
    c = Carte()
    if args.etat:
        print(json.dumps(c.etat(), ensure_ascii=False, indent=1))
    if args.choc:
        chocs = {}
        for x in args.choc:
            k, v = x.rsplit("=", 1)
            chocs[k] = float(v)
        for e in c.propager(chocs, args.horizon):
            print(f"j+{e['jour']:>5} {e['sens']:>6} {e['ampleur']:.2f}  {e['compartiment']:<34} taille {e['taille']}  {e['chemin']}")
    if args.voisinage:
        for e in c.voisinage(args.voisinage, args.pas):
            print(f"{e['pas']}  {e['compartiment']:<34} taille {e['taille']}  " + (f"z {e['z']}" if e["trace"] else "(pas de trace)")
                  + ("  · " + ", ".join(e["acteurs"]) if e["acteurs"] else ""))
    return 0


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("--etat", action="store_true")
    a.add_argument("--choc", nargs="*")
    a.add_argument("--horizon", type=float, default=120.0)
    a.add_argument("--voisinage")
    a.add_argument("--pas", type=int, default=2)
    sys.exit(principal(a.parse_args()))
