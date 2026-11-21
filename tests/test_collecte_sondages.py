from datetime import date

import collecte_sondages as cs

HTML = """
<table class="wikitable"><tr><th rowspan="2">Polling firm</th><th rowspan="2">Fieldwork date</th>
<th colspan="3">Candidates</th></tr>
<tr><th>Keiko Fujimori</th><th>Rafael López Aliaga</th><th>Others</th></tr>
<tr><td>Ipsos</td><td>5–9 Mar 2026</td><td>12%</td><td>10%</td><td>40</td></tr>
<tr><td>Datum</td><td>Feb 20–25, 2026</td><td>11</td><td>12.5</td><td>41</td></tr>
<tr><td>IEP</td><td>28 Mar 2026</td><td>14</td><td>9</td><td>39</td></tr>
<tr><td colspan="2">Election result</td><td>17</td><td>11</td><td>30</td></tr>
</table>"""


def test_lecture_et_moyennes_sans_fuite():
    ls = cs.sondages(HTML, 2026)
    assert len(ls) == 3 and ls[0]["fin"] == date(2026, 3, 9) and ls[1]["fin"] == date(2026, 2, 25)
    m = cs.moyennes(ls, "2026-03-29")              # le sondage du 28 mars (après jeu − 3 jours) n'entre pas
    assert m["Keiko Fujimori"]["n"] == 2 and m["Keiko Fujimori"]["moyenne"] == 11.5
    assert "Others" not in m


def test_sujet_election_colonne():
    t = "Will Keiko Fujimori advance to the runoff in the 2026 Peruvian presidential election?"
    assert cs.sujet(t) == "Keiko Fujimori"
    assert cs.election(t) == "2026 Peruvian presidential election"
    assert cs.colonne("Keiko Fujimori", ["Keiko Fujimori", "Rafael López Aliaga"]) == "Keiko Fujimori"
    assert cs.colonne("United Russia (ER)", ["ER", "KPRF", "LDPR"]) == "ER"
    assert cs.colonne("López Aliaga", ["Keiko Fujimori", "Rafael López Aliaga"]) == "Rafael López Aliaga"


HTML2 = """
<table><tr><th rowspan="2">Polling firm</th><th rowspan="2">Fieldwork date</th><th>Fidesz</th><th>Tisza</th><th>Mi Hazánk</th><th rowspan="2">Lead</th></tr>
<tr><th></th><th></th><th></th></tr>
<tr><td>Medián</td><td>1–5 Mar 2026</td><td>40</td><td>45</td><td>7</td><td>5</td></tr>
<tr><td>21 Kutató</td><td>8–10 Mar 2026</td><td>39</td><td>47</td><td>6</td><td>8</td></tr></table>"""


def test_entetes_sur_plusieurs_lignes_et_page():
    m = cs.moyennes(cs.sondages(HTML2, 2026), "2026-03-20")
    assert set(m) == {"Fidesz", "Tisza", "Mi Hazánk"}
    assert cs.election("Will Renan Santos win the 2026 Brazilian presidential election?") == "2026 Brazilian presidential election"
    assert cs.election("Will Denis Sassou Nguesso win the 2026 Presidential election in the Republic of the Congo?").endswith("Republic of the Congo")
    assert cs.page_convient("Opinion polling for the 2026 Brazilian presidential election", "2026 Brazilian presidential election")
    assert not cs.page_convient("Nationwide opinion polling for the 2024 United States presidential election", "2026 Brazilian presidential election")
    assert not cs.page_convient("Statewide opinion polling for the 2028 Republican Party presidential primaries", "2026 Iowa Governor Republican primary")
    assert cs.page_convient("2026 Iowa gubernatorial election", "2026 Iowa Governor Republican primary")


def test_colonne_ambigue():
    noms = ["Lula PT", "Flávio Bolsonaro PL", "Michelle Bolsonaro PL"]
    assert cs.colonne("Flavio Bolsonaro", noms) == "Flávio Bolsonaro PL"
    assert cs.colonne("Bolsonaro", noms) is None
    assert cs.colonne("Keiko Fujimori", ["Fujimori", "López Aliaga"]) == "Fujimori"
