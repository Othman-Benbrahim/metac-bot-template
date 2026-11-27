"""Brique scrutin restreinte (S2, S3), branchée le 2026-11-27."""
from datetime import date

import scrutin_regle as sr

PAGE = """{{Infobox election
| election_date = 15 December 2026
}}
{| class="wikitable"
! Pollster !! Fieldwork date !! Alice !! Bob !! Lead
|-
| P1 || 20 Nov 2026 || 48 || 40 || 8
|-
| P2 || 10 Nov 2026 || 50 || 38 || 12
|-
| P3 || 1 Nov 2026 || 47 || 41 || 6
|}
"""


def test_s1_exclu(monkeypatch):
    monkeypatch.setattr(sr, "_page", lambda e: ("x", PAGE))
    assert sr.estimer("Will Alice win the 2026 Brazilian presidential election?", date(2026, 11, 27)) is None


def test_un_tour(monkeypatch):
    monkeypatch.setattr(sr, "_page", lambda e: ("Opinion polling for the 2026 Testland general election", PAGE))
    e = sr.estimer("Will Alice win the 2026 Testland general election?", date(2026, 11, 27))
    assert e is not None and e["classe"] == "S2" and e["p_regle"] > 0.8 and e["jours_restants"] == 18


def test_sans_page(monkeypatch):
    monkeypatch.setattr(sr, "_page", lambda e: (None, ""))
    assert sr.estimer("Will Alice win the 2026 Testland general election?", date(2026, 11, 27)) is None
