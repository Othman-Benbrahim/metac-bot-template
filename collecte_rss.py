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
- economie (0.10.159 ; think_tanks/ECFR retiré en 0.10.167) : Investing.com (actualité économique, indicateurs), investingLive
  (0.10.160), IATA (0.10.161) ; famille dérivée « notation » : articles économiques qui nomment une agence de notation ;
- renseignement et lettres_fr (0.10.156) : Intelligence Online, Africa Intelligence ; La Lettre, Glitz (Indigo
  Publications), titres seuls ;
- cyber (0.10.199, en ombre) : CERT-FR (ANSSI) ; rapports « Menaces et incidents » qui nomment un attaquant ou un pays ;
- verification et enquete (0.10.200, en ombre) : Correctiv, vérifications de faits (pression de désinformation) et
  enquêtes ; noms de pays allemands en plus, pour ces deux familles seulement ;
- presse : presse francophone internationale retenue dans l'atlas atlasflux.saynete.com (un titre par groupe, regards
  France, Suisse, Canada, Afrique, Asie ; presse régionale qui reprend les mêmes dépêches écartée).
Pays reconnus par leurs noms anglais ET français (Unicode CLDR), ramenés au code ISO à deux lettres. 0.10.199, en ombre :
comptes parallèles « famille_large » qui reconnaissent aussi les adjectifs de nationalité (mledoze/countries, ODbL) ;
les comptes historiques gardent leur définition (noms seuls).
Registres : registre/rss-comptes.csv (pays, jour, famille, articles) ; registre/rss-vus.txt (empreintes des articles
déjà comptés, pour ne pas compter deux fois un article encore présent le lendemain) ; registre/rss-titres.csv
(0.10.198 : empreintes des titres normalisés et jour, pour ne pas compter une reprise du même article ; jamais le titre).

    python collecte_rss.py
