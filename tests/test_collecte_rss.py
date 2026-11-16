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


class _Client:
    def __init__(self, donnees):
        self.donnees = donnees

    def get(self, url, timeout=60):
        d = self.donnees

        class R:
            def json(self_):
                return d
        return R()


PAYS = [
    {"cca2": "IR", "unMember": True, "demonyms": {"eng": {"m": "Iranian", "f": "Iranian"}, "fra": {"m": "Iranien", "f": "Iranienne"}}},
    {"cca2": "FR", "unMember": True, "demonyms": {"eng": {"m": "French", "f": "French"}, "fra": {"m": "Français", "f": "Française"}}},
    {"cca2": "TF", "unMember": False, "demonyms": {"eng": {"m": "French", "f": "French"}, "fra": {"m": "Français", "f": "Française"}}},
    {"cca2": "CD", "unMember": True, "demonyms": {"eng": {"m": "Congolese", "f": "Congolese"}}},
    {"cca2": "CG", "unMember": True, "demonyms": {"eng": {"m": "Congolese", "f": "Congolese"}}},
    {"cca2": "US", "unMember": True, "demonyms": {"eng": {"m": "American", "f": "American"}, "fra": {"m": "Américain", "f": "Américaine"}}},
    {"cca2": "PL", "unMember": True, "demonyms": {"eng": {"m": "Polish", "f": "Polish"}, "fra": {"m": "Polonais", "f": "Polonaise"}}},
]


class TestAdjectifs(unittest.TestCase):
    """0.10.199 : pays reconnus aussi par leurs adjectifs de nationalité (en ombre, comptes « _large »)."""

    def setUp(self):
        self.adj = cr.adjectifs(_Client(PAYS))
        self.larges = cr.motifs_larges([(re.compile(r"(?<![\w-])iran(?![\w-])", re.I), "IR")], self.adj)

    def test_formes_et_ambiguite(self):
        self.assertEqual(self.adj["iranienne"], "IR")
        self.assertEqual(self.adj["iraniennes"], "IR")
        self.assertEqual(self.adj["iranians"], "IR")
        self.assertEqual(self.adj["french"], "FR")          # un seul membre de l'ONU parmi les porteurs
        self.assertNotIn("congolese", self.adj)             # deux membres de l'ONU : écarté

    def test_detection(self):
        self.assertEqual(cr.detecter_large("Activité offensive iranienne contre des intérêts français", self.larges), {"IR", "FR"})
        self.assertEqual(cr.detecter_large("Latin American leaders meet", self.larges), set())
        self.assertEqual(cr.detecter_large("We must polish the draft", self.larges), set())
        self.assertEqual(cr.detecter_large("Polish farmers block roads", self.larges), {"PL"})

    def test_source_indisponible(self):
        class Panne:
            def get(self, *a, **k):
                raise OSError("réseau")
        self.assertEqual(cr.adjectifs(Panne()), {})

    def test_famille_cyber(self):
        self.assertIn("cyber", cr.FLUX)
        self.assertIn("cyber", cr.LARGE_SEUL)
        self.assertNotIn("cyber", cr.DEDOUBLONNER)


class TestCorrectiv(unittest.TestCase):
    """0.10.200 : Correctiv en ombre ; vérifications lues avant le flux général ; noms allemands pour ces familles."""

    def test_ordre_et_familles(self):
        ordre = list(cr.FLUX)
        self.assertLess(ordre.index("verification"), ordre.index("enquete"))
        self.assertTrue({"verification", "enquete"} <= cr.LARGE_SEUL)
        self.assertEqual(cr.ALLEMAND, {"verification", "enquete"})

    def test_noms_allemands(self):
        terr = {"main": {"de": {"localeDisplayNames": {"territories": {"RU": "Russland", "CZ": "Tschechien", "DE": "Deutschland"}}}}}
        m = cr.noms_pays(_Client(terr), ("de",))
        self.assertEqual(cr.detecter("Desinformation aus Russland über Tschechien", m), {"RU", "CZ"})


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


