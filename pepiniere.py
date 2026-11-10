"""Pépinière de l'arbre (bot 0.10.8, skill §37 ; Wong et al. 2023, §4.1 « faire grandir un modèle par le langage »).

Agrège, sur tout le registre, les instructions que le TRADUCTEUR a tirées des textes (lien, bloque, exclut), chacune avec
son extrait cité et retrouvé. Elle range :
  - les relations ABSENTES de la matrice, affirmées dans assez de questions et de sources distinctes → candidates à une
    nouvelle arête (branche de l'arbre) ;
  - les relations déjà dans la matrice → confirmations ;
  - les « bloque » portant sur une arête existante → contre-indications.
Rien n'entre dans la matrice par ce rapport : une branche n'entre que par décision d'auteur datée, puis est mesurée sur
des questions nouvelles. Le rapport lit le registre, n'écrit que registre/pepiniere.json.

    python pepiniere.py                      # affiche le rapport
    python pepiniere.py --enregistrer        # et l'écrit dans registre/pepiniere.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import alphabet_pipeline as ap

MIN_QUESTIONS = 3        # questions distinctes où la relation est affirmée
MIN_SOURCES = 2          # domaines de source distincts (indépendance minimale)


def _domaine(url: str) -> str | None:
    m = re.match(r"^(?:https?://)?(?:www\.)?([^/?#\s]+)", str(url or "").strip().lower())
    return m.group(1) if m and "." in m.group(1) else None


def _lignes(registre: Path) -> list[dict]:
    out = []
    for nom in ("journal-bot.jsonl", "journal-autres.jsonl"):
        f = registre / nom
        if not f.is_file():
            continue
        for brut in f.read_text(encoding="utf-8").splitlines():
            try:
                out.append(json.loads(brut))
            except json.JSONDecodeError:
                continue
    return out


def _programmes(ligne: dict) -> list[tuple[str, dict]]:
    """(cible, programme) trouvés dans une ligne : bras C, ou lecture exploratoire."""
    res = []
    c = ((ligne.get("bras") or {}).get("C")) or {}
    for bloc in (c, c.get("exploratoire") or {}, ligne.get("exploratoire") or {}):
        tr = (bloc or {}).get("traduction") or {}
        ev = str((bloc or {}).get("evenement") or "").split(" ")[0]
        if tr.get("programme") and ev:
            res.append((ev, tr["programme"]))
    return res


def pepiniere(registre: Path) -> dict:
    m = ap._moteur()
    mat = m.P["matrice"]
    cle = m.cle_valide
    rel: dict[tuple, dict] = defaultdict(lambda: {"questions": set(), "sources": set(), "extraits": []})
    lignes = _lignes(registre)
    for ligne in lignes:
        qid = str(ligne.get("question_id"))
        for ev, prog in _programmes(ligne):
            try:
                cible = cle(ev)
            except ValueError:
                continue
            for x in prog:
                try:
                    ins = x.get("instruction")
                    if ins == "lien":
                        a = cle(str(x.get("de")))
                        b = cible if x.get("vers") in ("cible", None, ev, cible) else cle(str(x.get("vers")))
                        k = ("lien", a.split("@")[0], b.split("@")[0])
                    elif ins == "bloque":
                        k = ("bloque", cle(str(x.get("de"))).split("@")[0], cible.split("@")[0])
                    elif ins == "exclut":
                        k = ("exclut",) + tuple(sorted((cle(str(x.get("a"))).split("@")[0],
                                                        cle(str(x.get("b"))).split("@")[0])))
                    else:
                        continue
                except (ValueError, TypeError):
                    continue
                r = rel[k]
                r["questions"].add(qid)
                d = _domaine(x.get("source"))
                if d:
                    r["sources"].add(d)
                if len(r["extraits"]) < 3:
                    r["extraits"].append({"question_id": qid, "extrait": str(x.get("extrait") or "")[:300],
                                          "source": x.get("source")})
    candidates, confirmations, contre = [], [], []
    for (ins, a, b), r in sorted(rel.items()):
        fiche = {"instruction": ins, "de": a, "vers": b, "questions": len(r["questions"]),
                 "sources_distinctes": len(r["sources"]), "exemples": r["extraits"],
                 "dans_la_matrice": mat.get(a, {}).get(b) if ins in ("lien", "bloque") else None}
        if ins == "lien" and fiche["dans_la_matrice"]:
            confirmations.append(fiche)
        elif ins == "bloque" and fiche["dans_la_matrice"]:
            contre.append(fiche)
        elif ins in ("lien", "exclut"):
            fiche["seuil_atteint"] = (fiche["questions"] >= MIN_QUESTIONS and fiche["sources_distinctes"] >= MIN_SOURCES)
            candidates.append(fiche)
    candidates.sort(key=lambda f: (-f["seuil_atteint"], -f["questions"], -f["sources_distinctes"], f["de"], f["vers"]))
    empreinte = hashlib.sha256("\n".join(sorted(json.dumps(l_, sort_keys=True) for l_ in lignes)).encode()).hexdigest()
    return {"calcule_le": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "version_bot": ap.VERSION_BOT, "version_skill": ap.version_skill(),
            "lignes_lues": len(lignes), "empreinte_registre": empreinte,
            "seuils": {"questions": MIN_QUESTIONS, "sources_distinctes": MIN_SOURCES},
            "candidates": candidates, "confirmations": confirmations, "contre_indications": contre,
            "lecture": "candidates = relations absentes de la matrice affirmées par les textes ; une branche n'entre "
                       "dans la matrice que par décision d'auteur datée, puis est mesurée sur des questions nouvelles"}


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--enregistrer", action="store_true")
    a = p.parse_args()
    r = pepiniere(ap.REGISTRE)
    mures = [c for c in r["candidates"] if c["seuil_atteint"]]
    print(f"Pépinière : {r['lignes_lues']} lignes lues, {len(r['candidates'])} relations nouvelles "
          f"({len(mures)} au seuil), {len(r['confirmations'])} confirmations, "
          f"{len(r['contre_indications'])} contre-indications.")
    for c in mures[:20]:
        print(f"  {c['instruction']} {c['de']} → {c['vers']} : {c['questions']} questions, "
              f"{c['sources_distinctes']} sources")
    if a.enregistrer:
        ap.REGISTRE.mkdir(parents=True, exist_ok=True)
        (ap.REGISTRE / "pepiniere.json").write_text(json.dumps(r, ensure_ascii=False, indent=2) + "\n",
                                                    encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
