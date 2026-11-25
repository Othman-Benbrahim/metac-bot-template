"""2026-11-25 : liste publique des élections à venir (IFES ElectionGuide) ; forme copiée de la vraie page."""
import collecte_elections_ifes as ce

PAGE = """<table><tr><td>carte mobile</td></tr></table>
<table class="table table-hover" id="electionsTable"><thead><tr><th></th><th>Country</th><th>Election for</th>
<th>Start Date</th><th>End Date</th><th>Status</th><th>Is Snap?</th><!--<th>Last Held*</th><th>Last Registered</th>--></tr></thead><tbody>
<tr><td><img src="x.gif"></td><td><a href="/countries/id/200/">Spain</a></td><td><a href="/elections/id/5256/?'report_type=upcoming">Spanish Congress of Deputies</a>
<!-- commentaire --><td> 2026-11-29 <small>(d)</small></td><td> 2026-11-29 <small>(d)</small></td><td>Confirmed</td><td>Yes</td></tr>
<tr><td><img></td><td>France</td><td><a href="/elections/id/5250/">French Presidency</a><td>2027-04-18 <small>(t)</small></td>
<td>2027-04-18 <small>(t)</small></td><td>Date not confirmed</td><td>No</td></tr></tbody></table>"""


def test_analyser():
    L = ce.analyser(PAGE)
    assert [(x["id"], x["pays"], x["scrutin"], x["debut"], x["debut_precision"], x["anticipe"]) for x in L] == [
        ("5256", "Spain", "Spanish Congress of Deputies", "2026-11-29", "d", "Yes"),
        ("5250", "France", "French Presidency", "2027-04-18", "t", "No")]
    assert L[1]["statut"] == "Date not confirmed"
