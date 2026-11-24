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
from datetime import date, datetime, timedelta, timezone

from forecasting_tools import (
    ApiFilter,
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


def echelle_explicite(question) -> str:
    """Unité réécrite pour une seconde tentative : l'échelle exacte des bornes, et l'interdiction des pourcentages
    quand les bornes sont des fractions."""
    bas, haut = question.lower_bound, question.upper_bound
    unite = question.unit_of_measure or "same scale as the bounds"
    note = f"{unite} — answer on the SAME numeric scale as the bounds ({bas} to {haut})"
    if haut is not None and abs(haut) <= 1 and abs(bas or 0) <= 1:
        note += "; values are decimal fractions (e.g. 0.25), NOT percentages (not 25)"
    return note


def q_fin(question) -> str | None:
    fin = getattr(question, "scheduled_resolution_time", None) or getattr(question, "close_time", None)
    return fin.astimezone(timezone.utc).date().isoformat() if fin else None


class AlphabetBot(FallTemplateBot2026):
    """Bras A sur tout ; alphabet (bras B et C) sur les binaires."""

    def _genre_chercheur(self, r: object = "__principal__") -> tuple[str, object]:
        """0.2.0 (audit, B9) : UNE classification du chercheur, partagée par _recherche_reelle et _chercher.
        Rend (genre, chercheur) ; genre : asknews | smart_searcher | llm_web | memoire."""
        if r == "__principal__":
            r = self.get_llm("researcher")
        if isinstance(r, str) and r.startswith("asknews/"):
            return "asknews", r
        if isinstance(r, str) and r.startswith("smart-searcher"):
            return "smart_searcher", r
        if isinstance(r, str) and r and r not in ("None", "no_research"):
            import alphabet_modeles as am
            r = am.llm(r, temperature=0.1)                     # ex. « perplexity/sonar » donné en variable
        if isinstance(r, GeneralLlm):
            nom = GeneralLlm.to_model_name(r)
            # Un modèle « search » (gpt-4o-search-preview, perplexity/sonar…) interroge le web lui-même.
            return ("llm_web" if any(k in nom for k in ("perplexity", "sonar", "search")) else "memoire"), r
        return "memoire", None

    def _recherche_reelle(self) -> bool:
        return self._genre_chercheur()[0] != "memoire"

    def _second_chercheur(self) -> tuple[str, object] | None:
        """0.3.0 : une seconde source de recherche facultative (ALPHABET_CHERCHEUR_2), interrogée en plus de la
        première : plusieurs sources valent mieux qu'une, aucune n'étant meilleure seule. Ignorée si elle ne cherche
        pas vraiment sur le web."""
        r2 = os.environ.get("ALPHABET_CHERCHEUR_2")
        if not r2:
            return None
        g = self._genre_chercheur(r2)
        return g if g[0] != "memoire" else None

    def _chaine(self):
        """0.6.1 : chaîne de recherche du passage (Exa, seconde clé Exa, Tavily, GDELT)."""
        if getattr(self, "_chaine_", None) is None:
            import alphabet_recherche as ar_
            genre = self._genre_chercheur()
            exa = (lambda q: self._chercher_avec(genre, q)) if genre[0] == "smart_searcher" else None
            self._chaine_ = ar_.Chaine(exa)
        return self._chaine_

    async def run_research(self, question) -> str:
        """0.10.261 : toute recherche générale passe par alphabet_recherche.sans_foule (aucune cote ni prévision de
        foule n'arrive au modèle, quelle que soit la source)."""
        import alphabet_recherche as ar_
        import bras_m
        ar_.QUESTION_COURANTE.set(question.id_of_question or question.id_of_post or question.page_url)   # 0.10.277
        if getattr(self, "_disjoncte", False):
            raise RuntimeError("disjoncteur de recherche déclenché : question non traitée, reprise au prochain passage")
        try:
            texte, n = ar_.sans_foule(await self._run_research_brut(question))
        except Exception:
            # une recherche en échec compte pour le disjoncteur, puis l'erreur suit son cours (question non postée)
            self._n_recherches = getattr(self, "_n_recherches", 0) + 1
            self._n_vides = getattr(self, "_n_vides", 0) + 1
            if disjoncter(self._n_recherches, self._n_vides):
                self._disjoncte = True
            raise
        if n:
            print(f"Recherche : {n} phrase(s) citant une cote ou une prévision de foule retirée(s).")
        # 0.10.263 : disjoncteur (Khmelinskaya, Q6) : une panne générale de recherche n'est pas une information
        self._n_recherches = getattr(self, "_n_recherches", 0) + 1
        self._n_vides = getattr(self, "_n_vides", 0) + bras_m.recherche_vide(texte)
        if disjoncter(self._n_recherches, self._n_vides):
            self._disjoncte = True
            print(f"::warning::Disjoncteur de recherche : {self._n_vides} recherches vides sur {self._n_recherches} ; "
                  "plus aucune question n'est traitée dans ce passage (reprise au suivant).")
            raise RuntimeError("disjoncteur de recherche déclenché")
        import capture_recherche                 # 0.10.296 : capture en direct (ForecastGym) ; ne change rien au posté
        capture_recherche.capturer(question, texte)
        texte += await self._faits_demandes(question)
        return texte

    async def _faits_demandes(self, question) -> str:
        """0.10.510 (preenregistrements/dossier-interne.md, § 2) : la recherche reçoit seulement la question et les faits
        que nos mesures réclament (« a_chercher »), jamais une valeur interne."""
        if not isinstance(question, BinaryQuestion) or os.environ.get("ALPHABET_JUGE") == "0":
            return ""
        try:
            import dossier_interne as din
            auj = datetime.now(timezone.utc).date()
            fin = q_fin(question) or (auj + timedelta(days=90)).isoformat()
            D = await asyncio.to_thread(din.construire, question.question_text or "", fin, auj)
            R = din.pour_recherche(D)
            morceaux = []
            for a in R["a_chercher"][:3]:
                try:
                    morceaux.append(f"[{a['fait']}] " + await self._chercher(f"{a['consigne']} : {R['question']['titre']}"[:300]))
                except Exception as ex:
                    logger.warning("faits demandés : recherche échouée (%s)", type(ex).__name__)
            return ("\n\n--- FAITS DEMANDÉS PAR LES MESURES ---\n" + "\n\n".join(morceaux)) if morceaux else ""
        except Exception as ex:   # n'empêche jamais la recherche générale
            logger.warning("faits demandés : non construits (%s)", type(ex).__name__)
            return ""

    async def _run_research_brut(self, question) -> str:
        """Recherche générale du bras A (bot modèle). 0.6.1 : si Exa échoue, seconde clé Exa, puis Tavily, GDELT."""
        try:
            return await super().run_research(question)
        except Exception as e:
            ch = self._chaine()
            if ch._passer_seconde_cle():
                try:
                    return await super().run_research(question)
                except Exception:
                    pass
            secours = type(ch)(None, ch.env)
            return await secours.chercher(question.question_text[:300])

    async def _chercher(self, requete: str) -> str:
        """Une requête du plan : la chaîne de recherche (0.6.1), puis la seconde source si elle est configurée."""
        genre = self._genre_chercheur()
        if genre[0] == "smart_searcher":
            texte = await self._chaine().chercher(requete)
        else:
            texte = await self._chercher_avec(genre, requete)
        import alphabet_recherche as ar_
        texte = ar_.sans_foule(texte)[0]                     # 0.10.261 : aucune cote ni prévision de foule
        second = self._second_chercheur()
        if second is None:
            return texte
        try:
            texte2 = await self._chercher_avec(second, requete)
        except Exception as e:  # la seconde source n'est qu'un complément
            texte2 = f"(seconde source indisponible : {type(e).__name__})"
        return f"{texte}\n\n--- SECONDE SOURCE ---\n{ar_.sans_foule(texte2)[0]}"

    async def _historique(self, cles: list[str], aujourdhui: str) -> list[dict]:
        """0.3.0 : questions binaires RÉSOLUES de Metaculus, cherchées par mots-clés. Rend les issues seulement :
        ni prévision de la communauté ni score ne sont lus (§26)."""
        client, sortie = MetaculusClient(), []
        avant = datetime.fromisoformat(aujourdhui).replace(tzinfo=timezone.utc)
        for cle in cles:
            f = ApiFilter(allowed_types=["binary"], allowed_statuses=["resolved"], scheduled_resolve_time_lt=avant,
                          other_url_parameters={"search": cle})
            for q in (await client.get_questions_matching_filter(f))[:10]:
                fin = q.actual_resolution_time or q.scheduled_resolution_time
                sortie.append({"titre": q.question_text, "issue": q.resolution_string,
                               "resolue_le": fin.date().isoformat() if fin else None})
        return sortie

    async def _chercher_avec(self, chercheur: tuple[str, object], requete: str) -> str:
        genre, r = chercheur
        if genre == "asknews":
            return await AskNewsSearcher().call_preconfigured_version(r, requete)
        if genre == "smart_searcher":
            # 0.8.2 : le « moteur exa » est Exa PLUS le petit modèle qui rédige la synthèse. Passage 42489373511 :
            # 15 échecs comptés à Exa venaient du petit modèle saturé. Sur une saturation, on reprend la synthèse avec
            # les secours des rôles légers, sans toucher à Exa.
            import alphabet_modeles as am
            premier = r.removeprefix("smart-searcher/")
            secours = [m for m in (os.environ.get("ALPHABET_PETIT_SECOURS") or "").split(",") if m.strip() and m != premier]
            derniere = None
            for m in [premier] + secours:
                s = SmartSearcher(model=m, temperature=0, num_searches_to_run=1, num_sites_per_search=6,
                                  use_advanced_filters=False)
                try:
                    texte = await s.invoke(requete)
                except Exception as e:
                    if not am.PASSAGERE.search(f"{type(e).__name__}: {e}"):
                        raise
                    derniere = e
                    continue
                if m != premier:
                    BASCULES.append({"de": premier, "vers": m, "role": "synthese_recherche"})
                return texte
            raise derniere
        if genre == "llm_web":
            return await r.invoke(f"Find recent factual news (no forecasts, no market odds) about: {requete}")
        # Sans moteur de recherche : réponse du modèle de mémoire, consignée comme requête non exécutée.
        modele = r if isinstance(r, GeneralLlm) else self.get_llm("default", "llm")
        return await modele.invoke(f"From what you know, list dated facts about: {requete}")

    async def _explorer_autre(self, question, genre: str, rp: ReasonedPrediction, research: str):
        """0.9.1 (décision d'auteur du 2026-11-08) : l'alphabet lit aussi les questions non binaires, ramenées à une
        question binaire dérivée (médiane ou option la plus probable du bras A). Chiffre scellé, jamais posté."""
        if not ap.EXPLORATOIRE_AUTRES or genre not in ("numerique", "date", "choix_multiple"):
            return rp, None
        try:
            v = rp.prediction_value
            valeur = v.model_dump(mode="json") if hasattr(v, "model_dump") else v
            d = ap.question_derivee(genre, question.question_text, question.resolution_criteria or "", valeur,
                                    getattr(question, "unit_of_measure", "") or "")
            if d is None:
                return rp, {"statut": "sans_derivee"}
            fin = getattr(question, "scheduled_resolution_time", None) or getattr(question, "close_time", None)
            ex = await ap.explorer_derivee(
                d, str(question.id_of_question or question.id_of_post or question.page_url), question.page_url or "",
                question.background_info or "", question.fine_print or "", fin.astimezone(timezone.utc).date(),
                research, self._llm, self._chercher, self._recherche_reelle(),
                None if os.environ.get("ALPHABET_HISTORIQUE") == "0" else self._historique)
        except Exception as e:      # l'exploratoire ne doit jamais empêcher de répondre
            logger.exception("exploratoire : échec sur %s", question.page_url)
            return rp, {"statut": "erreur", "motif": f"{type(e).__name__}: {e}"[:300]}
        return ReasonedPrediction(prediction_value=rp.prediction_value,
                                  reasoning=(rp.reasoning or "") + ap.ligne_exploratoire_autre(ex)), ex

    def _journaliser_autre(self, question, genre: str, rp: ReasonedPrediction, exploratoire: dict | None = None,
                           extra: dict | None = None):
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
                     "publie": bool(self.publish_reports_to_metaculus), "mode": os.environ.get("ALPHABET_MODE"),
                     "modeles": ap.modeles_actifs(),
                     "raisonnement_sha256": hashlib.sha256((rp.reasoning or "").encode("utf-8")).hexdigest(),
                     **({"exploratoire": exploratoire} if exploratoire else {}), **(extra or {})}
            # 0.8.0 (audit m-13) : le commentaire envoyé est scellé, comme pour les binaires.
            ligne["commentaire"] = rp.reasoning or ""
            ligne = ap.sans_cles(ligne)          # 0.10.17 : aucune clé d'API dans le registre public
            ligne["sceau"] = ap.sceau(ligne)
            reg = ap.registre_ecrivable()
            with open(reg / "journal-autres.jsonl", "a", encoding="utf-8", newline="\n") as f:
                f.write(json.dumps(ligne, ensure_ascii=False, sort_keys=True, default=str) + "\n")
        except Exception as e:
            # 0.8.0 (audit M-10) : jamais de prévision postée sans sa ligne scellée. La question échoue ; elle sera
            # reprise au passage suivant (elle n'est pas marquée « déjà prévue »).
            logger.exception("registre : question %s non journalisée, non postée", getattr(question, "page_url", "?"))
            raise RuntimeError(f"registre non écrit : prévision non postée ({type(e).__name__})") from e
        return rp

    async def _run_forecast_on_numeric(self, question, research):
        try:
            rp = await super()._run_forecast_on_numeric(question, research)
        except Exception as e:
            if "far exceeding the bounds" not in str(e):
                raise
            # 0.1.4 (passage du 2026-11-04, question 45517) : réponse en pourcentages (5, 15, 40) pour une question bornée
            # entre 0,095 et 0,805. Une seconde tentative, avec l'échelle des bornes écrite dans l'unité, que le modèle
            # et le lecteur de la réponse voient tous deux.
            logger.warning("numérique : valeurs hors bornes sur %s, seconde tentative avec l'échelle explicite",
                           question.page_url)
            unite = question.unit_of_measure
            question.unit_of_measure = echelle_explicite(question)
            try:
                rp = await super()._run_forecast_on_numeric(question, research)
            finally:
                question.unit_of_measure = unite
        rp, ex = await self._explorer_autre(question, "numerique", rp, research)
        # 0.10.401 (décision d'auteur du 2026-11-20, 20 h 04) : fourchettes de prix du modèle log-normal pour les
        # clôtures d'actifs calibrés (preenregistrements/fourchettes-de-prix.md) ; distribution du bot scellée à côté.
        extra = {}
        try:
            import seuils_prix as spx
            from forecasting_tools import NumericDistribution, Percentile
            jour = datetime.now(timezone.utc).date().isoformat()
            fin = spx.echeance(question.question_text or "", jour)
            f = spx.fourchette(question.question_text or "", jour, fin)
            ombre_ind = None
            if f is None:   # 0.10.404 : indicateurs lents (séries FRED), prochaine publication
                import indicateurs_lents as ilx
                i_ = ilx.fourchette_publication(question.question_text or "")
                if i_ is not None and ilx.consensus_trouve(research or ""):
                    # 0.10.407 (décision de l'auteur du 2026-11-20, 22 h 01) : consensus des économistes dans la
                    # recherche → le bot garde sa réponse, le modèle est scellé en ombre
                    ombre_ind = {"indicateur_ombre": {"serie": i_["serie"], "percentiles": i_["percentiles"],
                                                      "derniere_valeur": i_["derniere_valeur"], "date": i_["date"]}}
                elif i_ is not None:
                    f = {"actif": f"indicateur {i_['serie']}", "dernier_prix": i_["derniere_valeur"], "date_prix": i_["date"],
                         "sigma_annuel": 0.0, "echeance": fin or q_fin(question), "percentiles": i_["percentiles"],
                         "mention": i_.get("mention")}
            if f is None:   # 0.10.403 : total CDC de la rougeole, comptes cumulés v1 (pari d'auteur)
                import comptes_cumules as ccx
                r_ = ccx.fourchette_rougeole(question.question_text or "", jour, fin or q_fin(question))
                if r_ is not None:
                    f = {"actif": "rougeole CDC", "dernier_prix": r_["dernier_total"], "date_prix": r_["date_total"],
                         "sigma_annuel": 0.0, "echeance": fin or q_fin(question), "percentiles": r_["percentiles"]}
            ombre = None
            if f is None:   # 0.10.406 : chiffre d'affaires trimestriel (Foster 1977), option 2 de l'auteur
                import resultats_entreprises as rex
                tk = rex.entreprise(question.question_text or "")
                m_ = rex.modele(tk, jour) if tk else None
                e_ = rex.echelle_numerique(m_, getattr(question, "lower_bound", None),
                                           getattr(question, "upper_bound", None)) if m_ else None
                if m_ and e_:
                    pc = rex.percentiles(m_, e_)
                    if rex.info_publiee(research or ""):
                        ombre = {"resultats_entreprise_ombre": {"ticker": tk, "percentiles": pc,
                                                                 "dernier_trimestre": m_["dernier_trimestre"]}}
                    else:
                        f = {"actif": f"revenu {tk}", "dernier_prix": m_["dernier_chiffre"], "date_prix": m_["dernier_trimestre"],
                             "sigma_annuel": 0.0, "echeance": fin or q_fin(question), "percentiles": pc,
                             "commentaire": rex.ligne_commentaire(m_)}
            if ombre or ombre_ind:
                extra = {**(ombre or {}), **(ombre_ind or {})}
            if f is not None:
                v = rp.prediction_value
                extra = {"prediction_brute": v.model_dump(mode="json") if hasattr(v, "model_dump") else str(v),
                         "fourchette_prix": {k: f[k] for k in ("actif", "dernier_prix", "date_prix", "sigma_annuel", "echeance")}}
                dist = NumericDistribution.from_question([Percentile(percentile=p, value=x) for p, x in f["percentiles"]], question)
                pct = ", ".join(f"P{int(p*100)} {x:,.2f}" for p, x in f["percentiles"])
                if f.get("commentaire"):
                    texte = f["commentaire"] + f" Percentiles: {pct}."
                elif str(f["actif"]).startswith("indicateur "):
                    texte = (f"\n\nSlow-indicator rule (coded): last published value {f['dernier_prix']:,.3f} ({f['date_prix']}), "
                             f"next release drawn from the 36 past release-to-release changes; percentiles: {pct}.")
                    if f.get("mention"):   # 0.10.405 : mention exigée par e-Stat
                        texte += f" Source: e-Stat (Statistics Bureau of Japan). {f['mention']}"
                elif f["actif"] == "rougeole CDC":
                    texte = (f"\n\nCumulative-count rule (coded): last CDC total {f['dernier_prix']:,.0f} as of {f['date_prix']}, "
                             f"future weekly increments drawn from the recent pace and its past variations (CDC forecast-hub "
                             f"baseline, adapted), horizon to {f['echeance']}; percentiles: {pct}.")
                else:
                    texte = (f"\n\nPrice-range rule (coded): last known close {f['dernier_prix']:,.2f} on {f['date_prix']}, 30-day "
                             f"annualised volatility {f['sigma_annuel']:.0%}, horizon to {f['echeance']}; driftless lognormal "
                             f"percentiles: {pct}.")
                rp = ReasonedPrediction(prediction_value=dist, reasoning=(rp.reasoning or "") + texte)
        except Exception as e:      # la fourchette qui échoue ne bloque rien : on garde celle du bot
            logger.warning("fourchette de prix : non appliquée (%s)", type(e).__name__)
            extra = {}
        return self._journaliser_autre(question, "numerique", rp, ex, extra)

    async def _run_forecast_on_multiple_choice(self, question, research):
        rp = await super()._run_forecast_on_multiple_choice(question, research)
        rp, ex = await self._explorer_autre(question, "choix_multiple", rp, research)
        # 0.10.396 (décision d'auteur du 2026-11-20, 16 h 18 : « un pari, un choix d'auteur ») : ancrage sur 1/N,
        # 85 % bot + 15 % répartition égale ; la répartition brute du bot reste scellée dans le journal
        # (preenregistrements/choix-multiple-ancre-uniforme.md, suivi par choix_multiple_ancre.py).
        brute, extra = rp, {}
        # 0.10.406 : tranches de chiffre d'affaires trimestriel (Foster 1977, option 2 de l'auteur) : le modèle remplace
        # le bot seulement sans prévision de l'entreprise ni consensus dans la recherche ; sinon il est scellé en ombre.
        try:
            import resultats_entreprises as rex
            tk = rex.entreprise(question.question_text or "")
            m_ = rex.modele(tk, datetime.now(timezone.utc).date().isoformat()) if tk else None
            v = rp.prediction_value
            valeur = v.model_dump(mode="json") if hasattr(v, "model_dump") else v
            r_ = rex.repartition(m_, [str(o["option_name"]) for o in valeur["predicted_options"]]) if m_ else None
            if r_ is not None:
                if rex.info_publiee(research or ""):
                    extra = {"resultats_entreprise_ombre": {"ticker": tk, "repartition": r_,
                                                            "dernier_trimestre": m_["dernier_trimestre"]}}
                else:
                    mel = type(v).model_validate({"predicted_options": [{"option_name": k, "probability": q} for k, q in r_.items()]})
                    rp = ReasonedPrediction(prediction_value=mel, reasoning=(rp.reasoning or "") + rex.ligne_commentaire(m_))
                    return self._journaliser_autre(question, "choix_multiple", rp, ex,
                                                   {"prediction_brute": valeur, "resultats_entreprise": tk})
        except Exception as e:
            logger.warning("tranches de chiffre d'affaires : non appliquées (%s)", type(e).__name__)
            extra = {}
        try:
            import choix_multiple_ancre as cma
            v = rp.prediction_value
            valeur = v.model_dump(mode="json") if hasattr(v, "model_dump") else v
            p = {str(o["option_name"]): float(o["probability"]) for o in valeur["predicted_options"]}
            m = cma.melange(p)
            mel = type(v).model_validate({"predicted_options": [{"option_name": k, "probability": q} for k, q in m.items()]})
            rp = ReasonedPrediction(prediction_value=mel, reasoning=(rp.reasoning or "") + cma.ligne_commentaire(len(p)))
            extra = {**extra, "prediction_brute": valeur, "ancrage_1_sur_n": cma.W}
        except Exception as e:      # l'ancrage qui échoue ne bloque rien : on poste la répartition du bot
            logger.warning("choix multiple : ancrage 1/N non appliqué (%s)", type(e).__name__)
            rp = brute
        return self._journaliser_autre(question, "choix_multiple", rp, ex, extra)

    async def _run_forecast_on_date(self, question, research):
        rp = await super()._run_forecast_on_date(question, research)
        rp, ex = await self._explorer_autre(question, "date", rp, research)
        return self._journaliser_autre(question, "date", rp, ex)

    async def _run_forecast_on_conditional(self, question, research):
        return self._journaliser_autre(question, "conditionnelle",
                                       await super()._run_forecast_on_conditional(question, research))

    async def _critique(self, consigne: str) -> str:
        """0.6.0 : le contradicteur (ALPHABET_CONTRADICTEUR), d'une autre famille que le lecteur ; en ombre."""
        import alphabet_modeles as am
        m = am.llm(os.environ["ALPHABET_CONTRADICTEUR"], temperature=0.1, timeout=180, allowed_tries=2)
        return await m.invoke(consigne)

    async def _llm(self, consigne: str) -> str:
        return await self.get_llm("default", "llm").invoke(consigne)

    async def _run_forecast_on_binary(self, question: BinaryQuestion, research: str) -> ReasonedPrediction[float]:
        import alphabet_recherche as ar_
        ar_.QUESTION_COURANTE.set(question.id_of_question or question.id_of_post or question.page_url)   # 0.10.277
        a = await super()._run_forecast_on_binary(question, research)  # bras A, avant toute carte
        # 0.10.5 (skill §35, Murphy 2026) : K − 1 essais de plus du modèle seul, en ombre, avant toute carte. Éteint
        # par défaut (ALPHABET_A_ESSAIS = 1) : chaque essai coûte un appel au modèle principal.
        essais_A: list[float] = []
        for _ in range(max(0, int(os.environ.get("ALPHABET_A_ESSAIS") or 1) - 1)):
            try:
                essais_A.append((await super()._run_forecast_on_binary(question, research)).prediction_value)
            except Exception as e:  # un essai en ombre qui échoue ne bloque rien
                logger.warning("alphabet : essai A en ombre échoué (%s)", type(e).__name__)
        # 0.10.34 : test de négation, en ombre, sur une part ALPHABET_NEGATION_TAUX des questions : la question est
        # réécrite en son contraire (petit modèle), puis posée au même modèle seul ; p + p_niée devrait valoir 1.
        negation = None
        qid_ = question.id_of_question or question.id_of_post or question.page_url
        if ap.tirage_negation(qid_):
            try:
                petit = self.get_llm("summarizer", "llm")
                n = ap.extraire_json(await petit.invoke(ap.consigne_negation(
                    question.question_text or "", question.resolution_criteria or "", question.fine_print or "")))
                qn = question.model_copy(update={"question_text": n["titre"], "resolution_criteria": n.get("criteres") or "",
                                                 "fine_print": n.get("precisions") or ""})
                p_n = (await super()._run_forecast_on_binary(qn, research)).prediction_value
                negation = dict(ap.coherence_negation(a.prediction_value, p_n), question_niee=str(n["titre"])[:300])
            except Exception as e:  # un test en ombre qui échoue ne bloque rien
                negation = {"statut": "erreur", "motif": f"{type(e).__name__}: {e}"[:200]}
        fin = question.scheduled_resolution_time or question.close_time
        q = ap.Question(id=question.id_of_question or question.id_of_post or question.page_url,
                        url=question.page_url or "", titre=question.question_text,
                        contexte=question.background_info or "", criteres=question.resolution_criteria or "",
                        precisions=question.fine_print or "",
                        resolution=fin.astimezone(timezone.utc).date())
        # 0.10.253 (décision d'auteur du 2026-11-18) : bras M, l'alphabet en matriochka ; posté selon bras_m.choisir_m.
        try:
            import bras_m
            matriochka = await bras_m.prevoir_m(self._llm, q.titre, q.criteres, q.contexte, q.resolution, research,
                                                datetime.now(timezone.utc).date())
        except Exception as e:  # M qui échoue ne bloque rien : on retombe sur la règle précédente
            matriochka = {"statut": "erreur", "motif": f"{type(e).__name__}: {e}"[:300]}
        try:
            r = await ap.prevoir_binaire(q, research, a.prediction_value, a.reasoning, self._llm, self._chercher,
                                         self._recherche_reelle(), publie=bool(self.publish_reports_to_metaculus),
                                         mode=os.environ.get("ALPHABET_MODE"),
                                         historique=None if os.environ.get("ALPHABET_HISTORIQUE") == "0"
                                         else self._historique,
                                         critique=self._critique if os.environ.get("ALPHABET_CONTRADICTEUR") else None,
                                         essais_A=essais_A or None, negation=negation, matriochka=matriochka)
        except Exception as e:
            # 0.8.0 (audit M-10) : les erreurs de l'alphabet sont déjà journalisées par prevoir_binaire (statut
            # « erreur », bras A posté). Une exception qui arrive ici veut dire que la ligne n'a PAS été écrite :
            # on ne poste pas une prévision hors registre. La question échoue et sera reprise au passage suivant.
            logger.exception("alphabet : ligne non écrite sur %s : prévision non postée", question.page_url)
            raise RuntimeError(f"registre non écrit : prévision non postée ({type(e).__name__}: {e})"[:300]) from e
        logger.info("alphabet : %s bras %s p=%.3f (A=%.3f B=%s C=%s)", question.page_url, r.bras_poste, r.p_poste,
                    r.p_A, r.p_B, r.p_C)
        # 0.10.399 (décision d'auteur du 2026-11-20, 19 h 34) : questions de seuil de prix, modèle log-normal calibré
        # (preenregistrements/seuils-de-prix-calibrage.md : −0,206 contre le taux de base sur 138 questions). La
        # prévision du pipeline reste scellée dans le journal ; le remplacement est scellé dans journal-seuils.jsonl.
        sp_ = self._seuil_de_prix(question, q, r.p_poste)
        # 0.10.494 (décision de l'auteur du 2026-11-24, 15 h 15) : événements comptés (violence entre deux gouvernements,
        # séismes de magnitude 6), mélange d'un quart en log-cote avec la prévision du bot, déplacement plafonné à 15
        # points ; calibrage sur 54 questions résolues (registre/calibrage-evenements.json). Scellé dans
        # journal-evenements.jsonl.
        if sp_ is None:
            sp_ = self._evenement_compte(question, q, r.p_poste)
        # 0.10.495 (décision de l'auteur du 2026-11-24, 15 h 30) : brique du maintien (mortalité SSA, risques Archigos,
        # saillance 3), même mélange et même plafond ; scellée dans journal-maintien.jsonl.
        if sp_ is None:
            sp_ = self._maintien(question, q, r.p_poste)
        # 0.10.497 (décision de l'auteur du 2026-11-24, 15 h 40) : échelle de l'escalade pour les questions de conflit
        # entre États (acte lourd ou léger), même mélange et même plafond ; scellée dans journal-escalade.jsonl.
        if sp_ is None:
            sp_ = self._escalade(question, q, r.p_poste)
        # 0.10.498 (décision de l'auteur du 2026-11-24, 15 h 51) : « un parmi N » avec saillance pour « X gagnera-t-il
        # <compétition> ? », confirmé une fois sur les questions de 2026 ; même mélange, même plafond ; journal-competitions.jsonl.
        if sp_ is None:
            sp_ = self._competition(question, q, r.p_poste)
        # 0.10.499 (décision de l'auteur du 2026-11-24, 15 h 59 : champ libre) : brique banque centrale, inertie de la Fed
        # (chaîne de Markov sur les réunions programmées depuis 1994, sources federalreserve.gov) ; passée une fois :
        # 0,469 contre 0,663 sur 47 questions, 0,575 contre 0,763 sur celles de 2026 ; même mélange, même plafond ;
        # journal-banque-centrale.jsonl.
        if sp_ is None:
            sp_ = self._banque_centrale(question, q, r.p_poste)
        # 0.10.500 (décision de l'auteur du 2026-11-24, 16 h 28 : découpage « matriochka ») : accords selon l'état de la
        # guerre (UCDP fin des conflits, table sourcée des guerres) ; seule la sous-famille « accord de paix pendant une
        # guerre en cours » a passé les critères (2 questions) ; même mélange, même plafond ; journal-accords.jsonl.
        if sp_ is None:
            sp_ = await self._accords_guerre(question, q, r.p_poste, research)
        # 0.10.509 (décisions de l'auteur du 2026-11-24, 21 h 14 à 21 h 24) : sondes de l'écosystème (relations, ponts,
        # phase), seulement sans brique, étalon recalé sur les 6 derniers mois, plafond 5 points, règle d'arrêt par
        # e-valeurs (preenregistrements/sondes-ecosysteme.md) ; journal-sondes.jsonl.
        if sp_ is None:
            sp_ = self._sondes(question, q, r.p_poste)
        # 0.10.408 (décision de l'auteur du 2026-11-20, 23 h 11) : cote Polymarket relevée EN OMBRE, après le calcul
        # de la prévision, scellée dans journal-cotes.jsonl ; elle ne touche jamais ce qui est posté.
        try:
            import cotes_ombre as cot
            await asyncio.to_thread(cot.relever, q.id, q.url, q.titre, q.resolution,
                                    sp_["p"] if sp_ is not None else r.p_poste, ap.VERSION_BOT)
        except Exception as e:     # l'ombre qui échoue ne bloque rien
            logger.warning("cotes en ombre : non relevées (%s)", type(e).__name__)
        # 0.10.510 (décision de l'auteur du 2026-11-24, 22 h 12 ; preenregistrements/dossier-interne.md) : la brique
        # sert de base (plus de mélange au quart) ; puis juge informé, après le sceau du bras A, dans une marge de 10
        # points au plus, modulée par la force de la preuve ; journal-juge.jsonl.
        texte = (r.commentaire or "") + (sp_["texte"] if sp_ is not None else "")
        p_mesure = float(sp_.get("p_regle", sp_["p"])) if sp_ is not None else r.p_poste
        j = await self._juge(question, q, research, a.prediction_value, p_mesure)
        if j is not None and j["decision"] == "ecart":
            texte += (f"\n\nInformed judge (bounded): departure for motive « {j['motif']} », capped at "
                      f"{j['marge']:.0%}: {p_mesure:.1%} -> {j['p_poste']:.1%}.")
            return ReasonedPrediction(prediction_value=j["p_poste"], reasoning=texte)
        return ReasonedPrediction(prediction_value=p_mesure, reasoning=texte)

    async def _juge(self, question, q, research: str, p_A: float, p_mesure: float) -> dict | None:
        """Juge informé : dossier interne standardisé, réponse fermée, bornée par le code ; journal scellé."""
        if os.environ.get("ALPHABET_JUGE") == "0":
            return None
        try:
            import dossier_interne as din
            import juge as jg
            etat = jg.etat()
            if etat.get("ferme"):
                return None
            auj = datetime.now(timezone.utc).date()
            fin = q_fin(question) or (auj + timedelta(days=90)).isoformat()
            D = await asyncio.to_thread(din.construire, question.question_text or "", fin, auj, str(q.id))
            criteres = (question.resolution_criteria or "") + "\n" + (question.fine_print or "")
            rep = await self._llm(jg.consigne(D, research, p_A, p_mesure, criteres))
            res = await asyncio.to_thread(jg.analyser, rep, D, research, p_mesure, criteres, auj)
            ligne = {"version_bot": ap.VERSION_BOT, "question_id": str(q.id), "url": q.url, "titre": q.titre,
                     "date_information": auj.isoformat(), "p_A": p_A, "p_mesure": p_mesure, "p_poste": res["p_poste"],
                     "juge": res, "reponse": (rep or "")[:4000], "dossier": D}
            ligne["sceau"] = ap.sceau(ligne)
            with open(ap.registre_ecrivable() / "journal-juge.jsonl", "a", encoding="utf-8", newline="\n") as f:
                f.write(json.dumps(ligne, ensure_ascii=False, sort_keys=True, default=str) + "\n")
            return res
        except Exception as ex:   # le juge qui échoue ne bloque rien : on poste la mesure
            logger.warning("juge informé : non appliqué (%s)", type(ex).__name__)
            return None

    def _sondes(self, question, q, p_pipeline: float) -> dict | None:
        try:
            import sondes as snd
            E = snd.etat()
            if not any(v.get("actif") and v.get("k") for v in (E.get("sondes") or {}).values()):
                return None
            if getattr(self, "_sondes_lecteur", None) is None:
                self._sondes_lecteur = snd.Sondes()
            auj = datetime.now(timezone.utc).date()
            fin = q_fin(question)
            horizon = max(1, (date.fromisoformat(fin) - auj).days) if fin else 90
            lecture = self._sondes_lecteur.lire(question.question_text or "", horizon, auj)
            res = snd.appliquer(p_pipeline, lecture, E)
            ligne = {"version_bot": ap.VERSION_BOT, "question_id": str(q.id), "url": q.url, "titre": q.titre,
                     "date_information": auj.isoformat(), "horizon": horizon, "p_base": p_pipeline, "p_poste": res["p"],
                     "sondes": res["parts"], "lecture": lecture, "etat_calcule_le": E.get("calcule_le")}
            ligne["sceau"] = ap.sceau(ligne)
            with open(ap.registre_ecrivable() / "journal-sondes.jsonl", "a", encoding="utf-8", newline="\n") as f:
                f.write(json.dumps(ligne, ensure_ascii=False, sort_keys=True, default=str) + "\n")
            if not res["parts"]:
                return None
            noms = ", ".join(f"{n} (k = {v['k']}, d = {v['d']})" for n, v in res["parts"].items())
            return {"p": res["p"], "p_regle": res["p"], "texte": (
                f"\n\nEcosystem probes (coded, capped): {noms}; calibration on the last 6 months of resolved questions; "
                f"shift from {p_pipeline:.1%} to {res['p']:.1%} (cap {max(v['plafond'] for v in res['parts'].values()):.0%}, "
                f"sequential stop rule).")}
        except Exception as ex:   # la sonde qui échoue ne bloque rien
            logger.warning("sondes : non appliquées (%s)", type(ex).__name__)
            return None

    async def _accords_guerre(self, question, q, p_pipeline: float, research: str = "") -> dict | None:
        try:
            import accords_guerre as agr
            import accords_regle as arr
            import guerres_releve as grl
            titre = question.question_text or ""
            # 0.10.501 : état de la guerre relevé automatiquement dans la recherche (faits datés et sourcés, jamais une
            # probabilité), pour toute question d'accord ; ajouté à registre/guerres-releves.csv avant la règle.
            if arr.classe(titre) in ("cessez_le_feu", "accord_paix", "tenue") and research:
                try:
                    auj = datetime.now(timezone.utc).date()
                    rep = await self._llm(grl.consigne(titre, auj.isoformat(), research))
                    grl.ecrire(grl.analyser(rep, research, auj, agr.guerre(titre, True)),
                               ap.registre_ecrivable() / "guerres-releves.csv")
                except Exception as ex:
                    logger.warning("relevé de l'état de la guerre : échec (%s)", type(ex).__name__)
            import accords_etats as aet
            # 0.10.502 : cessez-le-feu pendant une guerre (couche entre États COW depuis 1946, couche interne ETH/PRIO),
            # passé une fois : 0,553 contre 0,707 sur 17 questions, 0,840 contre 0,892 sur 2026 ; puis accord de paix.
            import accords_mid as amd
            # 0.10.503 : tenue des trêves (couche MID depuis 1946 pour les guerres entre États, ETH/PRIO sinon), passée
            # une fois : 0,719 contre 0,857 sur 7 questions, 0,985 contre 1,060 sur 2026.
            import rencontres_regle as rcr
            # 0.10.506 : rencontres au sommet (COLT, voyages des dirigeants 1990-2025) ; passé une fois : 0,151 contre
            # 0,312 sur 4 questions (toutes de 2026).
            import sommets_regle as smr
            # 0.10.507 : présence du président américain à un sommet de l'OTAN (liste officielle + COLT) ; passé une
            # fois : 0,020 contre 1,319 sur 2 questions (2026).
            import justice_regle as jsr
            # 0.10.508 : justice (Supreme Court Database 1946-2025 : victoire du demandeur 67 %, départs 0,39 par an) ;
            # passé une fois : 0,226 contre 0,815 sur 2 questions (2026).
            e = (aet.estimer(titre) or amd.estimer(titre) or agr.estimer(titre) or smr.estimer(titre)
                 or rcr.estimer(titre) or jsr.estimer(titre) or arr.estimer_autres(titre))
            if e is None:
                return None
            p = arr.melanger(p_pipeline, e["p"])
            e.update({"p_regle": e["p"], "p": p, "poids": arr.POIDS, "ecart_max": arr.ECART_MAX})
            jour = datetime.now(timezone.utc).date().isoformat()
            ligne = {"version_bot": ap.VERSION_BOT, "question_id": str(q.id), "url": q.url, "titre": q.titre,
                     "date_information": jour, "p_pipeline": p_pipeline, "p_poste": p, "accords": e}
            ligne["sceau"] = ap.sceau(ligne)
            with open(ap.registre_ecrivable() / "journal-accords.jsonl", "a", encoding="utf-8", newline="\n") as f:
                f.write(json.dumps(ligne, ensure_ascii=False, sort_keys=True, default=str) + "\n")
            quoi = {"cessez_le_feu": "ceasefire", "tenue": "truce breakdown or holding",
                    "autre": "agreement (base rate by number of consents required)",
                    "rencontre": "in-person summit meeting (COLT leader-travel frequency for this pair, 5 years)",
                    "justice": "US Supreme Court outcome (Supreme Court Database 1946-2025 base rates)"}.get(e["classe"], "peace agreement")
            e["texte"] = (f"\n\nWar-state rule (coded): {quoi} during an ongoing war ({e['guerre']}), measured rates "
                          f"by war type and age (COW interstate wars since 1946, ETH/PRIO civil-war ceasefires, UCDP "
                          f"conflict termination, MID interstate disputes since 1946): {e['p_regle']:.1%}. This coded rule is the measure (base, not blended).")
            return e
        except Exception as ex:   # la règle qui échoue ne bloque rien
            logger.warning("accords : non appliquée (%s)", type(ex).__name__)
            return None

    def _banque_centrale(self, question, q, p_pipeline: float) -> dict | None:
        try:
            import banque_centrale_regle as bcr
            e = bcr.estimer(question.question_text or "")
            if e is None:
                return None
            p = bcr.melanger(p_pipeline, e["p"])
            e.update({"p_regle": e["p"], "p": p, "poids": bcr.POIDS, "ecart_max": bcr.ECART_MAX})
            jour = datetime.now(timezone.utc).date().isoformat()
            ligne = {"version_bot": ap.VERSION_BOT, "question_id": str(q.id), "url": q.url, "titre": q.titre,
                     "date_information": jour, "p_pipeline": p_pipeline, "p_poste": p, "banque_centrale": e}
            ligne["sceau"] = ap.sceau(ligne)
            with open(ap.registre_ecrivable() / "journal-banque-centrale.jsonl", "a", encoding="utf-8", newline="\n") as f:
                f.write(json.dumps(ligne, ensure_ascii=False, sort_keys=True, default=str) + "\n")
            e["texte"] = (f"\n\nCentral-bank inertia rule (coded): Fed decisions at scheduled FOMC meetings since 1994 "
                          f"(federalreserve.gov), Markov chain on the direction and recency of the last move: "
                          f"{e['p_regle']:.1%}. This coded rule is the measure (base, not blended).")
            return e
        except Exception as ex:   # la règle qui échoue ne bloque rien
            logger.warning("banque centrale : non appliquée (%s)", type(ex).__name__)
            return None

    def _competition(self, question, q, p_pipeline: float) -> dict | None:
        try:
            import competitions_regle as cpr
            e = cpr.estimer(question.question_text or "", p_pipeline)
            if e is None:
                return None
            jour = datetime.now(timezone.utc).date().isoformat()
            ligne = {"version_bot": ap.VERSION_BOT, "question_id": str(q.id), "url": q.url, "titre": q.titre,
                     "date_information": jour, "p_pipeline": p_pipeline, "p_poste": e["p"], "competition": e}
            ligne["sceau"] = ap.sceau(ligne)
            with open(ap.registre_ecrivable() / "journal-competitions.jsonl", "a", encoding="utf-8", newline="\n") as f:
                f.write(json.dumps(ligne, ensure_ascii=False, sort_keys=True, default=str) + "\n")
            e["texte"] = (f"\n\nOne-among-N rule (coded): {e['n']} contenders under the competition's rules, salience "
                          f"factor {e['saillance']:g} (questions tend to be asked about favourites): {e['p_regle']:.1%}. "
                          f"This coded rule is the measure (base, not blended).")
            return e
        except Exception as ex:   # la règle qui échoue ne bloque rien
            logger.warning("compétition : non appliquée (%s)", type(ex).__name__)
            return None

    def _escalade(self, question, q, p_pipeline: float) -> dict | None:
        try:
            import escalade_regle as esc
            e = esc.estimer(question.question_text or "", p_pipeline)
            if e is None:
                return None
            jour = datetime.now(timezone.utc).date().isoformat()
            ligne = {"version_bot": ap.VERSION_BOT, "question_id": str(q.id), "url": q.url, "titre": q.titre,
                     "date_information": jour, "p_pipeline": p_pipeline, "p_poste": e["p"], "escalade": e}
            ligne["sceau"] = ap.sceau(ligne)
            with open(ap.registre_ecrivable() / "journal-escalade.jsonl", "a", encoding="utf-8", newline="\n") as f:
                f.write(json.dumps(ligne, ensure_ascii=False, sort_keys=True, default=str) + "\n")
            nom = "heavy act (invasion, blockade, war)" if e["classe"] == "lourd" else "light act (strike, attack, clash)"
            e["texte"] = (f"\n\nEscalation-ladder rule (coded): the question asks about a {nom}; resolved questions of "
                          f"this class resolved YES {e['p_regle']:.0%} of the time (shrunk). This coded rule is the measure (base, not blended).")
            return e
        except Exception as ex:   # la règle qui échoue ne bloque rien
            logger.warning("escalade : non appliquée (%s)", type(ex).__name__)
            return None

    def _maintien(self, question, q, p_pipeline: float) -> dict | None:
        try:
            import maintien_regle as mr
            jour = datetime.now(timezone.utc).date().isoformat()
            e = mr.estimer(question.question_text or "", jour, q.resolution.isoformat(), p_pipeline)
            if e is None:
                return None
            ligne = {"version_bot": ap.VERSION_BOT, "question_id": str(q.id), "url": q.url, "titre": q.titre,
                     "date_information": jour, "p_pipeline": p_pipeline, "p_poste": e["p"], "maintien": e}
            ligne["sceau"] = ap.sceau(ligne)
            with open(ap.registre_ecrivable() / "journal-maintien.jsonl", "a", encoding="utf-8", newline="\n") as f:
                f.write(json.dumps(ligne, ensure_ascii=False, sort_keys=True, default=str) + "\n")
            e["texte"] = (f"\n\nTenure rule (coded): age-based mortality (SSA 2023) and exit hazards by time in office "
                          f"(Archigos 4.1, 1990-2015), multiplied by {e['saillance']:g} because leaders whose exit is "
                          f"being asked about leave more often; chance of exit before the deadline {e['p_depart']:.1%}; "
                          f"measure for this question {e['p_regle']:.1%}. This coded rule is the measure (base, not blended).")
            return e
        except Exception as ex:   # la règle qui échoue ne bloque rien
            logger.warning("maintien : non appliqué (%s)", type(ex).__name__)
            return None

    def _evenement_compte(self, question, q, p_pipeline: float) -> dict | None:
        try:
            import evenements_regle as evr
            jour = datetime.now(timezone.utc).date().isoformat()
            e = evr.estimer(question.question_text or "", jour, q.resolution.isoformat(), p_pipeline)
            if e is None:
                return None
            ligne = {"version_bot": ap.VERSION_BOT, "question_id": str(q.id), "url": q.url, "titre": q.titre,
                     "date_information": jour, "p_pipeline": p_pipeline, "p_poste": e["p"], "evenement": e}
            ligne["sceau"] = ap.sceau(ligne)
            with open(ap.registre_ecrivable() / "journal-evenements.jsonl", "a", encoding="utf-8", newline="\n") as f:
                f.write(json.dumps(ligne, ensure_ascii=False, sort_keys=True, default=str) + "\n")
            src = "UCDP fatal events between the two governments" if e["serie"].startswith("ucdp") else "USGS M6+ earthquakes"
            e["texte"] = (f"\n\nCounted-event rule (coded): {src}, {e['k']} of the last {e['n']} "
                          f"{'months' if e['pas'] == 'mois' else 'days'} with an event; chance of at least one before the "
                          f"deadline {e['p_regle']:.1%}. This coded rule is the measure (base, not blended).")
            return e
        except Exception as ex:   # la règle qui échoue ne bloque rien
            logger.warning("événement compté : non appliqué (%s)", type(ex).__name__)
            return None

    def _seuil_de_prix(self, question, q, p_pipeline: float) -> dict | None:
        """Modèle de seuil de prix (seuils_prix.estimer) ; None si la question n'est pas reconnue, si les prix manquent,
        ou si l'écriture du journal échoue (on poste alors la prévision du pipeline)."""
        try:
            import seuils_prix as spx
            jour = datetime.now(timezone.utc).date().isoformat()
            fin = spx.echeance(question.question_text or "", jour) or q.resolution.isoformat()
            e = spx.estimer(question.question_text or "", jour, fin)
            if e is None:
                return None
            ligne = {"version_bot": ap.VERSION_BOT, "question_id": str(q.id), "url": q.url, "titre": q.titre,
                     "date_information": jour, "p_pipeline": p_pipeline, "p_poste": e["p"], "seuil": e}
            ligne["sceau"] = ap.sceau(ligne)
            with open(ap.registre_ecrivable() / "journal-seuils.jsonl", "a", encoding="utf-8", newline="\n") as f:
                f.write(json.dumps(ligne, ensure_ascii=False, sort_keys=True, default=str) + "\n")
            sens = "above" if e["au_dessus"] else "below"
            forme = ("at the stated date" if e["type"] == "date" else "at any time before the deadline")
            e["texte"] = (f"\n\nPrice-threshold rule (coded): last known price {e['dernier_prix']:,.2f} on {e['date_prix']}, "
                          f"30-day annualised volatility {e['sigma_annuel']:.0%}, threshold {e['k']:,.2f} ({sens}, {forme}), "
                          f"deadline {e['echeance']}; driftless lognormal model gives {e['p']:.1%}.")
            return e
        except Exception as ex:   # le modèle qui échoue ne bloque rien
            logger.warning("seuil de prix : non appliqué (%s)", type(ex).__name__)
            return None


