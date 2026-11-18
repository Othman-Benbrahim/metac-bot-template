"""Chaîne de recherche (0.6.3) : Exa, puis la seconde clé Exa, puis Tavily, puis TinyFish, puis GDELT.

Chaque requête essaie les moteurs dans l'ordre et s'arrête au premier qui rend un résultat. Un moteur sans clé est
sauté. Quand la première clé Exa échoue (quota épuisé, erreur), le bot passe à la seconde pour le reste du passage.
Chaque résultat commence par « [moteur : …] » : le registre sait quel moteur a servi chaque requête.

Ordre modifiable par la variable ALPHABET_RECHERCHE_ORDRE (par défaut « exa,tavily,tinyfish,gdelt »).
Secrets : EXA_API_KEY, EXA_API_KEY_2, TAVILY_API_KEY, TINYFISH_API_KEY ; GDELT n'a pas de clé. (Brave Search, qui exige une carte
bancaire même en offre gratuite, a été retiré en 0.6.2.)
"""
from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from typing import Awaitable, Callable

import httpx

ORDRE_DEFAUT = "exa,tavily,tinyfish,gdelt"
DELAI = 40

# 0.10.260 (trace du 2026-11-18, run 44291087818) : la recherche ramenait des pages de marchés de prédiction
# (Polymarket, Manifold) ; la règle « jamais de cote ni de prévision de foule en entrée » n'était tenue que par la
# consigne. Elle l'est désormais par le code, pour tous les moteurs. Wikipédia est une page vivante : en recherche
# RÉTROSPECTIVE (date d'information fixée), sa date affichée ne garantit pas son contenu ; elle est écartée là.
PREVISION_FOULE = ("polymarket.com", "manifold.markets", "kalshi.com", "predictit.org", "metaculus.com",
                   "gjopen.com", "goodjudgment.com", "infer-pub.com", "randforecastinginitiative.org",
                   "insightprediction.com", "smarkets.com", "betfair.com", "oddschecker.com", "futuur.com",
                   "predyx.com", "limitless.exchange", "myriad.markets", "hedgehog.markets")
PAGES_VIVANTES = ("wikipedia.org", "wikiwand.com", "wikidata.org", "ballotpedia.org")
_URL_BLOC = re.compile(r"^\[[^\]]*\] .*? — (\S+)\s*$", re.M)


def domaine_exclu(url: str, retro: bool) -> bool:
    from urllib.parse import urlparse
    d = urlparse(url or "").netloc.lower()
    interdits = PREVISION_FOULE + (PAGES_VIVANTES if retro else ())
    return any(d == x or d.endswith("." + x) for x in interdits)


_FOULE = re.compile(
    r"polymarket|kalshi|manifold\.markets|manifold markets|\bon manifold\b|predictit|metaculus|good judgment|gjopen|"
    r"smarkets|betfair|oddschecker|prediction[- ]markets?|betting (?:markets?|odds|exchanges?)|bookmakers?|"
    r"sportsbooks?|community (?:prediction|forecast)|crowd(?:sourced)? forecasts?|superforecasters?|"
    r"implied probability|traders? (?:are )?pric(?:e|ing)|march[ée]s? de pr[ée]diction|cotes? des? (?:paris|bookmakers?)",
    re.I)
_PHRASE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9«\"(\[])")


def sans_foule(texte: str) -> tuple[str, int]:
    """0.10.261 : retire d'un texte rédigé (synthèse d'un chercheur) toute phrase qui cite une cote, un marché de
    prédiction ou une prévision de foule, et toute adresse de ces sites. Ligne par ligne, puis phrase par phrase dans
    une ligne. Rend (texte nettoyé, nombre de phrases retirées). Règle tenue par le code, pas par la consigne."""
    retirees, lignes = 0, []
    for ligne in (texte or "").split("\n"):
        if not _FOULE.search(ligne) and not any(x in ligne.lower() for x in PREVISION_FOULE):
            lignes.append(ligne)
            continue
        garde = []
        for ph in _PHRASE.split(ligne):
            if _FOULE.search(ph) or any(x in ph.lower() for x in PREVISION_FOULE):
                retirees += 1
            else:
                garde.append(ph)
        if garde:
            lignes.append(" ".join(garde))
    return "\n".join(lignes), retirees


def filtrer(texte: str, retro: bool) -> str:
    """Retire les blocs « [date] titre — adresse » dont l'adresse est exclue ; garde l'en-tête du moteur."""
    blocs, garde = (texte or "").split("\n\n"), []
    for b in blocs:
        m = _URL_BLOC.search(b)
        if m and domaine_exclu(m.group(1), retro):
            continue
        garde.append(b)
    return "\n\n".join(garde)


