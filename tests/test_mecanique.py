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


class TestModules(unittest.TestCase):
    def ctx(self, articles):
        return {"articles": {"XX": articles}, "elections": {"XX": ["2025-03-20"]},
                "acte": {"curfew"}, "fait_passe": {"anniversary"}}

    def test_modules_orientes(self):
        sem = "2025-03-03"
        arts = [{"jour": "2025-03-04", "emetteur": "a", "officiel": True, "termes": ["curfew"]},
                {"jour": "2025-03-05", "emetteur": "b", "officiel": False, "termes": ["anniversary"]},
                {"jour": "2025-03-06", "emetteur": "b", "officiel": False, "termes": []}]
        x = m.modules("XX", sem, self.ctx(arts))
        self.assertEqual(x["corroboration"], 1.0)
        self.assertEqual(x["signal_faible"], 0.0)
        self.assertAlmostEqual(x["rang_emetteur"], 0.333, places=3)
        self.assertEqual(x["acte_haut_rang"], 1.0)
        self.assertAlmostEqual(x["fait_passe"], -0.333, places=3)
        self.assertEqual(x["echeance"], 1.0)
        # un signal faible : un seul article officiel, rien dans les 30 jours avant
        x2 = m.modules("XX", sem, self.ctx(arts[:1]))
        self.assertEqual(x2["signal_faible"], 1.0)
        # absence d'articles : zéros (pas un signe contraire)
        x3 = m.modules("YY", sem, self.ctx(arts))
        self.assertEqual(sum(abs(v) for v in x3.values()), 0.0)

    def test_boucle(self):
        etat = {"poids": {k: m.POIDS_DEPART for k in m.MODULES}, "appris_sur": []}
        j = [{"id": "a", "modules": '{"corroboration": 1.0}'}, {"id": "b", "modules": "{}"}]
        n = m.apprendre(etat, j, [{"id": "a", "prend": "1"}, {"id": "b", "prend": "0"}])
        self.assertEqual(n, 1)
        self.assertGreater(etat["poids"]["corroboration"], m.POIDS_DEPART)
        self.assertEqual(m.apprendre(etat, j, [{"id": "a", "prend": "1"}]), 0)     # une seule fois par issue


class TestEValeur(unittest.TestCase):
    def test_nulle_et_meilleure(self):
        # mécanique identique au taux de départ : e-valeur 1
        j = [{"id": str(i), "p_prend": str(m.TAUX_DEPART)} for i in range(30)]
        iss = [{"id": str(i), "prend": str(i % 3 == 0), "constate_le": "2027-01-11"} for i in range(30)]
        iss = [dict(r, prend="1" if r["prend"] == "True" else "0") for r in iss]
        self.assertEqual(m.e_valeur(j, iss)["e_valeur"], 1.0)
        # mécanique nettement meilleure : l'e-valeur franchit le seuil
        j2 = [{"id": str(i), "p_prend": "0.9" if i % 3 == 0 else "0.05"} for i in range(60)]
        iss2 = [{"id": str(i), "prend": "1" if i % 3 == 0 else "0", "constate_le": "2027-01-%02d" % (1 + i % 28)}
                for i in range(60)]
        e = m.e_valeur(j2, iss2)
        self.assertGreaterEqual(e["e_max"], m.E_SEUIL)
        self.assertTrue(e["e_franchi_le"])
        # mécanique pire : la mise reste nulle, l'e-valeur ne monte pas
        j3 = [{"id": str(i), "p_prend": "0.05" if i % 3 == 0 else "0.9"} for i in range(60)]
        self.assertLessEqual(m.e_valeur(j3, iss2)["e_max"], 1.0)


class TestControles(unittest.TestCase):
    def test_calibration_sous_ensembles_surprises(self):
        j = [{"id": "GM-2027-01-04", "pays": "GM", "semaine": "2027-01-04", "p_prend": "0.2"},
             {"id": "NI-2027-01-11", "pays": "NI", "semaine": "2027-01-11", "p_prend": "0.7"},
             {"id": "NI-2027-01-18", "pays": "NI", "semaine": "2027-01-18", "p_prend": "0.3"}]
        iss = [{"id": "GM-2027-01-04", "prend": "1", "constate_le": "2027-03-08"},
               {"id": "NI-2027-01-11", "prend": "0", "constate_le": "2027-03-15"},
               {"id": "NI-2027-01-18", "prend": "0", "constate_le": "2027-03-22"}]
        c = m.controles(j, iss)
        self.assertEqual(sum(t["n"] for t in c["calibration"]), 3)
        self.assertIn("Europe", c["sous_ensembles"]["regions"])
        self.assertIn("Afrique", c["sous_ensembles"]["regions"])
        self.assertEqual(c["surprises"]["nombre"], 2)
        self.assertEqual(m.controles(j, [])["calibration"], [])
