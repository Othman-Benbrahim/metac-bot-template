import os
import tempfile

os.environ["ALPHABET_REGISTRE"] = tempfile.mkdtemp(prefix="registre-test-")
os.environ["ALPHABET_TESTS"] = "1"

import unittest  # noqa: E402

import banc_gdelt_complement as bg  # noqa: E402
import score_registre as sr  # noqa: E402


class TComplement(unittest.TestCase):
    def test_meme_part_de_recherche_dans_les_deux_bras(self):
        rech = "x" * 6000
        art = [{"vu": "2026-01-01", "url": "https://a.org/x", "titre": "T" * 80}] * 15
        sans, avec = bg.recherches(rech, art)
        self.assertTrue(avec.startswith(sans))
        self.assertLessEqual(len(avec), bg.FENETRE)
        self.assertIn("GDELT", avec)
        self.assertNotIn("GDELT", sans)

    def test_tout_juger(self):
        ls = [{"question_id": f"m:{i}:2026-01-01", "issue": i % 2, "p_B": 0.5, "o": {"p": 0.6 if i % 2 else 0.4}}
              for i in range(40)]
        c = sr.critere_ombre_b(ls, "o", "gdelt_complement", exclure_vus=False, bloc_par="question", tout_juger=True)
        self.assertEqual((c["n_juge"], c["regard"]), (40, 1))
        self.assertLess(c["ecart_moyen"], 0)


if __name__ == "__main__":
    unittest.main()
