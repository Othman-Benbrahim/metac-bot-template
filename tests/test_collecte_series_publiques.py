"""0.10.358 : lecteurs des séries publiques, escales PortWatch, liste Wikipédia des récits de complot."""
import io
import zipfile
from pathlib import Path

import adaptateurs as ad
import collecte_ouvertes as co
import collecte_portwatch as cp
import collecte_series_publiques as sp


def test_nsidc():
    t = (" Year, Month, Day,     Extent,    Missing, Source Data\n YYYY,    MM,  DD, 10^6 sq km, 10^6 sq km, Source\n"
         " 2026,    11,  17,     9.123,      0.000, ['x']\n 2026,    11,  18,     -9999,      0.000, ['x']\n")
    assert sp.lire_nsidc(t) == [("2026-11-17", 9.123)]


def test_gfz():
    l = "2026 11 17 34289 34289.5 2617 15 " + " ".join(["1.333"] * 8) + " " + " ".join(["5"] * 8) + " 12 87 130.2 128.1 1\n"
    manq = "2026 11 18 34290 34290.5 2617 16 " + " ".join(["-1"] * 8) + " " + " ".join(["-1"] * 8) + " -1 -1 -1.0 -1.0 0\n"
    g = sp.lire_gfz("# en-tête\n" + l + manq)
    assert g == {"geomag_ap": [("2026-11-17", 12.0)], "taches_solaires": [("2026-11-17", 87.0)], "flux_f107": [("2026-11-17", 130.2)]}


def test_cpc():
    t = ("                Nino1+2      Nino3        Nino34        Nino4\n Week          SST SSTA     SST SSTA     SST SSTA     SST SSTA\n"
         " 05NOV2025     20.6-0.4     24.9-0.6     26.1-0.6     28.5 0.1\n 12NOV2025     20.9-0.3     25.0-0.5     26.3-0.4     28.6 0.2\n")
    assert sp.lire_cpc(t) == [("2025-11-05", -0.6), ("2025-11-12", -0.4)]


def test_kaub_usgs():
    k = [{"timestamp": "2026-11-18T00:00:00+01:00", "value": 120}, {"timestamp": "2026-11-18T00:15:00+01:00", "value": 122},
         {"timestamp": "2026-11-19T00:00:00+01:00", "value": 118}]
    assert sp.lire_kaub(k) == [("2026-11-18", 121.0), ("2026-11-19", 118.0)]
    anc = {"value": {"timeSeries": [{"values": [{"value": [{"value": "100000", "dateTime": "2026-11-17T00:00:00.000"},
                                                            {"value": "-999999", "dateTime": "2026-11-18T00:00:00.000"}]}]}]}}
    assert sp.lire_usgs_ancien(anc) == [("2026-11-17", 2831.7)]
    nouv = {"features": [{"properties": {"time": "2026-11-17", "value": "100000"}}]}
    assert sp.lire_usgs_nouveau(nouv) == [("2026-11-17", 2831.7)]


def test_usdm_json_et_csv():
    j = '[{"MapDate":"20261111","None":"60.1","D0":"39.9","D1":"25.0","D2":"12.5","D3":"4.0","D4":"0.5"}]'
    assert sp.lire_usdm(j) == [("2026-11-11", 12.5)]
    c = "MapDate,None,D0,D1,D2,D3,D4\n2026-11-04T00:00:00,60,40,25,11.0,4,0.5\n"
    assert sp.lire_usdm(c) == [("2026-11-04", 11.0)]


def test_psd():
    lignes = ["Commodity_Code,Commodity_Description,Country_Code,Country_Name,Market_Year,Calendar_Year,Month,"
              "Attribute_ID,Attribute_Description,Unit_ID,Unit_Description,Value"]
    for pays, v in (("France", 30000), ("India", 110000)):
        lignes.append(f"0410000,Wheat,XX,{pays},2026,2026,11,176,Ending Stocks,8,(1000 MT),{v}")
        lignes.append(f"0410000,Wheat,XX,{pays},2025,2026,11,176,Ending Stocks,8,(1000 MT),1")
    lignes.append("0410000,Wheat,WD,World,2026,2026,11,176,Ending Stocks,8,(1000 MT),999999")
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w") as z:
        z.writestr("psd_grains_pulses.csv", "\n".join(lignes))
    assert sp.lire_psd(b.getvalue()) == {"psd_ble_stocks": 140.0}


def test_arxiv_et_adaptateurs(tmp_path: Path):
    assert sp.total_arxiv('<feed><opensearch:totalResults xmlns:opensearch="x">412</opensearch:totalResults></feed>') == 412
    assert sp.total_arxiv("<feed/>") is None
    (tmp_path / "series-publiques.csv").write_text("serie,jour,valeur\nnino34_anomalie,2025-11-12,-0.4\n", encoding="utf-8")
    (tmp_path / "portwatch-ports.csv").write_text("port,jour,escales,petroliers,porte_conteneurs\nrotterdam,2026-11-01,80,20,30\n",
                                                  encoding="utf-8")
    assert ad.lire("pub:nino34_anomalie", tmp_path) == [("2025-11-12", -0.4)]
    assert ad.lire("port:rotterdam:petroliers", tmp_path) == [("2026-11-01", 20.0)]


def test_escales_et_listes():
    assert cp.escales({"portcalls": 5, "portcalls_tanker": 2, "portcalls_container": None}) == [5, 2, 0]
    assert cp.escales({"n_total": 7}) == [7, 0, 0] and cp.escales({}) is None
    assert set(co.LISTES) == {"attention_crise", "attention_complot"} and len(co.ARTICLES_COMPLOT) == 10


def test_gestes_compte_sans_note(tmp_path: Path):
    import json
    (tmp_path / "gdelt-dyades.json").write_text(json.dumps({"sens": {"RUS>UKR": {
        "2026-11-09": {"n": 40, "somme_g": -120.0, "coop_verbale": 5, "coop_materielle": 1, "conflit_verbal": 10, "conflit_materiel": 24}}}}),
        encoding="utf-8")
    assert ad.lire("gestes:RUS:UKR", tmp_path) == [("2026-11-09", 40.0)]
    assert ad.lire("gestes:RUS:UKR:conflit_materiel", tmp_path) == [("2026-11-09", 24.0)]


def test_toute_trace_branchee_a_une_nature():
    """Garde-fou (2026-11-19) : aucune série n'entre dans une fiche sans dire ce qu'elle compte (nature connue)."""
    import classer_series as cs
    import ecosystemes as ec
    mauvaises = [t["adaptateur"] for f in ec.charger(ec.DOSSIER).values() for c in f.get("compartiments", [])
                 for t in c.get("traces") or [] if isinstance(t, dict) and t.get("adaptateur")
                 and cs.nature(t["adaptateur"])[0] in ("non classé", "écarté")]
    assert not mauvaises, mauvaises
