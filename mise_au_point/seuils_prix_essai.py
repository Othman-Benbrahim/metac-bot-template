"""Calibrage du modèle log-normal sur les questions de seuil de prix résolues (préenregistrement
preenregistrements/seuils-de-prix-calibrage.md, 2026-11-20). Aucune cote de marché en entrée.

    python mise_au_point/seuils_prix_essai.py   # écrit registre/mise-au-point/seuils-prix.json
"""
from __future__ import annotations

import json
import math
import re
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import alphabet_pipeline as ap
import combinaisons as cb
import seuils_prix as sp

SORTIE = Path("registre") / "mise-au-point" / "seuils-prix.json"
NUM = re.compile(r"\$\s?([\d,]+(?:\.\d+)?)\s*([kKmM]?)\b|\b([\d,]+(?:\.\d+)?)\s*([kKmM])\b")
TOUCHE = re.compile(r"\b(reach|hit|touch|dip|drop|fall|trade (above|below|over|under)|at any (point|time)|again)\b", re.I)
DATE = re.compile(r"\b(close|closing|settle|be (above|below|over|under)|end (of )?\w+ (above|below))\b", re.I)
HAUT = re.compile(r"\b(above|over|higher|reach|hit)\b", re.I)
BAS = re.compile(r"\b(below|under|lower|dip|drop|fall)\b", re.I)


def borne(p):
    return min(0.99, max(0.01, p))


def perte(p, y):
    p = borne(p)
    return -math.log(p if y else 1 - p)


def montant(t):
    m = NUM.search(t)
    if not m:
        return None
    v, s = (m.group(1), m.group(2)) if m.group(1) else (m.group(3), m.group(4))
    try:
        x = float(v.replace(",", ""))
    except ValueError:
        return None
    return x * (1e3 if s.lower() == "k" else 1e6 if s.lower() == "m" else 1)


MOIS = {m: i for i, m in enumerate(["january", "february", "march", "april", "may", "june", "july", "august",
                                      "september", "october", "november", "december"], 1)}


def echeance(t: str, jeu: str) -> tuple[str | None, str]:
    """Correctif du 2026-11-20 : l'horizon du registre est le délai jusqu'à la RÉSOLUTION, raccourci quand un seuil est
    touché tôt (fuite de l'issue) ; on lit l'échéance écrite dans le titre."""
    ds = [x for x in ap.dates_citees(t) if x >= jeu]
    if ds:
        return min(ds), "date du titre"
    m = re.search(r"\bbefore (20\d\d)\b", t, re.I)
    if m:
        return f"{int(m.group(1)) - 1}-12-31", "année du titre"
    m = re.search(r"\b(?:by|in|end(?: of)?|during|close|end)\s+(?:the end of\s+)?(20\d\d)\b|(?<!\$)\b(20\d\d)\s*\??$", t, re.I)
    if m:
        return f"{m.group(1) or m.group(2)}-12-31", "année du titre"
    m = re.search(r"\b(?:by|before)\s+(?:the\s+)?end\s+of\s+([a-z]+)\b|\bby\s+([a-z]+)\s+\d{0,2}\b", t, re.I)
    mo = (m.group(1) or m.group(2) or "").lower() if m else ""
    if mo in MOIS:
        a = int(jeu[:4]) + (1 if MOIS[mo] < int(jeu[5:7]) else 0)
        fin = date(a + (MOIS[mo] == 12), MOIS[mo] % 12 + 1, 1) - timedelta(days=1)
        return fin.isoformat(), "mois du titre"
    return None, ""


