"""0.10.178 : sanctions OFAC et britanniques par pays visé."""
import os
import tempfile
import unittest

os.environ["ALPHABET_REGISTRE"] = tempfile.mkdtemp(prefix="registre-")
import collecte_sanctions as cs


class TestSanctions(unittest.TestCase):
    def test_ofac(self):
        page = ("<html><head><title>Iran-related Designations; Counter Terrorism Designations | Office of Foreign Assets "
                "Control</title></head><body><p>ACME CO, Tehran (Linked To: X) [IRAN-EO13902]</p>"
                "<p>B LLC [IRGC] [SDGT]</p><p>C OOO [RUSSIA-EO14024]</p><p>D [UKRAINE-EO13660]</p></body></html>")
        titre, c = cs.lire_ofac(page)
        self.assertEqual(titre, "Iran-related Designations; Counter Terrorism Designations")
        self.assertEqual(dict(c), {"IR": 2, "--": 1, "RU": 2})
        self.assertEqual(cs.pays_programme("SOUTH SUDAN"), "SS")
        self.assertEqual(cs.pays_programme("DPRK3"), "KP")
        self.assertEqual(cs.pays_programme("LIBYA2"), "LY")
        self.assertEqual(cs.pays_programme("SDNTK"), "--")
        self.assertEqual(cs.pays_programme("DPRK-NKSPEA"), "KP")

    def test_uk(self):
        h = [{"public_timestamp": "2026-11-10T12:00:00Z", "note": "Added 5 entries under the Russia sanctions regime."},
             {"public_timestamp": "2026-11-09T12:00:00Z", "note": "Made 4 amendments under the Global Irregular Migration sanctions regime."},
             {"public_timestamp": "2026-11-08T12:00:00Z", "note": "Designated 2 entries under the Democratic People's Republic of Korea sanctions regime."},
             {"public_timestamp": "2026-01-01T12:00:00Z", "note": "Added 9 entries under the Iran sanctions regime."}]
        self.assertEqual(cs.lire_notes_uk(h, "2026-06-01"), [("2026-11-10", "RU", 5), ("2026-11-08", "KP", 2)])


if __name__ == "__main__":
    unittest.main()
