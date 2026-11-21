"""Essai à blanc AVANT de brancher l'ombre du point de départ C dans le bot (demande de l'auteur du 2026-11-21, 16 h 20 :
« il faut tester avant de brancher »). Aucun appel de modèle, rien n'est posté.

Sur les questions binaires OUVERTES du tournoi et du MiniBench : taux des semblables (S), règles rattachées par la carte
robot, traductions par le code, sondages collectés à la volée (mêmes règles que le banc), C. Sortie à relire à la main :
registre/mise-au-point/ombre-c-ouvertes.json et .md (une ligne par question, alertes de mise en forme en tête).

    python mise_au_point/ombre_c_ouvertes.py
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import bras_m

SORTIE = Path("registre") / "mise-au-point" / "ombre-c-ouvertes"


def questions_ouvertes() -> list[dict]:
    from forecasting_tools import BinaryQuestion, MetaculusClient
    c = MetaculusClient()
    out, vus = [], set()
    for cible in (c.CURRENT_AI_COMPETITION_ID, c.CURRENT_MINIBENCH_ID):
        for q in c.get_all_open_questions_from_tournament(cible):
            k = getattr(q, "id_of_question", None) or q.page_url
            fin = getattr(q, "scheduled_resolution_time", None) or getattr(q, "close_time", None)
            if k in vus or not isinstance(q, BinaryQuestion) or fin is None:
                continue
            vus.add(k)
            out.append({"id": str(k), "url": q.page_url, "titre": q.question_text,
                        "cloture": fin.astimezone(timezone.utc).date()})
    return out


def principal() -> int:
    auj = datetime.now(timezone.utc).date()
    lignes, qs = [], questions_ouvertes()
    print(f"{len(qs)} question(s) binaire(s) ouverte(s) : " + " | ".join(q["titre"][:80] for q in qs))
    for q in qs:
        try:
            p_s = bras_m.semblables(q["titre"], q["cloture"], auj)
            oc = bras_m.ombre_c(q["titre"], q["cloture"], auj, p_s) if p_s is not None else None
        except Exception as e:
            p_s, oc = None, {"erreur": f"{type(e).__name__}: {e}"[:300]}
        if oc:
            lignes.append({**{k: str(v) for k, v in q.items()}, "p_S": p_s, **oc})
    SORTIE.parent.mkdir(parents=True, exist_ok=True)
    SORTIE.with_suffix(".json").write_text(json.dumps({"date": auj.isoformat(), "lignes": lignes}, ensure_ascii=False,
                                                      indent=1, default=str), encoding="utf-8")
    md = [f"# Ombre C, essai à blanc sur les questions ouvertes ({auj})", "",
          f"{len(qs)} questions binaires ouvertes ; {len(lignes)} avec au moins une règle rattachée ; "
          f"{sum(1 for l in lignes if l.get('p_C') is not None)} avec une traduction.", ""]
    for l in sorted(lignes, key=lambda l: (not (l.get("sondages") or {}).get("alertes"), l["titre"])):
        s = l.get("sondages") or {}
        md.append(f"- {l['titre'][:110]}")
        md.append(f"  - S {l['p_S']:.3f} → C {l['p_C']:.3f}" if l.get("p_C") is not None and l.get("p_S") is not None
                  else f"  - S {l.get('p_S')} ; pas de traduction")
        md.append(f"  - règles : {l.get('regles_traduites') or l.get('regles_rattachees')}")
        if s:
            col = s.get("colonne_sujet")
            m = (s.get("moyennes") or {}).get(col) or {}
            md.append(f"  - sondages : {s.get('statut')} ; {s.get('page')} ; colonne « {col} » {m.get('moyenne')} % "
                      f"(n {m.get('n')}, dernier {m.get('dernier')}) ; total "
                      f"{sum(v['moyenne'] for v in (s.get('moyennes') or {}).values()):.0f} %")
            if s.get("alertes"):
                md.append(f"  - ALERTES : {s['alertes']}")
            if s.get("essais"):
                md.append(f"  - pages essayées : {s['essais'][:3]}")
    SORTIE.with_suffix(".md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md[:3]))
    return 0


if __name__ == "__main__":
    sys.exit(principal())
