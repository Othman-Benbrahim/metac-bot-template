"""0.10.201 : pilote IRSEM (lecture des pages, sans réseau ni modèle)."""
import unittest

import mecanismes_irsem as mi

LISTE = '''<a href="/publications?page=2">2</a>
<a href="https://www.irsem.fr/publications/bab-el-mandeb-la-fin-des-mers-libres">Bab el-Mandeb</a>
<a href="/publications/bab-el-mandeb-la-fin-des-mers-libres">bis</a>
<a href="/publications/la-cooperation-russo-iranienne-dans-le-domaine-spatial">Spatial</a>'''

FICHE = '''<html><h1>Bab el-Mandeb : la fin des mers libres&nbsp;?</h1>
<span>Brève stratégique 94 - 09/2026</span><p>Influence Stratégie</p>
<a href="/storage/file_manager_files/2026/09/breve-94-lauret-bab-el-mandeb.pdf">Télécharger</a></html>'''


class TestIrsem(unittest.TestCase):
    def test_liens(self):
        self.assertEqual(mi.liens_de_page(LISTE), [
            "https://www.irsem.fr/publications/bab-el-mandeb-la-fin-des-mers-libres",
            "https://www.irsem.fr/publications/la-cooperation-russo-iranienne-dans-le-domaine-spatial"])

    def test_fiche(self):
        f = mi.fiche(FICHE, "u")
        self.assertEqual((f["serie"], f["numero"], f["mois"]), ("Brève stratégique", 94, "2026-09"))
        self.assertEqual(f["pdf"], "https://www.irsem.fr/storage/file_manager_files/2026/09/breve-94-lauret-bab-el-mandeb.pdf")
        self.assertTrue(f["titre"].startswith("Bab el-Mandeb"))

    def test_regle_arret(self):
        props = [{"mecanisme": "a", "indicateur": "hausse des manifestations", "delai": "2 semaines", "registre": "manifestations"},
                 {"mecanisme": "b", "indicateur": "hausse des manifestations", "delai": None, "registre": "manifestations"},
                 {"mecanisme": "c", "indicateur": "érosion de la confiance", "delai": "1 mois", "registre": "manifestations"},
                 {"mecanisme": "d", "indicateur": "hausse des manifestations", "delai": "1 mois", "registre": "aucun"},
                 {"mecanisme": "e", "indicateur": "sanctions", "delai": "1 mois", "registre": "inconnu"}]
        self.assertEqual([p["mecanisme"] for p in mi.candidats(props)], ["a"])

    def test_resume(self):
        p = {"mecanisme": "a", "indicateur": "passages de navires dans le détroit", "delai": "2 semaines", "registre": "maritime",
             "source": {"serie": "Brève stratégique", "numero": 94, "mois": "2026-09", "url": "u"}}
        r = mi.resumer([{}], [p])
        self.assertIn("1 passent la règle", r)
        self.assertIn("maritime : 1", r)

    def test_rubicon(self):
        liste = ('<a href="https://lerubicon.org/la-voie-vers-une-securite-durable-en-colombie/fulltext.pdf">PDF</a>'
                 '<a href="https://lerubicon.org/la-voie-vers-une-securite-durable-en-colombie/fulltext.pdf">bis</a>'
                 '<a href="https://lerubicon.org/autre-article/">sans PDF</a>')
        self.assertEqual(mi.liens_rubicon(liste), ["https://lerubicon.org/la-voie-vers-une-securite-durable-en-colombie/"])
        f = mi.fiche_rubicon("<h1>La voie vers une sécurité durable</h1><p>13 novembre 2026</p>", "https://lerubicon.org/x/")
        self.assertEqual((f["mois"], f["pdf"], f["serie"]), ("2026-11", "https://lerubicon.org/x/fulltext.pdf", "Le Rubicon"))

if __name__ == "__main__":
    unittest.main()
