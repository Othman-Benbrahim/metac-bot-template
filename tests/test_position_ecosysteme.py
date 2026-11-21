import random

import banc_position_ecosysteme as bp
import couverture_regles as cr


def test_consigne_et_placebo():
    cat = cr.catalogue()
    q = {"titre": "Will the Fed raise rates?", "cloture": "2026-07-30", "criteres": "c", "contexte": "x"}
    s = bp.consigne_avec_regles(q, 0.3, {}, "recherche", "2026-06-01", bp.bloc_regles(["us_fed_calendrier"], cat))
    assert "RÈGLES SOURCÉES" in s and s.index("RÈGLES SOURCÉES") < s.index("Pars du taux de base.")
    assert cat["us_fed_calendrier"]["situation"] in s
    plac = bp.placebo(["us_fed_calendrier", "us_senat_cloture"], cat, random.Random(1))
    assert len(plac) == 2 and all(cat[i]["objet"] not in {cat["us_fed_calendrier"]["objet"], cat["us_senat_cloture"]["objet"]} for i in plac)


def test_resumer_adoption():
    ls = [{"issue": i % 2, "p_B": 0.5, "p_M0": 0.5, "p_M1": 0.8 if i % 2 else 0.2, "p_M2": 0.5} for i in range(40)]
    r = bp.resumer(ls)
    assert r["adopte"] and r["M1_moins_M0"] < 0
