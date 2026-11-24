"""Sondes de l'écosystème (preenregistrements/sondes-ecosysteme.md ; décisions de l'auteur du 2026-11-24, 21 h 14 à
21 h 24). Trois sondes parallèles, chacune lit une question et rend (d, sens) ; l'étalon k et l'état (actif, plafond)
viennent de ecosystemes/sondes-etat.json, recalculés par sondes_etat.py.

- relations : couche des relations internes avec échelles et objet (ecosysteme_couche) ;
- ponts : ponts « influence » entrants, sens MESURÉ (corrélation des variations mensuelles sur 12 mois) ;
- phase : cycles des fiches, part de l'horizon qui tombe dans la phase vulnérable.
"""
from __future__ import annotations

import datetime as dt
import json
import math
import re
from pathlib import Path

import ecosysteme_couche as ecc
import ecosysteme_objet as eo

ICI = Path(__file__).resolve().parent
import os
ETAT = Path(os.environ.get("ALPHABET_REGISTRE", ICI / "registre")) / "sondes-etat.json"   # mis à jour par le workflow de score
NOMS = ("relations", "ponts", "phase")
MOIS = {"janvier": 1, "février": 2, "fevrier": 2, "mars": 3, "avril": 4, "mai": 5, "juin": 6, "juillet": 7, "août": 8,
        "aout": 8, "septembre": 9, "octobre": 10, "novembre": 11, "décembre": 12, "decembre": 12}
PLAFOND_DEPART = 0.05


def _mensuel(L, jour: dt.date, mois: int = 12):
    debut = jour - dt.timedelta(days=31 * (mois + 1))
    m = {}
    for d, v in L:
        if debut <= d < jour:
            m[(d.year, d.month)] = v                       # dernière valeur du mois
    cles = sorted(m)
    return {cles[i]: m[cles[i]] - m[cles[i - 1]] for i in range(1, len(cles))}


def _corr(a, b):
    n = len(a)
    if n < 3:
        return None
    ma, mb = sum(a) / n, sum(b) / n
    sa = math.sqrt(sum((x - ma) ** 2 for x in a))
    sb = math.sqrt(sum((y - mb) ** 2 for y in b))
    return None if sa == 0 or sb == 0 else sum((x - ma) * (y - mb) for x, y in zip(a, b)) / (sa * sb)


class Sondes:
    def __init__(self, registre: Path | None = None):
        self.c = ecc.Couche(registre)
        self.ponts_entrants = {}
        for p in self.c.carte.s["ponts"]:
            if p.get("resolu") and p.get("type") == "influence":
                self.ponts_entrants.setdefault(p["vers"], []).append(p)
        self.cycles = self.c.carte.s["cycles"]

    def relations(self, titre, horizon, jour):
        L = self.c.lire(titre, horizon, jour, objet=True)
        if not L.get("direction") or L["sens"] is None:
            return None
        return {"d": L["direction"], "sens": L["sens"], "details": L["contributions"][:6]}

    def ponts(self, titre, horizon, jour):
        s = ecc.sens(titre)
        if s is None:
            return None
        comps, _ = self.c.carte.rattacher(titre)
        apports = []
        for c in sorted(comps):
            for p in self.ponts_entrants.get(c, []):
                a, b = self.c.serie_de(p["de"]), self.c.serie_de(p["vers"])
                if not a or not b or a == b or not eo.porte_sur(a, titre):
                    continue
                va, vb = _mensuel(self.c._lire(a), jour), _mensuel(self.c._lire(b), jour)
                k = sorted(set(va) & set(vb))
                if len(k) < 8:
                    continue
                r = _corr([va[x] for x in k], [vb[x] for x in k])
                if r is None or abs(r) < 0.3:
                    continue
                z = self.c.z(a, jour, 30)
                if z is None:
                    continue
                g = max(-3.0, min(3.0, z))
                apports.append({"de": p["de"], "vers": c, "serie": a, "r_12_mois": round(r, 3), "z": round(z, 2),
                                "apport": round((1 if r > 0 else -1) * g, 3)})
        if not apports:
            return None
        return {"d": round(sum(x["apport"] for x in apports) / len(apports), 4), "sens": s, "details": apports[:6]}

    def phase(self, titre, horizon, jour):
        comps, _ = self.c.carte.rattacher(titre)
        fin = jour + dt.timedelta(days=max(1, int(horizon)))
        meilleurs = []
        for y in self.cycles:
            ids = {f"{y['theme']}:{k}" for k in y.get("compartiments") or []}
            if not ids & set(comps):
                continue
            mois = {MOIS[m] for m in re.findall(r"[a-zéû]+", (y.get("phase_vulnerable") or "").lower()) if m in MOIS}
            if not mois:
                continue
            jours = (fin - jour).days
            dans = sum(1 for i in range(jours) if (jour + dt.timedelta(days=i)).month in mois)
            meilleurs.append({"cycle": f"{y['theme']}:{y['id']}", "mois": sorted(mois), "part": round(dans / jours, 3)})
        if not meilleurs:
            return None
        return {"d": max(x["part"] for x in meilleurs), "sens": 1, "details": meilleurs}

    def lire(self, titre: str, horizon: float, jour: dt.date) -> dict:
        out = {}
        for n in NOMS:
            try:
                r = getattr(self, n)(titre, horizon, jour)
            except Exception:
                r = None
            if r is not None and r["d"]:
                out[n] = r
        return out


def etat() -> dict:
    try:
        return json.loads(ETAT.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def appliquer(p: float, lecture: dict, E: dict | None = None) -> dict:
    """Déplacement total et part de chaque sonde active, bornés par les plafonds."""
    E = E if E is not None else etat()
    parts, plafonds = {}, []
    for n, l in lecture.items():
        s = (E.get("sondes") or {}).get(n) or {}
        if not s.get("actif", False) or not s.get("k"):
            continue
        cap = float(s.get("plafond", PLAFOND_DEPART))
        ps = ecc.deplacer(p, l["d"], l["sens"], float(s["k"]))
        parts[n] = {"p_sonde": round(min(max(ps, p - cap), p + cap), 4), "k": s["k"], "plafond": cap, "d": l["d"],
                    "sens": l["sens"]}
        plafonds.append(cap)
    if not parts:
        return {"p": p, "parts": {}}
    total = sum(v["p_sonde"] - p for v in parts.values())
    cap = max(plafonds)
    return {"p": round(min(max(p + total, p - cap), p + cap), 4), "parts": parts}
