"""Taux d'exécution des annonces de droits de douane (préenregistrement preenregistrements/taux-execution-annonces.md).

Lit registre/annonces/tirade-*.csv (dernière version) et, s'il existe, registre/annonces/federal-register-tarifs.jsonl.
Écrit registre/annonces/taux-execution.json et .md. Rien n'entre dans le bot.

    python analyse_annonces_tarifs.py [--aujourdhui AAAA-MM-JJ]
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import re
import sys
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

REG = Path(os.environ.get("ALPHABET_REGISTRE", "registre")) / "annonces"
TOUT_PAYS = {"all countries", "all foreign", "all trading partners", "all partners", "all foreign countries", "global",
             "all nations", "all", "worldwide", "every country", "foreign countries"}
TOUT_SECT = {"all goods", "all products", "all imports"}
MOIS = {m: i for i, m in enumerate(["january", "february", "march", "april", "may", "june", "july", "august",
                                     "september", "october", "november", "december"], 1)}
ANNONCES = {"Threatened", "Announced", "Threatened / Announced"}


def jeu(s: str) -> set[str]:
    return {x.strip().lower() for x in (s or "").split(";") if x.strip()}


def recoupe(a: set[str], b: set[str], tout: set[str]) -> bool:
    if not a or not b:
        return False
    return bool(a & tout or b & tout or a & b)


def couvre(annonce: set[str], acte: set[str], tout: set[str]) -> bool:
    """Règle v2 (2026-11-24, 12 h 45) : l'acte doit nommer la cible annoncée. Un acte général (« All countries »,
    « All goods ») ne vaut exécution que d'une annonce elle-même générale. En v1, un acte général recoupait tout :
    74 actes sur 99 étaient plus larges que la cible (l'acier pour tous « exécutait » une menace sur la Colombie)."""
    if not annonce or not acte:
        return False
    if annonce & tout:
        return bool(acte & tout) or True                      # annonce générale : tout acte de la même famille compte
    return bool(annonce & acte)


def meme_cible(x: dict, y: dict, regle: str = "v2") -> bool:
    if regle == "v1":
        return recoupe(jeu(x["countries"]), jeu(y["countries"]), TOUT_PAYS) and \
            recoupe(jeu(x["sectors"]), jeu(y["sectors"]), TOUT_SECT)
    return couvre(jeu(x["countries"]), jeu(y["countries"]), TOUT_PAYS) and \
        couvre(jeu(x["sectors"]), jeu(y["sectors"]), TOUT_SECT)


def date_annoncee(planned: str, jour: date) -> date | None:
    p = (planned or "").lower()
    m = re.search(r"(january|february|march|april|may|june|july|august|september|october|november|december)\s+(\d{1,2}),?\s+(\d{4})", p) \
        or re.search(r"(\d{1,2})\s+(january|february|march|april|may|june|july|august|september|october|november|december)\s+(\d{4})", p)
    if m:
        g = m.groups()
        mo, d, y = (g[0], g[1], g[2]) if g[0].isalpha() else (g[1], g[0], g[2])
        try:
            return date(int(y), MOIS[mo], int(d))
        except ValueError:
            return None
    if re.search(r"\b(immediate|immediately|today)\b", p):
        return jour
    return None


def taux_min(x: dict) -> float | None:
    vs = [float(v) for v in re.findall(r"(\d+(?:\.\d+)?)\s*%", x.get("rate") or "")]
    if x.get("rate_value"):
        try:
            vs.append(float(x["rate_value"]))
        except ValueError:
            pass
    return min(vs) if vs else None


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    c = (p + z * z / (2 * n)) / (1 + z * z / n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return (max(0.0, c - h), min(1.0, c + h))


def fr_dates(f: Path) -> list[date]:
    if not f.exists():
        return []
    out = []
    for l in f.read_text(encoding="utf-8").splitlines():
        d = json.loads(l)
        if d.get("type") == "Presidential Document" or d.get("requete") == "presidentiel":
            s = d.get("signing_date") or d.get("publication_date")
            if s:
                out.append(date.fromisoformat(s[:10]))
    return out


def classer(lignes: list[dict], aujourdhui: date, fr: list[date] | None, regle: str = "v2") -> list[dict]:
    lignes = sorted(lignes, key=lambda x: (x["date"], x["row_id"]))
    out = []
    for i, a in enumerate(lignes):
        if a["role"] not in ("first_statement", "modification") or a["event_type"] not in ANNONCES:
            continue
        j0 = date.fromisoformat(a["date"])
        prevue = date_annoncee(a["planned_for"], j0)
        acte = recul = None
        for b in lignes[i + 1:]:
            jb = date.fromisoformat(b["date"])
            if jb < j0 or jb > j0 + timedelta(days=365) or not meme_cible(a, b, regle):
                continue
            if b["role"] == "climbdown" and recul is None and acte is None:
                recul = b
            if b["event_type"].startswith("Implemented") and b["role"] != "climbdown":
                acte = b
                break
        r = {"row_id": a["row_id"], "date": a["date"], "type": a["event_type"], "role": a["role"],
             "canal": a["source_type"], "conditionnelle": a["conditional"] == "1", "pays": a["countries"],
             "secteurs": a["sectors"], "taux": a["rate"], "prevue": prevue.isoformat() if prevue else None,
             "lien": a["link"], "recul": recul["row_id"] if recul else None}
        if acte:
            ja = date.fromisoformat(acte["date"])
            r.update(acte=acte["row_id"], date_acte=acte["date"], delai=(ja - j0).days, taux_acte=acte["rate"])
            if fr is not None:
                r["verifie_fr"] = any(abs((d - ja).days) <= 3 for d in fr)
            ta, tb = taux_min(a), taux_min(acte)
            if tb is not None and ta is not None and tb < ta:
                r["classe"] = "appliquee_modifiee"
            elif recul:
                r["classe"] = "appliquee_en_retard"
            elif prevue is None:
                r["classe"] = "appliquee_sans_date_annoncee"
            elif ja <= prevue + timedelta(days=3):
                r["classe"] = "appliquee_a_la_date"
            else:
                r["classe"] = "appliquee_en_retard"
        elif recul:
            r["classe"] = "suspendue_ou_retiree"
        elif (prevue and prevue > aujourdhui) or (not prevue and (aujourdhui - j0).days < 90):
            r["classe"] = "en_attente"
        else:
            r["classe"] = "sans_suite"
        out.append(r)
    return out


def resume(ms: list[dict]) -> dict:
    jugees = [m for m in ms if m["classe"] != "en_attente"]
    c = Counter(m["classe"] for m in jugees)
    n = len(jugees)
    app = sum(v for k, v in c.items() if k.startswith("appliquee"))
    delais = sorted(m["delai"] for m in jugees if "delai" in m)
    return {"n_mesures": len(ms), "n_jugees": n, "classes": dict(c.most_common()),
            "part_appliquee": round(app / n, 3) if n else None,
            "ic95_appliquee": [round(x, 3) for x in wilson(app, n)],
            "delai_median_jours": delais[len(delais) // 2] if delais else None,
            "en_attente": sum(1 for m in ms if m["classe"] == "en_attente")}


def principal() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--aujourdhui", default=date.today().isoformat())
    ap.add_argument("--regle", default="v2", choices=["v1", "v2"])
    a = ap.parse_args()
    auj = date.fromisoformat(a.aujourdhui)
    fs = sorted(REG.glob("tirade-v*.csv"), key=lambda p: [int(x) for x in re.findall(r"\d+", p.stem)])
    if not fs:
        print("aucun fichier TiRADE")
        return 1
    lignes = list(csv.DictReader(fs[-1].open(encoding="utf-8")))
    frf = REG / "federal-register-tarifs.jsonl"
    fr = fr_dates(frf) if frf.exists() else None
    ms = classer(lignes, auj, fr, a.regle)
    groupes = {"toutes": ms,
               "menaces": [m for m in ms if "Threatened" in m["type"] and not m["conditionnelle"]],
               "annonces": [m for m in ms if m["type"] == "Announced" and not m["conditionnelle"]],
               "conditionnelles": [m for m in ms if m["conditionnelle"]]}
    for canal in sorted({m["canal"] for m in ms}):
        groupes[f"canal:{canal}"] = [m for m in ms if m["canal"] == canal and not m["conditionnelle"]]
    res = {"regle": a.regle, "source": fs[-1].name, "federal_register": frf.name if fr is not None else None, "aujourdhui": auj.isoformat(),
           "groupes": {k: resume(v) for k, v in groupes.items()}, "mesures": ms}
    (REG / f"taux-execution-{a.regle}.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    for k, v in res["groupes"].items():
        print(f"{k:32} n={v['n_mesures']:3} jugées={v['n_jugees']:3} appliquée={v['part_appliquee']} IC95={v['ic95_appliquee']} "
              f"délai médian={v['delai_median_jours']} {v['classes']}")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
