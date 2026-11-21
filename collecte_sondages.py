"""Collecte automatique des sondages électoraux pour les questions d'élection (décision de l'auteur du 2026-11-21,
15 h 24 : « puis après il faudra en automatiser la collecte, comme pour tout le reste »).

Source : les pages de sondages de Wikipédia en anglais, par l'API REST de Wikimedia (api.wikimedia.org), robots.txt
vérifié par politesse.autorise ; une source qui refuse est notée « refusée », jamais forcée. Licence CC BY-SA 4.0 :
on ne garde que des nombres (moyennes de sondages par candidat ou par parti), jamais le texte des pages.

Pour chaque question d'élection de la carte robot (règles de sondages) :
1. la page est cherchée par le titre de l'élection (« Opinion polling for the … », puis la page de l'élection) ;
2. les tableaux de sondages sont lus (cellules fusionnées comprises) ; une ligne garde la date de FIN de terrain ;
3. pour la date d'une question (son jeu), seuls les sondages terminés au moins 3 jours avant comptent (pas de fuite :
   un sondage publié après le jeu ne peut pas entrer) ; les lignes de résultat d'élection sont écartées ;
4. pour chaque colonne de candidat ou de parti : moyenne des 5 derniers sondages, leur nombre, la date du dernier.

    python collecte_sondages.py            # écrit registre/sondages-questions.json
"""
from __future__ import annotations

import json
import re
import sys
from datetime import date, timedelta
from html.parser import HTMLParser
from pathlib import Path

from unidecode import unidecode

SORTIE = Path("registre") / "sondages-questions.json"
CARTE = Path("registre") / "carte-robot-jugement2026.json"
API = "https://api.wikimedia.org/core/v1/wikipedia/en"
REGLES_SONDAGES = {"sondages_erreur_comparee", "us_erreur_selon_temps_restant", "us_erreur_sondages_par_echelle",
                   "presidentielles_mode_de_scrutin", "seuils_parlements_nationaux_europe"}
MOIS = {m[:3]: i for i, m in enumerate(("january february march april may june july august september october "
                                        "november december").split(), 1)}
N_DERNIERS, MARGE_JOURS, FRAICHEUR_JOURS = 5, 3, 90   # un sondage de plus de 90 jours avant le jeu ne compte pas
GENERIQUES = {"", "?", "majority", "lead", "others", "other", "oth", "undecided", "und", "n", "turnout", "abstention",
              "blank", "void", "nota", "candidates", "candidate", "party", "parties", "polling firm", "pollster", "sample",
              "sample size", "margin", "margin of error", "fieldwork date", "date", "date(s) administered", "o/u", "oth/ und",
              "abst. undec.", "don't know/no answer", "none", "invalid", "spoilt"}
MOTS_VIDES = {"the", "election", "elections", "primary", "presidential", "general", "parliamentary", "legislative",
              "opinion", "polling", "for", "of", "and", "in", "next", "round", "first", "second", "by-election", "republican",
              "democratic", "governor", "gubernatorial", "senate", "house", "national", "federal", "state", "united", "states",
              "representatives", "chamber", "assembly", "statewide", "nationwide", "party", "parties", "runoff", "wins", "win"}
SUFFIXE_PARTI = re.compile(r"\((d|r|dfl|i|l|g|ind|lib|grn)\)\s*$", re.I)     # « Jerri Green (D) » : affiche générale


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", unidecode(str(s or "")).lower()).strip()


