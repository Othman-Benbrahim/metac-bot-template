"""0.10.147 : collecteur Violations Watch (comptes seulement)."""
import unittest

import collecte_violationswatch as cv

CSV = """\ufeffid,status,priority,headline,location,first_reported
VW-1,lead,High,x,Palestine (Gaza),2026-11-13T20:19:00Z
VW-2,lead,High,y,Palestine (Gaza),2026-11-13T21:00:00Z
VW-3,lead,Low,z,Nigeria,2026-11-14T08:00:00Z
"""


class TestVW(unittest.TestCase):
    def test_compter_et_fusionner(self):
        c = cv.compter(CSV)
        self.assertEqual(len(c[("Palestine", "2026-11-13", "High")]), 2)
        f = cv.fusionner({("Palestine", "2026-11-13", "High"): 1}, c)
        self.assertEqual(f[("Palestine", "2026-11-13", "High")], 2)      # le même jour revu : pas de double compte
        self.assertEqual(cv.fusionner(f, c)[("Palestine", "2026-11-13", "High")], 2)


if __name__ == "__main__":
    unittest.main()
