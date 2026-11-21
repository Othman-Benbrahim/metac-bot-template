import random

import decision_institution as di


def test_indicateurs():
    x = di.indicateurs({"etape_avant_echeance": "prevue", "soutien": "insuffisant", "regle": "deux_parties",
                        "confirmation": "une_partie", "deja_decide": "non"})
    assert x == {"etape": 1.0, "soutien": -1.0, "regle": -1.0, "confirmation_deux": 0.0, "confirmation_une": 1.0,
                 "deja_decide": 0.0}
    vide = di.indicateurs({"etape_avant_echeance": "inconnu", "regle": "inconnue", "soutien": "inconnu"})
    assert not di.utilisable(vide)
    assert di.est_decision("Will the Senate pass the SAVE Act?", "echeance")
    assert not di.est_decision("Will the Senate pass the SAVE Act?", "election")
    assert not di.est_decision("Will Bitcoin reach $150k?", "seuil")


def test_validation_croisee_retrouve_un_effet():
    r = random.Random(0)
    ls = []
    for i in range(300):
        e = r.choice([1.0, -1.0, 0.0])
        p = {1.0: 0.7, -1.0: 0.05, 0.0: 0.25}[e]
        x = dict.fromkeys(di.INDICATEURS, 0.0)
        x["etape"] = e
        ls.append({"question_id": f"q{i}", "p_S": 0.25, "issue": int(r.random() < p), "x": x})
    p = di.validation_croisee(ls)
    import math
    pl = lambda q, y: -math.log(q if y else 1 - q)
    assert sum(pl(q, l["issue"]) for q, l in zip(p, ls)) < sum(pl(0.25, l["issue"]) for l in ls)
    assert di.coefficients(ls)["etape"] > 0.5


def test_sans_fait_rend_le_taux_de_depart():
    ls = [{"question_id": f"q{i}", "p_S": 0.2, "issue": i % 5 == 0, "x": dict.fromkeys(di.INDICATEURS, 0.0)}
          for i in range(50)]
    assert all(abs(p - 0.2) < 1e-9 for p in di.validation_croisee(ls))
