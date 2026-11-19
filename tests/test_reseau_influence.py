"""0.10.347 : influence × connexion (modèle synthétique)."""
import numpy as np

import reseau_influence as ri


def test_couches_et_petit_monde():
    isole = ri.construire(1500, p_loin=0.0)
    relie = ri.construire(1500, p_loin=0.2)
    assert abs(isole["A"].nnz / 1500 - 149) < 2                          # 5 + 10 + 35 + 100 liens (moins soi-même)
    d0, d1 = ri.degres(isole, 30), ri.degres(relie, 30)
    assert d0["part_atteinte"]["4_pas"] < 0.15                            # sans liens lointains : communautés fermées
    assert d1["part_atteinte"]["3_pas"] > 0.95                            # 20 % de liens lointains : petit monde


def test_influence_et_connexion_se_renforcent():
    res = ri.construire(4000, p_loin=0.2)
    med = ri.medias(4000)
    sans = ri.diffuser(res, med, aligne=0, mu=0.5, graines_influentes=True)
    avec = ri.diffuser(res, med, aligne=3, mu=0.5, graines_influentes=True)
    assert avec["part_adoptants"] > sans["part_adoptants"] + 0.2
    assert avec["part_par_les_medias_seuls"] < 0.1                         # les médias seuls convainquent peu
    ferme = ri.diffuser(ri.construire(4000, p_loin=0.0), med, aligne=3, mu=0.5, graines_influentes=True)
    assert avec["part_adoptants"] >= ferme["part_adoptants"]


def test_concentration_des_medias():
    med = ri.medias(1000)
    assert 0 < med["hhi"] <= 1 and np.isclose(med["part_audience_proprietaire"].sum(), 1.0)
