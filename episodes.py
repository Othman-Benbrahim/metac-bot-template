"""Matrice d'épisodes N × D (bot 0.10.9 ; skill §38, d'après Murphy ch. 30 : l'apprentissage de structure prend en
entrée une matrice N × D, que le dépôt n'avait pas).

Une ligne par lecture du registre (bras C, ou lecture exploratoire), une colonne par carte de la strate de l'événement :
  F, f            carte ancrée et son intensité
  R:<catégorie>   candidate examinée puis rejetée (contredit, marqueur_non_rempli, aucun_fait, non_cherchee, non_classe)
  (vide)          carte non examinée
plus la question, la date, l'événement, la strate, le statut de C, p_B, p_C et l'issue si elle est connue. C'est
l'entrée des apprentissages futurs (couplages de co-présence par pseudo-vraisemblance, structure, λ) ; ce fichier
n'apprend rien lui-même.

    python episodes.py --enregistrer      # écrit registre/episodes.csv
"""
from __future__ import annotations

import argparse
import csv
import io
import json
from pathlib import Path

import alphabet_pipeline as ap


def _issues(reg: Path) -> dict[str, int]:
    out = {}
    f = reg / "issues.jsonl"
    if f.is_file():
        for brut in f.read_text(encoding="utf-8").splitlines():
            try:
                x = json.loads(brut)
                out[str(x.get("question_id"))] = x.get("issue")
            except (json.JSONDecodeError, AttributeError):
                continue
    return out


def _blocs(ligne: dict) -> list[tuple[str, dict]]:
    c = ((ligne.get("bras") or {}).get("C")) or {}
    res = [("C", c)] if c.get("etat") or c.get("rejets_classes") else []
    ex = c.get("exploratoire") or ligne.get("exploratoire") or {}
    if ex.get("etat"):
        res.append(("exploratoire", ex))
    return res


def episodes(reg: Path) -> list[dict]:
    m = ap._moteur()
    cartes = sorted(m.NOMS)
    issues = _issues(reg)
    rows = []
    for nom in ("journal-bot.jsonl", "journal-autres.jsonl"):
        f = reg / nom
        if not f.is_file():
            continue
        for brut in f.read_text(encoding="utf-8").splitlines():
            try:
                ligne = json.loads(brut)
            except json.JSONDecodeError:
                continue
            for canal, b in _blocs(ligne):
                ev = str(b.get("evenement") or "")
                try:
                    cible = m.cle_valide(ev.split(" ")[0])
                except ValueError:
                    continue
                s = int(cible.split("@")[1])
                cellule = {c: "" for c in cartes}
                try:
                    etat = m.lire_etat(b["etat"]) if b.get("etat") else {"mots": []}
                except (ValueError, KeyError):
                    etat = {"mots": []}
                for x in etat["mots"]:
                    if x["s"] == s:
                        cellule[x["c"]] = x["i"]
                for k, v in (b.get("rejets_classes") or {}).items():
                    try:
                        c_, s_ = m.cle_valide(str(k)).split("@")
                    except ValueError:
                        continue
                    if int(s_) == s and not cellule[c_]:
                        cellule[c_] = "R:" + str(v or "non_classe")
                qid = str(ligne.get("question_id"))
                rows.append({"question_id": qid, "date": str(ligne.get("date_information") or ligne.get("date") or "")[:10],
                             "canal": canal, "evenement": ev, "strate": s, "statut_C": b.get("statut"),
                             "p_B": ((ligne.get("bras") or {}).get("B") or {}).get("p"), "p_C": b.get("p_C"),
                             "issue": issues.get(qid), **cellule})
    return rows


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--enregistrer", action="store_true")
    a = p.parse_args()
    rows = episodes(ap.REGISTRE)
    tampon = io.StringIO()
    if rows:
        w = csv.DictWriter(tampon, fieldnames=list(rows[0].keys()), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    print(f"Épisodes : {len(rows)} lignes × {len(rows[0]) if rows else 0} colonnes.")
    if a.enregistrer and rows:
        ap.REGISTRE.mkdir(parents=True, exist_ok=True)
        (ap.REGISTRE / "episodes.csv").write_text(tampon.getvalue(), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
