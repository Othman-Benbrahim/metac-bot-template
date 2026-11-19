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
    python carte.py --simuler humain:stress_chronique=1 --horizon 365 [--maintenu]   (0.10.326, pas à pas)
    python carte.py --bascules                                                    (0.10.327, marges de bascule)
"""
from __future__ import annotations

import argparse
import heapq
import json
import re
import math
import statistics
import sys
from pathlib import Path

import adaptateurs as ad
import ecosystemes as ec

POIDS_FORCE = {"faible": 0.3, "moyenne": 0.6, "forte": 1.0, "inconnue": 0.4}
SIGNE = {"+": 1.0, "-": -1.0, "0": 0.0, "±": None}            # None : sens indéterminé, seule l'ampleur se transmet
DELAIS = (("permanent", 0), ("seconde", 0), ("minute", 0), ("heure", 0.2), ("jour", 2), ("semaine", 10), ("mois", 45),
          ("trimestre", 90), ("saison", 90), ("an", 365), ("décennie", 3650))
SEUIL_PROPAGATION = 0.05
AMPLEUR_MAX = 2.0          # un seuil franchi amplifie ; sans plafond, les boucles à seuil s'emballent sans fin
# Les axes dans la propagation (rappel de l'auteur, 4 h 34 : « tous les acteurs n'agissent pas à la même échelle »).
# Hypothèses de départ, à calibrer sur nos séries : chaque niveau d'échelle MONTÉ atténue l'effet (un navire ne fait
# pas un marché) sauf si la relation est à seuil (le petit qui fait basculer le grand) ; un effet qui DESCEND
# s'impose sans perte ; un compartiment lent montre le changement avec retard (une fraction de son temps propre).
ATTENUATION_MONTEE = 0.6
PART_TEMPS_PROPRE = 0.25
# 0.10.325 (Behave, Sapolsky) : une relation peut MODULER une relation à seuil au lieu de transmettre : l'intensité de
# sa source abaisse le seuil (seuil effectif = seuil − gain × intensité du modulateur, jamais sous SEUIL_PLANCHER).
# Valeurs de départ ; calibrer.py les remplace par la mesure quand les séries le permettent.
SEUIL_DEFAUT = 2.0
GAIN_DEFAUT = 0.5
SEUIL_PLANCHER = 0.5
REVISION = 1.5
REVISIONS_MAX = 2
# 0.10.326 (Schelling) : masse critique — seuils individuels distribués (mu, sigma en |z|) ; bornes 0,3 et 1,5 comme le
# seuil net, dont elle est la version continue (sigma → 0 redonne le seuil).
MU_DEFAUT = 2.0
INTENSITE_MAX = 4.0
# Comptes à rebours (jours jusqu'à la prochaine échéance) : des calendriers, pas des intensités (lus par calibrer.py aussi)
COMPTES_A_REBOURS = ("elections", "memoire", "feries_chine", "calendrier_nbs")
GAIN_PROPRE_MAX = 0.9      # simulation : une boucle sur soi seule ne fait pas basculer (il faut un circuit entre compartiments)
SIGMA_DEFAUT = 0.5
CALIBRATION = Path("registre/calibration.json")


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


def repartition(x: float, mu: float, sigma: float) -> float:
    """Part d'une population dont le seuil (loi normale mu, sigma) est franchi à l'intensité x."""
    if sigma <= 0:
        return 1.0 if x >= mu else 0.0
    return 0.5 * (1 + math.erf((x - mu) / (sigma * math.sqrt(2))))


def equilibres(mu: float, sigma: float, base: float = 0.0, n: int = 2001) -> dict:
    """Schelling, diagramme de la masse critique : la part qui agit demain est F(part qui agit aujourd'hui), F la
    répartition des seuils (exprimés en part de la population, 0 à 1), plus une base d'inconditionnels. Rend les
    équilibres stables, le point de bascule (équilibre instable) et le multiplicateur 1/(1 − pente) à l'équilibre haut."""
    g = lambda p: min(1.0, base + (1 - base) * repartition(p, mu, sigma)) - p
    pts = [i / (n - 1) for i in range(n)]
    racines = []
    for a, b in zip(pts, pts[1:]):
        if g(a) == 0 or g(a) * g(b) < 0:
            racines.append((a + b) / 2 if g(a) != 0 else a)
    if g(1.0) >= 0 and (not racines or racines[-1] < 1.0 - 1e-3):
        racines.append(1.0)
    stables, instables = [], []
    for r in racines:
        e = 1e-3
        pente = (g(min(1, r + e)) - g(max(0, r - e))) / (min(1, r + e) - max(0, r - e))
        (stables if pente < 0 or r in (0.0, 1.0) and g(r) == 0 else instables).append(round(r, 3))
    return {"stables": stables, "bascule": instables[0] if instables else None,
            "part_haute": max(stables) if stables else None}


def asymetrie(r: dict, ampleur: float) -> float:
    """Kahneman (théorie des perspectives) : une perte par rapport au point de référence pèse plus qu'un gain de même
    taille. Une relation peut porter « lambda_pertes » (départ 2) et « sens_perte » (+ ou −, le sens de la source qui
    est une perte) : l'effet est multiplié par lambda quand la source va dans ce sens. Le point de référence de la carte
    est l'habitude de chaque série (le z est déjà un écart à l'habitude)."""
    lam = r.get("lambda_pertes")
    if not lam or not ampleur:
        return 1.0
    perte = (ampleur > 0) == (r.get("sens_perte", "-") == "+")
    return float(lam) if perte else 1.0


def multiplicateur(regle: str | None, intensite: float, seuil: float = SEUIL_DEFAUT,
                   mu: float = MU_DEFAUT, sigma: float = SIGMA_DEFAUT) -> float:
    """Comment la force d'une relation varie avec l'intensité observée (|z| de la source) ; 1 sans intensité connue.
    Le seuil peut être abaissé par des modulateurs (0.10.325)."""
    i = abs(intensite)
    if regle == "proportionnelle":
        return 1 + 0.5 * i
    if regle == "seuil":
        return 0.3 if i < seuil else 1.5
    if regle == "masse_critique":
        return 0.3 + 1.2 * repartition(i, mu, sigma)
    if regle == "saturation":
        return min(1 + 0.5 * i, 2.0)
    if regle == "hysteresis":
        return 1.0                       # demande une mémoire de l'état ; non modélisée en v0
    return 1.0


class Carte:
    def __init__(self, dossier: Path = ec.DOSSIER, reg: Path = ad.REG, calibration: Path | None = CALIBRATION):
        self.fiches = ec.charger(dossier)
        erreurs = [e for f in self.fiches.values() for e in ec.valider(f)]
        if erreurs:
            raise ValueError("; ".join(erreurs))
        self.s = ec.assembler(self.fiches)
        self.reg = reg
        self.noeuds = {n["id"]: n for n in self.s["noeuds"]}
        self.niveaux = ec.niveaux(dossier / "niveaux.yaml")["niveaux"]
        # calibration mesurée (calibrer.py) : par relation « de>vers », remplace force, délai, signe, règle, seuil, gain
        self.calibration: dict[str, dict] = {}
        if calibration is not None and Path(calibration).exists():
            self.calibration = json.loads(Path(calibration).read_text(encoding="utf-8")).get("relations", {})
        self.persistance: dict[str, float] = {}
        if calibration is not None and Path(calibration).exists():
            comp = json.loads(Path(calibration).read_text(encoding="utf-8")).get("compartiments", {})
            self.persistance = {k: v["tau_jours"] for k, v in comp.items() if v.get("tau_jours")}
        self.sortants: dict[str, list[dict]] = {}
        self.modulateurs: dict[str, list[tuple[str, float]]] = {}
        for r in self.s["relations"]:
            cle = f"{r['de']}>{r['vers']}"
            par = r.get("parametres") or {}
            r = dict(r, cle=cle, seuil=float(par.get("seuil", SEUIL_DEFAUT)), mu=float(par.get("mu", MU_DEFAUT)),
                     sigma=float(par.get("sigma", SIGMA_DEFAUT)))
            if "lambda_pertes" in par:
                r["lambda_pertes"] = float(par["lambda_pertes"])
                r["sens_perte"] = "+" if float(par.get("sens_perte", -1)) > 0 else "-"
            m = self.calibration.get(cle) or {}
            # un signe mesuré contraire à la lecture ne retourne pas la relation : il la signale (« contredite ») pour
            # qu'on relise le mécanisme ; seule une mesure qui concorde (ou un sens écrit ±) remplace les valeurs écrites
            if m.get("verdict") == "significatif" and m.get("concorde") is False:
                r["contredite"] = True
            elif m.get("verdict") == "significatif":
                r.update(mesure=True, poids_mesure=m["poids"], delai_mesure=m["delai_jours"],
                         effet=m.get("signe", r.get("effet")), seuil=m.get("seuil", r["seuil"]),
                         mu=m.get("mu", r["mu"]), sigma=m.get("sigma", r["sigma"]))
                if m.get("lambda_pertes") and r.get("lambda_pertes") and m.get("lambda_significatif"):
                    r["lambda_pertes"] = m["lambda_pertes"]
                if m.get("regle"):
                    r["intensite"] = dict(r.get("intensite") or {"mesure": "calibration"}, regle=m["regle"])
            if r.get("module"):
                gain = float((r.get("parametres") or {}).get("gain", GAIN_DEFAUT))
                gm = (self.calibration.get(f"module:{r['de']}>{r['module']}") or {})
                if gm.get("verdict") == "significatif":
                    gain = gm["gain"]
                self.modulateurs.setdefault(r["module"], []).append((r["de"], gain))
                continue                          # une modulation ne transmet rien d'elle-même
            self.sortants.setdefault(r["de"], []).append(r)
        for p in self.s["ponts"]:
            if not p["resolu"]:
                continue
            if p.get("type") == "meme":           # deux lectures du même phénomène : dans les deux sens, sans perte
                for a, b in ((p["de"], p["vers"]), (p["vers"], p["de"])):
                    self.sortants.setdefault(a, []).append({"de": a, "vers": b, "forme": "pont", "effet": "+",
                                                            "force": "forte", "delai": "permanent", "pont": True})
            else:                                 # influence : un sens, transmission partielle, sens indéterminé
                lien = {"de": p["de"], "vers": p["vers"], "forme": "pont", "effet": "±", "force": "moyenne", "delai": "jours",
                        "pont": "influence", "cle": f"pont:{p['de']}>{p['vers']}"}
                m = self.calibration.get(lien["cle"]) or {}
                if m.get("verdict") == "significatif":   # 0.10.329 : la mesure donne le sens, la force et le délai
                    lien.update(effet=m["signe"], mesure=True, poids_mesure=m["poids"], delai_mesure=m["delai_jours"])
                self.sortants.setdefault(p["de"], []).append(lien)
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
                # fenêtres selon la fréquence de la série (0.10.322) : quotidienne → 7 derniers relevés contre les 90
                # précédents ; hebdomadaire → le dernier contre les 26 précédents ; mensuelle → le dernier contre les 24
                from datetime import date as _d
                ecarts = sorted((_d.fromisoformat(b[0][:10]) - _d.fromisoformat(a[0][:10])).days for a, b in zip(serie[-30:], serie[-29:]))
                pas = ecarts[len(ecarts) // 2] if ecarts else 1
                n_rec, n_base = (7, 90) if pas <= 3 else (1, 26) if pas <= 10 else (1, 24)
                recent, avant = v[-n_rec:], v[-(n_rec + n_base):-n_rec]
                sd = statistics.pstdev(avant) or 1e-9
                z = (statistics.mean(recent) - statistics.mean(avant)) / sd
                out[nid] = {"adaptateur": tr["adaptateur"], "dernier_jour": serie[-1][0], "derniere_valeur": round(v[-1], 4),
                            "moyenne_7j": round(statistics.mean(recent), 4), "moyenne_90j": round(statistics.mean(avant), 4),
                            "z": round(z, 2)}
                break
        self._etat = out
        return out

    def intensite(self, nid: str) -> float:
        """|z| plafonné à INTENSITE_MAX : une série dont l'habitude est presque nulle (collecte qui démarre) donne des z
        de plusieurs centaines qui ne disent rien de plus qu'« très au-dessus »."""
        e = self.etat().get(nid) or {}
        if str(e.get("adaptateur", "")).split(":")[0] in COMPTES_A_REBOURS:     # un calendrier n'est pas une intensité
            return 0.0
        z = float(e.get("z") or 0.0)
        return max(-INTENSITE_MAX, min(INTENSITE_MAX, z))

    def seuil_effectif(self, r: dict, atteints: dict[str, dict] | None = None) -> float:
        """Seuil d'une relation à seuil, abaissé par ses modulateurs : intensité observée (|z|) du modulateur, ou
        l'ampleur qu'un choc lui a donnée dans la propagation en cours (×2, comme pour l'intensité)."""
        s = r.get("seuil", SEUIL_DEFAUT)
        for src, gain in self.modulateurs.get(r.get("cle", ""), []):
            vu = (atteints or {}).get(src)
            i = max(abs(self.intensite(src)), 2 * vu["ampleur"] if vu else 0.0)
            s -= gain * i
        return max(SEUIL_PLANCHER, s)

    def _mult(self, r: dict, regle: str | None, i: float, atteints: dict | None) -> float:
        """Multiplicateur d'intensité ; les modulateurs abaissent le seuil, ou déplacent la moyenne des seuils (mu)
        d'une masse critique du même montant."""
        if regle == "seuil":
            return multiplicateur(regle, i, self.seuil_effectif(r, atteints))
        if regle == "masse_critique":
            baisse = r.get("seuil", SEUIL_DEFAUT) - self.seuil_effectif(r, atteints)
            return multiplicateur(regle, i, mu=max(SEUIL_PLANCHER, r.get("mu", MU_DEFAUT) - baisse), sigma=r.get("sigma", SIGMA_DEFAUT))
        return multiplicateur(regle, i)

    def simuler(self, chocs: dict[str, float], jours: int = 365, pas: int = 7, maintenu: bool = False) -> dict:
        """Simulation PAS À PAS (0.10.326 ; Schelling, le thermostat : une boucle de rappel AVEC retard dépasse sa cible
        et oscille ; une boucle de renforcement franchit ou non sa masse critique).
        Chaque compartiment tend vers une CIBLE, somme de ce que lui envoient ses relations (ampleur de la source au pas
        t − délai × poids × signe × multiplicateur d'intensité × échelle × passage de niveau), plus le choc s'il est
        maintenu ; il s'en approche d'une fraction pas/τ par pas, τ = son temps propre le plus court (premier ordre).
        Une boucle dont le gain dépasse 1 s'emballe jusqu'au plafond AMPLEUR_MAX : c'est une bascule, pas une erreur.
        Les relations ± (sens inconnu) et les modulations ne transmettent pas ; les ponts « meme » à moitié.
        Rend, pour chaque compartiment touché : pic, jour du pic, valeur finale, nombre de changements de sens."""
        n = jours // pas + 1
        x: dict[str, list[float]] = {nid: [a] for nid, a in chocs.items()}
        def val(nid, t):
            v = x.get(nid)
            return v[t] if v is not None and 0 <= t < len(v) else 0.0
        for t in range(1, n):
            cible: dict[str, float] = {nid: (a if maintenu else 0.0) for nid, a in chocs.items()}
            atteints = {k: {"ampleur": abs(v[t - 1])} for k, v in x.items()}
            for src in list(x):
                for r in self.sortants.get(src, []):
                    sg = SIGNE.get(r.get("effet"))
                    if not sg:
                        continue
                    lag = max(1, round((r["delai_mesure"] if r.get("mesure") else delai_jours(r.get("delai"))) / pas))
                    a = val(src, t - lag)
                    if abs(a) < 1e-4:
                        continue
                    if r.get("pont") is True:
                        poids = 0.5
                    else:
                        poids = r["poids_mesure"] if r.get("mesure") else POIDS_FORCE.get(r.get("force") or "inconnue", 0.4)
                        regle = (r.get("intensite") or {}).get("regle") if isinstance(r.get("intensite"), dict) else None
                        poids *= self._mult(r, regle, max(abs(self.intensite(src)), 2 * abs(a)), atteints)
                        poids *= asymetrie(r, a)
                        sa, sc = self.noeuds.get(src, {}).get("axes", {}), self.noeuds.get(r["vers"], {}).get("axes", {})
                        poids *= facteur_echelle(sa.get("taille"), sc.get("taille"), regle)
                        poids *= passage_de_niveau(a * poids, self.noeuds.get(src, {}).get("organisation"),
                                                   self.noeuds.get(r["vers"], {}).get("organisation"), self.niveaux, regle)
                    if r["vers"] == src:              # boucle sur soi : persistance renforcée, jamais seule à s'emballer
                        poids = min(poids, GAIN_PROPRE_MAX)
                    cible[r["vers"]] = cible.get(r["vers"], 0.0) + a * poids * sg
            for nid in set(cible) | set(x):
                vj = self.noeuds.get(nid, {}).get("axes", {}).get("vitesse_jours")
                alpha = min(1.0, pas / max(vj[0] if vj else pas, 1e-9)) if vj and vj[0] > 0 else 1.0
                tau = self.persistance.get(nid)               # retour vers l'habitude MESURÉ (calibrer.py, AR(1))
                if tau:
                    alpha = 1 - math.exp(-pas / tau)
                prec = val(nid, t - 1)
                v = prec + alpha * (cible.get(nid, 0.0) - prec)
                x.setdefault(nid, [0.0] * t).append(max(-AMPLEUR_MAX, min(AMPLEUR_MAX, v)))
        out = {}
        for nid, v in x.items():
            pic = max(range(len(v)), key=lambda i: abs(v[i]))
            if abs(v[pic]) < SEUIL_PROPAGATION:
                continue
            nz = [1 if a > 0 else -1 for a in v if abs(a) > SEUIL_PROPAGATION]
            out[nid] = {"pic": round(v[pic], 3), "jour_pic": pic * pas, "final": round(v[-1], 3),
                        "inversions": sum(1 for a, b in zip(nz, nz[1:]) if a != b),
                        "trajectoire": [round(a, 3) for a in v]}
        return dict(sorted(out.items(), key=lambda kv: -abs(kv[1]["pic"])))

    def marges_de_bascule(self, limite: int = 20) -> list[dict]:
        """Kuran (Private Truths, Public Lies, 1995) : l'opinion publique peut basculer sans que rien ne change dans les
        opinions privées, parce que les seuils d'expression sont cachés ; une révolution surprend parce qu'on ne voit
        pas la marge. Pour chaque relation à seuil ou à masse critique : seuil effectif aujourd'hui (abaissé par les
        modulateurs observés) moins l'intensité observée de la source. Une marge petite ou négative : une poudrière ;
        un petit choc suffit. Les relations sans trace à la source sont rendues avec marge inconnue (None), à la fin."""
        out = []
        for src, rs in self.sortants.items():
            for r in rs:
                regle = (r.get("intensite") or {}).get("regle") if isinstance(r.get("intensite"), dict) else None
                if regle not in ("seuil", "masse_critique") or r.get("pont"):
                    continue
                baisse = r.get("seuil", SEUIL_DEFAUT) - self.seuil_effectif(r, {})
                s_eff = self.seuil_effectif(r, {}) if regle == "seuil" else max(SEUIL_PLANCHER, r.get("mu", MU_DEFAUT) - baisse)
                trace = src in self.etat() and str(self.etat()[src].get("adaptateur", "")).split(":")[0] not in COMPTES_A_REBOURS
                i = abs(self.intensite(src)) if trace else None
                out.append({"relation": r.get("cle"), "regle": regle, "seuil_effectif": round(s_eff, 2),
                            "intensite": None if i is None else round(i, 2),
                            "marge": None if i is None else round(s_eff - i, 2),
                            "abaisse_par": [m for m, _ in self.modulateurs.get(r.get("cle", ""), [])]})
        out.sort(key=lambda d: (d["marge"] is None, d["marge"] if d["marge"] is not None else 0))
        return out[:limite]

    def verifier_identites(self, effets: list[dict] | dict) -> list[dict]:
        """Schelling, ch. 2 : une identité comptable tient quels que soient les motifs. Si tous les termes connus d'une
        identité vont dans le même sens et que le total part dans l'autre, la simulation est incohérente ; si le
        total n'a pas bougé, l'identité dit dans quel sens il doit aller."""
        if isinstance(effets, dict):
            sens = {k: (1 if v["final"] > 0 else -1) for k, v in effets.items()}
        else:
            sens = {e["compartiment"]: {"hausse": 1, "baisse": -1}.get(e["sens"], 0) for e in effets}
        out = []
        for idt in self.s.get("identites", []):
            contrib = {k: c * sens[k] for k, c in idt["termes"].items() if sens.get(k)}
            if not contrib or len(set(v > 0 for v in contrib.values())) > 1:      # termes contraires : rien à dire
                continue
            attendu = 1 if next(iter(contrib.values())) > 0 else -1
            obs = sens.get(idt["total"])
            if not obs:
                out.append({"identite": idt["total"], "verdict": "implique", "sens": "hausse" if attendu > 0 else "baisse",
                            "texte": idt.get("texte")})
            elif obs != attendu and len(contrib) == len(idt["termes"]):
                out.append({"identite": idt["total"], "verdict": "incoherent", "texte": idt.get("texte")})
        return out

    def propager(self, chocs: dict[str, float], horizon: float = 120.0) -> list[dict]:
        """Chocs signés sur des compartiments → effets attendus (compartiment, jour, ampleur, sens, chemin).
        Le sens « ? » veut dire : une relation ± a été traversée, la direction n'est plus déterminée."""
        tas = [(0.0, -abs(a), nid, a, True, [nid]) for nid, a in chocs.items()]
        heapq.heapify(tas)
        vus: dict[str, dict] = {}
        while tas:
            jour, _, nid, ampl, sens_connu, chemin = heapq.heappop(tas)
            if abs(ampl) < SEUIL_PROPAGATION or jour > horizon:
                continue
            # 0.10.325 : un effet faible arrivé tôt ne masque plus un effet fort arrivé plus tard par un autre chemin ;
            # un compartiment est revu si l'ampleur nouvelle dépasse REVISION × l'ancienne (au plus REVISIONS_MAX fois)
            if nid in vus and (abs(ampl) <= REVISION * vus[nid]["ampleur"] or vus[nid]["revisions"] >= REVISIONS_MAX
                               or nid in chemin[:-1]):
                continue
            vus[nid] = {"compartiment": nid, "jour": round(jour, 1), "ampleur": round(abs(ampl), 3),
                        "revisions": vus[nid]["revisions"] + 1 if nid in vus else 0,
                        "taille": self.noeuds.get(nid, {}).get("axes", {}).get("taille"),
                        "sens": ("hausse" if ampl > 0 else "baisse") if sens_connu else "?", "chemin": " → ".join(chemin)}
            for r in self.sortants.get(nid, []):
                s = SIGNE.get(r.get("effet"), None)
                if s == 0.0:
                    continue
                poids = r["poids_mesure"] if r.get("mesure") else POIDS_FORCE.get(r.get("force") or "inconnue", 0.4)
                regle = (r.get("intensite") or {}).get("regle") if isinstance(r.get("intensite"), dict) else None
                # l'intensité du moment : celle qu'on observe (|z| de la source), ou celle de l'effet qui arrive lui-même
                # (un choc assez fort franchit un seuil même là où aucune trace ne le mesure)
                poids *= self._mult(r, regle, max(abs(self.intensite(nid)), 2 * abs(ampl)), vus)
                poids *= asymetrie(r, ampl)
                src, cib = self.noeuds.get(nid, {}).get("axes", {}), self.noeuds.get(r["vers"], {}).get("axes", {})
                if r.get("pont") is not True:
                    poids *= facteur_echelle(src.get("taille"), cib.get("taille"), regle)
                nouvelle = ampl * poids * (s if s is not None else 1.0)
                nouvelle = max(-AMPLEUR_MAX, min(AMPLEUR_MAX, nouvelle))
                if r.get("pont") is not True:
                    nouvelle *= passage_de_niveau(nouvelle, self.noeuds.get(nid, {}).get("organisation"),
                                                  self.noeuds.get(r["vers"], {}).get("organisation"), self.niveaux, regle)
                arrivee = jour + (r["delai_mesure"] if r.get("mesure") else delai_jours(r.get("delai"))) + (0 if r.get("pont") is True else retard_propre(cib.get("vitesse_jours")))
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
    if getattr(args, "bascules", False):
        for m in c.marges_de_bascule(args.limite):
            print(f"marge {m['marge']!s:>6}  seuil {m['seuil_effectif']:<4} intensité {m['intensite']!s:<5} {m['regle']:<14} {m['relation']}")
    if getattr(args, "simuler", None):
        chocs = {k: float(v) for k, v in (x.rsplit("=", 1) for x in args.simuler)}
        for nid, v in list(c.simuler(chocs, int(args.horizon), maintenu=args.maintenu).items())[:args.limite]:
            print(f"pic {v['pic']:>6} j+{v['jour_pic']:<4} final {v['final']:>6} inversions {v['inversions']}  {nid}")
        print(json.dumps(c.verifier_identites(c.simuler(chocs, int(args.horizon), maintenu=args.maintenu)), ensure_ascii=False))
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
    a.add_argument("--bascules", action="store_true", help="relations à seuil les plus proches de basculer (Kuran)")
    a.add_argument("--simuler", nargs="*", help="simulation pas à pas : x=v ... (Schelling, thermostat)")
    a.add_argument("--maintenu", action="store_true", help="choc maintenu plutôt qu'impulsion")
    a.add_argument("--limite", type=int, default=20)
    sys.exit(principal(a.parse_args()))
