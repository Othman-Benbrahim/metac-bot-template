"""Suivi en avant des liens d'acteurs (2026-11-20)."""
import liens_acteurs as la
import suivi_liens as sl


def test_motifs_portent_sur_des_liens_existants():
    ids = {x["id"] for x in la.liens()}
    assert set(sl.MOTIFS) <= ids


def test_reconnaissance():
    assert "ht_elections_reportees" in sl.liens_de("Will Haiti hold the first round of its presidential election before 2027?")
    assert "us_loi_depend_du_congres" not in sl.liens_de("Will Argentina's Senate give media sanción to a bill?")
    assert "us_cour_supreme_session_annuelle" in sl.liens_de("Will the U.S. Supreme Court rule in Louisiana v. Callais?")
