import collecte_tennis_wiki as tw

PAGE = """
==Finals==
{{4TeamBracket-Tennis5
| RD1=Semifinals
| RD1-seed1=1
| RD1-team1={{flagicon|ITA}} '''[[Jannik Sinner]]'''
| RD1-score1-1='''6''' | RD1-score1-2='''6'''
| RD1-team2={{flagicon|SRB}} [[Novak Djokovic]]
| RD1-score2-1=3 | RD1-score2-2=4
| RD1-team3={{flagicon|ESP}} '''[[Carlos Alcaraz]]'''
| RD1-team4={{flagicon|GER}} [[Alexander Zverev]]
| RD2-team1={{flagicon|ITA}} [[Jannik Sinner]]
| RD2-team2={{flagicon|ESP}} '''[[Carlos Alcaraz]]'''
}}
==Section 1==
{{16TeamBracket-Compact-Tennis5
| RD1-team01={{flagicon|ITA}} '''[[Jannik Sinner|J Sinner]]'''
| RD1-team02={{flagicon|USA}} [[John Doe (tennis)|J Doe]]
| RD1-team03=Bye
| RD1-team04={{flagicon|FRA}} [[A Player]]
}}
"""


def test_lecture_des_tableaux():
    M = tw.matchs(PAGE)
    paires = {(g, p) for _, g, p, _ in M}
    assert ("Jannik Sinner", "Novak Djokovic") in paires
    assert ("Carlos Alcaraz", "Alexander Zverev") in paires
    assert ("Carlos Alcaraz", "Jannik Sinner") in paires
    assert ("Jannik Sinner", "John Doe") in paires
    assert all("Bye" not in g + p for _, g, p, _ in M)
    finale = [o for o, g, p, _ in M if (g, p) == ("Carlos Alcaraz", "Jannik Sinner")][0]
    premier_tour = [o for o, g, p, _ in M if p == "John Doe"][0]
    assert finale > premier_tour
