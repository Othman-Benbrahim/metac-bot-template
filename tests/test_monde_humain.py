"""0.10.36 : lecture réfléchie (perturbation « reflexion ») et référence humaine (export, notation)."""
from __future__ import annotations

import asyncio
import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import alphabet_pipeline as ap  # noqa: E402
import monde_synthetique as ms  # noqa: E402


def _lecteur(sits, toutes_absentes=False):
    appels = {"n": 0}

    async def lire(c):
        s = sits[appels["n"] % len(sits)]
        appels["n"] += 1
        mots = [{"carte": k.split("@")[0], "strate": 7, "intensite": "f"} for k in s["presentes"]]
        if toutes_absentes:
            mots += [{"carte": k.split("@")[0], "strate": 7, "intensite": "f"} for k in s["absentes"]]
        return json.dumps({"mots": mots, "rejets_classes": {}})
    return lire


class Tests(unittest.TestCase):
    def test_reflexion_et_humain(self):
        m = ap._moteur()
        cartes = [c for c in sorted(m.NOMS) if not m.hors_domaine(f"{c}@7")]
        sits = [s for s in (ms.situation(7, g, cartes) for g in range(6)) if s["evenement"]][:3]
        graines = [s["graine"] for s in sits]

        async def narrateur(c):
            return "[2026-11-01] Titre — https://a.example/x\nUn fait."

        r = asyncio.run(ms.lancer(narrateur, _lecteur(sits, True), 1, 7, graines[0], "2026-11-11",
                                  reflechi=_lecteur(sits[:1])))
        row = r["situations"][0]
        self.assertIn("lecture_reflechie", row)
        self.assertTrue(set(row["lecture_reflechie"]["ancrees"]) <= set(row["ancrees"]))
        # mesure : sur une ligne vérifiée sans erreur
        row["verification"] = {"presentes_non_montrees": [], "absentes_montrees": []}
        x = ms.mesurer([row])
        p = x["mesure_verifiee"]["perturbations"]["reflexion"]
        self.assertEqual(p["avec_reflexion"]["fp"], 0.0)
        self.assertEqual(p["sans_reflexion"]["fp"], 1.0)
        # options : Claude → thinking ; autre famille → reasoning_effort
        self.assertIn("thinking", ms.options_reflexion("bedrock/global.anthropic.claude-sonnet-4-6"))
        self.assertEqual(ms.options_reflexion("bedrock/deepseek.v3.2"), {"reasoning_effort": "medium"})
        # référence humaine : export sans la vérité dans le cahier, notation contre la clé
        passage = {"protocole_monde": 6, "strate": 7, "calcule_le": "2026-11-11T00:00:00+00:00",
                   "situations": [dict(row, texte="[2026-11-01] Titre\nUn fait.")]}
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            e = ms.exporter_humain([passage, dict(passage, protocole_monde=5)], d, 10)
            self.assertEqual(e["situations"], 1)                          # le protocole le plus récent seulement
            cahier = (d / "cahier.md").read_text(encoding="utf-8")
            self.assertNotIn("presentes", cahier)
            self.assertIn("Annexe", cahier)
            with open(d / "grille.csv", encoding="utf-8") as f_:
                lignes = list(csv.DictReader(f_))
            for l_ in lignes:                                             # l'humain lit exactement les présentes
                l_["lecture"] = "F" if l_["cle"] in row["presentes"] else ""
            with open(d / "grille.csv", "w", newline="", encoding="utf-8") as f_:
                w = csv.DictWriter(f_, fieldnames=["situation", "carte", "cle", "lecture"])
                w.writeheader()
                w.writerows(lignes)
            n = ms.noter_humain(d)
            self.assertEqual(n["humain"]["fp"], 0.0)
            if row["presentes"]:
                self.assertEqual(n["humain"]["sens_F"], 1.0)
            self.assertEqual(n["lecteur"]["fp"], 1.0)
            self.assertIn("lecteur_reflechi", n)


if __name__ == "__main__":
    unittest.main()
