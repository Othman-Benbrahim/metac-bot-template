"""0.10.334 : collecte météo par GHCN-Daily (stations au sol NOAA)."""
import collecte_meteo as cm

STATIONS = ("IN022021900  28.5830   77.2000  216.0    NEW DELHI/SAFDARJUNG\n"
            "IN000000001  29.9000   78.0000  300.0    TROP LOIN POUR DELHI\n"
            "USW00012960  29.9800  -95.3600   29.0 TX HOUSTON INTERCONTINENTAL\n")
INVENTAIRE = ("IN022021900  28.5830   77.2000 TMAX 1931 2026\nIN022021900  28.5830   77.2000 TMIN 1931 2026\n"
              "IN000000001  29.9000   78.0000 TAVG 1990 2010\nUSW00012960  29.9800  -95.3600 TAVG 1969 2026\n")


def test_stations_et_choix():
    st = cm.lire_stations(STATIONS)
    assert st["IN022021900"][:2] == (28.583, 77.2) and "SAFDARJUNG" in st["IN022021900"][2]
    v = cm.lire_inventaire(INVENTAIRE, 2026)
    assert v == {"IN022021900", "USW00012960"}                         # la station arrêtée en 2010 est écartée
    assert cm.choisir(st, v, 28.61, 77.21)[0] == "IN022021900"
    assert cm.choisir(st, v, 0.0, 0.0) is None                          # rien à moins de RAYON_KM


def test_lire_station():
    t = ("IN022021900,20160101,TMAX,250,,,S,\nIN022021900,20160101,TMIN,90,,,S,\n"
         "IN022021900,20160102,TAVG,171,,,S,\nIN022021900,20160103,TMAX,300,,X,S,\nIN022021900,20160103,TMIN,100,,,S,\n"
         "IN022021900,20151231,TAVG,100,,,S,\n")
    assert cm.lire_station(t, "2016-01-01") == [("2016-01-01", 17.0), ("2016-01-02", 17.1)]


def test_distance():
    assert abs(cm.distance_km((48.8566, 2.3522), (51.5074, -0.1278)) - 344) < 5   # Paris-Londres


def test_rayon_elargi():
    st = cm.lire_stations("IR000407540  35.6830   51.3170 1191.0    TEHRAN-MEHRABAD\n")
    v = {"IR000407540"}
    assert cm.candidates(st, v, 27.18, 56.27) == []                       # Bandar Abbas : Téhéran est à ~ 950 km
    assert cm.candidates(st, v, 33.9, 51.4)[0][0] == "IR000407540"        # ~ 200 km : admis au rayon élargi


def test_pays_admis():
    st = cm.lire_stations("TX000038750  37.4670   53.9670  -22.0    ESENGYLY\nMUM00041242  25.6000   56.2700    5.0    DIBA\n")
    v = set(st)
    assert cm.candidates(st, v, 35.69, 51.39, cm.PAYS["teheran"]) == []          # pas de témoin turkmène pour Téhéran
    assert cm.candidates(st, v, 27.18, 56.27, cm.PAYS["bandar_abbas"])[0][0] == "MUM00041242"
