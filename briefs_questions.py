"""Questions ouvertes touchées par un brief récent (2026-11-25, décision de l'auteur à 13 h 01 : les briefs servent de
sondes). Un brief des 7 derniers jours qui partage un compartiment avec une question ouverte la signale « fait nouveau
possible ». Rien ne change dans la prévision : c'est un signal pour l'auteur, affiché sur le tableau Metaculus de la
carte ; le bot ne reprévoit pas une question déjà prévue.

Compartiments d'une question : même règle que R-carte (dossier_interne.rattachement : termes du titre, jamais le pays
seul). Écrit registre/briefs-questions.json.
    uv run python briefs_questions.py
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

ICI = Path(__file__).resolve().parent
REG = ICI / "registre"
JOURS = 7


def _jsonl(f: Path) -> list[dict]:
    if not f.is_file():
        return []
    out = []
    for l in f.read_text(encoding="utf-8").splitlines():
        try:
            out.append(json.loads(l))
        except ValueError:
            pass
    return out


def questions_ouvertes(aujourdhui: str) -> dict[str, dict]:
    resolues = {str(x.get("question_id")) for x in _jsonl(REG / "issues.jsonl") + _jsonl(REG / "issues-autres.jsonl")}
    q = {}
    for x in _jsonl(REG / "journal-bot.jsonl") + _jsonl(REG / "journal-autres.jsonl"):
        i = str(x.get("question_id"))
        if not x.get("publie", True) or x.get("mode") == "test_questions" or i in resolues:
            continue
        if str(x.get("resolution_prevue") or "9999")[:10] < aujourdhui:
            continue
        q[i] = {"question_id": i, "titre": x.get("titre", ""), "url": x.get("url"), "echeance": str(x.get("resolution_prevue") or "")[:10]}
    return q


def croiser(questions: dict[str, dict], briefs: list[dict], rattacher) -> list[dict]:
    out = []
    for q in questions.values():
        comps, _ = rattacher(q["titre"])
        touches = [b for b in briefs if set(b.get("compartiments") or []) & comps]
        if touches:
            communs = sorted(set().union(*(set(b["compartiments"]) for b in touches)) & comps)
            out.append({**q, "compartiments": communs,
                        "briefs": [{"jour": b.get("jour"), "titre": b.get("brief", {}).get("titre"), "url": b.get("url"),
                                    "fichier": b.get("fichier")} for b in touches][:5]})
    return sorted(out, key=lambda x: (-len(x["briefs"]), x["echeance"]))


def principal() -> int:
    import dossier_interne as di
    aujourdhui = dt.date.today()
    depuis = (aujourdhui - dt.timedelta(days=JOURS)).isoformat()
    briefs = [b for b in _jsonl(ICI / "briefs" / "journal.jsonl") if b.get("statut") == "ok" and str(b.get("jour", "")) >= depuis]
    res = croiser(questions_ouvertes(aujourdhui.isoformat()), briefs, di.rattachement)
    (REG / "briefs-questions.json").write_text(json.dumps({"calcule_le": aujourdhui.isoformat(), "fenetre_jours": JOURS,
                                                           "questions": res}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(res)} question(s) ouverte(s) touchée(s) par un brief des {JOURS} derniers jours")
    for r in res[:10]:
        print(" -", r["question_id"], r["titre"][:80], "←", r["compartiments"])
    return 0


if __name__ == "__main__":
    raise SystemExit(principal())