def questions():
    out = []
    for f in ("registre/jugement-questions.jsonl", "registre/mise-au-point/questions.jsonl"):
        for l in Path(f).read_text(encoding="utf-8").splitlines():
            d = json.loads(l)
            t = d["titre"]
            a, k = sp.actif(t), montant(t)
            if not a or not k:
                continue
            typ = "touche" if TOUCHE.search(t) else "date" if DATE.search(t) else None
            if not typ:
                continue
            bas, haut = bool(BAS.search(t)), bool(HAUT.search(t))
            if bas == haut and typ == "date":
                continue
            au_dessus = not bas if bas != haut else True
            fin, source_fin = echeance(t, d["jeu"][:10])
            if not fin:
                fin, source_fin = (date.fromisoformat(d["jeu"][:10]) + timedelta(days=int(d.get("horizon") or 0))).isoformat(), "horizon"
            out.append({"cle": f'{d["source"]}:{d["id"]}', "source": d["source"], "jeu": d["jeu"][:10], "fin": fin,
                        "actif": a, "k": k, "type": typ, "au_dessus": au_dessus, "y": int(d["issue"]), "titre": t[:90], "source_fin": source_fin})
    return sorted(out, key=lambda q: q["jeu"])


def principal() -> int:
    qs = questions()
    lignes = []
    for i, q in enumerate(qs):
        e30, e90 = sp.etat(q["actif"], q["jeu"], 30), sp.etat(q["actif"], q["jeu"], 90)
        if not e30:
            continue
        s0, sig = e30
        t = max(sp.annees(q["jeu"], q["fin"]), 1 / 365)
        def m(sigma):
            if q["type"] == "date":
                return sp.p_a_la_date(s0, q["k"], sigma, t, q["au_dessus"])
            return sp.p_atteint_avant(s0, q["k"], sigma, t)
        passe = [p["y"] for p in qs[:i] if p["fin"] < q["jeu"] and p["type"] == q["type"]]
        pI = (sum(passe) + 5 * 0.5) / (len(passe) + 5)
        deja = False
        lignes.append({**q, "p_M": m(sig), "p_M90": m(e90[1]) if e90 else m(sig), "p_M15": m(sig * 1.5), "p_I": pI, "deja": deja})
    def ecart(cle):
        e = [(x["cle"], perte(x[cle], x["y"]) - perte(x["p_I"], x["y"])) for x in lignes]
        b, h = cb.bootstrap(e, 0.05)
        return {"moyenne": round(sum(v for _, v in e) / len(e), 4), "intervalle_90": [round(b, 4), round(h, 4)]}
    calib = {}
    for x in lignes:
        b = min(9, int(borne(x["p_M"]) * 10))
        calib.setdefault(b, []).append(x["y"])
    par = lambda s: {"n": len(s), "M": round(sum(perte(x["p_M"], x["y"]) for x in s) / len(s), 4),
                     "I": round(sum(perte(x["p_I"], x["y"]) for x in s) / len(s), 4)} if s else None
    r = {"questions_reconnues": len(qs), "jugees": len(lignes), "questions_distinctes": len({x["cle"] for x in lignes}),
         "pertes": {"I témoin": round(sum(perte(x["p_I"], x["y"]) for x in lignes) / len(lignes), 4),
                    "M sigma 30 j": round(sum(perte(x["p_M"], x["y"]) for x in lignes) / len(lignes), 4),
                    "M sigma 90 j": round(sum(perte(x["p_M90"], x["y"]) for x in lignes) / len(lignes), 4),
                    "M sigma x 1,5": round(sum(perte(x["p_M15"], x["y"]) for x in lignes) / len(lignes), 4)},
         "critere_M_moins_I": ecart("p_M"),
         "descriptif": {"M90_moins_I": ecart("p_M90"), "M15_moins_I": ecart("p_M15"),
                        "par_type": {t: par([x for x in lignes if x["type"] == t]) for t in ("date", "touche")},
                        "par_actif": {a: par([x for x in lignes if x["actif"] == a]) for a in sorted({x["actif"] for x in lignes})},
                        "echeance_lue_dans_le_titre": sum(1 for x in lignes if x["source_fin"] != "horizon"),
                        "calibrage_M (tranche: n, part de oui)": {f"{b*10}-{b*10+10} %": (len(v), round(sum(v) / len(v), 3)) for b, v in sorted(calib.items())}},
         "note": "perte log, plus bas = mieux ; M − I < 0 : le modèle aide ; aucune cote de marché en entrée"}
    SORTIE.write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(r, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(principal())
