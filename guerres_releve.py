"""Relevé automatique de l'état d'une guerre (décision de l'auteur du 2026-11-24, 16 h 38 : « Je ne fais rien à la main…
Si on peut automatiser, on le fait »). Bot 0.10.501.

Pour une question d'accord (cessez-le-feu, accord de paix, tenue), le modèle RELÈVE dans la recherche de la question des
faits datés (jamais une probabilité) : début des hostilités en cours, cessez-le-feu en vigueur, dernière rupture, type
de guerre. Le code garde un fait seulement si sa date est passée et si l'adresse qu'il cite figure dans la recherche.
Les faits gardés s'ajoutent à registre/guerres-releves.csv ; accords_guerre les lit avec la table sourcée.
"""
from __future__ import annotations

import csv
import datetime as dt
import json
import os
import re
from pathlib import Path

ICI = Path(__file__).resolve().parent
RELEVES = Path(os.environ.get("ALPHABET_REGISTRE", ICI / "registre")) / "guerres-releves.csv"
CHAMPS = ["guerre", "type", "date", "evenement", "source", "releve_le"]


def cle(titre: str) -> str:
    """Clé de la guerre pour une question hors table : noms propres du titre (hors calendrier), triés."""
    from mise_au_point.procedure_inertie import groupe
    return "releve:" + groupe(titre).lower().replace(" ", "_")


def consigne(titre: str, aujourdhui: str, recherche: str) -> str:
    return f"""Nous sommes le {aujourdhui}. Tu RELÈVES des faits datés dans les recherches ci-dessous. Tu NE DONNES PAS
de probabilité. Un fait absent des recherches = null. Chaque date doit être accompagnée de l'adresse (URL) de la
recherche où tu l'as lue.

QUESTION : {titre}

RECHERCHES :
{recherche[:9000]}

Rends UNIQUEMENT un objet JSON :
{{"type": "inter" (deux États se combattent) | "interne" (un État contre un groupe armé, ou guerre civile) | null,
 "debut": {{"date": "AAAA-MM-JJ", "source": "URL"}} ou null — début des hostilités en cours entre les parties nommées,
 "cessez_le_feu": {{"date": "AAAA-MM-JJ", "source": "URL"}} ou null — dernier cessez-le-feu entré en vigueur entre elles,
 "rupture": {{"date": "AAAA-MM-JJ", "source": "URL"}} ou null — dernière reprise des combats après ce cessez-le-feu}}"""


def analyser(reponse: str, recherche: str, aujourdhui: dt.date, guerre: str) -> list[dict]:
    m = re.search(r"\{.*\}", reponse or "", re.S)
    if not m:
        return []
    try:
        f = json.loads(m.group(0))
    except ValueError:
        return []
    ty = f.get("type") if f.get("type") in ("inter", "interne") else None
    if ty is None:
        return []
    out = []
    for k, ev in (("debut", "debut"), ("cessez_le_feu", "cessez"), ("rupture", "rupture")):
        x = f.get(k)
        if not isinstance(x, dict):
            continue
        try:
            d = dt.date.fromisoformat(str(x.get("date"))[:10])
        except ValueError:
            continue
        src = str(x.get("source") or "")
        if d >= aujourdhui or not src.startswith("http") or src not in (recherche or ""):
            continue                                   # date future ou source absente de la recherche : rejeté
        out.append({"guerre": guerre, "type": ty, "date": d.isoformat(), "evenement": ev, "source": src,
                    "releve_le": aujourdhui.isoformat()})
    return out


def ecrire(faits: list[dict], chemin: Path = RELEVES) -> None:
    if not faits:
        return
    deja = set()
    if chemin.exists():
        deja = {(r["guerre"], r["date"], r["evenement"]) for r in csv.DictReader(chemin.open(encoding="utf-8"))}
    neufs = [f for f in faits if (f["guerre"], f["date"], f["evenement"]) not in deja]
    if not neufs:
        return
    nouveau = not chemin.exists()
    with chemin.open("a", encoding="utf-8", newline="\n") as fh:
        w = csv.DictWriter(fh, fieldnames=CHAMPS)
        if nouveau:
            w.writeheader()
        w.writerows(neufs)


def charger(chemin: Path = RELEVES) -> list[dict]:
    try:
        return list(csv.DictReader(chemin.open(encoding="utf-8")))
    except OSError:
        return []
