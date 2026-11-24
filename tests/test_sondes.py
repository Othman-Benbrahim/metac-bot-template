import json
import math

import sondes as so


def test_appliquer_borne_et_ignore_les_sondes_inactives():
    E = {"sondes": {"relations": {"actif": True, "k": 3.0, "plafond": 0.05},
                    "ponts": {"actif": False, "k": 3.0, "plafond": 0.05},
                    "phase": {"actif": True, "k": 0.0, "plafond": 0.05}}}
    lec = {"relations": {"d": 3.0, "sens": 1}, "ponts": {"d": 3.0, "sens": 1}, "phase": {"d": 1.0, "sens": 1}}
    r = so.appliquer(0.30, lec, E)
    assert set(r["parts"]) == {"relations"}
    assert abs(r["p"] - 0.35) < 1e-9


def test_e_valeurs(tmp_path, monkeypatch):
    import sondes_etat as se
    (tmp_path / "issues.jsonl").write_text(json.dumps({"question_id": "1", "issue": 1}) + "\n", encoding="utf-8")
    (tmp_path / "journal-sondes.jsonl").write_text(json.dumps(
        {"question_id": "1", "p_base": 0.5, "sondes": {"relations": {"p_sonde": 0.55}}}) + "\n", encoding="utf-8")
    monkeypatch.setattr(se, "REG", tmp_path)
    ev = se.e_valeurs()
    assert abs(ev["relations"]["log_e"] - math.log(0.55 / 0.5)) < 1e-9 and ev["relations"]["resolues"] == 1


def test_objet_meteo_demande_le_phenomene():
    import ecosysteme_objet as eo
    assert not eo.porte_sur("meteo:teheran", "Will the Iranian regime fall by March 31?")
    assert eo.porte_sur("meteo:delhi", "Will Delhi record a temperature above 47C in May?")
