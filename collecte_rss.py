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
- parlement_ue_presse (0.10.357, en ombre) : communiqués et agenda de la semaine du Parlement européen ;
- conseil_ue (0.10.356, en ombre) : communiqués du Conseil de l'UE (sanctions, accords, conclusions) ;
- cyber (0.10.199, en ombre) : CERT-FR (ANSSI) ; rapports « Menaces et incidents » qui nomment un attaquant ou un pays ;
- verification et enquete (0.10.200, en ombre) : Correctiv, vérifications de faits (pression de désinformation) et
  enquêtes ; noms de pays allemands en plus, pour ces deux familles seulement ;
- monnaie, religion, biodiversite, defense, sante_afrique, crime, genre (0.10.455, en ombre, hors du total « tout ») : BCE,
  Fed ; Saint-Siège ; Mongabay ; Defense One ; OMS Afrique ; InSight Crime, OCCRP ; ONU Femmes. robots.txt vérifié pour
  chaque flux à chaque passage (politesse.autorise) : un refus est noté « refuse_robots » dans rss-sante.csv, jamais forcé ;
- presse : presse francophone internationale retenue dans l'atlas atlasflux.saynete.com (un titre par groupe, regards
  France, Suisse, Canada, Afrique, Asie ; presse régionale qui reprend les mêmes dépêches écartée).
Pays reconnus par leurs noms anglais ET français (Unicode CLDR), ramenés au code ISO à deux lettres. 0.10.199, en ombre :
comptes parallèles « famille_large » qui reconnaissent aussi les adjectifs de nationalité (mledoze/countries, ODbL) ;
les comptes historiques gardent leur définition (noms seuls).
- comptes par MATIÈRE stratégique (0.10.388) dans registre/rss-matieres.csv (matière, jour, famille, articles), sur la
  famille « economie » ; S&P Global Energy retirée en 0.10.390 (le site refuse les serveurs de GitHub, code 403).
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

import politesse

