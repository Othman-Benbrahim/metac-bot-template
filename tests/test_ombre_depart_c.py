from datetime import date

import bras_m
import collecte_sondages as cs


def test_ombre_c_fed_sans_reseau():
    r = bras_m.ombre_c("Will the Fed cut interest rates after its December 2026 meeting?", date(2026, 12, 20),
                       date(2026, 11, 21), 0.4)
    assert r is None or set(r) >= {"regles_rattachees", "regles_traduites", "p_C"}


def test_ombre_c_sondages(monkeypatch):
    entree = {"statut": "ok", "source": "wikipedia", "page": "x", "sujet": "Andy Biggs", "colonne_sujet": "Andy Biggs",
              "moyennes": {"Andy Biggs": {"moyenne": 45, "n": 5}, "Karrin Taylor Robson": {"moyenne": 22, "n": 5}}}
    monkeypatch.setattr(cs, "pour_question", lambda t, j: entree)
    r = bras_m.ombre_c("Will Andy Biggs win the 2026 Arizona Governor Republican primary election?", date(2026, 8, 4),
                       date(2026, 6, 7), 0.2)
    assert r and r["regles_traduites"] and r["p_C"] > 0.2 and r["sondages"]["colonne_sujet"] == "Andy Biggs"


def test_alertes():
    r = {"sujet": "Keiko Fujimori", "colonne_sujet": "Fujimori FP",
         "moyennes": {"Fujimori FP": {"moyenne": 70, "n": 1}, "JP": {"moyenne": 60, "n": 3}}}
    a = cs.alertes(r)
    assert any("total" in x for x in a) and any("un seul" in x for x in a)
