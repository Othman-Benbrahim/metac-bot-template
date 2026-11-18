"""Archive les recherches capturées en direct dans un dépôt Hugging Face PRIVÉ (bot 0.10.297).

Décision d'auteur du 2026-11-18, 22 h 14 (« oui, je te suis ») : le cache de GitHub Actions n'est pas un stockage
durable ; l'archive va sur Hugging Face. Les textes sont des extraits d'articles qui ne nous appartiennent pas : on
les garde pour nos bancs, on ne les republie JAMAIS. D'où :
- un dépôt SÉPARÉ du jeu public (par défaut « alphabet-captures », variable HF_CAPTURES), créé privé ;
- garde-fou : avant tout envoi, le dépôt est relu chez Hugging Face ; s'il n'est pas privé, RIEN n'est envoyé ;
- seuls les fichiers absents de l'archive partent ; aucune erreur ne remonte au passage du bot.

    python archiver_captures.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

DOSSIER = Path(os.environ.get("ALPHABET_CAPTURE_DOSSIER", "cache/recherche-tournoi"))
SOUS_DOSSIER = "recherches"


def depot_complet(api, nom: str) -> str:
    return nom if "/" in nom else f"{api.whoami()['name']}/{nom}"


def a_envoyer(locaux: list[str], distants: set[str]) -> list[str]:
    return sorted(f for f in locaux if f"{SOUS_DOSSIER}/{f}" not in distants)


def archiver(api, nom: str, dossier: Path = DOSSIER) -> int:
    depot = depot_complet(api, nom)
    api.create_repo(depot, repo_type="dataset", private=True, exist_ok=True)
    if not api.repo_info(depot, repo_type="dataset").private:            # garde-fou : jamais d'envoi en public
        raise RuntimeError(f"le dépôt {depot} n'est pas privé : rien n'est envoyé")
    locaux = sorted(p.name for p in dossier.glob("*.txt")) if dossier.is_dir() else []
    nouveaux = a_envoyer(locaux, set(api.list_repo_files(depot, repo_type="dataset")))
    if not nouveaux:
        return 0
    api.upload_folder(folder_path=str(dossier), repo_id=depot, repo_type="dataset", path_in_repo=SOUS_DOSSIER,
                      allow_patterns=nouveaux,
                      commit_message=f"{len(nouveaux)} recherche(s) capturée(s) (GitHub {os.environ.get('GITHUB_SHA', '')[:7]})")
    return len(nouveaux)


def principal() -> int:
    jeton, nom = os.environ.get("HF_TOKEN"), os.environ.get("HF_CAPTURES") or "alphabet-captures"
    if not jeton:
        print("::warning::HF_TOKEN absent : recherches capturées non archivées (elles restent dans le cache).")
        return 0
    try:
        from huggingface_hub import HfApi
        n = archiver(HfApi(token=jeton), nom)
        print(f"Archive Hugging Face (privée) : {n} nouvelle(s) recherche(s).")
    except Exception as e:                                   # n'empêche jamais le passage du bot de s'enregistrer
        print(f"::warning::archivage des recherches capturées impossible : {type(e).__name__}: {str(e)[:300]}")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
