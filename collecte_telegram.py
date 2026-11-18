"""Observatoire Telegram par les MÉTADONNÉES : rythme, horaire, vues, relais (bot 0.10.250, en ombre).

Décisions d'auteur du 2026-11-18 : principe des métadonnées (4 h 34-4 h 36, claude/principe-metadonnees.md) ; liste de
chaînes qui se met à jour d'elle-même par les relais entre chaînes (4 h 43, « je valide, mets-le en place »).
Sonde du 2026-11-18 (run 44231880738) : t.me n'a pas de robots.txt (404, aucune interdiction déclarée) ; l'aperçu public
d'une chaîne (https://t.me/s/<chaîne>) se lit sans compte (une vingtaine de messages par page). L'ISW refuse les
serveurs de GitHub (403) : sa liste n'est pas utilisée, rien n'est contourné.

AUCUN TEXTE N'EST GARDÉ. Pour chaque message : chaîne, numéro, heure UTC, nombre de vues, chaîne d'origine s'il est
relayé, chaînes citées par un lien t.me. Le rattachement à un pays se fait par la CHAÎNE (son groupe, fixé dans la
liste), jamais par le contenu.

Liste des chaînes (registre/telegram-chaines.csv : chaine, groupe, origine, ajoutee_le, statut) :
- noyau : les 20 chaînes par défaut de Cheyenne (MJCruickshank/cheyenne, intel.py ; noms de chaînes seulement) et les
  chaînes des sections conflits de la liste publique de J. Whittaker (news.jeremywhittaker.com/api/channels.json :
  Russia/Ukraine, Global Conflict, Middle East & Iran, China/Asia), lues une fois au premier passage ;
- mise à jour mensuelle (au premier passage de chaque mois) : ENTRENT au plus 10 chaînes, celles qui ont été relayées ou
  citées au moins 5 fois sur 30 jours par au moins 2 chaînes actives différentes (groupe : le plus fréquent parmi les
  chaînes qui les citent) ; deviennent MUETTES les chaînes sans message depuis 30 jours ; DISPARUES celles dont l'aperçu
  échoue 7 passages de suite. Une chaîne muette ou disparue reste au registre (son silence est une donnée).
Registres : registre/telegram-messages.csv (chaine, id, heure, vues, relaye_de, cite) ; registre/telegram-releves.csv
(releve, chaine, statut_http, messages_lus) ; registre/telegram-liste-journal.csv (jour, chaine, mouvement, raison).
Une pause de 3 secondes entre deux pages. 0.10.251 (après le premier passage, run 44237976381 : 19 chaînes sur 20
remplissaient leur unique page de 20 messages, soit quelques heures seulement pour les plus actives) : chaque chaîne
est remontée page par page (?before=) jusqu'au dernier message déjà connu, ou sur 26 heures pour une chaîne nouvelle,
au plus 15 pages ; le relevé note si la remontée est complète. Budget total : 35 minutes. Les comptes de bots
(nom finissant par « bot ») ne comptent pas comme citations.

    python collecte_telegram.py
"""
from __future__ import annotations

import csv
import html as html_mod
import os
import re
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx

REG = Path("registre")
CHAINES = REG / "telegram-chaines.csv"
MESSAGES = REG / "telegram-messages.csv"
RELEVES = REG / "telegram-releves.csv"
JOURNAL = REG / "telegram-liste-journal.csv"
UA = {"User-Agent": "alphabet-situationnel-bot/1.0 (recherche non commerciale ; GitHub Othman-Benbrahim)"}
WHITTAKER = "https://news.jeremywhittaker.com/api/channels.json"
SECTIONS = {"Russia/Ukraine": "UKRAINE", "Global Conflict": "MONDE", "Middle East & Iran": "MOYEN-ORIENT",
            "China/Asia": "ASIE"}
