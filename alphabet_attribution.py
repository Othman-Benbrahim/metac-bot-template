"""Contrôle d'attribution (0.9.3) : vérifier SANS modèle que les faits cités par la lecture viennent des résultats.

Sorti d'alphabet_pipeline.py pour être le SEUL fichier modifiable par la boucle d'amélioration du banc d'essai
`banc/attribution/` (juge et corpus verrouillés). Toute modification se mesure avec :

    uv run python banc/attribution/juge.py
"""
from __future__ import annotations

import re
import unicodedata


def _normal(texte: str) -> str:
    t = unicodedata.normalize("NFD", str(texte or "")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", t).strip()


def _chiffres(texte: str) -> list[str]:
    """Nombres d'au moins deux chiffres, séparateurs de milliers retirés (« 2 295 », « 2,295 » → 2295). 0.8.0 (audit
    m-02) : les décimales sont gardées et normalisées (« 10,4 » et « 10.4 » → 10.4 ; « 6,3 » → 6.3)."""
    t = re.sub(r"(?<=\d)[\s\u00a0\u202f.,](?=\d{3}\b)", "", str(texte or ""))
    t = re.sub(r"(?<=\d),(?=\d)", ".", t)
    nombres = set()
    for n in re.findall(r"\d+(?:\.\d+)?", t):
        n = n.rstrip("0").rstrip(".") if "." in n else n
        if len(n.replace(".", "")) >= 2:
            nombres.add(n)
    return sorted(nombres)


# Noms qui changent d'une langue à l'autre : lexique GÉNÉRIQUE (pays, villes, gentilés, mois), jamais taillé pour un
# corpus. Clé : forme française normalisée ; valeur : formes anglaises admises.
LEXIQUE = {
    "etats unis": ["us", "usa", "united states", "america", "american"], "americain": ["us", "american"],
    "americaine": ["us", "american"], "royaume uni": ["uk", "britain", "united kingdom", "british"],
    "britannique": ["uk", "british", "britain"], "angleterre": ["england", "english"], "anglais": ["english"],
    "anglaise": ["english"], "ecosse": ["scotland", "scottish"], "ecossais": ["scottish", "scotland"],
    "allemagne": ["germany", "german"], "allemand": ["german"], "allemande": ["german"], "france": ["france", "french"],
    "francais": ["french"], "francaise": ["french"], "espagne": ["spain", "spanish"], "italie": ["italy", "italian"],
    "italien": ["italian"], "russie": ["russia", "russian"], "russe": ["russian"], "chine": ["china", "chinese"],
    "chinois": ["chinese"], "japon": ["japan", "japanese"], "inde": ["india", "indian"], "indien": ["indian"],
    "indienne": ["indian"], "israel": ["israel", "israeli"], "israelien": ["israeli"], "egypte": ["egypt", "egyptian"],
    "iran": ["iran", "iranian"], "irak": ["iraq", "iraqi"], "syrie": ["syria", "syrian"], "turquie": ["turkey", "turkish"],
    "ukraine": ["ukraine", "ukrainian"], "pologne": ["poland", "polish"], "australie": ["australia", "australian"],
    "australien": ["australian"], "australienne": ["australian"], "canada": ["canada", "canadian"],
    "mexique": ["mexico", "mexican"], "bresil": ["brazil", "brazilian"], "argentine": ["argentina"],
    "colombie": ["colombia"], "arabie saoudite": ["saudi arabia", "saudi"], "coree": ["korea", "korean"],
    "afrique du sud": ["south africa"], "europe": ["europe", "european", "eu"],
    "union europeenne": ["eu", "european union"], "europeen": ["european", "eu"], "europeenne": ["european", "eu"],
    "londres": ["london"], "moscou": ["moscow"], "pekin": ["beijing"], "bruxelles": ["brussels"], "geneve": ["geneva"],
    "edimbourg": ["edinburgh"], "californie": ["california"],
    "janvier": ["january", "jan"], "fevrier": ["february", "feb"], "mars": ["march", "mar"], "avril": ["april", "apr"],
    "mai": ["may"], "juin": ["june", "jun"], "juillet": ["july", "jul"], "aout": ["august", "aug"],
    "septembre": ["september", "sep", "sept"], "octobre": ["october", "oct"], "novembre": ["november", "nov"],
    "decembre": ["december", "dec"],
    # familles politiques (noms de partis traduits)
    "verts": ["greens", "green"], "travaillistes": ["labour"], "travailliste": ["labour"],
    "conservateurs": ["conservatives", "conservative", "tories", "tory"], "liberaux": ["liberals", "liberal"],
    "socialistes": ["socialists", "socialist"], "republicains": ["republicans", "republican", "gop"],
    "democrates": ["democrats", "democratic"],
}
# Mots qu'une phrase française met souvent en majuscule sans qu'ils soient des noms propres vérifiables (titres,
# institutions génériques, jours) : ignorés comme ancres. Liste générique.
MAJUSCULES_COMMUNES = set("""le la les un une des du de il elle ils elles on selon mais et ou lundi mardi mercredi jeudi
vendredi samedi dimanche m mme monsieur madame sir lord lady dr president presidente premier premiere ministre ministere
ministres gouvernement parlement assemblee senat chambre communes reine roi prince cour conseil commission agence
reserve banque bourse etat etats federal federale federales nation nations union parti cabinet office tribunal justice
police armee nord sud est ouest""".split())


def _noms_propres(fait: str) -> list[str]:
    """Les noms propres d'un fait : suites de mots à majuscule hors début de phrase (et sigles), normalisées."""
    noms = []
    for m in re.finditer(r"(?<![.!?]\s)(?<!^)\b([A-ZÉÈÊÀÂÎÔÛÇ][\w'’-]+(?:\s+(?:[A-ZÉÈÊÀÂÎÔÛÇ][\w'’-]+))*)", fait):
        brut = re.sub(r"^(?:[LlDd]['’])", "", m.group(1))
        if re.search(r"minist[eè]re\s+(?:du|de la|de l['’]|des)\s*$", fait[:m.start(1)], re.I):
            continue                      # « ministère du Plan » : nom d'institution traduit
        if re.fullmatch(r"[A-Z]{2,3}", brut):
            continue                      # sigle court : souvent différent d'une langue à l'autre (SEC, ONU/UN)
        n = _normal(brut)
        if n in LEXIQUE:
            noms.append(n)                # nom traduit connu (« États-Unis ») : gardé entier
            continue
        if len(n.split()) >= 2 and not any(w in LEXIQUE for w in n.split()):
            noms.append(n)                # nom composé (« Cabinet Office », « Sir Edward Heath ») : gardé entier
            continue
        mots = [w for w in n.split() if w not in MAJUSCULES_COMMUNES and w.rstrip("s") not in MAJUSCULES_COMMUNES
                and len(w) >= 2]
        if mots:
            noms.append(" ".join(mots))
    return noms


MOIS_FR = ["janvier", "fevrier", "mars", "avril", "mai", "juin", "juillet", "aout", "septembre", "octobre", "novembre",
           "decembre"]
MOIS_EN = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november",
           "december"]


