"""Classement des questions par type et par régime causal, SANS modèle de langue (0.10.115, demande de l'auteur du
2026-11-15 : « automatiser le classement des types de question, par mot clé » ; des questions de même série se
ressemblent, un modèle n'y est pas utile). Déterministe, reproductible, gratuit.

Chaque type renvoie au régime causal dominant (note `claude/regimes-causaux-principes-actifs.md` du projet) :
  conflit → intention et contagion ; election → intention ; annonce → intention (calendriers promis qui glissent) ;
  marche → réflexivité ; meteo → causalité physique (cycle forcé) ; macro → inertie ; sante → contagion.
Ordre de priorité : la première règle qui reconnaît la question l'emporte (le modèle de question ForecastBench
d'abord, puis les mots clés). « indetermine » si rien ne correspond : on ne force pas une case.

    from type_question import classer
    classer("Will there be more 'Riots' in Armenia ...")  # → {"type": "conflit", "regime": [...], "regle": ...}
"""
from __future__ import annotations

import re

REGIMES = {"conflit": ["intention", "contagion"], "election": ["intention"], "annonce": ["intention"],
           "marche": ["reflexivite"], "meteo": ["cycle_force", "physique"], "macro": ["inertie"],
           "sante": ["contagion"], "indetermine": []}

# modèles de questions ForecastBench (séries) : reconnus avant les mots clés
GABARITS = [
    (r"'(riots|protests|battles|explosions/remote violence|violence against civilians|strategic developments)'", "conflit"),
    (r"\b(acled)\b|fatalities", "conflit"),
    (r"temperature|température|°c|precipitation|rainfall|snow\w*|neige|heatwave|canicule|hurricane|ouragan|typhoon|météo-france|meteofrance", "meteo"),
    (r"higher rate of return than|closing price|stock price|share price|market cap", "marche"),
    # séries ForecastBench « X aura-t-il augmenté au … par rapport au … » (FRED, DBnomics hors météo) : économie et
    # finance, régime d'inertie ou de réflexivité selon la série ; rangées en macro, le banc mesure le régime exact
    (r"have increased by \d{4}-\d{2}-\d{2} as compared to its value|probability that the value of the .* time series", "macro"),
]

MOTS = [
    ("conflit", r"\b(war|wars|attack|attacks|airstrike|missile|ceasefire|cease-fire|truce|invasion|invade|troops|"
                r"military|coup|insurgen\w*|militia|riot\w*|protest\w*|clash\w*|killed|casualt\w*|hostage\w*|"
                r"guerre|attaque|cessez-le-feu|frappe|émeute\w*|manifestation\w*)\b"),
    ("marche", r"\b(net worth|stock|stocks|s&p|nasdaq|dow jones|index|yield|treasury|bond|exchange rate|bitcoin|"
               r"ethereum|crypto\w*|oil price|brent|wti|gold price|bourse|devise)\b"),
    ("sante", r"\b(outbreak|pandemic|epidemic|cases of|infection\w*|vaccine\w*|virus|measles|h5n1|who declares|"
              r"épidémie|pandémie|vaccin\w*)\b"),
    ("macro", r"\b(inflation|cpi|gdp|unemployment|jobless|interest rates?|rate cut|cut rates|rate hike|fed funds|"
              r"federal reserve|the fed|central bank|recession|payrolls|pib|chômage|taux directeur|banque centrale)\b"),
    ("election", r"\b(election\w*|re-?elect\w*|vote|votes|voting|referendum|ballot|parliament\w*|presidential|"
                 r"prime minister|chancellor|impeach\w*|polls?|coalition|primaries|leave the eu|exit the eu|"
                 r"withdraw from|join (nato|the eu)|resign\w*|élection\w*|scrutin|référendum|sondage\w*|démission\w*)\b"),
    ("annonce", r"\b(launch\w*|release\w*|announce\w*|unveil\w*|ship\w*|deliver\w*|rollout|ipo|go public|"
                r"approve\w*|approval|sign\w*|agreement|deal|treaty|lancer|lancement|annonc\w*|sortie|accord|traité)\b"),
]


def classer(titre: str, criteres: str = "") -> dict:
    t = f"{titre} {criteres}".lower()
    for motif, typ in GABARITS:
        if re.search(motif, t):
            return {"type": typ, "regime": REGIMES[typ], "regle": f"gabarit:{motif[:40]}"}
    titre_l = titre.lower()          # les mots clés regardent le titre d'abord (les critères contiennent du bruit)
    for zone in (titre_l, t):
        for typ, motif in MOTS:
            m = re.search(motif, zone)
            if m:
                return {"type": typ, "regime": REGIMES[typ], "regle": f"mot:{m.group(0)}"}
    return {"type": "indetermine", "regime": [], "regle": None}
