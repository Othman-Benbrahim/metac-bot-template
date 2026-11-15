"""0.10.127 : taux de base ACLED, forme « dix fois plus que un plus la moyenne »."""
import os
import tempfile
import unittest

os.environ["ALPHABET_REGISTRE"] = tempfile.mkdtemp(prefix="registre-")
import alphabet_pipeline as _ap_regle_ab
_ap_regle_ab.POSTER_AB = False

import banc_forecastbench as fb


class TestBAcled(unittest.TestCase):
    def test_forme_simple_inchangee(self):
        self.assertAlmostEqual(fb.b_acled(2.0), fb.b_acled(2.0, 1.0))
        self.assertTrue(0.2 < fb.b_acled(2.0) < 0.6)

    def test_dix_fois(self):
        # moyenne 0,0833 (m = 1,0833) : seuil 10,8 événements ; quasi impossible
        self.assertLess(fb.b_acled(1.0833, 10.0), 1e-6)
        self.assertGreater(fb.b_acled(1.0833), 0.05)          # l'ancienne erreur annonçait plusieurs pour cent
        self.assertEqual(fb.facteur_acled("Will there be more than ten times as many 'Riots' in X"), 10.0)
        self.assertEqual(fb.facteur_acled("Will there be more 'Riots' in X"), 1.0)


if __name__ == "__main__":
    unittest.main()
