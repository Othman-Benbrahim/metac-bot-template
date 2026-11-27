"""Familles de situation et porte de compatibilité des briques (0.10.513, 2026-11-27, accord de l'auteur 11 h 35).

Une brique ne s'applique que si l'une des familles de situation de la question (mots du titre, sans modèle) fait partie
de ce qu'elle sait mesurer (COMPATIBLE). Sinon elle se tait (silence « hors_domaine »). Si aucune famille n'est reconnue,
la brique reste permise : la porte ne bloque jamais à l'aveugle. Origine : la grille du 2026-11-27 a trouvé la brique
« autres accords » déclenchée sur le prix Nobel de la paix (mot « peace »), 13 fois, à environ 27 % par candidat.
Correction générale (décision de l'auteur du 2026-11-26 : corriger par règle commune, pas brique par brique).
"""
from __future__ import annotations

import re

# (famille, motif, dynamique générique). L'ordre fixe la famille principale : du plus spécifique au plus général.
FAMILLES = [
    ("distinction_classement", r"\b(nobel|prize|award|oscar|grammy|emmy|person of the year|richest|trillionaire|"
                               r"largest|top \d+|leaderboard|ranking|ranked|billboard|hot 100|most valuable|"
                               r"m[aá]ximo goleador|mayores)\b", "compétition"),
    ("sport", r"\b(match|matches|tournament|championship|cup|grand prix|f1|formula 1|nba|nfl|mlb|nhl|uefa|premier league|"
              r"atp|wta|wimbledon|open|super bowl|world series|olympic|medal|goals?|scores?|playoffs?|finals?|"
              r"defeat|beat|ballon d'or|mvp)\b", "compétition"),
    ("election", r"\b(win|wins|won|elected|elections?|primary|primaries|nominee|vote share|seats|electoral|"
                 r"re-?elected|runoff|polls?|polling|referendum|become (the )?(prime minister|president|leader|chancellor)|"
                 r"return as|run for|intenci[oó]n de voto|encuestas|ganar[aá])\b", "course"),
    ("maintien", r"\bbe (the )?(president|prime minister|chancellor|premier|leader|head of|ceo|chair\w*|governor|mayor|speaker)\b|\b(exist|alive|leave office|remain|resign|resigns|resignation|step down|steps down|ousted|removed|fired|"
                 r"out as|cease to be|still be|impeach\w*|no-confidence|no confidence|depart)\b", "maintien"),
    ("rencontre", r"\b(meet|meets|meeting|visit|visits|travel to|attend|attends|summit|talk|talks|phone call|call with|"
                  r"speak with|in person)\b", "rare"),
    ("accord_conflit", r"\b(ceasefire|cease-fire|truce|armistice|peace (deal|agreement|treaty)|hostages?|"
                       r"prisoner exchange)\b", "procédure"),
    ("accord_general", r"\b(agreement|deal|treaty|pact|accord|joins?|join the|extended|extension|renew\w*|"
                       r"commit\w*|framework|memorandum)\b", "procédure"),
    ("conflit_escalade", r"\b(coup|uprising|detonate|nuclear device|displaced|controlled territory|strike|strikes|airstrike|attack|attacks|invade|invasion|troops|military|missile|drone|"
                         r"war|cyber-?attack\w*|bomb\w*|shell\w*|clash\w*|blockade|nuclear test|seize|capture)\b", "rare"),
    ("justice", r"\b(court|supreme court|judge|ruling|convicted|indicted|indictment|sentenced|lawsuit|trial|"
                r"plead|pardon\w*|arrest\w*|charged|verdict|appeal|acquitted|extradit\w*)\b", "procédure"),
    ("banque_centrale", r"\b(fed|fomc|federal reserve|ecb|bank of england|boj|interest rates?|rate cut|rate hike|"
                        r"basis points|bps|policy rate)\b", "lente"),
    ("marche_prix", r"\b(price|close|closes|closing|trade|trading|index|s&p|nasdaq|dow|bitcoin|btc|ethereum|eth|"
                    r"crude|brent|wti|gold|silver|yield|stock|shares|market cap|exchange rate|usd|eur|housing|exports?|"
                    r"market share|capitali[sz]\w*|bubble|crash|cerrar[aá]|superar[aá]|precios?|pib|ibex|etf|"
                    r"\$\d)", "rapide"),
    ("statistique_publiee", r"\b(inflation|cpi|gdp|unemployment|jobs report|payrolls|approval rating|"
                            r"poll average|rate of|number of|how many|cases|deaths|count|measles|temperature|"
                            r"emissions|population|downloads|views|subscribers|recession|record|discovered|found|confirmed)\b", "lente ou cumulative"),
    ("climat_catastrophe", r"\b(hurricane|typhoon|cyclone|storm|earthquake|magnitude|wildfire|flood\w*|drought|"
                           r"heat ?wave|tornado|volcan\w*|landfall|el ni[nñ]o|la ni[nñ]a)\b", "cyclique"),
    ("sante_epidemie", r"\b(outbreak|pandemic|epidemic|virus|h5n1|bird flu|covid|mpox|ebola|cholera|who declare\w*|"
                       r"phe(ic)?|vaccine)\b", "cyclique"),
    ("autorisation_reglementaire", r"\b(approve|approves|approval|approved|fda|ema|license|licence|permit|authoriz\w*|"
                                   r"authoris\w*|ban|bans|banned|regulat\w*|sanction\w*|tariff\w*|export control\w*|"
                                   r"certif\w*|designate\w*|requirements?|restrict\w*|legally permitted|suspension|lifted|"
                                   r"threat level|barred|phase out|null and void|illegal|filtered)\b", "procédure"),
    ("procedure_legislative", r"\b(bill|law|act|senate|house|congress|parliament|assembly|legislat\w*|pass|passes|"
                              r"ratif\w*|amendment|budget|vote|votes|shutdown|debt ceiling|motion|decree)\b", "procédure"),
    ("action_executive", r"\b(executive order|sign|signs|signed|invoke|invokes|announce|announces|declare|declares|"
                         r"nominate|nominates|appoint\w*|deploy\w*|withdraw\w*|recogni[sz]e|expel\w*|"
                         r"emergency|insurrection act|national guard)\b", "rare"),
    ("entreprise", r"\b(acquire|acquisition|merger|merge|ipo|bankrupt\w*|chapter 11|funding round|valuation|"
                   r"layoffs?|ceo|revenue|earnings|deal with|partnership|antitrust|unicorn)\b", "procédure"),
    ("technologie_ia", r"\b(ai|model|gpt|claude|gemini|llm|benchmark|openai|anthropic|deepmind|chip|chips|nvidia|"
                       r"release|launch|launches|app store|quantum|humanoid|robotaxi|starship|rocket|spacex|"
                       r"satellite|lunar|moon|mars|hack\w*|outage|offline|critical incident|internet|starlink|waymo|"
                       r"brain-computer|linux|website)\b", "jalon"),
    ("jalon_projet", r"\b(released?|published|complete|completed|completion|open|opens|opening|begin|begins|start|starts|operational|"
                     r"construction|reactor|fuel loading|first flight|delivered|delivery|restart|reopen\w*|"
                     r"finish\w*|deadline)\b", "jalon"),
]
REGEX = [(f, re.compile(m, re.I), d) for f, m, d in FAMILLES]

