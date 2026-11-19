import collecte_tfr as ct


def test_lignes_dedoublonne_et_tronque():
    d = [{"notam_id": "6/8739", "type": "SPECIAL", "facility": "ZLA", "state": "USA", "description": " x" * 300,
          "creation_date": "11/18/2026"}, {"notam_id": "6/8739"}, {"notam_id": ""}]
    vus = set()
    out = ct.lignes(d, vus, "2026-11-19")
    assert len(out) == 1 and out[0]["notam"] == "6/8739" and len(out[0]["description"]) <= 300
    assert ct.lignes(d, vus, "2026-11-20") == []
    assert ct.lignes({"pas": "une liste"}, set(), "2026-11-19") == []
