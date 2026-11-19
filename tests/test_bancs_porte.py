"""0.10.305 : bancs « correction finale à porte » (idée GraFT) — données synthétiques uniquement."""
import random

import banc_alphabet_correction as bac
import banc_graphe_questions as bgq
import banc_porte as bp


def test_score_centre_et_freins_inverse():
    tout4 = {k: {"note": 4} for k in bac.CLES}
    s = bac.score(tout4)
    assert abs(s - (6 * 1.5 - 1.5) / 7 / 1.5) < 1e-9         # freins à 4 = obstacles forts → pousse vers NON
    assert bac.score({k: 2 for k in bac.CLES[:6]}) is None    # note manquante
    neutre = {k: (2.5 if False else 2) for k in bac.CLES}
    assert bac.score(neutre) < 0


def test_porte_retombe_a_zero_sur_du_bruit():
    rnd = random.Random(1)
    ls = [{"question_id": f"m:{i}:2026-01-01", "issue": rnd.random() < 0.3, "p_S": 0.3, "c": 0.0} for i in range(80)]
    p, alpha, _ = bp.loo_porte(ls, "p_S", "c", bgq.GRILLE_ALPHA)
    assert alpha == 0.0 and all(abs(x - 0.3) < 1e-9 for x in p)


def test_porte_apprend_un_signal_vrai_sans_la_question():
    rnd = random.Random(2)
    ls = []
    for i in range(200):
        s = rnd.choice((-1.0, 1.0))
        ls.append({"question_id": f"m:{i}:2026-01-01", "issue": int(rnd.random() < (0.8 if s > 0 else 0.2)),
                   "p_A": 0.5, "score": s})
    p, alpha, aq = bp.loo_porte(ls, "p_A", "score", bac.GRILLE_ALPHA)
    assert alpha > 0.8 and len(aq) == 200
    assert bp.perte(ls, ps=p) < bp.perte(ls, "p_A")


def test_graphe_sans_fuite_et_meme_entite():
    xs = [{"source": "m", "id": "1", "jeu": "2026-01-01", "titre": "Will Vladimir Putin meet Xi Jinping?", "resolue_le": "2026-02-01",
           "cloture": "2026-02-01", "issue": 1, "p_S": 0.2},
          {"source": "m", "id": "2", "jeu": "2026-03-01", "titre": "Will Vladimir Putin visit Paris?", "resolue_le": "2026-06-01",
           "cloture": "2026-06-01", "issue": 0, "p_S": 0.4},
          {"source": "m", "id": "3", "jeu": "2026-03-01", "titre": "Will Emmanuel Macron resign?", "resolue_le": "2026-04-01",
           "cloture": "2026-04-01", "issue": 0, "p_S": 0.1}]
    c = {x["question_id"]: x for x in bgq.corrections(xs)}
    assert c["m:2:2026-03-01"]["n"] == 1 and abs(c["m:2:2026-03-01"]["c"] - 0.8 / 4) < 1e-9
    assert c["m:1:2026-01-01"]["n"] == 0                       # la 2 est résolue APRÈS le jeu de la 1 : pas de fuite
    assert c["m:3:2026-03-01"]["n"] == 0                       # aucune entité commune