# ---------------------------------------------------------------------------------------------- lecture des tableaux
class _Tables(HTMLParser):
    """Tableaux HTML → listes de lignes de cellules (texte, colspan, rowspan)."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tables, self._pile, self._cell, self._ignore = [], [], None, 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ("style", "script", "sup"):
            self._ignore += 1
        if tag == "table":
            self._pile.append([])
        elif tag == "tr" and self._pile:
            self._pile[-1].append([])
        elif tag in ("td", "th") and self._pile and self._pile[-1]:
            def entier(x):
                try:
                    return max(1, int(re.sub(r"\D", "", str(x)) or 1))
                except ValueError:
                    return 1
            self._cell = {"t": "", "c": entier(a.get("colspan", 1)), "r": entier(a.get("rowspan", 1)), "th": tag == "th"}
        elif tag == "br" and self._cell is not None:
            self._cell["t"] += " "

    def handle_endtag(self, tag):
        if tag in ("style", "script", "sup"):
            self._ignore = max(0, self._ignore - 1)
        if tag in ("td", "th") and self._cell is not None and self._pile and self._pile[-1]:
            self._pile[-1][-1].append(self._cell)
            self._cell = None
        elif tag == "table" and self._pile:
            self.tables.append(self._pile.pop())

    def handle_data(self, data):
        if self._cell is not None and not self._ignore:
            self._cell["t"] += data


def grilles(html: str) -> list[list[list[str]]]:
    """Chaque tableau en grille rectangulaire (fusions dépliées)."""
    p = _Tables()
    p.feed(html)
    out = []
    for rows in p.tables:
        grille, attente = [], {}
        for row in rows:
            ligne, col, cells = [], 0, list(row)
            while cells or col in attente:
                if col in attente:
                    t, reste = attente[col]
                    ligne.append(t)
                    if reste > 1:
                        attente[col] = (t, reste - 1)
                    else:
                        del attente[col]
                    col += 1
                    continue
                c = cells.pop(0)
                t = re.sub(r"\s+", " ", c["t"]).strip()
                for _ in range(c["c"]):
                    ligne.append(t)
                    if c["r"] > 1:
                        attente[col] = (t, c["r"] - 1)
                    col += 1
            grille.append(ligne)
        if grille:
            out.append(grille)
    return out


def fin_terrain(texte: str, an_defaut: int) -> date | None:
    """Date de fin de terrain : la DERNIÈRE date lisible de la cellule (« 5–9 Mar 2026 », « Mar 5–9, 2026 », « 2026-03-09 »)."""
    t = norm(texte)
    m = re.findall(r"(20\d\d)-(\d\d)-(\d\d)", t)
    if m:
        a, mo, j = m[-1]
        return date(int(a), int(mo), int(j))
    ans = [int(x) for x in re.findall(r"\b(20\d\d)\b", t)]
    an = ans[-1] if ans else an_defaut
    cand = []                                                  # (position, mois, jour) : la DERNIÈRE date du texte
    for m in re.finditer(r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+(\d{1,2}(?:\s*[–-]\s*\d{1,2})?)(?!\d)", t):
        cand.append((m.end(), MOIS[m.group(1)], int(re.findall(r"\d{1,2}", m.group(2))[-1])))
    for m in re.finditer(r"(?<!\d)(\d{1,2}(?:\s*[–-]\s*\d{1,2})?)\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*", t):
        cand.append((m.end(), MOIS[m.group(2)], int(re.findall(r"\d{1,2}", m.group(1))[-1])))
    if not cand:
        seuls = list(re.finditer(r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\b", t))
        if seuls and ans:
            cand.append((seuls[-1].end(), MOIS[seuls[-1].group(1)], 15))
    if not cand:
        return None
    _, mo, j = max(cand)
    for jj in (j, 30, 29, 28):
        try:
            return date(an, mo, min(j, jj))
        except ValueError:
            continue
    return None


def nombre(t: str) -> float | None:
    m = re.match(r"^\s*(\d{1,2}(?:[.,]\d+)?)\s*%?\s*$", t or "")
    return float(m.group(1).replace(",", ".")) if m else None


def sondages(html: str, an_defaut: int) -> list[dict]:
    """Toutes les lignes de sondage lisibles : {fin: date, valeurs: {colonne: %}}."""
    out = []
    for i_tab, g in enumerate(grilles(html)):
        if len(g) < 3 or any("aggregat" in norm(c) for c in g[0]):   # moyennes d'agrégateurs : pas des sondages
            continue
        entete, i_date = None, None
        for k, ligne in enumerate(g[:3]):
            for j, c in enumerate(ligne):
                if re.search(r"\b(dates?|fieldwork|conducted|administered|polling period|period)\b", norm(c)):
                    entete, i_date = k, j
                    break
            if entete is not None:
                break
        if entete is None:
            continue
        lus = []
        debut = entete
        while entete + 1 < len(g) and not any(nombre(c) is not None for c in g[entete + 1]):
            entete += 1                                        # entêtes sur plusieurs lignes
        noms = []
        for j in range(max(len(r) for r in g[debut:entete + 1])):
            pile = [r[j] for r in g[debut:entete + 1] if j < len(r) and r[j]]
            utiles = [x for x in pile if norm(x) not in GENERIQUES]
            nom = re.sub(r"\s*\[[^\]]*\]", "", (utiles or pile or [""])[-1]).strip()   # « ORÖ [hu] » → « ORÖ »
            noms.append("" if re.search(r"\d|%|^[<>]", nom) else nom)   # « 42–46% », vide : pas une colonne
        for ligne in g[entete + 1:]:
            if len(ligne) <= i_date:
                continue
            texte = " ".join(ligne[:max(i_date, 1) + 1])
            if re.search(r"\b(election|result|results|actual)\b", norm(texte)):
                continue
            fin = fin_terrain(ligne[i_date], an_defaut)
            vals = {noms[j]: v for j, c in enumerate(ligne) if j < len(noms) and j != i_date and noms[j]
                    and norm(noms[j]) not in GENERIQUES and (v := nombre(c)) is not None
                    and not re.search(r"\b(sample|size|margin|lead|error|others?|undecided|undec|blank|null|none|round)\b",
                                      norm(noms[j]))}
            if fin and len(vals) >= 2 and sum(vals.values()) <= 110:   # une ligne qui dépasse 100 % : pas un sondage
                lus.append({"fin": fin, "valeurs": vals, "table": i_tab})
        colonnes = {k for l in lus for k in l["valeurs"]}
        par_ligne = sorted(len(l["valeurs"]) for l in lus)
        if lus and len(colonnes) >= 4 and par_ligne[len(par_ligne) // 2] <= 2:
            continue                                           # matrice de duels de second tour : chaque ligne un duel
        out.extend(lus)
    return out


def moyennes(lignes: list[dict], jeu: str, table: int | None = None) -> dict[str, dict]:
    if table is not None:
        lignes = [l for l in lignes if l.get("table") == table]
    limite = date.fromisoformat(jeu) - timedelta(days=MARGE_JOURS)
    debut = date.fromisoformat(jeu) - timedelta(days=FRAICHEUR_JOURS)
    lignes = [l for l in lignes if l["fin"] >= debut]
    par: dict[str, list[tuple[date, float]]] = {}
    for l in lignes:
        if l["fin"] <= limite:
            for k, v in l["valeurs"].items():
                par.setdefault(k, []).append((l["fin"], v))
    out = {}
    for k, v in par.items():
        v = sorted(v)[-N_DERNIERS:]
        out[k] = {"moyenne": round(sum(x for _, x in v) / len(v), 2), "n": len(v), "dernier": v[-1][0].isoformat()}
    return out


def choisir_table(lignes: list[dict], jeu: str, sujet_: str, primaire_de_parti: bool) -> tuple[int | None, str | None]:
    """Un seul tableau par question (pas de mélange primaire / affiche générale / scénarios) : celui qui contient la
    colonne du sujet, avec le plus de sondages avant le jeu. Primaire d'un parti : les tableaux dont les noms portent
    une étiquette de parti (« (D) », « (R) ») sont des affiches générales, donc écartés."""
    limite = date.fromisoformat(jeu) - timedelta(days=MARGE_JOURS)
    debut = date.fromisoformat(jeu) - timedelta(days=FRAICHEUR_JOURS)
    cands = []
    for t in sorted({l.get("table") for l in lignes}, key=lambda x: (x is None, x)):
        ls = [l for l in lignes if l.get("table") == t and debut <= l["fin"] <= limite]
        if not ls:
            continue
        noms = sorted({k for l in ls for k in l["valeurs"]})
        if primaire_de_parti and sum(bool(SUFFIXE_PARTI.search(n)) for n in noms) * 2 >= len(noms):
            continue
        col = colonne(sujet_, noms)
        if col and sum(m["moyenne"] for m in moyennes(lignes, jeu, t).values()) <= 110:   # scénarios mêlés : refus
            cands.append((max(l["fin"] for l in ls), len(ls), t, col))
    if not cands:
        return None, None
    _, _, t, col = max(cands, key=lambda c: (c[0], c[1]))   # le tableau le plus récent, puis le plus fourni
    return t, col


# ------------------------------------------------------------------------------------------------- sujet et page
def sujet(titre: str) -> str:
    """Le candidat ou le parti dont parle la question (entre « Will » et le verbe)."""
    t = re.sub(r"^\s*(will|is|does)\s+", "", titre, flags=re.I)
    if re.match(r"(if|any|pro-|no|a|an)\b", t, re.I):         # conditionnel, ensemble de partis : pas un sujet unique
        return ""
    m = re.match(r"(.+?)\s+(win|wins|finish|advance|gain|receive|get|qualify|become|be elected|lead)\b", t, re.I)
    return (m.group(1) if m else t).strip(" ?")


def election(titre: str) -> str:
    """Le nom de l'élection tiré du titre (« 2026 Peruvian presidential election », « 2026 Texas Republican primary »)."""
    m = re.search(r"\b(20\d\d\s+[^?]*?(?:election|primary|by-election|referendum))(\s+in\s+(?:the\s+)?[A-Z][\w' ]+)?", titre, re.I)
    if m:
        return (m.group(1) + (m.group(2) or "")).strip()
    m = re.search(r"\b(next\s+[^?]*?(?:election|primary|by-election))", titre, re.I)   # « next Russian … election »
    if m:
        return m.group(1).strip()
    m = re.search(r".*\bthe\s+([^?]*?(?:election|primary|by-election))", titre, re.I)   # le DERNIER « the »
    return m.group(1).strip() if m else titre


