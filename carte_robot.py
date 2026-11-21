"""Carte de couverture par robot Python (décision de l'auteur du 2026-11-21, 14 h 45 : « dès qu'on peut, on
automatise l'ensemble comme prévu »). Aucun appel de modèle, reproductible à l'identique, gratuit.

Pourquoi : deux passages identiques de la carte v5 (même consigne, même modèle, mêmes questions) ont donné des règles
différentes pour 15 questions sur 119 (29 questions couvertes en commun sur 35) : le jugement du modèle varie. Ici,
chaque règle sourcée a des motifs écrits à la main (dans ce fichier, visibles et figés) : une question n'est rattachée
à une règle que si TOUS les motifs de la règle se trouvent dans son titre (l'événement ET la situation ou l'acteur), et
qu'aucun motif d'exclusion n'y est. Les motifs portent les choix de leur auteur (Claude), mais ces choix sont lisibles
et ne varient pas d'un passage à l'autre.

    python carte_robot.py      # écrit registre/carte-robot-banc-m.json et registre/carte-robot-jugement2026.json
"""
from __future__ import annotations

import collections
import json
import re
import sys
from pathlib import Path

import couverture_regles as cr

US = r"\b(u\.?s\.?|united states|american|america|federal|congress|senate|house|white house|trump|biden|fed|federal reserve)\b"
AUTRES_PAYS = r"\b(philippin\w*|brazil\w*|australi\w*|ital\w*|fran(ce|ch)|canad\w*|mexic\w*|argentin\w*|colombi\w*|chile\w*|india\w*|japan\w*|korea\w*|poland|polish|german\w*|spain|spanish|uk|british|thai\w*|nigeria\w*|kenya\w*)\b"
ELECTION = r"\b(elections?|elected|re-?elect\w*|vote|ballot|referendums?|primary|primaries|runoff|first round|second round)\b"
ETATS_US = r"\b(alabama|alaska|arizona|arkansas|california|colorado|connecticut|delaware|florida|georgia|hawaii|idaho|illinois|indiana|iowa|kansas|kentucky|louisiana|maine|maryland|massachusetts|michigan|minnesota|mississippi|missouri|montana|nebraska|nevada|new hampshire|new jersey|new mexico|new york|north carolina|north dakota|ohio|oklahoma|oregon|pennsylvania|rhode island|south carolina|south dakota|tennessee|texas|utah|vermont|virginia|washington|west virginia|wisconsin|wyoming|[a-z]{2}-\d{1,2})\b"
LOCAL = r"\b(mayor\w*|governor\w*|gubernatorial|municipal|state legislat\w*|state parliament|landtag|provinc\w*|regional|oblast|krai|primary|primaries|city council|scottish parliament|senedd|quebec|ontario|bavaria\w*|saxony|thuringia|brandenburg|mecklenburg\w*|rhineland\w*|baden\w*|hesse|berlin)\b"
TENUE = r"\b(hold|held|postpon\w*|delay\w*|cancel\w*|call\w* (an? )?(snap |early )?elections?|announce\w* (an? )?(\w+ )?elections?|schedul\w*)\b"
ISSUE_ELECTION = r"\b(win\w*|receive|get|vote share|percent|%|majority|supermajority|seats?|first round|runoff|advance|elected|re-?elected|become (the )?(president|prime minister))\b"
EUROPE = r"\b(german\w*|netherlands|dutch|poland|polish|czech\w*|hungar\w*|romania\w*|portug\w*|swed\w*|denmark|danish|norw\w*|finland|finnish|austria\w*|belgi\w*|ital\w*|spain|spanish|greece|greek|bulgaria\w*|croatia\w*|sloven\w*|slovak\w*|latvia\w*|lithuania\w*|estonia\w*|ireland|irish|iceland\w*)\b"

