"""0.10.376 : mesure de l'erreur des sondages infranationale (hors réseau)."""
import erreur_regionale as er

TEXTE = """{{Infobox election
| election_name = 2022 Bahia gubernatorial election
| election_date = 2 October 2022
| candidate1 = [[Jerônimo Rodrigues]]
| party1 = [[Workers' Party (Brazil)|PT]]
| 1blank = First round
| 1data1 = 4,019,830 (49.45%)
| candidate2 = [[ACM Neto]]
| 1data2 = 3,316,535 (40.80%)
}}
"""


def test_encadre_deux_tours():
    enc = er.encadre(TEXTE)
    assert enc["candidate1"] == "Jerônimo Rodrigues" and enc["election_date"] == "2 October 2022"
    assert er.resultats(enc) == [("Jerônimo Rodrigues", 49.45), ("ACM Neto", 40.8)]


def test_encadre_pourcentages():
    enc = er.encadre("{{Infobox election\n| party1 = SPD\n| percentage1 = 35.7%\n| party2 = CDU\n| percentage2 = 27.7\n}}")
    assert er.resultats(enc) == [("SPD", 35.7), ("CDU", 27.7)]


def test_titres():
    t = er.titres()
    assert ("2022 Bahia gubernatorial election", "bresil_etats") in t and len(t) > 500


def test_tours():
    enc = er.encadre(TEXTE.replace("}}", "| 2blank = Second round\n| 2data1 = 52.8%\n| 2data2 = 47.2%\n}}"))
    assert er.tours(enc) == ("1", "1")


def test_en_tete_fusionnee_et_sigles():
    import banc_scrutin as bs
    t = '{| class="wikitable"\n! rowspan="2" |Date\n! rowspan="2" |Institute\n! colspan="2" |Candidate\n! rowspan="2" |Blank\n|-\n!Jerônimo\n!ACM Neto\n|-\n|28 Sep 2022\n|Ipec\n|38%\n|43%\n|14%\n|}'
    assert bs.tableaux(t, 2022)[0]["colonnes"] == ["Date", "Institute", "Jerônimo", "ACM Neto", "Blank"]
    assert bs._date("2022-13-01", 2022) is None
    assert er.sigle("Christian Democratic Union (Germany)") == "CDU" and er.sigle("Coalition Avenir Québec") == "CAQ"
