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


def test_etendu_lecture_des_candidates():
    def code(cartes, essentiel):
        return {"ok": True, "cartes": cartes, "rejetees": 0, "reste": None, "reste_essentiel": essentiel}
    ls = []
    for i in range(20):
        avec = i % 2 == 0
        ls.append({"qid": f"m:{i}:2025-01-01", "titre": "t",
                   "gpt16": code(["HIE"], True), "haiku16": code(["HIE"], True),
                   "gpt21": code(["HIE"] + (["CMP"] if avec else []), not avec),
                   "haiku21": code(["HIE"] + (["CMP"] if avec else []), not avec)})
    r = bc.resumer_etendu(ls, ["HIE", "SEU"])
    assert r["candidates"]["CMP"]["passe"] and not r["candidates"]["CNV"]["passe"]
    assert r["ensemble"]["couverture_monte_pour_les_deux"]
    assert set(bc.CANDIDATES) == {"CMP", "ITN", "CAP", "MAR", "CNV"}


def test_questions_combinees_ecartees():
    s = bc.situations(etendu=True)
    assert s and not any(bc.combinee(x) for x in s)
    assert bc.combinee({"qid": "infer:['1', '2']:2025-01-01", "titre": "x"})
