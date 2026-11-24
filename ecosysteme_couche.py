"""Couche écosystème (décision de l'auteur, 2026-11-24, 20 h 41 : « Oui, avec toutefois un avertissement, chaque écosystème
joue à différents niveaux : temps, vitesse, espace, taille à travers différentes échelles. Il faut absolument en tenir
compte. […] cette carte soit incomplète, […] il faudra la compléter, petit à petit »). Procédure :
preenregistrements/couche-ecosysteme.md, versée avant le calcul.

La carte donne la structure (quels compartiments comptent, dans quel sens) ; les séries donnent l'état. Pour une
question (titre, horizon en jours, date) :
1. rattachement : compartiments cibles (liste validée du chantier A, mise_au_point/lecture_mecanique.Carte) ;
2. amont : relations entrantes des cibles, avec effet « + » ou « − » (« ± » ignoré), retenues selon les ÉCHELLES :
   - temps : délai de la relation ≤ horizon (l'effet arrive avant l'échéance) ;
   - vitesse : compartiment amont de vitesse « années » ou plus lente écarté si l'horizon < 180 jours ;
   - espace : compartiment amont limité à des pays (geopolitique.pays) écarté si la question nomme des pays et
     qu'aucun n'y figure ;
   - taille : la règle d'intensité de la relation module l'effet (seuil et masse critique : |z| ≥ 2, sinon rien ;
     hystérésis : |z| ≥ 1,5 ; saturation : tanh(z) ; proportionnelle ou non écrite : z borné à ±3) ;
3. état de l'amont : première série collectée du compartiment ; z = variation sur la fenêtre W (délai de la relation,
   7 à 90 jours) rapportée aux variations sur W des deux années précédentes ; données antérieures à la date seulement ;
4. direction d = Σ force·signe(effet)·g(z) / Σ force, sur les relations qui ont une série (force 3/2/1) ;
5. sens du « oui » (lexique écrit, SENS_HAUT / SENS_BAS) : +1 si le oui correspond au compartiment qui monte,
   −1 s'il descend, sinon abstention ;
6. déplacement en log-odds = k·d·sens ; k est le seul paramètre, mesuré sur les questions résolues.
Ce que la carte ne peut pas lire est consigné (lacunes) pour la compléter.
"""
from __future__ import annotations

import bisect
import datetime as dt
import math
import re
import statistics
from pathlib import Path

import adaptateurs as ad
from mise_au_point.lecture_mecanique import DELAI_JOURS, FORCE, Carte

ICI = Path(__file__).resolve().parent
LENT = {"années", "année", "décennie", "décennies", "générations", "permanent", "décennie"}
SENS_HAUT = re.compile(r"\b(exceed\w*|above|over|higher|more than|at least|rise[sn]?|rising|increase[sd]?|reach\w*|"
                       r"surpass\w*|record|hike[sd]?|raise[sd]?|escalat\w*|attack\w*|strike[sd]?|invade[sd]?|invasion|"
                       r"war|resign\w*|ousted|collapse[sd]?|default\w*|recession|outbreak|spike[sd]?)\b", re.I)
SENS_BAS = re.compile(r"\b(below|under|less than|lower|fall[s]?|drop\w*|decline[sd]?|cut[s]?|decrease[sd]?|"
                      r"ceasefire|cease-fire|truce|peace|lift\w*|ease[sd]?|end[s]?|reopen\w*)\b", re.I)


def sens(titre: str) -> int | None:
    h, b = bool(SENS_HAUT.search(titre or "")), bool(SENS_BAS.search(titre or ""))
    if h == b:
        return None
    return 1 if h else -1


def _g(z: float, regle: str | None) -> float:
    if regle in ("seuil", "masse_critique"):
        return max(-3, min(3, z)) if abs(z) >= 2 else 0.0
    if regle == "hysteresis":
        return max(-3, min(3, z)) if abs(z) >= 1.5 else 0.0
    if regle == "saturation":
        return math.tanh(z)
    return max(-3.0, min(3.0, z))