def _unites(texte: str, langue_fr: bool) -> set[str]:
    """Nombres liés à une unité, à UN chiffre compris : « 7 % » → « 7% » ; « 5 mai » / « 5 May » / « May 5 » → « 5/5 ».
    Les nombres nus d'un seul chiffre sont trop fréquents pour servir d'ancre ; liés à une unité, ils en sont une."""
    n = _normal(texte)
    out = set()
    t = re.sub(r"(?<=\d),(?=\d)", ".", str(texte or ""))
    for x in re.findall(r"(\d+(?:\.\d+)?)\s*(?:%|pour ?cent|per ?cent)", t):
        out.add(x.rstrip("0").rstrip(".") + "%" if "." in x else x + "%")
    mois = MOIS_FR if langue_fr else MOIS_EN
    for i, m in enumerate(mois, 1):
        for j in re.findall(rf"\b(\d{{1,2}})(?:er|st|nd|rd|th)? {m}\b", n):
            out.add(f"{int(j)}/{i}")
        if not langue_fr:
            for j in re.findall(rf"\b{m} (\d{{1,2}})\b", n):
                out.add(f"{int(j)}/{i}")
    return out


def _nom_present(nom: str, corpus: str) -> bool:
    c_ = f" {corpus} "
    if any(f" {c} " in c_ for c in [nom] + LEXIQUE.get(nom, [])):
        return True
    return all(any(f" {c} " in c_ for c in [w] + LEXIQUE.get(w, [])) for w in nom.split())


