"""0.10.153 : brouillage GPS (gpsjam.org), lecture tolérante et rattachement des zones aux pays."""
import asyncio
import unittest
from datetime import date, timedelta

import brouillage_gps as bg

try:
    import h3
    H3 = True
except Exception:
    H3 = False

CARRE_FR = {"features": [{"properties": {"ISO_A2": "-99", "ISO_A2_EH": "FR"},
                          "geometry": {"type": "Polygon", "coordinates": [[[0, 45], [5, 45], [5, 50], [0, 50], [0, 45]]]}}]}


class Rep:
    def __init__(self, texte=None, j=None):
        self.text, self._j = texte, j

    def json(self):
        return self._j


class TestBrouillage(unittest.TestCase):
    def test_lecture_et_seuil(self):
        lignes = bg.lire_jour("hex,count_good_aircraft,count_bad_aircraft\nabc,90,1\ndef,10,5\n")
        self.assertEqual(lignes, [("abc", 90, 1), ("def", 10, 5)])
        self.assertFalse(bg.rouge(90, 1))
        self.assertTrue(bg.rouge(10, 5))
        with self.assertRaises(ValueError):
            bg.lire_jour("a,b,c\n1,2,3\n")

    def test_frontieres(self):
        f = bg.charger_frontieres(CARRE_FR)
        self.assertEqual(bg.pays_du_point(47.0, 2.0, f), "FR")      # code « ISO_A2_EH » quand ISO_A2 vaut -99
        self.assertIsNone(bg.pays_du_point(40.0, 2.0, f))

    @unittest.skipUnless(H3, "h3 absent")
    def test_mesure(self):
        z_fr = h3.latlng_to_cell(47.0, 2.0, 4)

        async def obtenir(c, url):
            if url == bg.FRONTIERES:
                return Rep(j=CARRE_FR)
            return Rep(texte=f"hex,count_good_aircraft,count_bad_aircraft\n{z_fr},10,5\n")

        g = bg.Brouillage(obtenir)
        b = asyncio.new_event_loop()
        try:
            r = b.run_until_complete(g.mesure(None, "FR", date(2026, 9, 1)))
        finally:
            b.close()
        self.assertTrue(r["present"])
        self.assertEqual(r["valeur"], 1.0)                          # la seule zone du pays est rouge chaque jour


if __name__ == "__main__":
    unittest.main()
