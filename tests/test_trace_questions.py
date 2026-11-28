import json


def test_tracer_ecrit_une_ligne_avec_les_ecarts(tmp_path, monkeypatch):
    import alphabet_bot as ab
    import alphabet_pipeline as ap
    monkeypatch.setattr(ap, "registre_ecrivable", lambda *a, **k: tmp_path)
    bot = ab.AlphabetBot.__new__(ab.AlphabetBot)
    bot.publish_reports_to_metaculus = False

    class Q:
        id, url, titre = "42", "https://m/42", "Will X happen?"
    trace = {"p_A": 0.30, "essais_A": None, "bras": "M", "p_pipeline": 0.40, "brique": "banque_centrale",
             "brique_de_base": True, "p_brique": 0.70, "contradicteur": "dans_domaine", "garde_fou": False,
             "p_avant_juge": 0.70, "juge": "garde", "p_poste": 0.70}
    bot._tracer(Q(), trace)
    l = json.loads((tmp_path / "trace-questions.jsonl").read_text().splitlines()[0])
    assert l["question_id"] == "42" and l["p_poste"] == 0.70
    assert l["ecarts"] == {"pipeline": 0.1, "brique": 0.3, "contradicteur_garde_fou": 0.0, "juge": 0.0}


def test_tracer_ne_bloque_jamais(monkeypatch):
    import alphabet_bot as ab
    import alphabet_pipeline as ap
    monkeypatch.setattr(ap, "registre_ecrivable", lambda *a, **k: (_ for _ in ()).throw(OSError("x")))
    bot = ab.AlphabetBot.__new__(ab.AlphabetBot)
    bot.publish_reports_to_metaculus = False

    class Q:
        id, url, titre = "1", "u", "t"
    bot._tracer(Q(), {"p_A": 0.5, "p_pipeline": 0.5, "p_brique": 0.5, "p_avant_juge": 0.5, "p_poste": 0.5})


def test_tracer_brique_annulee(tmp_path, monkeypatch):
    import alphabet_bot as ab
    import alphabet_pipeline as ap
    monkeypatch.setattr(ap, "registre_ecrivable", lambda *a, **k: tmp_path)
    bot = ab.AlphabetBot.__new__(ab.AlphabetBot)
    bot.publish_reports_to_metaculus = False

    class Q:
        id, url, titre = "7", "u", "t"
    bot._tracer(Q(), {"p_A": 0.3, "p_pipeline": 0.4, "p_brique": 0.9, "brique_annulee": True,
                      "p_avant_juge": 0.4, "p_poste": 0.4})
    l = json.loads((tmp_path / "trace-questions.jsonl").read_text().splitlines()[0])
    assert l["ecarts"]["brique"] == 0.0 and l["ecarts"]["contradicteur_garde_fou"] == 0.0 and l["p_brique"] == 0.9
