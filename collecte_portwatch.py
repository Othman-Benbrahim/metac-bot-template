"""Passages quotidiens de navires dans les grands détroits, tirés d'IMF PortWatch (bot 0.10.176, en ombre).

Source : IMF PortWatch (FMI et université d'Oxford), service ArcGIS public « Daily_Chokepoints_Data ».
Source : IMF PortWatch. Transformation : seuls les comptes quotidiens de huit détroits sont gardés.

Conditions (décision d'auteur du 2026-11-16, 12 h 58) : les conditions du FMI autorisent la réutilisation non
commerciale des données avec attribution, mais interdisent le « téléchargement en masse par des moyens automatisés »
sans autorisation explicite. La demande d'autorisation (copyright@imf.org, 2026-11-16) n'a reçu qu'une réponse
automatique renvoyant au Copyright Clearance Center ; l'auteur juge qu'un accès à petite dose n'est pas un
téléchargement en masse. D'où des limites strictes, inscrites dans le code :
  - huit détroits seulement, une requête par détroit et par passage (pas de pagination sur toute la base) ;
  - l'année en cours seulement (filtre « year »), depuis le 2026-06-01 ;
  - deux passages par jour au plus ; aucune redistribution de la base, seulement les comptes dérivés ci-dessous.

Registre : registre/portwatch-detroits.csv (detroit, jour, navires, petroliers, porte_conteneurs).

0.10.335 — exception pour Ormuz (décision d'auteur du 2026-11-19, 11 h 24) : depuis juin le détroit tourne à environ
deux navires par jour ; mesurée sur la seule année en cours, la crise devient l'habitude et la carte voit Ormuz normal.
Une RÉFÉRENCE d'avant-crise est donc lue une seule fois : l'année 2025 pour Ormuz seulement (une requête, ≤ 365
jours, même petite dose), dans registre/portwatch-reference.csv, jamais relue si le fichier existe. Elle ne sert qu'à
l'habitude (adaptateur portwatch_ref, clé de trace « habitude ») ; l'état du jour vient toujours de l'année en cours.
"""
from __future__ import annotations

import csv
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

SERVICE = ("https://services9.arcgis.com/weJ1QsnbMYJlCHdG/arcgis/rest/services/Daily_Chokepoints_Data/"
           "FeatureServer/0/query")
SORTIE = Path("registre") / "portwatch-detroits.csv"
# 0.10.358 (décision d'auteur du 2026-11-19, 16 h 41) : escales quotidiennes de quelques ports clés (transport-maritime:ports),
# même source, même règle (année en cours seulement).
SERVICE_PORTS = ("https://services9.arcgis.com/weJ1QsnbMYJlCHdG/arcgis/rest/services/Daily_Ports_Data/"
                 "FeatureServer/0/query")
SORTIE_PORTS = Path("registre") / "portwatch-ports.csv"
PORTS = {"rotterdam": "Rotterdam", "singapour": "Singapore", "shanghai": "Shanghai", "bandar_abbas": "Bandar Abbas",
         "jebel_ali": "Jebel Ali", "los_angeles": "Los Angeles"}
REFERENCE = Path("registre") / "portwatch-reference.csv"
REFERENCE_DETROITS = {"ormuz": 2025}            # exception écrite : un détroit, une année d'avant-crise
DEBUT = "2026-06-01"
UA = {"User-Agent": "alphabet-situationnel-bot/1.0 (recherche ; GitHub Othman-Benbrahim)"}

# détroit (nom court) : (motif du nom PortWatch, pays riverains ou directement concernés), table fixée le 2026-11-16
DETROITS = {
    "suez": ("Suez", ["EG"]),
    "bab_el_mandeb": ("Bab el-Mandeb", ["YE", "ER", "DJ"]),
    "ormuz": ("Hormuz", ["IR", "OM", "AE"]),
    "malacca": ("Malacca", ["MY", "SG", "ID"]),
    "panama": ("Panama", ["PA"]),
    "bosphore": ("Bosporus", ["TR"]),
    "taiwan": ("Taiwan", ["TW", "CN"]),
    "bonne_esperance": ("Good Hope", ["ZA"]),
}


def requete(c: httpx.Client, motif: str, annee: int, service: str = SERVICE,
            champs: str = "date,portname,n_total,n_tanker,n_container") -> list[dict]:
    params = {"where": f"portname LIKE '%{motif}%' AND year = {annee}", "outFields": champs,
              "orderByFields": "date ASC", "resultRecordCount": 1000, "f": "json"}
    for essai in range(6):
        try:
            r = c.get(service, params=params)
            if r.status_code == 429 or r.status_code >= 500:
                time.sleep(65)
                continue
            r.raise_for_status()
            corps = r.json()
            if "error" in corps:
                # 0.10.183 : le quota ArcGIS (6 000 unités par minute) est partagé par tous les utilisateurs du
                # service ; une erreur 429 dans la réponse veut dire « réessayez dans 60 s », pas un refus.
                if (corps["error"] or {}).get("code") == 429 and essai < 5:
                    print(f"  {motif} : quota ArcGIS partagé dépassé, nouvel essai dans 65 s")
                    time.sleep(65)
                    continue
                print(f"  {motif} : erreur ArcGIS {corps['error']}")
                return []
            return [f.get("attributes") or {} for f in corps.get("features") or []]
        except httpx.HTTPError as e:
            print(f"  {motif} : {type(e).__name__}")
            time.sleep(10 * 2 ** essai)
    return []


