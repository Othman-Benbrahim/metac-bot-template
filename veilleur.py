"""Veilleur du tournoi (bot 0.10.278) : lance le bot dès qu'une question NOUVELLE s'ouvre, jour et nuit.

Décision d'auteur du 2026-11-18, 17 h 12 (« les deux », et surveiller le tournoi principal dès qu'il commencera).
Constat : le déclenchement programmé du bot (toutes les 20 minutes) n'a été honoré que 12 fois du 14 au 18 novembre ;
les questions du MiniBench, ouvertes 3 heures, ont été manquées pour la plupart.

Toutes les 15 minutes : liste les questions ouvertes du MiniBench et du tournoi principal non encore prévues par le
bot (API Metaculus, aucun modèle appelé, aucun coût) ; s'il y en a et qu'aucun passage du bot n'est déjà en cours ou
en attente, lance le bot dans le bon mode. Le tournoi principal est surveillé en permanence : dès qu'il a des
questions ouvertes, il est traité. Se relance lui-même avant la limite de durée de GitHub ; un seul veilleur à la fois
(un déclenchement horaire ne fait que le redémarrer s'il s'est arrêté).
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from datetime import datetime, timezone

from planificateur import Github

MOI = "veilleur.yaml"
BOT = "run_alphabet_bot.yaml"
PAS = 15 * 60
DUREE_PASSAGE = 5 * 3600 + 30 * 60


def nouvelles() -> dict[str, int]:
    """{mode : nombre de questions ouvertes pas encore prévues par le bot}."""
    from forecasting_tools import MetaculusClient
    c = MetaculusClient()
    out = {}
    for mode, cible in (("minibench", c.CURRENT_MINIBENCH_ID), ("tournament", c.CURRENT_AI_COMPETITION_ID)):
        try:
            qs = c.get_all_open_questions_from_tournament(cible)
            out[mode] = sum(1 for q in qs if not q.already_forecasted)
        except Exception as e:
            print(f"::warning::{mode} : liste indisponible ({type(e).__name__}: {str(e)[:120]})", flush=True)
            out[mode] = 0
    return out


def bot_occupe(gh: Github) -> bool:
    return any(x.get("path", "").endswith(BOT) for x in gh.en_cours())


def principal(essai: bool) -> int:
    jeton = os.environ.get("GITHUB_TOKEN")
    if not jeton or not os.environ.get("METACULUS_TOKEN"):
        print("GITHUB_TOKEN ou METACULUS_TOKEN absent.")
        return 1
    gh = Github(jeton)
    moi = os.environ.get("GITHUB_RUN_ID")
    autres = [x for x in gh.en_cours() if x.get("path", "").endswith(MOI) and str(x["id"]) != str(moi)]
    if autres and not essai:
        print("Un autre veilleur tourne déjà : arrêt.")
        return 0
    debut, lances = time.monotonic(), []
    while True:
        t = datetime.now(timezone.utc)
        if time.monotonic() - debut > DUREE_PASSAGE:
            if not essai:
                gh.lancer(MOI)
            print(f"{t:%H:%M} UTC : fin de ce passage, veilleur relancé.", flush=True)
            break
        n = nouvelles()
        a_lancer = [m for m in ("minibench", "tournament") if n.get(m)]
        print(f"{t:%H:%M} UTC : nouvelles questions {n}", flush=True)
        if a_lancer and not essai:
            if bot_occupe(gh):
                print("   le bot tourne déjà ; nouvel examen au prochain tour", flush=True)
            else:
                gh.lancer(BOT, {"mode": a_lancer[0], "max_questions": "0"})
                lances.append(f"{t:%H:%M} {a_lancer[0]} ({n[a_lancer[0]]} question(s))")
                print(f"   bot lancé en mode {a_lancer[0]}", flush=True)
        if essai:
            break
        time.sleep(PAS)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
            f.write("## Veilleur du tournoi\n\n" + ("\n".join(f"- {x}" for x in lances) or "aucun lancement") + "\n")
    return 0


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("--essai", action="store_true")
    sys.exit(principal(a.parse_args().essai))
