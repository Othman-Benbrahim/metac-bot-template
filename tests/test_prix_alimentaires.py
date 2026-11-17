"""0.10.214 : prix alimentaires en temps réel (Banque mondiale, RTFP), avec millésimes."""
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

import collecte_prix_alimentaires as cp
import indicateurs_niche as ni

CSV = ("Open,High,Low,Close,Inflation,country,ISO3,price_date\n"
       "1,1,1,1.00,,Afghanistan,AFG,10/01/2025\n"
       "1,1,1,1.20,0.2,Afghanistan,AFG,10/01/2026\n"
       "1,1,1,1.10,,Afghanistan,AFG,07/01/2026\n"
       "1,1,1,1.00,,Afghanistan,AFG,07/01/2025\n"
       "1,1,1,2.0,,Nulle part,XXX,10/01/2026\n")


class TestRTFP(unittest.TestCase):
    def test_choisir(self):
        res = [{"resource_id": 7, "title": "Documentation", "filename": "doc.pdf"},
               {"resource_id": 9, "title": "Data", "filename": "WLD_RTFP_country_2026-11-02.csv"}]
        self.assertEqual(cp.choisir(res), ("9", "2026-11-02"))

    def test_choisir_plus_recente(self):
        res = [{"resource_id": 1, "filename": "WLD_RTFP_country_2023-06-06.zip"},
               {"resource_id": 3, "filename": "WLD_RTFP_country_2026-11-09.zip"},
               {"resource_id": 2, "filename": "WLD_RTFP_country_2025-01-06.zip"}]
        self.assertEqual(cp.choisir(res), ("3", "2026-11-09"))
        self.assertEqual(len(cp.versions(res)), 3)

    def test_recentes(self):
        xs = [{"pays": "AF", "mois": m} for m in ("2026-10", "2025-05", "2025-04", "2024-01")]
        self.assertEqual([x["mois"] for x in cp.recentes(xs, 18)], ["2026-10", "2025-05"])

    def test_lire(self):
        xs = cp.lire_rtfp(CSV, {"AFG": "AF"}, "2026-11-02")
        self.assertEqual(len(xs), 4)
        self.assertEqual(xs[1], {"version": "2026-11-02", "pays": "AF", "mois": "2026-10", "close": "1.20", "inflation": "0.2"})

    def test_indicateur_millesime(self):
        with tempfile.TemporaryDirectory() as t:
            f = Path(t) / "p.csv"
            lignes = ["version,pays,mois,close,inflation"]
            for x in cp.lire_rtfp(CSV, {"AFG": "AF"}, "2026-11-02"):
                lignes.append(",".join(x[k] for k in cp.CHAMPS))
            f.write_text("\n".join(lignes) + "\n", encoding="utf-8")
            with mock.patch.object(ni, "PRIX_ALIMENTAIRES", f):
                r = ni.prix_alimentaires("AF", date(2026, 11, 10))
                self.assertEqual((r["valeur"], r["acceleration_3m"], r["mois"]), (20.0, 10.0, "2026-10"))
                # version publiée APRÈS la date : jamais lue (pas de fuite)
                self.assertFalse(ni.prix_alimentaires("AF", date(2026, 11, 1))["present"])
                self.assertFalse(ni.prix_alimentaires("FR", date(2026, 11, 10))["present"])


if __name__ == "__main__":
    unittest.main()
