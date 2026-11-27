"""0.10.517 : garde-fou général (brique extrême contredite par le modèle seul)."""
from types import SimpleNamespace

import alphabet_bot as ab
import alphabet_pipeline as ap


def _bot():
    return object.__new__(ab.AlphabetBot)


def test_extreme_et_desaccord(tmp_path, monkeypatch):
    monkeypatch.setattr(ap, "registre_ecrivable", lambda *a, **k: tmp_path)
    q = SimpleNamespace(id=1, url="u", titre="t")
    p, gf = _bot()._garde_fou(q, "rencontres", 0.05, 0.80)
    assert gf and p == 0.10 and (tmp_path / "journal-garde-fou.jsonl").exists()


def test_accord_rien(tmp_path, monkeypatch):
    monkeypatch.setattr(ap, "registre_ecrivable", lambda *a, **k: tmp_path)
    q = SimpleNamespace(id=1, url="u", titre="t")
    assert _bot()._garde_fou(q, "scrutin", 0.97, 0.75) == (0.97, False)     # désaccord de 22 points seulement
    assert _bot()._garde_fou(q, "scrutin", 0.60, 0.05) == (0.60, False)     # brique non extrême


def test_famille_exemptee(tmp_path, monkeypatch):
    monkeypatch.setattr(ap, "registre_ecrivable", lambda *a, **k: tmp_path)
    monkeypatch.setattr(ab, "GF_EXEMPTES", {"football_elo"})
    q = SimpleNamespace(id=1, url="u", titre="t")
    assert _bot()._garde_fou(q, "football_elo", 0.98, 0.30) == (0.98, False)
