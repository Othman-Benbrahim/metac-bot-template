"""Nature de chaque série chiffrée des fiches : stock, flux, potentiel, gradient ou phase (bot 0.10.359, brouillon).

Décision de l'auteur du 2026-11-19 (18 h 16) : repartir des bases. Un flux est une quantité qui traverse une frontière,
rapportée au temps ; un stock, ce qui s'accumule de part et d'autre (variation du stock = entrées − sorties) ; un
gradient, la différence de potentiel qui fait couler le flux. On classe ici chaque trace branchée (adaptateur), sans
aucun récit causal, et on la place sur les quatre axes (espace, temps, vitesse, taille) du compartiment qu'elle mesure,
c'est-à-dire la frontière qu'elle concerne.

Cinq natures (les deux dernières s'imposent à l'usage, à valider par l'auteur) :
- stock : quantité présente à un instant ;
- flux : quantité qui passe par unité de temps (comptes par jour ou par semaine, débits, taux de variation) ;
- potentiel : niveau d'où naissent les gradients (prix, taux, température brute) ;
- gradient : écart entre deux potentiels, dans l'espace ou dans le temps (anomalie par rapport à la normale) ;
- phase : position dans un calendrier (compte à rebours), ni stock ni flux.
Décisions de l'auteur (2026-11-19, 18 h 23) : une note de qualité d'un échange n'est pas une mesure (dyade: écarté,
remplacé par le nombre de gestes) ; un sondage est une « déclaration » qui dépend de l'échantillon, du contexte et de
l'émetteur du questionnaire ; les sorties de modèles (GFS, ConflictForecast) sont des mesures. 18 h 32 : une déclaration
n'est pas jetée ; elle renseigne sur son ÉMETTEUR (épiphénomène, intention, communication trompeuse), États compris.

Sortie : registre/nature-des-series.csv ; résumé à l'écran.
"""
from __future__ import annotations

import csv
import sys
from collections import Counter
from pathlib import Path

import ecosystemes as ec

SORTIE = Path("registre") / "nature-des-series.csv"

