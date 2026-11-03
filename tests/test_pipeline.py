"""Tests hors ligne du pipeline : modèle et recherche simulés, vrai moteur du skill.

    ALPHABET_SKILL_DIR=chemin/vers/alphabet-situationnel python -m unittest discover -s tests
"""
import asyncio
import copy
import json
import os
import sys
import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))
os.environ.setdefault("ALPHABET_REGISTRE", tempfile.mkdtemp(prefix="registre-"))
import alphabet_pipeline as ap  # noqa: E402

MAINTENANT = datetime(2026, 11, 3, 18, 0, tzinfo=timezone.utc)
Q = ap.Question(id=4242, url="https://www.metaculus.com/questions/4242/", titre="Will A and B cross an escalation threshold before 2027?",
                contexte="Fictitious test question.", criteres="Resolves YES if a recognized escalation threshold is crossed.",
                precisions="", resolution=date(2027, 1, 31))

PLAN = {"strates": [7, 6], "candidats": ["POL@7", "SEU@7", "CTR@6", "HIE@6"], "contre_candidate": ["SEU@7", "HIE@6"],
        "evenement": {"carte": "SEU", "strate": 7, "type": "apparait"}, "semantique": "au-moins-une-fois",
        "pourquoi_evenement": "YES = a threshold is crossed",
        "recherches": [{"famille": f, "cartes": [c], "requete": f"{f} requête {c}"}
                       for c in ("POL@7", "CTR@6") for f in ap.FAMILLES]
        + [{"famille": "discrimination", "cartes": ["POL@7", "SEU@7"], "requete": "discrimination POL SEU"},
           {"famille": "discrimination", "cartes": ["CTR@6", "HIE@6"], "requete": "discrimination CTR HIE"}]}


def dossier_valide(freq=0.2):
    d = json.loads(ap.lire_ref("assets/dossier.exemple.json"))
    for k in ("etat", "disponible_le", "recherches", "commentaire"):
        d.pop(k, None)
    for m in d["mots"]:
        m["date_consultation"] = "2026-11-03"
    ve = d["evenements"][0]["vue_exterieure"]
    ve.update(frequence=freq, periode="2000-2025", disponible_le="2026-01-01",
              classe_de_reference="crises bilatérales à deux blocs : rupture ou frappe reconnue en 3 mois (fictif)")
    ve["classe_alternative"]["frequence"] = min(0.9, freq * 1.5)
    return d


class LlmSimule:
    def __init__(self, reponses):
        self.reponses, self.consignes = list(reponses), []

    async def __call__(self, consigne):
        self.consignes.append(consigne)
        r = self.reponses.pop(0)
        return r if isinstance(r, str) else "```json\n" + json.dumps(r, ensure_ascii=False) + "\n```"


async def chercher(req):
    return f"Résultat factuel daté pour : {req}"


def lancer(reponses, p_A=0.3, reelle=True):
    llm = LlmSimule(reponses)
    r = asyncio.run(ap.prevoir_binaire(Q, "recherche générale", p_A, "raisonnement du modèle seul", llm, chercher,
                                       reelle, MAINTENANT))
    return r, llm


