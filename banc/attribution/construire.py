"""Construit le corpus VERROUILLÉ du banc d'attribution, de façon déterministe, à partir de :
  - articles.json : 50 articles réels de la BBC (jeu public BBC News, 2004-2005), une phrase chiffrée choisie par article ;
  - paraphrases.json : une paraphrase française FIDÈLE de chaque phrase (le bot cite en français des sources souvent
    anglaises).
Étiquettes sûres par construction (6 cas par article) :
  P1 attribuable  : la paraphrase, avec un extrait verbatim de la phrase source ;
  P2 attribuable  : la paraphrase, sans extrait ;
  N1 non attribuable : la paraphrase dont un nombre est changé, avec l'extrait réel ;
  N2 non attribuable : la paraphrase dont un nom propre est remplacé par un nom absent des résultats ;
  N3 non attribuable : la paraphrase d'un AUTRE article (absent des résultats), avec un extrait réel de celui-ci ;
  N4 non attribuable : la paraphrase d'un autre article, sans extrait.
Les résultats de recherche d'un cas = l'article source + un article de bruit, au format des résultats du bot.
Articles 0 à 34 : partie de travail ; 35 à 49 : partie CACHÉE (corpus-cache.json), jamais montrée à l'agent qui
modifie alphabet_attribution.py ; elle ne sert qu'à la vérification finale.

    python banc/attribution/construire.py
"""
import json
import random
import re
from pathlib import Path

ICI = Path(__file__).parent
NB_TRAVAIL = 35


def resultat(a):
    return f"[2005] {a['titre']} — https://www.bbc.co.uk/news/{a['id']}\n{a['corps']}"


def extrait(phrase):
    mots = phrase.rstrip(".").split()
    i = next((k for k, w in enumerate(mots) if re.search(r"\d", w)), len(mots) // 2)
    debut = max(0, min(i - 3, len(mots) - 8))
    return " ".join(mots[debut:debut + 8])


def changer_nombre(texte, rnd):
    m = list(re.finditer(r"\d+(?:[ ,.]\d+)*", texte))
    if not m:
        return None
    x = rnd.choice(m)
    brut = x.group()
    chiffres = [c for c in brut if c.isdigit()]
    k = max(i for i, c in enumerate(brut) if c.isdigit())
    if len(chiffres) == 1 or rnd.random() < 0.5:
        nouveau = brut[:k] + str((int(brut[k]) + rnd.randint(2, 7)) % 10) + brut[k + 1:]
    else:
        j = min(i for i, c in enumerate(brut) if c.isdigit())
        nouveau = brut[:j] + str((int(brut[j]) % 9) + 1 + (1 if brut[j] == str((int(brut[j]) % 9) + 1) else 0))[-1] + brut[j + 1:]
    return texte[:x.start()] + nouveau + texte[x.end():] if nouveau != brut else None


NOMS = re.compile(r"(?<!^)(?<![.!?] )\b([A-ZÉ][a-zéèêàâîôûç]{3,}(?:[- ][A-ZÉ][a-zéèêàâîôûç]+)*)\b")


def changer_nom(texte, autres_noms, resultats, rnd):
    noms = [m for m in NOMS.finditer(texte)]
    noms = [m for m in noms if m.group(1) in resultats]
    cands = [n for n in autres_noms if n.lower() not in resultats.lower()]
    if not noms or not cands:
        return None
    m = rnd.choice(noms)
    return texte[:m.start(1)] + rnd.choice(cands) + texte[m.end(1):]


def construire():
    rnd = random.Random(20261110)
    art = json.loads((ICI / "articles.json").read_text(encoding="utf-8"))
    par = json.loads((ICI / "paraphrases.json").read_text(encoding="utf-8"))
    assert len(art) == len(par)
    tous_noms = sorted({m.group(1) for p in par for m in NOMS.finditer(p)})
    travail, cache = [], []
    for i, a in enumerate(art):
        bruit = art[(i + 7) % len(art)]
        res = resultat(a) + "\n\n" + resultat(bruit)
        url = f"https://www.bbc.co.uk/news/{a['id']}"
        ext = extrait(a["phrase"])
        autre = (i + 13) % len(art)
        while autre == (i + 7) % len(art):
            autre = (autre + 1) % len(art)
        cas = [("P1", True, par[i], [ext]), ("P2", True, par[i], [])]
        n1 = changer_nombre(par[i], rnd)
        if n1:
            cas.append(("N1", False, n1, [ext]))
        n2 = changer_nom(par[i], tous_noms, res, rnd)
        if n2:
            cas.append(("N2", False, n2, [ext]))
        cas += [("N3", False, par[autre], [ext]), ("N4", False, par[autre], [])]
        for genre, attribuable, fait, extraits in cas:
            c = {"id": f"{i:02d}-{genre}", "article": i, "genre": genre, "attribuable": attribuable,
                 "fait": fait, "extraits": extraits, "source_url": url, "resultats": res}
            (travail if i < NB_TRAVAIL else cache).append(c)
    (ICI / "corpus-travail.json").write_text(json.dumps(travail, ensure_ascii=False, indent=1), encoding="utf-8")
    (ICI / "corpus-cache.json").write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")
    return travail, cache


if __name__ == "__main__":
    t, c = construire()
    print(f"{len(t)} cas de travail, {len(c)} cas cachés")