def jour(attr: dict) -> str | None:
    d = attr.get("date")
    if isinstance(d, (int, float)):
        return datetime.fromtimestamp(d / 1000, tz=timezone.utc).date().isoformat()
    if isinstance(d, str) and len(d) >= 10:
        return d[:10]
    return None


def escales(attr: dict) -> list[int] | None:
    """Escales du jour (toutes, pétroliers, porte-conteneurs), noms de champs tolérés (« portcalls », « n_total »)."""
    def v(*cles):
        for k in cles:
            if attr.get(k) is not None:
                return int(attr[k])
        return None
    t = v("portcalls", "n_total")
    return None if t is None else [t, v("portcalls_tanker", "n_tanker") or 0, v("portcalls_container", "n_container") or 0]


def ports(c: httpx.Client, annee: int) -> None:
    deja = {}
    if SORTIE_PORTS.exists():
        deja = {(x["port"], x["jour"]): [int(x["escales"]), int(x["petroliers"]), int(x["porte_conteneurs"])]
                for x in csv.DictReader(SORTIE_PORTS.open(encoding="utf-8"))}
    for nom, motif in PORTS.items():
        lignes = requete(c, motif, annee, SERVICE_PORTS, "*")
        noms = {str(a.get("portname")) for a in lignes}
        if len(noms) > 1:
            print(f"  port {nom} : plusieurs ports correspondent ({sorted(noms)}) : ignoré, table à préciser")
            time.sleep(15)
            continue
        n = 0
        for a in lignes:
            j, e = jour(a), escales(a)
            if j and j >= DEBUT and e is not None:
                n += deja.get((nom, j)) != e
                deja[(nom, j)] = e
        print(f"  port {nom:12s} {sorted(noms)} : {len(lignes)} jours, {n} nouveaux ou modifiés")
        time.sleep(15)
    if deja:
        with SORTIE_PORTS.open("w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["port", "jour", "escales", "petroliers", "porte_conteneurs"])
            for (p, j), v in sorted(deja.items(), key=lambda t: (t[0][1], t[0][0])):
                w.writerow([p, j, *v])


def lire() -> dict[tuple, list[int]]:
    if not SORTIE.exists():
        return {}
    return {(x["detroit"], x["jour"]): [int(x["navires"]), int(x["petroliers"]), int(x["porte_conteneurs"])]
            for x in csv.DictReader(SORTIE.open(encoding="utf-8"))}


def principal() -> int:
    comptes = lire()
    annee = datetime.now(timezone.utc).year
    nouveaux = 0
    with httpx.Client(headers=UA, timeout=60, follow_redirects=True) as c:
        for nom, (motif, _) in DETROITS.items():
            lignes = requete(c, motif, annee)
            noms = {str(a.get("portname")) for a in lignes}
            if len(noms) > 1:
                print(f"  {nom} : plusieurs détroits correspondent ({sorted(noms)}) : ignoré, table à préciser")
                continue
            n = 0
            for a in lignes:
                j = jour(a)
                if not j or j < DEBUT:
                    continue
                v = [int(a.get("n_total") or 0), int(a.get("n_tanker") or 0), int(a.get("n_container") or 0)]
                if comptes.get((nom, j)) != v:
                    n += 1
                comptes[(nom, j)] = v
            nouveaux += n
            dernier = max((jour(a) or "" for a in lignes), default="—")
            print(f"  {nom:16s} {sorted(noms)} : {len(lignes)} jours en {annee}, dernier {dernier}, {n} nouveaux ou modifiés")
            time.sleep(15)
        try:
            ports(c, annee)
        except Exception as e:
            print(f"::warning::ports : {type(e).__name__}")
        if not REFERENCE.exists():
            ref = []
            for nom, an in REFERENCE_DETROITS.items():
                for a in requete(c, DETROITS[nom][0], an):
                    j = jour(a)
                    if j and j.startswith(str(an)):
                        ref.append((nom, j, int(a.get("n_total") or 0), int(a.get("n_tanker") or 0), int(a.get("n_container") or 0)))
                print(f"  référence {nom} {an} : {sum(1 for r in ref if r[0] == nom)} jours")
            if ref:
                with REFERENCE.open("w", encoding="utf-8", newline="") as f:
                    w = csv.writer(f)
                    w.writerow(["detroit", "jour", "navires", "petroliers", "porte_conteneurs"])
                    w.writerows(sorted(ref, key=lambda r: (r[1], r[0])))
    SORTIE.parent.mkdir(exist_ok=True)
    with SORTIE.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["detroit", "jour", "navires", "petroliers", "porte_conteneurs"])
        for (d, j), v in sorted(comptes.items(), key=lambda t: (t[0][1], t[0][0])):
            w.writerow([d, j, *v])
    bilan = f"{nouveaux} comptes nouveaux ou modifiés ; {len(comptes)} cases détroit × jour. Source : IMF PortWatch."
    print(bilan)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
            f.write(f"## PortWatch\n\n{bilan}\n")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
