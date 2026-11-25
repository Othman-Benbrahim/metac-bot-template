"""Recoupement chiffré des briefs (2026-11-25, décision d'auteur à 17 h 07 : « ok, let's go », étages 1 et 2).

Tout est calculé par le code, sans modèle de langue.

Étage 1, contexte chiffré : pour chaque compartiment d'un brief, les séries collectées de ce compartiment (traces
« collecte » avec un adaptateur), lues À LA DATE DU BRIEF (aucune valeur postérieure) : dernière valeur, sa date, son
âge en jours, variation depuis le point précédent, et si cette variation est anormale au regard de l'historique de la
série (écart robuste |z| ≥ 2, médiane et écart absolu médian des variations passées, au moins 8 variations).

Étage 2, recoupement des chiffres cités : un fait dont le chiffre se retrouve, à 5 % près, parmi les trois dernières
valeurs d'une série de ses compartiments (après prise en compte de « milliard », « million », « millier », « % »)
est marqué « cohérent avec la série X ». Sinon : « non recoupable ». Jamais « contredit » : unités et périmètres
diffèrent trop souvent pour qu'un écart prouve une erreur.

Lit briefs/journal.jsonl ; écrit registre/briefs-recoupement.json (une entrée par brief, clé = fichier du brief) et
registre/briefs-recoupement-inventaire.json (compartiments touchés par les briefs sans aucune série : où brancher).
"""
from __future__ import annotations

import datetime as dt
import json
import re
import statistics as st
import sys
from collections import Counter
from pathlib import Path

import adaptateurs as ad
import ecosystemes as ec

ICI = Path(__file__).resolve().parent
JOURNAL = ICI / "briefs" / "journal.jsonl"
SORTIE = ICI / "registre" / "briefs-recoupement.json"
INVENTAIRE = ICI / "registre" / "briefs-recoupement-inventaire.json"
MAX_SERIES = 3
TOLERANCE = 0.05
# séries d'attention médiatique (articles, récits, messages, consultations) : elles mesurent qu'on parle d'un sujet,
# pas l'état du monde. Gardées à part (une au plus) ; elles ne comptent pas comme recoupement.
ATTENTION = {"rss", "rss_famille", "rss_matiere", "rss_region", "rss_villes", "recit_russe", "telegram", "wikipedia",
             "openmeasures"}
ECHELLES = (("milliard", 1e9), ("billion", 1e9), ("md", 1e9), ("million", 1e6), ("millier", 1e3), ("mille", 1e3))


def series_par_compartiment() -> dict[str, list[tuple[str, str]]]:
    s = ec.assembler(ec.charger(ec.DOSSIER))
    out = {}
    for n in s["noeuds"]:
        tr = [(t["adaptateur"], t.get("source", "")) for t in n.get("traces") or []
              if isinstance(t, dict) and t.get("statut") == "collecte" and t.get("adaptateur")]
        out[n["id"]] = tr
    return out


def contexte(serie: list[tuple[str, float]], jour: str) -> dict | None:
    """Étage 1 : la série vue au jour du brief."""
    pts = [(d[:10], v) for d, v in serie if v is not None and d[:10] <= jour]
    if not pts:
        return None
    d, v = pts[-1]
    r = {"date": d, "valeur": v, "age_jours": (dt.date.fromisoformat(jour) - dt.date.fromisoformat(d)).days}
    if len(pts) >= 2:
        var = [b[1] - a[1] for a, b in zip(pts, pts[1:])]
        r["variation"] = var[-1]
        passe = var[:-1]
        if len(passe) >= 8:
            med = st.median(passe)
            mad = st.median(abs(x - med) for x in passe) * 1.4826
            if mad > 0:
                z = (var[-1] - med) / mad
                r["z"] = round(z, 2)
                r["anormal"] = abs(z) >= 2
    return r


