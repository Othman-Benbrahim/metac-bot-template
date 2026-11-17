"""0.10.221 : troisième codeur (Newsmap) et modèle à classe latente."""
import random

import collecte_rss as cr
import dico_newsmap as dn

YML = """AFRICA:
  MIDDLE:
    'CD': [République Démocratique du Congo, RD Congo, RDC, Kinshasa]
NORTH AMERICA:
  NORTH:
    'US': [United States, US, American*, Washington]
"""


def test_lire_et_detecter():
    d = dn.lire_yml(YML)
    assert d["US"][2] == "American*"
    m = dn.construire([d])
    assert dn.detecter("Americans vote ; Kinshasa", m) == {"US", "CD"}
    assert dn.detecter("tell us more", m) == set()           # sigle en casse stricte
    assert dn.detecter("US inflation", m) == {"US"}


def test_classe_latente_retrouve_les_parametres():
    random.seed(1)
    se, sp, c = [0.9, 0.7, 0.8], [0.999, 0.9995, 0.998], {}
    for _ in range(100000):
        y = random.random() < 0.02
        k = "".join("1" if random.random() < (se[j] if y else 1 - sp[j]) else "0" for j in range(3))
        c[k] = c.get(k, 0) + 1
    r = dn.classe_latente(c)
    assert abs(r["nous"]["sensibilite"] - 0.9) < 0.03
    assert abs(r["grasland"]["sensibilite"] - 0.7) < 0.03


def test_bilan_trois_seuil():
    assert "trop peu" in cr.bilan_trois({("RU", "2026-11-17", "111"): 3, ("_articles", "2026-11-17", "total"): 10})
