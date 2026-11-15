"""Collecteur quotidien de flux RSS (0.10.152, décision d'auteur du 2026-11-15, 21 h 26). Aucun modèle de langue.

Les flux RSS ne donnent que les derniers articles, sans historique : on les lit chaque jour pour constituer notre
propre historique. On ne garde que des COMPTES (pays mentionné × jour × famille de source), jamais les textes.
Familles (choisies par l'auteur) :
- officiel : ReliefWeb (ONU, rapports humanitaires), avis de voyage britanniques, alertes GDACS et séismes USGS ;
- parlement_ue (0.10.155) : Parlement européen (relations extérieures, commissions AFET, DROI, SEDE, propositions de
  résolution, textes adoptés) : l'attention institutionnelle européenne portée à un pays ;
- sante (0.10.157) : OMS Disease Outbreak News (API OData), ECDC (menaces, mises à jour, risques, grippe aviaire) ;
- renseignement et lettres_fr (0.10.156) : Intelligence Online, Africa Intelligence ; La Lettre, Glitz (Indigo
  Publications), titres seuls ;
- presse : presse francophone internationale retenue dans l'atlas atlasflux.saynete.com (un titre par groupe, regards
  France, Suisse, Canada, Afrique, Asie ; presse régionale qui reprend les mêmes dépêches écartée).
Pays reconnus par leurs noms anglais ET français (Unicode CLDR), ramenés au code ISO à deux lettres.
Registres : registre/rss-comptes.csv (pays, jour, famille, articles) ; registre/rss-vus.txt (empreintes des articles
déjà comptés, pour ne pas compter deux fois un article encore présent le lendemain).

    python collecte_rss.py
"""
from __future__ import annotations

import csv
import hashlib
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

import httpx

FLUX = {
    "officiel": [
        "https://reliefweb.int/updates/rss.xml",
        "https://www.gov.uk/foreign-travel-advice.atom",
        "https://www.gdacs.org/xml/rss.xml",
        "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/significant_month.atom",
        "https://news.un.org/feed/subscribe/en/news/all/rss.xml",          # 0.10.156 : ONU Info (toutes les actualités)
    ],
    # 0.10.156 (décision d'auteur du 2026-11-15, 21 h 56) : lettres confidentielles d'Indigo Publications, TITRES SEULS
    # (contenu réservé aux abonnés) ; le renseignement et l'Afrique sont suivis à part ; La Lettre (pouvoir en France)
    # et Glitz (industrie du luxe) sont collectés dans une famille distincte, non branchée sur les conflits.
    # 0.10.157 (2026-11-15, 22 h) : santé mondiale. OMS « Disease Outbreak News » par son API OData (le site n'a plus
    # de RSS) et les flux de l'ECDC sur les menaces. Le flux IMDRF proposé est figé depuis 2021 (dispositifs médicaux).
    "sante": [
        "https://www.who.int/api/news/diseaseoutbreaknews?$orderby=PublicationDateAndTime%20desc&$top=50",
        "https://www.ecdc.europa.eu/en/taxonomy/term/1505/feed",   # rapport hebdomadaire des menaces transmissibles
        "https://www.ecdc.europa.eu/en/taxonomy/term/1310/feed",   # mises à jour épidémiologiques
        "https://www.ecdc.europa.eu/en/taxonomy/term/1295/feed",   # évaluations de risque
        "https://www.ecdc.europa.eu/en/taxonomy/term/323/feed",    # grippe aviaire
    ],
    "renseignement": [
        "http://feeds.feedburner.com/IntelligenceOnline-fr",
        "http://feeds.feedburner.com/AfricaIntelligence-fr",
    ],
    "lettres_fr": [
        "http://feeds.feedburner.com/LaLettre-fr",
        "http://feeds.feedburner.com/glitz-fr",
    ],
    # 0.10.155 (décision d'auteur du 2026-11-15, 21 h 50) : attention institutionnelle européenne sur les pays
    "parlement_ue": [
        "https://www.europarl.europa.eu/rss/topic/903/fr.xml",           # actualités : relations extérieures
        "https://www.europarl.europa.eu/rss/committee/afet/fr.xml",      # commission des affaires étrangères
        "https://www.europarl.europa.eu/rss/committee/droi/fr.xml",      # sous-commission des droits de l'homme
        "https://www.europarl.europa.eu/rss/committee/sede/fr.xml",      # sous-commission sécurité et défense
        "https://www.europarl.europa.eu/rss/doc/motions/fr.xml",         # propositions de résolution
        "https://www.europarl.europa.eu/rss/doc/texts-adopted/fr.xml",   # textes adoptés
    ],
    "presse": [
        "https://www.rfi.fr/fr/monde/rss",
        "https://sympli.rss-fusion.com/rss/ed181345284980c7c79fadd0f5f23b1c21c4f0fe6f70b868",   # France 24 : monde
        "https://www.lemonde.fr/international/rss_full.xml",
        "https://www.courrierinternational.com/feed/all/rss.xml",
        "https://www.la-croix.com/feeds/rss/international.xml",
        "https://www.lefigaro.fr/rss/figaro_international.xml",
        "https://www.liberation.fr/arc/outboundfeeds/rss/category/international/?outputType=xml",
        "https://www.rts.ch/info/monde/?format=rss/news",
        "https://www.ledevoir.com/rss/section/monde.xml?id=76",
        "https://burkina24.com/category/actualite/monde/feed/",
        "https://lefaso.net/spip.php?page=backend&id_rubrique=7",
        "https://fr.hespress.com/monde/feed",
        "https://www.tsa-algerie.com/category/international/feed/",
        "https://fr.yna.co.kr/RSS/international.xml",
    ],
}
CLDR = "https://raw.githubusercontent.com/unicode-org/cldr-json/main/cldr-json/cldr-localenames-full/main/{l}/territories.json"
COMPTES = Path("registre") / "rss-comptes.csv"
VUS = Path("registre") / "rss-vus.txt"
UA = {"User-Agent": "alphabet-situationnel-bot/1.0 (recherche ; GitHub Othman-Benbrahim)"}


