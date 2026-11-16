"""Indicateurs de niche (0.10.138, décision d'auteur du 2026-11-15, 16 h 54 : « fais-le aussi pour les prix
alimentaires, ça ne coûte rien d'essayer »). AUCUN modèle de langue, aucun coût, rien de posté.

Pour chaque couple (pays, jeu) du banc des indicateurs pertinents (registre/banc-indicateurs-frais.jsonl), mesuré
STRICTEMENT avant la date du jeu :
- wikimodif : activité de MODIFICATION (pas de consultation) des pages politiques du pays sur Wikipedia anglais
  (« Politics of X », « Human rights in X », « Censorship in X », « Elections in X ») : log((modifications des 30
  derniers jours + 1) / (moyenne par 30 jours des 180 jours précédents + 1)). D'après Oswald (CISS Munich, 2026) :
  les modifications de pages politiquement sensibles aident à prévoir les manifestations.
- prix_alim : prix alimentaires de détail du Programme alimentaire mondial (HDX, « WFP food prices for X ») :
  médiane, sur les couples marché × produit, de log(dernier prix connu / prix douze mois plus tôt), en monnaie locale,
  derniers prix d'au plus 120 jours avant la date. D'après Bellemare (AJAE 2015) : la hausse des prix alimentaires
  précède les émeutes.
- vols (0.10.140, si OPENSKY_CLIENT_ID et OPENSKY_CLIENT_SECRET sont fournis) : arrivées à l'aéroport principal du pays
  (le plus grand aéroport à vols réguliers le plus proche de la capitale, base OurAirports), OpenSky Network :
  log((arrivées des 2 jours avant la date + 1) / (arrivées des 2 mêmes jours, quatre semaines plus tôt + 1))
  (OpenSky limite chaque demande à 2 jours). Idée de
  l'auteur : l'espace aérien comme signal de niche (perturbations, fermetures, fuites).
- telegram (0.10.143 ; 0.10.151 : historique des canaux VALIDÉS par l'auteur, registre/telegram-canaux.json, liste
  proposée par decouvrir_canaux_telegram.py selon une règle fixée ; la recherche globale ne remontait presque pas dans
  le passé) : messages citant le pays en anglais, log((14 jours avant la date + 1) / (14 jours précédents + 1)), au plus
  300 messages lus par canal. Idée de l'auteur : les canaux publient avant la presse ; emballement, calme ou silence.
- gdelt (0.10.173, en ombre) : manifestations et émeutes dans la presse codée par GDELT (collecte_gdelt.py), pays du
  lieu de l'action ; log((14 jours avant la date + 1) / (14 jours précédents + 1)) ; historique complet, donc mesurable
  sur les questions déjà résolues.
- violationswatch (0.10.147, en ombre) : incidents graves (gravité « High » ou « Critical ») signalés par
  violationswatch.org dans le pays, premiers signalements dans les 14 jours avant la date ; lu dans nos comptes
  quotidiens (collecte_violationswatch.py) ; mesuré seulement si ces 14 jours sont couverts (données depuis le
  2026-11-06).
- rss_presse et rss_officiel (0.10.152, en ombre) : comptes quotidiens des flux RSS (collecte_rss.py), pays reconnu
  en anglais et en français ; presse : log((articles des 14 jours avant + 1) / (14 jours précédents + 1)) ; officiel
  (ReliefWeb, avis de voyage, GDACS, USGS) : articles des 14 jours avant ; mesurés seulement sur les dates couvertes
  par la collecte (à partir du 2026-11-16).
- brouillage_gps (0.10.153) : part des zones « rouges » de gpsjam.org dans le pays, moyenne des 14 jours avant la
  date (brouillage_gps.py) ; historique depuis le 2022-02-14, donc mesurable sur les questions passées.
Les huit passent ensuite par l'observatoire inductif (`induction.py`), lot après lot, avant tout pré-enregistrement.
Registre : registre/indicateurs-niche.jsonl.

    python indicateurs_niche.py
"""
from __future__ import annotations

