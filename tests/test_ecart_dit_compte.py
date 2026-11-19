"""0.10.361 : écart dit / compté ; règle des deux sources indépendantes (producteurs différents)."""
import ecart_dit_compte as e


def test_independance():
    assert e.independants("dyade:RUS:UKR", "hostilites:UA")[0] is False          # même producteur (GDELT)
    ok, note = e.independants("dyade:RUS:UKR", "ucdp:Ukraine")
    assert ok and "amont partagé" in note                                        # producteurs distincts, presse commune
    assert e.independants("dyade:RUS:UKR", "feux:UA") == (True, "amont distinct")
    assert e.independants("dyade:RUS:UKR", "inconnu:X")[0] is False


def test_semaines_et_ecart():
    assert e.par_semaine([("2026-11-18", 2.0), ("2026-11-16", 1.0), ("2026-11-23", 5.0)]) == {"2026-11-16": 3.0, "2026-11-23": 5.0}
    sem = [f"2026-{m:02d}-{d:02d}" for m in range(1, 7) for d in (5, 12, 19, 26)][:20]
    compte = {s: float(10 + i % 5) for i, s in enumerate(sem)}
    dit = {s: -0.5 * (10 + i % 5) for i, s in enumerate(sem)}
    dit[sem[10]] = 8.0                                                           # la presse raconte la paix ce jour-là
    r = e.ecarts(dit, compte)
    assert r["semaines"] == 20 and [x["semaine"] for x in r["semaines_d_ecart"]] == [sem[10]]
    assert r["semaines_d_ecart"][0]["z"] > 0
    assert "rien à conclure" in e.ecarts({"a": 1.0}, {"a": 2.0})["note"]
