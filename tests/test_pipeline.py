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

PLAN = {"strates": [7, 6], "candidats": ["POL@7", "INC@7", "CTR@6", "HIE@6"], "contre_candidate": ["INC@7", "HIE@6"],
        "evenement": {"carte": "SEU", "strate": 7, "type": "apparait"}, "semantique": "au-moins-une-fois",
        "pourquoi_evenement": "YES = a threshold is crossed",
        "recherches_reference": ["fréquence historique des crises bilatérales avec rupture en trois mois"],
        "recherches": [{"famille": f, "cartes": [c], "requete": f"{f} requête {c}"}
                       for c in ("POL@7", "CTR@6") for f in ap.FAMILLES]
        + [{"famille": "discrimination", "cartes": ["POL@7", "SEU@7"], "requete": "discrimination POL SEU"},
           {"famille": "discrimination", "cartes": ["CTR@6", "HIE@6"], "requete": "discrimination CTR HIE"}]}


def vue(freq=0.2):
    return {"frequence": freq, "classe_de_reference": "crises bilatérales à deux blocs : rupture ou frappe reconnue en 3 mois (fictif)",
            "source": "registre fictif de démonstration", "fondement": "recherche [R1]", "periode": "2000-2025",
            "disponible_le": "2026-01-01", "calcul": "8 cas sur 40 crises",
            "classe_alternative": {"frequence": min(0.9, freq * 1.5), "classe_de_reference": "crises avec représailles annoncées (fictif)",
                                   "source": "fictif", "pourquoi_ecartee": "classe choisie d'après l'état présent"},
            "ecart_critere": "identique : rupture reconnue par une partie",
            "resolution": "une frappe ou une rupture reconnue par l'une des parties",
            "source_resolution": {"emetteur": "ministère des affaires étrangères de A (fictif)", "document": "communiqués",
                                  "regle_ambiguite": "seul compte un acte publié et daté"}}


def lecture():
    d = json.loads(ap.lire_ref("assets/dossier.exemple.json"))
    for m in d["mots"]:
        m["date_consultation"] = "2026-11-03"
    lec = {k: d[k] for k in ("candidats", "contre_candidate", "mots", "liaisons", "questions")}
    lec["rejets"] = d["rejets"]          # format ancien (texte simple) : admis, catégorie « non_classe »
    return lec


