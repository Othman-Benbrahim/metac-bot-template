"""Tests hors ligne du pipeline : modèle et recherche simulés, vrai moteur du skill.

    ALPHABET_SKILL_DIR=chemin/vers/alphabet-situationnel python -m unittest discover -s tests
"""
import asyncio
import copy
import dataclasses
import json
import math
import os
import sys
import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))
os.environ["ALPHABET_REGISTRE"] = tempfile.mkdtemp(prefix="registre-")  # 0.8.0 : forcé, pas setdefault
os.environ["ALPHABET_TESTS"] = "1"
import alphabet_pipeline as ap  # noqa: E402

ap.NB_VUES = 1   # les tests historiques fournissent une seule vue ; les vues multiples ont leurs propres tests
ap.CLASSE_FIGEE = False   # idem pour l'étape « définir la classe » (0.4.0), testée à part
ap.PUITS = False   # idem pour les puits de données (0.7.0), testés dans test_puits.py

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


def vue(freq=0.2, source="registre fictif de démonstration"):
    return {"frequence": freq, "classe_de_reference": "crises bilatérales à deux blocs : rupture ou frappe reconnue en 3 mois (fictif)",
            "source": source, "fondement": "recherche [R1]", "periode": "2000-2025",
            "disponible_le": "2026-01-01", "calcul": "8 cas sur 40 crises", "expression": repr(freq),
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


def lecture_vide(cats=("aucun_fait", "marqueur_non_rempli", "contredit", "aucun_fait")):
    return {"candidats": PLAN["candidats"], "contre_candidate": PLAN["contre_candidate"],
            "rejets_classes": {c: {"categorie": k, "motif": "aucun fait ne remplit le marqueur"}
                               for c, k in zip(PLAN["candidats"], cats)},
            "mots": [], "liaisons": [], "questions": []}


class LlmSimule:
    def __init__(self, reponses):
        self.reponses, self.consignes = list(reponses), []

    async def __call__(self, consigne):
        self.consignes.append(consigne)
        if not self.reponses:
            raise RuntimeError("modèle simulé : plus de réponse prévue")
        r = self.reponses.pop(0)
        return r if isinstance(r, str) else "```json\n" + json.dumps(r, ensure_ascii=False) + "\n```"


async def chercher(req):
    return f"Résultat factuel daté pour : {req}"


def lancer(reponses, p_A=0.3, reelle=True, q=Q, publie=True, mode="minibench", maintenant=MAINTENANT):
    llm = LlmSimule(reponses)
    r = asyncio.run(ap.prevoir_binaire(q, "recherche générale", p_A, "raisonnement du modèle seul", llm, chercher,
                                       reelle, maintenant, publie=publie, mode=mode))
    return r, llm


class Tests(unittest.TestCase):
    def test_a_repete_en_ombre(self):
        # 0.10.5 (§35) : K essais du modèle seul scellés avec A ; le premier reste le bras A, rien d'autre ne change.
        llm = LlmSimule([PLAN, vue(0.2), lecture()])
        r = asyncio.run(ap.prevoir_binaire(Q, "recherche générale", 0.3, "raisonnement", llm, chercher, True,
                                           MAINTENANT, publie=True, mode="minibench", essais_A=[0.5, 0.4]))
        e = r.ligne["bras"]["A"]["essais"]
        self.assertEqual(e["n"], 3)
        self.assertAlmostEqual(e["moyenne"], 0.4)
        self.assertAlmostEqual(r.p_A, 0.3)
        self.assertTrue(0.3 < e["moyenne_logit"] < 0.5)
        self.assertEqual(r.ligne["bras"]["A"]["sceau"], ap.sceau({"question": str(Q.id), "date": MAINTENANT.date().isoformat(),
                                                                  **{k: v for k, v in r.ligne["bras"]["A"].items() if k != "sceau"}}))

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
        om = c["ombre_causale"]                           # 0.10.3 (§33) : sondes du moteur, en ombre
        self.assertIsNotNone(om)
        self.assertIn("p_mediation", om)
        self.assertTrue(om["ablation"])
        self.assertIsInstance(om["p_noisy_or"], float)      # 0.10.4 (§34) : en ombre
        self.assertIsInstance(om["valeur_information"]["arret"], bool)
        self.assertEqual([t["alpha"] for t in om["tempere"]], [0.25, 0.5, 0.75])   # 0.10.5 (§35) : en ombre
        self.assertAlmostEqual(r.p_C, c["p_C"])          # le chiffre posté reste celui du calcul actuel
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

    def test_rejets_en_liste(self):
        lec = lecture_vide()
        lec["rejets_classes"] = [{"carte": c, **v} for c, v in lec["rejets_classes"].items()]   # forme vue en vrai
        r, _ = lancer([PLAN, vue(0.04), lec])
        self.assertEqual(r.bras_poste, "B")
        self.assertEqual(r.ligne["bras"]["C"]["rejets_classes"]["CTR@6"], "contredit")

    def test_erreur_alphabet_journalisee(self):
        ancien = ap.alphabet

        async def panne(*a, **k):
            raise AttributeError("'list' object has no attribute 'items'")
        ap.alphabet = panne
        try:
            r, _ = lancer([])
        finally:
            ap.alphabet = ancien
        self.assertEqual(r.bras_poste, "A")
        self.assertEqual(r.ligne["bras"]["C"]["statut"], "erreur")
        self.assertIn("AttributeError", r.ligne["bras"]["C"]["motif"])
        self.assertEqual(len(r.ligne["sceau"]), 64)               # la ligne existe, scellée

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
        r, _ = lancer([mauvais, mauvais, mauvais])                 # 0.8.0 : deux corrections du plan
        self.assertEqual(r.bras_poste, "A")
        self.assertEqual(r.ligne["bras"]["C"]["reprises_plan"], 2)
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
        r, llm = lancer([plan, plan, plan])
        self.assertEqual(r.ligne["bras"]["C"]["statut"], "refuse")
        self.assertTrue(r.ligne["bras"]["C"]["motif"].startswith(("candidates :", "la carte visée")))
        self.assertEqual(len(llm.consignes), 3)
        # Filet de sécurité conservé : une lecture qui ancre la carte visée est refusée au contrôle de l'état.
        self.assertIn("déjà présente", ap.controle_etat({"mots": [{"carte": "POL", "strate": 7}]},
                                                         {"evenement": {"carte": "POL", "strate": 7, "type": "apparait"}}))

    def test_hors_strate_chiffree(self):
        plan = dict(PLAN, evenement={"carte": "CRO", "strate": 6, "type": "apparait"},   # économie : non chiffrée (L7)
                    candidats=["POL@6", "EME@6", "RES@6"], contre_candidate=["RES@6"])
        ancien, ap.EXPLORATOIRE = ap.EXPLORATOIRE, False          # comportement d'avant 0.9.0
        try:
            r, llm = lancer([plan, vue(0.03)])
        finally:
            ap.EXPLORATOIRE = ancien
        self.assertEqual(r.bras_poste, "A")
        self.assertEqual(r.ligne["bras"]["C"]["statut"], "hors_strate")
        self.assertAlmostEqual(r.p_B, 0.03)                       # la vue extérieure est enregistrée
        self.assertEqual(len(llm.consignes), 2)                   # lecture non lancée : pas de coût de lecture
        self.assertNotIn("Strates chiffrées", llm.consignes[0])  # 0.4.0 : étiquette de strate posée à l'aveugle

    def test_lecture_hors_strate_scellee(self):
        ancien, ancien_x = ap.LECTURE_HORS_STRATE, ap.EXPLORATOIRE
        ap.LECTURE_HORS_STRATE, ap.EXPLORATOIRE = True, False
        try:
            plan = dict(PLAN, evenement={"carte": "SEU", "strate": 6, "type": "apparait"})
            r, _ = lancer([plan, vue(0.03), lecture()])
            self.assertEqual(r.ligne["bras"]["C"]["statut"], "lu_non_chiffre")
            self.assertEqual(r.bras_poste, "A")
            self.assertTrue(r.ligne.get("dossier_fichier"))          # lecture scellée, chiffrable après une levée
            self.assertIsNone(r.p_C)
        finally:
            ap.LECTURE_HORS_STRATE, ap.EXPLORATOIRE = ancien, ancien_x

    def test_bras_exploratoire_hors_strate(self):
        # 0.9.0 (décision d'auteur ; skill §29) : hors strate 7, l'alphabet lit et le moteur chiffre en exploratoire ;
        # le chiffre est scellé, JAMAIS posté (A posté), et l'état nul exploratoire ne fait pas poster B.
        plan = dict(PLAN, evenement={"carte": "SEU", "strate": 6, "type": "apparait"})
        appels = []
        ancien = ap.appeler_moteur

        def moteur(*a, **k):
            appels.append(k.get("exploratoire"))
            return {"p": 0.41, "p_sans_cartes": 0.03, "drapeaux": ["EXPLORATOIRE (§29)"]}
        ap.appeler_moteur = moteur
        try:
            r, _ = lancer([plan, vue(0.03), lecture()])
        finally:
            ap.appeler_moteur = ancien
        c = r.ligne["bras"]["C"]
        self.assertEqual(appels, [True])
        self.assertEqual(c["statut"], "hors_strate")
        self.assertEqual(c["exploratoire"]["statut"], "estime")
        self.assertAlmostEqual(c["exploratoire"]["p_C"], 0.41)
        self.assertEqual(c["exploratoire"]["strate"], 6)
        self.assertIsNone(c.get("p_C"))
        self.assertEqual(r.bras_poste, "A")
        self.assertIn("NOT the posted forecast", r.ligne["commentaire"])
        self.assertTrue(r.ligne.get("dossier_fichier"))
        r, _ = lancer([plan, vue(0.03), lecture_vide(("contredit",) * 4)])    # état nul exploratoire
        self.assertEqual(r.ligne["bras"]["C"]["exploratoire"]["statut"], "etat_nul")
        self.assertEqual(r.bras_poste, "A")                               # pas B : hors strate 7, rien ne change

    def test_correction_symetrique(self):
        # 0.9.1 : une candidate CONTREDITE par les faits abaisse la cote (même λ, inversé) ; en ombre, jamais postée.
        r, _ = lancer([PLAN, vue(0.10), lecture_vide(("contredit",) * 4)])        # état nul, candidates contredites
        sy = r.ligne["bras"]["C"]["symetrique"]
        self.assertEqual(r.bras_poste, "B")                                     # la publication ne change pas
        self.assertLess(sy["p"], 0.10)                                          # la lecture abaisse enfin B
        self.assertGreater(sy["lr_contre"], 1)
        self.assertTrue(sy["contredites"])
        r, _ = lancer([PLAN, vue(0.10), lecture_vide(("aucun_fait",) * 4)])       # rien de contredit : pas de chiffre
        self.assertIsNone(r.ligne["bras"]["C"]["symetrique"])
        r, _ = lancer([PLAN, vue(0.03), lecture()])                              # estimé : C symétrique ≤ C
        c = r.ligne["bras"]["C"]
        if c.get("symetrique"):
            self.assertLessEqual(c["symetrique"]["p"], ap.borner(c["p_C"]) + 1e-9)

    def test_questions_derivees(self):
        # 0.9.1 : non binaires ramenées à une question binaire au point le plus informatif de A
        num = {"declared_percentiles": [{"percentile": 0.1, "value": 10}, {"percentile": 0.4, "value": 40},
                                        {"percentile": 0.6, "value": 60}, {"percentile": 0.9, "value": 90}]}
        d = ap.question_derivee("numerique", "Combien ?", "valeur officielle", num, "kt")
        self.assertAlmostEqual(d["seuil"], 50)
        self.assertEqual(d["p_A"], 0.5)
        self.assertIn("greater than 50 kt", d["titre"])
        self.assertEqual(ap.issue_derivee(d, "61.2"), 1)
        self.assertEqual(ap.issue_derivee(d, "12"), 0)
        self.assertEqual(ap.issue_derivee(d, "above_upper_bound"), 1)
        self.assertIsNone(ap.issue_derivee(d, "annulled"))
        mc = {"predicted_options": [{"option_name": "Alpha", "probability": 0.2}, {"option_name": "Beta", "probability": 0.7},
                                    {"option_name": "Gamma", "probability": 0.1}]}
        d = ap.question_derivee("choix_multiple", "Qui ?", "c", mc)
        self.assertEqual((d["option"], d["p_A"]), ("Beta", 0.7))
        self.assertEqual(ap.issue_derivee(d, "Beta"), 1)
        self.assertEqual(ap.issue_derivee(d, "Alpha"), 0)
        t0 = datetime(2027, 3, 1, tzinfo=timezone.utc).timestamp()
        dt = {"declared_percentiles": [{"percentile": 0.25, "value": t0 - 86400 * 30}, {"percentile": 0.75, "value": t0 + 86400 * 30}]}
        d = ap.question_derivee("date", "Quand ?", "c", dt)
        self.assertEqual(d["seuil_lisible"], "2027-03-01")
        self.assertEqual(ap.issue_derivee(d, "2027-05-01T00:00:00Z"), 1)
        self.assertEqual(ap.issue_derivee(d, "2027-01-01"), 0)

    def test_exploration_non_binaire_et_score(self):
        import score_registre as sr
        reg = Path(tempfile.mkdtemp(prefix="registre-autres-"))
        ancien, ap.REGISTRE = ap.REGISTRE, reg
        ancien_m = ap.appeler_moteur
        ap.appeler_moteur = lambda *a, **k: {"p": 0.7, "p_sans_cartes": 0.4, "drapeaux": []}
        d = ap.question_derivee("choix_multiple", "Qui ?", "c", {"predicted_options": [
            {"option_name": "Beta", "probability": 0.6}, {"option_name": "Alpha", "probability": 0.4}]})
        try:
            ex = asyncio.run(ap.explorer_derivee(d, "77", "u", "", "", date(2027, 1, 1), "recherche", LlmSimule(
                [PLAN, vue(0.4), lecture()]), chercher, True))
            self.assertEqual(ex["statut"], "estime")                # strate 7 : chiffré normalement, mais JAMAIS posté
            self.assertAlmostEqual(ex["p_C"], 0.7)
            self.assertTrue((reg / ex["dossier_fichier"]).is_file())
            self.assertIn("puits", ex)                              # 0.9.6 : trace des puits enregistrée
            self.assertIn("compte_calcule", ex)
            self.assertIn("NOT the posted forecast", ap.ligne_exploratoire_autre(ex))
            ligne = {"version_bot": ap.VERSION_BOT, "question_id": "77", "url": "u", "type": "choix_multiple",
                     "mode": "minibench", "publie": True, "exploratoire": ex}
            ligne["sceau"] = ap.sceau(ligne)
            (reg / "journal-autres.jsonl").write_text(json.dumps(ligne) + "\n", encoding="utf-8")
            (reg / "issues-autres.jsonl").write_text(json.dumps({"question_id": "77", "issue": "Beta"}) + "\n", encoding="utf-8")
            r = sr.scorer_explo_autres(reg)
        finally:
            ap.REGISTRE, ap.appeler_moteur = ancien, ancien_m
        self.assertEqual(r["resolues_chiffrees"], 1)
        self.assertGreater(r["C_exploratoire_sur_B"]["questions_gagnees"], 0)   # 0,7 contre 0,4, issue OUI
        self.assertIsNotNone(r["C_exploratoire_sur_A"])

    def test_score_exploratoire_a_part(self):
        import score_registre as sr
        reg = Path(tempfile.mkdtemp(prefix="registre-explo-"))
        ancien, ap.REGISTRE = ap.REGISTRE, reg
        ancien_m = ap.appeler_moteur
        ap.appeler_moteur = lambda *a, **k: {"p": 0.41, "p_sans_cartes": 0.03, "drapeaux": []}
        plan = dict(PLAN, evenement={"carte": "SEU", "strate": 6, "type": "apparait"})
        try:
            lancer([plan, vue(0.03), lecture()], q=dataclasses.replace(Q, id=9, url="https://www.metaculus.com/questions/9/"))
            s = sr.scorer(reg, {"9": 1})
        finally:
            ap.REGISTRE, ap.appeler_moteur = ancien, ancien_m
        self.assertEqual(s["C_exploratoire_sur_B"]["n"], 1)
        self.assertGreater(s["C_exploratoire_sur_B"]["tous"]["questions_gagnees"], 0)   # 0,41 contre 0,03, issue OUI
        self.assertIn("6", s["C_exploratoire_sur_B"]["par_strate"])
        self.assertEqual(s["statuts_exploratoires"], {"estime": 1})
        self.assertIsNone(s["apparie_ABC"])                          # hors verdict principal : C n'est pas apparié

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
        q1, q2, q3 = (dataclasses.replace(Q, id=i, url=f"https://www.metaculus.com/questions/{i}/") for i in (1, 2, 3))
        try:
            lancer([PLAN, vue(0.2), lecture()], q=q1)
            lancer([PLAN, vue(0.05), lecture_vide()], q=q2)
            lancer([dict(PLAN, evenement=None)], q=q3)
            issues = {"1": 0, "2": 0, "3": 1}
            s = sr.scorer(reg, issues)
            self.assertEqual(s["resolues"], 3)
            self.assertEqual(s["apparie_ABC"]["n"], 1)               # seule la ligne aux trois bras est appariée
            self.assertEqual(s["bras_poste"], {"A": 1, "B": 1, "C": 1})
            self.assertEqual(s["bras"]["B"]["n"], 2)
            self.assertIn("C_noisy_or", s["C_noisy_or_sur_C"]["verdict"])
            self.assertIn("C_tempere", s["C_tempere_sur_C"]["verdict"])        # 0.10.5 (§35)   # 0.10.4 (§34) : ombres comparées à C
            self.assertEqual(sum(v["questions"] for k, v in s["C_selon_arret_vdi"].items() if k != "note"), 1)
            lignes = (reg / "journal-bot.jsonl").read_text(encoding="utf-8").splitlines()
            x = json.loads(lignes[0]); x["p_poste"] = 0.5            # une ligne retouchée est écartée
            (reg / "journal-bot.jsonl").write_text("\n".join([json.dumps(x)] + lignes[1:]) + "\n", encoding="utf-8")
            self.assertEqual(len(sr.scorer(reg, issues)["retouchees"]), 1)
            # Issues gardées dans le registre, jamais réécrites.
            self.assertEqual(sr.enregistrer(reg, {"4242": 0}, {"n": 1}), 1)
            self.assertEqual(sr.enregistrer(reg, {"4242": 1}, {"n": 1}), 0)
            self.assertEqual(sr.issues_enregistrees(reg), {"4242": 0})
            self.assertTrue((reg / "score.json").is_file())
        finally:
            ap.REGISTRE = ancien

    # --- 0.2.0 : correctifs de l'audit ---

    def test_score_log_base(self):                                # 0.2.1 : le log, règle de Metaculus
        import score_registre as sr
        self.assertAlmostEqual(sr.score_reference(0.5, 1), 0)
        self.assertAlmostEqual(sr.score_reference(0.999, 1), 100 * (math.log2(0.999) + 1))
        self.assertAlmostEqual(sr.gain_pair(0.8, 0.5, 1), 100 * math.log(0.8 / 0.5))
        # Le log punit l'extrême faux bien plus que le Brier : un seul 0,001 manqué domine.
        apparies = [({"C": 0.1, "B": 0.2, "A": 0.2}, 0)] * 9 + [({"C": 0.001, "B": 0.05, "A": 0.05}, 1)]
        c = sr.comparer(apparies, "C", "B")
        self.assertLess(c["gain_log_moyen"], 0)                   # C perd en log, à cause d'une seule question
        self.assertGreater(c["fragilite"]["gain_sans_pire_question"], 0)   # sans elle, C gagne : fragile
        self.assertEqual((c["questions_gagnees"], c["questions_perdues"]), (9, 1))
        self.assertLess(c["brier_critere_L7"]["ecart_moyen"], 0)    # le Brier, lui, donne C meilleur...
        self.assertFalse(c["brier_critere_L7"]["accord_avec_log"])  # ... et le désaccord est signalé

    # --- 0.2.2 : angles morts de l'état nul ---

    RELANCE = {"recherches": [{"cartes": ["POL@7"], "requete": "nouvelle requête sur le phénomène politique"},
                              {"cartes": ["HIE@6"], "requete": "nouvelle requête sur la hiérarchie"}]}

    def test_relance_ancre_des_cartes(self):
        r, llm = lancer([PLAN, vue(0.2), lecture_vide(), self.RELANCE, lecture()])
        self.assertEqual(r.bras_poste, "C")                       # la relance a trouvé : le moteur juge, C posté
        rel = r.ligne["bras"]["C"]["relance"]
        self.assertEqual(sorted(rel["cibles"]), ["HIE@6", "POL@7"])   # seules les candidates « aucun_fait »
        self.assertGreater(rel["mots_apres"], 0)
        self.assertIn("Étape 3 bis", llm.consignes[3])
        self.assertTrue(any(x.get("relance") for x in r.ligne["bras"]["C"]["recherches"]))

    def test_relance_toujours_nul_angle_mort(self):
        r, _ = lancer([PLAN, vue(0.04), lecture_vide(), self.RELANCE, lecture_vide()])
        self.assertEqual(r.bras_poste, "B")                       # règle de postage inchangée
        c = r.ligne["bras"]["C"]
        self.assertEqual(c["nature_etat_nul"], "angle_mort")
        self.assertEqual(c["relance"]["mots_apres"], 0)
        self.assertIn("blind spot", r.commentaire)

    def test_structure_absente_sans_relance(self):
        r, llm = lancer([PLAN, vue(0.04), lecture_vide(("contredit", "marqueur_non_rempli", "contredit", "contredit"))])
        self.assertEqual(len(llm.consignes), 3)                   # aucune relance payée pour rien
        self.assertEqual(r.ligne["bras"]["C"]["nature_etat_nul"], "structure_absente")
        self.assertIsNone(r.ligne["bras"]["C"]["relance"])
        self.assertIn("set aside on evidence", r.commentaire)

    def test_dynamique_observee(self):                            # 0.2.3
        lec = lecture_vide(("contredit",) * 4)
        lec["dynamique_observee"] = "Les deux gouvernements multiplient les déclarations sans acte, en attendant l'élection."
        r, _ = lancer([PLAN, vue(0.04), lec])
        d = r.ligne["bras"]["C"]["dynamique_observee"]
        self.assertIn("déclarations", d["texte"])
        self.assertEqual(d["cartes_nommees"], [])
        nom = ap.noms_cartes()["SEU"]
        lec["dynamique_observee"] = f"On approche d'un {nom.lower()}."
        r, _ = lancer([PLAN, vue(0.04), lec])
        self.assertEqual(r.ligne["bras"]["C"]["dynamique_observee"]["cartes_nommees"], ["SEU"])   # signalé, gardé
        r, _ = lancer([PLAN, vue(0.04), lecture_vide(("contredit",) * 4)])
        self.assertIsNone(r.ligne["bras"]["C"]["dynamique_observee"])                         # absente : rien

    def test_relance_desactivable(self):
        ancien, ap.RELANCE_ETAT_NUL = ap.RELANCE_ETAT_NUL, False
        try:
            r, llm = lancer([PLAN, vue(0.04), lecture_vide()])
            self.assertEqual(len(llm.consignes), 3)
            self.assertEqual(r.ligne["bras"]["C"]["nature_etat_nul"], "angle_mort")
        finally:
            ap.RELANCE_ETAT_NUL = ancien

    def test_etat_nul_suivi_a_part(self):
        import score_registre as sr
        reg = Path(tempfile.mkdtemp(prefix="registre-nuls-"))
        ancien, ap.REGISTRE = ap.REGISTRE, reg
        try:
            lancer([PLAN, vue(0.04), lecture_vide(("contredit",) * 4)], p_A=0.3)
            s = sr.scorer(reg, {"4242": 0})
            self.assertIsNone(s["apparie_ABC"])                   # pas d'équivalence C = B
            nul = s["etats_nuls"]["par_nature"]["structure_absente"]
            self.assertEqual(nul["n"], 1)
            self.assertAlmostEqual(nul["gain_B_sur_A"], 100 * math.log(0.96 / 0.7))
        finally:
            ap.REGISTRE = ancien

    # --- 0.3.0 : taux de base médian sur plusieurs vues, questions résolues comparables ---

    def test_vue_mediane(self):
        ancien, ap.NB_VUES = ap.NB_VUES, 3
        try:
            r, llm = lancer([PLAN, vue(0.30, "annuaire Alpha"), vue(0.02, "base Bravo"), {"frequence": None, "motif": "rien"},
                             lecture()])
            b = r.ligne["bras"]["B"]
            self.assertEqual(b["vues"]["valides"], 2)
            self.assertEqual(b["vues"]["frequences"], [0.02, 0.30])
            self.assertAlmostEqual(b["vues"]["dispersion"], 0.28)
            self.assertAlmostEqual(r.p_B, 0.02)                    # médiane basse : une vraie vue, aucun chiffre fabriqué
            r, _ = lancer([PLAN, vue(0.3, "annuaire Alpha"), vue(0.1, "base Bravo"), vue(0.2, "corpus Charlie"), lecture()])
            self.assertAlmostEqual(r.p_B, 0.2)                     # médiane de trois
            r, _ = lancer([PLAN, vue(0.3), vue(0.1), vue(0.2), lecture()])
            self.assertEqual(r.ligne["bras"]["B"]["vues"]["valides"], 1)   # 0.8.1 : même source → refusée
            r, _ = lancer([PLAN] + [{"frequence": None, "motif": "aucune base"}] * 3)
            self.assertEqual(r.ligne["bras"]["C"]["statut"], "sans_vue")
            self.assertEqual(r.ligne["bras"]["C"]["motif"], "aucune base")
        finally:
            ap.NB_VUES = ancien

    def test_historique_metaculus(self):
        vus = {}

        async def historique(cles, aujourdhui):
            vus["cles"] = cles
            return [{"titre": "Will X happen by 2025?", "issue": "yes", "resolue_le": "2025-06-01"},
                    {"titre": "Will X happen by 2025?", "issue": "yes", "resolue_le": "2025-06-01"},   # doublon
                    {"titre": "Will Y happen?", "issue": "annulled", "resolue_le": "2025-01-01"},      # pas oui/non
                    {"titre": "Will Z happen?", "issue": "no", "resolue_le": "2027-01-01"}]            # après la date
        plan = dict(PLAN, recherches_historique=["border clash", "ceasefire"])
        llm = LlmSimule([plan, vue(0.2), lecture()])
        r = asyncio.run(ap.prevoir_binaire(Q, "r", 0.3, "a", llm, chercher, True, MAINTENANT, historique=historique))
        self.assertEqual(vus["cles"], ["border clash", "ceasefire"])
        self.assertEqual(r.ligne["bras"]["B"]["historique"]["trouvees"], 1)
        self.assertIn("[M1] Will X happen by 2025? → YES", llm.consignes[1])
        self.assertNotIn("Will Z", llm.consignes[1])
        self.assertFalse(ap.fondement_memoire(dict(vue(), fondement="questions résolues [M1]", calcul="3/9", source="Metaculus")))

        async def panne(cles, aujourdhui):
            raise RuntimeError("API indisponible")
        r = asyncio.run(ap.prevoir_binaire(Q, "r", 0.3, "a", LlmSimule([plan, vue(0.2), lecture()]), chercher, True,
                                           MAINTENANT, historique=panne))
        self.assertIn("API indisponible", r.ligne["bras"]["B"]["historique"]["erreur"])
        self.assertEqual(r.bras_poste, "C")                         # une panne de l'historique ne bloque rien

    def test_recalibration_et_plafonnement_etudies(self):         # 0.3.0 : rapport seulement
        import random
        import score_registre as sr
        self.assertIsNone(sr.recalibration([(0.5, 1)] * 5))        # trop peu de questions : rien
        rnd = random.Random(1)
        paires = []
        for _ in range(200):                                       # prévisions trop tranchées : vrai p = 0,5 + (p-0,5)/2
            p = rnd.choice([0.05, 0.2, 0.8, 0.95])
            paires.append((p, int(rnd.random() < 0.5 + (p - 0.5) / 2)))
        r = sr.recalibration(paires)
        self.assertLess(r["a"], 1)                                 # détecte l'excès de confiance
        self.assertGreater(r["gain_hors_echantillon"], 0)
        lignes = [{"question_id": "1", "p_poste": 0.001}, {"question_id": "2", "p_poste": 0.5}]
        e = sr.plafonnement_etudie(lignes, {"1": 1, "2": 0})
        self.assertEqual(e["questions_touchees"], 1)
        self.assertGreater(e["gain_moyen"], 0)                     # 0,02 au lieu de 0,001 sur un OUI : gain

    # --- 0.4.0 ---

    CLASSE = {"classe_de_reference": "crises bilatérales à deux blocs (fictif)", "unite": "une rupture reconnue",
              "population": "40 crises", "periode": "2000-2025", "mise_a_l_echelle": "proportionnelle",
              "sources_visees": "[R1]"}

    def test_classe_figee_avant_comptage(self):
        anciens = ap.CLASSE_FIGEE, ap.NB_VUES
        ap.CLASSE_FIGEE, ap.NB_VUES = True, 2
        try:
            r, llm = lancer([PLAN, self.CLASSE, vue(0.2), vue(0.25), lecture()])
            self.assertIn("Étape 2a", llm.consignes[1])
            self.assertIn("CLASSE DE RÉFÉRENCE IMPOSÉE", llm.consignes[2])
            self.assertIn("crises bilatérales à deux blocs (fictif)", llm.consignes[3])   # même classe pour chaque vue
            self.assertEqual(r.ligne["bras"]["B"]["classe"]["unite"], "une rupture reconnue")
            r, llm = lancer([PLAN, "illisible", vue(0.2), vue(0.2), lecture()])           # classe ratée : vues libres
            self.assertIsNone(r.ligne["bras"]["B"]["classe"])
            self.assertNotIn("IMPOSÉE", llm.consignes[2])
        finally:
            ap.CLASSE_FIGEE, ap.NB_VUES = anciens

    def test_registre_mental_refuse(self):
        self.assertIn("mémoire", ap.controle_vue(dict(vue(), source="registre mental des présidents, sans consultation en ligne")))
        self.assertIn("mémoire", ap.controle_vue(dict(vue(), fondement="from memory")))
        self.assertIsNone(ap.controle_vue(dict(vue(), source="liste officielle des retraits de l'UE (registre nommé)")))

    def test_details_rejets(self):
        lec = lecture_vide(("contredit",) * 4)
        lec["rejets_classes"]["POL@7"]["fait_attendu"] = "un vote de défiance daté"
        lec["rejets_classes"]["POL@7"]["extrait_proche"] = "[3] débat parlementaire sans vote"
        r, _ = lancer([PLAN, vue(0.04), lec])
        d = r.ligne["bras"]["C"]["rejets_details"]
        self.assertEqual(d["POL@7"]["fait_attendu"], "un vote de défiance daté")
        self.assertNotIn("INC@7", d)                              # rien fourni : rien inscrit

    def test_test_sequentiel_et_puissance(self):               # 0.4.0
        import score_registre as sr
        self.assertAlmostEqual(sr.e_valeur([]), 1.0)
        self.assertLess(sr.e_valeur([0.0] * 50), 1.0001)            # aucun écart : aucune preuve
        self.assertGreater(sr.e_valeur([40.0] * 200), 20)           # écart constant et net : établi
        self.assertGreater(sr.e_valeur([10.0] * 150, sr.borne_gain_C_B()),
                           sr.e_valeur([10.0] * 150))                # 0.4.1 : borne structurelle C−B, plus puissant
        self.assertAlmostEqual(sr.borne_gain_C_B(), 100 * math.log(10))
        self.assertLess(sr.e_valeur([40.0, -40.0] * 100), 20)       # bruit symétrique : rien d'établi
        p = sr.puissance_a_priori([], simuler=False)
        self.assertEqual(p["origine"][:7], "supposé")
        self.assertGreater(p["test_classique"]["5 points"], p["test_classique"]["20 points"])
        self.assertEqual(sr.puissance_a_priori([10, -10, 10, -10, 10], simuler=False)["origine"], "observé")
        self.assertGreater(sr._questions_sequentiel(20, 40, sr.borne_gain_C_B(), essais=20),
                           p["test_classique"]["20 points"])           # le séquentiel en demande davantage

    def test_biais_C(self):                                   # 0.4.2
        import score_registre as sr
        apparies = [({"C": 0.2, "B": 0.1, "A": 0.1}, 0)] * 9 + [({"C": 0.2, "B": 0.1, "A": 0.1}, 1)]
        b = sr.biais_C(apparies)
        self.assertGreater(b["deplacement_logit_moyen"], 0)
        self.assertEqual(b["part_C_au_dessus_de_B"], 1.0)
        self.assertGreater(b["gain_sur_les_OUI"]["moyen"], 0)
        self.assertLess(b["gain_sur_les_NON"]["moyen"], 0)
        self.assertAlmostEqual(b["taux_de_OUI"], 0.1)
        self.assertGreater(b["C_moyen"], b["taux_de_OUI"])        # B juste, C au-dessus : biais à la hausse
        self.assertIsNone(sr.biais_C([]))

    def test_intervalle_et_verdict(self):                     # 0.5.1
        import random
        import score_registre as sr
        m = sr.borne_gain_C_B()
        rnd = random.Random(1)
        g = [rnd.gauss(15, 40) for _ in range(150)]
        lo, hi = sr.intervalle_sequentiel(g, m)
        self.assertLess(lo, sum(g) / len(g))
        self.assertGreater(hi, sum(g) / len(g))
        self.assertGreater(lo, 0)                                 # écart net et assez de questions : 0 exclu
        lo, hi = sr.intervalle_sequentiel([10.0] * 3, m)
        self.assertLess(lo, 0)                                    # trois questions : rien d'établi
        apparies = [({"C": 0.3, "B": 0.1, "A": 0.1}, 1)] * 3 + [({"C": 0.3, "B": 0.1, "A": 0.1}, 0)] * 3
        c = sr.comparer(apparies, "C", "B", m, principal=True)
        self.assertEqual(c["verdict"], "C indéterminé par rapport à B")
        self.assertEqual(c["test_sequentiel"]["seuil_mieux"], 20)
        self.assertEqual(sr.comparer(apparies, "C", "A")["test_sequentiel"]["seuil_mieux"], 60)   # secondaire

    def test_commentaire_scelle(self):                        # 0.5.1
        r, _ = lancer([PLAN, vue(0.2), lecture()])
        self.assertEqual(r.ligne["commentaire"], r.commentaire)
        x = dict(r.ligne)
        s = x.pop("sceau")
        self.assertEqual(s, ap.sceau(x))                          # le texte envoyé est couvert par le sceau

    def test_controle_attribution(self):                      # 0.5.2 (idée EnVrai)
        dossier = {"mots": [{"carte": "SEU", "strate": 7, "fait": "Le 3 novembre, 2 295 soldats sont déployés.",
                             "passage": [{"extrait": "toute concession serait une capitulation"},
                                         {"extrait": "2295 soldats déployés"}]},
                            {"carte": "POL", "strate": 7, "fait": "Un vote de défiance est déposé.",
                             "passage": [{"extrait": "motion déposée par l'opposition"}]}]}
        textes = ("[R1] Le ministre déclare que « toute concession serait une capitulation ». Le 3 novembre, 2295 soldats "
                  "déployés.")    # 0.9.4 : la date du fait doit figurer dans les résultats
        a = ap.controle_attribution(dossier, textes)
        self.assertTrue(a["detail"]["SEU@7"]["attribue"])            # extrait et nombre retrouvés
        self.assertFalse(a["detail"]["POL@7"]["attribue"])           # extrait introuvable
        self.assertEqual(a["non_attribues"], 1)
        dossier["mots"][0]["fait"] = "Le 3 novembre, 4 100 soldats sont déployés."
        self.assertEqual(ap.controle_attribution(dossier, textes)["detail"]["SEU@7"]["chiffres_absents"], ["4100"])
        # 0.8.0 (audit M-04) : un fait inventé, avec des extraits authentiques et des nombres présents AILLEURS
        dossier["mots"][0]["fait"] = "Trump a vendu 6,3 milliards d'actifs à un fonds souverain en octobre 2026."
        dossier["mots"][0]["passage"] = [{"extrait": "toute concession serait une capitulation"}]
        d0 = ap.controle_attribution(dossier, textes + " Forbes estime sa fortune à 6,3 milliards en 2026.")["detail"]["SEU@7"]
        self.assertFalse(d0["attribue"])
        self.assertEqual(sorted(d0["chiffres_hors_extraits"]), ["2026", "6.3"])
        self.assertEqual(ap._chiffres("10,4 Md$ ; 2,295 ; 6.30"), ["10.4", "2295", "6.3"])
        self.assertIsNone(ap.controle_attribution(None, textes))
        self.assertIsNone(ap.controle_attribution({"mots": []}, textes))
        r, _ = lancer([PLAN, vue(0.2), lecture()])                   # résultats simulés : extraits introuvables
        att = r.ligne["bras"]["C"]["attribution"]
        self.assertFalse(att["detail"]["POL@7"]["attribue"])         # ses extraits ne sont pas dans les résultats
        self.assertIsNone(att["detail"]["CTR@6"]["attribue"])        # sans extrait ni nombre : non vérifiable
        self.assertEqual(att["non_verifiables"], 1)
        self.assertEqual(r.bras_poste, "C")                          # diagnostic seulement : rien ne change

    def test_borne_depassee_retombe(self):                    # 0.4.1
        import score_registre as sr
        apparies = [({"C": 0.9, "B": 0.01, "A": 0.5}, 1)] * 3     # cote ×891 : borne C−B dépassée
        c = sr.comparer(apparies, "C", "B", sr.borne_gain_C_B())
        self.assertTrue(c["test_sequentiel"]["borne_depassee"])
        self.assertAlmostEqual(c["test_sequentiel"]["borne"], sr.borne_gain())

    def test_classe_statut_et_versions(self):                 # 0.4.1
        import score_registre as sr
        r, _ = lancer([PLAN, vue(0.2), lecture()])
        self.assertEqual(r.ligne["bras"]["B"]["classe_statut"], "desactivee")
        anciens = ap.CLASSE_FIGEE
        ap.CLASSE_FIGEE = True
        try:
            r, _ = lancer([PLAN, "illisible", vue(0.2), lecture()])
            self.assertEqual(r.ligne["bras"]["B"]["classe_statut"], "echec")
        finally:
            ap.CLASSE_FIGEE = anciens
        v = sr.statuts_par_version([r.ligne | {"_intacte": True}])
        self.assertEqual(v[ap.VERSION_BOT]["classe"], {"echec": 1})

    def test_stabilite_strate(self):                         # 0.4.0
        import score_registre as sr
        lignes = [{"question_id": "1", "bras": {"C": {"evenement": "SEUIL@13 apparait"}}},
                  {"question_id": "1", "bras": {"C": {"evenement": "SEUIL@7 apparait"}}},
                  {"question_id": "2", "bras": {"C": {"evenement": "SEUIL@6 apparait"}}},
                  {"question_id": "2", "bras": {"C": {"evenement": "SEUIL@6 apparait"}}},
                  {"question_id": "3", "bras": {"C": {"evenement": None}}}]
        s = sr.stabilite_strate(lignes)
        self.assertEqual(s["questions_repetees"], 2)
        self.assertAlmostEqual(s["accord"], 0.5)
        lignes[1]["version_bot"] = "0.4.1"                         # 0.4.1 : versions différentes, pas comparées
        self.assertEqual(sr.stabilite_strate(lignes)["questions_repetees"], 1)

    def test_bornes_api(self):                                    # B1
        self.assertEqual(ap.borner(0.0004), 0.001)
        self.assertEqual(ap.borner(0.9999), 0.999)
        self.assertEqual(ap.borner(0.004), 0.004)                 # n'est plus écrasé à 0,01
        r, _ = lancer([PLAN, vue(0.004), lecture_vide()])         # f_B < 0,01 : B posté tel quel
        self.assertEqual(r.bras_poste, "B")
        self.assertAlmostEqual(r.p_poste, 0.004)

    def test_une_ligne_par_question(self):                        # B4
        import score_registre as sr
        reg = Path(tempfile.mkdtemp(prefix="registre-dedup-"))
        ancien, ap.REGISTRE = ap.REGISTRE, reg
        try:
            lancer([dict(PLAN, evenement=None)], p_A=0.9)
            lancer([dict(PLAN, evenement=None)], p_A=0.2, maintenant=MAINTENANT.replace(hour=19))
            lancer([dict(PLAN, evenement=None)], p_A=0.7, publie=False, maintenant=MAINTENANT.replace(hour=20))
            lancer([dict(PLAN, evenement=None)], p_A=0.6, mode="test_questions", maintenant=MAINTENANT.replace(hour=21))
            s = sr.scorer(reg, {"4242": 0})
            self.assertEqual((s["lignes"], s["lignes_essai_exclues"], s["questions"]), (4, 2, 1))
            self.assertAlmostEqual(s["bras"]["A"]["log"], -math.log(0.8))            # la dernière publiée : 0,2
            s = sr.scorer(reg, {"4242": 0}, inclure_essais=True)
            self.assertAlmostEqual(s["bras"]["A"]["log"], -math.log(0.4))            # la dernière tout court : 0,6
            # 0.8.0 : « dernière » selon l'horodatage scellé, pas selon l'ordre du fichier
            f = reg / "journal-bot.jsonl"
            l_ = f.read_text(encoding="utf-8").splitlines()
            f.write_text("\n".join([l_[1], l_[0]] + l_[2:]) + "\n", encoding="utf-8")
            self.assertAlmostEqual(sr.scorer(reg, {"4242": 0})["bras"]["A"]["log"], -math.log(0.8))
        finally:
            ap.REGISTRE = ancien

    def test_publie_et_mode(self):                                # B5
        r, _ = lancer([PLAN, vue(0.2), lecture()], publie=False, mode="test_questions")
        self.assertIs(r.ligne["publie"], False)
        self.assertEqual(r.ligne["mode"], "test_questions")
        self.assertIn("dry run, not posted", r.commentaire)
        self.assertNotIn("Posted arm:", r.commentaire)

    def test_issues_sous_questions(self):                         # B2
        import score_registre as sr

        class Sq:
            def __init__(self, i, res):
                self.id_of_question, self.resolution_string = i, res

        class Client:
            def __init__(self):
                self.appels = []

            def get_question_by_url(self, url, group_question_mode=None):
                self.appels.append(group_question_mode)
                if "panne" in url:
                    raise RuntimeError("404")
                return [Sq(10, "no"), Sq(11, "yes")]

        c = Client()
        self.assertEqual(sr.question_metaculus(c, "11", "https://x/groupe").resolution_string, "yes")
        self.assertEqual(c.appels, ["unpack_subquestions"])
        self.assertIsNone(sr.question_metaculus(c, "12", "https://x/groupe"))

    def test_requetes_coupees_consignees(self):                   # B10
        reqs = [{"famille": "f", "cartes": ["POL@7"], "requete": f"r{i}"} for i in range(5)]
        out = asyncio.run(ap.executer_requetes(reqs, chercher, True, 3))
        self.assertEqual(len(out), 5)
        self.assertEqual([x.get("non_lancee") for x in out], [None, None, None, "plafond", "plafond"])
        self.assertFalse(any(x["executee"] for x in out[3:]))
        self.assertIn("non_cherchee", ap.CATEGORIES_REJET)

    def test_temporalite(self):                                   # B11
        self.assertEqual(ap.temporalite_de({}), "generique")
        self.assertEqual(ap.temporalite_de({"temporalite": "programmee"}), "programmee")
        self.assertEqual(ap.temporalite_de({"temporalite": "n'importe"}), "generique")
        r, _ = lancer([dict(PLAN, temporalite="programmee"), vue(0.2), lecture()])
        self.assertNotEqual(r.ligne["bras"]["C"]["statut"], "estime")   # sans référence propre : non estimé

    def test_vue_date_information(self):                          # B6
        self.assertIsNone(ap.controle_vue(vue(), "2026-11-03"))
        self.assertIn("postérieur", ap.controle_vue(dict(vue(), disponible_le="2027-01-01"), "2026-11-03"))
        self.assertIn("illisible", ap.controle_vue(dict(vue(), disponible_le="récent"), "2026-11-03"))
        self.assertFalse(ap.fondement_memoire(vue()))
        self.assertTrue(ap.fondement_memoire(dict(vue(), fondement="de mémoire", calcul="env. 20 %")))

    def test_regles_ancrage_f(self):                              # 0.9.6 / skill 0.7.53 §30
        r = ap.regles_dossier()
        self.assertIn("AU MOINS UN", r)
        self.assertIn("CONTREDIT ≠ MARQUEUR NON REMPLI", r)
        self.assertIn("INCOMPLET", r)
        self.assertIn("ALTERNATIVES", r)                            # 0.9.9 : un marqueur suffit pour f
        self.assertIn("ne dépend PAS de l'objet de la question", r)

    def test_vue_et_donnees_fixees(self):                         # 0.9.7 : banc sans texte (alphabet-chaine)
        llm = LlmSimule([PLAN, lecture()])
        appels = []

        async def ne_pas_chercher(req):
            appels.append(req)
            return ""
        c = asyncio.run(ap.alphabet(Q, "relevés", llm, ne_pas_chercher, True, "2026-11-03", 30,
                                    vue_fixee=vue(0.25, source="registre du banc"),
                                    donnees_fixees="[D1] relevé fictif daté (source : API fictive)"))
        self.assertEqual(appels, [])                                    # aucune recherche lancée
        self.assertEqual(len(llm.consignes), 2)                         # plan + lecture, ni vue ni relance
        self.assertIn("[D1] relevé fictif", llm.consignes[1])
        self.assertEqual(c["vues"], {"fixee": True})
        self.assertAlmostEqual(c["p_B"], 0.25)
        llm2 = LlmSimule([PLAN])
        c2 = asyncio.run(ap.alphabet(Q, "r", llm2, ne_pas_chercher, True, "2026-11-03", 30,
                                     vue_fixee={"frequence": 0.3}))
        self.assertEqual(c2["statut"], "sans_vue")                      # une vue fixée incomplète est refusée

    def test_equivalences_donnees_sous_reglage(self):           # 0.9.8 : banc seulement
        ancien = ap.EQUIV_DONNEES
        try:
            ap.EQUIV_DONNEES = False
            self.assertNotIn("données de jetons", ap.equivalences([6]))
            ap.EQUIV_DONNEES = True
            self.assertIn("données de jetons", ap.equivalences([6]))
            self.assertNotIn("données de jetons", ap.equivalences([7]))
        finally:
            ap.EQUIV_DONNEES = ancien

    def test_faits_futurs_retires(self):                          # 0.10.2
        self.assertEqual(ap.dates_citees("le 11 novembre 2026, puis November 3, 2026 et 2026-12-01T00:00Z"),
                         ["2026-12-01", "2026-11-11", "2026-11-03"])
        d = {"mots": [{"carte": "SEU", "strate": 6, "intensite": "f", "fait": "la réserve chute avant l'échéance du 2026-11-11T03:31Z"},
                      {"carte": "CTR", "strate": 6, "intensite": "f", "fait": "vote prévu le 5 décembre 2026"},
                      {"carte": "CRO", "strate": 6, "intensite": "f", "fait": "hausse relevée le 2026-11-09"}], "rejets": {}}
        r = ap.retirer_faits_futurs(d, "Le vote est prévu le 2026-12-05.", "2026-11-10", 1)
        self.assertEqual(r, ["SEU@6"])                                 # date future absente des résultats : inventée
        self.assertEqual([m["carte"] for m in d["mots"]], ["CTR", "CRO"])   # échéance annoncée dans les résultats : admise
        self.assertIn("fait daté après la date d'information", d["rejets"]["SEU@6"])

    def test_dossiers_horodates(self):                            # B8
        reg = Path(tempfile.mkdtemp(prefix="registre-dossiers-"))
        ancien, ap.REGISTRE = ap.REGISTRE, reg
        try:
            r1, _ = lancer([PLAN, vue(0.2), lecture()])
            r2, _ = lancer([PLAN, vue(0.2), lecture()], maintenant=MAINTENANT.replace(hour=21))
            self.assertNotEqual(r1.ligne["dossier_fichier"], r2.ligne["dossier_fichier"])
            self.assertEqual(len(list((reg / "dossiers").iterdir())), 2)
        finally:
            ap.REGISTRE = ancien

if __name__ == "__main__":
    unittest.main()
