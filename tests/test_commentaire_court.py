"""Commentaire court sur Metaculus (décision de l'auteur, 2026-11-24, 23 h 41)."""
from alphabet_bot import COMMENTAIRE_MAX, commentaire_court


def test_court_et_structure_du_gabarit():
    r = ("Situational-alphabet bot. Posted arm: M.\nStarting point: 0.11.\n\n" + "- card: blah " * 800 +
         "\n\nCentral-bank inertia rule (coded): 12.0%. This coded rule is the measure (base, not blended)."
         "\n\nInformed judge (bounded): departure for motive « critere_resolution », capped at 10%: 12.0% -> 20.0%.")
    c = commentaire_court("Will the Fed cut?", 0.2, r)
    assert c.startswith("# SUMMARY") and "# RESEARCH" in c and "## R1:" in c
    corps = c.split("## R1: Forecaster 1 Reasoning\n")[1]
    assert len(corps) <= COMMENTAIRE_MAX + 1
    assert "Central-bank inertia rule" in corps and "Informed judge" in corps and "blah" not in corps


def test_sans_regle_debut_tronque():
    c = commentaire_court("Q", 0.3, "x " * 3000)
    assert len(c.split("## R1: Forecaster 1 Reasoning\n")[1]) <= COMMENTAIRE_MAX + 1
