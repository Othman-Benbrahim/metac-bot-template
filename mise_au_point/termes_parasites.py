"""Tri des mots du rattachement, au fil de l'eau (décision de l'auteur, 2026-11-26, 11 h 53 : « pas le choix de faire
un tri manuel au fil de l'eau ; un dispositif qui filtre les mots parasites et en propose de nouveaux, par tâtonnement »).

Sans modèle de langue. Sur les titres des questions (corpus résolu et questions du bot) :
1. PARASITES PROBABLES. Un terme est suspect quand
   - il est générique : il rattache beaucoup de questions dispersées sur beaucoup de fiches ; ou
   - il est isolé : dans la plupart des questions qu'il rattache, il est le seul à pointer vers sa fiche, alors que les
     autres termes de la question pointent ailleurs (le titre parle d'autre chose).
2. TERMES NOUVEAUX. Groupes de 1 à 3 mots fréquents dans les titres que rien ne rattache, avec la fiche la plus
   fréquente chez les questions rattachées où ils apparaissent (suggestion seulement).
Sorties (listes de l'auteur, lecteur-local/listes) : parasites-proposes.txt et termes-proposes.txt. Chaque ligne
commence par « ? ». L'auteur met « - » (retirer : le rattachement ne le lit plus) ou « + » (garder : plus jamais
reproposé) ; pour les termes nouveaux, « + » avec une fiche, à recopier dans valides.txt. Les lignes déjà tranchées
sont conservées telles quelles.
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ICI = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ICI))
from mise_au_point.lecture_mecanique import LISTES, _motif, termes_routage  # noqa: E402

MOTS_VIDES = set("""will the a an of in on to by for and or be is are was before after at as from with than that this
its it his her their which who what when there any no not more less least most new first last into during about over
under between against within without per via end year years month months day days 2024 2025 2026 2027 2028 jan feb mar
apr may jun jul aug sep oct nov dec january february march april june july august september october november december
win wins won reach reaches out next top have has had become becomes finish hit hits get gets make makes take takes
high low higher lower above below least than say says said announce announces happen happens remain remains still
again ever officially publicly least least people called
""".split())


def titres() -> list[str]:
    T = []
    for f, cle in ((ICI / "registre/jugement-questions.jsonl", "titre"), (ICI / "registre/journal-bot.jsonl", "titre")):
        if f.exists():
            for l in f.read_text(encoding="utf-8").splitlines():
                try:
                    t = json.loads(l).get(cle)
                except ValueError:
                    continue
                if t:
                    T.append(t)
    return sorted(set(T))


def _deja(nom: str) -> dict:
    f = LISTES / nom
    out = {}
    if f.exists():
        for l in f.read_text(encoding="utf-8").splitlines():
            p = [x.strip() for x in l.split("|")]
            if len(p) >= 2 and p[0] in "+-":
                out[p[1]] = l
    return out


def analyser(T: list[str], termes: dict) -> tuple[list, list]:
    fiche = lambda c: c.split(":")[0]
    motifs = {t: _motif(t) for t in termes}
    par_q = []
    for t in T:
        tt = [x for x, m in motifs.items() if m.search(t)]
        par_q.append((t, tt))
    n = Counter(); fiches = defaultdict(Counter); isole = Counter(); ex = defaultdict(list)
    for t, tt in par_q:
        for x in tt:
            fx = {fiche(c) for c in termes[x]}
            autres = {fiche(c) for y in tt if y != x for c in termes[y]}
            n[x] += 1
            for f in fx:
                fiches[x][f] += 1
            if autres and not (fx & autres):
                isole[x] += 1
                if len(ex[x]) < 2:
                    ex[x].append(t)
    N = max(1, len(T))
    par = []
    for x in n:
        generique = n[x] >= 40 and n[x] / N >= 0.01
        part_isole = isole[x] / n[x]
        if (generique and part_isole >= 0.5) or (n[x] >= 5 and part_isole >= 0.8):
            par.append((x, n[x], round(part_isole, 2), sorted(termes[x]), ex[x]))
    par.sort(key=lambda z: (-z[2], -z[1]))
    # termes nouveaux
    libres = [t for t, tt in par_q if not tt]
    gram = Counter()
    for t in libres:
        w = [m.lower() for m in re.findall(r"[A-Za-zÀ-ÿ][\w'-]+", t)]
        vus = set()
        for k in (1, 2, 3):
            for i in range(len(w) - k + 1):
                g = w[i:i + k]
                if g[0] in MOTS_VIDES or g[-1] in MOTS_VIDES or any(len(m) < 3 for m in g):
                    continue
                vus.add(" ".join(g))
        gram.update(vus)
    from mise_au_point.lecture_mecanique import routage
    connus = {t.lower() for t in termes} | {n.lower() for n in routage()[2]}   # pays : rattachés par ailleurs
    sugg = []
    for g, c in gram.most_common(400):
        if c < 8 or g in connus:
            continue
        m = _motif(g)
        f = Counter(fiche(cc) for t, tt in par_q if tt and m.search(t) for y in tt for cc in termes[y])
        sugg.append((g, c, f.most_common(1)[0][0] if f else "?"))
        if len(sugg) >= 60:
            break
    return par, sugg


def ecrire(par: list, sugg: list) -> None:
    d1, d2 = _deja("parasites-proposes.txt"), _deja("termes-proposes.txt")
    L = ["# Parasites probables du rattachement (mise_au_point/termes_parasites.py). « - » retire, « + » garde.",
         "# état | terme | questions rattachées | part isolée | compartiments | exemples"]
    L += list(d1.values())
    L += [f"? | {x} | {k} | {pi} | {';'.join(c)} | {' // '.join(e)}" for x, k, pi, c, e in par if x not in d1]
    (LISTES / "parasites-proposes.txt").write_text("\n".join(L) + "\n", encoding="utf-8")
    M = ["# Termes nouveaux proposés (titres non rattachés). « + » avec une fiche, puis recopier dans valides.txt ;",
         "# « - » écarte. état | terme | questions non rattachées | fiche suggérée"]
    M += list(d2.values())
    M += [f"? | {g} | {c} | {f}" for g, c, f in sugg if g not in d2]
    (LISTES / "termes-proposes.txt").write_text("\n".join(M) + "\n", encoding="utf-8")


if __name__ == "__main__":
    T = titres()
    par, sugg = analyser(T, termes_routage())
    ecrire(par, sugg)
    print(f"{len(T)} titres ; {len(par)} parasites probables ; {len(sugg)} termes nouveaux proposés ; listes : {LISTES}")
