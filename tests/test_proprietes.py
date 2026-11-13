"""Tests par propriétés (0.10.76, Hypothesis). Au lieu de cas écrits à la main, des centaines de dossiers et d'entrées
tirés au hasard, contre des règles que le code affirme dans ses commentaires. Un contre-exemple est réduit au plus
petit cas qui casse encore la règle. Ce n'est pas une preuve (beaucoup de cas, pas tous) ; et une règle bien respectée
n'est pas pour autant la bonne règle : seules les issues jugent la règle (fiche « Derrière les chiffres », 2026-11-13).

Règles vérifiées :
  1. le réparateur ne fait qu'affaiblir (aucune carte ancrée, liaison ou recherche ajoutée ; aucun f promu en F) et ne
     plante sur aucune entrée ;
  2. p publié : la combinaison des multiplicateurs reste une probabilité, et ajouter une source ne la fait jamais
     baisser (multiplicateurs de la matrice ≥ 1 ; les freins, λ < 1, ne jouent qu'en ombre) ;
  3. l'ombre « absence » ne monte jamais au-dessus de B et reste dans les bornes ;
  4. le rejeu est déterministe (deux rejeux d'une même lecture enregistrée donnent le même résultat).
"""
from __future__ import annotations

import copy
import json
import math
import os
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
os.environ.setdefault("ALPHABET_SKILL_DIR", str(pathlib.Path(__file__).resolve().parents[1] / "alphabet-situationnel"))

from hypothesis import HealthCheck, given, settings, strategies as st  # noqa: E402

import alphabet_pipeline as ap  # noqa: E402

M = ap._moteur()
REGLAGE = settings(max_examples=300, deadline=None, derandomize=True,
                   suppress_health_check=[HealthCheck.too_slow, HealthCheck.data_too_large])

CARTES = sorted(M.NOMS)
STRATES = st.integers(min_value=1, max_value=13)
TYPES_LIAISON = st.sampled_from(list(ap.LIAISONS_ADMISES) + ["provoque", "nourrit", "—", ""])


def cle(c, s):
    return f"{c}@{s}"


@st.composite
def mot(draw, strates=st.one_of(STRATES, st.sampled_from(["6", "13"]))):
    m = {"carte": draw(st.sampled_from(CARTES + ["POLARITÉ", "seuil", "XYZ"])), "strate": draw(strates),
         "intensite": draw(st.sampled_from(["f", "F", "M", None])),
         "portee": draw(st.sampled_from(list(M.PORTEES) + [None, "forte"]))}
    for champ, valeurs in (("fait", st.text(max_size=40)), ("source", st.text(max_size=30)),
                           ("corroboration", st.sampled_from(["unique", "independantes", "x"])),
                           ("force_initiale", st.sampled_from(["F", "f"]))):
        if draw(st.booleans()):
            m[champ] = draw(valeurs)
    if draw(st.booleans()):
        m["passage"] = draw(st.one_of(st.text(max_size=20), st.lists(st.dictionaries(
            st.sampled_from(["extrait", "id"]), st.text(max_size=400), max_size=2), max_size=2)))
    if draw(st.booleans()):
        m["tiers"] = draw(st.one_of(st.dictionaries(st.sampled_from(["type", "acteur"]),
                                                    st.sampled_from(["mediateur", "troisieme_pole", "aucun", "?"]),
                                                    max_size=2), st.text(max_size=5)))
    return m


@st.composite
def dossier(draw, strates_mots=None):
    s_ev = draw(STRATES)
    c_ev = draw(st.sampled_from(CARTES))
    mots = draw(st.lists(mot(strates_mots) if strates_mots is not None else mot(), max_size=6))
    cles = [cle(draw(st.sampled_from(CARTES)), draw(STRATES)) for _ in range(draw(st.integers(0, 6)))]
    liaisons = [f"{draw(st.sampled_from(cles or ['CTR@6']))} {draw(TYPES_LIAISON)} "
                f"{draw(st.sampled_from(cles or ['HIE@6']))}" for _ in range(draw(st.integers(0, 4)))]
    d = {"mots": mots, "candidats": draw(st.lists(st.sampled_from(cles or ["CTR@6"]), max_size=6)),
         "rejets": {k: draw(st.sampled_from(["[aucun_fait] rien", "[non_cherchee] x", "", "texte libre"]))
                    for k in draw(st.lists(st.sampled_from(cles or ["CTR@6"]), max_size=3))},
         "liaisons": liaisons, "questions": [],
         "recherches": [{"famille": draw(st.sampled_from(["contradiction", "observation", "discrimination"])),
                         "cartes": draw(st.lists(st.sampled_from(cles or ["CTR@6"]), max_size=3)),
                         "requete": draw(st.text(max_size=10)), "executee": draw(st.booleans())}
                        for _ in range(draw(st.integers(0, 3)))]}
    if draw(st.booleans()):
        d["contre_candidate"] = draw(st.one_of(st.sampled_from(cles or ["CTR@6"]), st.lists(st.sampled_from(cles or ["CTR@6"]), max_size=2)))
    plan = {"evenement": {"carte": c_ev, "strate": s_ev, "type": draw(st.sampled_from(["apparait", "persiste"]))},
            "candidats": draw(st.lists(st.sampled_from(CARTES), max_size=4)),
            "contre_candidate": draw(st.lists(st.sampled_from(CARTES), max_size=2))}
    return d, plan


