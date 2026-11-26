import os
from types import SimpleNamespace
import alphabet_bot as ab


def test_reprevoir_par_page_ou_question(monkeypatch):
    q = SimpleNamespace(id_of_question=47008, id_of_post=46751, page_url="https://www.metaculus.com/questions/46751")
    monkeypatch.setenv("ALPHABET_REPREVOIR", "46751")
    assert ab._a_reprevoir(q)
    monkeypatch.setenv("ALPHABET_REPREVOIR", "47008")
    assert ab._a_reprevoir(q)
    monkeypatch.setenv("ALPHABET_REPREVOIR", "")
    assert not ab._a_reprevoir(q)
