"""0.10.152 : collecteur RSS (comptes seulement)."""
import re
import unittest

import collecte_rss as cr


class TestRSS(unittest.TestCase):
    def test_detection(self):
        m = [(re.compile(r"(?<![\w-])" + re.escape(n) + r"(?![\w-])", re.I), c)
             for n, c in sorted({"soudan du sud": "SS", "south sudan": "SS", "soudan": "SD", "sudan": "SD",
                                 "niger": "NE", "nigeria": "NG"}.items(), key=lambda t: -len(t[0]))]
        self.assertEqual(cr.detecter("Clashes in South Sudan", m), {"SS"})
        self.assertEqual(cr.detecter("Violences au Soudan du Sud et au Soudan", m), {"SS", "SD"})
        self.assertEqual(cr.detecter("Attaque au Nigeria", m), {"NG"})

    def test_articles(self):
        xml = (b'<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Mali</title><id>x1</id>'
               b'<updated>2026-11-15T10:00:00Z</updated><link href="https://a"/></entry></feed>')
        a = cr.articles(xml)
        r = cr.articles(b'<rss><channel><item><title>Paris</title><description>Mali Niger</description>'
                        b'<guid>g</guid></item></channel></rss>', titres_seuls=True)
        self.assertEqual(r[0]["texte"].strip(), "Paris")
        o = cr.articles_oms({"value": [{"Id": "x", "Title": "Marburg virus disease - Ethiopia", "Summary": "<p>cas</p>",
                                        "PublicationDateAndTime": "2026-11-14T10:00:00Z"}, {"Id": "y", "Title": "sans date"}]})
        self.assertEqual((len(o), o[0]["jour"]), (1, "2026-11-14"))
        self.assertIn("Ethiopia", o[0]["texte"])
        self.assertTrue(cr.NOTATION.search("Fitch downgrades France to A+, outlook stable"))
        self.assertTrue(cr.NOTATION.search("Moody's relève la perspective de l'Italie"))
        self.assertFalse(cr.NOTATION.search("Fed's Daly: we need to raise rates"))
        # 0.10.169 : une virgule perdue concatène deux adresses ; chaque flux est une seule URL
        for urls in cr.FLUX.values():
            for u in urls:
                self.assertEqual(u.count("://"), 1, u)
        b = cr.bilan_sante([
            {"url": "a", "famille": "f", "statut": "ok", "dernier_nouveau": "2026-11-15"},
            {"url": "b", "famille": "f", "statut": "erreur HTTPStatusError"},
            {"url": "c", "famille": "f", "statut": "vide", "dernier_succes": ""},
            {"url": "d", "famille": "f", "statut": "ok", "dernier_nouveau": "2026-11-01"}], "2026-11-15")
        self.assertIn("4 flux : 1 en bon état, 1 en erreur, 1 vides, 1 sans nouvel article", b)                 # lettres réservées aux abonnés : titre seul
        self.assertEqual((a[0]["jour"], a[0]["texte"].strip()), ("2026-11-15", "Mali"))


if __name__ == "__main__":
    unittest.main()


class TestReprises(unittest.TestCase):
    """0.10.198 : une reprise (même titre normalisé, à moins de 30 jours) ne compte qu'une fois."""

    def test_normalisation(self):
        a = cr.empreinte_titre("Mali : l'armée annonce une OPÉRATION à Kidal")
        b = cr.empreinte_titre("  mali — l’armee annonce une operation a kidal ! ")
        self.assertIsNotNone(a)
        self.assertEqual(a, cr.empreinte_titre("Mali : l'armée annonce une opération à Kidal"))
        self.assertEqual(cr.empreinte_titre("Mali l armee annonce une operation a Kidal"), a)
        self.assertIsNone(cr.empreinte_titre("Flash info"))
        self.assertTrue(b)

    def test_fenetre(self):
        t = {}
        e = cr.empreinte_titre("Le gouvernement burkinabè dissout la commission électorale")
        self.assertFalse(cr.reprise(e, "2026-11-01", t))
        self.assertTrue(cr.reprise(e, "2026-11-03", t))      # reprise deux jours plus tard
        self.assertFalse(cr.reprise(e, "2026-12-15", t))     # hors fenêtre : nouvel article
        self.assertFalse(cr.reprise(None, "2026-11-03", t))  # titre trop court : jamais traité comme reprise

    def test_familles(self):
        self.assertIn("presse", cr.DEDOUBLONNER)
        self.assertNotIn("officiel", cr.DEDOUBLONNER)
        self.assertNotIn("sante", cr.DEDOUBLONNER)

    def test_titre_extrait(self):
        x = b"<rss><channel><item><title>Un titre &lt;b&gt;assez&lt;/b&gt; long pour compter</title><guid>1</guid></item></channel></rss>"
        self.assertIn("assez", cr.articles(x)[0]["titre"])


if __name__ == "__main__":
    unittest.main()
