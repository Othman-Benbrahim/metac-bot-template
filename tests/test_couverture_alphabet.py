"""0.10.308 : banc de couverture de l'alphabet (données synthétiques)."""
import banc_couverture_alphabet as bc


def test_ancrage_mot_pour_mot():
    r = {"cartes": [{"carte": "HIE", "passage": "Trump sign"}, {"carte": "SEU", "passage": "inventé"},
                    {"carte": "XXX", "passage": "the bill"}, {"carte": "CTR", "passage": "bi"}, {"carte": "HIE", "passage": "the bill"}]}
    assert bc.ancrees(r, "Will Trump sign the bill?", {"HIE", "SEU", "CTR"}) == ["HIE"]


def test_kappa_et_glouton():
    assert bc.kappa([True, False, True, False], [True, False, True, False]) == 1.0
    assert bc.kappa([True] * 4, [True] * 4) is None
    assert bc.glouton_80([{"A"}, {"A"}, {"A", "B"}, {"C"}, set()]) == 2      # A couvre 3 sur 4 (75 %), il faut C en plus
    

def test_resumer_couverture():
    ls = [{"qid": f"m:{i}:2026-01-01", "titre": "t", "gpt": {"ok": True, "cartes": ["HIE"], "rejetees": 0, "reste": None, "reste_essentiel": False},
           "haiku": {"ok": True, "cartes": ["HIE"] if i % 2 else [], "rejetees": 1, "reste": "x" if i == 0 else None, "reste_essentiel": i == 0}}
          for i in range(10)]
    r = bc.resumer(ls, ["HIE", "SEU"])
    assert r["codees_par_les_deux"] == 10 and r["gpt"]["couverture"] == 1.0 and r["haiku"]["couverture"] == 0.9
    assert r["couverture_les_deux"] == 0.9 and r["gpt"]["jamais_utilisees"] == ["SEU"] and len(r["restes"]) == 1