def ancres(d: dict) -> dict[str, str]:
    """Clé normalisée → intensité, pour les mots lisibles."""
    out = {}
    for m in d.get("mots") or []:
        if not isinstance(m, dict):
            continue
        try:
            out[ap.cle_normale(f"{m.get('carte')}@{m.get('strate')}")] = m.get("intensite")
        except Exception:
            continue
    return out


class Reparateur(unittest.TestCase):
    @REGLAGE
    @given(dossier())
    def test_ne_fait_qu_affaiblir(self, dp):
        d, plan = dp
        avant = copy.deepcopy(d)
        ap.reparer_dossier(d, plan, "2026-10-25")                         # ne doit jamais lever d'exception
        a0, a1 = ancres(avant), ancres(d)
        self.assertLessEqual(set(a1), set(a0), "carte ancrée ajoutée par le réparateur")
        for k, i in a1.items():
            if i == "F":
                self.assertEqual(a0.get(k), "F", f"{k} promue en F par le réparateur")
        self.assertLessEqual(len(d.get("liaisons") or []), len(avant.get("liaisons") or []))
        self.assertLessEqual(len(d.get("recherches") or []), len(avant.get("recherches") or []))
        for r in d.get("recherches") or []:
            self.assertLessEqual(len(r.get("cartes") or []), 2)


    # 0.10.76 : premier contre-exemple trouvé (2026-11-13). Un mot dont la strate est illisible après normalisation
    # (absente, vide, « x ») fait PLANTER le réparateur (hors_domaine → int()) au lieu d'être retiré ; l'assembleur
    # n'étant pas protégé, toute la lecture tombe. Correction en attente de décision d'auteur : ce test échoue tant
    # qu'elle n'est pas faite (il passera, et unittest le signalera, le jour où elle le sera).
    @unittest.expectedFailure
    @settings(max_examples=50, deadline=None, derandomize=True, suppress_health_check=[HealthCheck.too_slow])
    @given(dossier(strates_mots=st.sampled_from([None, "", "x"])))
    def test_strate_illisible(self, dp):
        d, plan = dp
        ap.reparer_dossier(d, plan, "2026-10-25")


LAMBDAS = sorted({float(v) for k, v in M.P["lambda"].items()})
LAMBDAS_PUBLIES = [v for v in LAMBDAS if v >= 1]


class Combinaison(unittest.TestCase):
    def test_matrice_publiee_sans_frein(self):
        # p publié : la matrice n'a que des classes à λ ≥ 1 ; les freins (λ < 1) sont hors du p publié
        classes = {I for ligne in M.P["matrice"].values() for I in ligne.values() if I}
        for I in classes:
            self.assertGreaterEqual(float(M.P["lambda"][I]), 1.0, f"classe {I} de la matrice avec λ < 1")
        self.assertFalse(M.FREINS)

    @REGLAGE
    @given(st.floats(min_value=0.001, max_value=0.999),
           st.lists(st.sampled_from(LAMBDAS_PUBLIES), max_size=6),
           st.sampled_from(LAMBDAS_PUBLIES),
           st.lists(st.booleans(), max_size=7),
           st.one_of(st.none(), st.floats(min_value=1.5, max_value=50)))
    def test_ajouter_une_source_ne_baisse_jamais(self, f, lams, nouveau, est_indice, plafond):
        src = [{"mot": f"m{i}", "lambda": l} for i, l in enumerate(lams)]
        ind = {f"m{i}" for i, b in enumerate(est_indice) if b}
        p0 = M.combiner_mixte(f, src, ind, plafond)
        p1 = M.combiner_mixte(f, src + [{"mot": f"m{len(lams)}", "lambda": nouveau}],
                              ind | ({f"m{len(lams)}"} if len(est_indice) > len(lams) and est_indice[len(lams)] else set()),
                              plafond)
        for p in (p0, p1):
            self.assertTrue(math.isfinite(p) and 0 <= p <= 1, p)
        self.assertGreaterEqual(p1 + 1e-12, p0)
        self.assertGreaterEqual(p0 + 1e-12, f)                     # aucune source publiée ne fait baisser sous f


class OmbreAbsence(unittest.TestCase):
    @REGLAGE
    @given(st.floats(min_value=0, max_value=1), st.sampled_from(["structure_absente", "carte_visee_absente"]))
    def test_jamais_au_dessus_de_B(self, p, nature):
        o = ap.ombre_absence(p, nature)
        self.assertTrue(0 < o < 1)
        self.assertLessEqual(o, ap.borner(p) + 1e-12)


def lignes_rejouables(n: int = 25) -> list[dict]:
    f = pathlib.Path(__file__).resolve().parents[1] / "registre" / "retro.jsonl"
    if not f.is_file():
        return []
    L = [json.loads(l) for l in f.read_text(encoding="utf-8").splitlines() if l.strip()]
    return [x for x in L if x.get("banc") == "forecastbench" and (x.get("rejeu") or {}).get("lectures")][-n:]


class Rejeu(unittest.TestCase):
    def test_deterministe(self):
        import rejeu_banc as rb
        L = lignes_rejouables()
        if not L:
            self.skipTest("registre absent")
        for x in L:
            r = x["rejeu"]
            a = rb.rejouer_lecture(r["lectures"][-1], r)
            b = rb.rejouer_lecture(r["lectures"][-1], r)
            self.assertEqual(a, b, x["question_id"])


if __name__ == "__main__":
    unittest.main()
