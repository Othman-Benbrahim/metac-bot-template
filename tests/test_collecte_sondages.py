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


HTML4 = """
<table><tr><th>Pollster</th><th>Polling period</th><th>Lula PT</th><th>F. Bolsonaro PL</th><th>Caiado PSD</th><th>Zema Novo</th><th>Blank Null Undec.</th></tr>
<tr><td>A</td><td>4 Mar</td><td>45</td><td>40</td><td></td><td></td><td>15</td></tr>
<tr><td>A</td><td>4 Mar</td><td>46</td><td></td><td>38</td><td></td><td>16</td></tr>
<tr><td>A</td><td>4 Mar</td><td>47</td><td></td><td></td><td>37</td><td>16</td></tr></table>"""


def test_duels_et_mots_uniques_run_44916010855():
    assert cs.sondages(HTML4, 2026) == []                  # matrice de duels : écartée
    assert cs.colonne("Luiz Inácio Lula da Silva", ["Lula PT", "F. Bolsonaro PL"]) == "Lula PT"
    assert not cs.page_convient("2026 Texas Attorney General election", "2026 Texas Republican Primary")
    assert not cs.page_convient("Opinion polling for the 2030 Hungarian parliamentary election", "next Hungarian parliamentary election", "2026-02-01")


def test_fraicheur_run_44916476984():
    ls = cs.sondages(HTML3, 2026)                          # sondages de mars et avril 2026
    assert cs.choisir_table(ls, "2026-12-01", "John Rose", True) == (None, None)   # plus de 90 jours : refus
    assert cs.moyennes(ls, "2026-12-01") == {}


BASE_DAWUM = {"Parliaments": {"15": {"Shortcut": "Sachsen-Anhalt", "Name": "Sachsen-Anhalt"}, "0": {"Shortcut": "Bundestag", "Name": "Bundestag"}},
              "Parties": {"1": {"Shortcut": "CDU"}, "7": {"Shortcut": "AfD"}, "5": {"Shortcut": "Linke"}, "0": {"Shortcut": "Sonstige"}},
              "Surveys": {"a": {"Date": "2026-06-10", "Survey_Period": {"Date_Start": "2026-06-01", "Date_End": "2026-06-08"},
                                "Parliament_ID": "15", "Results": {"1": 27, "7": 39, "5": 11, "0": 5}},
                          "b": {"Date": "2026-06-12", "Survey_Period": {"Date_Start": "2026-06-02", "Date_End": "2026-06-09"},
                                "Parliament_ID": "0", "Results": {"1": 30, "7": 25}}}}


def test_dawum():
    el = cs.election("Will The Left win the third most seats in the 2026 Sachsen-Anhalt parliamentary elections?")
    assert cs.parlement_dawum(el) == "Sachsen-Anhalt"
    ls = cs.lignes_dawum(BASE_DAWUM, "Sachsen-Anhalt")
    assert len(ls) == 1 and ls[0]["fin"] == date(2026, 6, 8) and set(ls[0]["valeurs"]) == {"CDU", "AfD", "Linke"}
    assert cs.choisir_table(ls, "2026-07-19", cs.sujet_parti("The Left"), False) == (0, "Linke")


def test_secours_run_44917505006():
    t = "Will Luiz Inácio Lula da Silva qualify for Brazil's presidential runoff?"
    assert cs.election(t) == t
    assert cs.election_de_secours(t, "2026-08-16") == "2026 Brazilian presidential election"
    assert cs.page_convient("Opinion polling for the 2026 Senedd election", "2026 Welsh election")


HTML5 = """
<table><tr><th>Pollster</th><th>Fieldwork date</th><th>Fidesz</th><th>Tisza</th><th>Lead</th></tr>
<tr><td>A</td><td>1 Mar 2026</td><td>40</td><td>45</td><td>5</td></tr>
<tr><td>B</td><td>3 Mar 2026</td><td>39</td><td>47</td><td>8</td></tr>
<tr><td>C</td><td>5 Mar 2026</td><td>41</td><td>46</td><td>+5</td></tr></table>
<table><tr><th>Pollster</th><th>Fieldwork date</th><th>Fidesz</th><th>Tisza</th><th>Lead</th></tr>
<tr><td>A</td><td>1 Mar 2026</td><td>40</td><td>45</td><td>12</td></tr>
<tr><td>B</td><td>3 Mar 2026</td><td>39</td><td>47</td><td>2</td></tr>
<tr><td>C</td><td>5 Mar 2026</td><td>41</td><td>46</td><td>9</td></tr></table>"""


def test_relecture_par_la_colonne_lead():
    ls = cs.sondages(HTML5, 2026)
    assert [l["verif"] for l in ls if l["table"] == 0] == [True, True, True]
    assert cs.accord_lead([l for l in ls if l["table"] == 1]) == (3, 0.0)
    assert cs.choisir_table(ls, "2026-03-20", "Tisza", False)[0] == 0   # le tableau mal lu est refusé


def test_parti_jamais_lu_dans_la_colonne_de_son_chef():
    noms = ["Nooshi Dadgostar (V)", "Magdalena Andersson (S)", "Ulf Kristersson (M)"]
    assert cs.colonne("Swedish Social Democratic Party (S)", noms) is None
    assert cs.colonne("Swedish Social Democratic Party (S)", ["V", "S", "MP", "SD"]) == "S"
    assert cs.colonne("United Russia (ER)", ["UR", "CPRF", "LDPR"]) == "UR"
    assert cs.colonne("Apvienotais Saraksts (AS)", ["JV", "ZZS", "AS"]) == "AS"


