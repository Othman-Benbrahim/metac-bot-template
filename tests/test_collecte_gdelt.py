"""0.10.173 : comptes GDELT de manifestations et indicateur dans l'observatoire."""
import os
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

os.environ["ALPHABET_REGISTRE"] = tempfile.mkdtemp(prefix="registre-")
import collecte_gdelt as cg
import indicateurs_niche as ni


def ligne(racine, base, pays, articles=1):
    col = [""] * 58
    col[cg.C_RACINE], col[cg.C_BASE], col[cg.C_PAYS_ACTION], col[cg.C_ARTICLES] = racine, base, pays, str(articles)
    return "\t".join(col)


class TestGdelt(unittest.TestCase):
    def test_compter(self):
        texte = "\n".join([ligne("14", "141", "UP", 3), ligne("14", "145", "UP", 2), ligne("19", "190", "UP"),
                           ligne("14", "141", "XX"), ligne("14", "145", "GM")])
        out = cg.compter(texte, {"UP": "UA", "GM": "DE"})
        self.assertEqual(out, {"UA": [2, 1, 5], "DE": [1, 1, 1]})

    def test_indicateur(self):
        d = Path(tempfile.mkdtemp())
        ancien = (ni.GDELT_COMPTES, ni.GDELT_JOURS, ni._GDELT)
        ni.GDELT_COMPTES, ni.GDELT_JOURS, ni._GDELT = d / "c.csv", d / "j.txt", None
        try:
            d0 = date(2026, 10, 1)
            jours = [(d0 - timedelta(days=k)).isoformat() for k in range(1, 29)]
            ni.GDELT_JOURS.write_text("\n".join(jours[:27]))           # un jour manquant : toléré
            ni.GDELT_COMPTES.write_text("pays,jour,manifestations,emeutes,articles\n"
                                        f"UA,{jours[0]},9,4,20\nUA,{jours[20]},2,0,3\n")
            m = ni.gdelt("UA", d0)
            self.assertTrue(m["present"])
            self.assertEqual((m["manifestations_14j"], m["manifestations_14j_avant"], m["emeutes_14j"]), (9, 2, 4))
            self.assertAlmostEqual(m["valeur"], 1.204, places=3)
            ni._GDELT = None
            ni.GDELT_JOURS.write_text("\n".join(jours[:20]))
            self.assertFalse(ni.gdelt("UA", d0)["present"])
        finally:
            ni.GDELT_COMPTES, ni.GDELT_JOURS, ni._GDELT = ancien


if __name__ == "__main__":
    unittest.main()