def controle_attribution(dossier: dict | None, textes: str | None) -> dict | None:
    """0.5.2, idée reprise d'EnVrai (contrôles locaux du repérage) : vérifier SANS modèle que ce que la lecture cite
    vient bien des résultats de recherche. Pour chaque mot ancré : (1) chaque extrait du passage se retrouve-t-il dans
    les résultats (70 % au moins de ses mots de quatre lettres ou plus) ? (2) chaque nombre du fait y figure-t-il ?
    Diagnostic scellé au registre : il ne change ni la lecture ni le calcul. Un mot sans extrait retrouvé, ou avec un
    nombre absent des résultats, est « non attribué » : la règle « ne cite que des faits trouvés » n'est pas tenue."""
    if not dossier or not dossier.get("mots") or textes is None:
        return None
    corpus = _normal(textes)
    mots_corpus = set(corpus.split())
    chiffres_corpus = set(_chiffres(textes))
    textes_bas = str(textes).lower()
    unites_corpus = _unites(textes, False) | _unites(textes, True)
    detail, non_attribues, non_verifiables = {}, 0, 0
    # 0.8.0 (audit M-04) : il ne suffit plus que les extraits existent et que les nombres du fait figurent QUELQUE
    # PART : les nombres du fait doivent être dans les extraits CITÉS, et le fait lui-même doit se retrouver dans le
    # corpus (la moitié au moins de ses mots de quatre lettres ou plus).
    for m in dossier["mots"]:
        cle = f"{m.get('carte')}@{m.get('strate')}"
        extraits = [x.get("extrait") for x in (m.get("passage") or []) if isinstance(x, dict) and x.get("extrait")]
        retrouves = 0
        for e in extraits:
            ne = _normal(e)
            longs = [w for w in ne.split() if len(w) >= 4]
            if (ne and ne in corpus) or (longs and sum(w in mots_corpus for w in longs) / len(longs) >= 0.7):
                retrouves += 1
        nombres = _chiffres(m.get("fait"))
        absents = [c for c in nombres if c not in chiffres_corpus]
        chiffres_cites = set(_chiffres(" ".join(extraits)))
        # tous les nombres du fait doivent être dans les résultats ; au moins UN dans les extraits cités (un extrait
        # court ne porte pas tous les nombres d'un fait qui en résume plusieurs)
        hors_extraits = [c for c in nombres if c not in chiffres_cites] if extraits else []
        hors_extraits = hors_extraits if (extraits and nombres and len(hors_extraits) == len(nombres)) else []
        unites = _unites(str(m.get("fait") or ""), True)
        unites_absentes = sorted(unites - unites_corpus)
        noms = _noms_propres(str(m.get("fait") or ""))
        noms_absents = [n for n in noms if not _nom_present(n, corpus)]
        url = str(m.get("source_url") or "").strip()
        cle_url = re.sub(r"^https?://(www\.)?", "", url).split("#")[0].split("?")[0].rstrip("/").lower()
        url_retrouvee = (cle_url in textes_bas) if cle_url else None     # 0.8.3 (O1) : l'URL citée a-t-elle été vue ?
        mots_fait = [w for w in _normal(m.get("fait")).split() if len(w) >= 4]
        part_fait = sum(w in mots_corpus for w in mots_fait) / len(mots_fait) if mots_fait else None
        specifiques = [c for c in nombres if not re.fullmatch(r"(19|20)\d\d", c)] + [n for n in noms if n not in LEXIQUE] \
            + sorted(unites)
        if not extraits and not specifiques:
            attribue = None                    # rien de littéral à retrouver : non vérifiable, pas « attribué »
            non_verifiables += 1
        else:
            attribue = ((not extraits or retrouves > 0) and not absents and not hors_extraits and not noms_absents
                        and not unites_absentes)
            non_attribues += not attribue
        detail[cle] = {"extraits": len(extraits), "extraits_retrouves": retrouves, "chiffres_absents": absents,
                       "chiffres_hors_extraits": hors_extraits, "noms_absents": noms_absents,
                       "unites_absentes": unites_absentes,
                       "url_retrouvee": url_retrouvee,
                       "part_fait_retrouvee": round(part_fait, 2) if part_fait is not None else None,
                       "attribue": attribue}
    return {"mots": len(dossier["mots"]), "non_attribues": non_attribues, "non_verifiables": non_verifiables,
            "detail": detail,
            "lecture": "diagnostic sans modèle ; un faux positif est possible quand la recherche résume au lieu de citer"}
