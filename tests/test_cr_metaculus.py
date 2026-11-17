import unittest
from datetime import date, timedelta

import banc_classe_reference as bcr
import banc_cr_metaculus as bm


class T(unittest.TestCase):
    def test_frequence_bot(self):
        self.assertEqual(bm.frequence_bot([0, 0, 0, 0, 0], 1), 0.1)
        self.assertEqual(bm.frequence_bot([3, 1, 2, 5, 0], 2), 0.6)

    def test_cas(self):
        c = {(date(2023, 1, 1) + timedelta(days=k)).isoformat(): (3 if (k // 30) % 2 else 0) for k in range(1000)}
        xs = bm.cas_seuil({("ucdp", "X"): c, ("ucdp", "Y"): c}, {"ucdp": "2023-01-01"}, date(2025, 9, 20), 30)
        self.assertTrue(xs)
        self.assertTrue(all(x["seuil"] >= 1 for x in xs))
        bcr.noyau(xs)
        self.assertTrue(any("p_K" in x for x in xs))

    def test_groupes(self):
        g = bm.groupes()
        self.assertEqual({s for s, *_ in g}, {"ucdp", "coupures_internet", "sanctions_us"})


if __name__ == "__main__":
    unittest.main()
