"""0.10.149 : lecture du KML de GeoConfirmed (formats de date tolérés)."""
import unittest

import alphabet_puits as apz

KML = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2"><Document><Folder>
<Placemark><name>10 NOV 2026 - Pokrovsk - drone strike</name><description><![CDATA[<a href="https://x">src</a>]]></description>
<Point><coordinates>37.18,48.28,0</coordinates></Point></Placemark>
<Placemark><name>Strike</name><TimeStamp><when>2026-11-12T08:00:00Z</when></TimeStamp>
<Point><coordinates>37.50,48.60</coordinates></Point></Placemark>
<Placemark><name>Sans date</name><Point><coordinates>30.0,50.0</coordinates></Point></Placemark>
</Folder></Document></kml>"""


class TestGeoConfirmed(unittest.TestCase):
    def test_lecture(self):
        e = apz.lire_kml_geoconfirmed(KML)
        self.assertEqual([x["date"] for x in e], ["2026-11-10", "2026-11-12"])   # le point sans date est écarté
        self.assertAlmostEqual(e[0]["lat"], 48.28)
        self.assertAlmostEqual(e[0]["lon"], 37.18)

    def test_dates(self):
        self.assertEqual(apz._date_geoconfirmed("3 Sept 2026 frappe"), "2026-09-03")
        self.assertIsNone(apz._date_geoconfirmed("rien"))
        self.assertIn("geoconfirmed", apz.CATALOGUE)


if __name__ == "__main__":
    unittest.main()
