"""2026-11-25 : liste publique des élections à venir (IFES ElectionGuide)."""
import collecte_elections_ifes as ce

PAGE = """<table><tr><th></th></tr><tr><td>x</td></tr></table>
<table><tr><th></th><th>Country</th><th>Election for</th><th>Start Date</th><th>End Date</th><th>Status</th><th>Is Snap?</th><th>Last Held*</th><th>Last Registered</th></tr>
<tr><td><img></td><td><a href="/countries/id/200/">Spain</a></td><td><a href="/elections/id/5256/?x">Spanish Congress of Deputies</a></td>
<td>2026-11-29 (d)</td><td>2026-11-29 (d)</td><td>Confirmed</td><td>Yes</td><td>2023-07-23</td><td>37,466,432</td></tr>
<tr><td></td><td>France</td><td><a href="/elections/id/5250/">French Presidency</a></td><td>Apr 18 2027 (t)</td><td>2027-04-18 (t)</td><td>Date not confirmed</td><td>No</td><td></td><td></td></tr></table>"""


def test_analyser():
    L = ce.analyser(PAGE)
    assert [(x["id"], x["pays"], x["debut"], x["debut_precision"], x["anticipe"]) for x in L] == [
        ("5256", "Spain", "2026-11-29", "d", "Yes"), ("5250", "France", "2027-04-18", "t", "No")]
    assert L[1]["statut"] == "Date not confirmed" and L[0]["inscrits"] == "37,466,432"
