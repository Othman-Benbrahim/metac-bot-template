import unittest

import pages_sans_flux as pfs

PAGE = """<a href="/elections/id/4321/">Chili <b>présidentielle</b></a>
<a href="/elections/id/4322/">Népal</a><a href="/elections/id/4322/">Népal</a>
<a href="https://ailleurs.org/x">dehors</a><a href="/about/">À propos</a><a href="#haut">haut</a>"""
BASE = "https://www.electionguide.org/elections/"


class TestPagesSansFlux(unittest.TestCase):
    def test_sonde(self):
        g = pfs.sonde(PAGE, BASE)
        self.assertEqual(g[0][:2], ("/elections/id/N", 3))
        self.assertNotIn("dehors", str(g))

    def test_lire(self):
        r = pfs.lire(PAGE, BASE, r"^/elections/id/\d+/?$")
        self.assertEqual([x["titre"] for x in r], ["Chili présidentielle", "Népal"])
        self.assertEqual(r[0]["lien"], "https://www.electionguide.org/elections/id/4321/")