import asyncio
import csv
import io
import json
import math
import statistics
import sys
from datetime import date, timedelta
from pathlib import Path

import os

import httpx

SOURCE = Path("registre") / "banc-indicateurs-frais.jsonl"
FICHIER = Path("registre") / "indicateurs-niche.jsonl"
UA = {"User-Agent": "alphabet-situationnel-bot/1.0 (recherche ; GitHub Othman-Benbrahim)"}
PAGES = ("Politics of {p}", "Human rights in {p}", "Censorship in {p}", "Elections in {p}")


async def obtenir(c: httpx.AsyncClient, url: str, **kw):
    """0.10.142 : réessaie (2, 4, 8 s) quand le service limite les appels (429) ou défaille (5xx)."""
    await asyncio.sleep(0.5)
    for attente in (2, 4, 8, None):
        try:
            r = await c.get(url, timeout=30, **kw)
        except Exception:
            r = None
        if r is not None and r.status_code == 200:
            return r
        if r is not None and r.status_code not in (429, 500, 502, 503, 504):
            return None
        if attente is None:
            return None
        await asyncio.sleep(attente)


async def wikimodif(c: httpx.AsyncClient, pays: str, d0: date) -> dict:
    debut, fin = d0 - timedelta(days=210), d0 - timedelta(days=1)
    par_jour: dict[str, int] = {}
    trouvees = 0
    for modele in PAGES:
        titre = modele.format(p=pays).replace(" ", "_")
        r = await obtenir(c, f"https://wikimedia.org/api/rest_v1/metrics/edits/per-page/en.wikipedia.org/{titre}/"
                             f"all-editor-types/daily/{debut:%Y%m%d}/{fin:%Y%m%d}")
        if r is None:
            continue
        res = ((r.json().get("items") or [{}])[0].get("results") or [])
        trouvees += 1
        for e in res:
            par_jour[e["timestamp"][:10]] = par_jour.get(e["timestamp"][:10], 0) + int(e.get("edits") or 0)
    if not trouvees:
        return {"present": False, "raison": "aucune page trouvée ou service indisponible"}
    recent = sum(v for k, v in par_jour.items() if k >= (d0 - timedelta(days=30)).isoformat())
    avant = sum(v for k, v in par_jour.items() if k < (d0 - timedelta(days=30)).isoformat()) / 6
    return {"present": True, "valeur": round(math.log((recent + 1) / (avant + 1)), 4), "pages": trouvees,
            "modifs_30j": recent, "moyenne_30j_avant": round(avant, 2)}


def _csv(pk: dict) -> str | None:
    for res in pk.get("resources", []):
        if str(res.get("format", "")).lower() == "csv" and res.get("url"):
            return res["url"]
    return None


async def ressource_wfp(c: httpx.AsyncClient, pays: str, cache: dict) -> str | None:
    """0.10.142 : jeux HDX « wfp-food-prices-for-<pays> » (titres du type « Kenya - Food Prices »)."""
    import re
    if pays in cache:
        return cache[pays]
    url = None
    slug = re.sub(r"[^a-z0-9]+", "-", pays.lower().replace("'", "")).strip("-")
    r = await obtenir(c, "https://data.humdata.org/api/3/action/package_show", params={"id": f"wfp-food-prices-for-{slug}"})
    if r is not None:
        url = _csv(r.json().get("result") or {})
    if not url:
        r = await obtenir(c, "https://data.humdata.org/api/3/action/package_search",
                          params={"q": f"{pays} food prices", "fq": "organization:wfp", "rows": 10})
        if r is not None:
            for pk in r.json().get("result", {}).get("results", []):
                t = pk.get("title", "").lower()
                if pays.lower() in t and "food prices" in t:
                    url = _csv(pk)
                    if url:
                        break
    cache[pays] = url
    return url