# id -> (motifs qui doivent TOUS être présents, motifs d'exclusion)
MOTIFS: dict[str, tuple[list[str], list[str]]] = {
    "us_president_college": ([r"\bpresident\w*\b", ELECTION, r"\b(u\.?s\.?|united states|american|electoral college)\b"], [AUTRES_PAYS]),
    "us_primaires_systemes_speciaux": ([r"\b(top-two|top-four|jungle primary|ranked[- ]choice)\b"], []),
    "us_erreur_sondages_par_echelle": ([r"\b(u\.?s\.?|united states|american)\b|" + ETATS_US[2:-2], r"\b(race|elections?|seat|primary|primaries|senate|house|governor|gubernatorial)\b", ISSUE_ELECTION], [AUTRES_PAYS, TENUE]),
    "us_erreur_selon_temps_restant": ([r"\b(elections?|referendums?)\b", ISSUE_ELECTION], [TENUE, LOCAL]),
    "us_avantage_sortant_congres": ([r"\b(incumbent|re-?elect\w*)\b", r"\b(senat\w*|house|congress\w*|representative)\b"], [AUTRES_PAYS]),
    "regimes_fermes_contestation": ([r"\b(protest\w*|uprising|revolution|regime change|overthrow\w*|toppl\w*)\b"], []),
    "afrique_limites_de_mandat": ([r"\b(third|fourth) term\b|\bterm limits?\b"], []),
    "sondages_erreur_comparee": ([r"\b(elections?|referendums?)\b", ISSUE_ELECTION], [TENUE, LOCAL]),
    "france_legislatives": ([r"\bfran(ce|ch)\b", r"\b(legislative|national assembly|assembl[ée]e nationale)\b"], []),
    "seuils_parlements_nationaux_europe": ([EUROPE, r"\b(parliament\w*|bundestag|sejm|seats?|threshold|supermajority|national assembly|riksdag|folketing|storting)\b", ELECTION], []),
    "seuils_elections_europeennes": ([r"\beuropean parliament\b", ELECTION], []),
    "ue_majorite_qualifiee": ([r"\b(council of the (eu|european union)|eu council|eu member states|european council)\b", r"\b(adopt\w*|approv\w*|vote\w*|agree\w*)\b"], []),
    "europe_formation_gouvernement": ([r"\b(prime minister|form\w* (a |the )?(new )?government|coalition government|chancellor|taoiseach)\b", r"\b(become|form\w*|be (the )?next|appointed|sworn in|confidence)\b"], [r"\b(resign|out as|cease to be|step down|removed)\b"]),
    "presidentielles_mode_de_scrutin": ([r"\bpresident\w*\b", ELECTION, ISSUE_ELECTION], [r"\b(u\.?s\.?|united states|american)\b", TENUE]),
    "indonesie_presidentielle": ([r"\bindonesia\w*\b", r"\bpresident\w*\b", ELECTION], []),
    "japon_chambre_basse": ([r"\bjapan\w*\b", r"\b(house of representatives|lower house|ldp|diet)\b", ELECTION], []),
    "australie_vote_preferentiel": ([r"\baustralia\w*\b", r"\b(federal election|house of representatives|labor|coalition)\b", ELECTION], []),
    "inde_scrutin_uninominal": ([r"\b(india|lok sabha)\b", r"\b(lok sabha|general election|bjp|congress party)\b"], []),
    "us_senat_cloture": ([r"\bsenate\b", r"\b(pass\w*|confirm\w*|filibuster|cloture|bill|legislation|act)\b"], [AUTRES_PAYS]),
    "onu_conseil_securite_vote": ([r"\bsecurity council\b", r"\b(resolution|adopt\w*|vote\w*|veto\w*|approv\w*)\b"], []),
    "coups_d_etat_frequence": ([r"\bcoups?\b"], [r"\bcoup de\b"]),
    "chefs_d_etat_sortie_irreguliere": ([r"\b(cease to be|out as|remain\w*|still be|leave office|removed|ousted|resign\w*|step down|be in power|lose power|overthrown|deposed)\b", r"\b(president|prime minister|supreme leader|king|chancellor|head of state|leader of)\b"], [r"\b(former|ex-)\b", r"\b(fed|federal reserve)\b"]),
    "second_tour_retournement": ([r"\b(runoff|second round)\b", r"\b(win\w*|winner|elected)\b"], [r"\bprimary\b"]),
    "bresil_gouverneurs_senat": ([r"\bbrazil\w*\b", r"\b(governor|senator|senate)\b", ELECTION], []),
    "us_fed_calendrier": ([r"\b(fed|federal reserve|fomc)\b", r"\b(rates?|cut\w*|hike\w*|raise\w*|lower\w*|basis points|bps|target range)\b"], [r"\b(chair|powell|governor of the)\b"]),
    "us_cour_supreme_calendrier": ([r"\b(supreme court|scotus)\b", r"\b(hear|rule\w*|decision|decide\w*|strike down|uphold\w*|overturn\w*|certiorari|case|hold)\b"], [AUTRES_PAYS, r"\bretire\w*\b"]),
    "us_reconciliation_budgetaire": ([r"\breconciliation\b", r"\b(bill|senate|house|congress|budget)\b"], []),
    "us_lois_de_finances_provisoires": ([r"\b(continuing resolution|government shutdown|shut ?down|appropriations|funding bill)\b"], [AUTRES_PAYS]),
    "us_chambre_sanctions_disciplinaires": ([r"\b(censure\w*|expel\w*|reprimand\w*)\b", r"\bhouse\b"], []),
    "usmca_revision_conjointe": ([r"\b(usmca|cusma|t-mec)\b"], []),
    "effet_d_echeance_negociation": ([r"\b(deal|agreement|accord|treaty|ceasefire|trade pact)\b", r"\b(sign\w*|reach\w*|finali[sz]e\w*|conclude\w*|agree\w*|announce\w*)\b"], [r"\b(renew\w*|extend\w*|extension|withdraw\w*|broken|collapse\w*|violat\w*)\b"]),
    "referendums_retour_statu_quo": ([r"\breferendum\b", r"\b(pass\w*|approv\w*|vote yes|yes|win\w*|succeed\w*)\b"], []),
    "us_confirmations_delais": ([r"\b(confirm\w*|sworn in|nominat\w*)\b", r"\b(senate|sworn in|attorney for|secretary|ambassador|judge|director)\b"], [AUTRES_PAYS]),
    "us_entourage_rotation": ([r"\b(out as|leave\w*|resign\w*|fired|depart\w*|cease to be|no longer|step down|be replaced)\b", r"\b(secretary of|attorney general|chief of staff|national security advis\w*|press secretary|cabinet|white house)\b"], [AUTRES_PAYS]),
    "us_sanctions_frequence": ([r"\bsanction\w*\b", r"\b(u\.?s\.?|united states|treasury|ofac|trump administration|washington)\b"], [r"\b(lift\w*|remove\w*|ease\w*|relief)\b"]),
    "us_inculpation_personnalites": ([r"\b(indict\w*|arrest\w*|charged|charges|prosecut\w*)\b", r"\b(former|rep\.|representative|senator|congress\w*|president|governor|mayor|official|attorney general|director)\b"], [AUTRES_PAYS]),
    "calendriers_annonces_glissent": ([r"\b(be released|be launched|launch(es)?|released?|be (fully )?(repaired|completed|finished|operational)|completion|rollout|roll out|have a service area|go live|begin operations|open to the public)\b"], [r"\b(release[sd]? (from|of) (prison|jail|custody|hostages?)|freed)\b", r"\b(ipo|s-1|attack\w*|strike\w*|offensive|missile\w*)\b", r"\b(report\w*|data|after (its |the )?launch|after (its |the )?release|of its release|market cap|fdv|price|hack\w*|unemployment|figures?|statistics)\b"]),
    "coree_du_nord_essais_nucleaires": ([r"\bnorth korea\w*\b", r"\bnuclear test\w*\b"], []),
    "us_ouragans_atterrissage": ([r"\bhurricane\w*\b", r"\blandfall\b"], []),
    "bolides_frequence": ([r"\b(meteor\w*|bolide\w*|fireball\w*)\b"], []),
    "records_temperature_persistance": ([r"\b(record|warmest|hottest)\b", r"\b(temperature\w*|warmest|hottest|sea surface)\b"], []),
    "coupe_du_monde_vainqueurs_hotes": ([r"\bworld cup\b", r"\b(win\w*|winner|champion\w*|semi-?finals?|quarter-?finals?|final|reach\w*|advance\w*|knockout)\b"], [r"\b(participat\w*|qualif\w*|play against|boycott\w*|host city)\b", r"\b(goals?|scor\w*|cards?|penalt\w*|attend\w*|viewers?)\b"]),
    "anciens_dirigeants_sort": ([r"\b(former|ex-)\b", r"\b(president|prime minister|leader|head of state)\b", r"\b(arrest\w*|indict\w*|jail\w*|prison|exile\w*|charged|convict\w*|sentenced)\b"], []),
    "dow_jones_changements": ([r"\b(dow jones|djia|dow)\b", r"\b(dropped|removed|added|replac\w*|component\w*|join\w*)\b"], []),
    "royaume_uni_niveau_menace": ([r"\bthreat level\b"], []),
    "schengen_controles_interieurs": ([r"\b(schengen|internal border|border control\w*)\b"], []),
    "opep_departs": ([r"\bopec\b", r"\b(quit\w*|leave\w*|exit\w*|withdraw\w*|suspend\w*)\b"], []),
    "royal_mail_hausses_tarifs": ([r"\broyal mail\b"], []),
    "papes_voyages": ([r"\bpope\b", r"\b(visit\w*|travel\w*|trip\w*)\b"], []),
    "sommets_etats_unis_russie": ([r"\b(trump|biden|u\.?s\.? president)\b", r"\bputin\b", r"\b(meet\w*|summit|in person)\b"], []),
}


