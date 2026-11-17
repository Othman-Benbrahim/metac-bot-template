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
- avions_etat (0.10.180, en ombre) : vols d'avions d'État de régimes autoritaires (plane-alert-db, catégorie
  « Dictator Alert » ; vols OpenSky) arrivés dans le pays depuis l'étranger dans les 14 jours ; comptes seulement.
- elections (0.10.179, en ombre) : élections nationales du pays (Wikidata, CC0) dans les 30 jours avant la date, et
  prévues dans les 30 jours après (fuite possible pour les élections anticipées, déclarée).
- sanctions (0.10.178, en ombre) : désignations visant le pays (OFAC, liste britannique) dans les 14 jours avant la
  date (collecte_sanctions.py).
- radar (0.10.177, en ombre) : coupures d'internet signalées par Cloudflare Radar (CC BY-NC 4.0), commencées dans
  les 14 jours avant la date ; total, décidées par l'État ou militaires, pannes électriques.
- portwatch (0.10.176, en ombre) : passages de navires dans les détroits liés au pays (IMF PortWatch), décalés d'une
  semaine pour le délai de publication ; log(14 jours / 14 jours précédents).
- recit_russe (0.10.202, en ombre, fiche M12) : articles de sources russes qui nomment le pays (GDELT DOC), log(14 jours
  / 14 jours précédents), et part « alibi » (provocation, mise en scène, faux drapeau).
- dates_memoire (0.10.202, en ombre, fiche M14) : dates de mémoire du calendrier fixe dans les 14 jours à partir de
  la date (pays baltes, Russie, Ukraine, Moldavie, Géorgie, Pologne, Norvège).
- contremesures_chine (0.10.205, en ombre, module Chine, couche 2) : sanctions, embargos, boycotts chinois visant le
  pays dans les 90 jours (GDELT, code CAMEO 163, acteur chinois, pays visé).
- avis_navigation (0.10.206, en ombre, module Chine, couche 3) : avertissements de navigation militaires en zone
  chinoise concernant le pays, émis dans les 14 jours (NGA, HYDROPAC).
- force_chinoise (0.10.224, en ombre, module Chine, couche 3, relais de avis_navigation) : démonstrations de force
  chinoises visant le pays dans les 14 jours (GDELT, racine CAMEO 15, acteur chinois → pays).
- feux (0.10.208, en ombre) : points chauds détectés par satellite (NASA FIRMS, VIIRS), log(14 jours / 14 jours
  précédents).
- silence_statistique (0.10.209, en ombre, fiche M15) : publications prévues du Bureau national des statistiques
  chinois parues en retard ou absentes dans les 30 jours (Chine seulement).
- prix_alimentaires (0.10.214, en ombre) : inflation alimentaire sur un an et accélération sur trois mois
  (Banque mondiale, RTFP, 37 pays surtout fragiles ; dernière version publiée avant la date).
