"""Collecteur quotidien de flux RSS (0.10.152, décision d'auteur du 2026-11-15, 21 h 26). Aucun modèle de langue.

Les flux RSS ne donnent que les derniers articles, sans historique : on les lit chaque jour pour constituer notre
propre historique. On ne garde que des COMPTES (pays mentionné × jour × famille de source), jamais les textes.
Familles (choisies par l'auteur) :
- officiel : ReliefWeb (ONU, rapports humanitaires), avis de voyage britanniques, alertes GDACS et séismes USGS ;
- parlement_ue (0.10.155) : Parlement européen (relations extérieures, commissions AFET, DROI, SEDE, propositions de
  résolution, textes adoptés) : l'attention institutionnelle européenne portée à un pays ;
- sante (0.10.157) : OMS Disease Outbreak News (API OData), ECDC (menaces, mises à jour, risques, grippe aviaire),
  Fonds mondial (communiqués, mises à jour ; 0.10.158) ;
- voix_citoyennes (0.10.158) : Global Voices, 11 flux régionaux ;
- think_tanks et economie (0.10.159) : ECFR ; Investing.com (actualité économique, indicateurs), investingLive
  (0.10.160), IATA (0.10.161) ; famille dérivée « notation » : articles économiques qui nomment une agence de notation ;
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
import os
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
        "https://www.theglobalfund.org/data/rss-feeds/news-releases/",  # 0.10.158 : Fonds mondial, communiqués
        "https://www.theglobalfund.org/data/rss-feeds/updates/",        # 0.10.158 : Fonds mondial, mises à jour
    ],
    # 0.10.158 : Global Voices (médias citoyens, réseau mondial de blogueurs et traducteurs) ; les 11 flux régionaux
    # couvrent tous les pays, le pays de chaque article est détecté comme ailleurs.
    "voix_citoyennes": [f"https://globalvoices.org/-/world/{r}/feed/" for r in (
        "caribbean", "central-asia-caucasus", "east-asia", "eastern-central-europe", "latin-america", "north-america",
        "oceania", "south-asia", "sub-saharan-africa", "middle-east-north-africa", "western-europe")],
    # 0.10.159 (2026-11-15, 22 h 16) : analyse géopolitique européenne (ECFR, articles et publications) et économie
    # (Investing.com en français : actualité économique, indicateurs économiques). Familles séparées, non mélangées
    # à la presse générale.
    "think_tanks": [
        "https://ecfr.eu/feed/?post_type=post",
        "https://ecfr.eu/feed/?post_type=publication",
    ],
    "economie": [
        "https://fr.investing.com/rss/news_14.rss",
        "https://fr.investing.com/rss/news_95.rss",
        "https://www.iata.org/api/rss/pressrelease",   # 0.10.161 : IATA (demande passagers et fret, mensuelle)
        "https://investinglive.com/feed/",   # 0.10.160 : ex-ForexLive (macro, banques centrales, données au fil de l'eau)
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
SANTE = Path("registre") / "rss-sante.csv"   # 0.10.162 : état de chaque flux (dernier essai, dernier succès, dernier nouvel article)
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
# 0.10.160 : les décisions des agences de notation passent par la presse économique (pas de flux public des agences) ;
# un article de la famille « economie » qui nomme une agence ET un mot de notation compte aussi dans « notation ».
NOTATION = re.compile(r"\b(Fitch|Moody'?s|S&P|Standard (?:&|and) Poor'?s|DBRS|Scope Ratings)\b.*?"
                      r"\b(rating|notation|note|outlook|perspective|downgrade|upgrade|abaiss|relève|affirm|confirm)",
                      re.I | re.S)


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


# 0.10.163 : certains sites (ONU, Parlement européen, ECFR) refusent les agents inconnus ; second essai avec l'en-tête
# d'un navigateur ordinaire, comme le ferait un lecteur de flux, en gardant notre identité dans « From ».
NAVIGATEUR = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0",
              "Accept": "application/rss+xml, application/atom+xml, application/xml;q=0.9, text/xml;q=0.8, */*;q=0.5",
              "Accept-Language": "fr,en;q=0.8", "From": "alphabet-situationnel-bot (GitHub Othman-Benbrahim)"}


def lire(c: httpx.Client, url: str) -> httpx.Response:
    r = c.get(url)
    if r.status_code in (401, 403, 406, 429) or (r.status_code == 200 and r.content.lstrip()[:15].lower().startswith((b"<!doctype html", b"<html"))):
        r = c.get(url, headers=NAVIGATEUR)
    r.raise_for_status()
    if r.content.lstrip()[:15].lower().startswith((b"<!doctype html", b"<html")):
        raise ValueError("page HTML au lieu d'un flux")
    return r


def describe(e: Exception) -> str:
    if isinstance(e, httpx.HTTPStatusError):
        return f"HTTP {e.response.status_code}"
    return f"{type(e).__name__}: {str(e)[:60]}" if str(e) else type(e).__name__


def bilan_sante(lignes: list[dict], aujourdhui: str, silence: int = 7) -> str:
    """Résumé lisible : flux en erreur, vides, ou sans nouvel article depuis `silence` jours."""
    from datetime import date
    j0 = date.fromisoformat(aujourdhui)
    def age(d):
        return (j0 - date.fromisoformat(d)).days if d else None
    erreurs = [x for x in lignes if str(x.get("statut", "")).startswith("erreur")]
    vides = [x for x in lignes if x.get("statut") == "vide"]
    muets = [x for x in lignes if x.get("statut") == "ok" and (age(x.get("dernier_nouveau")) or 0) >= silence]
    ok = len(lignes) - len(erreurs) - len(vides) - len(muets)
    out = [f"## Santé des flux RSS ({aujourdhui})", "",
           f"{len(lignes)} flux : {ok} en bon état, {len(erreurs)} en erreur, {len(vides)} vides, "
           f"{len(muets)} sans nouvel article depuis {silence} jours ou plus.", ""]
    for titre, groupe, champ in (("En erreur", erreurs, "statut"), ("Vides", vides, "dernier_succes"),
                                 (f"Muets ({silence} j et plus)", muets, "dernier_nouveau")):
        if groupe:
            out += [f"### {titre}", "", "| famille | flux | détail |", "|---|---|---|"]
            out += [f"| {x.get('famille', '')} | {x['url']} | {champ} : {x.get(champ) or 'jamais'} |" for x in groupe]
            out.append("")
    return "\n".join(out)


def principal() -> int:
    vus = set(VUS.read_text(encoding="utf-8").split()) if VUS.exists() else set()
    comptes: dict[tuple, int] = {}
    if COMPTES.exists():
        for x in csv.DictReader(COMPTES.open(encoding="utf-8")):
            comptes[(x["pays"], x["jour"], x["famille"])] = int(x["articles"])
    nouveaux = 0
    aujourdhui = datetime.now(timezone.utc).date().isoformat()
    sante = {x["url"]: x for x in csv.DictReader(SANTE.open(encoding="utf-8"))} if SANTE.exists() else {}
    with httpx.Client(headers=UA, follow_redirects=True, timeout=30) as c:
        motifs = noms_pays(c)
        print(f"{len(motifs)} noms de pays (anglais et français).")
        for famille, urls in FLUX.items():
            for url in urls:
                try:
                    r = lire(c, url)
                    arts = (articles_oms(r.json()) if "who.int/api/" in url
                            else articles(r.content, titres_seuls=famille in TITRES_SEULS))
                except Exception as e:
                    detail = describe(e)
                    print(f"  flux indisponible : {url[:70]} ({detail})")
                    st = sante.setdefault(url, {"url": url, "dernier_succes": "", "dernier_nouveau": ""})
                    st.update(famille=famille, dernier_essai=aujourdhui, statut=f"erreur {detail}", articles=0)
                    continue
                n = 0
                for a in arts:
                    if a["empreinte"] in vus:
                        continue
                    vus.add(a["empreinte"])
                    pays = detecter(a["texte"], motifs)
                    familles = [famille] + (["notation"] if famille == "economie" and NOTATION.search(a["texte"]) else [])
                    for p in pays:
                        for fa in familles:
                            comptes[(p, a["jour"], fa)] = comptes.get((p, a["jour"], fa), 0) + 1
                    n += 1
                nouveaux += n
                st = sante.setdefault(url, {"url": url, "dernier_succes": "", "dernier_nouveau": ""})
                st.update(famille=famille, dernier_essai=aujourdhui, statut="ok" if arts else "vide", articles=len(arts))
                if arts:
                    st["dernier_succes"] = aujourdhui
                if n:
                    st["dernier_nouveau"] = aujourdhui
                print(f"  {famille:8s} {url[:70]:70s} : {len(arts)} articles, {n} nouveaux")
    COMPTES.parent.mkdir(exist_ok=True)
    with COMPTES.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["pays", "jour", "famille", "articles"])
        for (p, j, fa), n in sorted(comptes.items(), key=lambda t: (t[0][1], t[0][0], t[0][2])):
            w.writerow([p, j, fa, n])
    VUS.write_text("\n".join(sorted(vus)), encoding="utf-8")
    actuels = {u for urls in FLUX.values() for u in urls}
    with SANTE.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["url", "famille", "dernier_essai", "statut", "articles", "dernier_succes",
                                          "dernier_nouveau"])
        w.writeheader()
        for u in sorted(actuels & set(sante)):
            w.writerow({k: sante[u].get(k, "") for k in w.fieldnames})
    rapport = bilan_sante([sante[u] for u in sorted(actuels & set(sante))], aujourdhui)
    print(rapport)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
            f.write(rapport + "\n")
    print(f"{nouveaux} nouveaux articles comptés ; {len(comptes)} cases pays × jour × famille.")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
