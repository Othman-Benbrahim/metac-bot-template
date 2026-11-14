"""Tests hors ligne des suites de modèles, du contradicteur en ombre et de la surveillance (0.6.0)."""
import asyncio
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
os.environ["ALPHABET_REGISTRE"] = tempfile.mkdtemp(prefix="registre-")  # 0.8.0 : forcé, pas setdefault
os.environ["ALPHABET_TESTS"] = "1"
import alphabet_modeles as am  # noqa: E402
import alphabet_pipeline as ap  # noqa: E402
import test_pipeline as tp  # noqa: E402

def setUpModule():
    # 0.10.82 : ces tests éprouvent le chemin où C est posté ; la règle par défaut (B posté, C en ombre) a son propre test
    ap.POSTER_C = True


def tearDownModule():
    ap.POSTER_C = False


def appel_simule(disponibles):
    async def appel(modele, consigne):
        if modele not in disponibles:
            raise RuntimeError("503 indisponible")
        return disponibles[modele]
    return appel


class TestsModeles(unittest.TestCase):
    def test_suite_et_choix(self):
        self.assertEqual(am.suite(" openai/a, openai/b ,"), ["openai/a", "openai/b"])
        env = {"ALPHABET_LLM": "openai/large-3,openai/large-latest", "ALPHABET_PETIT_LLM": "openai/small",
               "ALPHABET_CONTRADICTEUR": "openai/qwen,openai/gptoss"}
        ok = '{"ok": true}'
        choix, essais = asyncio.run(am.choisir(env, appel_simule({"openai/large-latest": ok, "openai/qwen": "bonjour",
                                                                    "openai/gptoss": ok})))
        self.assertEqual(choix["principal"], "openai/large-latest")       # le premier ne répond pas : le suivant
        self.assertEqual(choix["petit"], "openai/large-latest")           # petit indisponible : retombe sur le principal
        self.assertEqual(choix["contradicteur"], "openai/gptoss")         # qwen répond sans JSON valide : écarté
        self.assertEqual(len(essais), 5)

    def test_appliquer(self):
        env = {"ALPHABET_CHERCHEUR": "smart-searcher/{petit}"}
        am.appliquer({"principal": "openai/L", "petit": "openai/S", "contradicteur": None}, env)
        self.assertEqual(env["ALPHABET_LLM"], "openai/L")
        self.assertEqual(env["ALPHABET_CHERCHEUR"], "smart-searcher/openai/S")
        self.assertEqual(env["ALPHABET_CONTRADICTEUR"], "")
        self.assertEqual(json.loads(env["ALPHABET_MODELES"])["chercheur"], "smart-searcher/openai/S")

    def test_modeles_au_registre(self):
        with mock.patch.dict(os.environ, {"ALPHABET_MODELES": json.dumps({"principal": "openai/L"})}):
            r, _ = tp.lancer([tp.PLAN, tp.vue(0.2), tp.lecture()])
        self.assertEqual(r.ligne["modeles"]["principal"], "openai/L")


class TestsContradicteur(unittest.TestCase):
    def lancer(self, verdicts):
        async def critique(consigne):
            self.assertIn("CONTRADICTEUR", consigne)
            return json.dumps({"verdicts": verdicts}) if isinstance(verdicts, dict) else verdicts
        llm = tp.LlmSimule([tp.PLAN, tp.vue(0.2), tp.lecture()])
        return asyncio.run(ap.prevoir_binaire(tp.Q, "r", 0.3, "a", llm, tp.chercher, True, tp.MAINTENANT,
                                              critique=critique))

    def test_retrait_recalcule_en_ombre(self):
        r = self.lancer({"POL@7": {"decision": "retirer", "motif": "absent des résultats"}})
        c = r.ligne["bras"]["C"]
        self.assertEqual(c["critique"]["retires"], ["POL@7"])
        self.assertIn(c["critique"]["statut"], ("estime", "non_estime", "refuse"))
        self.assertEqual(r.bras_poste, "C")
        self.assertAlmostEqual(r.p_poste, ap.borner(c["p_C"]))             # le posté ne change pas

    def test_affaiblir_et_inchange(self):
        r = self.lancer({"POL@7": {"decision": "affaiblir"}})
        self.assertEqual(r.ligne["bras"]["C"]["critique"]["affaiblis"], ["POL@7"])
        r = self.lancer({"POL@7": {"decision": "maintenir"}})
        self.assertEqual(r.ligne["bras"]["C"]["critique"]["statut"], "inchange")

    def test_tout_retirer_et_illisible(self):
        cartes = [f"{m['carte']}@{m['strate']}" for m in tp.lecture()["mots"]]
        r = self.lancer({k: {"decision": "retirer"} for k in cartes})
        cr = r.ligne["bras"]["C"]["critique"]
        self.assertEqual(cr["statut"], "etat_nul")
        self.assertAlmostEqual(cr["p_C_critique"], 0.2)                  # la règle donnerait alors B
        r = self.lancer("pas du JSON")
        self.assertEqual(r.ligne["bras"]["C"]["critique"]["statut"], "illisible")

    def test_sans_contradicteur_rien(self):
        r, _ = tp.lancer([tp.PLAN, tp.vue(0.2), tp.lecture()])
        self.assertIsNone(r.ligne["bras"]["C"]["critique"])


