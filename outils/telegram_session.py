"""Créer la « clé de session » Telegram du bot (une seule fois, sur TON ordinateur).

Ce script te connecte à Telegram comme le ferait une application, puis affiche une longue chaîne de caractères : la
clé de session. Le bot s'en servira, depuis GitHub, pour LIRE des canaux publics, sans redemander de code.

ATTENTION : cette clé donne accès à ton compte Telegram. Ne la colle nulle part ailleurs que dans le secret GitHub
TELEGRAM_SESSION. Tu peux la révoquer à tout moment : Telegram → Paramètres → Appareils → fermer la session.
Rien n'est enregistré sur le disque par ce script.

Utilisation (Windows, dans un terminal PowerShell) :
    py -m pip install telethon
    py telegram_session.py
"""
import asyncio
import getpass


async def principal() -> None:
    from telethon import TelegramClient
    from telethon.sessions import StringSession

    api_id = int(input("api_id (le nombre donné par my.telegram.org) : ").strip())
    api_hash = getpass.getpass("api_hash (la chaîne donnée par my.telegram.org, rien ne s'affiche) : ").strip()
    client = TelegramClient(StringSession(), api_id, api_hash)
    # Telethon demande ton numéro (format international, ex. +33612345678), puis le code reçu dans Telegram,
    # puis, si tu en as un, ton mot de passe de validation en deux étapes.
    await client.start()
    moi = await client.get_me()
    cle = client.session.save()
    await client.disconnect()
    print("\nConnecté en tant que :", moi.first_name or moi.username or moi.id)
    print("\n=== CLÉ DE SESSION (à mettre dans le secret GitHub TELEGRAM_SESSION) ===\n")
    print(cle)
    print("\n=== fin de la clé ===")
    print("Copie-la, mets-la dans GitHub, puis ferme cette fenêtre. Ne la partage avec personne.")


if __name__ == "__main__":
    asyncio.run(principal())