BASCULES: list[dict] = []     # 0.7.4 : remplacements en cours de passage (journal du bilan)


class LlmTenace(GeneralLlm):
    """0.7.4 : un modèle saturé en cours de passage. D'abord on attend et on réessaie le MÊME modèle (`attentes`, en
    secondes) ; ensuite seulement, on passe aux modèles de `secours`. Le modèle principal n'a pas de secours : il est
    le codeur du passage, et une question n'est jamais lue par deux codeurs. Les rôles légers (lecture des réponses,
    résumés) en ont : changer de lecteur de format ne change pas la lecture."""

    def __init__(self, model: str, *, secours=(), attentes=(), **kwargs) -> None:
        import alphabet_modeles as am
        m_, k_ = am.adapter(model, kwargs)                # 0.10.101 : fournisseur (Azure Foundry, raisonnement)
        super().__init__(model=m_, **k_)
        self._secours, self._attentes, self._kw = list(secours), list(attentes), dict(kwargs)

    async def invoke(self, prompt, system_prompt: str | None = None) -> str:
        import alphabet_modeles as am
        try:
            return await super().invoke(prompt, system_prompt)
        except Exception as e:
            if not am.PASSAGERE.search(f"{type(e).__name__}: {e}"):
                raise
            derniere = e
        for s_ in self._attentes:
            await asyncio.sleep(s_)
            try:
                return await super().invoke(prompt, system_prompt)
            except Exception as e:
                if not am.PASSAGERE.search(f"{type(e).__name__}: {e}"):
                    raise
                derniere = e
        for m in self._secours:
            try:
                r = await am.llm(m, **self._kw).invoke(prompt, system_prompt)
            except Exception as e:
                derniere = e
                continue
            BASCULES.append({"de": self.model, "vers": m})
            logger.warning("modèle %s saturé : remplacé par %s pour cet appel", self.model, m)
            return r
        raise derniere


