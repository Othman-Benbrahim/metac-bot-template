"""0.10.381 : conversion de forecasting_raw au format du registre."""
import collecte_forecasting_raw as cf


def test_convertir():
    ls = [{"question_type": "binary", "is_resolved": True, "resolution": 0.0, "date_begin": "2017-11-07",
           "date_close": "2018-01-01", "date_resolve_at": "2018-01-11", "url": "https://www.gjopen.com/questions/683",
           "question": "Before 1 January 2018, will Russia and Egypt sign an agreement?", "data_source": "gjopen",
           "background": "secret", "community_predictions": [["2017-11-07", 0.24]]},
          {"question_type": "multiple_choice", "is_resolved": True, "resolution": 1.0, "date_begin": "2018-01-01"},
          {"question_type": "binary", "is_resolved": True, "resolution": 0.5, "date_begin": "2018-01-01", "date_close": "2018-02-01"}]
    xs = cf.convertir(ls)
    assert len(xs) == 1
    x = xs[0]
    assert x["source"] == "gjopen" and x["id"] == "683" and x["horizon"] == 55 and x["issue"] == 0
    assert "background" not in x and "community_predictions" not in x


def test_formats():
    assert cf._jour(1510012800) == "2017-11-07" and cf._jour(1510012800000) == "2017-11-07"
    xs = cf.convertir([{"question_type": "Binary", "is_resolved": "True", "resolution": "YES", "date_begin": 1510012800000,
                        "date_close": "2018-01-01", "date_resolve_at": None, "url": "https://manifold.markets/x/abc",
                        "question": "q", "data_source": "manifold"}])
    assert xs and xs[0]["issue"] == 1 and xs[0]["jeu"] == "2017-11-07"
