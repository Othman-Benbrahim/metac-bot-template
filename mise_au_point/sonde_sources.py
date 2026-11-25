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
import time
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
# 5e passage (18 h 30) : liste publique des élections à venir d'IFES ElectionGuide (adresse donnée par l'auteur).
# 6e passage (22 h 21) : bne IntelliNews (adresse donnée par l'auteur) ; mur payant, on cherche seulement un flux de
# TITRES gratuit (règles du site, liens RSS annoncés par l'accueil, adresses de flux usuelles). Aucun article lu.
# 8e passage (22 h 42, décision de l'auteur « banco ») : structure des tableaux des trackers Just Security (en-têtes,
# 3 premières lignes, cellules coupées à 300 caractères, liens de cellule relevés) et glossaire des statuts. robots.txt :
# permis, « Crawl-delay: 3 » respecté. Rien d'autre n'est gardé.
ADRESSES = {
    "jst_proces": "https://www.justsecurity.org/107087/tracker-litigation-legal-challenges-trump-administration/",
    "jst_glossaire": "https://www.justsecurity.org/161783/litigation-tracker-case-status-key-glossary/",
    "jst_habeas": "https://www.justsecurity.org/133928/immigration-habeas-tracker/",
    "jst_corruption": "https://www.justsecurity.org/117267/anti-corruption-tracker/",
}


def _cellules(ligne: str) -> list[dict]:
    out = []
    for c in re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", ligne, re.S | re.I):
        texte = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", c)).strip()
        out.append({"texte": texte[:300], "liens": re.findall(r'href="([^"]+)"', c)[:3]})
    return out


def structure_tableaux(texte: str, n: int = 3) -> list[dict]:
    res = []
    for t in re.findall(r"<table.*?</table>", texte, re.S | re.I)[:6]:
        lignes = re.findall(r"<tr.*?</tr>", t, re.S | re.I)
        res.append({"lignes": len(lignes), "attributs_table": re.match(r"<table[^>]*>", t, re.I).group(0)[:300],
                    "entete": _cellules(lignes[0]) if lignes else [], "exemples": [_cellules(l) for l in lignes[1:1 + n]]})
    return res
IN_FLUX_USUELS = ["https://www.intellinews.com/feed/", "https://www.intellinews.com/rss/",
                  "https://www.intellinews.com/rss.xml", "https://www.intellinews.com/feed.xml"]
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
            if texte and nom.startswith("jst_"):
                etat[nom]["tableaux"] = structure_tableaux(texte, 8 if nom == "jst_glossaire" else 3)
                (SORTIE / f"{nom}.txt").unlink(missing_ok=True)   # pas de texte de page gardé
                time.sleep(3)                                      # Crawl-delay: 3 du site
            if texte and nom == "js_robots":
                (SORTIE / "js_robots.txt").write_text(texte[:20000], encoding="utf-8")
            if texte and nom == "js_accueil":
                etat[nom]["flux_annonces"] = re.findall(r'<link[^>]+(?:rss|atom)[^>]*>', texte, re.I)[:10]
                trackers = sorted(set(u for u in re.findall(r'href="(https://www\.justsecurity\.org/[^"#?]+)"', texte)
                                      if "tracker" in u.lower()))[:8]
                etat[nom]["trackers"] = trackers
                flux = [m for a in etat[nom]["flux_annonces"] for m in re.findall(r'href="([^"]+)"', a)][:1] or \
                       ["https://www.justsecurity.org/feed/"]
                t = sonder(c, "js_flux", flux[0], etat)
                if t:
                    etat["js_flux"]["items"] = len(re.findall(r"<item|<entry", t))
                    etat["js_flux"]["titres"] = [re.sub(r"<!\[CDATA\[|\]\]>", "", x).strip()
                                                 for x in re.findall(r"<title>(.*?)</title>", t, re.S)[:6]]
                for i, u in enumerate(trackers):
                    t = sonder(c, f"js_tracker_{i}", u, etat)
                    if t:
                        e = etat[f"js_tracker_{i}"]
                        e["tableaux"] = len(re.findall(r"<table", t, re.I))
                        e["lignes_tableaux"] = len(re.findall(r"<tr", t, re.I))
                        e["integres"] = sorted(set(re.findall(r'(?:src|href)="([^"]*(?:docs\.google|airtable|datawrapper|flourish|\.csv|\.xlsx|\.json|tableau)[^"]*)"', t, re.I)))[:10]
                        (SORTIE / f"js_tracker_{i}.txt").unlink(missing_ok=True)   # on ne garde pas le texte des pages
            if texte and nom == "in_robots":
                (SORTIE / "in_robots.txt").write_text(texte[:20000], encoding="utf-8")
            if texte and nom == "in_accueil":
                annonces = re.findall(r'<link[^>]+(?:rss|atom)[^>]*>', texte, re.I)
                liens = sorted(set(re.findall(r'href="([^"]*(?:rss|feed|atom)[^"]*)"', texte, re.I)))[:30]
                etat[nom]["flux_annonces"] = annonces[:10]
                etat[nom]["liens_flux"] = liens
                cands = [m for a in annonces for m in re.findall(r'href="([^"]+)"', a)] + liens + IN_FLUX_USUELS
                vus = []
                for u in cands:
                    u = u if u.startswith("http") else "https://www.intellinews.com/" + u.lstrip("/")
                    if u in vus or len(vus) >= 8:
                        continue
                    vus.append(u)
                    t = sonder(c, f"in_flux_{len(vus)}", u, etat)
                    if t:
                        etat[f"in_flux_{len(vus)}"]["items"] = len(re.findall(r"<item|<entry", t))
                        etat[f"in_flux_{len(vus)}"]["titres"] = [re.sub(r"<!\[CDATA\[|\]\]>", "", x).strip()
                                                               for x in re.findall(r"<title>(.*?)</title>", t, re.S)[:8]]
            if texte and nom == "eg_avenir":
                etat[nom]["entetes"] = re.findall(r"<th[^>]*>(.*?)</th>", texte, re.S)[:20]
                etat[nom]["lignes_table"] = len(re.findall(r"<tr", texte))
                etat[nom]["donnees"] = sorted(set(re.findall(r'["\']([^"\']*(?:api|json|ajax)[^"\']*)["\']', texte)))[:30]
                (SORTIE / "eg_avenir-table.txt").write_text("\n".join(re.findall(r"<tr.*?</tr>", texte, re.S)[:6]), encoding="utf-8")
            if texte and nom == "iw_script":
                # 4e passage (16 h 55) : les fichiers sondés sont ceux de la législature 9 (2019-2024) ; la législature
                # en cours se lit par autoupdate_data_eu + backups.json. On garde le code autour de ces mots pour lire
                # comment l'adresse est construite.
                extraits = []
                for mot in ("autoupdate_data_eu", "backups.json", "legislature_10", "timestamp", "dpi_legislature_10"):
                    for m in re.finditer(re.escape(mot), texte):
                        extraits.append(f"--- {mot} @{m.start()}\n" + texte[max(0, m.start() - 600): m.start() + 600])
                (SORTIE / "iw_script_extraits.txt").write_text("\n\n".join(extraits[:25]), encoding="utf-8")
                chemins = sorted(set(re.findall(r'["\'`]([^"\'`\s]+\.(?:json|csv)(?:\?[^"\'`]*)?)["\'`]', texte)))
                etat[nom]["chemins"] = chemins[:40]
                for i, ch in enumerate([c for c in chemins if "legislature_9" not in c][:5]):
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
