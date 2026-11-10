"""Bot 0.10.8 : pépinière de l'arbre et test de reconstruction de la matrice."""
from __future__ import annotations

import asyncio
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import alphabet_pipeline as ap  # noqa: E402
import pepiniere as pp  # noqa: E402
import reconstruction_matrice as rm  # noqa: E402


def ligne(qid, prog, ev="SEUIL@7 apparait"):
    return {"question_id": qid, "bras": {"C": {"evenement": ev, "traduction": {"programme": prog}}}}


class Tests(unittest.TestCase):
    def test_pepiniere(self):
        reg = Path(tempfile.mkdtemp(prefix="registre-pep-"))
        nouvelle = {"instruction": "lien", "de": "ÉMERGENCE@7", "vers": "cible", "extrait": "x"}   # EME → SEU : absente
        existante = {"instruction": "lien", "de": "CROISSANCE@7", "vers": "cible", "extrait": "y"}  # CRO → SEU : présente
        bloque = {"instruction": "bloque", "de": "CONTRAINTE@7", "extrait": "z"}                     # CTR → SEU : présente
        lignes = [ligne(str(i), [dict(nouvelle, source=f"https://www.site{i % 2}.org/a"), existante, bloque])
                  for i in range(3)]
        (reg / "journal-bot.jsonl").write_text("\n".join(json.dumps(l_) for l_ in lignes) + "\n", encoding="utf-8")
        r = pp.pepiniere(reg)
        self.assertEqual(r["lignes_lues"], 3)
        c = r["candidates"][0]
        self.assertEqual((c["instruction"], c["de"], c["vers"]), ("lien", "EME", "SEU"))
        self.assertEqual((c["questions"], c["sources_distinctes"]), (3, 2))
        self.assertTrue(c["seuil_atteint"])
        self.assertEqual([(x["de"], x["dans_la_matrice"]) for x in r["confirmations"]], [("CRO", "M")])
        self.assertEqual([x["de"] for x in r["contre_indications"]], ["CTR"])
        lignes[0]["bras"]["C"]["traduction"]["programme"] = [dict(nouvelle, source="")]  # une source de moins
        (reg / "journal-bot.jsonl").write_text("\n".join(json.dumps(l_) for l_ in lignes[:2]) + "\n", encoding="utf-8")
        self.assertFalse(pp.pepiniere(reg)["candidates"][0]["seuil_atteint"])           # 2 questions : sous le seuil

    def test_reconstruction(self):
        m = ap._moteur()
        mat = m.P["matrice"]
        noms = m.NOMS
        parfait = {noms[a]: {noms[b]: i for b, i in d.items()} for a, d in mat.items()}

        async def llm_parfait(c):
            self.assertNotIn("λ", c)
            self.assertNotIn("Voisines", c)
            return "```json\n" + json.dumps(parfait, ensure_ascii=False) + "\n```"
        r = asyncio.run(rm.lancer(llm_parfait, 3))
        cp = r["comparaison"]["accord_presence"]
        self.assertEqual((cp["communes"], cp["seulement_modele"], cp["seulement_matrice"]), (66, 0, 0))
        self.assertAlmostEqual(cp["kappa"], 1.0)
        self.assertEqual(r["comparaison"]["accord_force_sur_communes"]["identique"], 66)

        async def llm_vide(c):
            return "{}"
        r0 = asyncio.run(rm.lancer(llm_vide, 2))
        self.assertEqual(r0["comparaison"]["accord_presence"]["communes"], 0)
        self.assertEqual(len(r0["comparaison"]["a_reexaminer"]["dans_la_matrice_jamais_reconstruites"]), 66)


if __name__ == "__main__":
    unittest.main()