def noms_pays(c: httpx.Client) -> list[tuple[re.Pattern, str]]:
    """(motif, code ISO) pour les noms anglais et français des pays (codes à deux lettres seulement)."""
    motifs = {}
    for langue in ("en", "fr"):
        try:
            d = c.get(CLDR.format(l=langue), timeout=60).json()
            terr = d["main"][langue]["localeDisplayNames"]["territories"]
        except Exception:
            continue
        for code, nom in terr.items():
            code2 = code.split("-")[0]
            if len(code2) == 2 and code2.isalpha() and code2 not in ("EU", "EZ", "UN", "ZZ", "QO"):
                motifs.setdefault(nom.lower(), code2)
    extra = {"gaza": "PS", "cisjordanie": "PS", "west bank": "PS", "rdc": "CD", "drc": "CD", "congo-kinshasa": "CD",
             "russie": "RU", "russia": "RU", "ukraine": "UA", "usa": "US", "états-unis": "US", "royaume-uni": "GB"}
    for k, v in extra.items():
        motifs.setdefault(k, v)
    return [(re.compile(r"(?<![\w-])" + re.escape(n) + r"(?![\w-])", re.I), code)
            for n, code in sorted(motifs.items(), key=lambda t: -len(t[0])) if len(n) >= 4 or n in ("iran", "iraq", "irak", "mali", "oman", "togo", "chad", "peru", "cuba", "laos", "fiji")]


def detecter(texte: str, motifs: list[tuple[re.Pattern, str]]) -> set[str]:
    """Noms du plus long au plus court ; un nom trouvé est masqué (« South Sudan » ne compte pas aussi « Sudan »)."""
    trouves = set()
    for m, code in motifs:
        if m.search(texte):
            trouves.add(code)
            texte = m.sub(" ", texte)
    return trouves


TITRES_SEULS = {"renseignement", "lettres_fr"}


