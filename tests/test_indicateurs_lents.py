"""Indicateurs lents (0.10.404)."""
import indicateurs_lents as il


def test_fourchette_suivante():
    x = [4.0 + 0.1 * ((-1) ** i) for i in range(40)]
    f = dict(il.fourchette_suivante(x))
    assert f[0.1] <= x[-1] <= f[0.9]


def test_reconnaissance():
    assert il.fourchette_publication("What will the U.S. unemployment rate be for November 2026?") is not None
    assert il.fourchette_publication("What will the Tokyo (Ku-area) core CPI year-on-year inflation rate be?") is None


def test_pas_de_confusion_entre_pays():
    assert il.fourchette_publication("What will Japan's core CPI year-over-year be, compared with the U.S.?") is None
