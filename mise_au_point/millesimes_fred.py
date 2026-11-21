"""Couverture des fourchettes d'indicateurs lents jugée sur la PREMIÈRE PUBLICATION (millésimes ALFRED) au lieu des
chiffres révisés d'aujourd'hui (veille ML4T, chapitre 4, données « à date » ; décision de l'auteur du 2026-11-21,
19 h 14). Mesure descriptive, aucun modèle de langue, aucun réglage : elle dit si la couverture mesurée sur les chiffres
révisés (mise_au_point/indicateurs_lents_essai.py) était optimiste.

Même calcul que l'essai d'origine (indicateurs_lents.fourchette_suivante, fenêtre de 36 publications), deux fois :
- « révisé » : la série d'aujourd'hui (comme l'essai d'origine) ;
- « première publication » : chaque mois pris à sa valeur annoncée la première fois (ALFRED, output_type=4). Pour
  l'inflation sur un an, le mois courant et le mois d'il y a douze mois sont tous deux pris en première publication
  (approximation : le bot de l'époque voyait le mois d'il y a douze mois déjà révisé).
Clé : secret FRED_API_KEY (API documentée, clé personnelle).

    python mise_au_point/millesimes_fred.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import indicateurs_lents as il

SORTIE = Path("registre") / "mise-au-point" / "millesimes-fred.json"
API = "https://api.stlouisfed.org/fred/series/observations"
SERIES = {"UNRATE": "chômage", "UMCSENT": "confiance des ménages", "CPIAUCSL": "inflation sur un an",
          "CPILFESL": "inflation sous-jacente sur un an"}


def observations(c, cle: str, serie: str, premiere: bool) -> list[tuple[str, float]]:
    p = {"series_id": serie, "api_key": cle, "file_type": "json", "observation_start": "1990-01-01"}
    if premiere:
        p.update({"realtime_start": "1776-07-04", "realtime_end": "9999-12-31", "output_type": 4})
    r = c.get(API, params=p)
    r.raise_for_status()
    out = {}
    for o in r.json().get("observations", []):
        try:
            out.setdefault(o["date"], float(o["value"]))
        except (KeyError, ValueError):
            continue
    return sorted(out.items())


def couverture(x: list[float]) -> dict:
    n = c80 = c60 = 0
    for t in range(19, len(x) - 1):
        f = il.fourchette_suivante(x[: t + 1])
        if not f:
            continue
        q = dict(f)
        n += 1
        c80 += q[0.1] <= x[t + 1] <= q[0.9]
        c60 += q[0.2] <= x[t + 1] <= q[0.8]
    return {"n": n, "couverture_80": round(c80 / n, 3) if n else None, "couverture_60": round(c60 / n, 3) if n else None}


def serie_calcul(obs: list[tuple[str, float]], cle: str) -> list[float]:
    if cle in ("CPIAUCSL", "CPILFESL"):
        d = dict(obs)
        out = []
        for j, v in obs:
            a = f"{int(j[:4]) - 1}{j[4:]}"
            if a in d:
                out.append(100 * (v / d[a] - 1))
        return out
    return [v for _, v in obs]


def principal() -> int:
    import httpx
    cle = os.environ.get("FRED_API_KEY", "").strip()
    if not cle:
        print("FRED_API_KEY absent")
        return 1
    res, tot = {}, {"revise": [0, 0, 0], "premiere": [0, 0, 0]}
    with httpx.Client(timeout=60) as c:
        for s, nom in SERIES.items():
            r = {}
            for mode in ("revise", "premiere"):
                obs = observations(c, cle, s, mode == "premiere")
                cv = couverture(serie_calcul(obs, s))
                r[mode] = {**cv, "mois": len(obs), "dernier": obs[-1][0] if obs else None}
                if cv["n"]:
                    t = tot[mode]
                    t[0] += cv["n"]; t[1] += round(cv["couverture_80"] * cv["n"]); t[2] += round(cv["couverture_60"] * cv["n"])
            res[nom] = r
    ens = {m: {"n": t[0], "couverture_80": round(t[1] / t[0], 3), "couverture_60": round(t[2] / t[0], 3)}
           for m, t in tot.items() if t[0]}
    out = {"ensemble": ens, "series": res,
           "note": "attendu 0,80 et 0,60 ; « revise » = chiffres d'aujourd'hui (comme l'essai d'origine), « premiere » = "
                   "valeurs à leur première publication (ALFRED)"}
    SORTIE.parent.mkdir(parents=True, exist_ok=True)
    SORTIE.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(principal())