class Couche:
    def __init__(self, registre: Path | None = None):
        self.carte = Carte()
        self.reg = registre or ICI / "registre"
        self.noeuds = {n["id"]: n for n in self.carte.s["noeuds"]}
        self._series, self._z = {}, {}

    def serie_de(self, comp: str) -> str | None:
        for t in self.noeuds.get(comp, {}).get("traces") or []:
            if isinstance(t, dict) and t.get("statut") == "collecte" and t.get("adaptateur"):
                return t["adaptateur"]
        return None

    def _lire(self, a: str):
        if a not in self._series:
            try:
                L = sorted((dt.date.fromisoformat(d[:10]), float(v)) for d, v in (ad.lire(a, self.reg) or [])
                           if v is not None)
            except Exception:
                L = []
            self._series[a] = L
        return self._series[a]

    def z(self, a: str, jour: dt.date, w: int) -> float | None:
        k = (a, jour, w)
        if k in self._z:
            return self._z[k]
        S = self._lire(a)
        jours = [d for d, _ in S]
        L = S[:bisect.bisect_left(jours, jour)]
        res = None
        if len(L) >= 30:
            dl = jours[:len(L)]

            def valeur(t):
                i = bisect.bisect_right(dl, t)
                return L[i - 1][1] if i else None
            fin = L[-1][0]
            dernier = valeur(fin)
            avant = valeur(fin - dt.timedelta(days=w))
            hist = []
            t = fin - dt.timedelta(days=w)
            debut = fin - dt.timedelta(days=730)
            while t - dt.timedelta(days=w) >= max(debut, L[0][0]):
                a1, a0 = valeur(t), valeur(t - dt.timedelta(days=w))
                if a1 is not None and a0 is not None:
                    hist.append(a1 - a0)
                t -= dt.timedelta(days=w)
            if dernier is not None and avant is not None and len(hist) >= 6:
                sd = statistics.pstdev(hist)
                if sd > 0 and (jour - fin).days <= max(45, w):          # séries mensuelles publiées avec retard
                    res = (dernier - avant - statistics.mean(hist)) / sd
        self._z[k] = res
        return res

    def lire(self, titre: str, horizon: float, jour: dt.date, objet: bool = False) -> dict:
        """`objet` (0.10.509) : une série ne compte que si le titre nomme ce qu'elle mesure (ecosysteme_objet)."""
        comps, pays = self.carte.rattacher(titre)
        lu = {"compartiments": sorted(comps), "pays": pays, "sens": sens(titre), "contributions": [], "lacunes": []}
        if not comps:
            lu["lacunes"].append("aucun compartiment rattaché")
            return lu
        num = den = 0.0
        for c in sorted(comps):
            entrants = self.carte.entrants.get(c, [])
            if not entrants:
                lu["lacunes"].append(f"{c} : aucune relation entrante")
            for r in entrants:
                if str(r.get("effet")) not in ("+", "-", "−"):
                    continue
                dj = DELAI_JOURS.get(str(r.get("delai") or "").strip())
                if dj is None or dj > horizon:                        # temps
                    continue
                amont = self.noeuds.get(r["de"], {})
                vit = str((amont.get("niveau") or {}).get("vitesse") or "")
                if horizon < 180 and any(m in vit for m in LENT):     # vitesse
                    continue
                pz = (amont.get("geopolitique") or {}).get("pays") or []
                if pays and pz and not set(pays) & set(pz):           # espace
                    continue
                a = self.serie_de(r["de"])
                if a is None:
                    lu["lacunes"].append(f"{r['de']} → {c} : amont sans série")
                    continue
                if objet:
                    import ecosysteme_objet as eo
                    if not eo.porte_sur(a, titre):
                        lu["lacunes"].append(f"{r['de']} → {c} : série hors de l'objet de la question ({a})")
                        continue
                w = int(min(90, max(7, dj)))
                zz = self.z(a, jour, w)
                if zz is None:
                    lu["lacunes"].append(f"{r['de']} → {c} : série sans état récent ({a})")
                    continue
                regle = (r.get("intensite") or {}).get("regle") if isinstance(r.get("intensite"), dict) else None
                f = FORCE.get(r.get("force"), 1)
                s = 1 if str(r.get("effet")) == "+" else -1
                g = _g(zz, regle)                                      # taille
                num += f * s * g
                den += f
                lu["contributions"].append({"de": r["de"], "vers": c, "effet": r.get("effet"), "delai": r.get("delai"),
                                            "force": r.get("force"), "regle": regle, "serie": a, "z": round(zz, 2),
                                            "apport": round(f * s * g, 3)})
        lu["direction"] = round(num / den, 4) if den else None
        if not den and not lu["lacunes"]:
            lu["lacunes"].append("aucune relation retenue aux échelles de la question (temps, vitesse, espace)")
        if den and lu["sens"] is None:
            lu["lacunes"].append("sens du oui illisible")
        return lu


def deplacer(p: float, direction: float | None, s: int | None, k: float) -> float:
    if direction is None or s is None or k == 0:
        return p
    p = min(max(p, 0.01), 0.99)
    return 1 / (1 + math.exp(-(math.log(p / (1 - p)) + k * direction * s)))
