"""0.10.130 : garde-fou sur B."""
import unittest

import audit_b as a


def ligne(i, jeu, p, issue, dix=True):
    t = ("Will there be more than ten times as many 'Riots' in X for the 30 days before 2026-08-01 compared to one plus"
         if dix else "Will there be more 'Riots' in X for the 30 days before 2026-08-01 compared to the 30-day average")
    return {"question_id": f"q{i}", "jeu": jeu, "titre": t, "source_question": "acled", "p_B": p, "issue": issue,
            "version_bot": "0.10.130"}


class TestAudit(unittest.TestCase):
    def test_erreur_repetee_signalee(self):
        ls = [ligne(i, f"2026-0{1 + i % 4}-01", 0.4, 0) for i in range(40)]
        r = a.auditer(ls)
        self.assertTrue(any("dix fois · (tous types)" in x for x in r["alertes"]))

    def test_b_juste_silencieux(self):
        ls = [ligne(i, f"2026-0{1 + i % 4}-01", 0.25, int(i % 4 == 0), dix=False) for i in range(80)]
        self.assertEqual(a.auditer(ls)["alertes"], [])

    def test_mouvement_commun_a_surveiller(self):
        ls = [ligne(i, "2026-01-01" if i < 15 else "2026-02-01", 0.5, 0) for i in range(30)]
        r = a.auditer(ls)
        self.assertEqual(r["alertes"], [])
        self.assertTrue(r["a_surveiller"])

    def test_pour_resume_ignore_les_lignes_anciennes(self):
        ls = [dict(ligne(i, f"2026-0{1 + i % 4}-01", 0.4, 0), version_bot="0.10.120") for i in range(40)]
        self.assertEqual(a.pour_resume(ls)["alertes"], [])


if __name__ == "__main__":
    unittest.main()
