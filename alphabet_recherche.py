"""Chaîne de recherche (0.6.2) : Exa, puis la seconde clé Exa, puis Tavily, puis GDELT.

Chaque requête essaie les moteurs dans l'ordre et s'arrête au premier qui rend un résultat. Un moteur sans clé est
sauté. Quand la première clé Exa échoue (quota épuisé, erreur), le bot passe à la seconde pour le reste du passage.
Chaque résultat commence par « [moteur : …] » : le registre sait quel moteur a servi chaque requête.

Ordre modifiable par la variable ALPHABET_RECHERCHE_ORDRE (par défaut « exa,tavily,gdelt »).
Secrets : EXA_API_KEY, EXA_API_KEY_2, TAVILY_API_KEY ; GDELT n'a pas de clé. (Brave Search, qui exige une carte
bancaire même en offre gratuite, a été retiré en 0.6.2.)
"""
from __future__ import annotations

import os
import re
from datetime import datetime
from typing import Awaitable, Callable

import httpx

ORDRE_DEFAUT = "exa,tavily,gdelt"
DELAI = 40


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


async def gdelt(requete: str, avant: datetime | None = None) -> str:
    """GDELT DOC 2.0 : articles de presse mondiaux, sans clé. Renvoie titres, liens et dates (pas le texte)."""
    mots = " ".join(w for w in re.sub(r"[^\w\s-]", " ", requete).split() if len(w) > 2)[:250]
    params = {"query": mots, "mode": "artlist", "format": "json", "maxrecords": 15, "sort": "datedesc"}
    if avant is not None:
        params["enddatetime"] = avant.strftime("%Y%m%d%H%M%S")
    async with httpx.AsyncClient(timeout=DELAI) as c:
        r = await c.get("https://api.gdeltproject.org/api/v2/doc/doc", params=params)
        r.raise_for_status()
        try:
            res = r.json().get("articles") or []
        except ValueError:                    # GDELT répond en texte quand la requête lui déplaît
            raise RuntimeError(f"GDELT : {r.text[:120]}")
    return "\n\n".join(_ligne(x.get("seendate"), x.get("title"), x.get("url"),
                              f"source : {x.get('domain')} ({x.get('sourcecountry')}, {x.get('language')})")
                       for x in res)


MOTEURS_HTTP = {"tavily": ("TAVILY_API_KEY", tavily), "gdelt": (None, gdelt)}


class Chaine:
    """Un état par passage : la bascule vers la seconde clé Exa vaut pour tout le passage."""

    def __init__(self, exa: Callable[[str], Awaitable[str]] | None = None, env=os.environ, ordre: str | None = None):
        self.exa, self.env, self._ordre = exa, env, ordre
        self.seconde_cle = False
        self.usage: dict[str, int] = {}
        self.echecs: dict[str, int] = {}

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
        except Exception:
            if self._passer_seconde_cle():
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
                erreurs.append(f"{nom} : {type(e).__name__}")
                continue
            if texte and texte.strip():
                etiquette = "exa2" if nom == "exa" and self.seconde_cle else nom
                self.usage[etiquette] = self.usage.get(etiquette, 0) + 1
                return f"[moteur : {etiquette}]\n{texte}"
            erreurs.append(f"{nom} : aucun résultat")
        raise RuntimeError("aucun moteur de recherche n'a répondu (" + " ; ".join(erreurs) + ")")


def moteur_de(texte: str) -> str | None:
    m = re.match(r"\[moteur : ([\w-]+)\]", texte or "")
    return m.group(1) if m else None
