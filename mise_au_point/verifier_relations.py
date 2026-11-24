"""Couche écosystème, étape 1 : vérification des relations des fiches par leurs séries (décision de l'auteur,
2026-11-24, 18 h 54 : « Yep »). Procédure : preenregistrements/verification-relations.md, versée avant le calcul.

Relations testables : les deux compartiments (de, vers) ont une trace collectée avec adaptateur ; on prend la PREMIÈRE
série collectée de chaque compartiment. Effet « + » ou « − » seulement (« ± » : ambigu, non testable).
Délai → fréquence et décalages (périodes) :
  minutes, heures, heures à jours, jours → semaine, 0 à 1 ; jours à semaines → semaine, 0 à 8 ; semaines → semaine,
  1 à 8 ; jours à mois → semaine, 0 à 5 ; semaines à mois → mois, 0 à 3 ; mois → mois, 1 à 6 ; jours à saisons →
  mois, 0 à 6 ; saison(s) → mois, 3 à 9 ; saison à année, saisons à années → mois, 3 à 18 ; mois à années → mois,
  1 à 24 ; années, décennie(s), permanent, saisons à décennies → non testable (séries trop courtes).
Statistique : moyenne, sur les décalages, de la corrélation entre la variation de l'amont (période t) et la variation
de l'aval (période t + décalage) ; variations = différences des moyennes par période. n = périodes communes au plus
petit décalage ; n ≥ 20 exigé. Seuil : |r̄| > 2,5 / √n.
Verdict : « verifie » si r̄ a le signe de l'effet et dépasse le seuil ; « conteste » si signe opposé et seuil dépassé ;
« non_tranche » sinon ; « non_testable » (délai, effet ambigu, n < 20, série vide).
Sortie : registre/verification-relations.json. Aucun statut de fiche n'est modifié par ce calcul.
"""
from __future__ import annotations

import datetime as dt
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import adaptateurs as ad  # noqa: E402
import ecosystemes as ec  # noqa: E402

DELAIS = {"minutes": ("S", 0, 1), "heures": ("S", 0, 1), "heures à jours": ("S", 0, 1), "jours": ("S", 0, 1),
          "jours à semaines": ("S", 0, 8), "semaines": ("S", 1, 8), "jours à mois": ("S", 0, 5),
          "semaines à mois": ("M", 0, 3), "mois": ("M", 1, 6), "jours à saisons": ("M", 0, 6),
          "saison": ("M", 3, 9), "saisons": ("M", 3, 9), "saison à année": ("M", 3, 18),
          "saisons à années": ("M", 3, 18), "mois à années": ("M", 1, 24)}


def periode(d: str, f: str) -> str:
    j = dt.date.fromisoformat(d[:10])
    if f == "M":
        return f"{j.year}-{j.month:02d}"
    a, s, _ = j.isocalendar()
    return f"{a}-S{s:02d}"


def variations(L, f):
    acc = {}
    for d, v in L:
        try:
            acc.setdefault(periode(d, f), []).append(float(v))
        except (ValueError, TypeError):
            continue
    P = sorted(acc)
    moy = {p: sum(acc[p]) / len(acc[p]) for p in P}
    return {P[i]: moy[P[i]] - moy[P[i - 1]] for i in range(1, len(P))}, P[1:]


def suivant(p: str, k: int, f: str) -> str:
    if f == "M":
        a, m = map(int, p.split("-"))
        m += k
        a += (m - 1) // 12
        return f"{a}-{(m - 1) % 12 + 1:02d}"
    a, s = p.split("-S")
    lundi = dt.date.fromisocalendar(int(a), int(s), 1) + dt.timedelta(weeks=k)
    a2, s2, _ = lundi.isocalendar()
    return f"{a2}-S{s2:02d}"