# type d'adaptateur → (nature, raison)
PAR_TYPE = {
    "portwatch": ("flux", "navires qui traversent le détroit par jour"),
    "port": ("flux", "escales par jour (entrées dans le port)"),
    "avions": ("flux", "appareils observés par jour"),
    "urgences": ("flux", "appareils affichant un code d'urgence par jour"),
    "feux": ("flux", "foyers détectés par jour"),
    "sanctions": ("flux", "désignations nouvelles par jour"),
    "sanctions_chine": ("flux", "mesures nouvelles par jour"),
    "seismes": ("flux", "séismes par jour (énergie libérée par la croûte)"),
    "manifestations": ("flux", "événements par jour"),
    "hostilites": ("flux", "actes par jour"),
    "violations": ("flux", "incidents par jour"),
    "ucdp": ("flux", "événements par jour"),
    "pluie": ("gradient", "pluie des 30 derniers jours en % de la normale (écart à la normale dans le temps)"),
    "ucdp_mois": ("flux", "morts par mois (UCDP, tous types de violence organisée)"),
    "voisins": ("flux", "événements par jour chez les voisins (traversée de la frontière régionale)"),
    "paire": ("flux", "gestes de A envers B par jour (flux orienté)"),
    "paire_mois": ("flux", "événements par mois entre deux pays"),
    "federal_register": ("flux", "actes publiés par jour"),
    "tfr": ("flux", "interdictions de survol émises par jour"),
    "routines": ("flux", "publications officielles par jour"),
    "congres": ("flux", "actes du Congrès par jour"),
    "tribunaux": ("flux", "décisions par jour"),
    "certificats": ("flux", "certificats émis par jour"),
    "epoch": ("flux", "modèles publiés par mois"),
    "rss_matiere": ("flux", "articles par jour qui nomment le sujet"),
    "rss_villes": ("flux", "articles nouveaux par jour citant un pays par son nom, son adjectif ou une de ses villes (en ombre)"),
    "rss_famille": ("flux", "articles nouveaux par jour de la famille de flux"),
    "owid": ("stock", "graphique d’Our World in Data (série annuelle ou datée, selon le graphique)"),
    "confiance_actualite": ("stock", "confiance dans l’actualité par pays (Reuters Institute, Digital News Report)"),
    "ages_dirigeants": ("stock", "âge des dirigeants en poste au 1er juillet, par région (Archigos 4.1, 1946-2015)"),
    "wdi": ("stock", "indicateur annuel de la Banque mondiale (part de la population par âge, ou indicateur d’un pays)"),
    "fts": ("gradient", "part des besoins humanitaires financés dans l'année (%)"),
    "elo": ("stock", "note de force Elo à la fin du mois (ou dispersion, ou variation, des meilleurs)"),
    "publications_nbs": ("flux", "publications parues par jour"),
    "rss": ("flux", "articles par jour (information : flux qui ne se conserve pas)"),
    "rss_region": ("flux", "articles par jour (information)"),
    "telegram": ("flux", "messages par jour (information)"),
    "recit_russe": ("flux", "récits par jour (information)"),
    "openmeasures": ("flux", "messages par jour (information)"),
    "wikipedia": ("flux", "pages vues par jour (attention : information reçue)"),
    "webamon": ("flux", "domaines ou analyses par jour"),
    "ooni": ("flux", "mesures de censure par jour"),
    "radar": ("stock", "coupures d'internet EN COURS à chaque date"),
    "acaps": ("stock", "crises ouvertes à chaque date"),
    "acaps_risques": ("stock", "risques ouverts à chaque date (cumul)"),
    "meteo": ("gradient", "écart de température à la normale (gradient dans le temps)"),
    "climat": ("gradient", "écart glissant sur 365 jours à la normale"),
    "elections": ("phase", "jours avant la prochaine élection"),
    "memoire": ("phase", "jours avant la prochaine date de mémoire"),
    "feries_chine": ("phase", "jours avant le prochain férié"),
    "calendrier_nbs": ("phase", "jours avant la prochaine publication prévue"),
    "gestes": ("flux", "gestes de A envers B par semaine (compte, sans note de qualité)"),
    "dyade": ("déclaration", "note de qualité d'un échange (Goldstein) : ne mesure pas la relation entre A et B, mais la façon "
                             "dont les médias la racontent (émetteur : codage GDELT des récits) ; à lire en écart avec le compte "
                             "des gestes (auteur, 2026-11-19, 18 h 32)"),
    "meteo_prevue": ("gradient", "écart à la normale annoncé par le modèle GFS (mesure d'un modèle)"),
    "conflictforecast": ("potentiel", "niveau de risque publié par le modèle ConflictForecast (mesure d'un modèle)"),
    "nowcast": ("flux", "variation mensuelle des prix prévue (taux de variation)"),
    "prix_alimentaires": ("flux", "inflation alimentaire mensuelle (taux de variation d'un potentiel)"),
}
# séries dont la nature dépend de la série elle-même
PAR_SERIE = {
    "fred:DCOILBRENTEU": ("potentiel", "prix"), "fred:DCOILWTICO": ("potentiel", "prix"), "fred:DHHNGSP": ("potentiel", "prix"),
    "fred:CBBTCUSD": ("potentiel", "prix"), "fred:CBETHUSD": ("potentiel", "prix"), "fred:DFF": ("potentiel", "taux"), "fred:DFEDTARU": ("potentiel", "taux"), "fred:DGS10": ("potentiel", "taux"),
    "fred:ECBDFR": ("potentiel", "taux"), "fred:DTWEXBGS": ("potentiel", "valeur du dollar"),
    "fred:T10YIE": ("gradient", "écart entre taux nominal et taux indexé (inflation anticipée)"),
    "fred:VIXCLS": ("potentiel", "prix du risque (volatilité implicite)"),
    "fred:UNRATE": ("stock", "chômeurs présents, en part de la population active"),
    "fred:UMCSENT": ("déclaration", "réponses à un questionnaire (Université du Michigan) : mesure l'acte de déclarer sous ce "
                                    "questionnaire, cet échantillon et cet émetteur, pas la confiance elle-même ; à lire aussi "
                                    "comme conséquence (le chômage la précède, r = −0,37 mesuré)"),
    "fred:CPIAUCSL:var12": ("flux", "inflation : taux de variation du niveau des prix"),
    "fred:CES0500000003:var12": ("flux", "taux de variation des salaires"),
    "fred:PFOODINDEXM:var12": ("flux", "taux de variation des prix alimentaires mondiaux"),
    "fred:DPSACBW027SBOG:var52": ("flux", "variation sur un an des dépôts (entrées − sorties)"),
    "eia:WCESTUS1:var52": ("flux", "variation sur un an des stocks de brut"),
    "eia:WCSSTUS1": ("stock", "réserve stratégique de brut"), "eia:WCRFPUS2": ("flux", "production de brut par jour"),
    "eia:WRPUPUS2": ("flux", "produits livrés par jour (demande)"),
    "ouvert:attention_complot": ("flux", "pages vues par jour (information reçue)"),
    "ouvert:attention_crise": ("flux", "pages vues par jour (information reçue)"),
    "ouvert:co2_mauna_loa:var12": ("flux", "variation sur un an de la concentration (entrées nettes dans l'atmosphère)"),
    "ouvert:polarisation_chambre": ("gradient", "écart idéologique entre les deux partis"),
    "pub:banquise_arctique": ("stock", "surface de glace présente"),
    "pub:taches_solaires": ("stock", "taches présentes sur le disque"),
    "pub:geomag_ap": ("flux", "perturbation du champ par le vent solaire (énergie reçue), par jour"),
    "pub:nino34_anomalie": ("gradient", "écart de température de la mer à la normale"),
    "pub:rhin_kaub_cm": ("stock", "hauteur d'eau présente"),
    "pub:mississippi_saint_louis": ("flux", "débit (m³ par seconde)"),
    "pub:secheresse_us_d2plus": ("stock", "surface en sécheresse présente"),
    "pub:psd_ble_stocks": ("stock", "stocks prévus en fin de campagne"),
    "pub:psd_mais_production": ("flux", "production prévue par campagne"),
    "pub:arxiv_cs_lg": ("flux", "prépublications par jour"),
}