def test_dates_et_verdicts_multilingues():
    assert cs.fin_terrain("1–5 de marzo de 2026", 2026) == date(2026, 3, 5)
    assert cs.fin_terrain("12.04.2026", 2026) == date(2026, 4, 12)
    assert cs.fin_terrain("2026.03.09.", 2026) == date(2026, 3, 9)
    assert cs.fin_terrain("5–9 marta 2026", 2026) == date(2026, 3, 9)          # « марта » translittéré
    assert cs.fin_terrain("3 iiunia 2026", 2026) == date(2026, 6, 3)
    assert cs.fin_terrain("20 maj 2026", 2026) == date(2026, 5, 20)
    assert cs.langue_locale("2026 Brazilian presidential election") == "pt"
    assert cs.langue_locale("2026 Texas Republican primary") is None
    ok = {"source": "wikipedia", "relecture_lead": {"lignes_verifiees": 5, "accord": 1.0}}
    assert cs.verdict(ok) == "confirme_lead"
    assert cs.verdict({**ok, "seconde_source": {"ecart_points": 4.5}}) == "desaccord"
    assert cs.verdict({"source": "wikipedia", "seconde_source": {"ecart_points": -1.0}}) == "confirme_second_source"
    assert cs.verdict({"source": "wikipedia"}) == "non_verifie"
    assert cs.verdict({"source": "dawum"}) == "confirme_structure"


HTML6 = """
<table><tr><th>Instituto</th><th>Data</th><th>Lula PT</th><th>Flávio PL</th><th>Caiado PSD</th><th>Zema NOVO</th></tr>
<tr><td>A</td><td>10.08.2026</td><td>40</td><td>35</td><td>5</td><td>3</td></tr>
<tr><td>B</td><td>12.08.2026</td><td>41</td><td>34</td><td>5</td><td>4</td></tr></table>
<table><tr><th>Instituto</th><th>Data</th><th>Lula PT</th><th>Caiado PSD</th></tr>
<tr><td>A</td><td>11.08.2026</td><td>46</td><td>39</td></tr>
<tr><td>B</td><td>13.08.2026</td><td>45</td><td>40</td></tr></table>"""


def test_premier_tour_contre_duel_run_44925812553():
    ls = cs.sondages(HTML6, 2026)
    t, col = cs.choisir_table(ls, "2026-08-20", "Ronaldo Caiado", False)
    assert col == "Caiado PSD" and cs.moyennes(ls, "2026-08-20", t)[col]["moyenne"] == 5   # 1er tour, pas le duel
    t, col = cs.choisir_table(ls, "2026-08-20", "Ronaldo Caiado", False, second_tour=True)
    assert cs.moyennes(ls, "2026-08-20", t)[col]["moyenne"] == 39.5


WIKITEXTE = """
{| class="wikitable sortable"
|-
! rowspan=2 | Poll source
! rowspan=2 | Date(s)<br />administered
! colspan=3 | Candidates
|-
! [[Andy Biggs]]
! Karrin Taylor<br />Robson
! Other
|-
| [[Emerson College|Emerson]]<ref>{{cite web|url=x}}</ref>
| {{dts|2026|05|10}}
| {{Party shading/Republican}} | '''45%'''
| 22%
| 8%
|-
| Noble Predictive || May 1–3, 2026 || 43% || 24% || 9%
|}"""

HTML_EQ = """<table><tr><th rowspan="2">Poll source</th><th rowspan="2">Date(s) administered</th><th colspan="3">Candidates</th></tr>
<tr><th>Andy Biggs</th><th>Karrin Taylor Robson</th><th>Other</th></tr>
<tr><td>Emerson</td><td>May 10, 2026</td><td>45%</td><td>22%</td><td>8%</td></tr>
<tr><td>Noble Predictive</td><td>May 1–3, 2026</td><td>43%</td><td>24%</td><td>9%</td></tr></table>"""


def test_seconde_lecture_wikitexte():
    lw = cs.sondages_grilles(cs.grilles_wikitexte(WIKITEXTE), 2026)
    lh = cs.sondages(HTML_EQ, 2026)
    assert len(lw) == 2 and lw[0]["fin"] == date(2026, 5, 10) and lw[0]["valeurs"]["Andy Biggs"] == 45
    jeu = "2026-06-01"
    tw, cw = cs.choisir_table(lw, jeu, "Andy Biggs", True)
    th, ch = cs.choisir_table(lh, jeu, "Andy Biggs", True)
    assert cs.moyennes(lw, jeu, tw)[cw]["moyenne"] == cs.moyennes(lh, jeu, th)[ch]["moyenne"] == 44
    assert cs.verdict({"source": "wikipedia", "relecture_wikitexte": {"ecart_points": 0.0}}) == "confirme_wikitexte"
    assert cs.verdict({"source": "wikipedia", "relecture_wikitexte": {"ecart_points": 3.0},
                       "relecture_lead": {"lignes_verifiees": 5, "accord": 1.0}}) == "desaccord_lecture"


def test_meme_nom_autre_personne():
    noms = ["Lula PT", "F. Bolsonaro PL", "Caiado PSD"]
    assert cs.colonne("Michelle Bolsonaro", noms) is None
    assert cs.colonne("Flavio Bolsonaro", noms) == "F. Bolsonaro PL"
    assert cs.colonne("Luiz Inácio Lula da Silva", noms) == "Lula PT"
    assert cs.colonne("Ronaldo Caiado", noms) == "Caiado PSD"


def test_parti_entre_parentheses_pas_de_repli_sur_la_personne():
    assert cs.colonne("Orban (Fidesz)", ["Orbán", "Magyar"]) is None
    assert cs.colonne("Orban (Fidesz)", ["Fidesz–KDNP", "Tisza"]) == "Fidesz–KDNP"
    assert cs.colonne("United Russia (ER)", ["United Russia", "CPRF"]) == "United Russia"
