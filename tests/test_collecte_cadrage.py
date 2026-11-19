"""0.10.368 : cadrage des acteurs (phrases par acteur, semaine) ; EmoAtlas n'est pas importé hors du workflow."""
import collecte_cadrage as cc


def test_phrases_par_acteur():
    t = ("The Council condemns Russia's brutal attacks on Ukrainian cities. Russia must withdraw. "
         "The EU welcomes the agreement with Ukraine on reconstruction.")
    pa = cc.par_acteur(t)
    assert len(pa["russie"]) == 2 and len(pa["ukraine"]) == 2 and len(pa["ue"]) == 1
    assert cc.semaine("2026-11-19") == "2026-11-16"
