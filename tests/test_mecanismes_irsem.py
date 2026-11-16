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
        props = [{"mecanisme": "a", "indicateur": "x", "delai": "2 semaines", "portee": "général"},
                 {"mecanisme": "b", "indicateur": "x", "delai": None, "portee": "général"},
                 {"mecanisme": "c", "indicateur": "x", "delai": "1 mois", "portee": "cas"}]
        self.assertEqual([p["mecanisme"] for p in mi.candidats(props)], ["a"])

    def test_resume(self):
        p = {"mecanisme": "a", "indicateur": "x", "delai": "2 semaines", "portee": "région", "domaine": "maritime ou commerce",
             "source": {"serie": "Brève stratégique", "numero": 94, "mois": "2026-09", "url": "u"}}
        r = mi.resumer([{}], [p])
        self.assertIn("1 passent le filtre", r)


if __name__ == "__main__":
    unittest.main()
