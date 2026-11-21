import io
import zipfile

import collecte_agro as ca

CSV_T = "valid_time,latitude,longitude,t2m\n2026-07-01 00:00:00,42,-93.6,290.15\n2026-07-01 15:00:00,42,-93.6,306.15\n2026-07-02 00:00:00,42,-93.6,291.15\n"
CSV_S = "valid_time,latitude,longitude,swvl1,tp\n2026-07-01 00:00:00,42,-93.6,0.30,0.0\n2026-07-01 12:00:00,42,-93.6,0.20,0.004\n2026-07-02 00:00:00,42,-93.6,0.25,0.006\n"


def test_lecture_cds_et_journalier():
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w") as z:
        z.writestr("t2m.csv", CSV_T)
        z.writestr("autres.csv", CSV_S)
    lignes = ca.lire_sortie_cds(b.getvalue())
    assert len(lignes) == 3 and lignes[1]["t2m"] == 306.15
    j = ca.journalier(lignes)
    assert j["2026-07-01"]["tmax"] == 33.0
    assert j["2026-07-01"]["sol_0_7"] == 0.25
    assert j["2026-07-01"]["pluie_mm"] == 6.0          # cumul de 24 h lu à 0 h du lendemain


def test_usdm():
    js = [{"MapDate": "20260715", "StateAbbreviation": "CA", "None": 10.5, "D0": 89.5, "D1": 60.0, "D2": 30.0,
           "D3": 5.0, "D4": 0.0}]
    assert ca.lire_usdm(js, "CA") == [["CA", "2026-07-15", 10.5, 89.5, 60.0, 30.0, 5.0, 0.0]]