import dico_grasland as dg
import dico_newsmap as dn

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
    # 0.10.356 (décision d'auteur du 2026-11-19, 16 h 15, en ombre) : là où l'UE décide (sanctions, accords, conclusions).
    # Famille séparée : « parlement_ue » est lue par le bot, celle-ci ne l'est pas (rien de neuf côté Metaculus).
    "conseil_ue": ["https://www.consilium.europa.eu/en/rss/pressreleases.ashx"],   # Conseil de l'UE : communiqués
    # 0.10.388 → 0.10.390 : S&P Global Energy (14 flux) retirée : le site répond 403 aux serveurs de GitHub (run
    # 44749464241) ; on ne contourne pas un refus. Les comptes par matière restent tenus sur la famille « economie ».
    # 0.10.393 (décision d'auteur du 2026-11-20, 15 h 05) : presse spécialisée mines et énergie, 8 flux vérifiés lisibles
    # DEPUIS GitHub (run 44750437386 ; MINING.COM 403 et Global Mining Review 404 écartés) ; en ombre, non lue par le bot.
    "matieres_presse": [
        "https://www.miningweekly.com/page/latest-news/feed",     # Mining Weekly (reprend aussi Reuters)
        "https://www.mining-technology.com/feed/",                # Mining Technology
        "https://www.northernminer.com/feed/",                    # The Northern Miner
        "https://im-mining.com/feed/",                            # International Mining
        "https://www.e-mj.com/feed/",                             # Engineering & Mining Journal
        "https://www.canadianminingjournal.com/feed/",            # Canadian Mining Journal
        "https://oilprice.com/rss/main",                          # OilPrice.com
        "https://www.rigzone.com/news/rss/rigzone_latest.aspx",   # Rigzone
    ],
    # 0.10.357 : Parlement européen, communiqués de presse et agenda de la semaine (relais FeedBurner créés par l'auteur le
    # 2026-11-19) ; famille séparée de « parlement_ue » (lue par le bot), en ombre.
    "parlement_ue_presse": [
        "https://feeds.feedburner.com/europa/EBIBFevXeKy",  # doc/press-releases  # communiqués de presse
        "https://feeds.feedburner.com/europa/RSA20gHbg5F",  # doc/agendas-news    # agenda de la semaine
    ],
    # 0.10.199 (décision d'auteur du 2026-11-16, 18 h 28, en ombre) : CERT-FR (ANSSI). Les avis et alertes portent sur
    # des produits ; ce qui compte ici, ce sont les rapports « Menaces et incidents » qui nomment un attaquant ou un pays
    # (acte public d'une agence d'État). Pays reconnus par noms ET adjectifs (« iranienne »).
    # 2026-11-21 : « https://cert.cyber.gouv.fr/flux-rss/ » renvoyait une page HTML depuis le début (rss-sante.csv :
    # jamais un succès) ; flux réel du CERT-FR :
    "cyber": ["https://www.cert.ssi.gouv.fr/feed/"],
    # 0.10.200 (décision d'auteur du 2026-11-16, 18 h 37, en ombre) : Correctiv (rédaction d'enquête allemande).
    # « verification » (Faktencheck : pression de désinformation) est lue AVANT « enquete » (flux général) : un
    # article présent dans les deux flux garde le même identifiant et n'est compté qu'une fois, en vérification.
    "verification": ["https://correctiv.org/thema/faktencheck/feed/"],
    "enquete": ["https://correctiv.org/feed/"],
    # 0.10.455 (décision d'auteur du 2026-11-22, 10 h 13 : « tout ce qu'on peut brancher », inventaire du jour) : familles
    # nouvelles, EN OMBRE, pour les compartiments sans trace ; exclues du total « tout » (adaptateurs_sources_b.HORS_TOUT).
    "monnaie": ["https://www.ecb.europa.eu/rss/press.html",              # BCE : communiqués, discours, entretiens
                "https://www.federalreserve.gov/feeds/press_all.xml"],   # Réserve fédérale : tous les communiqués
    "religion": ["https://rss.vatican.va/xml/rss_en.xml",                 # Saint-Siège (vatican.va)
                 "https://press.vatican.va/content/salastampa/en/bollettino.feedrss.xml"],  # bulletin du Bureau de presse
    "biodiversite": ["https://news.mongabay.com/feed/"],                 # Mongabay (presse environnementale indépendante)
    "defense": ["https://www.defenseone.com/rss/all/"],                  # Defense One
    "sante_afrique": ["https://www.afro.who.int/rss/featured-news.xml",   # OMS Afrique : communiqués (droit d'auteur OMS)
                      "https://www.afro.who.int/rss/emergencies.xml"],    # OMS Afrique : urgences et épidémies
    "crime": ["https://www.insightcrime.org/feed/",                       # InSight Crime (crime organisé, Amériques)
              "https://www.occrp.org/en/feed"],                           # OCCRP (enquêtes : corruption, blanchiment)
    "genre": ["https://www.unwomen.org/en/rss-feeds/news"],               # ONU Femmes : actualités
    # 0.10.456 (décision d'auteur du 2026-11-22, 11 h 27 : second inventaire, fiches sans source) : en ombre, hors « tout »
    "psyche": ["https://www.sciencedaily.com/rss/mind_brain/psychology.xml",     # ScienceDaily : psychologie
               "https://www.sciencedaily.com/rss/mind_brain/psychiatry.xml"],    # ScienceDaily : psychiatrie
    "asie": ["https://www.dawn.com/feeds/pakistan/",                             # Dawn (Pakistan)
             "https://thediplomat.com/feed/",                                    # The Diplomat (Asie-Pacifique)
             "https://www.korea.net/koreanet/rss/news/2"],                       # Korea.net (portail officiel sud-coréen)
    "transport": ["https://www.railnews.co.uk/rss/news/",                        # Rail News (Royaume-Uni)
                  "https://simpleflying.com/feed"],                              # Simple Flying (aviation)
    "tech": ["https://restofworld.org/feed/latest"],                             # Rest of World (tech hors Occident)
    "minerais": ["https://www.mining.com/feed/"],                                # MINING.COM
    "inegalites": ["https://feeds.feedburner.com/Inequalityorg"],                # Inequality.org
    # 2026-11-25 (fiche « surveillance et espionnage », demande de l'auteur à 7 h 15 : « complète-le maintenant ») : en
    # ombre, hors « tout » ; comptes seulement. Flux absents ou refusés notés dans rss-sante.csv, jamais forcés.
    "surveillance": ["https://citizenlab.ca/feed/",                                # Citizen Lab (Université de Toronto)
                     "https://www.eff.org/rss/updates.xml",                        # Electronic Frontier Foundation
                     "https://therecord.media/feed",                               # The Record (Recorded Future News)
                     "https://blog.google/threat-analysis-group/rss/",             # Google Threat Analysis Group
                     "https://www.cisa.gov/cybersecurity-advisories/all.xml"],     # CISA : avis (dont avis conjoints)
    "analyse": ["https://www.atlanticcouncil.org/feed"],                         # Atlantic Council (dont DFRLab)
    "geopolitique_europe": ["https://legrandcontinent.eu/fr/feed/"],            # Le Grand Continent (revue géopolitique européenne), source ajoutée par l'auteur le 2026-11-25
    # 2026-11-25, 13 h 09 (sources validées par l'auteur) : regards régionaux pour diversifier les briefs ; en ombre.
    "moyen_orient": ["https://www.aljazeera.com/xml/rss/all.xml",                # Al Jazeera (Qatar)
                     "https://www.middleeasteye.net/rss",                         # Middle East Eye (Londres, indépendant)
                     "https://orientxxi.info/?page=backend&lang=fr"],             # Orient XXI (analyse, français)
    # 2026-11-26 (source validée par l'auteur le 2026-11-24, 14 h 35 : « notes de version des laboratoires ») : annonces
    # officielles des laboratoires d'IA, pour les questions de sortie de modèles ; en ombre, hors « tout » ; titres,
    # liens et dates seulement. Anthropic, Meta, xAI et Mistral ne publient pas de flux : non forcés.
    "laboratoires_ia": ["https://openai.com/news/rss.xml",                       # OpenAI : actualités et sorties
                        "https://deepmind.google/blog/rss.xml",                  # Google DeepMind : blog
                        "https://blog.google/technology/ai/rss/",                # Google : IA (annonces Gemini)
                        "https://huggingface.co/blog/feed.xml"],                 # Hugging Face : blog (modèles ouverts)
    "chine": ["https://www.scmp.com/rss/91/feed",                                 # South China Morning Post : Chine
              "https://chinamediaproject.org/feed/"],                             # China Media Project (discours officiel)
    "russie": ["https://meduza.io/rss/en/all",                                    # Meduza (indépendant, en exil)
               "https://www.themoscowtimes.com/rss/news"],                        # The Moscow Times (indépendant, en exil)
    "amerique_latine": ["https://en.mercopress.com/rss/",                         # MercoPress (cône Sud)
                        "https://www.americasquarterly.org/feed/",                # Americas Quarterly
                        "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/internacional/portada"],  # El País, international
    "inde": ["https://www.thehindu.com/news/international/feeder/default.rss"],   # The Hindu : international
    # voix d'État, étiquetées comme telles dans les briefs (Xinhua n'a pas de flux : China Daily, quotidien d'État)
    "voix_etat": ["https://tass.com/rss/v2.xml",                                  # TASS (agence d'État russe)
                  "https://www.chinadaily.com.cn/rss/world_rss.xml"],             # China Daily (quotidien d'État chinois)
    "afrique": ["https://fr.allafrica.com/tools/headlines/rdf/westafrica/headlines.rdf"],  # AllAfrica, Afrique de l'Ouest
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
VILLES_CSV = Path("registre") / "rss-villes.csv"  # 2026-11-25 : pays par noms, adjectifs ET villes (GeoNames), en ombre
REGIONS = Path("registre") / "rss-regions.csv"   # 0.10.219 : macro-régions (dictionnaire Grasland-Toureille), en ombre
ACCORD = Path("registre") / "rss-accord.csv"     # 0.10.219 : accord entre nos pays et ceux du second codeur
TROIS = Path("registre") / "rss-trois-codeurs.csv"  # 0.10.221 : profils de réponse des trois codeurs (Newsmap en 3e)
N_PAYS = 250                                     # univers des codes pays, pour le profil « 000 » du modèle latent
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
# 0.10.220 : sigles en majuscules, casse stricte (« US inflation », « U.S. strikes », « l'EAU », « la RDC »). Angle mort
# révélé par le second codeur au premier passage (32 mentions des États-Unis vues par lui seul) ; « usa », « rdc » et
# « drc » figuraient déjà dans `noms_pays` mais étaient écartés par le filtre des noms de moins de quatre lettres.
SIGLES = {"US": "US", "U.S.": "US", "U.S.A.": "US", "USA": "US", "UK": "GB", "U.K.": "GB", "UAE": "AE", "EAU": "AE",
          "RDC": "CD", "DRC": "CD", "RCA": "CF"}


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
    for sigle, code in SIGLES.items():
        tous.append((r"(?<![\w.-])" + re.escape(sigle) + r"(?!\w)", code, 0))   # « U.S.-China » compte
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
# 0.10.388 : matières stratégiques reconnues dans les titres et résumés (comptes matière × jour × famille, jamais le texte)
MATIERES = {m: re.compile(rx, re.I) for m, rx in {
    "graphite": r"\bgraphite", "lithium": r"\blithium", "nickel": r"\bnickel", "cobalt": r"\bcobalt",
    "cuivre": r"\bcopper", "terres_rares": r"rare earth|\brees?\b", "uranium": r"\buranium", "aluminium": r"\balumin",
    "acier": r"\bsteel\b", "minerai_fer": r"iron ore", "petrole": r"\b(crude|oil|brent|wti)\b", "gaz": r"natural gas|\blng\b",
    "charbon": r"\bcoal\b", "electricite": r"\bpower prices?|electricity", "engrais": r"fertili[sz]er|\burea\b|potash|ammonia",
    "ble": r"\bwheat", "mais": r"\bcorn\b|\bmaize", "soja": r"\bsoy", "fret_maritime": r"freight|tanker|container|shipping",
    "carbone": r"carbon (market|price|credit)|emissions trading|\bets\b", "hydrogene": r"hydrogen",
    # 2026-11-25 : sujets de la fiche « surveillance et espionnage » (titres et résumés ; comptes seulement)
    "spyware": r"spyware|stalkerware|\bpegasus\b|\bpredator\b|\bparagon\b|\bnso group|intellexa|candiru|zero-click",
    "espionnage": r"espionage|\bspying\b|\bspies\b|cyber-?espionage|salt typhoon|volt typhoon|\bAPT ?\d+",
    "interceptions": r"\bfisa\b|section 702|wiretap|lawful interception|bulk collection|mass surveillance",
    "biometrie": r"facial recognition|face recognition|biometric",
    "courtiers": r"data brokers?|location data",
    "cibles": r"(journalist|activist|dissident|lawmaker|opposition|human rights defender)\w*\W+(?:\w+\W+){0,8}?(spyware|hack\w*|surveil\w*|target\w*)"
              r"|(spyware|surveil\w*)\W+(?:\w+\W+){0,8}?(journalist|activist|dissident|lawmaker)",
    "chiffrement": r"end-to-end encrypt|encryption backdoor|threat notification"}.items()}
