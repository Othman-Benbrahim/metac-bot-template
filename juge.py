"""Juge informé (preenregistrements/dossier-interne.md, § 5 et § 5 bis ; validé par l'auteur le 2026-11-24, 22 h 12).
Après le sceau du bras A, le modèle reçoit le dossier interne, la recherche et le p du bras A ; il rend un objet fermé :
garder la mesure, ou s'en écarter pour un motif de la liste avec une preuve vérifiable. Le code borne et rejette.
"""
from __future__ import annotations

import datetime as dt
import json
import re

import sources_preuve as sp

MOTIFS = ("fait_nouveau_source", "brique_hors_domaine", "critere_resolution")
PLAFOND = 0.10                                         # décision de l'auteur : 10 points


def consigne(D: dict, recherche: str, p_A: float, p_mesure: float, criteres: str) -> str:
    x = {k: v for k, v in D.items() if k != "empreinte"}
    return f"""You are the informed judge of a forecasting bot. Below is the INTERNAL DOSSIER (measured, sourced facts
built by code), the research, the model-alone forecast (arm A) and the MEASURE that will be posted unless you justify a
departure. You may depart from the measure only for one of these motives:
- "fait_nouveau_source": a dated fact, published after the measure's data, that changes the outcome; give EVERY source
  you found for it (several independent sources are required; a single source is rejected);
- "brique_hors_domaine": the coded rule in "briques" does not apply to this question (quote the words of the question or
  of its resolution criteria that put it outside the rule's mechanism);
- "critere_resolution": the resolution criteria make the measure wrong (quote the criterion verbatim).
Any departure is capped at 10 percentage points, less if the evidence is weaker. If no motive applies, keep the measure.

INTERNAL DOSSIER:
{json.dumps(x, ensure_ascii=False, default=str)}

RESOLUTION CRITERIA:
{criteres}

ARM A (model alone): {p_A:.3f}
MEASURE: {p_mesure:.3f}

RESEARCH:
{recherche}

Answer with ONE JSON object and nothing else:
{{"decision": "mesure"}}
or
{{"decision": "ecart", "motif": "fait_nouveau_source" | "brique_hors_domaine" | "critere_resolution",
  "preuve": [{{"url": "...", "date": "YYYY-MM-DD"}}, ...]  (fait_nouveau_source)  or  "verbatim quote"  (other motives),
  "p_juge": 0.xx}}"""


def _json(rep: str) -> dict | None:
    m = re.search(r"\{.*\}", rep or "", re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except ValueError:
        return None


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").lower()).strip()


def analyser(rep: str, D: dict, recherche: str, p_mesure: float, criteres: str, aujourdhui: dt.date,
             lecteur=sp.lire_page) -> dict:
    """Décision bornée par le code. Rend p_poste, la décision admise et, en cas de rejet, son motif."""
    out = {"p_mesure": p_mesure, "p_poste": p_mesure, "decision": "mesure", "rejet": None}
    x = _json(rep)
    if not x or x.get("decision") not in ("mesure", "ecart"):
        out["rejet"] = "reponse_illisible"
        return out
    if x["decision"] == "mesure":
        return out
    motif, preuve = x.get("motif"), x.get("preuve")
    out.update({"motif": motif, "preuve": preuve})
    try:
        p_juge = float(x.get("p_juge"))
    except (TypeError, ValueError):
        out["rejet"] = "p_juge_absent"
        return out
    if motif not in MOTIFS:
        out["rejet"] = "motif_hors_liste"
        return out
    if motif == "fait_nouveau_source":
        f = sp.force(preuve if isinstance(preuve, list) else [], recherche, D["question"]["titre"], aujourdhui, lecteur)
        out["force"] = f
        marge = min(PLAFOND, f["marge"])
    else:
        q = _norm(preuve if isinstance(preuve, str) else "")
        texte = _norm(D["question"]["titre"] + " " + (criteres or ""))
        if len(q) < 12 or q not in texte:
            out["rejet"] = "citation_introuvable"
            return out
        if motif == "brique_hors_domaine" and not isinstance(D.get("briques"), list):
            out["rejet"] = "aucune_brique"
            return out
        marge = PLAFOND
    if marge <= 0:
        out["rejet"] = "preuve_insuffisante"
        return out
    p = min(max(p_juge, p_mesure - marge), p_mesure + marge)
    out.update({"decision": "ecart", "marge": marge, "p_juge": p_juge, "p_poste": round(min(0.99, max(0.01, p)), 4)})
    return out


# Règle d'arrêt (§ 6) : log E = Σ log(p_posté(issue) / p_mesure(issue)) sur les questions résolues où le juge s'est
# écarté (dernière ligne par question) ; log E ≤ −ln 20 → marge fermée (on poste la mesure) ; élargissement seulement
# par décision de l'auteur. Calculé par le workflow « Score du bot alphabet » (python juge.py).
import math
import os
from pathlib import Path

REG = Path(os.environ.get("ALPHABET_REGISTRE", Path(__file__).resolve().parent / "registre"))
ETAT = REG / "juge-etat.json"


def etat() -> dict:
    try:
        return json.loads(ETAT.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def e_valeur(reg: Path = REG) -> dict:
    issues, dernier = {}, {}
    f = reg / "issues.jsonl"
    if f.exists():
        for l in f.read_text(encoding="utf-8").splitlines():
            if l.strip():
                x = json.loads(l)
                if "issue" in x:
                    issues[str(x["question_id"])] = int(x["issue"])
    f = reg / "journal-juge.jsonl"
    if f.exists():
        for l in f.read_text(encoding="utf-8").splitlines():
            if l.strip():
                x = json.loads(l)
                dernier[str(x["question_id"])] = x
    le, n = 0.0, 0
    for q, x in dernier.items():
        if q not in issues or (x.get("juge") or {}).get("decision") != "ecart":
            continue
        y = issues[q]
        pp, pm = (min(max(float(x[k]), .001), .999) for k in ("p_poste", "p_mesure"))
        le += math.log((pp if y else 1 - pp) / (pm if y else 1 - pm))
        n += 1
    return {"log_e": round(le, 4), "ecarts_resolus": n}


if __name__ == "__main__":
    avant = etat()
    ev = e_valeur()
    ferme = bool(avant.get("ferme")) or ev["log_e"] <= -math.log(20)
    E = {"calcule_le": dt.date.today().isoformat(), "ferme": ferme, "plafond": PLAFOND, **ev,
         "procedure": "preenregistrements/dossier-interne.md"}
    ETAT.write_text(json.dumps(E, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(E, ensure_ascii=False, indent=1))