def configuration(env=os.environ) -> dict:
    """Modèles imposés par les variables du dépôt ; vide = défauts de forecasting-tools.

    ALPHABET_LLM         raisonnement, plan et dossier (ex. « anthropic/claude-sonnet-5-5 ») ;
    ALPHABET_PETIT_LLM   lecture des réponses et résumés (par défaut : ALPHABET_LLM) ;
    ALPHABET_CHERCHEUR   recherche (ex. « smart-searcher/anthropic/claude-haiku-5-5 » avec EXA_API_KEY,
                         ou « asknews/news-summaries » avec une clé AskNews).
    """
    llms = {}
    if env.get("ALPHABET_LLM"):
        # 0.8.0 (audit M-11) : pire cas d'un appel ramené de 11 min à ≈ 6 min (2 × 120 s + attentes 30 + 90 s).
        llms["default"] = LlmTenace(env["ALPHABET_LLM"], attentes=(30, 90), temperature=0.2, timeout=120,
                                    allowed_tries=2)
        petit = env.get("ALPHABET_PETIT_LLM") or env["ALPHABET_LLM"]
        secours = [m for m in (env.get("ALPHABET_PETIT_SECOURS") or "").split(",") if m.strip() and m != petit]
        for role in ("parser", "summarizer"):
            llms[role] = LlmTenace(petit, attentes=(20,), secours=secours, temperature=0.2, timeout=120,
                                   allowed_tries=2)
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
    r2 = env.get("ALPHABET_CHERCHEUR_2") or ""
    if r2.startswith("smart-searcher") and not env.get("EXA_API_KEY"):
        bloquants.append("ALPHABET_CHERCHEUR_2 utilise Exa (smart-searcher) mais le secret EXA_API_KEY est absent.")
    if r2.startswith("asknews/") and not (env.get("ASKNEWS_API_KEY")
                                         or (env.get("ASKNEWS_CLIENT_ID") and env.get("ASKNEWS_SECRET"))):
        bloquants.append("ALPHABET_CHERCHEUR_2 utilise AskNews mais aucune clé AskNews n'est présente.")
    if r2 and bot._second_chercheur() is None:
        avertissements.append(f"ALPHABET_CHERCHEUR_2 = « {r2} » ne cherche pas sur le web : ignoré.")
    if not bot._recherche_reelle():
        avertissements.append(f"chercheur « {nom} » : pas de vraie recherche web ; les requêtes de l'alphabet seront "
                              "marquées non exécutées et les lectures resteront Spéculatives.")
    return bloquants, avertissements


