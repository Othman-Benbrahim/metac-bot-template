"""Dernier cours frais (API Ninjas) : admis seulement s'il date d'avant la date d'information, à 5 jours au plus."""
import cours_frais as cf
import seuils_prix as spx

T = "Will front-month ICE Brent crude futures settle above $100.00 per barrel on 27 November 2026?"


def _fred(monkeypatch, dernier_jour):
    pts = [(f"2026-{m:02d}-{d:02d}", 80.0 + (d % 3)) for m in (9, 10, 11) for d in range(1, 29)]
    pts = [p for p in pts if p[0] <= dernier_jour]
    monkeypatch.setattr(spx, "points", lambda s: pts)


def test_fred_ancien_cours_frais_admis(monkeypatch):
    _fred(monkeypatch, "2026-11-17")
    monkeypatch.setattr(cf, "dernier", lambda s: {"jour": "2026-11-23", "prix": 95.0, "contrat": "F27", "bourse": "ICE"})
    e = spx.estimer(T, "2026-11-24", "2026-11-27")
    assert e and e["dernier_prix"] == 95.0 and e["date_prix"] == "2026-11-23" and e["source_prix"].startswith("API Ninjas")


def test_cours_frais_posterieur_refuse(monkeypatch):
    _fred(monkeypatch, "2026-10-01")
    monkeypatch.setattr(cf, "dernier", lambda s: {"jour": "2026-11-23", "prix": 95.0})
    assert spx.estimer(T, "2026-10-10", "2026-10-20") is None      # banc historique : jamais de regard vers l'avant


def test_sans_cle_silence(monkeypatch):
    _fred(monkeypatch, "2026-11-17")
    monkeypatch.delenv("API_NINJAS_KEY", raising=False)
    cf.dernier.cache_clear()
    assert spx.estimer(T, "2026-11-24", "2026-11-27") is None
