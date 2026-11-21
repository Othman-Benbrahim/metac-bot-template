import math
import random

from mise_au_point import taille_mises_a_jour_m as t


def test_k_retrouve_un_m_trop_sur():
    random.seed(3)
    xs = []
    for i in range(300):
        pb = 0.3
        vrai = 1 / (1 + math.exp(-(math.log(pb / (1 - pb)) + random.gauss(0, 1))))
        z_m = math.log(pb / (1 - pb)) + 2 * (math.log(vrai / (1 - vrai)) - math.log(pb / (1 - pb)))   # M bouge deux fois trop
        xs.append({"jeu": f"2026-{1 + i // 30:02d}-01", "p_B": pb, "p_M": 1 / (1 + math.exp(-z_m)),
                   "issue": int(random.random() < vrai), "question_id": f"m:{i}:x"})
    assert 0.3 <= t.meilleur_k(xs) <= 0.75
    r = t.evaluer(xs, tirages=300)
    assert r["n_juge"] > 0 and r["ecart"] < 0


def test_une_par_question_garde_le_premier_jeu():
    ls = [{"question_id": "m:1:b", "jeu": "2026-02-01", "p_M": .4, "p_B": .3, "issue": 0},
          {"question_id": "m:1:a", "jeu": "2026-01-01", "p_M": .5, "p_B": .3, "issue": 0}]
    assert t.une_par_question(ls)[0]["jeu"] == "2026-01-01"
