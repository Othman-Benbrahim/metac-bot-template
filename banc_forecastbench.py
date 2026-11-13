"""Banc ForecastBench (bot 0.10.43 ; décision d'auteur du 2026-11-11) : jouer B et C sur des questions ForecastBench
DÉJÀ résolues, à leur date d'information, pour avoir vite assez d'issues (biais de C, λ appris, C contre B).

Source : forecastingresearch/forecastbench-datasets (Forecasting Research Institute ; CC BY-SA 4.0). Toutes les deux
semaines, un jeu de 500 questions (date D) ; le jeu de résolutions du même D les résout à plusieurs horizons, le premier
à D + 7 jours.

Garde-fous contre la fuite (§26), les mêmes que les tests rétrospectifs, plus deux :
  - seules les questions tirées de SÉRIES (fred, dbnomics, yfinance, acled, wikipedia) sont jouées : les questions de
    marchés (Metaculus, Manifold, Polymarket, Kalshi) portent la cote de la foule au gel, interdite avant scellement ;
  - jeux postérieurs à la date de connaissance du modèle (--apres) ; recherche Exa bornée à D (pages datées seulement) ;
  - sonde : si le modèle dit connaître l'issue et a raison, la question est exclue ;
  - la dernière valeur de la série au gel (`freeze_datetime_value`) est donnée : c'est un fait daté, pas une prévision.
Les lignes vont dans registre/retro.jsonl (type « retro », banc « forecastbench ») : le score des tests rétrospectifs
(biais de C, correction, C contre B) les compte avec les autres. Rien n'est posté.

    uv run python banc_forecastbench.py --n 20 [--jeu 2026-10-25] [--sources fred,dbnomics,yfinance,acled,wikipedia]
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import random
import sys
from datetime import date, datetime, timedelta, timezone

import math

import httpx

import alphabet_pipeline as ap
import alphabet_retro as ar

DEPOT = "https://raw.githubusercontent.com/forecastingresearch/forecastbench-datasets/main/datasets"
SOURCES_SERIES = ("fred", "dbnomics", "yfinance", "acled", "wikipedia")
MARCHES = ("metaculus", "manifold", "polymarket", "kalshi", "infer")


async def _json(url: str) -> dict:
    async with httpx.AsyncClient(timeout=60, follow_redirects=True) as c:
        r = await c.get(url)
        r.raise_for_status()
        return r.json()


def jeux_candidats(aujourdhui: date, apres: date, n_max: int = 12) -> list[str]:
    """Les dates D (tous les 14 jours, ancrées sur 2026-10-25) dont la première résolution (D + 7) est passée."""
    d, out = date(2026, 10, 25), []
    while d + timedelta(days=14) + timedelta(days=7) <= aujourdhui:
        d += timedelta(days=14)
    while d > apres and len(out) < n_max:
        if d + timedelta(days=7) <= aujourdhui:
            out.append(d.isoformat())
        d -= timedelta(days=14)
    return out


def apparier(questions: dict, resolutions: dict, sources=SOURCES_SERIES) -> list[dict]:
    """Une entrée par question de série résolue (0 ou 1), à son PREMIER horizon résolu. Les questions combinées
    (identifiant en liste) et toutes les questions de marché sont écartées."""
    qs = {(q["source"], q["id"]): q for q in questions.get("questions", [])
          if q.get("source") in sources and isinstance(q.get("id"), str)}
    garde: dict = {}
    for r in resolutions.get("resolutions", []):
        if not isinstance(r.get("id"), str):
            continue
        cle = (r.get("source"), r.get("id"))
        if cle not in qs or not r.get("resolved") or r.get("resolved_to") not in (0, 1, 0.0, 1.0):
            continue
        if cle not in garde or r["resolution_date"] < garde[cle]["resolution_date"]:
            garde[cle] = r
    out = []
    for cle, r in garde.items():
        q = qs[cle]
        out.append({"question": q, "resolution_date": r["resolution_date"], "issue": int(r["resolved_to"])})
    return sorted(out, key=lambda x: (x["question"]["source"], x["question"]["id"]))


def construire(item: dict, jeu: str) -> dict:
    q, rd = item["question"], item["resolution_date"]
    sub = lambda s: str(s or "").replace("{forecast_due_date}", jeu).replace("{resolution_date}", rd)
    contexte = sub(q.get("background"))
    if q.get("freeze_datetime_value") not in (None, "", "N/A") and q.get("source") in SOURCES_SERIES:
        contexte += (f"\n\nDernière valeur connue au {str(q.get('freeze_datetime', ''))[:10]} : "
                     f"{q['freeze_datetime_value']} ({q.get('freeze_datetime_value_explanation', '')}).")
    return {"qid": f"fb:{jeu}:{q['source']}:{q['id']}:{rd}", "titre": sub(q["question"]), "contexte": contexte,
            "criteres": sub(q.get("resolution_criteria")), "url": q.get("url") or "", "resolution": rd,
            "source": q["source"], "issue": item["issue"], "_q": q}


# --------------------------------------------------------------------------- 0.10.44 : B calculé par le code

EMETTEURS = {"acled": "ACLED", "fred": "FRED (Federal Reserve Bank of St. Louis)", "dbnomics": "DBnomics",
             "yfinance": "Yahoo Finance", "wikipedia": "Wikipedia"}


def _vue(f: float, classe: str, source: str, periode: str, disponible: str, calcul: str, x: dict | None = None,
         ecart: str = "identique : même série, même comparaison, même horizon que le critère de résolution") -> dict:
    v = {"frequence": min(0.999, max(0.001, f)), "compte_calcule": True, "classe_de_reference": classe,
         "source": source, "periode": periode, "disponible_le": disponible, "calcul": calcul, "ecart_critere": ecart,
         "classe_alternative": None, "motif_sans_alternative": "classe fixée par la forme de la question ForecastBench"}
    if x:   # 0.10.46 : la résolution vient de la question (sans elle, le dossier était refusé)
        v["resolution"] = x.get("criteres") or x.get("titre")
        v["source_resolution"] = {"emetteur": EMETTEURS.get(x.get("source"), str(x.get("source"))),
                                  "document": x.get("url") or "jeu de résolutions ForecastBench",
                                  "regle_ambiguite": "la résolution publiée par ForecastBench fait foi"}
    return v


def b_acled(m: float) -> float:
    """« Plus d'événements dans les 30 jours avant R que la moyenne sur 30 jours des 360 jours avant D » (m, valeur au
    gel). Compte total K = 12·m sur 12 fenêtres ; taux a posteriori Gamma(K + ½, 12) (Jeffreys) ; compte d'une nouvelle
    fenêtre : binomiale négative (r = K + ½, p = 12/13). P(N > m) = 1 − Σ_{n ≤ ⌊m⌋} P(N = n). Ne voit pas la
    surdispersion des conflits (rafales) : pour les morts, la vraie probabilité est plutôt plus basse."""
    r, q = 12 * max(m, 0.0) + 0.5, 1 / 13
    cdf = sum(math.exp(math.lgamma(n + r) - math.lgamma(r) - math.lgamma(n + 1) + r * math.log(1 - q) + n * math.log(q))
              for n in range(int(math.floor(m)) + 1))
    return 1 - cdf


def b_hausse(points: list[dict], h: int, avant: date, annees: int = 5) -> tuple[float, int, int] | None:
    """Part des intervalles de h jours (sur les `annees` dernières années avant D) où la série a MONTÉ : (k + ½)/(n + 1)."""
    pts = sorted((date.fromisoformat(p["date"][:10]), float(p["valeur"])) for p in points
                 if p.get("date") and p.get("valeur") is not None and p["date"][:10] < avant.isoformat())
    pts = [p for p in pts if p[0] >= avant - timedelta(days=365 * annees)]
    if len(pts) < 20:
        return None
    k = n = 0
    j = 0
    for i, (t, v) in enumerate(pts):
        cible = t + timedelta(days=h)
        while j < len(pts) and pts[j][0] < cible:
            j += 1
        if j >= len(pts):
            break
        n += 1
        k += pts[j][1] > v
    if n < 10:
        return None
    return (k + 0.5) / (n + 1), k, n


async def vue_calculee(x: dict, q: dict, jeu: str) -> dict | None:
    """Le taux de base calculé par le code quand la forme de la question le permet ; None sinon (vues du modèle)."""
    d0 = date.fromisoformat(jeu)
    h = (date.fromisoformat(x["resolution"]) - d0).days
    gel = str(q.get("freeze_datetime") or jeu)[:10]
    src = q.get("source")
    try:
        if src == "acled":
            m = float(q.get("freeze_datetime_value"))
            return _vue(b_acled(m), "fenêtres de 30 jours du même pays et du même type d'événement (ACLED)",
                        "ForecastBench, valeur de référence au gel (moyenne ACLED sur 30 jours, 360 jours)",
                        f"360 jours avant {gel}", gel,
                        f"binomiale négative, r = 12·{m:.4g} + 0,5, p = 12/13 ; P(N > {m:.4g}) (Jeffreys)", x,
                        "la classe suppose un taux stable (Poisson-gamma) ; le critère compare la fenêtre de 30 jours qui "
                        "finit à la résolution à la moyenne des 360 jours avant le gel, et les conflits arrivent en rafales")
        if src == "yfinance" and "higher rate of return than" in q.get("question", ""):
            return _vue(0.5, "paires d'actions, rendement relatif sur le même intervalle", "symétrie de la paire",
                        jeu, jeu, "0,5 : les deux actions sont échangeables a priori (aucune ne domine sans information)", x,
                        "identique : le critère compare les deux rendements sur le même intervalle")
        if src in ("fred", "dbnomics") and h > 0:
            import alphabet_puits as apz
            if src == "fred":
                try:
                    r = await apz.fred(q["id"], avant=d0)
                except Exception:
                    r = {}
                if len(r.get("points") or []) < 20:
                    # 0.10.46 : certaines séries (SP500…) n'ont pas de millésimes ALFRED ; valeurs actuelles, bornées à D
                    # par b_hausse (les cours de marché ne sont pas révisés)
                    r = await apz.fred(q["id"])
            else:
                r = await apz.dbnomics(q["url"].split("db.nomics.world/", 1)[1], avant=d0)
            b = b_hausse(r.get("points") or [], h, d0)
            # 0.10.78 : la série téléchargée ici sert aussi à l'ombre « ancrage par les séries » (au banc, le puits du
            # bot n'est pas appelé pour ces questions) ; bornée STRICTEMENT avant la date d'information
            x["_releve"] = dict(r, points=[p for p in r.get("points") or [] if str(p.get("date", ""))[:10] < jeu])
            if b:
                f, k, n = b
                return _vue(f, f"intervalles de {h} jours de la même série, 5 ans avant {jeu}",
                            f"{r.get('source')} : {r.get('titre')}", f"5 ans avant {jeu}", jeu,
                            f"({k} hausses + 0,5) / ({n} intervalles + 1) (Jeffreys)", x)
    except Exception:
        return None
    return None


async def un_test(x: dict, jeu: str, llm, deja: set[str]) -> dict | None:
    if x["qid"] in deja:
        return None
    info = datetime.fromisoformat(jeu).replace(tzinfo=timezone.utc)
    issue = "yes" if x["issue"] == 1 else "no"
    ligne = {"type": "retro", "banc": "forecastbench", "jeu": jeu, "source_question": x["source"],
             "version_bot": ap.VERSION_BOT, "version_skill": ap.version_skill(), "question_id": x["qid"],
             "modeles": ap.modeles_actifs(), "url": x["url"], "titre": x["titre"], "date_information": jeu,
             "resolution": x["resolution"], "issue": x["issue"],
             "licence": "ForecastBench, Forecasting Research Institute, CC BY-SA 4.0"}
    try:
        sonde = ap.extraire_json(await llm(ar.consigne_sonde(x["titre"], x["criteres"])))
    except Exception as e:
        sonde = {"erreur": str(e)[:200]}
    ligne["sonde"] = sonde
    if sonde.get("connait") is True and str(sonde.get("issue") or "").lower() == issue:
        ligne["statut"] = "exclue_connue"
        return ligne
    q = ap.Question(id=x["qid"], url=x["url"], titre=x["titre"], contexte=x["contexte"], criteres=x["criteres"],
                    precisions="", resolution=date.fromisoformat(x["resolution"]))
    jours = max(1, (date.fromisoformat(x["resolution"]) - info.date()).days)

    async def chercher(req: str) -> str:
        return await ar.chercher_avant(req, info)
    vue = await vue_calculee(x, x["_q"], jeu)
    ligne["b_calcule"] = bool(vue)
    ligne["vue_calculee"] = vue     # 0.10.47 : gardée au registre, pour vérifier la cohérence de B
    c = await ap.alphabet(q, "", llm, chercher, True, jeu, jours, ar.historique_avant, vue_fixee=vue)
    p_b = c.get("p_B")
    if p_b is None and vue and vue.get("frequence") is not None:
        # 0.10.61 : B est calculé par le code AVANT la lecture ; une question jugée hors alphabet (ou refusée au plan)
        # garde son B, comme la pipeline le fixe (trace["p_B"] = fréquence de la vue)
        p_b = float(vue["frequence"])
    ligne.update(statut=c.get("statut"), p_B=p_b, p_C=c.get("p_C"), motif=c.get("motif"),
                 evenement=c.get("evenement"), etat=c.get("etat"), vues=c.get("vues"), classe_statut=c.get("classe_statut"),
                 nature_etat_nul=c.get("nature_etat_nul"), puits=c.get("puits"),
                 compte_calcule=bool((c.get("vue") or {}).get("compte_calcule")),
                 exploratoire=c.get("exploratoire"), symetrique=c.get("symetrique"),
                 ombre_causale=c.get("ombre_causale"), rejeu=c.get("_rejeu"),
                 empreintes_passages=c.get("empreintes_passages"),
                 tiers_polarite=c.get("tiers_polarite") or (c.get("exploratoire") or {}).get("tiers_polarite"),
                 attribution=ap.controle_attribution(c.get("dossier"), c.get("_textes")))
    # 0.10.70 : ombre « absence » (hypothèse enregistrée le 2026-11-13), état nul posté ou exploratoire
    for k_ in ("ombre_filtrage", "ombre_series"):      # 0.10.73 : tâches refaites par le code, en ombre
        ligne[k_] = c.get(k_) or (c.get("exploratoire") or {}).get(k_)
    if not ligne.get("ombre_series") and x.get("_releve"):       # 0.10.78 : série du banc, bornée à D
        try:
            import ombres_auto as oa
            mots_ = (((c.get("_rejeu") or {}).get("lectures") or [{}])[-1] or {}).get("mots")
            ligne["ombre_series"] = oa.comparer_series([x["_releve"]], None, mots_)
        except Exception as e:
            ligne["ombre_series"] = {"erreur": f"{type(e).__name__}: {e}"[:200]}
    ligne["ombre_absence"] = ap.ombre_absence(p_b, c.get("nature_etat_nul")
                                              or (c.get("exploratoire") or {}).get("nature_etat_nul"))
    if c.get("statut") == "refuse" and c.get("dossier"):     # 0.10.55 : en strate 7 aussi, le dossier refusé est gardé
        d_ = c["dossier"]
        ligne["dossier_refuse"] = {k: d_.get(k) for k in ("candidats", "contre_candidate", "mots", "rejets", "liaisons",
                                                          "questions", "_reparations") if k in d_}
    if (c.get("exploratoire") or {}).get("statut") == "panne":      # 0.10.54 : la panne de la lecture exploratoire
        ligne.update(statut="panne", motif=c["exploratoire"].get("motif"))
    return ligne


def questions_de(version: str) -> tuple[list[str], set[str]]:
    """0.10.58 : les questions (identifiants et jeux) jouées par une version du bot : pour qu'un autre codeur lise les
    MÊMES questions (test multi-lecteurs). Les pannes ne comptent pas."""
    f = ap.REGISTRE / ar.RETRO
    lignes = [json.loads(l) for l in f.read_text(encoding="utf-8").splitlines() if l.strip()] if f.is_file() else []
    qids = {x["question_id"] for x in lignes if x.get("banc") == "forecastbench" and x.get("version_bot") == version
            and x.get("statut") != "panne"}
    return sorted({q.split(":")[1] for q in qids}), qids


def deja_par(modele: str) -> set[str]:
    """0.10.58 : les questions du banc déjà lues par CE modèle principal (un autre codeur peut les relire)."""
    f = ap.REGISTRE / ar.RETRO
    lignes = [json.loads(l) for l in f.read_text(encoding="utf-8").splitlines() if l.strip()] if f.is_file() else []
    return {x["question_id"] for x in lignes if x.get("banc") == "forecastbench" and x.get("statut") != "panne"
            and (x.get("modeles") or {}).get("principal") == modele}


async def principal(n: int, apres: str, jeu: str | None, sources: tuple[str, ...], graine: int,
                    memes_que: str | None = None) -> int:
    import alphabet_bot as ab
    import alphabet_modeles as am
    if not ar.recherche_bornee_disponible():
        print("Banc ForecastBench : il faut une recherche bornable dans le temps (EXA_API_KEY ou TINYFISH_API_KEY). "
              "Rien n'est lancé.")
        return 1
    choix, essais = await am.choisir()
    if not choix["principal"]:
        print("Aucun modèle principal disponible. Rien n'est lancé.")
        for e_ in essais:                          # 0.10.58 : pourquoi (modèle inconnu, clé, réponse sans JSON…)
            print(f"  essai {e_.get('role')} {e_.get('modele')} : {e_.get('erreur')}")
        return 1
    am.appliquer(choix)
    modele = ab.configuration().get("default")

    delai_appel = float(os.environ.get("ALPHABET_APPEL_DELAI") or "600")

    async def llm(consigne: str) -> str:
        # 0.10.59 : aucun appel ne peut bloquer le banc au-delà de ce délai ; le dépassement est une PANNE (harnais)
        try:
            return await asyncio.wait_for(modele.invoke(consigne), delai_appel)
        except asyncio.TimeoutError:
            raise TimeoutError(f"appel au modèle sans réponse en {delai_appel:.0f} s") from None
    jeux = [jeu] if jeu else jeux_candidats(date.today(), date.fromisoformat(apres))
    deja, faites, pannes_suite = ar.deja_faites(), 0, 0
    cibles = None
    if memes_que:
        # 0.10.58 : test multi-lecteurs : les questions d'une version passée, relues par le codeur de ce passage
        jeux, cibles = questions_de(memes_que)
        deja = deja_par(choix["principal"])
        print(f"Mêmes questions que la version {memes_que} : {len(cibles)} ; codeur {choix['principal']} ; "
              f"{len(cibles & deja)} déjà lue(s) par lui.")
        if not cibles:
            print("Aucune question pour cette version. Rien n'est lancé.")
            return 1
    rnd = random.Random(graine)
    from forecasting_tools import MonetaryCostManager
    for j in jeux:
        if faites >= n or pannes_suite >= 3:
            break
        try:
            qs = await _json(f"{DEPOT}/question_sets/{j}-llm.json")
            rs = await _json(f"{DEPOT}/resolution_sets/{j}_resolution_set.json")
        except Exception as e:
            print(f"Jeu {j} indisponible : {type(e).__name__}")
            continue
        items = [construire(i, j) for i in apparier(qs, rs, sources)]
        if cibles is not None:
            items = [x for x in items if x["qid"] in cibles]
        rnd.shuffle(items)
        print(f"Jeu {j} : {len(items)} questions de séries résolues.")
        for x in items:
            if faites >= n:
                break
            avant_m = ar.moteurs_utilises()
            with MonetaryCostManager() as cm:
                try:
                    ligne = await un_test(x, j, llm, deja)
                except Exception as e:
                    # 0.10.54 : une exception du banc est une panne du HARNAIS (code ou service), pas un refus
                    ligne = {"type": "retro", "banc": "forecastbench", "version_bot": ap.VERSION_BOT,
                             "question_id": x["qid"], "statut": "panne", "motif": f"{type(e).__name__}: {e}"[:300]}
                cout = cm.current_usage
            if ligne is None:
                continue
            ligne["cout_usd"] = round(float(cout or 0), 4)
            apres_m = ar.moteurs_utilises()      # 0.10.50 : quels moteurs ont servi pour CETTE question
            ligne["moteurs_recherche"] = {k: v - avant_m.get(k, 0) for k, v in apres_m.items() if v - avant_m.get(k, 0)}
            ar.ecrire(ligne)
            if ligne.get("statut") == "panne":
                # 0.10.54 : écrite pour le diagnostic, mais ni comptée ni marquée faite : un prochain passage la refera.
                # Trois pannes de suite : le service est tombé, on s'arrête plutôt que de brûler la liste.
                pannes_suite += 1
                print(f"{ligne['question_id'][:60]} : PANNE (non comptée) · {ligne.get('motif', '')[:120]}")
                if pannes_suite >= 3:
                    print("Trois pannes de suite : arrêt du banc.")
                    break
                continue
            pannes_suite = 0
            deja.add(ligne["question_id"])
            faites += 1
            print(f"{ligne['question_id'][:60]} : {ligne.get('statut')} · B {ligne.get('p_B')} · C {ligne.get('p_C')} · "
                  f"issue {ligne.get('issue')} · {ligne['cout_usd']} $")
    print(f"{faites} question(s) ForecastBench écrite(s) dans registre/{ar.RETRO}.")
    return 0


if __name__ == "__main__":
    a = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    a.add_argument("--n", type=int, default=int(os.environ.get("ALPHABET_FB_N") or 20))
    a.add_argument("--apres", default=os.environ.get("ALPHABET_RETRO_APRES") or "2026-07-01",
                   help="jeux postérieurs à cette date (après la date de connaissance du modèle)")
    a.add_argument("--jeu", default=None, help="date d'un jeu (AAAA-MM-JJ) ; sinon les plus récents résolus")
    a.add_argument("--sources", default=",".join(SOURCES_SERIES))
    a.add_argument("--graine", type=int, default=0)
    a.add_argument("--memes-que", default=os.environ.get("ALPHABET_FB_MEMES") or None,
                   help="version du bot dont on relit les mêmes questions (test multi-lecteurs)")
    args = a.parse_args()
    srcs = tuple(s for s in args.sources.split(",") if s in SOURCES_SERIES)
    sys.exit(asyncio.run(principal(args.n, args.apres, args.jeu, srcs, args.graine, args.memes_que)))