def _ligne(date, titre, url, extrait) -> str:
    return f"[{date or 's.d.'}] {titre or ''} — {url or ''}\n{(extrait or '').strip()}"


async def tavily(requete: str, avant: datetime | None = None) -> str:
    cle = os.environ.get("TAVILY_API_KEY")
    corps = {"api_key": cle, "query": requete, "max_results": 8, "search_depth": "basic", "include_answer": False}
    if avant is not None:
        corps["end_date"] = avant.date().isoformat()
    async with httpx.AsyncClient(timeout=DELAI) as c:
        r = await c.post("https://api.tavily.com/search", json=corps, headers={"Authorization": f"Bearer {cle}"})
        r.raise_for_status()
        res = r.json().get("results") or []
    return "\n\n".join(_ligne(x.get("published_date"), x.get("title"), x.get("url"), x.get("content")) for x in res)


def _premiere(x: dict, *cles):
    for k in cles:
        v = x.get(k)
        if v:
            return v
    return None


def _date_iso(v) -> datetime | None:
    try:
        d = datetime.fromisoformat(str(v).replace("Z", "+00:00"))
    except ValueError:
        return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


async def tinyfish(requete: str, avant: datetime | None = None) -> str:
    """TinyFish Search (0.6.3) : gratuit, sans carte, clé X-API-Key. La doc publique ne fixe pas le nom des champs
    de la réponse : on lit les noms courants. TinyFish ne sait pas borner par date ; quand une date limite est
    donnée, seuls les résultats DATÉS et antérieurs sont gardés (sinon rien, et la chaîne passe au moteur suivant)."""
    cle = os.environ.get("TINYFISH_API_KEY")
    params = {"query": requete}
    async with httpx.AsyncClient(timeout=DELAI) as c:
        r = await c.get("https://api.search.tinyfish.ai", params=params, headers={"X-API-Key": cle})
        r.raise_for_status()
        corps = r.json()
    res = corps if isinstance(corps, list) else (
        _premiere(corps, "results", "organic", "data", "items", "web") or [])
    if isinstance(res, dict):
        res = _premiere(res, "results", "items") or []
    lignes = []
    for x in res:
        if not isinstance(x, dict):
            continue
        date = _premiere(x, "published_date", "publishedDate", "date", "published_at", "age")
        if avant is not None:
            d = _date_iso(date) if date else None
            if d is None or d > avant:
                continue
        lignes.append(_ligne(date, _premiere(x, "title", "name"), _premiere(x, "url", "link"),
                             _premiere(x, "snippet", "description", "content", "text")))
    return "\n\n".join(lignes)


_GDELT_VERROU = None
_GDELT_DERNIER = 0.0
GDELT_ECART = 5.5            # 0.10.264 : GDELT demande une requête toutes les 5 secondes au plus
GDELT_ESSAIS, GDELT_PAUSE_429 = 4, 8.0   # 0.10.266 : 429 → attendre 8, 16, 32 s (ou Retry-After) et réessayer
GDELT_REFUS_MAX = 3          # 0.10.271 : après 3 questions refusées de suite (429 persistant), GDELT est coupé
_GDELT_REFUS = 0             # pour le reste du processus : une panne durable ne doit pas ralentir chaque question


async def _gdelt_attendre() -> None:
    """Une seule requête GDELT à la fois, espacées d'au moins GDELT_ECART secondes (tout le processus)."""
    import asyncio
    import time
    global _GDELT_VERROU, _GDELT_DERNIER
    boucle = asyncio.get_running_loop()
    if _GDELT_VERROU is None or _GDELT_VERROU[0] is not boucle:     # un verrou par boucle d'événements
        _GDELT_VERROU = (boucle, asyncio.Lock())
    async with _GDELT_VERROU[1]:
        attente = GDELT_ECART - (time.monotonic() - _GDELT_DERNIER)
        if attente > 0:
            await asyncio.sleep(attente)
        _GDELT_DERNIER = time.monotonic()


_MOTS_VIDES: set[str] | None = None
GDELT_MOTS = 4


def _mots_vides() -> set[str]:
    global _MOTS_VIDES
    if _MOTS_VIDES is None:
        from pathlib import Path
        f = Path(__file__).parent / "registre" / "mots-vides-anglais.txt"
        _MOTS_VIDES = {l.strip().lower() for l in f.read_text(encoding="utf-8").splitlines() if l.strip()} if f.exists() else set()
        _MOTS_VIDES |= {"will", "would", "before", "after", "least", "more", "than", "according"}
    return _MOTS_VIDES