SEUIL_DISJONCTEUR, MIN_DISJONCTEUR = 0.3, 5


def disjoncter(n: int, vides: int) -> bool:
    """0.10.263 : au moins 5 recherches dans le passage, et plus de 30 % vides : panne, pas information."""
    return n >= MIN_DISJONCTEUR and vides / n > SEUIL_DISJONCTEUR


def en_pause(env=os.environ) -> bool:
    """0.10.263 : interrupteur général (variable du dépôt ALPHABET_PAUSE = « oui ») : aucun passage ne poste."""
    return str(env.get("ALPHABET_PAUSE", "")).strip().lower() in ("oui", "1", "true", "on")


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


def deja_envoyees_aujourdhui(jour: str | None = None) -> int:
    """Questions envoyées aux modèles aujourd'hui (UTC), tous passages confondus, d'après registre/passages.jsonl."""
    jour = jour or datetime.now(timezone.utc).date().isoformat()
    f = ap.REGISTRE / "passages.jsonl"
    if not f.is_file():
        return 0
    return sum(x.get("envoyees", 0) for x in map(json.loads, f.read_text(encoding="utf-8").splitlines())
               if x.get("date") == jour and x.get("statut", "lance") == "lance")   # 0.8.0 : « fin » ne recompte pas


def noter_passage(mode: str, declencheur: str, trouvees: int, lot: list, vus: list | None = None,
                  statut: str = "lance", detail: dict | None = None) -> None:
    """Une ligne par passage, écrite AVANT les prévisions : une question qui échoue compte quand même dans le budget."""
    reg = ap.registre_ecrivable()
    maintenant = datetime.now(timezone.utc)
    ligne = {"date": maintenant.date().isoformat(), "horodatage": maintenant.isoformat(timespec="seconds"),
             "mode": mode, "declencheur": declencheur, "trouvees": trouvees, "envoyees": len(lot),
             "modeles": ap.modeles_actifs(),
             "questions": [getattr(q, "page_url", None) for q in lot],
             # 0.5.1 : le jeu de questions REÇU, pas seulement celui traité : ce qui était visible à cette date.
             "trouvees_ids": sorted(str(getattr(q, "id_of_question", None) or getattr(q, "page_url", "")) for q in (vus or lot)),
             # 0.8.0 (audit M-14) : un passage arrêté (sans modèle, configuration) laisse sa trace ; « fin » ferme un
             # passage lancé avec les remplacements de modèles et l'usage des moteurs de recherche.
             "statut": statut, **({"detail": detail} if detail else {})}
    with open(reg / "passages.jsonl", "a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(ligne, ensure_ascii=False, sort_keys=True) + "\n")


def depense_depuis(depuis: str | None) -> float:
    """0.10.33 : somme des coûts estimés (registre/couts.jsonl) depuis une date (AAAA-MM-JJ) incluse."""
    f = ap.REGISTRE / "couts.jsonl"
    if not f.is_file():
        return 0.0
    tot = 0.0
    for brut in f.read_text(encoding="utf-8").splitlines():
        try:
            x = json.loads(brut)
        except json.JSONDecodeError:
            continue
        if not depuis or str(x.get("date", "")) >= depuis:
            tot += float(x.get("cout_usd") or 0)
    return tot


def noter_couts(mode: str, rapports: list, lot: list) -> float:
    """0.10.33 : une ligne par question traitée dans registre/couts.jsonl : coût estimé par litellm (modèles appelés
    par le bot ; les moteurs de recherche payants hors litellm ne sont pas comptés), durée, modèles. Les lignes scellées
    du journal ne sont pas touchées. Rend le total du passage."""
    reg = ap.registre_ecrivable()
    maintenant = datetime.now(timezone.utc)
    tot = 0.0
    with open(reg / "couts.jsonl", "a", encoding="utf-8", newline="\n") as f:
        for q, r in zip(lot, rapports):
            if isinstance(r, BaseException):
                continue
            c = float(getattr(r, "price_estimate", 0) or 0)
            tot += c
            f.write(json.dumps({"date": maintenant.date().isoformat(), "horodatage": maintenant.isoformat(timespec="seconds"),
                                "mode": mode, "question_id": str(getattr(q, "id_of_question", None) or ""),
                                "url": getattr(q, "page_url", None), "cout_usd": round(c, 4),
                                "minutes": round(float(getattr(r, "minutes_taken", 0) or 0), 2),
                                "modeles": ap.modeles_actifs(), "version_bot": ap.VERSION_BOT},
                               ensure_ascii=False, sort_keys=True) + "\n")
    return round(tot, 4)


def lignes_autres() -> list[dict]:
    f = ap.REGISTRE / "journal-autres.jsonl"
    if not f.is_file():
        return []
    return [json.loads(x) for x in f.read_text(encoding="utf-8").splitlines() if x.strip()]


def bilan(rapports: list, nouvelles: list[dict], publier: bool, autres: list[dict] | None = None) -> tuple[str, int]:
    """Bilan lisible du passage et code de sortie : 1 si des questions ont été trouvées mais rien n'a été prévu."""
    ok = [r for r in rapports if not isinstance(r, BaseException)]
    ko = [r for r in rapports if isinstance(r, BaseException)]
    bras = {b: sum(x.get("bras_poste") == b for x in nouvelles) for b in ("A", "B", "C", "AB", "M")}
    statuts, motifs = {}, {}
    for x in nouvelles:
        s = x["bras"]["C"].get("statut")
        statuts[s] = statuts.get(s, 0) + 1
        for cat in (x["bras"]["C"].get("rejets_classes") or {}).values():
            motifs[cat] = motifs.get(cat, 0) + 1
    texte = "\n".join([
        "=" * 70,
        "BILAN DU PASSAGE",
        f"  questions traitées : {len(rapports)}  (prévues : {len(ok)}, en échec : {len(ko)})",
        f"  {'postées sur Metaculus' if publier else 'NON postées (--sans-publier)'} : {len(ok)}",
        f"  questions binaires journalisées : {len(nouvelles)}  (bras M posté : {bras['M']}, bras C : {bras['C']}, bras B : {bras['B']}, bras A : {bras['A']})",
        f"  statuts de l'alphabet : {statuts or '—'}",
        f"  motifs de rejet des candidates : {motifs or '—'}",
        f"  autres questions journalisées (bras A seul) : {len(autres or [])}",
        *([f"  modèles légers remplacés en cours de passage (saturation) : {len(BASCULES)} appel(s), "
           + ", ".join(sorted({f"{b['de']} → {b['vers']}" for b in BASCULES}))] if BASCULES else []),
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
    if args.sans_publier and args.mode != "test_questions":
        # 0.5.1 : regarder les sorties du bot sur des questions OUVERTES du tournoi sans les poster, puis ajuster le bot,
        # est interdit par le règlement : le passage à blanc est réservé à la zone de test.
        print("❌  --sans-publier n'est admis qu'en mode test_questions (règlement : pas de prévisualisation sur les "
              "questions ouvertes du tournoi).")
        sys.exit(1)
    if en_pause():
        print("⏸  ALPHABET_PAUSE est à « oui » (variable du dépôt) : passage arrêté, rien n'est posté ni dépensé.")
        sys.exit(0)
    os.environ["ALPHABET_MODE"] = args.mode  # 0.2.0 (audit, B5/rec. 11) : chaque ligne du registre porte son mode
    check_environment(strict=True)  # jeton Metaculus et clé de modèle, sinon arrêt en rouge
    client = MetaculusClient()
    cibles = {"tournament": [client.CURRENT_AI_COMPETITION_ID, client.CURRENT_MINIBENCH_ID],
              "minibench": [client.CURRENT_MINIBENCH_ID],
              "test_questions": ["bot-testing-area"]}[args.mode]
    sauter_deja_prevues = args.mode != "test_questions"
    avant, avant_autres = len(lignes_registre()), len(lignes_autres())
    # 0.1.8 (budget) : passage planifié = plafond QUOTIDIEN (questions envoyées aujourd'hui, comptées dans
    # registre/passages.jsonl, avant toute prévision) ; passage manuel = plafond du passage (champ max_questions).
    # Un contrôle sans question nouvelle, ou après épuisement du plafond, ne coûte rien.
    # 0.6.0 : 0 (ou vide) = aucun plafond, toutes les questions ouvertes sont traitées.
    plafond = int(os.environ.get("ALPHABET_MAX_QUESTIONS") or 0)
    planifie = os.environ.get("GITHUB_EVENT_NAME") == "schedule"
    deja = deja_envoyees_aujourdhui() if planifie else 0
    reste = max(0, plafond - deja) if plafond > 0 else None
    questions = []
    for cible in cibles:
        ouvertes = client.get_all_open_questions_from_tournament(cible)
        if sauter_deja_prevues:
            ouvertes = [q for q in ouvertes if not q.already_forecasted]
        vus = {getattr(q, "id_of_question", None) or q.page_url for q in questions}
        questions += [q for q in ouvertes if (getattr(q, "id_of_question", None) or q.page_url) not in vus]
    if plafond <= 0:
        print(f"🔎  {len(questions)} question(s) nouvelle(s) ; aucun plafond")
        lot = list(questions)
    elif planifie:
        print(f"🔎  {len(questions)} question(s) nouvelle(s) ; plafond quotidien : {plafond}, déjà envoyées aujourd'hui : "
              f"{deja}, reste : {reste}")
        lot = questions[:reste]
    else:
        print(f"🔎  {len(questions)} question(s) nouvelle(s) ; plafond du passage : {plafond}")
        lot = questions[:plafond]
    if not lot:
        print(bilan([], [], not args.sans_publier, [])[0])
        sys.exit(0)
    # 0.10.33 : budget en dollars (ALPHABET_BUDGET_USD) depuis une date (ALPHABET_BUDGET_DEPUIS) : passage refusé s'il
    # est épuisé ; pendant le passage, plafond dur sur le reste (les appels déjà lancés se terminent).
    budget = float(os.environ.get("ALPHABET_BUDGET_USD") or 0)
    reste_budget = None
    if budget > 0:
        depuis = os.environ.get("ALPHABET_BUDGET_DEPUIS") or None
        depense = depense_depuis(depuis)
        reste_budget = round(budget - depense, 4)
        print(f"💶  Budget : {budget} $ depuis {depuis or 'le début'} ; dépensé {round(depense, 2)} $ ; reste {reste_budget} $")
        if reste_budget <= 0:
            print("❌  Budget épuisé : passage arrêté, rien n'est posté.")
            noter_passage(args.mode, "planifie" if planifie else "manuel", len(questions), [], questions,
                          statut="budget", detail={"budget_usd": budget, "depense_usd": round(depense, 4)})
            sys.exit(0)
    # 0.6.0 : les modèles ne sont sondés que s'il y a des questions ; le premier de chaque suite qui répond est gardé
    # pour tout le passage.
    import alphabet_modeles as am
    choix, essais = asyncio.run(am.choisir())
    for e_ in essais:
        print(f"{'✅' if e_['json_ok'] else '❌'}  {e_['role']} : {e_['modele']} ({e_['secondes']} s)"
              + (f" — {e_['erreur']}" if e_['erreur'] else ""))
    if not choix["principal"]:
        print("❌  Aucun modèle principal disponible (ALPHABET_LLM) : passage arrêté, rien n'est posté.")
        noter_passage(args.mode, "planifie" if planifie else "manuel", len(questions), [], questions,
                      statut="sans_modele", detail={"essais": [{k: e_.get(k) for k in ("role", "modele", "erreur")}
                                                                for e_ in essais if e_.get("role") == "principal"]})
        sys.exit(1)
    am.appliquer(choix)
    am.installer_traceur()                       # 0.10.100 : versions exactes servies, relevées pour le passage
    am.servis_et_vider()
    print(f"🧠  Modèles du passage : {os.environ['ALPHABET_MODELES']}")
    bot = construire(publier=not args.sans_publier)
    bot.skip_previously_forecasted_questions = sauter_deja_prevues
    bloquants, avertissements = problemes(bot)
    for a_ in avertissements:
        print(f"⚠️  {a_}")
    if bloquants:
        print("❌  Configuration :")
        for b_ in bloquants:
            print(f"    • {b_}")
        noter_passage(args.mode, "planifie" if planifie else "manuel", len(questions), [], questions,
                      statut="configuration", detail={"bloquants": bloquants})
        sys.exit(1)
    noter_passage(args.mode, "planifie" if planifie else "manuel", len(questions), lot, questions)
    if reste_budget is not None:
        from forecasting_tools import MonetaryCostManager

        async def _tout():
            with MonetaryCostManager(reste_budget):
                return await bot.forecast_questions(lot, return_exceptions=True)
        rapports = asyncio.run(_tout())
    else:
        rapports = asyncio.run(bot.forecast_questions(lot, return_exceptions=True))
    bot.log_report_summary(rapports, raise_errors=False)
    cout_passage = noter_couts(args.mode, rapports, lot)
    print(f"💶  Coût estimé du passage : {cout_passage} $")
    texte, code = bilan(rapports, lignes_registre()[avant:], not args.sans_publier, lignes_autres()[avant_autres:])
    print(texte)
    ch = getattr(bot, "_chaine_", None)
    noter_passage(args.mode, "planifie" if planifie else "manuel", len(questions), lot, questions, statut="fin",
                  detail={"prevues": sum(not isinstance(r, BaseException) for r in rapports),
                          "en_echec": sum(isinstance(r, BaseException) for r in rapports),
                          "bascules_modeles": BASCULES,
                          "recherche_usage": getattr(ch, "usage", None), "recherche_echecs": getattr(ch, "echecs", None),
                          "recherche_erreurs": getattr(ch, "erreurs", None), "cout_usd": cout_passage,
                          "modeles_servis": am.servis_et_vider()})
    sys.exit(code)
