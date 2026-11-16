"""Feux et anomalies thermiques par pays, vus par satellite (NASA FIRMS ; bot 0.10.208, en ombre).

Décision d'auteur du 2026-11-16 (22 h 07), après la revue de la boîte à outils de Bellingcat. En zone de conflit, une
hausse brutale des points chauds signale frappes, incendies de villages ou de dépôts, combats ; ailleurs, elle suit
surtout les brûlis agricoles (saisonniers) : d'où le rapport à la quinzaine précédente et le jugement par
l'observatoire, jamais une lecture directe.

Source : API « country » de FIRMS (NASA, données publiques, clé gratuite FIRMS_MAP_KEY) :
https://firms.modaps.eosdis.nasa.gov/api/country/csv/{clé}/{source}/{ISO3}/{jours}/{date}
Capteur : VIIRS ; pour chaque fenêtre, le premier produit qui la couvre selon les dates publiées par FIRMS
(data_availability), archive standard (SP) avant temps quasi réel (NRT) ; aucun produit : fenêtre ignorée. Fenêtres de JOURS jours ; une requête par pays et par fenêtre ; limite de l'API : 5 000 requêtes par 10 minutes.

On garde des COMPTES : pays, jour, detections, forte_confiance (confiance « h »).
Registres : registre/feux.csv ; registre/feux-jours.txt (jours lus pour TOUS les pays).
Usage : python collecte_feux.py [--depuis AAAA-MM-JJ] [--pays FR,UA]   (par défaut : les 10 derniers jours)
"""
from __future__ import annotations

import argparse
import csv
import io
import os
import sys
import time
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import httpx

API = "https://firms.modaps.eosdis.nasa.gov/api/country/csv/{cle}/{source}/{pays}/{jours}/{date}"
CODES = "https://raw.githubusercontent.com/datasets/country-codes/main/data/country-codes.csv"
REGISTRE = Path("registre") / "feux.csv"
JOURS_LUS = Path("registre") / "feux-jours.txt"
JOURS = 5
PAUSE = 0.15                   # environ 400 requêtes par minute, sous la limite de l'API
UA = {"User-Agent": "alphabet-situationnel-bot/1.0 (recherche ; GitHub Othman-Benbrahim)"}


def pays_iso(c: httpx.Client) -> dict[str, str]:
    """ISO3 → ISO2 des pays indépendants."""
    r = c.get(CODES, timeout=60)
    r.raise_for_status()
    return {x["ISO3166-1-Alpha-3"].strip(): x["ISO3166-1-Alpha-2"].strip() for x in csv.DictReader(io.StringIO(r.text))
            if len((x.get("ISO3166-1-Alpha-3") or "").strip()) == 3 and len((x.get("ISO3166-1-Alpha-2") or "").strip()) == 2
            and (x.get("is_independent") or "").strip().lower() in ("yes", "true", "1")}


def compter(texte: str) -> dict[str, list[int]]:
    """CSV FIRMS → jour (acq_date) : [détections, confiance forte]."""
    out: dict[str, list[int]] = {}
    for x in csv.DictReader(io.StringIO(texte)):
        j = (x.get("acq_date") or "")[:10]
        if len(j) != 10:
            continue
        v = out.setdefault(j, [0, 0])
        v[0] += 1
        v[1] += str(x.get("confidence") or "").strip().lower() in ("h", "high")
    return out


DISPO = "https://firms.modaps.eosdis.nasa.gov/api/data_availability/csv/{cle}/ALL"
# ordre de préférence (même logique que la source « firms » du puits, 0.10.94) : le même capteur d'abord, archive
# standard avant temps quasi réel
ORDRE = ("VIIRS_SNPP_SP", "VIIRS_SNPP_NRT", "VIIRS_NOAA20_SP", "VIIRS_NOAA20_NRT", "VIIRS_NOAA21_NRT")


def plages(texte: str) -> dict[str, tuple[str, str]]:
    return {r.get("data_id"): (r.get("min_date") or "", r.get("max_date") or "")
            for r in csv.DictReader(io.StringIO(texte)) if r.get("data_id")}


def source_pour(debut: str, fin: str, dispo: dict[str, tuple[str, str]]) -> str | None:
    """Premier produit qui couvre toute la fenêtre ; None si aucun (données pas encore publiées)."""
    for c in ORDRE:
        lo, hi = dispo.get(c) or ("", "")
        if lo and hi and lo <= debut and fin <= hi:
            return c
    return None


def lire() -> dict[tuple, list[int]]:
    if not REGISTRE.exists():
        return {}
    return {(x["pays"], x["jour"]): [int(x["detections"]), int(x["forte_confiance"])]
            for x in csv.DictReader(REGISTRE.open(encoding="utf-8"))}