async def prix_alim(c: httpx.AsyncClient, pays: str, d0: date, cache: dict, cache_csv: dict) -> dict:
    url = await ressource_wfp(c, pays, cache)
    if not url:
        return {"present": False, "raison": "pas de jeu WFP"}
    if url not in cache_csv:
        r = await obtenir(c, url, follow_redirects=True)
        cache_csv[url] = r.text if r is not None else None
    texte = cache_csv[url]
    if not texte:
        return {"present": False, "raison": "téléchargement impossible"}
    series: dict[tuple, list[tuple[date, float]]] = {}
    for ligne in csv.DictReader(io.StringIO(texte)):
        try:
            d = date.fromisoformat(str(ligne.get("date", ""))[:10])
            p = float(ligne.get("price") or "nan")
        except ValueError:
            continue                                  # ligne d'étiquettes HXL ou date illisible
        if d >= d0 or not p > 0 or str(ligne.get("pricetype", "")).lower() != "retail":
            continue
        series.setdefault((ligne.get("market"), ligne.get("commodity"), ligne.get("unit")), []).append((d, p))
    changes = []
    for pts in series.values():
        pts.sort()
        d_last, p_last = pts[-1]
        if (d0 - d_last).days > 120:
            continue
        cible = d_last - timedelta(days=365)
        anciens = [x for x in pts if abs((x[0] - cible).days) <= 45]
        if anciens:
            p_old = min(anciens, key=lambda x: abs((x[0] - cible).days))[1]
            changes.append(math.log(p_last / p_old))
    if len(changes) < 3:
        return {"present": False, "raison": f"{len(changes)} séries utilisables"}
    return {"present": True, "valeur": round(statistics.median(changes), 4), "series": len(changes)}


OURAIRPORTS = "https://davidmegginson.github.io/ourairports-data/airports.csv"
OURAIRPORTS_PAYS = "https://davidmegginson.github.io/ourairports-data/countries.csv"
JETON_URL = "https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token"


class OpenSky:
    """Accès OpenSky par client API (OAuth2, « client credentials ») ; jeton renouvelé avant expiration."""

    def __init__(self, c: httpx.AsyncClient):
        self.c = c
        self.id = os.environ.get("OPENSKY_CLIENT_ID", "").strip()
        self.secret = os.environ.get("OPENSKY_CLIENT_SECRET", "").strip()
        self.jeton, self.expire = None, 0.0
        self.aeroports: list[dict] | None = None
        self.codes_pays: dict[str, str] | None = None
        self.derniere_erreur = ""

    async def code_pays(self, nom: str) -> str | None:
        """0.10.144 : code ISO du pays par la table d'OurAirports (même source que les aéroports, stable)."""
        if self.codes_pays is None:
            r = await obtenir(self.c, OURAIRPORTS_PAYS)
            self.codes_pays = {}
            for x in (csv.DictReader(io.StringIO(r.text)) if r is not None else []):
                self.codes_pays[x["name"].lower()] = x["code"]
                for k in (x.get("keywords") or "").split(","):
                    if k.strip():
                        self.codes_pays.setdefault(k.strip().lower(), x["code"])
        n = nom.lower()
        alias = {"ivory coast": "côte d'ivoire", "democratic republic of congo": "congo (kinshasa)",
                 "republic of congo": "congo (brazzaville)", "czech republic": "czechia", "curacao": "curaçao"}
        return self.codes_pays.get(n) or self.codes_pays.get(alias.get(n, ""))

    @property
    def disponible(self) -> bool:
        return bool(self.id and self.secret)

    async def entete(self) -> dict:
        import time
        if not self.jeton or time.time() > self.expire - 60:
            r = await self.c.post(JETON_URL, data={"grant_type": "client_credentials", "client_id": self.id,
                                                   "client_secret": self.secret}, timeout=30)
            r.raise_for_status()
            j = r.json()
            self.jeton, self.expire = j["access_token"], time.time() + float(j.get("expires_in", 1800))
        return {"Authorization": f"Bearer {self.jeton}"}

    async def aeroport(self, cca2: str | None, latlng) -> str | None:
        if not cca2:
            return None
        if self.aeroports is None:
            r = await obtenir(self.c, OURAIRPORTS)
            self.aeroports = list(csv.DictReader(io.StringIO(r.text))) if r is not None else []
        cand = [a for a in self.aeroports if a.get("iso_country") == cca2 and a.get("type") == "large_airport"
                and a.get("scheduled_service") == "yes" and len(a.get("ident", "")) == 4]
        if not cand:
            cand = [a for a in self.aeroports if a.get("iso_country") == cca2 and a.get("type") == "medium_airport"
                    and a.get("scheduled_service") == "yes" and len(a.get("ident", "")) == 4]
        if not cand:
            return None
        if latlng:
            la, lo = float(latlng[0]), float(latlng[1])
            cand.sort(key=lambda a: (float(a["latitude_deg"]) - la) ** 2 + (float(a["longitude_deg"]) - lo) ** 2)
        return cand[0]["ident"]

    async def arrivees(self, icao: str, debut: date, fin: date) -> int | None:
        from datetime import datetime, timezone
        b = int(datetime(debut.year, debut.month, debut.day, tzinfo=timezone.utc).timestamp())
        e = int(datetime(fin.year, fin.month, fin.day, tzinfo=timezone.utc).timestamp())
        try:
            r = await self.c.get("https://opensky-network.org/api/flights/arrival",
                                 params={"airport": icao, "begin": b, "end": e}, headers=await self.entete(), timeout=60)
        except Exception:
            return None
        if r.status_code == 404:
            return 0                                  # OpenSky répond 404 quand aucun vol n'est trouvé
        if r.status_code != 200:
            self.derniere_erreur = f"HTTP {r.status_code} : {r.text[:150]}"
            return None
        return len(r.json() or [])


