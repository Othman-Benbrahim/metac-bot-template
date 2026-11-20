"""Choix multiple : mélange 85 % bot + 15 % répartition égale (préenregistrement du 2026-11-20)."""
import choix_multiple_ancre as cm


def test_melange_somme_et_plancher():
    m = cm.melange({"a": 0.999, "b": 0.001, "c": 0.0, "d": 0.0})
    assert abs(sum(m.values()) - 1) < 1e-9
    assert min(m.values()) >= 0.15 / 4 - 1e-12


def test_gagnante_insensible_a_la_casse():
    assert cm.gagnante({"Democratic Party": 0.5, "Other": 0.5}, " democratic party ") == "Democratic Party"
    assert cm.gagnante({"a": 1.0}, None) is None


def test_ecart_signe():
    p = {"a": 0.9, "b": 0.1}
    m = cm.melange(p)
    assert cm.perte(m["b"]) < cm.perte(p["b"])          # l'outsider gagne : le mélange aide
    assert cm.perte(m["a"]) > cm.perte(p["a"])          # le favori gagne : le mélange coûte un peu


def test_e_processus_sans_donnees():
    assert cm.e_processus([])["atteint_a"] is None
