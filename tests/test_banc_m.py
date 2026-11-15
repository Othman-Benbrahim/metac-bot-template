"""0.10.124 : banc des jugements intermédiaires, passage complet avec modèle et données simulés."""
import asyncio
import json
import os
import tempfile
import unittest
from unittest import mock

os.environ["ALPHABET_REGISTRE"] = tempfile.mkdtemp(prefix="registre-")   # avant tout import du pipeline

import alphabet_pipeline as _ap_regle_ab
_ap_regle_ab.POSTER_AB = False

import banc_m as bm


class FauxLlm:
    def __init__(self, *a, **k):
        pass

    async def invoke(self, consigne):
        if "Tu NE DONNES PAS de probabilité" in consigne:
            return json.dumps({"notes": {k: {"note": 2, "pourquoi": "ordinaire"} for k in bm.CLES}, "connait_issue": False})
        if "LE COMITÉ A NOTÉ" in consigne:
            return json.dumps({"p": 0.1, "raison": "notes ordinaires"})
        return json.dumps({"p": 0.3, "raison": "a", "connait_issue": False})


class TestBancM(unittest.TestCase):
    def test_lire_notes(self):
        r = bm.lire_notes({"notes": {"tendance": {"note": "3"}, "freins": 7, "calendrier": 1}})
        self.assertEqual(set(r), {"tendance", "calendrier"})

    def test_passage(self):
        import tempfile, pathlib, os
        d = pathlib.Path(tempfile.mkdtemp())
        jeux = ["2026-08-02", "2026-08-16"]
        def construire(i, j):
            return {"qid": f"fb:{j}:acled:{i}", "titre": "Will there be more Riots in X?", "criteres": "c",
                    "contexte": "", "source": "acled", "issue": int(i) % 2, "_q": {}, "_releve": {"points": []}}
        async def _json(url):
            return {}
        async def vue(x, q, j):
            return {"frequence": 0.2, "calcul": "k/n"}
        async def chercher(t, info):
            return "extrait"
        with mock.patch.object(bm, "FICHIER", d / "m.jsonl"), mock.patch.object(bm, "RESUME", d / "m.json"), \
             mock.patch.object(bm, "REGISTRE", d), mock.patch.object(bm, "VUS", d / "vus.txt"), \
             mock.patch.object(bm.fb, "jeux_candidats", lambda *a, **k: jeux), \
             mock.patch.object(bm.fb, "_json", _json), \
             mock.patch.object(bm.fb, "apparier", lambda qs, rs, s: [str(i) for i in range(6)]), \
             mock.patch.object(bm.fb, "construire", construire), \
             mock.patch.object(bm.fb, "vue_calculee", vue), \
             mock.patch.object(bm.ar, "recherche_bornee_disponible", lambda: True), \
             mock.patch.object(bm.ar, "chercher_avant", chercher), \
             mock.patch.object(bm.am, "llm", lambda *a, **k: FauxLlm()):
            (d / "vus.txt").write_text("fb:2026-08-02:acled:0\n")
            boucle = asyncio.new_event_loop()          # pas asyncio.run : il retire la boucle globale des autres tests
            try:
                self.assertEqual(boucle.run_until_complete(bm.principal(20, 3.0)), 0)
            finally:
                boucle.close()
            ls = bm.lignes()
            self.assertEqual(len(ls), 11)                       # 12 questions moins une déjà lue
            self.assertNotIn("fb:2026-08-02:acled:0", {x["question_id"] for x in ls})
            r = json.loads((d / "m.json").read_text())
            self.assertEqual(r["n"], 11)
            self.assertEqual(r["p_moyenne"]["M"], 0.1)
            self.assertIn("critere", r)
            self.assertIn("lineaire_descriptif", r)


if __name__ == "__main__":
    unittest.main()
