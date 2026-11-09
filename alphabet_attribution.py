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
        hors_extraits = [c for c in nombres if c not in chiffres_cites] if extraits else []
        url = str(m.get("source_url") or "").strip()
        cle_url = re.sub(r"^https?://(www\.)?", "", url).split("#")[0].split("?")[0].rstrip("/").lower()
        url_retrouvee = (cle_url in textes_bas) if cle_url else None     # 0.8.3 (O1) : l'URL citée a-t-elle été vue ?
        mots_fait = [w for w in _normal(m.get("fait")).split() if len(w) >= 4]
        part_fait = sum(w in mots_corpus for w in mots_fait) / len(mots_fait) if mots_fait else None
        if not extraits and not nombres:
            attribue = None                    # rien de littéral à retrouver : non vérifiable, pas « attribué »
            non_verifiables += 1
        else:
            attribue = ((not extraits or retrouves > 0) and not absents and not hors_extraits
                        and (part_fait is None or part_fait >= 0.5))
            non_attribues += not attribue
        detail[cle] = {"extraits": len(extraits), "extraits_retrouves": retrouves, "chiffres_absents": absents,
                       "chiffres_hors_extraits": hors_extraits, "url_retrouvee": url_retrouvee,
                       "part_fait_retrouvee": round(part_fait, 2) if part_fait is not None else None,
                       "attribue": attribue}
    return {"mots": len(dossier["mots"]), "non_attribues": non_attribues, "non_verifiables": non_verifiables,
            "detail": detail,
            "lecture": "diagnostic sans modèle ; un faux positif est possible quand la recherche résume au lieu de citer"}