def lecture_vide():
    cats = ["aucun_fait", "marqueur_non_rempli", "contredit", "aucun_fait"]
    return {"candidats": PLAN["candidats"], "contre_candidate": PLAN["contre_candidate"],
            "rejets_classes": {c: {"categorie": k, "motif": "aucun fait ne remplit le marqueur"}
                               for c, k in zip(PLAN["candidats"], cats)},
            "mots": [], "liaisons": [], "questions": []}


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
        r, llm = lancer([PLAN, vue(0.2), lecture()])
        self.assertEqual(r.bras_poste, "C")
        self.assertAlmostEqual(r.p_B, 0.2)
        self.assertNotAlmostEqual(r.p_C, r.p_B)          # les cartes déplacent le taux de base
        self.assertIn("Posted arm: C", r.commentaire)
        self.assertIn("8 cas sur 40", r.commentaire)
        self.assertIn("TAUX DE BASE", llm.consignes[1])   # la vue extérieure vient avant toute carte
        self.assertNotIn("FICHES DES CANDIDATES", llm.consignes[1])
        c = r.ligne["bras"]["C"]
        self.assertEqual(c["statut"], "estime")
        self.assertTrue(all(x["executee"] for x in c["recherches"]))
        self.assertEqual(r.ligne["bras"]["B"]["source"], "registre fictif de démonstration")
        self.assertEqual(len(r.ligne["sceau"]), 64)

    def test_etat_nul_poste_b(self):
        r, _ = lancer([PLAN, vue(0.04), lecture_vide()])
        self.assertEqual(r.bras_poste, "B")
        self.assertAlmostEqual(r.p_poste, 0.04)
        self.assertEqual(r.ligne["bras"]["C"]["statut"], "etat_nul")
        self.assertIn("Posted arm: B", r.commentaire)
        self.assertIn("none anchored", r.commentaire)

    def test_rejets_classes(self):
        r, _ = lancer([PLAN, vue(0.04), lecture_vide()])
        cats = r.ligne["bras"]["C"]["rejets_classes"]
        self.assertEqual(cats["CTR@6"], "contredit")
        self.assertEqual(sorted(set(cats.values())), ["aucun_fait", "contredit", "marqueur_non_rempli"])
        self.assertIn("[contredit]", r.commentaire)              # le motif public garde sa catégorie

    def test_rejet_non_classe_admis(self):
        lec = lecture()                                          # format ancien : rejets en texte simple
        r, _ = lancer([PLAN, vue(), lec])
        self.assertEqual(r.bras_poste, "C")
        self.assertTrue(all(v == "non_classe" for v in r.ligne["bras"]["C"]["rejets_classes"].values()))

    def test_candidates_hors_matrice_corrigees(self):
        mauvais = dict(PLAN, candidats=["PER@7", "SEU@7"], contre_candidate=["PER@7"])   # SEU visée, PER seule source
        r, llm = lancer([mauvais, PLAN, vue(0.2), lecture()])
        self.assertEqual(r.bras_poste, "C")
        self.assertIn("TON PLAN PRÉCÉDENT A ÉTÉ REFUSÉ", llm.consignes[1])
        self.assertIn("MATRICE DES DYNAMIQUES", llm.consignes[0])

    def test_candidates_hors_matrice_refus(self):
        mauvais = dict(PLAN, candidats=["PER@7", "SEU@7"], contre_candidate=["PER@7"])
        r, _ = lancer([mauvais, mauvais])
        self.assertEqual(r.bras_poste, "A")
        self.assertEqual(r.ligne["bras"]["C"]["statut"], "refuse")
        self.assertIn("matrice", r.ligne["bras"]["C"]["motif"])

    def test_sources_matrice(self):
        src = dict(ap.sources_matrice("SEU"))
        self.assertIn("POL", src)
        self.assertNotIn("SEU", src)
        poids = [ap.POIDS[w] for _, w in ap.sources_matrice("SEU")]
        self.assertEqual(poids, sorted(poids, reverse=True))     # la plus forte d'abord

    def test_sans_vue_poste_a(self):
        r, _ = lancer([PLAN, {"frequence": None, "motif": "aucune base honnête"}])
        self.assertEqual(r.bras_poste, "A")
        self.assertEqual(r.ligne["bras"]["C"]["statut"], "sans_vue")
        self.assertIsNone(r.p_B)

    def test_recherche_sans_moteur_non_executee(self):
        r, _ = lancer([PLAN, vue(), lecture()], reelle=False)
        self.assertFalse(any(x["executee"] for x in r.ligne["bras"]["C"]["recherches"]))

    def test_hors_alphabet(self):
        r, _ = lancer([dict(PLAN, evenement=None, pourquoi_evenement="question nominative")])
        self.assertEqual(r.bras_poste, "A")
        self.assertAlmostEqual(r.p_poste, 0.3)
        self.assertEqual(r.ligne["bras"]["C"]["statut"], "hors_alphabet")

    def test_correction_puis_estime(self):
        mauvaise = lecture()
        del mauvaise["mots"][0]["a6"]          # F sans ligne A6 : le moteur refuse
        r, llm = lancer([PLAN, vue(), mauvaise, lecture()])
        self.assertEqual(r.bras_poste, "C")
        self.assertEqual(r.ligne["bras"]["C"]["tentatives"], 2)
        self.assertIn("ERREUR DU MOTEUR", llm.consignes[3])
        self.assertNotIn("vue_exterieure", llm.consignes[3])   # la correction ne touche pas à la vue extérieure

    def test_correction_vers_etat_nul(self):
        mauvaise = lecture()
        del mauvaise["mots"][0]["a6"]
        r, _ = lancer([PLAN, vue(0.1), mauvaise, lecture_vide()])
        self.assertEqual(r.bras_poste, "B")

    def test_refus_definitif(self):
        mauvaise = lecture()
        del mauvaise["mots"][0]["a6"]
        r, _ = lancer([PLAN, vue(0.25)] + [copy.deepcopy(mauvaise) for _ in range(ap.MAX_CORRECTIONS + 1)])
        self.assertEqual(r.bras_poste, "A")
        self.assertEqual(r.ligne["bras"]["C"]["statut"], "refuse")
        self.assertAlmostEqual(r.p_B, 0.25)    # la vue extérieure reste scorée

    def test_reponse_illisible(self):
        r, _ = lancer(["je ne sais pas"])
        self.assertEqual(r.bras_poste, "A")
        self.assertIn("plan illisible", r.ligne["bras"]["C"]["motif"])

    def test_evenement_incoherent(self):
        # POL visée en « apparait » alors qu'elle est candidate : refusé dès le plan (0.1.5), avant toute recherche.
        plan = dict(PLAN, evenement={"carte": "POL", "strate": 7, "type": "apparait"})
        r, llm = lancer([plan, plan])
        self.assertEqual(r.ligne["bras"]["C"]["statut"], "refuse")
        self.assertTrue(r.ligne["bras"]["C"]["motif"].startswith(("candidates :", "la carte visée")))
        self.assertEqual(len(llm.consignes), 2)
        # Filet de sécurité conservé : une lecture qui ancre la carte visée est refusée au contrôle de l'état.
        self.assertIn("déjà présente", ap.controle_etat({"mots": [{"carte": "POL", "strate": 7}]},
                                                         {"evenement": {"carte": "POL", "strate": 7, "type": "apparait"}}))

    def test_hors_strate_chiffree(self):
        plan = dict(PLAN, evenement={"carte": "CRO", "strate": 6, "type": "apparait"},   # économie : non chiffrée (L7)
                    candidats=["POL@6", "EME@6", "RES@6"], contre_candidate=["RES@6"])
        r, llm = lancer([plan, vue(0.03)])
        self.assertEqual(r.bras_poste, "A")
        self.assertEqual(r.ligne["bras"]["C"]["statut"], "hors_strate")
        self.assertAlmostEqual(r.p_B, 0.03)                       # la vue extérieure est enregistrée
        self.assertEqual(len(llm.consignes), 2)                   # lecture non lancée : pas de coût de lecture
        self.assertIn("[7]", llm.consignes[0])                    # le plan connaît les strates chiffrées

    def test_lecture_hors_strate_scellee(self):
        ancien = ap.LECTURE_HORS_STRATE
        ap.LECTURE_HORS_STRATE = True
        try:
            plan = dict(PLAN, evenement={"carte": "SEU", "strate": 6, "type": "apparait"})
            r, _ = lancer([plan, vue(0.03), lecture()])
            self.assertEqual(r.ligne["bras"]["C"]["statut"], "lu_non_chiffre")
            self.assertEqual(r.bras_poste, "A")
            self.assertTrue(r.ligne.get("dossier_fichier"))          # lecture scellée, chiffrable après une levée
            self.assertIsNone(r.p_C)
        finally:
            ap.LECTURE_HORS_STRATE = ancien

    def test_refus_structurel_sans_correction(self):
        ancien = ap.appeler_moteur
        ap.appeler_moteur = lambda *a, **k: {"erreur": "prévision chiffrée limitée aux strates [7] (décision L7, 0.7.34)"}
        try:
            r, llm = lancer([PLAN, vue(), lecture()])
            self.assertEqual(r.ligne["bras"]["C"]["tentatives"], 1)   # aucune correction payée pour rien
            self.assertEqual(len(llm.consignes), 3)
        finally:
            ap.appeler_moteur = ancien

    def test_journal(self):
        lancer([PLAN, vue(), lecture()])
        x = json.loads((ap.REGISTRE / "journal-bot.jsonl").read_text(encoding="utf-8").splitlines()[-1])
        s = x.pop("sceau")
        self.assertEqual(s, ap.sceau(x))
        self.assertTrue((ap.REGISTRE / x["dossier_fichier"]).is_file())

    def test_score(self):
        import score_registre as sr
        reg = Path(tempfile.mkdtemp(prefix="registre-score-"))
        ancien, ap.REGISTRE = ap.REGISTRE, reg
        try:
            lancer([PLAN, vue(0.2), lecture()])
            lancer([PLAN, vue(0.05), lecture_vide()])
            lancer([dict(PLAN, evenement=None)])
            s = sr.scorer(reg, {"4242": 0})
            self.assertEqual(s["resolues"], 3)
            self.assertEqual(s["apparie_ABC"]["n"], 1)               # seule la ligne aux trois bras est appariée
            self.assertEqual(s["bras_poste"], {"A": 1, "B": 1, "C": 1})
            self.assertEqual(s["bras"]["B"]["n"], 2)
            lignes = (reg / "journal-bot.jsonl").read_text(encoding="utf-8").splitlines()
            x = json.loads(lignes[0]); x["p_poste"] = 0.5            # une ligne retouchée est écartée
            (reg / "journal-bot.jsonl").write_text("\n".join([json.dumps(x)] + lignes[1:]) + "\n", encoding="utf-8")
            self.assertEqual(len(sr.scorer(reg, {"4242": 0})["retouchees"]), 1)
            # Issues gardées dans le registre, jamais réécrites.
            self.assertEqual(sr.enregistrer(reg, {"4242": 0}, {"n": 1}), 1)
            self.assertEqual(sr.enregistrer(reg, {"4242": 1}, {"n": 1}), 0)
            self.assertEqual(sr.issues_enregistrees(reg), {"4242": 0})
            self.assertTrue((reg / "score.json").is_file())
        finally:
            ap.REGISTRE = ancien


if __name__ == "__main__":
    unittest.main()
