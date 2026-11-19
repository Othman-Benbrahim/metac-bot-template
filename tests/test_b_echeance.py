"""0.10.362 : B à l'échéance (report de la dernière observation, calendrier des observations)."""
from datetime import date, timedelta

import banc_forecastbench as fb


def _mensuelle(n_mois=60, fin=date(2026, 10, 1)):
    pts, d, v = [], fin, 100.0
    for i in range(n_mois):
        pts.append({"date": d.isoformat(), "valeur": v + (i % 2)})          # alterne : la moitié des mois en hausse
        d = (d.replace(day=1) - timedelta(days=1)).replace(day=1)
    return pts


def test_fenetre_sans_observation_donne_non():
    pts = _mensuelle()
    r = fb.b_echeance(pts, 7, date(2026, 10, 11))                          # (11 oct, 18 oct] : aucun 1er du mois
    assert r is not None and r["fenetre_avec_observation"] is False and r["p"] < 0.01
    b = fb.b_hausse(pts, 7, date(2026, 10, 11))
    assert 0.3 < b[0] < 0.7                                                 # l'ancien B y voit une chance sur deux


def test_fenetre_avec_observation():
    r = fb.b_echeance(_mensuelle(), 7, date(2026, 10, 28))                 # (28 oct, 4 nov] contient le 1er novembre
    assert r["fenetre_avec_observation"] is True and 0.3 < r["p"] < 0.7


def test_ecart_inconnu():
    pts = [{"date": (date(2020, 1, 1) + timedelta(days=50 * i)).isoformat(), "valeur": float(i)} for i in range(40)]
    assert fb.b_echeance(pts, 7, date(2026, 1, 1)) is None
