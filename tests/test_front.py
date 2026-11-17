import csv
import gzip
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

import banc_front as bf


class T(unittest.TestCase):
    def test_voisins(self):
        g = 100 * 720 + 50 + 1
        v = bf.voisins_cellule(g)
        self.assertEqual(len(v), 8)
        self.assertIn(g + 1, v)
        self.assertIn(g + 720, v)
        self.assertEqual(len(bf.voisins_cellule(1)), 5)       # bord sud, colonne repliée

    def test_front(self):
        d0 = date(2020, 6, 1)
        g = 100 * 720 + 50 + 1
        cel = {(d0 - timedelta(days=100)).isoformat(): {g},
               (d0 - timedelta(days=10)).isoformat(): {g + 1, g + 2, g + 720}}
        self.assertEqual(bf.front(cel, d0), 1)               # g+1 et g+720 touchent g ; g+2 non
        cel2 = {(d0 - timedelta(days=10)).isoformat(): {g + 1, g + 2}}
        self.assertEqual(bf.front(cel2, d0), 0)

    def test_chaine(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "c.csv.gz"
            with gzip.open(p, "wt", encoding="utf-8", newline="") as f:
                w = csv.writer(f)
                w.writerow(["pays", "jour", "cellule", "evenements", "morts"])
                d = date(2015, 1, 1)
                while d < date(2025, 6, 1):
                    if d.day % 3 == 0:
                        w.writerow(["A", d.isoformat(), 51000 + (d.month % 3), 1 + d.month % 4, 1])
                        w.writerow(["B", d.isoformat(), 61000, 2, 1])
                    d += timedelta(days=1)
            ev, cel = bf.charger(p)
            xs = bf.questions(ev, cel, date(2025, 5, 31))
            self.assertTrue(xs)
            r = bf.juger(xs)
            self.assertIn("reference_confirmation", r)


if __name__ == "__main__":
    unittest.main()


class TRichardson(unittest.TestCase):
    def test_hill_et_questions(self):
        import random
        import banc_richardson_evenements as br
        rnd = random.Random(0)
        tailles = [10 * (1 - rnd.random()) ** (-1 / 1.5) for _ in range(2000)]
        a = br.hill(tailles)
        self.assertTrue(1.2 < a < 1.8)
        par, tous = {}, []
        d = date(2015, 1, 1)
        while d < date(2025, 3, 1):
            if rnd.random() < 0.3:
                t = float(int(1 + 10 * (1 - rnd.random()) ** (-1 / 1.2)))
                par.setdefault("A", {}).setdefault(d.isoformat(), []).append(t)
                tous.append((d.isoformat(), t))
            d += timedelta(days=1)
        tous.sort()
        xs = br.questions(par, tous, date(2025, 2, 28), 100)
        self.assertTrue(xs)
        self.assertIn("confirmation", br.resumer(xs, True))
