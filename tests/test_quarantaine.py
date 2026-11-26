from types import SimpleNamespace
import alphabet_bot as ab


def test_quarantaine_apres_trois_echecs(tmp_path, monkeypatch):
    monkeypatch.setattr(ab, "_echecs_fichier", lambda: tmp_path / "e.json")
    q = SimpleNamespace(id_of_post=1, page_url="https://www.metaculus.com/questions/1", id_of_question=2)
    for i in range(2):
        assert ab.echecs_noter([q], [RuntimeError("x")]) == []
    assert not ab.en_quarantaine(q)
    assert ab.echecs_noter([q], [RuntimeError("x")])
    assert ab.en_quarantaine(q)
    ab.echecs_noter([q], ["ok"])
    assert not ab.en_quarantaine(q)