NOYAU_CHEYENNE = [  # noms publics des chaînes ; groupe tel que donné par Cheyenne
    ("kpszsu", "UKRAINE"), ("GeneralStaffZSU", "UKRAINE"), ("DeepStateUA", "UKRAINE"), ("suspilnenews", "UKRAINE"),
    ("Tsaplienko", "UKRAINE"), ("UkraineNow", "UKRAINE"), ("mod_russia", "UKRAINE"), ("rybar", "UKRAINE"),
    ("boris_rozhin", "UKRAINE"), ("astrapress", "UKRAINE"), ("manniefabian", "MOYEN-ORIENT"),
    ("idfofficial", "MOYEN-ORIENT"), ("englishabuali", "MOYEN-ORIENT"), ("CumtaAlertsEnglishChannel", "MOYEN-ORIENT"),
    ("QudsNen", "MOYEN-ORIENT"), ("ajanews", "MOYEN-ORIENT"), ("Alhadath_Brk", "MOYEN-ORIENT"),
    ("Middle_East_Spectator", "MOYEN-ORIENT"), ("warmonitors", "MOYEN-ORIENT"), ("bintjbeilnews", "MOYEN-ORIENT"),
]
NOM = re.compile(r"^[A-Za-z][A-Za-z0-9_]{3,31}$")
ENTREES_MAX, SEUIL_CITATIONS, SEUIL_CITANTS, MUETTE_JOURS, ECHECS_MAX = 10, 5, 2, 30, 7
CH_C = ["chaine", "groupe", "origine", "ajoutee_le", "statut"]
MS_C = ["chaine", "id", "heure", "vues", "relaye_de", "cite"]
RL_C = ["releve", "chaine", "statut_http", "messages_lus", "pages", "complet"]
DIAG = Counter()   # contrôle de lecture : balises de relais vues dans le HTML brut
PAGES_MAX, PLANCHER_HEURES, DUREE_MAX = 15, 26, 35 * 60
JL_C = ["jour", "chaine", "mouvement", "raison"]
_DECOUPE = re.compile(r'<div class="tgme_widget_message_wrap')
_POST = re.compile(r'data-post="([^"/]+)/(\d+)"')
_HEURE = re.compile(r'<time datetime="([^"]+)"')
_VUES = re.compile(r'tgme_widget_message_views">([^<]+)<')
_RELAIS_BALISE = re.compile(r'<a\b[^>]*tgme_widget_message_forwarded_from_name[^>]*>')
_HREF = re.compile(r'href="https?://t\.me/([A-Za-z][A-Za-z0-9_]{3,31})')
_LIEN = re.compile(r'href="https?://t\.me/(?:s/)?([A-Za-z][A-Za-z0-9_]{3,31})(?:/\d+)?["?]')


def vues(s: str) -> int | None:
    s = (s or "").strip().upper().replace(",", ".")
    m = re.fullmatch(r"([\d.]+)\s*([KM]?)", s)
    if not m:
        return None
    return int(float(m.group(1)) * {"": 1, "K": 1_000, "M": 1_000_000}[m.group(2)])


def lire_page(page: str, chaine: str) -> list[dict]:
    """Métadonnées des messages d'un aperçu public ; aucun texte."""
    coupes = [m.start() for m in _DECOUPE.finditer(page)] + [len(page)]
    out = []
    for a, b in zip(coupes, coupes[1:]):
        bloc = page[a:b]
        p, h = _POST.search(bloc), _HEURE.findall(bloc)
        if not p or not h:
            continue
        try:
            heure = datetime.fromisoformat(h[-1]).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            continue
        v = _VUES.search(bloc)
        b = _RELAIS_BALISE.search(bloc)
        r = _HREF.search(b.group(0)) if b else None   # relais d'une chaîne privée : pas de lien, pas de nom gardé
        relaye = r.group(1) if r else ""
        cites = sorted({c for c in _LIEN.findall(bloc) if not c.lower().endswith("bot") and c.lower() not in (chaine.lower(), p.group(1).lower(),
                                                                         relaye.lower(), "share", "joinchat", "addstickers",
                                                                         "proxy", "iv", "contact", "addlist", "boost")})
        out.append({"chaine": p.group(1), "id": int(p.group(2)), "heure": heure,
                    "vues": "" if not v or vues(html_mod.unescape(v.group(1))) is None else vues(html_mod.unescape(v.group(1))),
                    "relaye_de": relaye, "cite": ";".join(cites)})
    return out


def lire_csv(p: Path) -> list[dict]:
    return list(csv.DictReader(p.open(encoding="utf-8"))) if p.exists() else []


def ecrire_csv(p: Path, champs: list[str], lignes: list[dict]) -> None:
    with p.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=champs)
        w.writeheader()
        w.writerows(lignes)


