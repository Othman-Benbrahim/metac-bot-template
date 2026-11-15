"""0.10.111 : les tests du pipeline écrits avant la règle AB (½A + ½B en strates 7 et 13) vérifient les bras B et C ;
la règle AB est coupée par défaut dans les tests et rallumée par ceux qui la vérifient (fixture `poster_ab`)."""
import pytest


@pytest.fixture(autouse=True)
def _sans_ab(monkeypatch):
    import alphabet_pipeline as ap
    monkeypatch.setattr(ap, "POSTER_AB", False)


@pytest.fixture
def poster_ab(monkeypatch):
    import alphabet_pipeline as ap
    monkeypatch.setattr(ap, "POSTER_AB", True)
