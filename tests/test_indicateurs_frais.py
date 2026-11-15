"""0.10.129 : modèle figé des indicateurs pertinents."""
import os
import tempfile
import unittest

os.environ["ALPHABET_REGISTRE"] = tempfile.mkdtemp(prefix="registre-")
import alphabet_pipeline as _ap_regle_ab
_ap_regle_ab.POSTER_AB = False

import banc_indicateurs_frais as bf


class TestFrais(unittest.TestCase):
    def test_famille(self):
        self.assertEqual(bf.famille("Will there be more 'Riots' in X for the"), "mobilisation")
        self.assertEqual(bf.famille("Will there be more fatalities in X for the"), "violence")
        self.assertEqual(bf.famille("Will there be more 'Strategic developments' in X"), "strategique")

    def test_modele_fige(self):
        pluie = {"pluie": 3.0, "fcdo": 0.0, "presents": {"pluie": True, "fcdo": True}}
        self.assertLess(bf.p_pertinent(0.4, "mobilisation", pluie), 0.4)       # forte pluie : moins de mobilisation
        self.assertAlmostEqual(bf.p_pertinent(0.4, "strategique", pluie), 0.4)  # case non pertinente : B inchangé
        absent = {"pluie": 3.0, "presents": {}}
        self.assertAlmostEqual(bf.p_pertinent(0.4, "mobilisation", absent), 0.4)  # non mesuré : neutre
        alerte = {"fcdo": 2.0, "pluie": 0.0, "presents": {"fcdo": True}}
        self.assertLess(bf.p_pertinent(0.3, "violence", alerte), 0.3)


if __name__ == "__main__":
    unittest.main()
