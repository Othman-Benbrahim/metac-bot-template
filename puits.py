"""Puits de données (décision de l'auteur, 2026-11-27, 19 h 43) : notre propre index, alimenté par nos collectes,
interrogé en parallèle des moteurs externes, pour rester indépendant.

Règle de l'auteur : le LIEN, le TITRE et des MÉTADONNÉES, jamais le texte de l'article. Le texte original se relit à
la source au moment voulu (robots.txt respecté). Métadonnées : date, domaine (l'émetteur), famille du flux, pays
détectés, noms propres (anticipation.noms : la même chaîne que les mots clés de la veille anticipée), matières.

Stockage : registre/puits/AAAA-MM.jsonl.gz (un fichier par mois, ajout en fin de fichier).
Recherche : index plein texte SQLite (FTS5, intégré à Python) construit à la volée sur les mois demandés ; tri BM25.
"""
from __future__ import annotations

import gzip
import json
import sqlite3
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import urlparse

ICI = Path(__file__).resolve().parent
DOSSIER = ICI / "registre" / "puits"


def domaine(url: str) -> str:
    try:
        return urlparse(url).netloc.lower().removeprefix("www.")
    except ValueError:
        return ""


def ajouter(lignes: list[dict], dossier: Path = DOSSIER) -> int:
    """lignes : {jour, lien, titre, famille, pays, noms, matieres}. Écrit par mois ; rend le nombre écrit."""
    par_mois: dict[str, list[dict]] = {}
    for l in lignes:
        if not l.get("lien") or not l.get("titre"):
            continue
        r = {"j": l["jour"], "u": l["lien"][:500], "t": " ".join(l["titre"].split())[:300], "d": domaine(l["lien"]),
             "f": l.get("famille", ""), "p": sorted(l.get("pays") or []), "n": sorted(l.get("noms") or [])[:20],
             "m": sorted(l.get("matieres") or [])}
        par_mois.setdefault(l["jour"][:7], []).append(r)
    dossier.mkdir(parents=True, exist_ok=True)
    n = 0
    for mois, rs in par_mois.items():
        with gzip.open(dossier / f"{mois}.jsonl.gz", "at", encoding="utf-8") as f:
            for r in rs:
                f.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")
                n += 1
    return n


def charger(depuis: date, jusqu: date, dossier: Path = DOSSIER) -> list[dict]:
    out, m = [], date(depuis.year, depuis.month, 1)
    while m <= jusqu:
        p = dossier / f"{m:%Y-%m}.jsonl.gz"
        if p.exists():
            with gzip.open(p, "rt", encoding="utf-8") as f:
                for l in f:
                    try:
                        r = json.loads(l)
                    except ValueError:
                        continue
                    if depuis.isoformat() <= r["j"] <= jusqu.isoformat():
                        out.append(r)
        m = date(m.year + (m.month == 12), m.month % 12 + 1, 1)
    return out


def chercher(requete: str, jusqu: date, jours: int = 30, limite: int = 20, dossier: Path = DOSSIER) -> list[dict]:
    """Les `limite` meilleurs articles (BM25 sur titre, noms, pays) publiés dans les `jours` jours avant `jusqu`
    (jamais après : pas de regard vers l'avant). Un lien vu plusieurs fois ne compte qu'une fois."""
    rs = charger(jusqu - timedelta(days=jours), jusqu, dossier)
    if not rs:
        return []
    db = sqlite3.connect(":memory:")
    db.execute("CREATE VIRTUAL TABLE a USING fts5(t, n, p, i UNINDEXED, tokenize='unicode61 remove_diacritics 2')")
    vus = {}
    for i, r in enumerate(rs):
        if r["u"] in vus:
            continue
        vus[r["u"]] = i
        db.execute("INSERT INTO a VALUES (?,?,?,?)", (r["t"], " ".join(r["n"]), " ".join(r["p"]), i))
    mots = [w for w in "".join(c if c.isalnum() else " " for c in requete).split() if len(w) >= 3]
    if not mots:
        return []
    q = " OR ".join(f'"{w}"' for w in mots)
    try:
        res = db.execute("SELECT i, bm25(a) FROM a WHERE a MATCH ? ORDER BY bm25(a) LIMIT ?", (q, limite)).fetchall()
    except sqlite3.OperationalError:
        return []
    return [{**rs[i], "score": round(-s, 3)} for i, s in res]
