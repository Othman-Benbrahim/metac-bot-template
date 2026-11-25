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
ADRESSES = {
    "ep_liste_xml": "https://www.europarl.europa.eu/meps/en/full-list/xml",
    "ep_reunions_1": "https://www.europarl.europa.eu/meps/en/197606/ZARZALEJOS%20Javier/meetings/past",
    "ep_reunions_2": "https://www.europarl.europa.eu/meps/en/197778/TOM_BERENDSEN/meetings/past",
    "ember_annuel": "https://storage.googleapis.com/emb-prod-bkt-publicdata/public-downloads/yearly_full_release_long_format.csv",
}


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
