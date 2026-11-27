"""Grille des familles de situation (2026-11-27, demande de l'auteur : « établir une grille pour chaque famille et
ratisser le plus large possible »).

Sans modèle de langue, sans appel réseau : mots du titre seulement. Chaque question reçoit une famille principale (la
première qui reconnaît le titre, dans l'ordre de FAMILLES) et la liste de toutes celles qui la reconnaissent.

Sorties (registre/grille-familles.json) :
- par famille : nombre de questions (Metaculus et toutes sources), part de « oui » (descriptif, NON causal : biais des
  rédacteurs), part couverte par au moins une brique (audit des briques du 2026-11-26) ;
- associations suspectes : brique déclenchée sur une question dont aucune famille n'est compatible avec elle
  (candidates « hors domaine », à relire, pas à corriger automatiquement) ;
- questions restées sans famille (pour compléter la grille au fil de l'eau).

    python mise_au_point/grille_familles.py
"""
from __future__ import annotations

import collections
import json
import re
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
REG = RACINE / "registre"

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


def principal() -> int:
    qs = {}
    for l in open(REG / "jugement-questions.jsonl", encoding="utf-8"):
        d = json.loads(l)
        if (d.get("titre") or "").startswith(COMBINAISON):     # questions combinées de ForecastBench : écartées
            continue
        qs[(d["source"], d["titre"].strip())] = d             # une question compte une fois (même titre)
    briq = collections.defaultdict(set)
    for l in open(REG / "audit-briques-2026-11-26.jsonl", encoding="utf-8"):
        a = json.loads(l)
        briq[(a["source"], a["titre"].strip())].add(a["fam"])

    stats = {s: collections.defaultdict(lambda: {"n": 0, "oui": 0, "jugees": 0, "brique": 0})
             for s in ("metaculus", "toutes")}
    suspectes, sans = [], []
    for k, d in qs.items():
        fs = familles(d["titre"])
        fp = fs[0] if fs else "sans_famille"
        y = d.get("issue")
        y = int(y) if str(y) in ("0", "1") else None
        for s in ("metaculus", "toutes"):
            if s == "metaculus" and d["source"] != "metaculus":
                continue
            c = stats[s][fp]
            c["n"] += 1
            if y is not None:
                c["jugees"] += 1
                c["oui"] += y
            if briq.get(k):
                c["brique"] += 1
        for b in briq.get(k, ()):
            if not (COMPATIBLE.get(b, set()) & set(fs)):
                suspectes.append({"source": d["source"], "id": d["id"], "titre": d["titre"][:160],
                                  "brique": b, "familles": fs})
        if not fs:
            sans.append({"source": d["source"], "titre": d["titre"][:160]})

    def tab(s):
        tot = sum(c["n"] for c in stats[s].values())
        out = []
        for f, c in sorted(stats[s].items(), key=lambda x: -x[1]["n"]):
            out.append({"famille": f, "n": c["n"], "part": round(c["n"] / tot, 3),
                        "oui": round(c["oui"] / c["jugees"], 3) if c["jugees"] else None,
                        "couverte_brique": round(c["brique"] / c["n"], 3)})
        return {"total": tot, "familles": out}

    res = {"date": "2026-11-27", "methode": "mots du titre, famille principale = première reconnue ; descriptif",
           "dynamique": {f: d for f, _, d in FAMILLES},
           "metaculus": tab("metaculus"), "toutes": tab("toutes"),
           "associations_suspectes": {"n": len(suspectes),
                                      "par_brique": dict(collections.Counter(x["brique"] for x in suspectes)),
                                      "exemples": suspectes[:60]},
           "sans_famille": {"n": len(sans), "exemples": sans[:40]}}
    (REG / "grille-familles.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    for s in ("metaculus", "toutes"):
        print(f"== {s} ({res[s]['total']})")
        for x in res[s]["familles"]:
            print(f"  {x['famille']:28s} {x['n']:5d} {x['part']:6.1%}  oui {x['oui']}  brique {x['couverte_brique']:.0%}")
    print("associations suspectes", res["associations_suspectes"]["n"], res["associations_suspectes"]["par_brique"])
    print("sans famille", len(sans))
    return 0


if __name__ == "__main__":
    raise SystemExit(principal())