async def vols(os_: OpenSky, c: httpx.AsyncClient, pays: str, d0: date, cache_pays: dict) -> dict:
    import banc_indicateurs as bi
    f = await bi.fiche_pays(c, pays, cache_pays)
    icao = await os_.aeroport(await os_.code_pays(pays) or f.get("cca2"), f.get("latlng"))
    if not icao:
        return {"present": False, "raison": "aucun aéroport"}
    # 0.10.144 : OpenSky n'accepte que 2 jours par demande (« only query across 2 partitions ») : 2 jours avant la
    # date contre les 2 mêmes jours de la semaine, quatre semaines plus tôt
    recent = await os_.arrivees(icao, d0 - timedelta(days=2), d0)
    avant = await os_.arrivees(icao, d0 - timedelta(days=30), d0 - timedelta(days=28))
    if recent is None or avant is None:
        return {"present": False, "raison": "OpenSky indisponible", "aeroport": icao, "detail": os_.derniere_erreur}
    if recent == 0 and avant == 0:                    # 0.10.145 : pas de récepteurs OpenSky dans la région, pas un aéroport fermé
        return {"present": False, "raison": "aucun vol enregistré (couverture OpenSky)", "aeroport": icao}
    return {"present": True, "valeur": round(math.log((recent + 1) / (avant + 1)), 4), "aeroport": icao,
            "arrivees_2j": recent, "arrivees_2j_quatre_semaines_avant": avant}


