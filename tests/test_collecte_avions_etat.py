"""0.10.180 : avions d'État, liste et comptes par pays."""
import os
import tempfile
import unittest

os.environ["ALPHABET_REGISTRE"] = tempfile.mkdtemp(prefix="registre-")
import collecte_avions_etat as ca


class TestAvionsEtat(unittest.TestCase):
    def test_liste(self):
        texte = ("$ICAO,$Registration,$Operator,$Type,$ICAO Type,#CMPG,$Tag 1,$#Tag 2,$#Tag 3,Category,$#Link\n"
                 "4B1805,HB-X,Gov,Jet,GLF6,Gov,a,b,c,Dictator Alert,\n"
                 "ABC123,N1,USAF,Jet,C17,Mil,a,b,c,USAF,\n")
        self.assertEqual(ca.avions(texte), ["4b1805"])

    def test_compter(self):
        aero = {"LSGG": "CH", "UUEE": "RU", "OMDB": "AE"}
        vols = [{"estDepartureAirport": "UUEE", "estArrivalAirport": "LSGG"},
                {"estDepartureAirport": "LSGG", "estArrivalAirport": "LSGG"},
                {"estDepartureAirport": None, "estArrivalAirport": "OMDB"}]
        self.assertEqual(ca.compter(vols, aero), {"CH": [1, 0], "RU": [0, 1]})


if __name__ == "__main__":
    unittest.main()
