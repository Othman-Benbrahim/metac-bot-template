"""0.10.295 : contrôle automatique des chiffres écrits à la main (fiches de résultats, verdicts d'essais).

Décision d'auteur du 2026-11-18, 21 h 48 (« oui, et il faudrait l'automatiser »). Chaque nombre d'une fiche de
fiches/ et de chaque verdict d'essai qui déclare son résumé (« resume ») doit se retrouver dans le résultat brut,
sauf s'il est déclaré comme constante de conception, chiffre de journal ([journal: …]), estimation
([estimation: …]) ou calcul vérifié ([calc: a - b = c])."""
import os
import tempfile

os.environ.setdefault("ALPHABET_REGISTRE", tempfile.mkdtemp(prefix="registre-test-"))
os.environ["ALPHABET_TESTS"] = "1"

import unittest
from pathlib import Path

import controle_chiffres as cc
import essais as es

RACINE = Path(__file__).resolve().parent.parent
CONSTANTES_VERDICTS = [90.0, 30.0, 0.693]      # niveau des intervalles, seuil des ratés, pile ou face


class Fonctions(unittest.TestCase):
    def test_nombres_et_correspondance(self):
        t = "Perte 0,4735 contre 0,4634 ; écart +0,010 ; [−0,016 ; +0,038] ; 1 878 questions ; run 44358972727 ; 2026"
        ns = [v for _, v, _ in cc.nombres(t)]
        self.assertIn(0.4735, ns)
        self.assertIn(1878.0, ns)
        self.assertNotIn(44358972727.0, ns)
        self.assertNotIn(2026.0, ns)
        self.assertTrue(cc.correspond(0.057, 3, [0.0574925]))
        self.assertFalse(cc.correspond(0.058, 3, [0.0574925]))        # l'erreur réelle trouvée par l'audit
        self.assertTrue(cc.correspond(36.0, 0, [0.36]))                # pourcentage

    def test_calculs_et_marqueurs(self):
        self.assertEqual(cc.verifier_calculs("[calc: 0,5564 - 0,5667 = -0,010]"), [])
        self.assertTrue(cc.verifier_calculs("[calc: 0,5564 - 0,5667 = -0,020]"))
        self.assertEqual(cc.nombres("[journal: coût 0,41 $] gpt-5-mini Haiku 4.5 à 19 h 40"), [])


class Fiches(unittest.TestCase):
    def test_chaque_fiche_retrouve_ses_chiffres(self):
        for f in sorted((RACINE / "fiches").glob("*.md")):
            t = f.read_text(encoding="utf-8")
            sources = [RACINE / s for s in cc.sources_de(t)]
            self.assertTrue(sources, f"{f.name} : en-tête « sources: » manquant")
            r = cc.verifier(t, sources)
            self.assertEqual((r["introuvables"], r["calculs"]), ([], []), f.name)


class Verdicts(unittest.TestCase):
    def test_verdicts_avec_resume(self):
        for nom, e in es.ESSAIS.items():
            if not e.get("resume") or not e.get("verdict"):
                continue
            r = cc.verifier(e["verdict"], [RACINE / s for s in e["resume"]])
            reste = [x for x in r["introuvables"]
                     if not cc.correspond(*[v for _, v, _ in cc.nombres(x)][:1],
                                          max([d for _, _, d in cc.nombres(x)] or [0]), CONSTANTES_VERDICTS)]
            self.assertEqual((reste, r["calculs"]), ([], []), nom)


if __name__ == "__main__":
    unittest.main()