def distinctifs(texte: str) -> set[str]:
    return {w for w in re.findall(r"[a-z][a-z'-]{3,}", norm(texte)) if w not in MOTS_VIDES}


def course(texte: str) -> str | None:
    t = norm(texte)
    if re.search(r"governor|gubernatorial", t):
        return "gouverneur"
    if re.search(r"\bsenate\b", t):
        return "senat"
    if re.search(r"\bhouse\b|congress|district|\b\d+(st|nd|rd|th)\b|chamber", t):
        return "chambre"
    if re.search(r"president", t):
        return "presidentielle"
    if re.search(r"attorney general|lieutenant|secretary of state|mayor|comptroller|treasurer", t):
        return "autre_poste"
    return None


def page_convient(titre_page: str, el: str, jeu: str = "2026-01-01") -> bool:
    """La page doit porter l'année de l'élection (sans année : « next », ou une année au moins égale à celle du jeu),
    le même type de course (gouverneur, Sénat, Chambre, présidentielle) et au moins un mot distinctif commun (pays,
    État, région, nom). Sans mot distinctif dans le nom de l'élection : refus (mieux vaut pas de sondage qu'un faux)."""
    ans, ans_p = re.findall(r"\b20\d\d\b", el), re.findall(r"\b(19\d\d|20\d\d)\b", titre_page)
    if ans and ans[0] not in titre_page:
        return False
    if not ans and not ("next" in norm(titre_page)
                        or (ans_p and all(int(jeu[:4]) <= int(a) <= int(jeu[:4]) + 1 for a in ans_p))):
        return False                                           # « prochaine » élection : l'année du jeu ou la suivante
    c_el, c_p = course(el), course(titre_page)
    if c_el and c_el != "presidentielle" and c_p != c_el:
        return False
    if c_el in (None, "presidentielle") and c_p in ("gouverneur", "senat", "chambre", "autre_poste"):
        return False
    d_el, d_p = distinctifs(el), distinctifs(titre_page)
    racines = lambda xs: {w[:5] for w in xs}                  # brazil / brazilian, peru / peruvian
    return bool(racines(d_el) & racines(d_p))


