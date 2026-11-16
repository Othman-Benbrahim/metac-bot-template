"""ACAPS : liste des risques et indice de gravité INFORM, par pays (bot 0.10.196, en ombre).

Décision d'auteur du 2026-11-16 (17 h 18) : sources d'alerte précoce. API gratuite après inscription
(https://api.acaps.org, jeton par identifiant et mot de passe : secrets ACAPS_USER, ACAPS_PASSWORD, ou ACAPS_TOKEN).
Source : ACAPS.

1. Liste des risques (risk-list) : risques formulés par les analystes d'ACAPS, avec date d'entrée, probabilité,
   impact, niveau, statut. On garde chaque risque (une ligne par pays concerné). Pour la PRÉVISION, seuls comptent
   les champs fixés à l'entrée (date_entered, pays) : probabilité, niveau et statut peuvent avoir été révisés après la
   date d'une question (last_risk_update) ; le statut (« materialised ») sert à juger ACAPS, jamais à prévoir.
2. INFORM Severity Index : instantané mensuel (gravité 0–10 et catégorie par crise et pays) ; on garde nos propres
   instantanés datés (l'historique de l'API n'est pas encore exploré).
3. Calendrier saisonnier : point d'accès non trouvé dans la documentation ; essais de chemins plausibles, notés.

Registres : registre/acaps-risques.csv ; registre/acaps-inform.csv (instantane, crise, pays, indice, categorie).
"""
from __future__ import annotations

import csv
import io
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

API = "https://api.acaps.org/api/v1/"
CODES = "https://raw.githubusercontent.com/datasets/country-codes/main/data/country-codes.csv"
RISQUES = Path("registre") / "acaps-risques.csv"
INFORM = Path("registre") / "acaps-inform.csv"
CHAMPS_R = ["risk_id", "pays", "date_entered", "last_risk_update", "probability", "impact", "risk_level", "status",
            "risk_type", "geographic_level", "risk_title"]
CHAMPS_I = ["instantane", "crisis_id", "pays", "indice", "categorie", "derniere_maj"]
SAISON = ["seasonal-events-calendar/seasonal-calendar/", "seasonal-events-calendar/", "seasonal-calendar/",
          "seasonal-events/", "seasonal-events-calendar/seasonal-events-calendar/"]


def jeton(c: httpx.Client) -> str | None:
    t = os.environ.get("ACAPS_TOKEN", "").strip()
    if t:
        return t
    u, p = os.environ.get("ACAPS_USER", ""), os.environ.get("ACAPS_PASSWORD", "")
    if not u or not p:
        return None
    r = c.post(API + "token-auth/", data={"username": u, "password": p})
    return (r.json() or {}).get("token") if r.status_code == 200 else None


def iso3_vers_iso2(c: httpx.Client) -> dict[str, str]:
    try:
        r = c.get(CODES, timeout=60)
        return {x["ISO3166-1-Alpha-3"]: x["ISO3166-1-Alpha-2"] for x in csv.DictReader(io.StringIO(r.text))
                if x.get("ISO3166-1-Alpha-3") and x.get("ISO3166-1-Alpha-2")}
    except Exception:
        return {}


def toutes_les_pages(c: httpx.Client, h: dict, chemin: str) -> list[dict]:
    out, url = [], API + chemin
    while url:
        r = c.get(url, headers=h)
        if r.status_code != 200:
            print(f"  {chemin} : HTTP {r.status_code}")
            break
        j = r.json()
        out += (j.get("results") or []) if isinstance(j, dict) else j
        url = j.get("next") if isinstance(j, dict) else None
        time.sleep(0.5)
    return out


def lignes_risques(res: list[dict], conv: dict[str, str]) -> list[dict]:
    out = []
    for x in res:
        for i3 in x.get("iso3") or []:
            out.append({"risk_id": x.get("risk_id"), "pays": conv.get(i3, i3), "date_entered": str(x.get("date_entered") or "")[:10],
                        "last_risk_update": str(x.get("last_risk_update") or "")[:10], "probability": x.get("probability"),
                        "impact": x.get("impact"), "risk_level": x.get("risk_level"), "status": x.get("status"),
                        "risk_type": x.get("risk_type"), "geographic_level": x.get("geographic_level"),
                        "risk_title": str(x.get("risk_title") or "")[:200]})
    return out


def lignes_inform(res: list[dict], conv: dict[str, str], instantane: str) -> list[dict]:
    out = []
    for x in res:
        pays = x.get("iso3") or []
        if not pays and len(str(x.get("crisis_id") or "")) >= 3:
            pays = [str(x["crisis_id"])[:3]]          # « AFG001 » : pays de la crise quand iso3 est vide
        for i3 in pays:
            out.append({"instantane": instantane, "crisis_id": x.get("crisis_id"), "pays": conv.get(i3, i3),
                        "indice": x.get("INFORM Severity Index"), "categorie": x.get("INFORM Severity category"),
                        "derniere_maj": x.get("Last updated")})
    return out


def ecrire(chemin: Path, champs: list[str], lignes: list[dict]) -> None:
    chemin.parent.mkdir(exist_ok=True)
    with chemin.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=champs)
        w.writeheader()
        for l in lignes:
            w.writerow({k: l.get(k, "") for k in champs})


def principal() -> int:
    with httpx.Client(timeout=60, follow_redirects=True) as c:
        t = jeton(c)
        if not t:
            print("Jeton ACAPS indisponible (secrets ACAPS_USER / ACAPS_PASSWORD ou ACAPS_TOKEN).")
            return 1
        h = {"Authorization": f"Token {t}", "Accept": "application/json"}
        conv = iso3_vers_iso2(c)
        risques = lignes_risques(toutes_les_pages(c, h, "risk-list/"), conv)
        ecrire(RISQUES, CHAMPS_R, sorted(risques, key=lambda x: (x["date_entered"], x["risk_id"], x["pays"])))
        print(f"Risques : {len({x['risk_id'] for x in risques})} risques, {len(risques)} lignes pays.")
        statuts = {}
        for x in risques:
            statuts[x["status"]] = statuts.get(x["status"], 0) + 1
        print("  statuts :", statuts)
        instantane = datetime.now(timezone.utc).date().isoformat()
        inf = lignes_inform(toutes_les_pages(c, h, "inform-severity-index/"), conv, instantane)
        anciens = list(csv.DictReader(INFORM.open(encoding="utf-8"))) if INFORM.exists() else []
        anciens = [x for x in anciens if x["instantane"] != instantane]
        ecrire(INFORM, CHAMPS_I, anciens + inf)
        print(f"INFORM : {len(inf)} lignes pays ce jour ; {len({x['instantane'] for x in anciens}) + 1} instantané(s).")
        for chemin in SAISON:
            r = c.get(API + chemin, headers=h)
            print(f"  calendrier saisonnier, essai {chemin} : HTTP {r.status_code}")
            if r.status_code == 200:
                try:
                    j = r.json()
                    res = j.get("results") if isinstance(j, dict) else j
                    print("    clés :", sorted(res[0].keys()) if res else "aucun enregistrement")
                except ValueError:
                    pass
                break
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
            f.write(f"## ACAPS\n\n{len(risques)} lignes de risques ; {len(inf)} lignes INFORM. Source : ACAPS.\n")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