FAMILLES_MATIERES = {"geopolitique_europe", "economie", "matieres_presse", "surveillance", "cyber", "renseignement", "tech", "defense"}
MATIERES_CSV = Path("registre") / "rss-matieres.csv"
# 0.10.457 (décision de l'auteur, 2026-11-22, 11 h 36) : articles nouveaux par famille et par jour, avec ou sans pays
# reconnu, pour la carte des écosystèmes (lecteur-local) ; compte seulement, jamais le texte
FAMILLES_CSV = Path("registre") / "rss-familles.csv"
FAMILLES_VUS = Path("registre") / "rss-familles-vus.txt"   # 0.10.458 : empreintes déjà comptées dans rss-familles.csv

DEDOUBLONNER = {"surveillance", "crime", "defense", "biodiversite", "asie", "transport", "tech", "minerais", "inegalites", "analyse", "afrique", "presse", "voix_citoyennes", "economie", "renseignement", "lettres_fr", "parlement_ue", "conseil_ue", "parlement_ue_presse", "sp_energie", "matieres_presse"}
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
    refuses = [x for x in lignes if x.get("statut") == "refuse_robots"]   # 0.10.455
    ok = len(lignes) - len(erreurs) - len(vides) - len(muets) - len(refuses)
    out = [f"## Santé des flux RSS ({aujourdhui})", "",
           f"{len(lignes)} flux : {ok} en bon état, {len(erreurs)} en erreur, {len(vides)} vides, "
           f"{len(muets)} sans nouvel article depuis {silence} jours ou plus, {len(refuses)} refusés par robots.txt.", ""]
    for titre, groupe, champ in (("En erreur", erreurs, "statut"), ("Refusés par robots.txt", refuses, "dernier_succes"),
                                 ("Vides", vides, "dernier_succes"),
                                 (f"Muets ({silence} j et plus)", muets, "dernier_nouveau")):
        if groupe:
            out += [f"### {titre}", "", "| famille | flux | détail |", "|---|---|---|"]
            out += [f"| {x.get('famille', '')} | {x['url']} | {champ} : {x.get(champ) or 'jamais'} |" for x in groupe]
            out.append("")
    return "\n".join(out)


