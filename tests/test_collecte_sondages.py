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


def test_pages_refusees_run_44915155718():
    pc = cs.page_convient
    assert not pc("2026 United States Senate election in Michigan", "2026 Michigan Governor Democratic primary")
    assert not pc("2026 United States House of Representatives elections in Colorado", "2026 Colorado Governor Democratic primary")
    assert not pc("2026 United States House of Representatives elections in Colorado", "2026 Colombian Chamber of Representatives election")
    assert not pc("Opinion polling for the 2026 Portuguese presidential election", "2026 presidential election")
    assert not pc("Opinion polling for the next United Kingdom general election", "general election")
    assert not pc("1993 Russian legislative election", "next Russian parliamentary election", "2026-05-01")
    assert pc("Opinion polling for the 2026 Russian legislative election", "next Russian parliamentary election", "2026-05-01")
    assert not pc("2026 United States elections", "Russia Elections: United Russia Wins Every Region")
    assert cs.election("Will United Russia win the most seats in the next Russian parliamentary election?") == \
        "next Russian parliamentary election"


def test_sigles_initiales_sujets():
    assert cs.colonne("United Russia (ER)", ["UR", "CPRF", "LDPR", "NP"]) == "UR"
    assert cs.colonne("New People (NL)", ["UR", "CPRF", "LDPR", "NP"]) == "NP"
    assert cs.colonne("the Communist Party of the Russian Federation (KPRF)", ["UR", "CPRF", "LDPR"]) == "CPRF"
    assert cs.colonne("Flavio Bolsonaro", ["Lula PT", "F. Bolsonaro PL", "M. Bolsonaro PL"]) == "F. Bolsonaro PL"
    assert cs.colonne("Keiko Fujimori", ["Fujimori FP", "Sánchez JP"]) == "Fujimori FP"
    assert cs.sujet("Will any political party or coalition win a majority?") == ""
    assert cs.sujet("If Viktor Orbán leads a party, will it win?") == ""


HTML3 = """
<table><tr><th>Poll source</th><th>Date(s) administered</th><th>Marsha Blackburn</th><th>John Rose</th></tr>
<tr><td>A</td><td>Mar 1–3, 2026</td><td>50</td><td>20</td></tr><tr><td>B</td><td>Apr 1–3, 2026</td><td>52</td><td>18</td></tr></table>
<table><tr><th>Poll source</th><th>Date(s) administered</th><th>Marsha Blackburn (R)</th><th>Jerri Green (D)</th></tr>
<tr><td>C</td><td>Mar 5–7, 2026</td><td>55</td><td>35</td></tr><tr><td>C</td><td>Mar 9, 2026</td><td>54</td><td>36</td></tr></table>
<table><tr><th>Pollster</th><th>Polling period</th><th>Lula PT</th><th>F. Bolsonaro PL</th><th>Others</th></tr>
<tr><td>D</td><td>4 Mar</td><td>40</td><td>37</td><td>5</td></tr><tr><td>E</td><td>2 Mar</td><td>41</td><td>36</td><td>5</td></tr></table>"""


def test_un_seul_tableau_par_question():
    ls = cs.sondages(HTML3, 2026)
    assert {l["table"] for l in ls} == {0, 1, 2}           # « Polling period » est lu comme une date
    t, col = cs.choisir_table(ls, "2026-05-01", "Jerri Green", True)
    assert t is None and col is None                        # primaire démocrate : l'affiche générale ne compte pas
    t, col = cs.choisir_table(ls, "2026-05-01", "John Rose", True)
    assert col == "John Rose" and set(cs.moyennes(ls, "2026-05-01", t)) == {"Marsha Blackburn", "John Rose"}
    assert cs.choisir_table(ls, "2026-05-01", "Flavio Bolsonaro", False)[1] == "F. Bolsonaro PL"
