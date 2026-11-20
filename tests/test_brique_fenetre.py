"""0.10.378 : brique « occurrence dans une fenêtre »."""
import brique_fenetre as bf


def test_acteur_et_fenetre():
    assert bf.acteur("Will the U.S. conduct a ground invasion of Iran before May 2026?") == "militaire"
    assert bf.acteur("Will the Senate pass the bill before July 2026?") == "legislatif"
    assert bf.acteur("Will Volodymyr Zelenskyy and Vladimir Putin meet in person before September 1, 2026?") == "chef"
    assert bf.acteur("Will France recognize Palestine in 2025?") == "international"
    assert bf.fenetre(5) == "<=7" and bf.fenetre(45) == "31-90" and bf.fenetre(400) == ">180"


def test_calcul_chronologique():
    xs = []
    for i in range(80):
        xs.append({"source": "s", "id": str(i), "jeu": f"2025-0{1 + i % 6}-01", "resolue_le": "2025-01-15", "cloture": "2025-01-15",
                   "issue": int(i % 4 == 0), "structure": "autre", "acteur": "chef", "fenetre": "8-30", "p_R1": 0.3})
    xs.append({"source": "s", "id": "x", "jeu": "2026-02-01", "resolue_le": "2026-03-01", "issue": 0, "structure": "autre",
               "acteur": "chef", "fenetre": "8-30", "p_R1": 0.3})
    bf.calculer(xs)
    assert xs[-1]["niveau_F"] == "acteur×fenêtre" and 0.24 < xs[-1]["p_F"] < 0.3
    assert xs[0]["niveau_F"] == "base"                    # rien de passé avant le 2025-01-15