def colonne(sujet_: str, noms: list[str]) -> str | None:
    """Colonne du sujet : abréviation entre parenthèses, puis nom complet, puis prénom et nom, puis nom seul s'il est
    unique (deux Bolsonaro : pas de choix au hasard)."""
    abre = re.findall(r"\(([^)]+)\)", sujet_)
    for a in abre:
        for n in noms:
            if re.search(rf"\b{re.escape(norm(a))}\b", norm(n)):
                return n
    s = re.sub(r"^(the|a)\s+", "", re.sub(r"\(.*?\)", "", norm(sujet_)).strip())
    if not s:
        return None
    sigle = "".join(w[0] for w in re.findall(r"[a-z]+", s) if w not in ("of", "the", "and", "for", "de", "la", "du"))
    if len(sigle) >= 2:                                       # « United Russia » → UR, « New People » → NP
        ok = [n for n in noms if sigle in norm(n).split()]
        if len(ok) == 1:
            return ok[0]
    entiers = [n for n in noms if s and s in norm(n)]
    if len(entiers) == 1 or (entiers and len(s.split()) >= 2):
        return entiers[0]
    mots = [w for w in s.split() if len(w) > 2]
    if len(mots) >= 2:
        for n in noms:
            if all(re.search(rf"\b{re.escape(w)}\b", norm(n)) for w in (mots[0], mots[-1])):
                return n
    if len(mots) >= 2:                                        # « Flavio Bolsonaro » → « F. Bolsonaro PL »
        ok = [n for n in noms if re.search(rf"\b{re.escape(mots[0][0])}\.\s*{re.escape(mots[-1])}\b", norm(n))]
        if len(ok) == 1:
            return ok[0]
    for w in ([mots[-1]] if mots else []) + sorted((w for w in mots[:-1] if len(w) >= 4), key=len, reverse=True):
        ok = [n for n in noms if re.search(rf"\b{re.escape(w)}\b", norm(n))]   # « Luiz Inácio Lula da Silva » → « Lula PT »
        if len(ok) == 1:
            return ok[0]
    return None