class Telegram:
    """Lecture seule de la recherche globale de Telegram (Telethon, session de l'auteur)."""

    def __init__(self):
        self.id = os.environ.get("TELEGRAM_API_ID", "").strip().strip("\"'")
        self.hash = os.environ.get("TELEGRAM_API_HASH", "").strip().strip("\"'")
        import re
        # 0.10.146 : la clé collée depuis PowerShell peut contenir des retours à la ligne, des espaces ou des guillemets
        brut = re.sub(r"\s+", "", os.environ.get("TELEGRAM_SESSION", "")).strip("\"'")
        # 0.10.148 : si l'en-tête « === CLÉ DE SESSION … === » a été collé avec la clé, on ne garde que la clé elle-même
        # (une longue suite qui commence par « 1 », alphabet base64 ; elle peut finir par « = », c'est normal)
        brut = re.sub(r"===[^=]*?===", "", brut)          # en-tête et pied « === … === » retirés d'abord
        m = re.search(r"1[A-Za-z0-9+/_-]{200,}={0,2}", brut)
        self.session = m.group(0) if m else brut
        self.client = None
        self.derniere_erreur = ""

    @property
    def disponible(self) -> bool:
        return bool(self.id and self.hash and self.session)

    async def ouvrir(self) -> bool:
        try:
            from telethon import TelegramClient
            from telethon.sessions import StringSession
            self.client = TelegramClient(StringSession(self.session), int(self.id), self.hash, flood_sleep_threshold=120)
            await self.client.connect()
            if not await self.client.is_user_authorized():
                self.derniere_erreur = "session non autorisée"
                return False
            return True
        except Exception as e:
            self.derniere_erreur = (f"{type(e).__name__}: {e}"[:200] + f" ; clé de {len(self.session)} caractères, "
                                    f"commence par « {self.session[:1]} » (une clé valide commence par « 1 » et fait environ 350 caractères)")
            return False

    async def fermer(self):
        if self.client is not None:
            await self.client.disconnect()

    async def compter(self, canaux: list[str], terme: str, d0: date, plafond: int = 300) -> tuple[int, int] | None:
        """0.10.151 : historique des canaux validés (la recherche globale ne remonte presque pas dans le passé)."""
        from datetime import datetime, timezone
        fin = datetime(d0.year, d0.month, d0.day, tzinfo=timezone.utc)
        coupure, debut = fin - timedelta(days=14), fin - timedelta(days=28)
        recent = avant = 0
        lus_ok = 0
        for canal in canaux:
            lus = 0
            try:
                async for m in self.client.iter_messages(canal, search=terme, offset_date=fin):
                    lus += 1
                    if m.date < debut or lus > plafond:
                        break
                    if m.date >= coupure:
                        recent += 1
                    else:
                        avant += 1
                lus_ok += 1
            except Exception as e:
                self.derniere_erreur = f"@{canal} : {type(e).__name__}: {e}"[:200]
        if not lus_ok:
            return None
        return recent, avant


CANAUX_VALIDES = Path("registre") / "telegram-canaux.json"


def canaux_valides() -> list[str]:
    if not CANAUX_VALIDES.exists():
        return []
    d = json.loads(CANAUX_VALIDES.read_text(encoding="utf-8"))
    return [c["canal"] if isinstance(c, dict) else str(c) for c in (d.get("canaux") or [])]


async def telegram(tg: Telegram, pays: str, d0: date) -> dict:
    canaux = canaux_valides()
    if not canaux:
        return {"present": False, "raison": "liste de canaux non validée (registre/telegram-canaux.json)"}
    r = await tg.compter(canaux, pays, d0)
    if r is None:
        return {"present": False, "raison": "Telegram indisponible", "detail": tg.derniere_erreur}
    recent, avant = r
    return {"present": True, "methode": "canaux", "canaux": len(canaux),
            "valeur": round(math.log((recent + 1) / (avant + 1)), 4), "messages_14j": recent, "messages_14j_avant": avant}


GDELT_COMPTES = Path("registre") / "gdelt-manifestations.csv"
GDELT_JOURS = Path("registre") / "gdelt-jours.txt"
_GDELT: dict | None = None


