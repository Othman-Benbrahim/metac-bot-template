"""0.10.176 : PortWatch, dates et indicateur décalé d'une semaine."""
import os
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

os.environ["ALPHABET_REGISTRE"] = tempfile.mkdtemp(prefix="registre-")
import collecte_portwatch as cp
import indicateurs_niche as ni


class TestPortwatch(unittest.TestCase):
    def test_jour(self):
        self.assertEqual(cp.jour({"date": 1767225600000}), "2026-01-01")
        self.assertIsNone(cp.jour({}))

    def test_indicateur(self):
        d = Path(tempfile.mkdtemp())
        ancien = (ni.PORTWATCH, ni._PW)
        ni.PORTWATCH, ni._PW = d / "p.csv", None
        try:
            d0 = date(2026, 10, 1)
            lignes = ["detroit,jour,navires,petroliers,porte_conteneurs"]
            for k in range(1, 40):
                j = (d0 - timedelta(days=k)).isoformat()
                lignes.append(f"bab_el_mandeb,{j},{10 if k <= 21 else 40},2,3")
            ni.PORTWATCH.write_text("\n".join(lignes))
            m = ni.portwatch("YE", d0)
            self.assertTrue(m["present"])
            self.assertEqual((m["navires_14j"], m["navires_14j_avant"]), (14 * 10, 14 * 40))  # jours ≤ d0−8 seulement
            self.assertLess(m["valeur"], -1)
            self.assertFalse(ni.portwatch("FR", d0)["present"])
        finally:
            ni.PORTWATCH, ni._PW = ancien


if __name__ == "__main__":
    unittest.main()
