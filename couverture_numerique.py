"""Couverture des fourchettes du bot sur les questions numériques et de date (bot 0.10.293).

Décision d'auteur du 2026-11-18, 20 h 52 (« oui, aux deux »). Préenregistrement : preenregistrements/couverture-numerique.md.
Suivi DESCRIPTIF, sans appel à un modèle, sans aucun effet sur ce que le bot poste (décision du 2026-11-18, 19 h 40 :
rien ne change côté Metaculus avant le tournoi).

Pour chaque question numérique ou de date résolue (registre/issues-autres.jsonl, rempli par le score quotidien), on
situe la valeur réelle dans la PREMIÈRE distribution postée par le bot (centiles déclarés 10, 20, 40, 60, 80, 90 de
registre/journal-autres.jsonl, interpolation linéaire entre centiles). Une fourchette bien calibrée laisse 10 % des
valeurs sous le centile 10, 10 % au-dessus du centile 90, 80 % entre les deux.

    python couverture_numerique.py
"""
from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path

REGISTRE = Path("registre")
SORTIE = REGISTRE / "couverture-numerique.json"
CASES = [(0.0, 0.1), (0.1, 0.2), (0.2, 0.4), (0.4, 0.6), (0.6, 0.8), (0.8, 0.9), (0.9, 1.0)]
N_ALERTE = 30
EXCLUES = {"annulled", "ambiguous", ""}


def _lignes(f: Path) -> list[dict]:
    return [json.loads(l) for l in f.read_text(encoding="utf-8").splitlines() if l.strip()] if f.is_file() else []


def valeur(issue: str, prev: dict) -> float | str | None:
    """Valeur réelle dans l'unité des centiles ; « bas » / « haut » si hors des bornes de la question ; None sinon."""
    s = str(issue or "").strip().lower()
    if s in EXCLUES:
        return None
    if s in ("below_lower_bound", "below lower bound"):
        return "bas"
    if s in ("above_upper_bound", "above upper bound"):
        return "haut"
    try:
        return float(s)
    except ValueError:
        pass
    if prev.get("is_date"):
        try:
            d = datetime.fromisoformat(str(issue).replace("Z", "+00:00"))
            return (d if d.tzinfo else d.replace(tzinfo=timezone.utc)).timestamp()
        except ValueError:
            return None
    return None


def rang(v: float | str, centiles: list[tuple[float, float]]) -> float:
    """Rang de la valeur dans la distribution déclarée (0 à 1), interpolé entre centiles ; queues : 0,05 et 0,95."""
    if v == "bas":
        return 0.05
    if v == "haut":
        return 0.95
    ps = sorted(centiles)
    if v < ps[0][1]:
        return 0.05
    if v > ps[-1][1]:
        return 0.95
    for (p0, v0), (p1, v1) in zip(ps, ps[1:]):
        if v0 <= v <= v1:
            return p0 if v1 == v0 else p0 + (p1 - p0) * (v - v0) / (v1 - v0)
    return 0.5


def binom_sup(k: int, n: int, p: float) -> float:
    """P(X ≥ k), X ~ Binomiale(n, p) : probabilité d'au moins k valeurs hors fourchette si le bot était calibré."""
    return sum(math.comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(k, n + 1))


def calculer(journal: list[dict], issues: list[dict]) -> dict:
    premiere: dict[str, dict] = {}
    for x in sorted(journal, key=lambda x: x.get("horodatage", "")):
        if x.get("type") in ("numerique", "date") and isinstance(x.get("prediction"), dict):
            premiere.setdefault(x["question_id"], x)
    lignes = []
    for i in issues:
        x = premiere.get(i["question_id"])
        if not x:
            continue
        prev = x["prediction"]
        cent = [(float(c["percentile"]), float(c["value"])) for c in prev.get("declared_percentiles") or []]
        v = valeur(i.get("issue"), prev)
        if v is None or len(cent) < 2:
            continue
        lignes.append({"question_id": i["question_id"], "type": x["type"], "rang": round(rang(v, cent), 4)})
    n = len(lignes)
    hors = sum(1 for l in lignes if l["rang"] < 0.1 or l["rang"] > 0.9)
    out = {"questions_resolues": n, "note": "première distribution postée ; attendu : 10 % sous p10, 80 % entre p10 et "
                                            "p90, 10 % au-dessus de p90",
           "sous_p10": sum(1 for l in lignes if l["rang"] < 0.1), "au_dessus_p90": sum(1 for l in lignes if l["rang"] > 0.9),
           "dans_p10_p90": n - hors,
           "cases": {f"{a:.1f}-{b:.1f}": {"n": sum(1 for l in lignes if a <= l["rang"] < b or (b == 1.0 and l["rang"] == 1.0)),
                                          "attendu": round((b - a) * n, 1)} for a, b in CASES},
           "detail": lignes}
    if n:
        out["part_hors_fourchette"] = round(hors / n, 3)
        out["p_valeur_trop_etroit"] = round(binom_sup(hors, n, 0.2), 4)
    out["verdict"] = ("en attente (moins de 30 questions résolues)" if n < N_ALERTE else
                      "fourchettes trop étroites (signal préenregistré)" if hors / n > 0.3 and out["p_valeur_trop_etroit"] < 0.05
                      else "pas de signal de fourchettes trop étroites")
    return out


def principal() -> int:
    r = calculer(_lignes(REGISTRE / "journal-autres.jsonl"), _lignes(REGISTRE / "issues-autres.jsonl"))
    r["calcule_le"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    SORTIE.write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in r.items() if k != "detail"}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(principal())
