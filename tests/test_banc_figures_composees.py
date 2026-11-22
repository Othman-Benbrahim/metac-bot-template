import banc_figures_composees as bfc
import banc_jugement_alphabet as bja

Q = {"titre": "Will X win?", "cloture": "2026-12-01", "criteres": "c", "contexte": "ctx"}


def test_consigne_notes10_garde_les_sept_et_ajoute_les_figures():
    t = bfc.consigne_notes10(bja, Q, 0.3, "recherche", "2026-07-01")
    for k in bja.CLES + bfc.CLES_FIG:
        assert f'"{k}"' in t
    assert t.rstrip().endswith("}") or "Rends UNIQUEMENT" in t
    assert t.index("COMPÉTITION") < t.index("Rends UNIQUEMENT")


def test_lire_figures_bornes_et_sens():
    r = {"notes": {"competition": {"note": 4, "sens": "OUI", "pourquoi": "p"}, "intention": {"note": 7},
                   "convention": {"note": "2", "sens": "bizarre"}}}
    f = bfc.lire_figures(r)
    assert f["competition"]["note"] == 4 and f["competition"]["sens"] == "oui"
    assert "intention" not in f
    assert f["convention"]["sens"] == "neutre"


def test_finale10_contient_les_figures_avant_la_recherche():
    notes = {k: {"note": 2, "pourquoi": ""} for k in bja.CLES}
    figs = {k: {"note": 3, "sens": "non", "pourquoi": "w"} for k in bfc.CLES_FIG}
    t = bfc.consigne_finale10(bja, Q, 0.3, notes, figs, "recherche", "2026-07-01")
    assert t.index("FIGURES COMPOSÉES") < t.index("RÉSULTATS DE RECHERCHE")
    assert "pousse vers NON" in t


def test_resumer_vide_et_essai_declare():
    import essais
    assert essais.ESSAIS["figures_composees"]["statut"] == "ouvert"
    assert bfc.resumer([])["n"] == 0
