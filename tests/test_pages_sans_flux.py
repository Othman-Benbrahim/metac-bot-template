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

    def test_ligne(self):
        page = """<table><tr><td><a href="/countries/id/207/">Switzerland</a></td><td>Referendum de prix</td>
        <td><a href="/elections/id/5097/">Referendum</a></td><td>Mar 8, 2027</td></tr>
        <tr><td><a href="/countries/id/12/">Chile</a></td><td><a href="/elections/id/5100/">President</a></td></tr></table>"""
        r = pfs.lire(page, BASE, pfs.SITES["ElectionGuide"]["motif"], ligne=True)
        self.assertEqual(r[0], {"lien": "https://www.electionguide.org/elections/id/5097/",
                                "titre": "Switzerland — Referendum", "date_affichee": "2027-03-08"})
        self.assertEqual(r[1]["titre"], "Chile — President")
        self.assertNotIn("date_affichee", r[1])

    def test_date_electionguide(self):
        bloc = ('<tr><td><strong>Nov 29 2026</strong> <small>(d)</small> <br> <a href="/elections/id/5097/">Referendum</a>'
                '<br> <a href="/countries/id/207/">Switzerland</a></td></tr>')
        r = pfs.lire(bloc, BASE, pfs.SITES["ElectionGuide"]["motif"], ligne=True)
        self.assertEqual(r[0]["date_affichee"], "2026-11-29")
        self.assertEqual(pfs.iso("Sept. 6, 2027"), "")      # format inconnu : rien d'inventé
        self.assertEqual(pfs.iso("6 Dec 2026"), "2026-12-06")

    def test_titre_par_adresse_et_borne(self):
        page = ('<a href="/blog/assistive-robotics-sam"><img src="x.png"></a>'
                '<a href="/blog/long-one">' + "mot " * 60 + '</a><a href="/blog/long-one">court</a>')
        r = pfs.lire(page, "https://ai.meta.com/blog/", r"^/blog/[A-Za-z0-9-]+/?$")
        self.assertEqual(r[0]["titre"], "assistive robotics sam")
        self.assertLessEqual(len(r[1]["titre"]), 120)

    def test_generique_et_date_adresse(self):
        page = ('<a href="/blog/tribe-v2-model">Learn More</a>'
                '<a href="/files/178-20261119-pre-01-00-en.pdf">Press release No. 2026/30</a>')
        r = pfs.lire(page, "https://ai.meta.com/blog/", r"^/blog/[A-Za-z0-9-]+/?$")
        self.assertEqual(r[0]["titre"], "tribe v2 model")
        r = pfs.lire(page, "https://www.icj-cij.org/", r"-pre-\d+-\d+-en\.pdf$")
        self.assertEqual(r[0]["date_affichee"], "2026-11-19")