def collecter() -> dict:
    import httpx
    import politesse
    carte = [o for o in json.loads(CARTE.read_text(encoding="utf-8"))["detail"] if set(o["regles"]) & REGLES_SONDAGES]
    out, pages = {}, {}
    with httpx.Client(headers={"User-Agent": politesse.UA}, timeout=60, follow_redirects=True) as c:
        for o in carte:
            el = election(o["titre"])
            if el not in pages:
                pages[el] = None
                for q in (f"Opinion polling for the {el}", el):
                    url = f"{API}/search/page"
                    if not politesse.autorise(c, url):
                        pages[el] = {"statut": "refusee"}
                        break
                    r = c.get(url, params={"q": q, "limit": 5})
                    if r.status_code != 200:
                        continue
                    for p in r.json().get("pages", []):
                        if not page_convient(p.get("title", ""), el, o["jeu"]):
                            continue
                        h = c.get(f"{API}/page/{p['key']}/html")
                        if h.status_code == 200 and (ls := sondages(h.text, int(o["jeu"][:4]))):
                            pages[el] = {"statut": "ok", "page": p["title"], "lignes": ls}
                            break
                    if pages[el]:
                        break
            info = pages[el] or {"statut": "introuvable"}
            if info.get("statut") != "ok":
                out[o["question"]] = {"election": el, "statut": info["statut"]}
                continue
            su = sujet(o["titre"])
            primaire = bool(re.search(r"\b(democratic|republican|dfl|labour|conservative)\b.*\bprimary\b", norm(o["titre"])))
            t, col = choisir_table(info["lignes"], o["jeu"], su, primaire)
            moy = moyennes(info["lignes"], o["jeu"], t) if t is not None else {}
            statut = "ok" if col else ("sujet_absent_des_tableaux" if moyennes(info["lignes"], o["jeu"])
                                       else "aucun_sondage_dans_les_90_jours_avant_le_jeu")
            out[o["question"]] = {"election": el, "statut": statut, "page": info["page"], "sujet": su,
                                  "colonne_sujet": col, "jeu": o["jeu"], "moyennes": moy}
    return {"source": "Wikipédia (en), CC BY-SA 4.0, via api.wikimedia.org ; seuls des nombres sont gardés",
            "questions": out}


def principal() -> int:
    r = collecter()
    SORTIE.write_text(json.dumps(r, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    qs = r["questions"].values()
    print(f"{len(r['questions'])} questions ; ok {sum(1 for q in qs if q.get('statut') == 'ok')} ; "
          f"avec la colonne du sujet {sum(1 for q in qs if q.get('colonne_sujet'))}")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
