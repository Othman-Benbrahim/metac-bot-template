"""Classes homologues tirées des fiches écosystémiques (bot 0.10.385, ombre).

Décisions de l'auteur, 2026-11-20 (12 h 24 et 12 h 29) : raisonnement par induction avec des règles d'échelle et de
variabilité propres à chaque écosystème ; ne l'appliquer que là où les critères définis s'appliquent ; champ libre
pour les classes, sous cette contrainte ; viser une couverture suffisante pour que les tests soient valides.

Une question entre dans une classe si :
1. un acteur d'une fiche est nommé dans le titre (motifs écrits ci-dessous ; si plusieurs acteurs sont nommés, celui qui
   apparaît le premier, le sujet grammatical le plus souvent) ;
2. la taille, la vitesse et la nature (organisation) de cet acteur sont celles que la FICHE déclare (lues dans le
   fichier YAML, jamais réécrites ici) ;
3. la fenêtre de la question se situe par rapport à la vitesse de l'acteur : « courte » (moins d'une fois sa vitesse),
   « à sa mesure » (1 à 4 fois), « large » (plus de 4 fois).
Classe = fiche × nature de l'acteur × rapport fenêtre / vitesse. Pas de mélange entre écosystèmes.
Sinon : hors cadre, la question n'est pas touchée.
"""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

import yaml

DOSSIER = Path("ecosystemes")
# vitesse déclarée dans les fiches → jours (ordre de grandeur, conversion écrite)
JOURS = {"minutes": 0.01, "heures": 0.25, "jours": 3, "semaines": 14, "mois": 60, "trimestre": 90, "saisons": 90,
         "année": 365, "années": 365, "décennie": 3650, "siècle": 36500, "millénaire": 365000}

# (fiche, début du nom de l'acteur dans la fiche, motif du titre en anglais) — motifs écrits, ordre sans importance
MOTIFS = [
    ("politique-americaine", "le président en personne", r"\btrump\b|\bbiden\b|\bvance\b"),
    ("politique-americaine", "une agence fédérale", r"\b(fda|epa|cdc|fbi|doj|department of justice|irs|faa|fcc|ftc|sec|doge|ice|dhs)\b"),
    ("politique-americaine", "la majorité de chaque chambre", r"\b(congress|senate|house of representatives|house speaker|filibuster|shutdown)\b|\bpass(es|ed)? (the|a) bill\b"),
    ("politique-americaine", "la Cour suprême", r"supreme court|\bscotus\b"),
    ("politique-americaine", "un juge fédéral", r"federal judge|district court|court of appeals|\bindict|\bconvicted\b|\bsentenced\b"),
    ("politique-americaine", "Réserve fédérale", r"federal reserve|\bthe fed\b|\bfomc\b|\bpowell\b"),
    ("politique-americaine", "représentant au Commerce", r"\btariff|\bustr\b|trade deal|trade agreement"),
    ("politique-americaine", "bureau du contrôle des avoirs", r"\bofac\b|\bsanction"),
    ("russie-ukraine", "le président russe en personne", r"\bputin\b"),
    ("russie-ukraine", "le président ukrainien en personne", r"\bzelensk"),
    ("russie-ukraine", "les forces armées russes", r"russia(n)? (forces|troops|army|military)|russia (capture|take|seize|advance|attack|strike)|\b(pokrovsk|kupiansk|kostiantynivka|zaporizhzhia|kharkiv|sumy|kherson|odesa)\b"),
    ("russie-ukraine", "Russie (gouvernement)", r"\brussia\b|\bkremlin\b|\bmoscow\b"),
    ("russie-ukraine", "Ukraine (gouvernement)", r"\bukrain|\bkyiv\b"),
    ("guerre-levant", "Israël (État)", r"\bisrael|\bidf\b|\bnetanyahu\b"),
    ("guerre-levant", "Hamas", r"\bhamas\b"),
    ("guerre-levant", "Hezbollah", r"\bhezbollah\b"),
    ("guerre-levant", "Houthis", r"\bhouthi"),
    ("guerre-levant", "l'Assemblée générale et le Conseil de sécurité", r"security council|\bunsc\b|general assembly"),
    ("iran-nucleaire", "Iran (État)", r"\biran\b|\biranian\b|\btehran\b"),
    ("iran-nucleaire", "le Guide suprême en personne", r"\bkhamenei\b|supreme leader"),
    ("iran-nucleaire", "Agence internationale de l'énergie atomique", r"\biaea\b|atomic energy agency"),
    ("rivalite-sino-americaine", "le dirigeant chinois en personne", r"\bxi jinping\b|\bxi\b"),
    ("rivalite-sino-americaine", "Armée populaire de libération", r"\bpla\b|people's liberation army|china (invade|blockade|attack)|taiwan strait"),
    ("rivalite-sino-americaine", "Taïwan (autorités)", r"\btaiwan"),
    ("rivalite-sino-americaine", "Chine (direction du Parti et de l'État)", r"\bchina\b|\bchinese\b|\bbeijing\b"),
    ("securite-europeenne", "l'OTAN", r"\bnato\b"),
    ("securite-europeenne", "le Conseil européen", r"european union|\beu\b|european council|european commission"),
    ("inflation-mondiale", "Banque centrale européenne", r"\becb\b|european central bank|\blagarde\b"),
    ("inflation-mondiale", "Banque populaire de Chine", r"people's bank of china|\bpboc\b"),
    ("sciences-techniques", "un laboratoire d'IA", r"\bopenai\b|\banthropic\b|\bdeepmind\b|google|\bxai\b|\bgrok\b|\bgpt|\bgemini\b|\bclaude\b|\bllm\b|ai model|\bdeepseek\b|\bmeta\b"),
    ("energie-mondiale", "OPEP+", r"\bopec"),
    ("energie-mondiale", "Arabie saoudite", r"\bsaudi"),
    ("epidemies", "Organisation mondiale de la santé", r"\bwho\b|world health organization|pandemic emergency|\bpheic\b"),
    ("epidemies", "un variant", r"\bh5n1\b|bird flu|measles|\bmpox\b|covid|ebola|\bvariant\b|outbreak"),
    ("climat-extremes", "un cyclone tropical", r"hurricane|tropical storm|typhoon|cyclone"),
    ("climat-extremes", "El Niño", r"el ni[nñ]o|la ni[nñ]a"),
]


