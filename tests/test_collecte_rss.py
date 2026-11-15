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
        self.assertFalse(cr.NOTATION.search("Fed's Daly: we need to raise rates"))                 # lettres réservées aux abonnés : titre seul
        self.assertEqual((a[0]["jour"], a[0]["texte"].strip()), ("2026-11-15", "Mali"))


if __name__ == "__main__":
    unittest.main()
