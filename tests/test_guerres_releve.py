import datetime as dt

import guerres_releve as gr


def test_garde_seulement_les_faits_dates_et_sources():
    rech = "… https://exemple.org/a … https://exemple.org/b …"
    rep = ('{"type": "inter", "debut": {"date": "2026-02-28", "source": "https://exemple.org/a"},'
           ' "cessez_le_feu": {"date": "2026-04-07", "source": "https://ailleurs.org/x"},'
           ' "rupture": {"date": "2030-01-01", "source": "https://exemple.org/b"}}')
    f = gr.analyser(rep, rech, dt.date(2026, 11, 24), "releve:iran_us")
    assert [x["evenement"] for x in f] == ["debut"]        # source absente et date future rejetées


def test_ecrire_sans_doublon(tmp_path):
    c = tmp_path / "r.csv"
    x = {"guerre": "g", "type": "inter", "date": "2026-01-01", "evenement": "debut", "source": "https://a",
         "releve_le": "2026-11-24"}
    gr.ecrire([x], c)
    gr.ecrire([x], c)
    assert len(gr.charger(c)) == 1
