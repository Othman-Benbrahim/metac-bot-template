"""Brique football (collecte_football : lecture du wikitexte ; football_elo_regle : reconnaissance et simulation)."""
import json
from datetime import date

import collecte_football as cf
import football_elo_regle as fr

WIKI = """== League table ==
{{#invoke:Sports table|main|style=WDL
|source=[https://example.org Premier League]
|update=22 November 2026
|team1=ARS |team2=MCI |team3=LIV |team4=CHE |team5=AVL |team6=TOT |team7=NEW |team8=MUN |team9=BHA |team10=WHU
|team11=FUL |team12=BRE |team13=CRY |team14=EVE |team15=WOL |team16=BOU |team17=NFO |team18=LEE |team19=BUR |team20=SUN
|win_ARS=9 |draw_ARS=2 |loss_ARS=1 |gf_ARS=25 |ga_ARS=8 <!-- commentaire -->
|win_MCI=8 |draw_MCI=1 |loss_MCI=3
|name_ARS=[[Arsenal F.C.|Arsenal]]
|name_MCI=[[Manchester City F.C.|Manchester City]]
|adjust_points_EVE=-2
}}
== Results ==
{{#invoke:Sports results
|team1=ARS |team2=MCI
|match_ARS_MCI=[[2026–27 Arsenal F.C. season|2–1]]
|match_MCI_ARS=
}}
"""


def test_tableau():
    t = cf.lire_tableau(WIKI)
    assert t["mise_a_jour"] == "2026-11-22"
    assert t["equipes"]["ARS"]["points"] == 29 and t["equipes"]["ARS"]["nom"] == "Arsenal"
    assert t["equipes"]["EVE"]["points"] == -2 and len(t["equipes"]) == 20


def test_resultats():
    r = cf.lire_resultats(WIKI, {"ARS", "MCI"})
    assert r == {("ARS", "MCI"): (2, 1)}


def test_reconnaissance():
    assert fr.reconnaitre("Will Arsenal win the 2026–27 English Premier League?") == ("en.1", "Arsenal")
    assert fr.reconnaitre("Will Barcelona win La Liga 2026–27?") == ("es.1", "Barcelona")
    assert fr.reconnaitre("Will Arsenal finish top 4 in the 2026–27 Premier League?") is None
    assert fr.reconnaitre("Will Mumbai Indians win the 2026 Indian Premier League?") is None
    assert fr.reconnaitre("Will Arsenal win the Champions League?") is None


def test_simulation_leader_large():
    eq = {"A": {"points": 60, "elo": 1700}, "B": {"points": 40, "elo": 1700}, "C": {"points": 40, "elo": 1500}}
    rest = [["A", "B"], ["B", "C"], ["C", "A"]]
    p = fr.simuler(eq, rest, 60, 0.25)
    assert p["A"] == 1.0


def test_abstention_si_perime(tmp_path, monkeypatch):
    E = {"calcule_le": "2026-11-27", "saison": 2026, "ligues": {"en.1": {
        "titre": "2026–27 Premier League", "mise_a_jour": "2026-09-20", "complete": False, "H": 60, "p_nul": 0.25,
        "equipes": {"ARS": {"nom": "Arsenal", "points": 10, "elo": 1700}, "MCI": {"nom": "Manchester City", "points": 9, "elo": 1700}},
        "restants": [["ARS", "MCI"]], "controle": {"restants": 1, "attendu_total": 2, "matchs_classement": 1}}}}
    f = tmp_path / "etat.json"
    f.write_text(json.dumps(E), encoding="utf-8")
    monkeypatch.setattr(fr, "ETAT", f)
    fr._etat.cache_clear()
    assert fr.estimer("Will Arsenal win the 2026–27 Premier League?", date(2026, 11, 27)) is None   # classement de septembre
    E["ligues"]["en.1"]["mise_a_jour"] = "2026-11-25"
    f.write_text(json.dumps(E), encoding="utf-8")
    fr._etat.cache_clear()
    e = fr.estimer("Will Arsenal win the 2026–27 Premier League?", date(2026, 11, 27))
    assert e is not None and 0.01 <= e["p_regle"] <= 0.99
    fr._etat.cache_clear()