def nature(adaptateur: str) -> tuple[str, str]:
    if adaptateur in PAR_SERIE:
        return PAR_SERIE[adaptateur]
    if ":proche" in adaptateur:
        return ("phase", "fenêtre de proximité d'une échéance")
    return PAR_TYPE.get(adaptateur.split(":")[0], ("non classé", "type d'adaptateur inconnu de la table"))


def principal() -> int:
    fiches = ec.charger(ec.DOSSIER)
    lignes = []
    for nom, f in sorted(fiches.items()):
        for c in f.get("compartiments", []):
            niv = c.get("niveau") or {}
            for t in c.get("traces") or []:
                if isinstance(t, dict) and t.get("adaptateur"):
                    n, r = nature(t["adaptateur"])
                    lignes.append({"fiche": nom, "compartiment": c["id"], "adaptateur": t["adaptateur"], "nature": n,
                                   "raison": r, "espace": niv.get("espace", ""), "temps": niv.get("temps", ""),
                                   "vitesse": niv.get("vitesse", ""), "taille": niv.get("taille", ""),
                                   "source": t.get("source", "")})
    SORTIE.parent.mkdir(parents=True, exist_ok=True)
    with SORTIE.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(lignes[0]))
        w.writeheader()
        w.writerows(lignes)
    cpt = Counter(l["nature"] for l in lignes)
    print(f"{len(lignes)} traces branchées : " + ", ".join(f"{k} {v}" for k, v in cpt.most_common()))
    for l in lignes:
        if l["nature"] in ("à trancher", "non classé"):
            print(f"  {l['nature']} : {l['fiche']}:{l['compartiment']} {l['adaptateur']} — {l['raison']}")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
