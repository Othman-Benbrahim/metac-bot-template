"""0.10.225 : combinaisons de mécanismes (grille de bon sens, exploration puis confirmation)."""
import unittest
from datetime import date
from unittest import mock

import combinaisons as cb
import indicateurs_niche as ni


def q(jeu, fam, etats, issue, p=0.3):
    return {"jeu": jeu, "question_id": f"fb:{jeu}:acled:{id(etats)}:{issue}", "famille": fam, "issue": issue,
            "p_B": p, "etats": etats}


class TestCombinaisons(unittest.TestCase):
    def test_grille_complete(self):
        self.assertEqual(len(cb.GRILLE), 15)
        self.assertEqual(sum(v == "temoin" for v in cb.GRILLE.values()), 5)
        self.assertEqual(cb.familles_paire("M4", "M17"), {"mobilisation"})
        self.assertEqual(cb.familles_paire("M11", "FC"), {"mobilisation", "strategique", "violence"})

    def test_etats(self):
        with mock.patch.multiple(ni, elections=lambda c, d: {"present": True, "valeur": 1},
                                 voisins_gdelt=lambda c, d: {"present": True, "valeur": 0.9},
                                 dates_memoire=lambda c, d: {"present": False, "raison": "aucune date de mémoire pour ce pays"},
                                 alignement_rival=lambda c, d: {"present": False, "raison": "période non couverte"},
                                 force_chinoise=lambda c, d: {"present": True, "valeur": 0}):
            e = cb.etats("PH", "Will there be more 'Riots' in Philippines for the 30 days…", date(2026, 3, 1), "2024-06-01")
            self.assertEqual(e, {"M4": 1, "M10": 1, "M11": 1, "M14": 0, "M17": None, "FC": 0})
            # calendrier électoral qui commence après la fenêtre : non mesurable
            e = cb.etats("PH", "'Protests' in Philippines", date(2025, 3, 1), "2026-01-01")
            self.assertIsNone(e["M10"])
            self.assertEqual(e["M4"], 0)

    def test_exploration_puis_confirmation(self):
        ls = []
        for jeu in ("2025-03-02", "2025-05-11", "2025-08-03", "2026-02-01", "2026-04-12", "2026-06-07"):
            for i in range(4):
                ls.append(q(jeu, "mobilisation", {"M10": 1, "M11": 1, "M4": 0}, 1))      # les deux : toujours OUI
                ls.append(q(jeu, "mobilisation", {"M10": 0, "M11": 0, "M4": 0}, i % 3 == 0))
                ls.append(q(jeu, "mobilisation", {"M10": 1, "M11": 0, "M4": 0}, i % 3 == 0))
                ls.append(q(jeu, "mobilisation", {"M10": 0, "M11": 1, "M4": 0}, i % 3 == 0))
        r = cb.resumer(ls)
        p = next(x for x in r["paires"] if x["paire"] == "M10 × M11")
        self.assertEqual(p["exploration"]["11"], 12)
        self.assertGreater(p["delta"], 0)
        self.assertGreater(p["interaction_exploration"], 0)          # renforcement
        self.assertEqual(p["verdict"], "confirmée")
        self.assertLess(p["perte_ajustee"], p["perte_B"])
        self.assertEqual(r["k_juges"], 1)
        self.assertEqual(r["valeur_du_bon_sens"]["part_confirmees"], 1.0)
        self.assertIsNone(r["valeur_du_bon_sens"]["part_confirmes"])

    def test_case_trop_petite_non_jugee(self):
        ls = [q("2025-03-02", "mobilisation", {"M10": 1, "M11": 1}, 1)] * 5 + \
             [q("2026-03-01", "mobilisation", {"M10": 1, "M11": 1}, 1)] * 20
        r = cb.resumer(ls)
        p = next(x for x in r["paires"] if x["paire"] == "M10 × M11")
        self.assertNotIn("verdict", p)
        self.assertEqual(r["k_juges"], 0)


if __name__ == "__main__":
    unittest.main()
