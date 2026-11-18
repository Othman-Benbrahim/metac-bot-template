"""Volume des articles de sources russes qui nomment un pays, par jour (bot 0.10.202, M12, en ombre).

Décision d'auteur du 2026-11-16 (18 h 56). Mécanisme M12 « le récit monte avant l'acte » (rapport KAS, *Cognitive
Warfare*, 2026, chapitre Ukraine : StopFake dit avoir anticipé l'invasion de février 2022 en suivant le volume des
récits russes dans les semaines précédentes ; affirmation de praticiens, non vérifiée).

Source : API DOC 2.0 de GDELT (gratuite, sans clé), mode « timelinevolraw » : nombre d'articles par jour qui répondent
à la requête, et nombre total d'articles surveillés ce jour-là. Requête : sourcecountry:russia et le nom anglais du
pays (GDELT traduit les articles en russe et cherche dans la traduction). La fenêtre de l'API est glissante, de trois
mois au plus : chaque passage relit les trois derniers mois et complète notre propre historique.

Variante « alibi informationnel » : même requête, restreinte aux articles qui contiennent « provocation », « staged »
ou « false flag » ; seulement pour les pays dont le volume dépasse SEUIL_ALIBI articles sur les 14 derniers jours
(une requête par pays et par passage coûte 5 secondes, limite de l'API).

On ne garde que des COMPTES. Registre : registre/recit-russe.csv (pays, jour, articles, alibi, total_surveille).
Usage : python collecte_recit_russe.py [--pays EE,LV] [--duree 3m]
"""
from __future__ import annotations

import argparse
import csv
import io
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx

API = "https://api.gdeltproject.org/api/v2/doc/doc"
CODES = "https://raw.githubusercontent.com/datasets/country-codes/main/data/country-codes.csv"
REGISTRE = Path("registre") / "recit-russe.csv"
UA = {"User-Agent": "alphabet-situationnel-bot/1.0 (recherche ; GitHub Othman-Benbrahim)"}
PAUSE = 8.0                      # l'API DOC demande au plus une requête toutes les 5 secondes ; les adresses de GitHub
                                 # étant partagées, 5,5 s ne suffisait pas (164 refus « 429 » sur 196 au premier passage)
ATTENTES_429 = (30, 90)          # 0.10.210 : deux nouvelles tentatives espacées après un refus « 429 »
DUREE_MAX = 110 * 60             # 0.10.245 : budget du passage (le pas de temps du workflow est de 150 min) ; au-delà, on
                                 # écrit ce qui est lu et le passage suivant reprend avec les pays les moins à jour
ARRET_429 = 8                    # refus persistants d'affilée : on s'arrête et l'on garde ce qui est lu
SEUIL_ALIBI = 20
MOTS_ALIBI = '(provocation OR staged OR "false flag")'
CHAMPS = ["pays", "jour", "articles", "alibi", "total_surveille"]
# noms anglais simples, pour une requête plein texte (la table publique donne parfois des noms officiels longs)
NOMS = {"RU": None, "US": "United States", "GB": "United Kingdom", "KR": "South Korea", "KP": "North Korea",
        "IR": "Iran", "SY": "Syria", "VE": "Venezuela", "BO": "Bolivia", "TZ": "Tanzania", "MD": "Moldova",
        "VN": "Vietnam", "LA": "Laos", "CD": "Democratic Republic of the Congo", "CG": "Republic of the Congo",
        "CZ": "Czech Republic", "MK": "North Macedonia", "PS": "Palestine", "TW": "Taiwan", "CI": "Ivory Coast",
        "FM": "Micronesia", "BN": "Brunei", "CV": "Cape Verde", "SZ": "Eswatini", "TR": "Turkey", "XK": "Kosovo"}


def pays_et_noms(c: httpx.Client) -> dict[str, str]:
    r = c.get(CODES, timeout=60)
    r.raise_for_status()
    out = {}
    for x in csv.DictReader(io.StringIO(r.text)):
        i = (x.get("ISO3166-1-Alpha-2") or "").strip()
        nom = (x.get("CLDR display name") or x.get("UNTERM English Short") or "").strip()
        if len(i) == 2 and nom and (x.get("is_independent") or "").strip().lower() in ("yes", "true", "1"):
            out[i] = nom
    for i, nom in NOMS.items():
        if nom is None:
            out.pop(i, None)
        elif i in out or i in ("XK", "PS", "TW"):
            out[i] = nom
    return out


