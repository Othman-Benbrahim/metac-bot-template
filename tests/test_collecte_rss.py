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
        self.assertEqual((a[0]["jour"], a[0]["texte"].strip()), ("2026-11-15", "Mali"))


if __name__ == "__main__":
    unittest.main()
