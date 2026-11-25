"""2026-11-25 : sonde de sources validées par l'auteur à 16 h 32, AVANT d'écrire leur collecte (regarder la vraie donnée
d'abord). Pour chaque adresse : robots.txt vérifié (politesse.autorise), statut HTTP, type, taille et le début de la
réponse (4 000 caractères au plus), écrits dans registre/sondes/. Rien n'est forcé : un refus est noté.

Sources sondées :
- Parlement européen : liste officielle des députés (export XML) et pages « réunions passées » de deux députés,
  avec le chargement de la suite (« Load more ») si un lien de suite apparaît dans la page.
- Ember : fichier annuel complet de l'électricité (CC BY 4.0).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import politesse  # noqa: E402

SORTIE = Path("registre") / "sondes"
# 2e passage (16 h 45) : le site du Parlement répond 403 (CloudFront) aux machines de GitHub : non forcé.
# Integrity Watch EU (Transparency International EU) republie les mêmes réunions sous licence ODbL 1.0 ;
# l'ancien fichier Ember renvoie vers une nouvelle adresse.
# 3e passage (16 h 50) : la page d'Integrity Watch charge ses données par static/mepmeetings.js ; on lit ce script,
# on y relève les adresses de données, et on sonde chacune (robots vérifié). Ember : refusé par robots.txt, non forcé.
ADRESSES = {
    "iw_script": "https://www.integritywatch.eu/static/mepmeetings.js?v=9",
}
BASE_IW = "https://www.integritywatch.eu/"


def sonder(c: httpx.Client, nom: str, url: str, etat: dict) -> str | None:
    if not politesse.autorise(c, url):
        etat[nom] = {"url": url, "statut": "refuse_robots"}
        return None
    try:
        r = c.get(url)
    except Exception as e:
        etat[nom] = {"url": url, "statut": f"erreur {type(e).__name__}"}
        return None
    texte = r.text
    etat[nom] = {"url": url, "statut": r.status_code, "type": r.headers.get("content-type"), "taille": len(r.content)}
    (SORTIE / f"{nom}.txt").write_text(texte[:4000], encoding="utf-8")
    return texte


def principal() -> int:
    SORTIE.mkdir(parents=True, exist_ok=True)
    etat: dict = {}
    with httpx.Client(headers={"User-Agent": politesse.UA}, follow_redirects=True, timeout=120) as c:
        for nom, url in ADRESSES.items():
            texte = sonder(c, nom, url, etat)
            if texte and nom == "iw_script":
                chemins = sorted(set(re.findall(r'["\'`]([^"\'`\s]+\.(?:json|csv)(?:\?[^"\'`]*)?)["\'`]', texte)))
                etat[nom]["chemins"] = chemins[:40]
                for i, ch in enumerate(chemins[:5]):
                    url = ch if ch.startswith("http") else BASE_IW + ch.lstrip("./")
                    sonder(c, f"iw_donnees_{i}", url, etat)
            if texte and nom.startswith("iw_") and nom != "iw_script":
                # liens de données dans la page (fichiers .json, .csv, dossiers data/)
                etat[nom]["donnees"] = sorted(set(re.findall(r'["\']([^"\']+\.(?:json|csv)(?:\?[^"\']*)?)["\']', texte)))[:40]
                etat[nom]["scripts"] = sorted(set(re.findall(r'<script[^>]+src="([^"]+)"', texte)))[:20]
            if texte and nom.startswith("ep_reunions"):
                # les liens et attributs qui ressemblent à une suite de liste ou à un export
                indices = sorted(set(re.findall(r'(?:href|data-[\w-]+)="([^"]*(?:meeting|load|page|xml|csv|json)[^"]*)"', texte, re.I)))
                etat[nom]["indices"] = indices[:60]
                (SORTIE / f"{nom}-reunions.txt").write_text(
                    "\n".join(m for m in re.findall(r'<div class="erpl_document[^"]*".*?</div>\s*</div>', texte, re.S)[:3]),
                    encoding="utf-8")
    (SORTIE / "etat.json").write_text(json.dumps(etat, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(etat, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(principal())