def nombre(chiffre: str) -> float | None:
    """« 9 745 », « 4,6 % », « 1,2 milliard de dollars » → valeur (milliard → ×1e9 ; % gardé tel quel)."""
    t = (chiffre or "").lower().replace(" ", " ").replace("\xa0", " ")
    m = re.search(r"[-−]?\d{1,3}(?:[ .]\d{3})+(?:,\d+)?|[-−]?\d+(?:[.,]\d+)?", t)
    if not m:
        return None
    brut = m.group(0).replace("−", "-")
    if re.fullmatch(r"-?\d{1,3}(?:[ .]\d{3})+(?:,\d+)?", brut):
        brut = brut.replace(" ", "").replace(".", "")
    try:
        v = float(brut.replace(",", "."))
    except ValueError:
        return None
    reste = t[m.end():m.end() + 20]
    for mot, k in ECHELLES:
        if reste.strip().startswith(mot):
            return v * k
    return v


def recouper(valeur: float, serie: list[tuple[str, float]], jour: str) -> tuple[str, float] | None:
    """Étage 2 : la valeur se retrouve-t-elle (à 5 %) parmi les trois dernières valeurs connues au jour du brief ?"""
    pts = [(d[:10], v) for d, v in serie if v is not None and d[:10] <= jour][-3:]
    for d, v in reversed(pts):
        if v and abs(valeur - v) <= TOLERANCE * abs(v):
            return d, v
    return None


def traiter(lignes: list[dict], series: dict, lire=ad.lire, reg: Path = ad.REG) -> tuple[dict, Counter]:
    cache: dict = {}

    def serie(a):
        if a not in cache:
            try:
                cache[a] = lire(a, reg) or []
            except Exception:
                cache[a] = []
        return cache[a]

    out, sans = {}, Counter()
    for x in lignes:
        if x.get("statut") != "ok" or not x.get("fichier"):
            continue
        jour = x.get("jour") or ""
        comps = []
        for c in x.get("compartiments") or []:
            vus, attention = [], []
            for a, src in series.get(c, []):
                media = a.split(":")[0] in ATTENTION
                if (media and attention) or (not media and len(vus) >= MAX_SERIES):
                    continue
                ctx = contexte(serie(a), jour)
                if ctx:
                    (attention if media else vus).append({"adaptateur": a, "source": src[:160], **ctx})
            if not vus:
                sans[c] += 1
            comps.append({"compartiment": c, "series": vus, "attention": attention})
        faits = []
        for f in (x.get("brief") or {}).get("faits") or []:
            v = nombre(f.get("chiffre", ""))
            if v is None:
                continue
            verdict = {"chiffre": f.get("chiffre"), "verdict": "non recoupable"}
            for c in x.get("compartiments") or []:
                for a, src in series.get(c, []):
                    if a.split(":")[0] in ATTENTION:
                        continue
                    hit = recouper(v, serie(a), jour)
                    if hit:
                        verdict = {"chiffre": f.get("chiffre"), "verdict": "cohérent avec la série",
                                   "adaptateur": a, "source": src[:160], "date": hit[0], "valeur": hit[1]}
                        break
                if verdict["verdict"] != "non recoupable":
                    break
            faits.append(verdict)
        out[x["fichier"]] = {"jour": jour, "url": x.get("url"), "compartiments": comps, "chiffres": faits}
    return out, sans


def principal() -> int:
    lignes = []
    if JOURNAL.exists():
        for l in JOURNAL.read_text(encoding="utf-8").splitlines():
            try:
                lignes.append(json.loads(l))
            except Exception:
                continue
    out, sans = traiter(lignes, series_par_compartiment())
    SORTIE.write_text(json.dumps(out, ensure_ascii=False, indent=0), encoding="utf-8")
    INVENTAIRE.write_text(json.dumps({"genere_le": dt.date.today().isoformat(),
                                      "compartiments_sans_serie": sans.most_common()}, ensure_ascii=False, indent=1),
                          encoding="utf-8")
    n_ser = sum(1 for b in out.values() for c in b["compartiments"] if c["series"])
    n_comp = sum(len(b["compartiments"]) for b in out.values())
    n_ch = Counter(f["verdict"] for b in out.values() for f in b["chiffres"])
    print(f"{len(out)} briefs ; {n_ser}/{n_comp} compartiments avec au moins une série ; chiffres : {dict(n_ch)}")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
