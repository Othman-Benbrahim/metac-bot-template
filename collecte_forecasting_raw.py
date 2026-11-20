"""Échantillon de mise au point : « forecasting_raw » (Halawi et al., 2024), Hugging Face, Apache-2.0 (bot 0.10.381).

50 343 questions résolues de 2015 à 2024 (Metaculus, Good Judgment Open, INFER, Polymarket, Manifold). On garde les
questions BINAIRES résolues, au format du registre de jugement : source, id, jeu (date d'ouverture), titre, horizon
(jours jusqu'à la clôture), resolue_le, issue. Ni le contexte, ni les prévisions de la foule, ni les liens ne sont
gardés (la foule n'est jamais une entrée). Décision de l'auteur, 2026-11-20, 02 h 25 : cet ensemble sert à METTRE AU
POINT les briques ; la confirmation se fait ailleurs (questions ForecastBench à venir).

    python collecte_forecasting_raw.py      # réseau (workflow) ; écrit registre/mise-au-point/questions.jsonl
"""
from __future__ import annotations

import io
import json
import re
import sys
from datetime import date
from pathlib import Path

PARQUET = "https://huggingface.co/api/datasets/YuehHanChen/forecasting_raw/parquet/default/train/{i}.parquet"
SORTIE = Path("registre") / "mise-au-point" / "questions.jsonl"
LICENCE = "forecasting_raw (Halawi et al., 2024), Hugging Face YuehHanChen/forecasting_raw, Apache-2.0"


def _jour(v) -> str | None:
    s = str(v or "")[:10]
    return s if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s) else None


def convertir(lignes: list[dict]) -> list[dict]:
    out, vus = [], set()
    for r in lignes:
        if str(r.get("question_type")) != "binary" or not r.get("is_resolved"):
            continue
        try:
            issue = float(r.get("resolution"))
        except (TypeError, ValueError):
            continue
        if issue not in (0.0, 1.0):
            continue
        debut, fin, res = _jour(r.get("date_begin")), _jour(r.get("date_close")), _jour(r.get("date_resolve_at"))
        if not debut or not (fin or res):
            continue
        cloture = min(x for x in (fin, res) if x)
        horizon = (date.fromisoformat(cloture) - date.fromisoformat(debut)).days
        if horizon < 0:
            continue
        ident = str(r.get("url") or "").rstrip("/").split("/")[-1] or str(len(out))
        cle = (r.get("data_source"), ident)
        if cle in vus:
            continue
        vus.add(cle)
        out.append({"source": str(r.get("data_source")), "id": ident, "jeu": debut, "titre": str(r.get("question") or "")[:300],
                    "horizon": horizon, "resolue_le": res or cloture, "issue": int(issue), "licence": LICENCE})
    return sorted(out, key=lambda x: (x["jeu"], x["source"], x["id"]))


def principal() -> int:
    import httpx
    import pyarrow.parquet as pq
    import politesse
    lignes = []
    with httpx.Client(headers={"User-Agent": politesse.UA}, timeout=120, follow_redirects=True) as c:
        if not politesse.autorise(c, PARQUET.format(i=0)):
            print("::warning::Hugging Face refuse cette adresse dans robots.txt ; rien collecté.")
            return 1
        for i in range(20):
            r = c.get(PARQUET.format(i=i))
            if r.status_code != 200:
                break
            lignes += pq.read_table(io.BytesIO(r.content)).to_pylist()
    if not lignes:
        print("::warning::aucun fichier lu")
        return 1
    xs = convertir(lignes)
    SORTIE.parent.mkdir(parents=True, exist_ok=True)
    SORTIE.write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in xs), encoding="utf-8")
    from collections import Counter
    print(f"{len(lignes)} lignes lues ; {len(xs)} questions binaires résolues gardées ; "
          f"{dict(Counter(x['source'] for x in xs))} ; {xs[0]['jeu']} → {xs[-1]['jeu']}")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