def bilan_accord(accord: dict, ecarts_nous: dict, ecarts_eux: dict) -> str:
    """0.10.219 : accord cumulé entre notre détection (noms et gentilés) et le second codeur (Grasland-Toureille)."""
    if not accord:
        return "Second codeur (Grasland-Toureille) : aucun compte."
    c, n, e = (sum(v[i] for v in accord.values()) for i in range(3))
    tot = c + n + e
    top = lambda d: ", ".join(f"{k} {v}" for k, v in sorted(d.items(), key=lambda t: -t[1])[:8]) or "aucun"
    return (f"## Second codeur (Grasland-Toureille, en ombre)\n\nCumul : {c} mentions communes, {n} vues par nous seuls, "
            f"{e} par eux seuls (accord {c / tot:.0%}).\nCe passage, pays vus par nous seuls : {top(ecarts_nous)} ; "
            f"par eux seuls : {top(ecarts_eux)}.")


def bilan_trois(trois: dict) -> str:
    """0.10.221 : modèle à classe latente sur les profils cumulés des trois codeurs (tous pays confondus)."""
    prof: dict[str, int] = {}
    articles = 0
    for (p, _, pr), n in trois.items():
        if p == "_articles":
            articles += n
        else:
            prof[pr] = prof.get(pr, 0) + n
    vus = sum(prof.values())
    if vus < 200:
        return f"Trois codeurs (nous, Grasland-Toureille, Newsmap) : {vus} mention(s) cumulée(s), trop peu pour le modèle latent (200)."
    prof["000"] = max(0, articles * N_PAYS - vus)
    r = dn.classe_latente(prof)
    l = [f"## Trois codeurs, modèle à classe latente (en ombre, erreurs supposées indépendantes : indicatif)", "",
         f"{vus} mentions cumulées sur {articles} articles. Profils (nous, Grasland, Newsmap) : "
         + ", ".join(f"{k} {v}" for k, v in sorted(prof.items()) if k != "000") + "."]
    for nom in ("nous", "grasland", "newsmap"):
        v = r[nom]
        l.append(f"- {nom} : sensibilité {v['sensibilite']:.0%}, fausses alertes {1 - v['specificite']:.3%} des cases.")
    return "\n".join(l)


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
    villes_c: dict[tuple, int] = {}
    entites_c: dict[tuple, int] = {}   # 2026-11-26 : veille anticipée (anticipation.py)
    if VILLES_CSV.exists():
        for x in csv.DictReader(VILLES_CSV.open(encoding="utf-8")):
            villes_c[(x["pays"], x["jour"], x["famille"])] = int(x["articles"])
    import anticipation
    import villes_pays
    regions: dict[tuple, int] = {}
    if REGIONS.exists():
        for x in csv.DictReader(REGIONS.open(encoding="utf-8")):
            regions[(x["region"], x["jour"], x["famille"])] = int(x["articles"])
    accord: dict[tuple, list] = {}
    if ACCORD.exists():
        for x in csv.DictReader(ACCORD.open(encoding="utf-8")):
            accord[(x["pays"], x["jour"])] = [int(x["commun"]), int(x["nous_seul"]), int(x["eux_seul"])]
    trois: dict[tuple, int] = {}
    if TROIS.exists():
        for x in csv.DictReader(TROIS.open(encoding="utf-8")):
            trois[(x["pays"], x["jour"], x["profil"])] = int(x["n"])
    ecarts_nous: dict[str, int] = {}
    ecarts_eux: dict[str, int] = {}
    aujourdhui = datetime.now(timezone.utc).date().isoformat()
    sante = {x["url"]: x for x in csv.DictReader(SANTE.open(encoding="utf-8"))} if SANTE.exists() else {}
    matieres: dict[tuple, int] = {}
    if MATIERES_CSV.exists():
        for x in csv.DictReader(MATIERES_CSV.open(encoding="utf-8")):
            matieres[(x["matiere"], x["jour"], x["famille"])] = int(x["articles"])
    par_famille: dict[tuple, int] = {}
    vus_familles = set(FAMILLES_VUS.read_text(encoding="utf-8").split()) if FAMILLES_VUS.exists() else set()
    if FAMILLES_CSV.exists():
        for x in csv.DictReader(FAMILLES_CSV.open(encoding="utf-8")):
            par_famille[(x["famille"], x["jour"])] = int(x["articles"])
    with httpx.Client(headers=UA, follow_redirects=True, timeout=30) as c:
        motifs = noms_pays(c)
        print(f"{len(motifs)} noms de pays (anglais et français).")
        adj = adjectifs(c)
        larges = motifs_larges(motifs, adj) if adj else []
        motifs_de = noms_pays(c, ("en", "fr", "de"))
        larges_de = motifs_larges(motifs_de, adj) if adj else motifs_de
        print(f"{len(adj)} adjectifs de nationalité" + ("" if adj else " : source indisponible, comptes « _large » non écrits ce jour") + ".")
        # 0.10.219 (en ombre) : second codeur, dictionnaire de Grasland et Toureille (capitales, chefs d'État, macro-régions)
        gr = dg.charger(c, ("en", "fr"))
        gr_de = dg.charger(c, ("en", "fr", "de")) if gr else []
        # 0.10.221 (en ombre) : troisième codeur, dictionnaire de Newsmap (K. Watanabe ; français : C. Grasland)
        nm = dn.charger(c, ("en", "fr")) if gr else []
        nm_de = dn.charger(c, ("en", "fr", "de")) if nm else []
        print(f"{len(nm)} expressions du dictionnaire Newsmap" + ("" if nm else " : source indisponible, profils à trois codeurs non écrits ce jour") + ".")
        print(f"{len(gr)} expressions du dictionnaire Grasland-Toureille" + ("" if gr else " : source indisponible, comptes « _grasland » non écrits ce jour") + ".")
        for famille, urls in FLUX.items():
            for url in urls:
                # 0.10.455 : robots.txt respecté pour chaque flux (politesse.autorise) ; un refus n'est jamais contourné
                if not politesse.autorise(c, url):
                    print(f"  flux refusé par robots.txt : {url[:70]}")
                    st = sante.setdefault(url, {"url": url, "dernier_succes": "", "dernier_nouveau": ""})
                    st.update(famille=famille, dernier_essai=aujourdhui, statut="refuse_robots", articles=0)
                    continue
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
                    # 0.10.458 : compte par famille tenu à part (son propre registre d'empreintes), pour que les articles
                    # déjà lus avant la création du compte soient comptés une fois, à leur date de publication
                    if a["empreinte"] not in vus_familles:
                        vus_familles.add(a["empreinte"])
                        par_famille[(famille, a["jour"])] = par_famille.get((famille, a["jour"]), 0) + 1
                    if a["empreinte"] in vus:
                        continue
                    vus.add(a["empreinte"])
                    if famille in DEDOUBLONNER and reprise(empreinte_titre(a.get("titre")), a["jour"], titres):
                        reprises[famille] = reprises.get(famille, 0) + 1
                        continue
                    pays = detecter(a["texte"], motifs)
                    for n_ in anticipation.noms(a.get("titre") or ""):   # 2026-11-26 : veille anticipée (noms seuls)
                        entites_c[(a["jour"], n_)] = entites_c.get((a["jour"], n_), 0) + 1
                    if famille in FAMILLES_MATIERES:
                        for m, rx in MATIERES.items():
                            if rx.search(a["texte"]):
                                matieres[(m, a["jour"], famille)] = matieres.get((m, a["jour"], famille), 0) + 1
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
                    # 2026-11-25, en ombre : un article qui cite « Kharkiv » ou « Goma » sans nommer le pays compte aussi
                    for p in (pays_large or pays) | villes_pays.pays(a["texte"]):
                        for fa in familles:
                            villes_c[(p, a["jour"], fa)] = villes_c.get((p, a["jour"], fa), 0) + 1
                    for p in pays_large:
                        for fa in familles_larges:
                            comptes[(p, a["jour"], fa)] = comptes.get((p, a["jour"], fa), 0) + 1
                    if gr:
                        pays_gr, regions_gr = dg.detecter(a["texte"], gr_de if famille in ALLEMAND else gr)
                        for p in pays_gr:
                            for fa in familles:
                                comptes[(p, a["jour"], fa + "_grasland")] = comptes.get((p, a["jour"], fa + "_grasland"), 0) + 1
                        # 0.10.220 : compte « fusion » (pays vu par l'un OU l'autre codeur), la capture la plus complète
                        for p in (pays_large if (larges or famille in LARGE_SEUL) else pays) | pays_gr:
                            for fa in familles:
                                comptes[(p, a["jour"], fa + "_fusion")] = comptes.get((p, a["jour"], fa + "_fusion"), 0) + 1
                        nous = pays_large if (larges or famille in LARGE_SEUL) else pays
                        if nm:
                            pays_nm = dn.detecter(a["texte"], nm_de if famille in ALLEMAND else nm)
                            for p in nous | pays_gr | pays_nm:
                                k = (p, a["jour"], f"{int(p in nous)}{int(p in pays_gr)}{int(p in pays_nm)}")
                                trois[k] = trois.get(k, 0) + 1
                            trois[("_articles", a["jour"], "total")] = trois.get(("_articles", a["jour"], "total"), 0) + 1
                        for rg in regions_gr:
                            for fa in familles:
                                regions[(rg, a["jour"], fa)] = regions.get((rg, a["jour"], fa), 0) + 1
                        for p in nous | pays_gr:
                            k = (p, a["jour"])
                            v = accord.setdefault(k, [0, 0, 0])
                            v[0 if (p in nous and p in pays_gr) else 1 if p in nous else 2] += 1
                            if p not in pays_gr:
                                ecarts_nous[p] = ecarts_nous.get(p, 0) + 1
                            elif p not in nous:
                                ecarts_eux[p] = ecarts_eux.get(p, 0) + 1
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
    FAMILLES_VUS.write_text("\n".join(sorted(vus_familles)), encoding="utf-8")
    with FAMILLES_CSV.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["famille", "jour", "articles"])
        for (fa, j), n in sorted(par_famille.items(), key=lambda t: (t[0][1], t[0][0])):
            w.writerow([fa, j, n])
    if matieres:
        with MATIERES_CSV.open("w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["matiere", "jour", "famille", "articles"])
            for (m, j, fa), n in sorted(matieres.items(), key=lambda t: (t[0][1], t[0][0], t[0][2])):
                w.writerow([m, j, fa, n])
    if entites_c:   # 2026-11-26 : veille anticipée ; liste du jour des acteurs qui montent, et mesure
        try:
            anticipation.ecrire_comptes(entites_c)
            anticipation.ecrire_liste(datetime.now(timezone.utc).date().isoformat())
            anticipation.mesurer()
        except Exception as ex:
            print(f"veille anticipée : non écrite ({type(ex).__name__})")
    if villes_c:
        with VILLES_CSV.open("w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["pays", "jour", "famille", "articles"])
            for (p, j, fa), n in sorted(villes_c.items(), key=lambda t: (t[0][1], t[0][0], t[0][2])):
                w.writerow([p, j, fa, n])
    if regions:
        with REGIONS.open("w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["region", "jour", "famille", "articles"])
            for (rg, j, fa), n in sorted(regions.items(), key=lambda t: (t[0][1], t[0][0], t[0][2])):
                w.writerow([rg, j, fa, n])
    if trois:
        with TROIS.open("w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["pays", "jour", "profil", "n"])
            for (p, j, pr), n in sorted(trois.items(), key=lambda t: (t[0][1], t[0][0], t[0][2])):
                w.writerow([p, j, pr, n])
    if accord:
        with ACCORD.open("w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["pays", "jour", "commun", "nous_seul", "eux_seul"])
            for (p, j), v in sorted(accord.items(), key=lambda t: (t[0][1], t[0][0])):
                w.writerow([p, j, *v])
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
    rapport += "\n\n" + bilan_accord(accord, ecarts_nous, ecarts_eux)
    rapport += "\n\n" + bilan_trois(trois)
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
