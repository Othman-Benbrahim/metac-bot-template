import contradicteur_brique as cb
import dossier_interne as di

T = "Will Donald Trump and Vladimir Putin meet in person or talk on the phone before January 1, 2027?"


def test_hors_domaine_citation_verifiee():
    r = cb.analyser('{"verdict": "hors_domaine", "citation": "or talk on the phone"}', T)
    assert r["verdict"] == "hors_domaine"
    r = cb.analyser('{"verdict": "hors_domaine", "citation": "video call"}', T)
    assert r["verdict"] == "rejete"


def test_terrain_exige_des_sources():
    assert cb.analyser('{"verdict": "contre_terrain", "sources": []}', T)["verdict"] == "rejete"
    assert cb.analyser("pas de json", T)["verdict"] == "illisible"


def test_chaque_brique_a_un_domaine():
    import inspect
    src = inspect.getsource(di._briques)
    import re
    fams = re.findall(r'\("([a-z_]+)", "', src)
    assert fams and all(f in di.DOMAINES for f in fams)
