"""0.10.464 : mécanique de bascule en ombre (étape 1) — étincelles, journal à ajout seul, issues, score. Sans réseau."""
import csv
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

import mecanique as m


def serie(n_semaines: int, pic: int | None = None, suite_elevee: int = 0, debut=date(2025, 1, 6)):
    """Part 0,01 chaque semaine (1 000 événements, 10 manifestations) ; pic à 0,03 à l'indice pic ; puis suite_elevee
    semaines à 0,02 (≥ 1,5 × 0,01)."""
    rows = []
    for k in range(n_semaines):
        manifs = 10
        if pic is not None and k == pic:
            manifs = 30
        elif pic is not None and pic < k <= pic + suite_elevee:
            manifs = 20
        rows.append({"pays": "XX", "semaine": (debut + timedelta(weeks=k)).isoformat(), "evenements": 1000,
                     "manifs": manifs, "manifs_racine": 0, "articles_manifs": 0})
    return rows


def ecrire(rows, chemin):
    with open(chemin, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


class TestMecanique(unittest.TestCase):
    def test_etincelle_inscrite_puis_issue(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "s.csv"
            ecrire(serie(70, pic=60, suite_elevee=6), f)
            series = m.lire_series(f)
            semaine_pic = date(2025, 1, 6) + timedelta(weeks=60)
            # le lundi qui suit la semaine du pic : seule la semaine du pic est « dernière semaine complète »
            auj = semaine_pic + timedelta(weeks=1, days=2)
            neuves = m.inscrire(series, [], auj)
            self.assertEqual([r["semaine"] for r in neuves], [semaine_pic.isoformat()])
            self.assertAlmostEqual(float(neuves[0]["p_prend"]), m.TAUX_DEPART, places=3)
            # pas d'issue tant que les 8 semaines ne sont pas complètes
            self.assertEqual(m.constater(series, neuves, [], auj), [])
            # neuf semaines plus tard : issue « prend » (6 semaines élevées ≥ 4)
            plus_tard = semaine_pic + timedelta(weeks=9, days=1)
            iss = m.constater(series, neuves, [], plus_tard)
            self.assertEqual(iss[0]["prend"], 1)
            self.assertEqual(iss[0]["semaines_elevees"], 6)
            sc = m.score(neuves, iss)
            self.assertEqual(sc["constatees"], 1)
            self.assertAlmostEqual(sc["brier"], (1 - m.TAUX_DEPART) ** 2, places=3)

    def test_pas_de_rattrapage(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "s.csv"
            ecrire(serie(70, pic=60), f)
            series = m.lire_series(f)
            auj = date(2025, 1, 6) + timedelta(weeks=63, days=2)      # deux semaines trop tard
            self.assertEqual(m.inscrire(series, [], auj), [])

    def test_ajout_seul(self):
        with tempfile.TemporaryDirectory() as d:
            j = Path(d) / "j.csv"
            m.ajouter(j, ["id", "x"], [{"id": "a", "x": 1}])
            m.ajouter(j, ["id", "x"], [{"id": "b", "x": 2}])
            self.assertEqual([r["id"] for r in m.lire_csv(j)], ["a", "b"])

    def test_codes_pays(self):
        self.assertEqual(m.codes_iso3().get("GM"), "DEU")


if __name__ == "__main__":
    unittest.main()
