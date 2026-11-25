"""2026-11-25 : tracker des procès de Just Security (collecte_justsecurity.py)."""
import collecte_justsecurity as js

ENTETE = "".join(f"<th>{x}</th>" for x in js.ATTENDU + ["Case Summary", "Case Updates"])
LIGNE = ('<tr><td><a href="https://www.courtlistener.com/docket/1/x/">Perkins Coie LLP v. U.S. Department of Justice '
         '(D.D.C.) 1:25-cv-00716</a></td><td>Complaint</td><td>2025-03-11</td><td>Plaintiff-side State Amicus</td>'
         '<td>Government Action Blocked; Appeal Pending</td><td>Civil Liberties and Rights</td><td>EO 14230</td>'
         '<td>2026-04-03</td><td>Résumé long</td><td>Historique</td></tr>')
PAGE = f'<table id="tablepress-42" class="tablepress"><tr>{ENTETE}</tr>{LIGNE}</table>'


def test_analyser():
    (l,) = js.analyser(PAGE)
    assert l["affaire"] == "Perkins Coie LLP v. U.S. Department of Justice" and l["tribunal"] == "D.D.C."
    assert l["dossier"] == "1:25-cv-00716" and l["courtlistener"].startswith("https://www.courtlistener.com/")
    assert l["depot"] == "2025-03-11" and l["maj"] == "2026-04-03"
    assert (l["famille"], l["appel"]) == ("bloque", 1)
    assert "Résumé" not in str(l)


def test_familles_du_glossaire():
    f = js.famille
    assert f("Decision Pending") == ("attente", 0)
    assert f("Government Action Temporarily Blocked") == ("bloque_temp", 0)
    assert f("Government Action Temporarily Blocked; Appellate Court Affirmed Block") == ("bloque_temp", 1)
    assert f("Temporary Block of Government Action Denied; Appeal Pending") == ("refuse_temp", 1)
    assert f("Block of Government Action Denied") == ("refuse", 0)
    assert f("Government Action Unblocked by Appellate Court") == ("debloque_appel", 1)
    assert f("Government Action Temporarily Unblocked by Appellate Court") == ("debloque_appel", 1)
    assert f("Case Closed in Favor of Plaintiff(s)") == ("clos_plaignant", 0)
    assert f("Case Closed/Dismissed in Favor of Government") == ("clos_gouvernement", 0)
    assert f("Government Action Blocked in Part; Block Denied in Part; Appeal Pending") == ("partiel", 1)
    assert f("Case Closed; Split Outcome") == ("partiel", 0)
    assert f("Case Closed") == ("clos", 0)


def test_colonnes_changees():
    import pytest
    with pytest.raises(ValueError):
        js.analyser('<table id="tablepress-42"><tr><th>Autre</th></tr></table>')
