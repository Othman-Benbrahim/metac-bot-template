"""0.10.367 : traits émotionnels des titres (part positive des scores EmoAtlas)."""
import emotions_questions as eq


def test_traits():
    em = {k: 0.0 for k in eq.EMOTIONS}
    em.update(anger=2.0, fear=-1.0, trust=1.0)
    t = eq.traits(em)
    assert round(t[0], 4) == round(__import__("math").log1p(2.0), 4) and t[2] == 0.0
