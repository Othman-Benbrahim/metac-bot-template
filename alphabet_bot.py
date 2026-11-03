"""Bot Metaculus de l'alphabet situationnel.

À placer à la racine d'un fork de Metaculus/metac-bot-template, à côté de `main.py`, avec le dossier du skill
`alphabet-situationnel/`. Le bot hérite du bot modèle de Metaculus et ne remplace que les questions binaires :
  - binaires : bras A (modèle seul, le raisonnement du modèle Metaculus, scellé d'abord), puis l'alphabet (bras B et C) ;
    le bras C est posté s'il est estimé, sinon le bras A, signalé dans le commentaire ;
  - numériques, choix multiples, dates, conditionnelles : le bot modèle, inchangé (bras A).
Chaque question binaire laisse une ligne scellée dans registre/journal-bot.jsonl et son dossier dans registre/dossiers/.
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import os
from datetime import timezone

from forecasting_tools import (
    AskNewsSearcher,
    BinaryQuestion,
    GeneralLlm,
    MetaculusClient,
    ReasonedPrediction,
    SmartSearcher,
)

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


def construire(publier: bool) -> AlphabetBot:
    # Modèles : ceux de forecasting-tools par défaut ; ALPHABET_LLM et ALPHABET_CHERCHEUR les remplacent
    # (ex. ALPHABET_LLM="openrouter/<fournisseur>/<modèle>", ALPHABET_CHERCHEUR="asknews/news-summaries").
    llms = {}
    if os.environ.get("ALPHABET_LLM"):
        llms["default"] = GeneralLlm(model=os.environ["ALPHABET_LLM"], temperature=0.2, timeout=180, allowed_tries=2)
    if os.environ.get("ALPHABET_CHERCHEUR"):
        llms["researcher"] = os.environ["ALPHABET_CHERCHEUR"]
    return AlphabetBot(
        llms=llms or None,
        research_reports_per_question=1,
        predictions_per_research_report=1,  # une seule lecture par question : le pipeline est coûteux et scellé
        use_research_summary_to_forecast=False,
        publish_reports_to_metaculus=publier,
        folder_to_save_reports_to=None,
        skip_previously_forecasted_questions=True,
        extra_metadata_in_explanation=False,
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    p = argparse.ArgumentParser(description="Bot de l'alphabet situationnel")
    p.add_argument("--mode", choices=["tournament", "minibench", "test_questions"], default="test_questions")
    p.add_argument("--sans-publier", action="store_true", help="calculer et journaliser sans poster sur Metaculus")
    args = p.parse_args()
    bot = construire(publier=not args.sans_publier)
    client = MetaculusClient()
    cibles = {"tournament": [client.CURRENT_AI_COMPETITION_ID, client.CURRENT_MINIBENCH_ID],
              "minibench": [client.CURRENT_MINIBENCH_ID],
              "test_questions": ["bot-testing-area"]}[args.mode]
    if args.mode == "test_questions":
        bot.skip_previously_forecasted_questions = False
    rapports = []
    for cible in cibles:
        rapports += asyncio.run(bot.forecast_on_tournament(cible, return_exceptions=True))
    bot.log_report_summary(rapports)
