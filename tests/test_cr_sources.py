import unittest
from datetime import date, timedelta

import banc_classe_reference as bcr
import banc_cr_sources as bs


class T(unittest.TestCase):
    def test_comptes_et_cas(self):
        pts = [{"date": (date(2024, 1, 1) + timedelta(days=k)).isoformat()} for k in range(0, 900, 3)]
        c = bs.comptes_jour(pts, "2024-01-01")
        self.assertEqual(sum(c.values()), 300)
        comptes = {("src", "a"): c, ("src", "b"): c}
        cov = {"src": bs.jours("2024-01-01", date(2026, 6, 1))}
        xs = bs.cas_source(comptes, cov, date(2026, 5, 31), 30)
        self.assertTrue(xs)
        bcr.noyau(xs)
        self.assertTrue(any("p_K" in x for x in xs))
        r = bs.juger(xs, 1)
        self.assertIn("perte_B", r)

    def test_groupes_fixes(self):
        g = bs.groupes()
        self.assertEqual(len({s for s, *_ in g}), 6)
        self.assertEqual(len(g), 25 + 20 + 2 + 6 + 7 + 8)


if __name__ == "__main__":
    unittest.main()
