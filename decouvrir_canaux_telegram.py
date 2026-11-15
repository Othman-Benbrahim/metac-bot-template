"""Découverte des canaux Telegram selon une règle fixée d'avance (0.10.151, 2026-11-15).

Constat du passage 43754624230 : la recherche globale de Telegram ne remonte presque pas dans le passé (166 couples
pays × date sur 185 à zéro message). Pour mesurer ce qui s'est dit avant une date passée, il faut lire l'historique
de canaux précis. Pour ne pas les choisir à la main, règle fixée ici :
- mots-clés neutres : « world news », « breaking news », « osint », « war news », « conflict news », « geopolitics » ;
- canaux publics (pas les groupes) proposés par la recherche de Telegram pour ces mots ;
- au moins 20 000 abonnés ; les 25 plus suivis.
Écrit registre/telegram-canaux-candidats.json. RIEN n'est utilisé avant validation par l'auteur : la liste validée va
dans registre/telegram-canaux.json.

    python decouvrir_canaux_telegram.py
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

MOTS = ("world news", "breaking news", "osint", "war news", "conflict news", "geopolitics")
ABONNES_MIN = 20000
NOMBRE = 25
SORTIE = Path("registre") / "telegram-canaux-candidats.json"


async def principal() -> int:
    import indicateurs_niche as ni
    from telethon.tl.functions.contacts import SearchRequest
    from telethon.tl.functions.channels import GetFullChannelRequest
    tg = ni.Telegram()
    if not tg.disponible or not await tg.ouvrir():
        print(f"Telegram indisponible : {tg.derniere_erreur}")
        return 1
    vus = {}
    for mot in MOTS:
        try:
            r = await tg.client(SearchRequest(q=mot, limit=50))
        except Exception as e:
            print(f"Recherche « {mot} » impossible : {type(e).__name__}")
            continue
        for ch in r.chats:
            if not getattr(ch, "broadcast", False) or not getattr(ch, "username", None) or ch.username in vus:
                continue
            n = getattr(ch, "participants_count", None)
            if n is None:
                try:
                    n = (await tg.client(GetFullChannelRequest(ch))).full_chat.participants_count
                except Exception:
                    n = 0
            vus[ch.username] = {"canal": ch.username, "titre": ch.title, "abonnes": n or 0, "trouve_par": mot}
    await tg.fermer()
    liste = sorted((v for v in vus.values() if v["abonnes"] >= ABONNES_MIN), key=lambda v: -v["abonnes"])[:NOMBRE]
    SORTIE.parent.mkdir(exist_ok=True)
    SORTIE.write_text(json.dumps({"regle": {"mots": MOTS, "abonnes_min": ABONNES_MIN, "nombre": NOMBRE},
                                  "candidats": liste}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{len(vus)} canaux trouvés ; {len(liste)} retenus par la règle :")
    for v in liste:
        print(f"  @{v['canal']:30s} {v['abonnes']:>9,d} abonnés · {v['titre'][:60]}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(principal()))