def serie(c: httpx.Client, requete: str, duree: str) -> dict[str, tuple[int, int]]:
    """Jour (AAAA-MM-JJ) → (articles, total surveillé). Après un refus « 429 », attend puis réessaie (ATTENTES_429)."""
    for attente in (*ATTENTES_429, None):
        r = c.get(API, params={"query": requete, "mode": "timelinevolraw", "timespan": duree, "format": "json"})
        if r.status_code != 429 or attente is None:
            break
        time.sleep(attente)
    r.raise_for_status()
    out = {}
    try:
        j = r.json()
    except ValueError:
        raise RuntimeError(f"réponse non JSON : {r.text[:120]}")
    for s in j.get("timeline") or []:
        for p in s.get("data") or []:
            d = str(p.get("date") or "")
            if len(d) >= 8:
                out[f"{d[:4]}-{d[4:6]}-{d[6:8]}"] = (int(p.get("value") or 0), int(p.get("norm") or 0))
    return out


def requete(nom: str, alibi: bool = False) -> str:
    return f'sourcecountry:russia "{nom}"' + (f" {MOTS_ALIBI}" if alibi else "")


def lire() -> dict[tuple, dict]:
    if not REGISTRE.exists():
        return {}
    return {(x["pays"], x["jour"]): x for x in csv.DictReader(REGISTRE.open(encoding="utf-8"))}


def ecrire(reg: dict[tuple, dict]) -> None:
    REGISTRE.parent.mkdir(exist_ok=True)
    with REGISTRE.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CHAMPS)
        w.writeheader()
        for k in sorted(reg, key=lambda k: (k[1], k[0])):
            w.writerow({c: reg[k].get(c, "") for c in CHAMPS})


def principal() -> int:
    a_ = argparse.ArgumentParser()
    a_.add_argument("--pays", default="", help="codes ISO séparés par des virgules (défaut : tous les pays indépendants)")
    a_.add_argument("--duree", default="3m")
    a = a_.parse_args()
    reg = lire()
    hier = (datetime.now(timezone.utc).date() - timedelta(days=1)).isoformat()
    il_y_a_14 = (datetime.now(timezone.utc).date() - timedelta(days=15)).isoformat()
    ok = echecs = alibis = 0
    with httpx.Client(headers=UA, timeout=45, follow_redirects=True) as c:   # 0.10.245 : 90 → 45 s par requête
        noms = pays_et_noms(c)
        # 0.10.210 : les pays les moins à jour d'abord, pour qu'un passage interrompu reprenne là où l'autre s'est arrêté
        dernier = {}
        for (p_, j_) in reg:
            dernier[p_] = max(dernier.get(p_, ""), j_)
        cibles = [p.strip().upper() for p in a.pays.split(",") if p.strip()] or sorted(noms, key=lambda p: (dernier.get(p, ""), p))
        refus = 0
        debut = time.monotonic()
        print(f"{len(cibles)} pays.", flush=True)
        for p in cibles:
            if time.monotonic() - debut > DUREE_MAX:
                print(f"  budget de {DUREE_MAX // 60} min atteint : arrêt ; le prochain passage reprendra ici.", flush=True)
                break
            nom = noms.get(p)
            if not nom:
                continue
            try:
                s = serie(c, requete(nom), a.duree)
                ok += 1
                refus = 0
            except Exception as e:
                echecs += 1
                refus = refus + 1 if "429" in str(e) else 0
                print(f"  {p} : échec ({type(e).__name__}: {str(e)[:80]})", flush=True)
                if refus >= ARRET_429:
                    print(f"  {refus} refus « 429 » d'affilée malgré les attentes : arrêt ; le prochain passage reprendra ici.")
                    break
                time.sleep(PAUSE)
                continue
            time.sleep(PAUSE)
            for j, (n, tot) in s.items():
                if j <= hier:                                   # jour en cours incomplet : jamais gardé
                    x = reg.setdefault((p, j), {"pays": p, "jour": j})
                    x.update(articles=n, total_surveille=tot)
            recent = sum(n for j, (n, _) in s.items() if il_y_a_14 < j <= hier)
            if recent >= SEUIL_ALIBI:
                try:
                    sa = serie(c, requete(nom, alibi=True), a.duree)
                    alibis += 1
                    for j in [j for j in s if j <= hier]:
                        reg[(p, j)]["alibi"] = sa.get(j, (0, 0))[0]
                except Exception as e:
                    print(f"  {p} (alibi) : échec ({type(e).__name__})")
                time.sleep(PAUSE)
            if ok % 25 == 0:
                ecrire(reg)
    ecrire(reg)
    bilan = (f"{ok} pays lus, {echecs} échec(s), {alibis} requête(s) « alibi » ; "
             f"{len({k[1] for k in reg})} jours au registre. Source : GDELT (API DOC 2.0).")
    print(bilan)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
            f.write(f"## Récit russe par pays (M12)\n\n{bilan}\n")
    if not ok:
        print("::warning::aucun pays lu (API DOC de GDELT indisponible ou saturée).")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