def gdelt_mots(requete: str) -> str:
    """0.10.264-0.10.266 (sonde GDELT du 2026-11-18, run 44303267909) : GDELT exige TOUS les mots de la requête ;
    les mots vides (« Will », « the »…) la rendent trop étroite. Il refuse les mots de moins de 3 lettres et tout
    tiret hors guillemets (« S-1 », « mail-in » : « illegal character ») : un mot à tiret est mis entre guillemets."""
    # 0.10.275 (sonde du 2026-11-18 par le pont : 7 réponses vides sur 20, requêtes de 6 à 8 mots) : GDELT exige
    # TOUS les mots ; on garde au plus 4 mots, les noms propres d'abord (majuscule hors début de phrase), puis les
    # autres dans l'ordre, sans doublon.
    # Une suite de noms propres (« Luiz Inacio Lula ») ne garde que son premier et son dernier mot.
    vides = _mots_vides()
    propres, autres, vus, suite = [], [], set(), []

    def fermer():
        propres.extend(suite if len(suite) <= 2 else [suite[0], suite[-1]])
        suite.clear()
    for i, w in enumerate(re.sub(r"[^\w\s-]", " ", requete).split()):
        w = w.strip("-")
        if len(w) <= 2 or w.isdigit() or w.lower() in vides or w.lower() in vus:
            fermer()
            continue
        vus.add(w.lower())
        mot = f'"{w}"' if "-" in w else w
        if w[0].isupper() and i > 0:
            suite.append(mot)
        else:
            fermer()
            autres.append(mot)
    fermer()
    return " ".join((propres + autres)[:GDELT_MOTS])


async def gdelt(requete: str, avant: datetime | None = None) -> str:
    """GDELT DOC 2.0 : articles de presse mondiaux, sans clé. Renvoie titres, liens et dates (pas le texte).
    0.10.264 : l'espacement demandé par GDELT est respecté ; une réponse « limit requests » est retentée une fois ;
    toute réponse non JSON remonte avec son texte (pour savoir pourquoi, au lieu d'une simple « panne »).
    En mode liste d'articles, GDELT ne regarde que les 3 derniers mois de la fenêtre demandée (blog GDELT, DOC 2.0)."""
    global _GDELT_REFUS
    if _GDELT_REFUS >= GDELT_REFUS_MAX:
        raise RuntimeError(f"GDELT coupé pour ce passage ({_GDELT_REFUS} refus 429 de suite)")
    params = {"query": gdelt_mots(requete), "mode": "artlist", "format": "json", "maxrecords": 15, "sort": "datedesc"}
    if avant is not None:
        params["enddatetime"] = avant.strftime("%Y%m%d%H%M%S")
        from datetime import timedelta
        params["startdatetime"] = (avant - timedelta(days=90)).strftime("%Y%m%d%H%M%S")
    res = None
    # 0.10.272 : pont par visiondufutur.com (décision d'auteur du 2026-11-18, 15 h 21) quand GDELT_PONT est réglé ;
    # le pont espace lui-même ses requêtes et garde un cache (pont-visiondufutur/gdelt.php)
    pont = (os.environ.get("GDELT_PONT") or "").strip()
    url = pont or "https://api.gdeltproject.org/api/v2/doc/doc"
    entetes = {"X-Pont-Cle": os.environ.get("GDELT_PONT_CLE", "")} if pont else {}
    async with httpx.AsyncClient(timeout=DELAI + (60 if pont else 0)) as c:
        for essai in range(GDELT_ESSAIS):
            if not pont:
                await _gdelt_attendre()
            r = await (c.get(url, params=params, headers=entetes) if pont else c.get(url, params=params))
            if getattr(r, "status_code", 200) == 429 and essai < GDELT_ESSAIS - 1:
                # 0.10.266 : 30 refus « 429 » sur 40 malgré l'espacement (adresses partagées des serveurs de GitHub) :
                # attente croissante, ou celle que GDELT demande (Retry-After), puis nouvel essai
                import asyncio
                try:
                    attente = float(getattr(r, "headers", {}).get("Retry-After") or 0)
                except (TypeError, ValueError):
                    attente = 0.0
                await asyncio.sleep(max(attente, GDELT_PAUSE_429 * 2 ** essai))
                continue
            if getattr(r, "status_code", 200) == 429:
                _GDELT_REFUS += 1
            r.raise_for_status()
            _GDELT_REFUS = 0
            try:
                corps = r.json()
                if isinstance(corps, dict) and "texte_gdelt" in corps:     # réponse texte de GDELT, relayée par le pont
                    raise ValueError(corps["texte_gdelt"])
                res = corps.get("articles") or []
                break
            except ValueError as e:               # GDELT répond en texte quand la requête lui déplaît
                texte = " ".join((str(e) if str(e) and pont else r.text).split())[:200]
                if essai < GDELT_ESSAIS - 1 and re.search(r"limit requests|one every", texte, re.I):
                    continue
                if not texte:                      # corps vide : aucun article
                    res = []
                    break
                raise RuntimeError(f"GDELT : {texte}")
    return "\n\n".join(_ligne(x.get("seendate"), x.get("title"), x.get("url"),
                              f"source : {x.get('domain')} ({x.get('sourcecountry')}, {x.get('language')})")
                       for x in res)


