"""Plan B des acteurs de veto : nombre d'accords nécessaires, question par question, par règles écrites sur le titre
(préenregistrement preenregistrements/accords-requis.md, 2026-11-20). Règles fixées avant toute lecture des issues ;
ordre fixe, la première règle qui s'applique décide. Aucun modèle de langue.

Tranches : « 1 » (un décideur seul : agence, entreprise, tribunal, dirigeant, gouvernement, une chambre),
« 2 » (deux accords : nomination confirmée, ratification par un pays, deux chambres, accord entre deux parties),
« 3+ » (trois accords ou plus : loi complète, accord entre trois parties ou plus, décision à l'unanimité de l'UE ou de
l'OTAN, ratification par plusieurs États).
"""
from __future__ import annotations

import re

import acteurs_de_veto as av

R = lambda s: re.compile(s, re.I)
UNANIMITE = R(r"\b(EU|European Union|European Council|NATO|all (EU|NATO) members|unanimous|unanimity)\b.*"
              r"\b(impose|lift|adopt|approve|agree|admit|accession|join|sanction|extend|renew|ratif)")
LOI = R(r"\b(become law|signed into law|sign\w* .{0,40}\binto law|enact\w*|be enacted)\b")
DEUX_CHAMBRES = R(r"\bboth (houses|chambers)\b|\bcongress (pass|approve)")
CONFIRMATION = R(r"\bconfirm(ed)? (by the senate|as)\b|\bsenate (confirm|vote to confirm)|\bratif")
UNILATERAL = R(r"\b(announce\w*|withdraw\w*|rule|rules|ruling|exit|leave|quit|suspend\w*|terminate\w*|declare\w*)\b")
ACCORD = R(r"\b(agreement|agree|deal|treaty|ceasefire|cease-fire|truce|peace (deal|agreement|talks)|normaliz\w*"
           r"|diplomatic relations|meet|summit|negotiat\w*)\b")


def accords(titre: str) -> str:
    t = titre or ""
    if UNANIMITE.search(t):
        return "3+"
    if LOI.search(t):
        return "3+" if av.pays(t) <= {"USA"} or DEUX_CHAMBRES.search(t) else "2"
    if DEUX_CHAMBRES.search(t):
        return "2"
    if CONFIRMATION.search(t):
        return "3+" if re.search(r"\ball\b|\bevery\b|\bmember (states|countries)\b", t, re.I) else "2"
    if UNILATERAL.search(t):
        return "1"
    if ACCORD.search(t):
        n = len(av.pays(t))
        return "3+" if n >= 3 else "2"
    return "1"