class TestsScoreParModele(unittest.TestCase):
    def test_filtre(self):
        import score_registre as sr
        reg = Path(tempfile.mkdtemp(prefix="registre-modele-"))
        ancien, ap.REGISTRE = ap.REGISTRE, reg
        try:
            for i, m in ((1, "openai/L"), (2, "anthropic/S")):
                with mock.patch.dict(os.environ, {"ALPHABET_MODELES": json.dumps({"principal": m})}):
                    q = tp.dataclasses.replace(tp.Q, id=i, url=f"u{i}")
                    tp.lancer([dict(tp.PLAN, evenement=None)], q=q)
            self.assertEqual(sr.scorer(reg, {"1": 0, "2": 1}, modele="openai/L")["questions"], 1)
            self.assertEqual(sr.scorer(reg, {"1": 0, "2": 1})["questions"], 2)
        finally:
            ap.REGISTRE = ancien


class TestsSante(unittest.TestCase):
    def test_ecrit_si_changement(self):
        import sante_modeles as sm
        reg = Path(tempfile.mkdtemp(prefix="registre-sante-"))
        ok = {"modele": "openai/L", "disponible": True, "json_ok": True, "secondes": 0.1, "erreur": None}

        async def sonder(m, appel=None):
            return dict(ok, modele=m)
        env = {"ALPHABET_LLM": "openai/L", "ALPHABET_PETIT_LLM": "", "ALPHABET_CONTRADICTEUR": ""}
        with mock.patch.object(sm, "REGISTRE", reg), mock.patch.object(am, "sonder", sonder), \
                mock.patch.dict(os.environ, env):
            self.assertEqual(asyncio.run(sm.principal()), 0)
            self.assertEqual(asyncio.run(sm.principal()), 0)
        self.assertEqual(len((reg / "sante-modeles.jsonl").read_text().splitlines()), 1)   # inchangé : une ligne

        async def panne(m, appel=None):
            return dict(ok, modele=m, disponible=False, json_ok=False, erreur="503")
        with mock.patch.object(sm, "REGISTRE", reg), mock.patch.object(am, "sonder", panne), \
                mock.patch.dict(os.environ, env):
            self.assertEqual(asyncio.run(sm.principal()), 1)              # plus de principal : rouge
        self.assertEqual(len((reg / "sante-modeles.jsonl").read_text().splitlines()), 2)



class TestsSaturation(unittest.TestCase):
    def test_reessaie_si_sature_puis_trouve(self):
        import alphabet_modeles as am_
        tours = {"n": 0}
        attentes = []

        async def appel(m, c):
            if m == "p1":
                tours["n"] += 1
                if tours["n"] < 3:
                    raise RuntimeError("ServiceUnavailableError: This model is temporarily at capacity")
            return '{"ok": true}'

        async def attendre(s):
            attentes.append(s)
        env = {"ALPHABET_LLM": "p1", "ALPHABET_PETIT_LLM": "s1"}
        choix, essais = asyncio.run(am_.choisir(env, appel, attendre))
        self.assertEqual(choix["principal"], "p1")
        self.assertEqual(attentes, [60, 120])

    def test_echec_durable_ne_fait_pas_attendre(self):
        import alphabet_modeles as am_
        attentes = []

        async def appel(m, c):
            raise RuntimeError("NotFoundError: model does not exist")

        async def attendre(s):
            attentes.append(s)
        choix, _ = asyncio.run(am_.choisir({"ALPHABET_LLM": "x"}, appel, attendre))
        self.assertIsNone(choix["principal"])
        self.assertEqual(attentes, [])



class TestsTenace(unittest.TestCase):
    def test_leger_passe_au_secours(self):
        import alphabet_bot as ab
        appels = []

        async def faux(self, prompt, system_prompt=None):
            appels.append(self.model)
            if self.model == "openai/s1":
                raise RuntimeError("ServiceUnavailableError: at capacity")
            return "ok"
        with mock.patch.object(ab.GeneralLlm, "invoke", faux), mock.patch.object(ab.asyncio, "sleep", mock.AsyncMock()):
            m = ab.LlmTenace("openai/s1", attentes=(20,), secours=["openai/s2"])
            ab.BASCULES.clear()
            self.assertEqual(asyncio.run(m.invoke("x")), "ok")
        self.assertEqual(appels, ["openai/s1", "openai/s1", "openai/s2"])
        self.assertEqual(ab.BASCULES, [{"de": "openai/s1", "vers": "openai/s2"}])

    def test_erreur_durable_remonte(self):
        import alphabet_bot as ab

        async def faux(self, prompt, system_prompt=None):
            raise ValueError("mauvaise requête")
        with mock.patch.object(ab.GeneralLlm, "invoke", faux):
            with self.assertRaises(ValueError):
                asyncio.run(ab.LlmTenace("openai/p", secours=["openai/q"]).invoke("x"))

    def test_secours_du_petit(self):
        env = {"ALPHABET_LLM": "p1,p2", "ALPHABET_PETIT_LLM": "s1,s2"}
        am.appliquer({"principal": "p1", "petit": "s1", "contradicteur": None}, env)
        self.assertEqual(env["ALPHABET_PETIT_SECOURS"], "s2,p1")


if __name__ == "__main__":
    unittest.main()