def gdelt(cca2: str | None, d0: date, manque_max: int = 2) -> dict:
    """0.10.173 : manifestations (code CAMEO 14) et émeutes (145) dans la presse codée par GDELT, pays du lieu de
    l'action ; log((14 jours avant la date + 1) / (14 jours précédents + 1)). Mesuré seulement si au plus `manque_max`
    des 28 jours manquent (collecte_gdelt.py)."""
    global _GDELT
    if not cca2 or not GDELT_COMPTES.exists() or not GDELT_JOURS.exists():
        return {"present": False, "raison": "pays inconnu ou comptes GDELT absents"}
    if _GDELT is None:
        par = {}
        for x in csv.DictReader(GDELT_COMPTES.open(encoding="utf-8")):
            par.setdefault(x["pays"], {})[x["jour"]] = (int(x["manifestations"]), int(x["emeutes"]))
        _GDELT = {"par": par, "jours": set(GDELT_JOURS.read_text(encoding="utf-8").split())}
    jours = [(d0 - timedelta(days=k)).isoformat() for k in range(1, 29)]
    manque = sum(1 for j in jours if j not in _GDELT["jours"])
    if manque > manque_max:
        return {"present": False, "raison": f"{manque} jours GDELT manquants sur 28"}
    p = _GDELT["par"].get(cca2, {})
    rec = [p.get(j, (0, 0)) for j in jours[:14]]
    av = [p.get(j, (0, 0)) for j in jours[14:]]
    m_r, m_a = sum(x[0] for x in rec), sum(x[0] for x in av)
    e_r, e_a = sum(x[1] for x in rec), sum(x[1] for x in av)
    return {"present": True, "valeur": round(math.log((m_r + 1) / (m_a + 1)), 4),
            "valeur_emeutes": round(math.log((e_r + 1) / (e_a + 1)), 4),
            "manifestations_14j": m_r, "manifestations_14j_avant": m_a, "emeutes_14j": e_r, "emeutes_14j_avant": e_a,
            "jours_manquants": manque}


RSS_COMPTES = Path("registre") / "rss-comptes.csv"
RSS_DEBUT = date(2026, 11, 16)


def rss(cca2: str | None, d0: date) -> tuple[dict, dict]:
    absent = {"present": False, "raison": "période non couverte ou pays inconnu"}
    if not cca2 or not RSS_COMPTES.exists() or d0 - timedelta(days=14) < RSS_DEBUT:
        return absent, absent
    rec = av = off = pe = ren = san = vc = tt = eco = nota = 0
    for x in csv.DictReader(RSS_COMPTES.open(encoding="utf-8")):
        if x["pays"] != cca2:
            continue
        j = date.fromisoformat(x["jour"])
        n = int(x["articles"])
        if x["famille"] == "officiel" and d0 - timedelta(days=14) <= j < d0:
            off += n
        if x["famille"] == "parlement_ue" and d0 - timedelta(days=14) <= j < d0:
            pe += n
        if x["famille"] == "renseignement" and d0 - timedelta(days=14) <= j < d0:
            ren += n
        if x["famille"] == "sante" and d0 - timedelta(days=14) <= j < d0:
            san += n
        if x["famille"] == "voix_citoyennes" and d0 - timedelta(days=14) <= j < d0:
            vc += n
        if x["famille"] == "think_tanks" and d0 - timedelta(days=14) <= j < d0:
            tt += n
        if x["famille"] == "economie" and d0 - timedelta(days=14) <= j < d0:
            eco += n
        if x["famille"] == "notation" and d0 - timedelta(days=14) <= j < d0:
            nota += n
        if x["famille"] == "presse":
            if d0 - timedelta(days=14) <= j < d0:
                rec += n
            elif d0 - timedelta(days=28) <= j < d0 - timedelta(days=14):
                av += n
    presse = ({"present": True, "valeur": round(math.log((rec + 1) / (av + 1)), 4), "articles_14j": rec, "articles_14j_avant": av}
              if d0 - timedelta(days=28) >= RSS_DEBUT else absent)
    return presse, {"present": True, "valeur": float(off), "articles_officiels_14j": off, "parlement_ue_14j": pe,
                    "renseignement_14j": ren, "sante_14j": san, "voix_citoyennes_14j": vc,
                    "think_tanks_14j": tt, "economie_14j": eco, "notation_14j": nota}