"""
from __future__ import annotations

import csv
import os
import hashlib
import re
import sys
import unicodedata
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

import httpx

FLUX = {
    "officiel": [
        # 0.10.167 : ReliefWeb retiré (page vide pour GitHub et FeedBurner ; API réservée aux organisations)
        "https://www.gov.uk/foreign-travel-advice.atom",
        "https://www.gdacs.org/xml/rss.xml",
        "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/significant_month.atom",
        # 0.10.156 : ONU Info ; 0.10.164 : le flux « toutes les actualités » renvoie 404, remplacé par les 5 flux régionaux
        # 0.10.170 : ONU Info retiré (anciens flux en 404, flux français bloqué par CloudFront même dans un navigateur)
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
    # 0.10.165 : le site du Parlement renvoie une page vide aux serveurs de GitHub ; relais FeedBurner créés par
    # l'auteur (2026-11-15), même contenu, même ordre.
    "parlement_ue": [
        "https://feeds.feedburner.com/europa/hMbj972YL3S",  # topic/903           # actualités : relations extérieures
        "https://feeds.feedburner.com/europa/han23L6OwaM",  # committee/afet      # commission des affaires étrangères
        "https://feeds.feedburner.com/europa/L2FFkjEMMuC",  # committee/droi      # sous-commission des droits de l'homme
        "https://feeds.feedburner.com/europa/iCspPtqfmYa",  # committee/sede      # sous-commission sécurité et défense
        "https://feeds.feedburner.com/europa/7KToFj21lKH",  # doc/motions         # propositions de résolution
        "https://feeds.feedburner.com/europa/4MusBpiFxYU",  # doc/texts-adopted   # textes adoptés
    ],
    # 0.10.199 (décision d'auteur du 2026-11-16, 18 h 28, en ombre) : CERT-FR (ANSSI). Les avis et alertes portent sur
    # des produits ; ce qui compte ici, ce sont les rapports « Menaces et incidents » qui nomment un attaquant ou un pays
    # (acte public d'une agence d'État). Pays reconnus par noms ET adjectifs (« iranienne »).
    "cyber": ["https://cert.cyber.gouv.fr/flux-rss/"],
    # 0.10.200 (décision d'auteur du 2026-11-16, 18 h 37, en ombre) : Correctiv (rédaction d'enquête allemande).
    # « verification » (Faktencheck : pression de désinformation) est lue AVANT « enquete » (flux général) : un
    # article présent dans les deux flux garde le même identifiant et n'est compté qu'une fois, en vérification.
    "verification": ["https://correctiv.org/thema/faktencheck/feed/"],
    "enquete": ["https://correctiv.org/feed/"],
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
        "https://feeds.feedburner.com/lefaso/ODhP2vnmuWf",  # 0.10.169 : relais FeedBurner de l'auteur
        "https://feeds.feedburner.com/hespress/fcOoEW4V9pN",  # 0.10.169 : relais FeedBurner de l'auteur
        "https://www.tsa-algerie.com/category/international/feed/",
        "https://fr.yna.co.kr/RSS/international.xml",
    ],
}
DEMONYMES = "https://raw.githubusercontent.com/mledoze/countries/master/countries.json"  # ODbL ; adjectifs en/fr
CLDR = "https://raw.githubusercontent.com/unicode-org/cldr-json/main/cldr-json/cldr-localenames-full/main/{l}/territories.json"
COMPTES = Path("registre") / "rss-comptes.csv"
VUS = Path("registre") / "rss-vus.txt"
TITRES = Path("registre") / "rss-titres.csv"  # 0.10.198 : empreintes de titres (jamais les titres), pour les reprises
SANTE = Path("registre") / "rss-sante.csv"   # 0.10.162 : état de chaque flux (dernier essai, dernier succès, dernier nouvel article)
UA = {"User-Agent": "alphabet-situationnel-bot/1.0 (recherche ; GitHub Othman-Benbrahim)"}


def noms_pays(c: httpx.Client, langues: tuple[str, ...] = ("en", "fr")) -> list[tuple[re.Pattern, str]]:
    """(motif, code ISO) pour les noms des pays dans les langues demandées (codes à deux lettres seulement)."""
    motifs = {}
    for langue in langues:
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


# 0.10.199 : adjectifs de nationalité (« iranienne », « Russian »). Un adjectif porté par plusieurs territoires va au
# seul membre de l'ONU s'il y en a un (« French » → FR, « Indian » → IN), sinon il est écarté (« Congolese »,
# « Dominican »). Expressions trompeuses masquées d'abord (« Latin American », « océan Indien »).
EXCLUSIONS = re.compile(r"(?<![\w-])(latin|south|north|central|native|african|pan|anglo|latino|sud|nord|afro|centre)[ -]?"
                        r"(american|americans|américain|américaine|américains|américaines)(?![\w-])"
                        r"|(?<![\w-])(indian ocean|océan indien|west indian|indian country|french fries|french toast)(?![\w-])", re.I)
ADJECTIFS_HORS = {"islander", "channel islander", "virgin islander"}
CASSE_STRICTE = {"polish", "polishes"}


def adjectifs(c: httpx.Client) -> dict[str, str]:
    """Adjectif (minuscules, singulier et pluriel, masculin et féminin, anglais et français) → code ISO à deux lettres."""
    try:
        d = c.get(DEMONYMES, timeout=60).json()
    except Exception:
        return {}
    porteurs: dict[str, set] = {}
    onu = {x["cca2"] for x in d if x.get("unMember")}
    for x in d:
        for langue in ("eng", "fra"):
            for genre in ("m", "f"):
                a = (((x.get("demonyms") or {}).get(langue) or {}).get(genre) or "").strip().lower()
                if len(a) < 4 or a in ADJECTIFS_HORS:
                    continue
                for forme in {a, a if a.endswith(("s", "x")) else a + "s"}:
                    porteurs.setdefault(forme, set()).add(x["cca2"])
    out = {}
    for a, codes in porteurs.items():
        if len(codes) > 1:
            codes = codes & onu
        if len(codes) == 1:
            out[a] = next(iter(codes))
    return out


def motifs_larges(motifs: list[tuple[re.Pattern, str]], adj: dict[str, str]) -> list[tuple[re.Pattern, str]]:
    """Noms et adjectifs ensemble, du plus long au plus court (le masquage de `detecter` évite les doubles comptes)."""
    tous = [(m.pattern, code, re.I) for m, code in motifs]
    for a, code in adj.items():
        if a in CASSE_STRICTE:          # mot courant en minuscules (« polish » : polir) : seule la majuscule compte
            tous.append((r"(?<![\w-])" + re.escape(a.capitalize()) + r"(?![\w-])", code, 0))
        else:
            tous.append((r"(?<![\w-])" + re.escape(a) + r"(?![\w-])", code, re.I))
    def longueur(motif: str) -> int:
        return len(re.sub(r"\(\?<?[!=][^)]*\)", "", motif).replace("\\", ""))
    return [(re.compile(m, f), code) for m, code, f in sorted(tous, key=lambda t: -longueur(t[0]))]


def detecter_large(texte: str, larges: list[tuple[re.Pattern, str]]) -> set[str]:
    return detecter(EXCLUSIONS.sub(" ", texte), larges)


def detecter(texte: str, motifs: list[tuple[re.Pattern, str]]) -> set[str]:
    """Noms du plus long au plus court ; un nom trouvé est masqué (« South Sudan » ne compte pas aussi « Sudan »)."""
    trouves = set()
    for m, code in motifs:
        if m.search(texte):
            trouves.add(code)
            texte = m.sub(" ", texte)
    return trouves


TITRES_SEULS = {"renseignement", "lettres_fr"}
LARGE_SEUL = {"cyber", "verification", "enquete"}
ALLEMAND = {"verification", "enquete"}   # 0.10.200 : noms allemands (CLDR « de ») en plus, pour ces familles seulement       # 0.10.199 : familles sans historique « noms seuls », comptées d'emblée avec les adjectifs

# 0.10.198 (décision d'auteur du 2026-11-16, 18 h 03, appliquée directement, sans ombre) : contre le blanchiment
# d'information, un article REPRIS (même titre, une fois normalisé) dans un autre flux ou par un autre média ne compte
# qu'une fois : on compte des titres distincts, pas des reprises. Fenêtre de 30 jours. Familles éditoriales seulement :
# les familles « officiel » et « sante » répètent légitimement un même intitulé pour des événements distincts (mise à
# jour d'un avis de voyage, nouveau séisme au même endroit, nouveau bulletin OMS sur le même pays), elles ne sont pas
# dédoublonnées par titre. Un titre de moins de 5 mots n'est pas assez distinctif : il n'est pas dédoublonné.
DEDOUBLONNER = {"presse", "voix_citoyennes", "economie", "renseignement", "lettres_fr", "parlement_ue"}
FENETRE_TITRES, MOTS_MIN = 30, 5


def empreinte_titre(titre: str) -> str | None:
    t = "".join(c for c in unicodedata.normalize("NFD", str(titre or "").lower()) if unicodedata.category(c) != "Mn")
    mots = re.findall(r"[a-z0-9]+", t)
    return hashlib.sha1(" ".join(mots).encode()).hexdigest()[:16] if len(mots) >= MOTS_MIN else None


def reprise(emp: str | None, jour: str, titres: dict[str, str]) -> bool:
    """Vrai si ce titre a déjà été compté à moins de FENETRE_TITRES jours ; sinon l'enregistre et rend Faux."""
    if not emp:
        return False
    d = datetime.fromisoformat(jour).date()
    vu = titres.get(emp)
    if vu and abs((d - datetime.fromisoformat(vu).date()).days) <= FENETRE_TITRES:
        return True
    titres[emp] = jour
    return False
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
        out.append({"jour": jour, "texte": re.sub(r"<[^>]+>", " ", texte), "empreinte": hashlib.sha1(cle.encode()).hexdigest()[:16],
                    "titre": re.sub(r"<[^>]+>", " ", champs.get("title", ""))})
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
    if r.status_code in (401, 403, 406, 415, 429) or (r.status_code == 200 and r.content.lstrip()[:15].lower().startswith((b"<!doctype html", b"<html"))):
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
    titres: dict[str, str] = {}
    if TITRES.exists():
        for x in csv.DictReader(TITRES.open(encoding="utf-8")):
            titres[x["empreinte"]] = x["jour"]
    reprises: dict[str, int] = {}
    aujourdhui = datetime.now(timezone.utc).date().isoformat()
    sante = {x["url"]: x for x in csv.DictReader(SANTE.open(encoding="utf-8"))} if SANTE.exists() else {}
    with httpx.Client(headers=UA, follow_redirects=True, timeout=30) as c:
        motifs = noms_pays(c)
        print(f"{len(motifs)} noms de pays (anglais et français).")
        adj = adjectifs(c)
        larges = motifs_larges(motifs, adj) if adj else []
        motifs_de = noms_pays(c, ("en", "fr", "de"))
        larges_de = motifs_larges(motifs_de, adj) if adj else motifs_de
        print(f"{len(adj)} adjectifs de nationalité" + ("" if adj else " : source indisponible, comptes « _large » non écrits ce jour") + ".")
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
                    if famille in DEDOUBLONNER and reprise(empreinte_titre(a.get("titre")), a["jour"], titres):
                        reprises[famille] = reprises.get(famille, 0) + 1
                        continue
                    pays = detecter(a["texte"], motifs)
                    familles = [famille] + (["notation"] if famille == "economie" and NOTATION.search(a["texte"]) else [])
                    # 0.10.199, en ombre : comptes parallèles « famille_large » (noms ET adjectifs) ; les comptes
                    # historiques (noms seuls) gardent leur définition. La famille cyber ne compte qu'en large.
                    if famille in ALLEMAND:
                        pays_large = detecter_large(a["texte"], larges_de)
                    else:
                        pays_large = detecter_large(a["texte"], larges) if larges else set()
                    if famille in LARGE_SEUL:
                        pays, familles_larges = pays_large, []
                    else:
                        familles_larges = [fa + "_large" for fa in familles] if larges else []
                    for p in pays:
                        for fa in familles:
                            comptes[(p, a["jour"], fa)] = comptes.get((p, a["jour"], fa), 0) + 1
                    for p in pays_large:
                        for fa in familles_larges:
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
    limite = datetime.now(timezone.utc).date().toordinal() - 2 * FENETRE_TITRES
    with TITRES.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["empreinte", "jour"])
        for e, j in sorted(titres.items(), key=lambda t: (t[1], t[0])):
            if datetime.fromisoformat(j).date().toordinal() >= limite:
                w.writerow([e, j])
    actuels = {u for urls in FLUX.values() for u in urls}
    with SANTE.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["url", "famille", "dernier_essai", "statut", "articles", "dernier_succes",
                                          "dernier_nouveau"])
        w.writeheader()
        for u in sorted(actuels & set(sante)):
            w.writerow({k: sante[u].get(k, "") for k in w.fieldnames})
    rapport = bilan_sante([sante[u] for u in sorted(actuels & set(sante))], aujourdhui)
    rapport += ("\n\nReprises écartées (même titre déjà compté à moins de 30 jours) : "
                + (", ".join(f"{k} {v}" for k, v in sorted(reprises.items())) or "aucune") + ".")
    print(rapport)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
            f.write(rapport + "\n")
    print(f"{nouveaux} nouveaux articles comptés ; {len(comptes)} cases pays × jour × famille.")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