def rattacher(titre: str, cat: dict) -> list[str]:
    t = titre.lower()
    out = []
    for i, (oui, non) in MOTIFS.items():
        if i not in cat:
            continue
        if all(re.search(m, t) for m in oui) and not any(re.search(m, t) for m in non):
            out.append(i)
    return out


def carte(ensemble: str) -> dict:
    cat = cr.catalogue()
    qs = cr.questions(ensemble)
    detail = [{"question": q, "titre": x["titre"], "issue": x["issue"], "jeu": x.get("jeu"), "regles": rattacher(x["titre"], cat)}
              for q, x in sorted(qs.items())]
    compte = collections.Counter(i for o in detail for i in o["regles"])
    return {"ensemble": ensemble, "regles_au_catalogue": len(cat), "regles_avec_motifs": len([i for i in MOTIFS if i in cat]),
            "questions": len(detail), "couvertes": sum(1 for o in detail if o["regles"]),
            "par_regle": dict(compte.most_common()), "detail": detail}


def principal() -> int:
    for ens in ("banc_m", "jugement2026"):
        r = carte(ens)
        p = Path("registre") / f"carte-robot-{ens.replace('_', '-')}.json"
        p.write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"{ens} : {r['couvertes']} sur {r['questions']} ; par règle : {r['par_regle']}")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
