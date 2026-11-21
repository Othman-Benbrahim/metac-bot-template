"""Test placebo avant d'inscrire une règle comme brique (piste du skill d'inférence causale de Learning Bayesian
Statistics : pas de « cause » sans test de réfutation ; décision de l'auteur du 2026-11-21, 12 h 53). Aucun appel de
modèle.

Idée : une règle qui capte un vrai mécanisme ne doit faire gagner des points QUE sur les questions dont l'événement est
son objet (cas homologues). Si elle en fait gagner autant sur des questions hors de son objet, son gain ne vient pas
du mécanisme mais d'un effet générique (par exemple un simple rétrécissement vers le taux de base : c'est ce qu'avait
montré la mise au point de la brique « fenêtre » le 2026-11-20, où le témoin « mélange avec le taux de base » faisait
aussi bien).

Entrée : pour chaque question, la perte log avec la règle et sans elle, et si la question est dans l'objet de la règle
(par exemple d'après la carte de couverture v4). Sortie :
- gain moyen dans l'objet et hors de l'objet (perte sans − perte avec : positif = la règle aide) ;
- écart entre les deux et sa probabilité sous permutation des étiquettes (le hasard ferait-il un écart aussi grand ?) ;
- lecture : « spécifique » (aide dans l'objet, pas au-dehors, écart improbable par hasard), « générique » (aide aussi
  au-dehors), « sans effet » ou « indéterminé ». Une règle « générique » ne s'inscrit pas comme brique de mécanisme.
"""
from __future__ import annotations

import numpy as np


def placebo(perte_avec: list[float], perte_sans: list[float], dans_objet: list[bool], tirages: int = 5000,
            graine: int = sum(map(ord, "placebo"))) -> dict:
    a, s = np.asarray(perte_avec, dtype=float), np.asarray(perte_sans, dtype=float)
    m = np.asarray(dans_objet, dtype=bool)
    g = s - a                                        # gain par question
    if m.sum() < 5 or (~m).sum() < 5:
        return {"lecture": "indéterminé (moins de 5 questions d'un côté)", "n_objet": int(m.sum()), "n_hors": int((~m).sum())}
    ecart = float(g[m].mean() - g[~m].mean())
    rng = np.random.default_rng(graine)
    perm = np.empty(tirages)
    for k in range(tirages):
        mm = rng.permutation(m)
        perm[k] = g[mm].mean() - g[~mm].mean()
    p = float((np.abs(perm) >= abs(ecart)).mean())
    se = lambda x: float(x.std(ddof=1) / np.sqrt(len(x)))
    dedans, dehors = float(g[m].mean()), float(g[~m].mean())
    aide_dedans = dedans > 1.645 * se(g[m])
    aide_dehors = dehors > 1.645 * se(g[~m])
    if aide_dedans and not aide_dehors and p < 0.10:
        lecture = "spécifique : la règle aide dans son objet et pas au-dehors"
    elif aide_dehors:
        lecture = "générique : la règle aide aussi hors de son objet (effet non lié au mécanisme)"
    elif not aide_dedans and not aide_dehors:
        lecture = "sans effet net"
    else:
        lecture = "indéterminé"
    return {"n_objet": int(m.sum()), "n_hors": int((~m).sum()), "gain_dans_objet": round(dedans, 4),
            "gain_hors_objet": round(dehors, 4), "ecart": round(ecart, 4), "p_permutation": round(p, 4),
            "lecture": lecture}