def correlation(x, y):
    n = len(x)
    if n < 3:
        return None
    mx, my = sum(x) / n, sum(y) / n
    sx = math.sqrt(sum((a - mx) ** 2 for a in x))
    sy = math.sqrt(sum((b - my) ** 2 for b in y))
    if sx == 0 or sy == 0:
        return None
    return sum((a - mx) * (b - my) for a, b in zip(x, y)) / (sx * sy)


def principal() -> int:
    reg = Path("registre")
    F = ec.charger(ec.DOSSIER)
    series = {}
    for n, f in F.items():
        for c in f.get("compartiments", []):
            for t in c.get("traces") or []:
                if isinstance(t, dict) and t.get("statut") == "collecte" and t.get("adaptateur"):
                    series.setdefault((n, c["id"]), []).append(t["adaptateur"])
    cache, out = {}, []
    for n, f in F.items():
        for r in f.get("relations", []) or []:
            de, vers = (n, r.get("de")), (n, r.get("vers"))
            if de not in series or vers not in series:
                continue
            ligne = {"fiche": n, "de": r.get("de"), "vers": r.get("vers"), "effet": r.get("effet"),
                     "delai": r.get("delai"), "serie_de": series[de][0], "serie_vers": series[vers][0]}
            out.append(ligne)
            # règle ajoutée le 2026-11-24 (décision de l'auteur, 18 h 58) : même série, ou série et sa composante (même
            # source et même lieu, ex. portwatch:ormuz:*) = pas une relation testable
            a_, b_ = ligne["serie_de"], ligne["serie_vers"]
            if a_ == b_ or a_.split(":")[:2] == b_.split(":")[:2] and a_.split(":")[0] in ("portwatch",):
                ligne["verdict"], ligne["motif"] = "non_testable", "même série ou composante d'une même série"
                continue
            reg_d = DELAIS.get(str(r.get("delai") or "").strip())
            if str(r.get("effet")) not in ("+", "-", "−") or reg_d is None:
                ligne["verdict"] = "non_testable"
                ligne["motif"] = "effet ambigu" if reg_d else "délai trop long pour les séries"
                continue
            f_, l0, l1 = reg_d
            for a in (ligne["serie_de"], ligne["serie_vers"]):
                if a not in cache:
                    try:
                        cache[a] = ad.lire(a, reg) or []
                    except Exception:
                        cache[a] = []
            vx, _ = variations(cache[ligne["serie_de"]], f_)
            vy, _ = variations(cache[ligne["serie_vers"]], f_)
            rs, n0 = [], None
            for k in range(l0, l1 + 1):
                paires = [(vx[p], vy[q]) for p in vx if (q := suivant(p, k, f_)) in vy]
                if k == l0:
                    n0 = len(paires)
                c = correlation([a for a, _ in paires], [b for _, b in paires]) if len(paires) >= 20 else None
                if c is not None:
                    rs.append(c)
            ligne.update({"frequence": f_, "decalages": [l0, l1], "n": n0})
            if not rs or (n0 or 0) < 20:
                ligne["verdict"], ligne["motif"] = "non_testable", "moins de 20 périodes communes"
                continue
            rb = sum(rs) / len(rs)
            seuil = 2.5 / math.sqrt(n0)
            signe = 1 if str(r.get("effet")) == "+" else -1
            ligne.update({"r_moyen": round(rb, 4), "seuil": round(seuil, 4)})
            ligne["verdict"] = ("verifie" if rb * signe > seuil else "conteste" if rb * signe < -seuil else "non_tranche")
    resume = {}
    for l in out:
        resume[l["verdict"]] = resume.get(l["verdict"], 0) + 1
    Path("registre/verification-relations.json").write_text(
        json.dumps({"resume": resume, "relations": out}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(resume, ensure_ascii=False))
    for l in out:
        if l["verdict"] in ("verifie", "conteste"):
            print(l["verdict"], l["fiche"], l["de"], "→", l["vers"], l["effet"], l["delai"], l["r_moyen"], "n =", l["n"])
    return 0


if __name__ == "__main__":
    sys.exit(principal())