def articles(xml: bytes, titres_seuls: bool = False) -> list[dict]:
    racine = ET.fromstring(xml)
    ns = lambda t: t.split("}", 1)[-1]
    out = []
    for e in racine.iter():
        if ns(e.tag) not in ("item", "entry"):
            continue
        champs = {}
        for f in e:
            t = ns(f.tag)
            if t == "link" and f.get("href"):
                champs.setdefault("link", f.get("href"))
            elif f.text:
                champs.setdefault(t, f.text.strip())
        quand = champs.get("pubDate") or champs.get("updated") or champs.get("published") or champs.get("date")
        try:
            d = parsedate_to_datetime(quand) if quand and not quand[:4].isdigit() else datetime.fromisoformat(quand.replace("Z", "+00:00"))
            jour = d.astimezone(timezone.utc).date().isoformat()
        except Exception:
            jour = datetime.now(timezone.utc).date().isoformat()
        texte = " ".join(champs.get(k, "") for k in (("title",) if titres_seuls else ("title", "description", "summary", "category")))
        cle = champs.get("guid") or champs.get("id") or champs.get("link") or champs.get("title", "")
        out.append({"jour": jour, "texte": re.sub(r"<[^>]+>", " ", texte), "empreinte": hashlib.sha1(cle.encode()).hexdigest()[:16]})
    return out


def articles_oms(donnees: dict) -> list[dict]:
    """API OData de l'OMS (Disease Outbreak News) : titre (« maladie – pays ») et résumé, date de publication réelle."""
    out = []
    for v in donnees.get("value", []):
        quand = v.get("PublicationDateAndTime") or v.get("PublicationDate") or ""
        try:
            jour = datetime.fromisoformat(quand.replace("Z", "+00:00")).astimezone(timezone.utc).date().isoformat()
        except Exception:
            continue
        texte = re.sub(r"<[^>]+>", " ", f"{v.get('OverrideTitle') or v.get('Title') or ''} {v.get('Summary') or ''}")
        cle = str(v.get("Id") or v.get("DonId") or v.get("UrlName") or texte[:80])
        out.append({"jour": jour, "texte": texte, "empreinte": hashlib.sha1(("oms:" + cle).encode()).hexdigest()[:16]})
    return out


def principal() -> int:
    vus = set(VUS.read_text(encoding="utf-8").split()) if VUS.exists() else set()
    comptes: dict[tuple, int] = {}
    if COMPTES.exists():
        for x in csv.DictReader(COMPTES.open(encoding="utf-8")):
            comptes[(x["pays"], x["jour"], x["famille"])] = int(x["articles"])
    nouveaux = 0
    with httpx.Client(headers=UA, follow_redirects=True, timeout=30) as c:
        motifs = noms_pays(c)
        print(f"{len(motifs)} noms de pays (anglais et français).")
        for famille, urls in FLUX.items():
            for url in urls:
                try:
                    r = c.get(url)
                    r.raise_for_status()
                    arts = (articles_oms(r.json()) if "/api/" in url
                            else articles(r.content, titres_seuls=famille in TITRES_SEULS))
                except Exception as e:
                    print(f"  flux indisponible : {url[:70]} ({type(e).__name__})")
                    continue
                n = 0
                for a in arts:
                    if a["empreinte"] in vus:
                        continue
                    vus.add(a["empreinte"])
                    pays = detecter(a["texte"], motifs)
                    for p in pays:
                        comptes[(p, a["jour"], famille)] = comptes.get((p, a["jour"], famille), 0) + 1
                    n += 1
                nouveaux += n
                print(f"  {famille:8s} {url[:70]:70s} : {len(arts)} articles, {n} nouveaux")
    COMPTES.parent.mkdir(exist_ok=True)
    with COMPTES.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["pays", "jour", "famille", "articles"])
        for (p, j, fa), n in sorted(comptes.items(), key=lambda t: (t[0][1], t[0][0], t[0][2])):
            w.writerow([p, j, fa, n])
    VUS.write_text("\n".join(sorted(vus)), encoding="utf-8")
    print(f"{nouveaux} nouveaux articles comptés ; {len(comptes)} cases pays × jour × famille.")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