- acaps (0.10.196, en ombre) : risques nouveaux émis par les analystes d'ACAPS pour le pays dans les 180 jours avant
  la date (date d'entrée et pays seulement, champs non révisés) ; source ACAPS.
- voisins (0.10.186, en ombre, fiche M11) : manifestations et émeutes de GDELT dans les pays frontaliers (GeoNames,
  CC BY 4.0), 14 jours contre 14 jours précédents ; diffusion spatiale par contagion de proximité.
- ooni (0.10.175, en ombre) : censure d'internet (OONI, CC BY-NC-SA 4.0) : part des mesures anormales sur 14 jours
  moins la même part sur les 14 jours précédents, sites web et messageries à part ; absent sous un minimum de mesures.
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


VOISINS_URL = "https://download.geonames.org/export/dump/countryInfo.txt"
VOISINS = Path("registre") / "voisins.json"
_VOISINS: dict | None = None


def lire_voisins_geonames(texte: str) -> dict[str, list[str]]:
    """countryInfo.txt de GeoNames (CC BY 4.0) : colonne 0 = code ISO, dernière colonne utile = voisins (« FR,DE »)."""
    out = {}
    for l in texte.splitlines():
        if not l or l.startswith("#"):
            continue
        c = l.split("\t")
        if len(c) > 17 and len(c[0]) == 2:
            out[c[0]] = [v for v in c[17].split(",") if len(v) == 2]
    return out


def voisins(cca2: str) -> list[str]:
    """0.10.186 : pays frontaliers (GeoNames), mis en cache dans registre/voisins.json au premier besoin."""
    global _VOISINS
    if _VOISINS is None:
        if VOISINS.exists():
            _VOISINS = json.loads(VOISINS.read_text(encoding="utf-8"))
        else:
            try:
                r = httpx.get(VOISINS_URL, timeout=60, follow_redirects=True)
                r.raise_for_status()
                _VOISINS = lire_voisins_geonames(r.text)
                if len(_VOISINS) > 200:
                    VOISINS.parent.mkdir(exist_ok=True)
                    VOISINS.write_text(json.dumps(_VOISINS, ensure_ascii=False, sort_keys=True), encoding="utf-8")
            except Exception:
                _VOISINS = {}
    return _VOISINS.get(cca2, [])


def voisins_gdelt(cca2: str | None, d0: date, manque_max: int = 2) -> dict:
    """0.10.186, fiche M11 (diffusion spatiale, Hägerstrand ; contagion des manifestations entre pays voisins) :
    manifestations et émeutes de GDELT dans les pays FRONTALIERS, 14 jours avant la date contre les 14 précédents ;
    log((récent + 1) / (avant + 1)). Absent pour un pays sans voisin terrestre."""
    if not cca2:
        return {"present": False, "raison": "pays inconnu"}
    vs = voisins(cca2)
    if not vs:
        return {"present": False, "raison": "aucun pays frontalier connu (île ou table absente)"}
    sous = [gdelt(v, d0, manque_max) for v in vs]
    if not any(s.get("present") for s in sous):
        return {"present": False, "raison": (sous[0] or {}).get("raison", "GDELT absent")}
    ok = [s for s in sous if s.get("present")]
    m_r, m_a = sum(s["manifestations_14j"] for s in ok), sum(s["manifestations_14j_avant"] for s in ok)
    e_r, e_a = sum(s["emeutes_14j"] for s in ok), sum(s["emeutes_14j_avant"] for s in ok)
    return {"present": True, "valeur": round(math.log((m_r + 1) / (m_a + 1)), 4),
            "valeur_emeutes": round(math.log((e_r + 1) / (e_a + 1)), 4), "voisins": vs,
            "manifestations_14j": m_r, "manifestations_14j_avant": m_a}


OONI_COMPTES = Path("registre") / "ooni-censure.csv"
OONI_JOURS = Path("registre") / "ooni-jours.txt"
_OONI: dict | None = None


def ooni(cca2: str | None, d0: date, min_web: int = 50, min_msg: int = 20, manque_max: int = 2) -> dict:
    """0.10.175 : censure (OONI) : part des mesures anormales sur 14 jours avant la date, moins la même part sur les
    14 jours précédents ; sites web (web_connectivity) et messageries (Telegram, WhatsApp, Signal, Messenger) à part.
    Absent sous `min_web` (`min_msg`) mesures dans l'une des deux périodes (réserve de l'auteur : volontaires)."""
    global _OONI
    if not cca2 or not OONI_COMPTES.exists() or not OONI_JOURS.exists():
        return {"present": False, "raison": "pays inconnu ou comptes OONI absents"}
    if _OONI is None:
        par = {}
        for x in csv.DictReader(OONI_COMPTES.open(encoding="utf-8")):
            g = "web" if x["test"] == "web_connectivity" else "msg"
            v = par.setdefault(x["pays"], {}).setdefault((x["jour"], g), [0, 0, 0])
            v[0] += int(x["mesures"]); v[1] += int(x["anomalies"]); v[2] += int(x["confirmees"])
        _OONI = {"par": par, "jours": set(OONI_JOURS.read_text(encoding="utf-8").split())}
    jours = [(d0 - timedelta(days=k)).isoformat() for k in range(1, 29)]
    manque = sum(1 for j in jours if j not in _OONI["jours"])
    if manque > manque_max:
        return {"present": False, "raison": f"{manque} jours OONI manquants sur 28"}
    p = _OONI["par"].get(cca2, {})

    def somme(js, g):
        s = [0, 0, 0]
        for j in js:
            v = p.get((j, g))
            if v:
                s = [s[0] + v[0], s[1] + v[1], s[2] + v[2]]
        return s

    out = {"present": False, "raison": "trop peu de mesures OONI"}
    w_r, w_a = somme(jours[:14], "web"), somme(jours[14:], "web")
    m_r, m_a = somme(jours[:14], "msg"), somme(jours[14:], "msg")
    if w_r[0] >= min_web and w_a[0] >= min_web:
        out = {"present": True, "valeur": round(w_r[1] / w_r[0] - w_a[1] / w_a[0], 4),
               "mesures_web_14j": w_r[0], "mesures_web_14j_avant": w_a[0], "confirmees_web_14j": w_r[2]}
    if m_r[0] >= min_msg and m_a[0] >= min_msg:
        out = {**(out if out.get("present") else {"present": True}),
               "valeur_messageries": round(m_r[1] / m_r[0] - m_a[1] / m_a[0], 4),
               "mesures_msg_14j": m_r[0], "mesures_msg_14j_avant": m_a[0], "confirmees_msg_14j": m_r[2]}
        out.setdefault("valeur", None)
    return out


PORTWATCH = Path("registre") / "portwatch-detroits.csv"
_PW: dict | None = None


def portwatch(cca2: str | None, d0: date, delai: int = 7) -> dict:
    """0.10.176 : passages de navires (IMF PortWatch) dans les détroits liés au pays (table fixe de
    collecte_portwatch.DETROITS). PortWatch publie avec retard : on n'utilise que les jours antérieurs d'au moins
    `delai` jours à la date ; log((14 jours [d0−21, d0−8] + 1) / (14 jours [d0−35, d0−22] + 1)), tous les jours
    présents exigés."""
    global _PW
    import collecte_portwatch as cp
    detroits = [k for k, (_, pays) in cp.DETROITS.items() if cca2 in pays] if cca2 else []
    if not detroits or not PORTWATCH.exists():
        return {"present": False, "raison": "aucun détroit lié au pays, ou comptes absents"}
    if _PW is None:
        _PW = {(x["detroit"], x["jour"]): (int(x["navires"]), int(x["petroliers"]))
               for x in csv.DictReader(PORTWATCH.open(encoding="utf-8"))}
    rec = [(d0 - timedelta(days=k)).isoformat() for k in range(delai + 1, delai + 15)]
    av = [(d0 - timedelta(days=k)).isoformat() for k in range(delai + 15, delai + 29)]
    if any((d, j) not in _PW for d in detroits for j in rec + av):
        return {"present": False, "raison": "jours PortWatch manquants"}
    s = lambda js, i: sum(_PW[(d, j)][i] for d in detroits for j in js)
    return {"present": True, "valeur": round(math.log((s(rec, 0) + 1) / (s(av, 0) + 1)), 4),
            "valeur_petroliers": round(math.log((s(rec, 1) + 1) / (s(av, 1) + 1)), 4),
            "detroits": detroits, "navires_14j": s(rec, 0), "navires_14j_avant": s(av, 0)}


RADAR = Path("registre") / "radar-coupures.csv"
RADAR_COUVERTURE = Path("registre") / "radar-couverture.txt"
CAUSES_ETAT = {"GOVERNMENT_DIRECTED", "MILITARY_ACTION"}


def radar(cca2: str | None, d0: date) -> dict:
    """0.10.177 : coupures d'internet signalées par Cloudflare Radar dans le pays, commencées dans les 14 jours avant la
    date ; total, coupures décidées par l'État ou dues à une action militaire, pannes électriques."""
    if not cca2 or not RADAR.exists() or not RADAR_COUVERTURE.exists():
        return {"present": False, "raison": "pays inconnu ou coupures Radar absentes"}
    if date.fromisoformat(RADAR_COUVERTURE.read_text(encoding="utf-8").strip()) > d0 - timedelta(days=14):
        return {"present": False, "raison": "période non couverte"}
    a, b = (d0 - timedelta(days=14)).isoformat(), d0.isoformat()
    vues = [x for x in csv.DictReader(RADAR.open(encoding="utf-8")) if x["pays"] == cca2 and a <= x["debut"] < b]
    return {"present": True, "valeur": len(vues),
            "etat_14j": sum(1 for x in vues if x["cause"] in CAUSES_ETAT and x.get("motif") != "examens"),
            "examens_14j": sum(1 for x in vues if x.get("motif") == "examens"),
            "electricite_14j": sum(1 for x in vues if x["cause"] == "POWER_OUTAGE")}


SANCTIONS = Path("registre") / "sanctions.csv"
SANCTIONS_COUVERTURE = Path("registre") / "sanctions-couverture.txt"


def sanctions(cca2: str | None, d0: date) -> dict:
    """0.10.178 : désignations de sanctions visant le pays (OFAC, Royaume-Uni ; UE depuis 0.10.207) dans les 14 jours
    avant la date."""
    if not cca2 or not SANCTIONS.exists() or not SANCTIONS_COUVERTURE.exists():
        return {"present": False, "raison": "pays inconnu ou sanctions absentes"}
    if date.fromisoformat(SANCTIONS_COUVERTURE.read_text(encoding="utf-8").strip()) > d0 - timedelta(days=14):
        return {"present": False, "raison": "période non couverte"}
    a, b = (d0 - timedelta(days=14)).isoformat(), d0.isoformat()
    vues = [x for x in csv.DictReader(SANCTIONS.open(encoding="utf-8")) if x["pays"] == cca2 and a <= x["jour"] < b]
    return {"present": True, "valeur": sum(int(x["designations"]) for x in vues),
            "ofac_14j": sum(int(x["designations"]) for x in vues if x["source"] == "ofac"),
            "uk_14j": sum(int(x["designations"]) for x in vues if x["source"] == "uk"),
            "ue_14j": sum(int(x["designations"]) for x in vues if x["source"] == "ue")}


ELECTIONS = Path("registre") / "elections.csv"


def elections(cca2: str | None, d0: date) -> dict:
    """0.10.179 : élections nationales du pays (Wikidata) dans les 30 jours avant la date (sans fuite) et prévues dans
    les 30 jours après (fuite possible pour une élection anticipée annoncée après la date, déclarée)."""
    if not cca2 or not ELECTIONS.exists():
        return {"present": False, "raison": "pays inconnu ou calendrier absent"}
    av_a, av_b = (d0 - timedelta(days=30)).isoformat(), d0.isoformat()
    ap_b = (d0 + timedelta(days=30)).isoformat()
    xs = [x for x in csv.DictReader(ELECTIONS.open(encoding="utf-8")) if x["pays"] == cca2]
    avant = [x for x in xs if av_a <= x["date"] < av_b]
    apres = [x for x in xs if av_b <= x["date"] < ap_b]
    return {"present": True, "valeur": len(avant), "apres_30j": len(apres),
            "noms": [x["nom"] for x in avant + apres][:4]}


AVIONS_ETAT = Path("registre") / "avions-etat.csv"
AVIONS_ETAT_JOURS = Path("registre") / "avions-etat-jours.txt"


def avions_etat(cca2: str | None, d0: date, manque_max: int = 2) -> dict:
    """0.10.180 : vols d'avions d'État de régimes autoritaires (liste « Dictator Alert ») arrivés dans le pays depuis
    l'étranger, et partis du pays vers l'étranger, dans les 14 jours avant la date (collecte_avions_etat.py)."""
    if not cca2 or not AVIONS_ETAT.exists() or not AVIONS_ETAT_JOURS.exists():
        return {"present": False, "raison": "pays inconnu ou comptes absents"}
    lus = set(AVIONS_ETAT_JOURS.read_text(encoding="utf-8").split())
    js = [(d0 - timedelta(days=k)).isoformat() for k in range(1, 15)]
    if sum(1 for j in js if j not in lus) > manque_max:
        return {"present": False, "raison": "période non couverte"}
    xs = [x for x in csv.DictReader(AVIONS_ETAT.open(encoding="utf-8")) if x["pays"] == cca2 and x["jour"] in js]
    return {"present": True, "valeur": sum(int(x["arrivees_etrangeres"]) for x in xs),
            "departs_14j": sum(int(x["departs_vers_etranger"]) for x in xs)}


ACAPS_RISQUES = Path("registre") / "acaps-risques.csv"


def acaps(cca2: str | None, d0: date, fenetre: int = 180) -> dict:
    """0.10.196 : risques nouveaux émis par ACAPS pour le pays (date d'entrée dans les `fenetre` jours avant la date).
    Seuls la date d'entrée et le pays sont utilisés : probabilité, niveau et statut peuvent avoir été révisés après."""
    if not cca2 or not ACAPS_RISQUES.exists():
        return {"present": False, "raison": "pays inconnu ou risques ACAPS absents"}
    a, b = (d0 - timedelta(days=fenetre)).isoformat(), d0.isoformat()
    xs = {x["risk_id"] for x in csv.DictReader(ACAPS_RISQUES.open(encoding="utf-8"))
          if x["pays"] == cca2 and a <= x["date_entered"] < b}
    return {"present": True, "valeur": len(xs), "fenetre_jours": fenetre}


RECIT_RUSSE = Path("registre") / "recit-russe.csv"
DATES_MEMOIRE = Path("registre") / "dates-memoire.csv"


def recit_russe(cca2: str | None, d0: date, couverture_min: int = 24) -> dict:
    """0.10.202 (M12, en ombre) : articles de sources russes qui nomment le pays (GDELT DOC), log(14 jours / 14 jours
    précédents) ; part « alibi » (provocation, mise en scène, faux drapeau) sur les 14 derniers jours quand elle est lue."""
    if not cca2 or not RECIT_RUSSE.exists():
        return {"present": False, "raison": "pays inconnu ou registre absent"}
    a, m = (d0 - timedelta(days=28)).isoformat(), (d0 - timedelta(days=14)).isoformat()
    xs = [x for x in csv.DictReader(RECIT_RUSSE.open(encoding="utf-8"))
          if x["pays"] == cca2 and a <= x["jour"] < d0.isoformat()]
    if len({x["jour"] for x in xs}) < couverture_min:
        return {"present": False, "raison": "période non couverte"}
    rec = [x for x in xs if x["jour"] >= m]
    n_rec, n_av = sum(int(x["articles"] or 0) for x in rec), sum(int(x["articles"] or 0) for x in xs if x["jour"] < m)
    out = {"present": True, "valeur": round(math.log((n_rec + 1) / (n_av + 1)), 4), "articles_14j": n_rec,
           "articles_14j_avant": n_av}
    if rec and all((x.get("alibi") or "") != "" for x in rec) and n_rec:
        out["part_alibi_14j"] = round(sum(int(x["alibi"]) for x in rec) / n_rec, 4)
    return out


def dates_memoire(cca2: str | None, d0: date, fenetre: int = 14) -> dict:
    """0.10.202 (M14, en ombre) : dates de mémoire du calendrier fixe (registre/dates-memoire.csv) qui tombent dans
    les `fenetre` jours à partir de la date. Calendrier connu d'avance : aucune fuite. Absent pour un pays sans date."""
    if not cca2 or not DATES_MEMOIRE.exists():
        return {"present": False, "raison": "pays inconnu ou calendrier absent"}
    md = [x["mois_jour"] for x in csv.DictReader(DATES_MEMOIRE.open(encoding="utf-8")) if x["pays"] == cca2]
    if not md:
        return {"present": False, "raison": "aucune date de mémoire pour ce pays"}
    jours = {(d0 + timedelta(days=k)).strftime("%m-%d") for k in range(fenetre)}
    return {"present": True, "valeur": sum(m in jours for m in md), "fenetre_jours": fenetre}


CHINE_SANCTIONS = Path("registre") / "gdelt-chine-sanctions.csv"
CHINE_JOURS = Path("registre") / "gdelt-chine-jours.txt"


def contremesures_chine(cca2: str | None, d0: date, fenetre: int = 90, couverture_min: float = 0.9) -> dict:
    """0.10.205 (module Chine, couche 2, en ombre) : sanctions, embargos et boycotts imposés par un acteur chinois au
    pays (GDELT, code CAMEO 163, pays visé), dans les `fenetre` jours avant la date. Collecte automatique : le site du
    ministère du Commerce interdit les robots, l'API de Global Trade Alert est payante, et l'auteur ne veut pas de
    saisie à la main (2026-11-16, 21 h 45)."""
    if not cca2 or not CHINE_SANCTIONS.exists() or not CHINE_JOURS.exists():
        return {"present": False, "raison": "pays inconnu ou registre absent"}
    a = (d0 - timedelta(days=fenetre)).isoformat()
    lus = {j for j in CHINE_JOURS.read_text(encoding="utf-8").split() if a <= j < d0.isoformat()}
    if len(lus) < couverture_min * fenetre:
        return {"present": False, "raison": "période non couverte"}
    n = sum(int(x["evenements"]) for x in csv.DictReader(CHINE_SANCTIONS.open(encoding="utf-8"))
            if x["pays"] == cca2 and a <= x["jour"] < d0.isoformat())
    return {"present": True, "valeur": n, "fenetre_jours": fenetre}


PAIRES_JOUR = Path("registre") / "gdelt-paires-jour.csv"
PAIRES_MOIS = Path("registre") / "gdelt-paires-mois.csv"
PAIRES_JOURS = Path("registre") / "gdelt-paires-jours.txt"
RIVALITE_MIN_CONFLITS = 200      # 0.10.222, fixés avant toute mesure : au moins 200 événements conflictuels en 12 mois
RIVALITE_MIN_PART = 0.35         # et au moins 35 % des événements de la paire
# 0.10.223 (décision d'auteur du 2026-11-17, 10 h 21) : rivalités stratégiques de Thompson et Dreyer (Handbook of
# International Rivalries, 1494-2010, CQ Press 2011), celles encore actives en 2010, ajoutées aux rivalités calculées.
RIVALITES_FIXES = Path("registre") / "rivalites-strategiques.csv"


def rivalites(d0: date) -> set[tuple[str, str]]:
    """0.10.222 (M17) : paires de pays rivales à la date d0, calculées sur les 12 mois COMPLETS avant le mois de d0
    (GDELT, QuadClass 3 et 4 : conflit verbal et matériel). Ensemble vide si moins de 11 de ces mois sont couverts."""
    if not PAIRES_MOIS.exists() or not PAIRES_JOURS.exists():
        return set()
    m0 = date(d0.year, d0.month, 1)
    mois = []
    for k in range(1, 13):
        a, mm = m0.year, m0.month - k
        while mm <= 0:
            a, mm = a - 1, mm + 12
        mois.append(f"{a}-{mm:02d}")
    couverts = {j[:7] for j in PAIRES_JOURS.read_text(encoding="utf-8").split()}
    if sum(m in couverts for m in mois) < 11:
        return set()
    tot: dict[tuple, list[int]] = {}
    for x in csv.DictReader(PAIRES_MOIS.open(encoding="utf-8")):
        if x["mois"] in mois:
            v = tot.setdefault((x["a"], x["b"]), [0, 0])
            v[0] += int(x["evenements"])
            v[1] += int(x["conflit"])
    calculees = {k for k, (n, c) in tot.items() if c >= RIVALITE_MIN_CONFLITS and c >= RIVALITE_MIN_PART * n}
    return calculees | rivalites_fixes()


def rivalites_fixes() -> set[tuple[str, str]]:
    """0.10.223 : liste fixe de Thompson et Dreyer (rivalités stratégiques actives en 2010), paires triées. Elle répare
    un défaut constaté à la relecture de la liste calculée : un grand volume d'échanges ordinaires dilue la part de
    conflit des vrais rivaux (Chine-Japon 30 %, Chine-États-Unis 23 %) au niveau d'alliés en dispute (Canada-États-Unis
    22 %), si bien qu'aucun seuil sur cette part ne les sépare. Liste antérieure à toute issue : pas de fuite."""
    if not RIVALITES_FIXES.exists():
        return set()
    return {tuple(sorted((x["a"], x["b"]))) for x in csv.DictReader(RIVALITES_FIXES.open(encoding="utf-8"))}


def alignement_rival(cca2: str | None, d0: date, fenetre: int = 14, couverture_min: float = 0.85) -> dict:
    """0.10.222 (M17, en ombre) : « le resserrement militaire d'un pays avec le rival d'une puissance appelle une
    démonstration de force de cette puissance ». Valeur : nombre d'événements de coopération militaire (CAMEO 062,
    0312, dans les deux sens) entre le pays X et un partenaire R, dans les `fenetre` jours avant d0, tels qu'il existe
    une puissance P ≠ X rivale de R ET rivale ou voisine terrestre de X. Rivalités calculées par `rivalites(d0)`."""
    if not cca2 or not PAIRES_JOUR.exists() or not PAIRES_JOURS.exists():
        return {"present": False, "raison": "pays inconnu ou registre absent"}
    a = (d0 - timedelta(days=fenetre)).isoformat()
    lus = {j for j in PAIRES_JOURS.read_text(encoding="utf-8").split() if a <= j < d0.isoformat()}
    if len(lus) < couverture_min * fenetre:
        return {"present": False, "raison": "période non couverte"}
    riv = rivalites(d0)
    if not riv:
        return {"present": False, "raison": "rivalités incalculables (moins de 11 mois couverts)"}
    rivaux: dict[str, set[str]] = {}
    for u, v in riv:
        rivaux.setdefault(u, set()).add(v)
        rivaux.setdefault(v, set()).add(u)
    proches_x = rivaux.get(cca2, set()) | set(voisins(cca2))
    n, puissances = 0, set()
    for x in csv.DictReader(PAIRES_JOUR.open(encoding="utf-8")):
        if not (a <= x["jour"] < d0.isoformat()) or int(x["coop_mil"]) == 0 or cca2 not in (x["a"], x["b"]):
            continue
        r = x["b"] if x["a"] == cca2 else x["a"]
        p = (rivaux.get(r, set()) & proches_x) - {cca2}
        if p:
            n += int(x["coop_mil"])
            puissances |= p
    return {"present": True, "valeur": n, "puissances": sorted(puissances), "fenetre_jours": fenetre,
            "rivalites": len(riv)}


AVIS_NAVIGATION = Path("registre") / "avis-navigation-chine.csv"
AVIS_JOURS = Path("registre") / "avis-navigation-jours.txt"


def avis_navigation(cca2: str | None, d0: date, fenetre: int = 14) -> dict:
    """0.10.206 (module Chine, couche 3, en ombre) : avertissements de navigation militaires en zone chinoise
    concernant le pays (NGA, HYDROPAC), émis dans les `fenetre` jours avant la date. Présent seulement quand la
    collecte couvrait déjà toute la fenêtre (l'API ne rend que les avertissements en cours)."""
    if not cca2 or not AVIS_NAVIGATION.exists() or not AVIS_JOURS.exists():
        return {"present": False, "raison": "pays inconnu ou registre absent"}
    jours = sorted(AVIS_JOURS.read_text(encoding="utf-8").split())
    a = (d0 - timedelta(days=fenetre)).isoformat()
    if not jours or jours[0] > a:
        return {"present": False, "raison": "période non couverte"}
    n = sum(1 for x in csv.DictReader(AVIS_NAVIGATION.open(encoding="utf-8"))
            if x["militaire"] == "1" and cca2 in x["pays"].split(";") and a <= (x["emission"] or x["premier_vu"]) < d0.isoformat())
    return {"present": True, "valeur": n, "fenetre_jours": fenetre}


def force_chinoise(cca2: str | None, d0: date, fenetre: int = 14, couverture_min: float = 0.85) -> dict:
    """0.10.224 (module Chine, couche 3, en ombre ; décision d'auteur du 2026-11-17, 10 h 41) : relais de
    `avis_navigation`, dont la source (NGA) est en maintenance et n'a jamais livré. Valeur : démonstrations de force
    (racine CAMEO 15 : mises en alerte, mobilisations, manœuvres) d'un acteur chinois visant le pays, dans les
    `fenetre` jours avant la date, d'après `registre/gdelt-paires-jour.csv` (déjà collecté depuis juillet 2024).
    Différence avec la source NGA : un avertissement de navigation ANNONCE l'exercice ; GDELT relève la démonstration
    une fois rapportée par la presse. Signal plus tardif et plus bruité, mais disponible et avec un historique.
    Calculé à côté de `avis_navigation`, pas à sa place : les deux restent comparables si la NGA revient."""
    if not cca2 or cca2 == "CN" or not PAIRES_JOUR.exists() or not PAIRES_JOURS.exists():
        return {"present": False, "raison": "pays inconnu, Chine elle-même ou registre absent"}
    a, b = (d0 - timedelta(days=fenetre)).isoformat(), d0.isoformat()
    if sum(1 for j in PAIRES_JOURS.read_text(encoding="utf-8").split() if a <= j < b) < couverture_min * fenetre:
        return {"present": False, "raison": "période non couverte"}
    n = sum(int(x["force"]) for x in csv.DictReader(PAIRES_JOUR.open(encoding="utf-8"))
            if x["a"] == "CN" and x["b"] == cca2 and a <= x["jour"] < b)
    return {"present": True, "valeur": n, "fenetre_jours": fenetre}


FEUX = Path("registre") / "feux.csv"
FEUX_JOURS = Path("registre") / "feux-jours.txt"


def feux(cca2: str | None, d0: date, couverture_min: int = 26) -> dict:
    """0.10.208 (en ombre) : points chauds détectés par satellite dans le pays (NASA FIRMS, VIIRS), log(14 jours /
    14 jours précédents) ; part de confiance forte sur 14 jours."""
    if not cca2 or not FEUX.exists() or not FEUX_JOURS.exists():
        return {"present": False, "raison": "pays inconnu ou registre absent"}
    a, m, b = (d0 - timedelta(days=28)).isoformat(), (d0 - timedelta(days=14)).isoformat(), d0.isoformat()
    if sum(1 for j in FEUX_JOURS.read_text(encoding="utf-8").split() if a <= j < b) < couverture_min:
        return {"present": False, "raison": "période non couverte"}
    xs = [x for x in csv.DictReader(FEUX.open(encoding="utf-8")) if x["pays"] == cca2 and a <= x["jour"] < b]
    rec = sum(int(x["detections"]) for x in xs if x["jour"] >= m)
    av = sum(int(x["detections"]) for x in xs if x["jour"] < m)
    fort = sum(int(x["forte_confiance"]) for x in xs if x["jour"] >= m)
    return {"present": True, "valeur": round(math.log((rec + 1) / (av + 1)), 4), "detections_14j": rec,
            "detections_14j_avant": av, "part_forte_confiance": round(fort / rec, 3) if rec else None}


CALENDRIER_NBS = Path("registre") / "calendrier-nbs.csv"
PUBLICATIONS_NBS = Path("registre") / "publications-nbs.csv"
FERIES_CHINE = Path("registre") / "jours-feries-chine.csv"   # 0.10.216 : congés officiels (Conseil d'État), à renouveler


def _feries_chine() -> set[date]:
    out: set[date] = set()
    if FERIES_CHINE.exists():
        for x in csv.DictReader(FERIES_CHINE.open(encoding="utf-8")):
            d, f = date.fromisoformat(x["debut"]), date.fromisoformat(x["fin"])
            while d <= f:
                out.add(d)
                d += timedelta(days=1)
    return out


def echeance_nbs(prevue: date, tolerance: int, feries: set[date]) -> date:
    """0.10.216 : date limite d'une publication = date prévue + tolérance, prolongée d'un jour par jour férié chinois
    compris dans l'intervalle (le site anglais ne publie pas pendant les « semaines d'or » : PMI du 30 avril paru le
    6 mai, PMI du 30 septembre paru le 8 octobre 2026)."""
    limite = prevue + timedelta(days=tolerance)
    while True:
        n = sum(1 for k in range((limite - prevue).days + 1) if prevue + timedelta(days=k) in feries)
        nouvelle = prevue + timedelta(days=tolerance + n)
        if nouvelle == limite:
            return limite
        limite = nouvelle


def silence_statistique(cca2: str | None, d0: date, fenetre: int = 30, tolerance: int = 3) -> dict:
    """0.10.209 (M15, en ombre) : publications du Bureau national des statistiques chinois PRÉVUES par le calendrier
    officiel dans les `fenetre` jours avant la date, et jugeables (date prévue + tolérance < date), qui ont paru en
    retard ou pas du tout. Chine seulement. Seules les publications observées avant la date comptent (pas de fuite)."""
    if cca2 != "CN":
        return {"present": False, "raison": "Chine seulement"}
    if not CALENDRIER_NBS.exists() or not PUBLICATIONS_NBS.exists():
        return {"present": False, "raison": "registre absent"}
    obs = [x for x in csv.DictReader(PUBLICATIONS_NBS.open(encoding="utf-8")) if x["jour"] < d0.isoformat()]
    if not obs:
        return {"present": False, "raison": "aucune publication observée avant la date"}
    debut = max(min(x["jour"] for x in obs), (d0 - timedelta(days=fenetre)).isoformat())
    a_temps = retard = absente = 0
    manquantes = []
    feries = _feries_chine()
    for x in csv.DictReader(CALENDRIER_NBS.open(encoding="utf-8")):
        e = date.fromisoformat(x["date_prevue"])
        limite = echeance_nbs(e, tolerance, feries)
        if not (debut <= (e - timedelta(days=1)).isoformat() and limite < d0):
            continue
        vues = [date.fromisoformat(o["jour"]) for o in obs if o["publication"] == x["publication"]]
        if any(e - timedelta(days=1) <= v <= limite for v in vues):
            a_temps += 1
        elif any(limite < v for v in vues):
            retard += 1
            manquantes.append(f"{x['publication']} {x['date_prevue']} (retard)")
        else:
            absente += 1
            manquantes.append(f"{x['publication']} {x['date_prevue']} (absente)")
    if not (a_temps + retard + absente):
        return {"present": False, "raison": "aucune publication prévue jugeable dans la fenêtre"}
    return {"present": True, "valeur": retard + absente, "a_temps": a_temps, "retard": retard, "absente": absente,
            "manquantes": manquantes[:6]}


PRIX_ALIMENTAIRES = Path("registre") / "prix-alimentaires.csv"


def prix_alimentaires(cca2: str | None, d0: date) -> dict:
    """0.10.214 (en ombre) : inflation alimentaire sur un an (Banque mondiale, RTFP), calculée sur l'indice « Close »
    (Close du dernier mois / Close douze mois plus tôt − 1, en %), dans la DERNIÈRE VERSION publiée avant la date
    (millésime : les estimations sont recalculées à chaque version) ; et son accélération sur trois mois."""
    if not cca2 or not PRIX_ALIMENTAIRES.exists():
        return {"present": False, "raison": "pays inconnu ou registre absent"}
    xs = [x for x in csv.DictReader(PRIX_ALIMENTAIRES.open(encoding="utf-8")) if x["version"] < d0.isoformat()]
    if not xs:
        return {"present": False, "raison": "aucune version publiée avant la date"}
    v = max(x["version"] for x in xs)
    serie = {x["mois"]: float(x["close"]) for x in xs if x["version"] == v and x["pays"] == cca2 and x["close"] not in ("", "NA")}
    if not serie:
        return {"present": False, "raison": "pays absent de la base (37 pays)"}

    def recul(mois: str, n: int) -> str:
        a, m = int(mois[:4]), int(mois[5:7]) - n
        while m <= 0:
            a, m = a - 1, m + 12
        return f"{a:04d}-{m:02d}"

    dernier = max(serie)

    def glissement(m: str) -> float | None:
        b = serie.get(recul(m, 12))
        return round(100 * (serie[m] / b - 1), 2) if m in serie and b else None
    g = glissement(dernier)
    if g is None:
        return {"present": False, "raison": "série trop courte"}
    g3 = glissement(recul(dernier, 3))
    return {"present": True, "valeur": g, "acceleration_3m": round(g - g3, 2) if g3 is not None else None,
            "mois": dernier, "version": v}


RSS_COMPTES = Path("registre") / "rss-comptes.csv"
RSS_DEBUT = date(2026, 11, 16)
RSS_LARGE_DEBUT = date(2026, 11, 17)  # 0.10.199 : premier jour complet des comptes « _large » (adjectifs) et cyber


def rss(cca2: str | None, d0: date) -> tuple[dict, dict]:
    absent = {"present": False, "raison": "période non couverte ou pays inconnu"}
    if not cca2 or not RSS_COMPTES.exists() or d0 - timedelta(days=14) < RSS_DEBUT:
        return absent, absent
    rec = av = off = pe = ren = san = vc = tt = eco = nota = cyb = rec_l = av_l = verif = enq = 0
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
        if x["famille"] == "cyber" and d0 - timedelta(days=14) <= j < d0:      # 0.10.199, en ombre
            cyb += n
        if x["famille"] == "verification" and d0 - timedelta(days=14) <= j < d0:   # 0.10.200, en ombre (Correctiv)
            verif += n
        if x["famille"] == "enquete" and d0 - timedelta(days=14) <= j < d0:
            enq += n
        if x["famille"] == "presse_large":                                    # 0.10.199 : noms ET adjectifs, en ombre
            if d0 - timedelta(days=14) <= j < d0:
                rec_l += n
            elif d0 - timedelta(days=28) <= j < d0 - timedelta(days=14):
                av_l += n
        if x["famille"] == "presse":
            if d0 - timedelta(days=14) <= j < d0:
                rec += n
            elif d0 - timedelta(days=28) <= j < d0 - timedelta(days=14):
                av += n
    presse = ({"present": True, "valeur": round(math.log((rec + 1) / (av + 1)), 4), "articles_14j": rec, "articles_14j_avant": av}
              if d0 - timedelta(days=28) >= RSS_DEBUT else absent)
    if presse.get("present") and d0 - timedelta(days=28) >= RSS_LARGE_DEBUT:
        presse["valeur_large"] = round(math.log((rec_l + 1) / (av_l + 1)), 4)
        presse["articles_14j_large"], presse["articles_14j_avant_large"] = rec_l, av_l
    return presse, {"present": True, "valeur": float(off), "articles_officiels_14j": off, "parlement_ue_14j": pe,
                    "renseignement_14j": ren, "sante_14j": san, "voix_citoyennes_14j": vc,
                    "think_tanks_14j": tt, "economie_14j": eco, "notation_14j": nota,
                    **({"cyber_14j": cyb, "verification_14j": verif, "enquete_14j": enq}
                       if d0 - timedelta(days=14) >= RSS_LARGE_DEBUT else {})}


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
                    k for k in ("wikimodif", "prix_alim", "vols", "telegram", "violationswatch", "rss_presse", "rss_officiel", "brouillage_gps", "gdelt", "ooni", "portwatch", "radar", "sanctions", "elections", "avions_etat", "voisins", "acaps", "recit_russe", "dates_memoire", "contremesures_chine", "avis_navigation", "force_chinoise", "feux", "silence_statistique", "prix_alimentaires", "alignement_rival") if (x.get(k) or {}).get("present")
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
                if "avions_etat" not in fait and AVIONS_ETAT_JOURS.exists():
                    code = await os_.code_pays(pays) or (await __import__("banc_indicateurs").fiche_pays(c, pays, cache_pays)).get("cca2")
                    ligne["avions_etat"] = avions_etat(code, d0)
                if "elections" not in fait and ELECTIONS.exists():
                    code = await os_.code_pays(pays) or (await __import__("banc_indicateurs").fiche_pays(c, pays, cache_pays)).get("cca2")
                    ligne["elections"] = elections(code, d0)
                if "sanctions" not in fait and SANCTIONS.exists():
                    code = await os_.code_pays(pays) or (await __import__("banc_indicateurs").fiche_pays(c, pays, cache_pays)).get("cca2")
                    ligne["sanctions"] = sanctions(code, d0)
                if "radar" not in fait and RADAR.exists():
                    code = await os_.code_pays(pays) or (await __import__("banc_indicateurs").fiche_pays(c, pays, cache_pays)).get("cca2")
                    ligne["radar"] = radar(code, d0)
                if "portwatch" not in fait and PORTWATCH.exists():
                    code = await os_.code_pays(pays) or (await __import__("banc_indicateurs").fiche_pays(c, pays, cache_pays)).get("cca2")
                    ligne["portwatch"] = portwatch(code, d0)
                if "acaps" not in fait and ACAPS_RISQUES.exists():
                    code = await os_.code_pays(pays) or (await __import__("banc_indicateurs").fiche_pays(c, pays, cache_pays)).get("cca2")
                    ligne["acaps"] = acaps(code, d0)
                if "recit_russe" not in fait and RECIT_RUSSE.exists():          # 0.10.202, M12
                    code = await os_.code_pays(pays) or (await __import__("banc_indicateurs").fiche_pays(c, pays, cache_pays)).get("cca2")
                    ligne["recit_russe"] = recit_russe(code, d0)
                if "alignement_rival" not in fait and PAIRES_JOUR.exists():          # 0.10.222, M17
                    ligne["alignement_rival"] = alignement_rival(code, d0)
                if "contremesures_chine" not in fait and CHINE_SANCTIONS.exists():   # 0.10.204, module Chine
                    code = await os_.code_pays(pays) or (await __import__("banc_indicateurs").fiche_pays(c, pays, cache_pays)).get("cca2")
                    ligne["contremesures_chine"] = contremesures_chine(code, d0)
                if "avis_navigation" not in fait and AVIS_NAVIGATION.exists():   # 0.10.206, module Chine
                    code = await os_.code_pays(pays) or (await __import__("banc_indicateurs").fiche_pays(c, pays, cache_pays)).get("cca2")
                    ligne["avis_navigation"] = avis_navigation(code, d0)
                if "force_chinoise" not in fait and PAIRES_JOUR.exists():       # 0.10.224, relais de la NGA
                    code = await os_.code_pays(pays) or (await __import__("banc_indicateurs").fiche_pays(c, pays, cache_pays)).get("cca2")
                    ligne["force_chinoise"] = force_chinoise(code, d0)
                if "feux" not in fait and FEUX.exists():                         # 0.10.208, NASA FIRMS
                    code = await os_.code_pays(pays) or (await __import__("banc_indicateurs").fiche_pays(c, pays, cache_pays)).get("cca2")
                    ligne["feux"] = feux(code, d0)
                if "silence_statistique" not in fait and PUBLICATIONS_NBS.exists():   # 0.10.209, M15
                    code = await os_.code_pays(pays) or (await __import__("banc_indicateurs").fiche_pays(c, pays, cache_pays)).get("cca2")
                    ligne["silence_statistique"] = silence_statistique(code, d0)
                if "prix_alimentaires" not in fait and PRIX_ALIMENTAIRES.exists():   # 0.10.214, RTFP
                    code = await os_.code_pays(pays) or (await __import__("banc_indicateurs").fiche_pays(c, pays, cache_pays)).get("cca2")
                    ligne["prix_alimentaires"] = prix_alimentaires(code, d0)
                if "dates_memoire" not in fait and DATES_MEMOIRE.exists():      # 0.10.202, M14
                    code = await os_.code_pays(pays) or (await __import__("banc_indicateurs").fiche_pays(c, pays, cache_pays)).get("cca2")
                    ligne["dates_memoire"] = dates_memoire(code, d0)
                if "voisins" not in fait and GDELT_JOURS.exists():
                    code = await os_.code_pays(pays) or (await __import__("banc_indicateurs").fiche_pays(c, pays, cache_pays)).get("cca2")
                    ligne["voisins"] = voisins_gdelt(code, d0)
                if "ooni" not in fait and OONI_JOURS.exists():
                    code = await os_.code_pays(pays) or (await __import__("banc_indicateurs").fiche_pays(c, pays, cache_pays)).get("cca2")
                    ligne["ooni"] = ooni(code, d0)
                if ("rss_officiel" not in fait or "rss_presse" not in fait) and d0 - timedelta(days=14) >= RSS_DEBUT:
                    code = await os_.code_pays(pays) or (await __import__("banc_indicateurs").fiche_pays(c, pays, cache_pays)).get("cca2")
                    ligne["rss_presse"], ligne["rss_officiel"] = rss(code, d0)
                if len(ligne) == 2:
                    continue
                f.write(json.dumps(ligne, ensure_ascii=False) + "\n")
                f.flush()
                print(f"{pays[:22]:22s} {jeu} : " + " · ".join(f"{k} {(ligne[k] or {}).get('valeur')}"
                                                            for k in ("wikimodif", "prix_alim", "vols", "telegram", "violationswatch", "rss_presse", "rss_officiel", "brouillage_gps", "gdelt", "ooni", "portwatch", "radar", "sanctions", "elections", "avions_etat", "voisins", "acaps", "recit_russe", "dates_memoire", "contremesures_chine", "avis_navigation", "force_chinoise", "feux", "silence_statistique", "prix_alimentaires", "alignement_rival") if k in ligne))
        await tg.fermer()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(principal()))
