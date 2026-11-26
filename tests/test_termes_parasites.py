from mise_au_point.termes_parasites import analyser


def test_terme_isole_signale_et_terme_coherent_garde():
    termes = {"agreement": {"dette-emergents:gisements"}, "ceasefire": {"russie-ukraine:negociations"},
              "Ukraine": {"russie-ukraine:front"}, "nuclear": {"energie:nucleaire"}}
    T = [f"Will Ukraine agree to a ceasefire agreement number {i} on nuclear plants?" for i in range(6)]
    par, _ = analyser(T, termes)
    noms = [p[0] for p in par]
    assert "agreement" in noms and "ceasefire" not in noms