@lru_cache(maxsize=1)
def acteurs() -> list[dict]:
    """Acteurs des fiches avec leurs axes déclarés, joints aux motifs ; un motif sans acteur trouvé est une erreur."""
    out = []
    for fiche, debut, rx in MOTIFS:
        d = yaml.safe_load((DOSSIER / f"{fiche}.yaml").read_text(encoding="utf-8")) or {}
        trouve = None
        for c in d.get("compartiments") or []:
            for a in c.get("acteurs") or []:
                if isinstance(a, dict) and a.get("nom", "").startswith(debut):
                    trouve = a
                    break
            if trouve:
                break
        if not trouve:
            raise KeyError(f"{fiche} : acteur introuvable « {debut} »")
        out.append({"fiche": fiche, "acteur": trouve["nom"], "organisation": trouve.get("organisation"),
                    "taille": trouve.get("taille"), "vitesse": trouve.get("vitesse"),
                    "vitesse_jours": JOURS.get(str(trouve.get("vitesse")).strip()), "rx": re.compile(rx, re.I)})
    return out


def rapport(horizon: int | None, vitesse_jours: float | None) -> str | None:
    if horizon is None or not vitesse_jours:
        return None
    r = horizon / vitesse_jours
    return "courte" if r < 1 else "a_sa_mesure" if r <= 4 else "large"


def classe(titre: str, horizon: int | None) -> dict | None:
    """Classe homologue de la question, ou None (hors cadre)."""
    t = titre or ""
    vus = []
    for a in acteurs():
        m = a["rx"].search(t)
        if m:
            vus.append((m.start(), a))
    if not vus:
        return None
    _, a = min(vus, key=lambda v: v[0])
    rp = rapport(horizon, a["vitesse_jours"])
    if rp is None:
        return None
    return {"fiche": a["fiche"], "acteur": a["acteur"], "organisation": a["organisation"], "taille": a["taille"],
            "vitesse": a["vitesse"], "rapport": rp, "cle": f'{a["fiche"]}|{a["organisation"]}|{rp}'}