MOTEURS_HTTP = {"tavily": ("TAVILY_API_KEY", tavily), "tinyfish": ("TINYFISH_API_KEY", tinyfish),
                "gdelt": (None, gdelt)}


class Chaine:
    """Un état par passage : la bascule vers la seconde clé Exa vaut pour tout le passage."""

    def __init__(self, exa: Callable[[str], Awaitable[str]] | None = None, env=os.environ, ordre: str | None = None):
        self.exa, self.env, self._ordre = exa, env, ordre
        self.seconde_cle = False
        self.usage: dict[str, int] = {}
        self.echecs: dict[str, int] = {}
        self.erreurs: dict[str, str] = {}      # 0.8.2 : la dernière erreur de chaque moteur, pour savoir QUI échoue

    def ordre(self) -> list[str]:
        brut = self._ordre or self.env.get("ALPHABET_RECHERCHE_ORDRE") or ORDRE_DEFAUT
        return [m.strip() for m in brut.split(",") if m.strip()]

    def _passer_seconde_cle(self) -> bool:
        if not self.seconde_cle and self.env.get("EXA_API_KEY_2"):
            self.env["EXA_API_KEY"] = self.env["EXA_API_KEY_2"]
            self.seconde_cle = True
            return True
        return False

    async def _exa(self, requete: str) -> str:
        try:
            return await self.exa(requete)
        except Exception as e:
            # 0.8.2 : on ne change de clé que pour une erreur d'Exa lui-même (clé, crédits, quota), pas pour une
            # saturation du modèle qui rédige la synthèse.
            if erreur_de_cle_exa(e) and self._passer_seconde_cle():
                return await self.exa(requete)
            raise

    async def chercher(self, requete: str, avant: datetime | None = None) -> str:
        erreurs = []
        for nom in self.ordre():
            if nom == "exa":
                if self.exa is None or not self.env.get("EXA_API_KEY"):
                    continue
                appel = self._exa
            elif nom in MOTEURS_HTTP:
                var, fn = MOTEURS_HTTP[nom]
                if var and not self.env.get(var):
                    continue
                appel = (lambda q, fn=fn: fn(q, avant))
            else:
                continue
            try:
                texte = await appel(requete)
            except Exception as e:
                self.echecs[nom] = self.echecs.get(nom, 0) + 1
                self.erreurs[nom] = f"{type(e).__name__}: {e}"[:200]
                erreurs.append(f"{nom} : {type(e).__name__}: {str(e)[:160]}")      # 0.10.264 : le pourquoi
                continue
            texte = sans_foule(filtrer(texte, retro=avant is not None))[0]
            if texte and texte.strip():
                etiquette = "exa2" if nom == "exa" and self.seconde_cle else nom
                self.usage[etiquette] = self.usage.get(etiquette, 0) + 1
                return f"[moteur : {etiquette}]\n{texte}"
            erreurs.append(f"{nom} : aucun résultat")
        raise RuntimeError("aucun moteur de recherche n'a répondu (" + " ; ".join(erreurs) + ")")


CLE_EXA = re.compile(r"\b40[123]\b|unauthori[sz]ed|invalid api key|api[_ ]key|credits?|quota|payment|exa", re.I)


def erreur_de_cle_exa(e: BaseException) -> bool:
    """Erreur qui vient d'Exa (clé refusée, crédits ou quota épuisés), pas du modèle de synthèse."""
    texte = f"{type(e).__name__}: {e}"
    if re.search(r"at capacity|ServiceUnavailable|litellm|openai", texte, re.I):
        return False
    return bool(CLE_EXA.search(texte))


def moteur_de(texte: str) -> str | None:
    m = re.match(r"\[moteur : ([\w-]+)\]", texte or "")
    return m.group(1) if m else None