def ecrire(reg: dict[tuple, list[int]], jours: set[str]) -> None:
    REGISTRE.parent.mkdir(exist_ok=True)
    with REGISTRE.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["pays", "jour", "detections", "forte_confiance"])
        for (p, j), v in sorted(reg.items(), key=lambda t: (t[0][1], t[0][0])):
            w.writerow([p, j, *v])
    JOURS_LUS.write_text("\n".join(sorted(jours)) + "\n", encoding="utf-8")


def principal() -> int:
    a_ = argparse.ArgumentParser()
    a_.add_argument("--depuis", default="")
    a_.add_argument("--pays", default="")
    a = a_.parse_args()
    cle = os.environ.get("FIRMS_MAP_KEY", "").strip()
    if not cle:
        print("Clé FIRMS absente (secret FIRMS_MAP_KEY) : rien à faire.")
        return 1
    aujourdhui = datetime.now(timezone.utc).date()
    hier = aujourdhui - timedelta(days=1)
    debut = date.fromisoformat(a.depuis) if a.depuis else aujourdhui - timedelta(days=10)
    reg = lire()
    jours = set(JOURS_LUS.read_text(encoding="utf-8").split()) if JOURS_LUS.exists() else set()
    requetes = echecs = 0
    with httpx.Client(headers=UA, timeout=120, follow_redirects=True) as c:
        iso = pays_iso(c)
        dispo = plages(c.get(DISPO.format(cle=cle)).text)
        print("Produits FIRMS :", ", ".join(f"{k} {v[0]}→{v[1]}" for k, v in dispo.items() if k in ORDRE))
        cibles = {k: v for k, v in iso.items() if not a.pays or v in a.pays.upper().split(",")}
        print(f"{len(cibles)} pays.")
        d = debut
        while d <= hier:
            fin = min(d + timedelta(days=JOURS - 1), hier)
            fenetre = [(d + timedelta(days=k)).isoformat() for k in range((fin - d).days + 1)]
            if all(j in jours for j in fenetre) and not a.pays:
                d = fin + timedelta(days=1)
                continue
            produit = source_pour(fenetre[0], fenetre[-1], dispo)
            if not produit:
                print(f"  fenêtre {fenetre[0]} → {fenetre[-1]} : aucun produit FIRMS ne la couvre ; ignorée")
                d = fin + timedelta(days=1)
                continue
            ok, tampon = True, {}
            for i3, i2 in cibles.items():
                url = API.format(cle=cle, source=produit, pays=i3, jours=len(fenetre), date=d.isoformat())
                try:
                    r = c.get(url)
                    requetes += 1
                    if r.status_code != 200 or r.text.lower().startswith(("invalid", "error")):
                        raise RuntimeError(f"HTTP {r.status_code} {r.text[:80]}")
                    par_jour = compter(r.text)
                    for j in fenetre:
                        tampon[(i2, j)] = par_jour.get(j, [0, 0])
                except Exception as e:
                    ok = False
                    echecs += 1
                    if echecs <= 5:
                        print(f"  {i3} {d} : {type(e).__name__}: {str(e)[:100]}")
                time.sleep(PAUSE)
            # garde : une fenêtre sans AUCUN point chaud dans le monde veut dire « données pas encore publiées »
            # (archive standard en retard), jamais « zéro feu » : rien n'est gardé, la fenêtre sera relue
            if sum(v[0] for v in tampon.values()) == 0:
                ok = False
                print(f"  fenêtre {fenetre[0]} : aucune détection dans le monde, données non publiées ; ignorée")
            else:
                reg.update(tampon)
            if ok and not a.pays:
                jours.update(fenetre)
            print(f"  fenêtre {fenetre[0]} → {fenetre[-1]} ({produit}) : {'complète' if ok else 'incomplète'}")
            ecrire(reg, jours)
            d = fin + timedelta(days=1)
    ecrire(reg, jours)
    recents = Counter()
    for (p, j), v in reg.items():
        if j >= (hier - timedelta(days=13)).isoformat():
            recents[p] += v[0]
    bilan = (f"{requetes} requête(s), {echecs} échec(s) ; {len(jours)} jours complets au registre. "
             f"Pays les plus touchés sur 14 jours : {dict(recents.most_common(8))}. Source : NASA FIRMS (VIIRS).")
    print(bilan)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
            f.write(f"## Feux par pays (NASA FIRMS)\n\n{bilan}\n")
    return 0 if requetes and echecs < requetes else 1


if __name__ == "__main__":
    sys.exit(principal())
