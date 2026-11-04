"""Bot Metaculus de l'alphabet situationnel.

À placer à la racine d'un fork de Metaculus/metac-bot-template, à côté de `main.py`, avec le dossier du skill
`alphabet-situationnel/`. Le bot hérite du bot modèle de Metaculus et ne remplace que les questions binaires :
  - binaires : bras A (modèle seul, le raisonnement du modèle Metaculus, scellé d'abord), puis l'alphabet (bras B et C) ;
    le bras C est posté s'il est estimé, le bras B si aucune carte n'est ancrée (état nul), sinon le bras A ;
  - numériques, choix multiples, dates, conditionnelles : le bot modèle, inchangé (bras A), journalisé et scellé dans
    registre/journal-autres.jsonl.
Chaque question binaire laisse une ligne scellée dans registre/journal-bot.jsonl et son dossier dans registre/dossiers/.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
import hashlib
from datetime import datetime, timezone

from forecasting_tools import (
    AskNewsSearcher,
    BinaryQuestion,
    GeneralLlm,
    MetaculusClient,
    ReasonedPrediction,
    SmartSearcher,
)

from bot_helpers import check_environment
from main import FallTemplateBot2026  # le bot modèle de Metaculus (fork de metac-bot-template)
import alphabet_pipeline as ap

logger = logging.getLogger(__name__)


class AlphabetBot(FallTemplateBot2026):
    """Bras A sur tout ; alphabet (bras B et C) sur les binaires."""

    def _recherche_reelle(self) -> bool:
        r = self.get_llm("researcher")
        nom = GeneralLlm.to_model_name(r) if isinstance(r, GeneralLlm) else str(r or "")
        # Un modèle « search » (gpt-4o-search-preview, perplexity/sonar…) interroge le web ; un modèle seul répond de mémoire.
        return any(k in nom for k in ("asknews/", "smart-searcher", "perplexity", "sonar", "search"))

    async def _chercher(self, requete: str) -> str:
        """Une requête du plan, par le même chercheur que la recherche générale du bot modèle."""
        r = self.get_llm("researcher")
        if isinstance(r, GeneralLlm):
            return await r.invoke(f"Find recent factual news (no forecasts, no market odds) about: {requete}")
        if isinstance(r, str) and r.startswith("asknews/"):
            return await AskNewsSearcher().call_preconfigured_version(r, requete)
        if isinstance(r, str) and r.startswith("smart-searcher"):
            s = SmartSearcher(model=r.removeprefix("smart-searcher/"), temperature=0, num_searches_to_run=1,
                              num_sites_per_search=6, use_advanced_filters=False)
            return await s.invoke(requete)
        # Sans moteur de recherche : réponse du modèle de mémoire, consignée comme requête non exécutée.
        return await self.get_llm("default", "llm").invoke(f"From what you know, list dated facts about: {requete}")

    def _journaliser_autre(self, question, genre: str, rp: ReasonedPrediction):
        """Questions hors alphabet (numériques, choix multiples, dates, conditionnelles) : bras A seul, journalisé et scellé
        dans registre/journal-autres.jsonl, pour garder l'historique complet du bot. Un échec d'écriture ne bloque rien."""
        try:
            v = rp.prediction_value
            valeur = v.model_dump(mode="json") if hasattr(v, "model_dump") else v
            fin = getattr(question, "scheduled_resolution_time", None) or getattr(question, "close_time", None)
            maintenant = datetime.now(timezone.utc)
            ligne = {"version_bot": ap.VERSION_BOT, "question_id": str(question.id_of_question or question.id_of_post
                                                                         or question.page_url),
                     "url": question.page_url or "", "titre": question.question_text, "type": genre,
                     "date_information": maintenant.date().isoformat(),
                     "horodatage": maintenant.isoformat(timespec="seconds"),
                     "resolution_prevue": fin.astimezone(timezone.utc).date().isoformat() if fin else None,
                     "bras_poste": "A", "prediction": valeur,
                     "raisonnement_sha256": hashlib.sha256((rp.reasoning or "").encode("utf-8")).hexdigest()}
            ligne["sceau"] = ap.sceau(ligne)
            ap.REGISTRE.mkdir(parents=True, exist_ok=True)
            with open(ap.REGISTRE / "journal-autres.jsonl", "a", encoding="utf-8", newline="\n") as f:
                f.write(json.dumps(ligne, ensure_ascii=False, sort_keys=True, default=str) + "\n")
        except Exception:
            logger.exception("registre : question %s non journalisée", getattr(question, "page_url", "?"))
        return rp

    async def _run_forecast_on_numeric(self, question, research):
        return self._journaliser_autre(question, "numerique", await super()._run_forecast_on_numeric(question, research))

    async def _run_forecast_on_multiple_choice(self, question, research):
        return self._journaliser_autre(question, "choix_multiple",
                                       await super()._run_forecast_on_multiple_choice(question, research))

    async def _run_forecast_on_date(self, question, research):
        return self._journaliser_autre(question, "date", await super()._run_forecast_on_date(question, research))

    async def _run_forecast_on_conditional(self, question, research):
        return self._journaliser_autre(question, "conditionnelle",
                                       await super()._run_forecast_on_conditional(question, research))

    async def _llm(self, consigne: str) -> str:
        return await self.get_llm("default", "llm").invoke(consigne)

    async def _run_forecast_on_binary(self, question: BinaryQuestion, research: str) -> ReasonedPrediction[float]:
        a = await super()._run_forecast_on_binary(question, research)  # bras A, avant toute carte
        fin = question.scheduled_resolution_time or question.close_time
        q = ap.Question(id=question.id_of_question or question.id_of_post or question.page_url,
                        url=question.page_url or "", titre=question.question_text,
                        contexte=question.background_info or "", criteres=question.resolution_criteria or "",
                        precisions=question.fine_print or "",
                        resolution=fin.astimezone(timezone.utc).date())
        try:
            r = await ap.prevoir_binaire(q, research, a.prediction_value, a.reasoning, self._llm, self._chercher,
                                         self._recherche_reelle())
        except Exception as e:  # l'alphabet ne doit jamais empêcher de répondre : bras A, signalé
            logger.exception("alphabet : échec sur %s", question.page_url)
            return ReasonedPrediction(prediction_value=a.prediction_value,
                                      reasoning=f"Situational-alphabet bot. Posted arm: A, model alone "
                                                f"(alphabet failed: {type(e).__name__}).\n\n{a.reasoning}")
        logger.info("alphabet : %s bras %s p=%.3f (A=%.3f B=%s C=%s)", question.page_url, r.bras_poste, r.p_poste,
                    r.p_A, r.p_B, r.p_C)
        return ReasonedPrediction(prediction_value=r.p_poste, reasoning=r.commentaire)


def configuration(env=os.environ) -> dict:
    """Modèles imposés par les variables du dépôt ; vide = défauts de forecasting-tools.

    ALPHABET_LLM         raisonnement, plan et dossier (ex. « anthropic/claude-sonnet-5-5 ») ;
    ALPHABET_PETIT_LLM   lecture des réponses et résumés (par défaut : ALPHABET_LLM) ;
    ALPHABET_CHERCHEUR   recherche (ex. « smart-searcher/anthropic/claude-haiku-5-5 » avec EXA_API_KEY,
                         ou « asknews/news-summaries » avec une clé AskNews).
    """
    llms = {}
    if env.get("ALPHABET_LLM"):
        llms["default"] = GeneralLlm(model=env["ALPHABET_LLM"], temperature=0.2, timeout=180, allowed_tries=2)
        petit = env.get("ALPHABET_PETIT_LLM") or env["ALPHABET_LLM"]
        for role in ("parser", "summarizer"):
            llms[role] = GeneralLlm(model=petit, temperature=0.2, timeout=120, allowed_tries=2)
    if env.get("ALPHABET_CHERCHEUR"):
        llms["researcher"] = env["ALPHABET_CHERCHEUR"]
    return llms


def problemes(bot: AlphabetBot, env=os.environ) -> tuple[list[str], list[str]]:
    """(bloquants, avertissements) avant de lancer : un passage qui ne peut rien poster doit échouer en rouge."""
    bloquants, avertissements = [], []
    for role in ("default", "parser", "summarizer", "researcher"):
        m = bot.get_llm(role)
        nom = GeneralLlm.to_model_name(m) if isinstance(m, GeneralLlm) else str(m or "")
        if nom.startswith("metaculus/"):
            bloquants.append(f"modèle « {role} » = {nom} : le proxy de Metaculus n'existe plus. "
                             "Renseigner ALPHABET_LLM (et ALPHABET_CHERCHEUR pour la recherche).")
    cherche = bot.get_llm("researcher")
    nom = GeneralLlm.to_model_name(cherche) if isinstance(cherche, GeneralLlm) else str(cherche or "")
    if nom.startswith("smart-searcher") and not env.get("EXA_API_KEY"):
        bloquants.append("ALPHABET_CHERCHEUR utilise Exa (smart-searcher) mais le secret EXA_API_KEY est absent.")
    if nom.startswith("asknews/") and not (env.get("ASKNEWS_API_KEY")
                                          or (env.get("ASKNEWS_CLIENT_ID") and env.get("ASKNEWS_SECRET"))):
        bloquants.append("ALPHABET_CHERCHEUR utilise AskNews mais aucune clé AskNews n'est présente.")
    if not bot._recherche_reelle():
        avertissements.append(f"chercheur « {nom} » : pas de vraie recherche web ; les requêtes de l'alphabet seront "
                              "marquées non exécutées et les lectures resteront Spéculatives.")
    return bloquants, avertissements


def construire(publier: bool) -> AlphabetBot:
    return AlphabetBot(
        llms=configuration() or None,
        research_reports_per_question=1,
        predictions_per_research_report=1,  # une seule lecture par question : le pipeline est coûteux et scellé
        use_research_summary_to_forecast=False,
        publish_reports_to_metaculus=publier,
        folder_to_save_reports_to=None,
        skip_previously_forecasted_questions=True,
        extra_metadata_in_explanation=False,
    )


def lignes_registre() -> list[dict]:
    f = ap.REGISTRE / "journal-bot.jsonl"
    if not f.is_file():
        return []
    return [json.loads(x) for x in f.read_text(encoding="utf-8").splitlines() if x.strip()]


def lignes_autres() -> list[dict]:
    f = ap.REGISTRE / "journal-autres.jsonl"
    if not f.is_file():
        return []
    return [json.loads(x) for x in f.read_text(encoding="utf-8").splitlines() if x.strip()]


def bilan(rapports: list, nouvelles: list[dict], publier: bool, autres: list[dict] | None = None) -> tuple[str, int]:
    """Bilan lisible du passage et code de sortie : 1 si des questions ont été trouvées mais rien n'a été prévu."""
    ok = [r for r in rapports if not isinstance(r, BaseException)]
    ko = [r for r in rapports if isinstance(r, BaseException)]
    bras = {b: sum(x.get("bras_poste") == b for x in nouvelles) for b in "ABC"}
    statuts = {}
    for x in nouvelles:
        s = x["bras"]["C"].get("statut")
        statuts[s] = statuts.get(s, 0) + 1
    texte = "\n".join([
        "=" * 70,
        "BILAN DU PASSAGE",
        f"  questions traitées : {len(rapports)}  (prévues : {len(ok)}, en échec : {len(ko)})",
        f"  {'postées sur Metaculus' if publier else 'NON postées (--sans-publier)'} : {len(ok)}",
        f"  questions binaires journalisées : {len(nouvelles)}  (bras C posté : {bras['C']}, bras B : {bras['B']}, bras A : {bras['A']})",
        f"  statuts de l'alphabet : {statuts or '—'}",
        f"  autres questions journalisées (bras A seul) : {len(autres or [])}",
        *[f"  échec : {type(e).__name__} : {str(e)[:300]}" for e in ko[:10]],
        "  aucune question ouverte trouvée : rien à faire pour l'instant." if not rapports else "",
        "=" * 70])
    return texte, (1 if rapports and not ok else 0)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    p = argparse.ArgumentParser(description="Bot de l'alphabet situationnel")
    p.add_argument("--mode", choices=["tournament", "minibench", "test_questions"], default="test_questions")
    p.add_argument("--sans-publier", action="store_true", help="calculer et journaliser sans poster sur Metaculus")
    args = p.parse_args()
    check_environment(strict=True)  # jeton Metaculus et clé de modèle, sinon arrêt en rouge
    bot = construire(publier=not args.sans_publier)
    bloquants, avertissements = problemes(bot)
    for a_ in avertissements:
        print(f"⚠️  {a_}")
    if bloquants:
        print("❌  Configuration :")
        for b_ in bloquants:
            print(f"    • {b_}")
        sys.exit(1)
    client = MetaculusClient()
    cibles = {"tournament": [client.CURRENT_AI_COMPETITION_ID, client.CURRENT_MINIBENCH_ID],
              "minibench": [client.CURRENT_MINIBENCH_ID],
              "test_questions": ["bot-testing-area"]}[args.mode]
    if args.mode == "test_questions":
        bot.skip_previously_forecasted_questions = False
    avant, avant_autres = len(lignes_registre()), len(lignes_autres())
    rapports = []
    for cible in cibles:
        rapports += asyncio.run(bot.forecast_on_tournament(cible, return_exceptions=True))
    bot.log_report_summary(rapports, raise_errors=False)
    texte, code = bilan(rapports, lignes_registre()[avant:], not args.sans_publier, lignes_autres()[avant_autres:])
    print(texte)
    sys.exit(code)
