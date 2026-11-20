"""Décompte des questions par structure (bot 0.10.378, ombre).

Pour savoir où porter l'effort : combien de questions résolues de Metaculus (registre/jugement-questions.jsonl,
proxy du tournoi) relèvent de chaque structure. Classement par mots du titre, dans un ordre fixe ; heuristique
déclarée, sans modèle de langue, sans lire les issues. `python structures_questions.py` écrit
registre/structures-questions.md.
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

REG = Path("registre")
REGLES = [
    ("course électorale", r"\belection|primary|primaries|nominat|by-?election|referendum|mayoral|gubernatorial|"
                          r"\bseats?\b|prime minister after|next (prime minister|president|chancellor)"),
    ("compétition (sport, prix, classements)", r"\b(win|wins|champion|championship|cup|league|grand prix|medal|oscar|"
                          r"award|nobel|eurovision|ballon d'or|super bowl|world series|final|tournament|top \d+|rank)\b"),
    ("maintien", r"\b(remain|still|continue to|stay|leave office|resign|step down|be removed|out as|cease to be|"
                 r"be (the )?(president|prime minister|ceo|leader|chair))\b"),
    ("événement rare", r"\b(attack|strike|invade|invasion|war\b|coup|die|death|killed|assassinat|earthquake|"
                       r"eruption|pandemic|outbreak|default|collapse|nuclear (test|weapon)|explosion|blockade|seize)"),
    ("seuil (quantité)", r"((above|below|exceed|at least|more than|less than|fewer than|greater than|higher than|"
                         r"lower than|between|over|under|reach|hit|or more|or fewer|or higher|or lower)\b[^?]*\d|"
                         r"\d+(\.\d+)?\s*%|\$\s*\d|\d[\d,]{3,}|\b(price|rate|index|gdp|inflation|unemployment|yield)\b)"),
    ("procédure (décision, vote, accord)", r"\b(pass|sign|approve|confirm|veto|ratify|vote|enact|announce|hold|rule|"
                         r"indict|sanction|impose|tariff|law|bill|court|deal|agreement|ceasefire|meet|release|"
                         r"launch|publish|recogni[sz]e|join|withdraw|extend|lift|ban|declare)"),
]


DATES = re.compile(r"\b(19|20)\d{2}\b|\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.? \d{1,2}(st|nd|rd|th)?\b|"
                   r"\b\d{1,2}(st|nd|rd|th)? (jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*|\bq[1-4]\b", re.I)


def structure(titre: str) -> str:
    t = DATES.sub(" ", titre)                       # les dates ne sont pas des seuils
    return next((nom for nom, r in REGLES if re.search(r, t, re.I)), "autre")


def principal() -> int:
    xs = [json.loads(l) for l in (REG / "jugement-questions.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    import banc_proxemie as bp
    xs = [x for x in xs if x["source"] == "metaculus" and not bp.COMBINEE.search(x.get("titre") or "")]
    vus, uniq = set(), []
    for x in xs:
        if x["id"] not in vus:
            vus.add(x["id"])
            uniq.append(x)
    par = {a: Counter(structure(x["titre"]) for x in uniq if x["jeu"][:4] == a) for a in ("2025", "2026")}
    tout = Counter(structure(x["titre"]) for x in uniq)
    ex = {}
    for x in uniq:
        ex.setdefault(structure(x["titre"]), []).append(x["titre"][:90])
    L = ["# Questions Metaculus résolues par structure (heuristique sur le titre)", "",
         f"{len(uniq)} questions distinctes (2024-2026). Ordre de classement fixe : la première structure reconnue l'emporte.", "",
         "| Structure | Total | Part | 2025 | 2026 |", "|---|---|---|---|---|"]
    for s, n in tout.most_common():
        L.append(f"| {s} | {n} | {n / len(uniq):.0%} | {par['2025'][s]} | {par['2026'][s]} |")
    L += ["", "## Exemples (les 8 plus récents par structure)", ""]
    for s, _ in tout.most_common():
        L += [f"**{s}**", ""] + [f"- {t}" for t in ex[s][-8:]] + [""]
    (REG / "structures-questions.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    sys.exit(principal())
