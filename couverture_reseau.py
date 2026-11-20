"""Couverture du réseau d'acteurs par écosystème, avec le moins d'interprétation possible (2026-11-20, 18 h 45 ; demande
de l'auteur : « fais-le, mais avec le moins de biais possible »). Aucune lecture des issues ; aucun choix au cas par cas.

Règles, dans l'ordre :
1. La question entre dans une fiche par les motifs existants (classes_homologues.classe) : on garde cette fiche.
2. Sinon, par le réseau lui-même : chaque acteur reçoit l'écosystème MAJORITAIRE des questions classées où il apparaît
   dans l'échantillon de mise au point (2015-2023), s'il y apparaît au moins 3 fois et que la majorité fait au moins
   60 %. La question prend ce type si tous ses acteurs ainsi rattachés donnent le même type.
3. Sinon, si l'un de ses acteurs est un pays suivi par la collecte UCDP (25 pays en conflit armé, liste fixée le
   2026-11-17 pour d'autres bancs) : type « conflit » (EXTENSION déclarée : le sens a été observé sur cinq écosystèmes
   de conflit, pas sur ces pays).
4. Sinon : hors du test (aucun sens prédit).

Types : « conflit » (russie-ukraine, guerre-levant, iran-nucleaire, securite-europeenne, rivalite-sino-americaine),
« politique » (politique-americaine) ; tout autre écosystème : pas de sens prédit.
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from functools import lru_cache
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "mise_au_point"))
import classes_homologues as ch
import reseau_observation as ro

CONFLIT = {"russie-ukraine", "guerre-levant", "iran-nucleaire", "securite-europeenne", "rivalite-sino-americaine"}
POLITIQUE = {"politique-americaine"}
# pays de la collecte UCDP (registre/ucdp-cellules.csv.gz), noms de la DPI
UCDP = {"Afghanistan", "Burkina Faso", "Cameroon", "Colombia", "Congo (DRC)", "Ethiopia", "Haiti", "India", "Iraq",
        "Israel", "Kenya", "Mali", "Mexico", "Mozambique", "Myanmar", "Niger", "Nigeria", "Pakistan", "Philippines",
        "Somalia", "South Sudan", "Sudan", "Syria", "Ukraine", "Yemen"}


def type_de(fiche: str | None) -> str | None:
    return "conflit" if fiche in CONFLIT else "politique" if fiche in POLITIQUE else ("autre" if fiche else None)


@lru_cache(maxsize=1)
def ecosysteme_des_acteurs() -> dict[str, str]:
    par = defaultdict(Counter)
    for l in Path("registre/mise-au-point/questions.jsonl").read_text(encoding="utf-8").splitlines():
        d = json.loads(l)
        if d["source"] not in ("metaculus", "gjopen", "cset"):
            continue
        k = ch.classe(d["titre"], d.get("horizon", 30))
        if k:
            for a in ro.acteurs(d["titre"]):
                par[a][k["fiche"]] += 1
    out = {}
    for a, c in par.items():
        f, n = c.most_common(1)[0]
        if sum(c.values()) >= 3 and n / sum(c.values()) >= 0.6:
            out[a] = f
    return out


def type_question(titre: str, horizon) -> tuple[str | None, str]:
    k = ch.classe(titre, horizon or 30)
    if k:
        return type_de(k["fiche"]), "fiche"
    a = ro.acteurs(titre)
    eco = ecosysteme_des_acteurs()
    types = {type_de(eco[x]) for x in a if x in eco}
    if len(types) == 1:
        return types.pop(), "réseau"
    if not types and a & UCDP:
        return "conflit", "extension UCDP"
    return None, "hors test"
