"""0.10.336 : banc du rédacteur de questions."""
import numpy as np

import banc_redacteur as br


def test_traits_et_ajustement():
    x = {"source": "metaculus", "titre": "Will the minister remain in office by 2027?", "horizon": 60}
    v = br.traits(x)
    assert len(v) == 1 + 3 + 4 + 2 + 1 + 1 + 5 + 1 and v[0] == 1.0
    rng = np.random.default_rng(0)
    X = np.c_[np.ones(2000), rng.normal(size=2000)]
    y = (rng.random(2000) < 1 / (1 + np.exp(-(0.5 + 2 * X[:, 1])))).astype(float)
    w = br.ajuster(X, y, lam=0.0)
    assert abs(w[0] - 0.5) < 0.2 and abs(w[1] - 2) < 0.3


def test_pas_de_fuite():
    xs = [{"source": "metaculus", "id": str(i), "jeu": "2026-02-01" if i >= 60 else "2025-06-01", "titre": f"Will thing {i % 2} happen?",
           "horizon": 30, "resolue_le": "2025-07-01" if i < 60 else "2026-03-01", "cloture": "2025-07-01" if i < 60 else "2026-03-03",
           "issue": i % 2, "p_R1": 0.3} for i in range(80)]
    br.predire(xs)
    assert all(0.02 <= x["p_R"] <= 0.98 for x in xs)
    assert all(x["p_R"] == 0.3 for x in xs if x["jeu"] == "2025-06-01")      # aucun passé admis : repli sur R1