class Tests(unittest.TestCase):
    def test_bras_c_poste(self):
        r, llm = lancer([PLAN, dossier_valide(0.2)])
        self.assertEqual(r.bras_poste, "C")
        self.assertAlmostEqual(r.p_B, 0.2)
        self.assertIsNotNone(r.p_C)
        self.assertNotAlmostEqual(r.p_C, r.p_B)          # les cartes déplacent le taux de base
        self.assertIn("Posted arm: C", r.commentaire)
        self.assertIn("sealed before the alphabet", r.commentaire)
        self.assertNotIn("Polymarket odds", llm.consignes[0].split("Interdit")[0])
        c = r.ligne["bras"]["C"]
        self.assertEqual(c["statut"], "estime")
        self.assertTrue(all(x["executee"] for x in c["recherches"]))
        self.assertEqual(len(r.ligne["sceau"]), 64)

    def test_recherche_sans_moteur_non_executee(self):
        r, _ = lancer([PLAN, dossier_valide()], reelle=False)
        self.assertFalse(any(x["executee"] for x in r.ligne["bras"]["C"]["recherches"]))

    def test_hors_alphabet(self):
        plan = dict(PLAN, evenement=None, pourquoi_evenement="question nominative")
        r, _ = lancer([plan])
        self.assertEqual(r.bras_poste, "A")
        self.assertAlmostEqual(r.p_poste, 0.3)
        self.assertEqual(r.ligne["bras"]["C"]["statut"], "hors_alphabet")
        self.assertIn("Posted arm: A", r.commentaire)

    def test_correction_puis_estime(self):
        mauvais = dossier_valide()
        del mauvais["mots"][0]["a6"]          # F sans ligne A6 : le moteur refuse
        r, llm = lancer([PLAN, mauvais, dossier_valide()])
        self.assertEqual(r.bras_poste, "C")
        self.assertEqual(r.ligne["bras"]["C"]["tentatives"], 2)
        self.assertIn("ERREUR DU MOTEUR", llm.consignes[2])

    def test_refus_definitif(self):
        mauvais = dossier_valide(0.25)
        del mauvais["mots"][0]["a6"]
        r, _ = lancer([PLAN] + [copy.deepcopy(mauvais) for _ in range(ap.MAX_CORRECTIONS + 1)])
        self.assertEqual(r.bras_poste, "A")
        self.assertEqual(r.ligne["bras"]["C"]["statut"], "refuse")
        self.assertAlmostEqual(r.p_B, 0.25)    # la vue extérieure reste scorée

    def test_reponse_illisible(self):
        r, _ = lancer(["je ne sais pas"])
        self.assertEqual(r.bras_poste, "A")
        self.assertIn("plan illisible", r.ligne["bras"]["C"]["motif"])

    def test_evenement_incoherent(self):
        plan = dict(PLAN, evenement={"carte": "POL", "strate": 7, "type": "apparait"})   # POL déjà présente
        r, _ = lancer([plan] + [dossier_valide() for _ in range(ap.MAX_CORRECTIONS + 1)])
        self.assertEqual(r.ligne["bras"]["C"]["statut"], "refuse")
        self.assertIn("déjà présente", r.ligne["bras"]["C"]["motif"])

    def test_journal(self):
        lancer([PLAN, dossier_valide()])
        lignes = (ap.REGISTRE / "journal-bot.jsonl").read_text(encoding="utf-8").splitlines()
        x = json.loads(lignes[-1])
        s = x.pop("sceau")
        self.assertEqual(s, ap.sceau(x))
        self.assertTrue((ap.REGISTRE / x["dossier_fichier"]).is_file())

    def test_score(self):
        import score_registre as sr
        reg = Path(tempfile.mkdtemp(prefix="registre-score-"))
        ancien, ap.REGISTRE = ap.REGISTRE, reg
        try:
            r1, _ = lancer([PLAN, dossier_valide(0.2)])
            r2, _ = lancer([dict(PLAN, evenement=None)])
            s = sr.scorer(reg, {"4242": 0})
            self.assertEqual(s["resolues"], 2)
            self.assertEqual(s["apparie_ABC"]["n"], 1)               # seule la ligne aux trois bras est appariée
            self.assertEqual(s["bras_poste"], {"A": 1, "C": 1})
            lignes = (reg / "journal-bot.jsonl").read_text(encoding="utf-8").splitlines()
            x = json.loads(lignes[0]); x["p_poste"] = 0.5            # une ligne retouchée est écartée
            (reg / "journal-bot.jsonl").write_text("\n".join([json.dumps(x)] + lignes[1:]) + "\n", encoding="utf-8")
            self.assertEqual(len(sr.scorer(reg, {"4242": 0})["retouchees"]), 1)
        finally:
            ap.REGISTRE = ancien


if __name__ == "__main__":
    unittest.main()
