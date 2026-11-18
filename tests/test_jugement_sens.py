import unittest

import numpy as np

import banc_jugement_sens as bs


def q(i, jeu, res, y, src="metaculus"):
    return {"source": src, "id": str(i), "jeu": jeu, "resolue_le": res, "cloture": res, "issue": y, "p_R1": 0.3,
            "p_S": 0.3, "titre": f"t{i}"}


class TSens(unittest.TestCase):
    def test_voisines_proches_et_anterieures(self):
        xs = [q(0, "2026-03-01", "2026-06-01", 1), q(1, "2025-01-01", "2025-02-01", 1),
              q(2, "2025-01-01", "2025-02-01", 0), q(3, "2025-01-01", "2026-05-01", 1)]
        V = np.array([[1, 0], [1, 0], [0, 1], [1, 0]], dtype=np.float32)   # 3 : proche mais résolue après le jeu
        bs.calculer_sens(xs, V)
        attendu = (1.0 * 1 + 0.0 * 0 + 5 * 0.3) / (1.0 + 0.0 + 5)
        self.assertAlmostEqual(xs[0]["p_SE"], attendu)

    def test_resume(self):
        xs = [dict(q(i, "2026-02-01" if i % 2 else "2025-05-01", "2025-01-01", i % 3 == 0), p_SE=0.25) for i in range(40)]
        r = bs.resumer(xs)
        self.assertIn(r["confirmation_2026"]["verdict"], ("sens meilleur", "sens moins bon", "non tranché"))
        self.assertIn("verdict_final", r)


if __name__ == "__main__":
    unittest.main()