# Briques compatibles avec chaque famille de situation (ce qu'une brique est censée mesurer).
COMPATIBLE = {
    "prix": {"marche_prix"},
    "evenements": {"statistique_publiee", "conflit_escalade", "climat_catastrophe", "sante_epidemie"},
    "maintien": {"maintien"},
    "escalade": {"conflit_escalade"},
    "tennis_elo": {"sport"},
    "football_elo": {"sport", "election", "distinction_classement"},
    "competitions": {"sport", "election", "technologie_ia", "entreprise", "distinction_classement"},
    "banque_centrale": {"banque_centrale"},
    "cessez_le_feu": {"accord_conflit", "accord_general"},
    "tenue": {"accord_conflit"},
    "accord_guerre": {"accord_conflit", "accord_general"},
    "rencontres": {"rencontre"},
    "sommets": {"rencontre"},
    "justice": {"justice"},
    "autres_accords": {"accord_general", "procedure_legislative", "entreprise", "autorisation_reglementaire",
                       "accord_conflit"},
}


COMBINAISON = "We are presenting you with two probability questions"


def familles(titre: str) -> list[str]:
    return [f for f, rx, _ in REGEX if rx.search(titre or "")]




def compatible(brique: str, titre: str) -> tuple[bool, list[str]]:
    """(permise, familles de la question). Brique inconnue de la table, ou question sans famille : permise."""
    fs = familles(titre)
    if not fs or brique not in COMPATIBLE:
        return True, fs
    return bool(COMPATIBLE[brique] & set(fs)), fs