def ajouter_csv(p: Path, champs: list[str], lignes: list[dict]) -> None:
    if p.exists():
        with p.open(encoding="utf-8") as f:
            entete = next(csv.reader(f), [])
        if entete != champs:                                    # colonnes ajoutées : on réécrit, cases vides
            ecrire_csv(p, champs, [{k: l.get(k, "") for k in champs} for l in lire_csv(p)])
    neuf = not p.exists()
    with p.open("a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=champs)
        if neuf:
            w.writeheader()
        w.writerows(lignes)


def noyau(jour: str) -> list[dict]:
    return [{"chaine": n, "groupe": g, "origine": "cheyenne", "ajoutee_le": jour, "statut": "active"} for n, g in NOYAU_CHEYENNE]


def whittaker(c: httpx.Client, chaines: list[dict], jour: str) -> list[dict]:
    """Ajoute les chaînes des sections conflits de la liste Whittaker ; renvoie les ajouts ([] si indisponible)."""
    lignes = {x["chaine"].lower(): x for x in chaines}
    ajouts = []
    try:
        r = c.get(WHITTAKER)
        r.raise_for_status()
        for x in r.json().get("channels", r.json() if isinstance(r.json(), list) else []):
            g = SECTIONS.get(x.get("section_label") or x.get("section") or "")
            h = (x.get("handle") or "").lstrip("@")
            if g and NOM.match(h) and h.lower() not in lignes:
                lignes[h.lower()] = {"chaine": h, "groupe": g, "origine": "whittaker", "ajoutee_le": jour, "statut": "active"}
                ajouts.append(lignes[h.lower()])
    except Exception as e:
        print(f"Liste Whittaker indisponible ({type(e).__name__}) : nouvel essai au prochain passage.")
        return []
    if not ajouts:
        print("Liste Whittaker lue, aucune chaîne nouvelle dans les sections retenues.")
    return ajouts


def remonter(c: httpx.Client, chaine: str, dernier_id: int, plancher: str, pages_max: int) -> tuple[str, list[dict], int, bool]:
    """Remonte l'aperçu page par page (?before=) jusqu'au dernier message connu, ou jusqu'au plancher horaire
    si la chaîne est nouvelle. Renvoie (statut HTTP, messages, pages lues, complet)."""
    ms, url, code = [], f"https://t.me/s/{chaine}", ""
    for page in range(1, pages_max + 1):
        if page > 1:
            time.sleep(3)
        try:
            r = c.get(url)
            code = str(r.status_code)
        except Exception as e:
            return (code or type(e).__name__), ms, page, False
        if r.status_code != 200:
            return code, ms, page, False
        DIAG["balises_relais"] += r.text.count("forwarded_from")
        lot = lire_page(r.text, chaine)
        if not lot:
            return code, ms, page, True                       # début de la chaîne atteint (ou page vide)
        ms += lot
        bas = min(lot, key=lambda m: m["id"])
        if bas["id"] <= dernier_id or bas["heure"] < plancher:
            return code, ms, page, True
        url = f"https://t.me/s/{chaine}?before={bas['id']}"
    return code, ms, pages_max, False


def mettre_a_jour(chaines: list[dict], messages: list[dict], releves: list[dict], jour: str) -> list[dict]:
    """Entrées par les relais et citations ; muettes ; disparues. Renvoie les mouvements du journal."""
    limite = (datetime.fromisoformat(jour) - timedelta(days=30)).strftime("%Y-%m-%d")
    actives = {x["chaine"].lower(): x for x in chaines if x["statut"] == "active"}
    connues = {x["chaine"].lower() for x in chaines}
    citations, citants = Counter(), defaultdict(set)
    for m in messages:
        if m["heure"][:10] < limite or m["chaine"].lower() not in actives:
            continue
        for c in ([m["relaye_de"]] if m["relaye_de"] else []) + [x for x in m["cite"].split(";") if x]:
            k = c.lower()
            if k in connues or not NOM.match(c):
                continue
            citations[k] += 1
            citants[k].add(m["chaine"].lower())
    noms = {}
    for m in messages:
        for c in ([m["relaye_de"]] if m["relaye_de"] else []) + [x for x in m["cite"].split(";") if x]:
            noms.setdefault(c.lower(), c)
    mouvements = []
    retenues = [k for k, n in citations.most_common() if n >= SEUIL_CITATIONS and len(citants[k]) >= SEUIL_CITANTS][:ENTREES_MAX]
    for k in retenues:
        groupe = Counter(actives[c]["groupe"] for c in citants[k] if c in actives).most_common(1)[0][0]
        chaines.append({"chaine": noms[k], "groupe": groupe, "origine": "relais", "ajoutee_le": jour, "statut": "active"})
        mouvements.append({"jour": jour, "chaine": noms[k], "mouvement": "entrée",
                           "raison": f"{citations[k]} relais ou citations par {len(citants[k])} chaînes en 30 jours"})
    dernier = defaultdict(str)
    for m in messages:
        dernier[m["chaine"].lower()] = max(dernier[m["chaine"].lower()], m["heure"][:10])
    echecs = defaultdict(int)
    for r in sorted(releves, key=lambda r: r["releve"]):
        k = r["chaine"].lower()
        echecs[k] = 0 if r["statut_http"] == "200" else echecs[k] + 1
    for x in chaines:
        k = x["chaine"].lower()
        if x["statut"] != "active" or x["ajoutee_le"] > limite:
            continue
        if echecs[k] >= ECHECS_MAX:
            x["statut"] = "disparue"
            mouvements.append({"jour": jour, "chaine": x["chaine"], "mouvement": "disparue", "raison": f"{echecs[k]} échecs de suite"})
        elif dernier[k] < limite:
            x["statut"] = "muette"
            mouvements.append({"jour": jour, "chaine": x["chaine"], "mouvement": "muette",
                               "raison": f"dernier message : {dernier[k] or 'jamais lu'}"})
    return mouvements


def principal() -> int:
    maintenant = datetime.now(timezone.utc)
    jour, releve = maintenant.strftime("%Y-%m-%d"), maintenant.strftime("%Y-%m-%dT%H:%MZ")
    REG.mkdir(exist_ok=True)
    with httpx.Client(headers=UA, timeout=40, follow_redirects=True) as c:
        chaines = lire_csv(CHAINES)
        if not chaines:
            chaines = noyau(jour)
            ajouter_csv(JOURNAL, JL_C, [{"jour": jour, "chaine": x["chaine"], "mouvement": "entrée", "raison": "noyau (cheyenne)"}
                                         for x in chaines])
        if not any(l["raison"] == "noyau (whittaker)" for l in lire_csv(JOURNAL)):
            ajouts = whittaker(c, chaines, jour)
            chaines += ajouts
            ajouter_csv(JOURNAL, JL_C, [{"jour": jour, "chaine": x["chaine"], "mouvement": "entrée", "raison": "noyau (whittaker)"}
                                         for x in ajouts])
        messages = lire_csv(MESSAGES)
        deja = {(m["chaine"].lower(), m["id"]): m for m in messages}
        derniers = defaultdict(int)
        for (k, i) in deja:
            derniers[k] = max(derniers[k], int(i))
        plancher = (maintenant - timedelta(hours=PLANCHER_HEURES)).strftime("%Y-%m-%dT%H:%M:%SZ")
        debut, lus, pleines, nouveaux, rel = time.monotonic(), 0, 0, 0, []
        for x in chaines:
            if x["statut"] == "disparue":
                continue
            if time.monotonic() - debut > DUREE_MAX:
                rel.append({"releve": releve, "chaine": x["chaine"], "statut_http": "temps", "messages_lus": 0, "pages": 0, "complet": "non"})
                continue
            time.sleep(3)
            code, ms, pages, complet = remonter(c, x["chaine"], derniers[x["chaine"].lower()], plancher, PAGES_MAX)
            rel.append({"releve": releve, "chaine": x["chaine"], "statut_http": code, "messages_lus": len(ms),
                        "pages": pages, "complet": "oui" if complet else "non"})
            lus += code == "200"
            pleines += code == "200" and not complet
            for m in ms:
                k = (m["chaine"].lower(), str(m["id"]))
                if k in deja:
                    if m["vues"] != "":
                        deja[k]["vues"] = m["vues"]          # les vues croissent : on garde la dernière mesure
                else:
                    m["id"] = str(m["id"])
                    deja[k] = m
                    nouveaux += 1
        messages = sorted(deja.values(), key=lambda m: (m["chaine"].lower(), int(m["id"])))
        ajouter_csv(RELEVES, RL_C, rel)
        mouvements = []
        derniere_revue = max((l["jour"] for l in lire_csv(JOURNAL)), default=jour)   # le noyau compte comme revue
        if jour[:7] != derniere_revue[:7]:
            mouvements = mettre_a_jour(chaines, messages, lire_csv(RELEVES), jour)
            ajouter_csv(JOURNAL, JL_C, mouvements or [{"jour": jour, "chaine": "", "mouvement": "revue", "raison": "aucun mouvement"}])
        ecrire_csv(CHAINES, CH_C, chaines)
        ecrire_csv(MESSAGES, MS_C, messages)
    actives = sum(1 for x in chaines if x["statut"] == "active")
    bilan = (f"{releve} : {lus} chaînes lues sur {actives} actives, {nouveaux} nouveaux messages, {pleines} chaîne(s) incomplète(s) (plafond de {PAGES_MAX} pages) ; "
             f"{len(mouvements)} mouvement(s) de liste ; contrôle : {DIAG['balises_relais']} balise(s) « forwarded_from » dans le HTML, {sum(1 for m in messages if m['relaye_de'])} relais lus au total. Métadonnées seulement (aucun texte gardé). Source : aperçus publics t.me.")
    print(bilan)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
            f.write(f"## Observatoire Telegram (métadonnées)\n\n{bilan}\n")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