class _Client:
    def __init__(self, donnees):
        self.donnees = donnees

    def get(self, url, timeout=60):
        d = self.donnees

        class R:
            def json(self_):
                return d
        return R()


PAYS = [
    {"cca2": "IR", "unMember": True, "demonyms": {"eng": {"m": "Iranian", "f": "Iranian"}, "fra": {"m": "Iranien", "f": "Iranienne"}}},
    {"cca2": "FR", "unMember": True, "demonyms": {"eng": {"m": "French", "f": "French"}, "fra": {"m": "Français", "f": "Française"}}},
    {"cca2": "TF", "unMember": False, "demonyms": {"eng": {"m": "French", "f": "French"}, "fra": {"m": "Français", "f": "Française"}}},
    {"cca2": "CD", "unMember": True, "demonyms": {"eng": {"m": "Congolese", "f": "Congolese"}}},
    {"cca2": "CG", "unMember": True, "demonyms": {"eng": {"m": "Congolese", "f": "Congolese"}}},
    {"cca2": "US", "unMember": True, "demonyms": {"eng": {"m": "American", "f": "American"}, "fra": {"m": "Américain", "f": "Américaine"}}},
    {"cca2": "PL", "unMember": True, "demonyms": {"eng": {"m": "Polish", "f": "Polish"}, "fra": {"m": "Polonais", "f": "Polonaise"}}},
]


class TestAdjectifs(unittest.TestCase):
    """0.10.199 : pays reconnus aussi par leurs adjectifs de nationalité (en ombre, comptes « _large »)."""

    def setUp(self):
        self.adj = cr.adjectifs(_Client(PAYS))
        self.larges = cr.motifs_larges([(re.compile(r"(?<![\w-])iran(?![\w-])", re.I), "IR")], self.adj)

    def test_formes_et_ambiguite(self):
        self.assertEqual(self.adj["iranienne"], "IR")
        self.assertEqual(self.adj["iraniennes"], "IR")
        self.assertEqual(self.adj["iranians"], "IR")
        self.assertEqual(self.adj["french"], "FR")          # un seul membre de l'ONU parmi les porteurs
        self.assertNotIn("congolese", self.adj)             # deux membres de l'ONU : écarté

    def test_detection(self):
        self.assertEqual(cr.detecter_large("Activité offensive iranienne contre des intérêts français", self.larges), {"IR", "FR"})
        self.assertEqual(cr.detecter_large("Latin American leaders meet", self.larges), set())
        self.assertEqual(cr.detecter_large("We must polish the draft", self.larges), set())
        self.assertEqual(cr.detecter_large("Polish farmers block roads", self.larges), {"PL"})

    def test_source_indisponible(self):
        class Panne:
            def get(self, *a, **k):
                raise OSError("réseau")
        self.assertEqual(cr.adjectifs(Panne()), {})

    def test_famille_cyber(self):
        self.assertIn("cyber", cr.FLUX)
        self.assertIn("cyber", cr.LARGE_SEUL)
        self.assertNotIn("cyber", cr.DEDOUBLONNER)


class TestCorrectiv(unittest.TestCase):
    """0.10.200 : Correctiv en ombre ; vérifications lues avant le flux général ; noms allemands pour ces familles."""

    def test_ordre_et_familles(self):
        ordre = list(cr.FLUX)
        self.assertLess(ordre.index("verification"), ordre.index("enquete"))
        self.assertTrue({"verification", "enquete"} <= cr.LARGE_SEUL)
        self.assertEqual(cr.ALLEMAND, {"verification", "enquete"})

    def test_noms_allemands(self):
        terr = {"main": {"de": {"localeDisplayNames": {"territories": {"RU": "Russland", "CZ": "Tschechien", "DE": "Deutschland"}}}}}
        m = cr.noms_pays(_Client(terr), ("de",))
        self.assertEqual(cr.detecter("Desinformation aus Russland über Tschechien", m), {"RU", "CZ"})


if __name__ == "__main__":
    unittest.main()