async def principal() -> int:
    if not SOURCE.exists():
        print("Pas de registre source.")
        return 1
    lignes = [json.loads(l) for l in SOURCE.read_text(encoding="utf-8").splitlines() if l.strip()]
    mesures: dict[tuple, set] = {}
    if FICHIER.exists():
        for l in FICHIER.read_text(encoding="utf-8").splitlines():
            if l.strip():
                x = json.loads(l)
                # 0.10.142 : seule une mesure réussie compte comme faite ; les échecs sont retentés
                mesures.setdefault((x["pays"], x["jeu"]), set()).update(
                    k for k in ("wikimodif", "prix_alim", "vols", "telegram", "violationswatch", "rss_presse", "rss_officiel", "brouillage_gps", "gdelt") if (x.get(k) or {}).get("present")
                    and (k != "telegram" or x[k].get("methode") == "canaux"))
    couples = sorted({(x["pays"], x["jeu"]) for x in lignes if x.get("pays")})
    cache, cache_csv, cache_pays = {}, {}, {}
    async with httpx.AsyncClient(headers=UA, follow_redirects=True) as c:
        os_ = OpenSky(c)
        import brouillage_gps as bg
        gps = bg.Brouillage(obtenir)
        essai = await gps.jour(c, date(2026, 6, 1)) if await gps.preparer(c) else None
        print(f"gpsjam.org : {'fichiers quotidiens lus (' + str(len(essai)) + ' pays le 2026-06-01)' if essai else 'indisponible (' + (gps.erreur or 'aucune réponse') + ')'}.")
        if os_.disponible:                          # vérification du client API au démarrage
            try:
                await os_.entete()
            except Exception as e:
                print(f"OpenSky : jeton refusé ({type(e).__name__}) ; vérifier OPENSKY_CLIENT_ID et OPENSKY_CLIENT_SECRET.")
                os_.id = ""
        tg = Telegram()
        if tg.disponible and not await tg.ouvrir():
            print(f"Telegram : connexion refusée ({tg.derniere_erreur}) ; vérifier les trois secrets TELEGRAM_*.")
            tg.session = ""
        print(f"{len(couples)} couples pays × jeu ; OpenSky {'disponible' if os_.disponible else 'non configuré'} ; "
              f"Telegram {'disponible' if tg.disponible else 'non configuré'}.")
        with FICHIER.open("a", encoding="utf-8") as f:
            for pays, jeu in couples:
                fait = mesures.get((pays, jeu), set())
                d0 = date.fromisoformat(jeu)
                ligne = {"pays": pays, "jeu": jeu}
                if "wikimodif" not in fait:
                    ligne["wikimodif"] = await wikimodif(c, pays, d0)
                if "prix_alim" not in fait:
                    ligne["prix_alim"] = await prix_alim(c, pays, d0, cache, cache_csv)
                if "vols" not in fait and os_.disponible:
                    ligne["vols"] = await vols(os_, c, pays, d0, cache_pays)
                if "telegram" not in fait and tg.disponible and canaux_valides():
                    ligne["telegram"] = await telegram(tg, pays, d0)
                if "violationswatch" not in fait and d0 - timedelta(days=14) >= VW_DEBUT:
                    ligne["violationswatch"] = violationswatch(pays, d0)
                if "brouillage_gps" not in fait and essai:
                    code_g = await os_.code_pays(pays) or (await __import__("banc_indicateurs").fiche_pays(c, pays, cache_pays)).get("cca2")
                    ligne["brouillage_gps"] = await gps.mesure(c, code_g, d0)
                if "gdelt" not in fait and GDELT_JOURS.exists():
                    code = await os_.code_pays(pays) or (await __import__("banc_indicateurs").fiche_pays(c, pays, cache_pays)).get("cca2")
                    ligne["gdelt"] = gdelt(code, d0)
                if ("rss_officiel" not in fait or "rss_presse" not in fait) and d0 - timedelta(days=14) >= RSS_DEBUT:
                    code = await os_.code_pays(pays) or (await __import__("banc_indicateurs").fiche_pays(c, pays, cache_pays)).get("cca2")
                    ligne["rss_presse"], ligne["rss_officiel"] = rss(code, d0)
                if len(ligne) == 2:
                    continue
                f.write(json.dumps(ligne, ensure_ascii=False) + "\n")
                f.flush()
                print(f"{pays[:22]:22s} {jeu} : " + " · ".join(f"{k} {(ligne[k] or {}).get('valeur')}"
                                                            for k in ("wikimodif", "prix_alim", "vols", "telegram", "violationswatch", "rss_presse", "rss_officiel", "brouillage_gps", "gdelt") if k in ligne))
        await tg.fermer()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(principal()))
