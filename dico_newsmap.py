"""Troisième codeur pour la détection des pays dans les flux RSS : dictionnaire géographique de Newsmap
(bot 0.10.221, en ombre).

Décision d'auteur du 2026-11-17 (4 h 40), à la suite du tri des publications de l'IMAG : T. Lefort et J. Salmon
(peerannot, Computo 2024 ; thèse de T. Lefort, 2024) agrègent les étiquettes de plusieurs annotateurs sans vérité
connue (modèle de Dawid et Skene). Avec DEUX codeurs, on ne peut mesurer que leur accord : la fiabilité de chacun n'est
pas identifiable. Avec TROIS codeurs, un modèle à classe latente (vrai pays mentionné ou non) estime la sensibilité et
la spécificité de chacun, sans vérité de référence.

Source : K. Watanabe, paquet Newsmap (github.com/koheiw/newsmap, licence MIT), fichiers `dict/english.yml`,
`dict/french.yml`, `dict/german.yml` : pour chaque pays, nom, gentilés (avec joker *), capitale, parfois grandes villes.
Lu à chaque passage, jamais recopié.

RÉSERVE D'INDÉPENDANCE : le dictionnaire français de Newsmap a pour auteur Claude Grasland, comme le second codeur ;
les trois codeurs sont des dictionnaires et partagent des erreurs (« Georgia », « Jordan »). Le modèle à classe latente
suppose des erreurs indépendantes : ses estimations sont donc indicatives, pas des mesures de vérité.

Application : jokers « * » = suite de lettres ; sigles en majuscules (≤ 3 lettres, ex. « US ») en casse stricte,
le reste sans tenir compte de la casse (Newsmap, via quanteda, ignore la casse ; « us » ou « uk » minuscules ne sont
pas des pays).
"""
from __future__ import annotations

import re

URLS = {"en": "https://raw.githubusercontent.com/koheiw/newsmap/master/dict/english.yml",
        "fr": "https://raw.githubusercontent.com/koheiw/newsmap/master/dict/french.yml",
        "de": "https://raw.githubusercontent.com/koheiw/newsmap/master/dict/german.yml"}
_LIGNE = re.compile(r"^\s*'?([A-Z]{2})'?:\s*\[(.*)\]\s*$")
_CACHE: dict[str, str] = {}


def lire_yml(texte: str) -> dict[str, list[str]]:
    """{code ISO : [expressions]} d'un fichier de Newsmap (format : « 'FR': [France, Français*, Paris] »)."""
    out: dict[str, list[str]] = {}
    for ligne in texte.splitlines():
        m = _LIGNE.match(ligne)
        if m:
            out.setdefault(m.group(1), []).extend(e.strip().strip("'\"") for e in m.group(2).split(",") if e.strip())
    return out


def motif(expression: str) -> re.Pattern:
    joker = expression.endswith("*")
    e = expression.rstrip("*").strip()
    corps = re.escape(e).replace(r"\ ", r"\s+") + (r"\w*" if joker else "")
    sigle = len(e) <= 3 and e.isupper()
    return re.compile(r"(?<![\w-])" + corps + r"(?![\w-])", 0 if sigle else re.I)


def construire(dicos: list[dict[str, list[str]]]) -> list[tuple[re.Pattern, str]]:
    entrees = {}
    for d in dicos:
        for code, exprs in d.items():
            for e in exprs:
                if len(e.rstrip("*")) >= 2:
                    entrees.setdefault(e, code)
    return [(motif(e), c) for e, c in sorted(entrees.items(), key=lambda t: -len(t[0]))]


def detecter(texte: str, motifs: list[tuple[re.Pattern, str]]) -> set[str]:
    t, out = texte or "", set()
    for m, code in motifs:
        if m.search(t):
            out.add(code)
            t = m.sub(" ", t)
    return out


def charger(c, langues: tuple[str, ...] = ("en", "fr")) -> list[tuple[re.Pattern, str]]:
    """Liste vide si une source manque (les comptes à trois codeurs ne sont pas écrits ce jour)."""
    try:
        for l in langues:
            if l not in _CACHE:
                r = c.get(URLS[l], timeout=60)
                r.raise_for_status()
                _CACHE[l] = r.text
    except Exception:
        return []
    return construire([lire_yml(_CACHE[l]) for l in langues])


def classe_latente(motifs_comptes: dict[str, int], iterations: int = 500) -> dict:
    """Modèle à classe latente (Dawid et Skene, deux classes, trois codeurs binaires), ajusté par EM sur les comptes
    des huit profils de réponse « abc » (a = nous, b = Grasland-Toureille, c = Newsmap ; « 101 » = vu par nous et par
    Newsmap). Rend la prévalence et, pour chaque codeur, sensibilité et spécificité. Suppose des erreurs indépendantes."""
    prof = {k: float(v) for k, v in motifs_comptes.items() if v}
    if sum(prof.values()) <= 0:
        return {}
    pi, se, sp = 0.01, [0.8, 0.8, 0.8], [0.999, 0.999, 0.999]
    for _ in range(iterations):
        n1, a1, b0 = 0.0, [0.0] * 3, [0.0] * 3
        tot = sum(prof.values())
        for k, n in prof.items():
            x = [int(ch) for ch in k]
            l1, l0 = pi, 1 - pi
            for j in range(3):
                l1 *= se[j] if x[j] else 1 - se[j]
                l0 *= (1 - sp[j]) if x[j] else sp[j]
            w = l1 / (l1 + l0) if l1 + l0 > 0 else 0.0
            n1 += n * w
            for j in range(3):
                a1[j] += n * w * x[j]
                b0[j] += n * (1 - w) * (1 - x[j])
        n0 = tot - n1
        pi = n1 / tot
        se = [min(max(a1[j] / n1, 1e-6), 1 - 1e-6) if n1 else 0.5 for j in range(3)]
        sp = [min(max(b0[j] / n0, 1e-9), 1 - 1e-9) if n0 else 0.5 for j in range(3)]
    noms = ["nous", "grasland", "newsmap"]
    return {"prevalence": pi, **{n: {"sensibilite": se[j], "specificite": sp[j]} for j, n in enumerate(noms)}}
