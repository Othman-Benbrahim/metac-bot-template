"""Planificateur de nuit : lance lui-même les collectes quotidiennes, sans dépendre de l'horloge de GitHub (bot 0.10.246).

Décision d'auteur du 2026-11-18 (3 h 21) : « je valide le mécanisme, fais-le plutôt la nuit, la journée, ça risque de
rentrer en conflit avec mes propres workflows ». Origine : DARK-AVENGER-78758/metaculus-autopilot (veille du
2026-11-17) : GitHub retarde ou saute les tâches programmées (constaté le 2026-11-17 : 7 h 23 → 17 h 14, 17 h 37 →
0 h 38) ; chaque passage lance donc le suivant lui-même.

Fonctionnement (la nuit seulement, de 21 h 00 à 5 h 45 UTC, soit 22 h 00 à 6 h 45 à Paris en hiver) :
- toutes les 3 minutes, le planificateur regarde quelles collectes de la liste sont DUES (aucun passage réussi depuis
  16 heures, aucune tentative depuis 2 heures, et leurs contraintes propres : avions d'État après 0 h 10 UTC, quand les
  crédits OpenSky reviennent ; nowcast les jours ouvrés) ;
- il en lance une (workflow_dispatch), la plus en retard, si moins de 3 collectes tournent déjà, et si c'est la veille
  d'articles (qui partage le groupe des bancs), seulement quand aucun banc ne tourne ;
- au bout de 5 h 15 (limite d'un passage : 6 h), il se relance lui-même s'il fait encore nuit, puis s'arrête.
Démarrage : deux tâches programmées le soir (20 h 53 et 22 h 53 UTC ; la seconde rattrape la première si GitHub la
saute) ; un planificateur qui en trouve un autre déjà en marche s'arrête aussitôt. Les collectes gérées ici n'ont plus de
tâche programmée propre ; on peut toujours les lancer à la main.

    python planificateur.py [--essai]   (--essai : dit ce qu'il lancerait, sans rien lancer)
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from datetime import datetime, timedelta, timezone

import httpx

DEPOT = os.environ.get("GITHUB_REPOSITORY", "Othman-Benbrahim/metac-bot-template")
API = f"https://api.github.com/repos/{DEPOT}"
NUIT = (21 * 60, 5 * 60 + 45)            # minutes UTC : début, fin (la fenêtre passe minuit)
DUREE_PASSAGE = 5 * 3600 + 15 * 60
PAS = 180
MAX_EN_COURS = 3
DELAI_REUSSITE = timedelta(hours=16)
# 0.10.485 (décision de l'auteur, 2026-11-24, 10 h 23) : la veille d'articles (liens envoyés par courriel) passe en tête
# de file ; elle ne s'est pas faite la nuit du 24 novembre, restée dans la file à la fin de la nuit.
PRIORITAIRES = ("veille_articles.yaml",)
DELAI_TENTATIVE = timedelta(hours=2)
MOI = "planificateur.yaml"
GROUPE_BANCS = "bot-alphabet-registre"
# (fichier, contrainte) ; contrainte : None, "apres_minuit" (avions d'État : crédits OpenSky), "jours_ouvres",
# "lundi" (0.10.464 : une fois par semaine, la nuit de dimanche à lundi, après minuit UTC),
# "premier_lundi" (0.10.470 : une fois par mois, le premier lundi)
COLLECTES = (
    ("collecte_gdelt.yaml", None), ("collecte_ooni.yaml", None), ("collecte_radar.yaml", None),
    ("collecte_sanctions.yaml", None), ("collecte_rss.yaml", None), ("collecte_feux.yaml", None),
    ("collecte_violationswatch.yaml", None), ("collecte_calendrier_nbs.yaml", None),
    ("collecte_avis_navigation.yaml", None), ("collecte_portwatch.yaml", None),
    ("collecte_recit_russe.yaml", None), ("collecte_avions_etat.yaml", "apres_minuit"),
    ("collecte_nowcast_inflation.yaml", "jours_ouvres"), ("veille_articles.yaml", "groupe_bancs"),
    ("collecte_telegram.yaml", None),
    ("gdelt_bigquery.yaml", None),            # 0.10.277 : requête groupée de nuit (questions ouvertes, 30 jours)
    ("collecte_certificats.yaml", None),      # 0.10.299 : sources hors cadre (certificats, routines, Federal Register)
    ("collecte_routines.yaml", None), ("collecte_federal_register.yaml", None),
    ("collecte_congres.yaml", None),          # 0.10.301 : clés données par l'auteur (EUIPO retiré en 0.10.303 :
                                              # pièce d'identité exigée, refusée par l'auteur)
    ("collecte_tribunaux.yaml", None),
    ("collecte_tfr.yaml", None),              # 0.10.304 : interdictions de survol FAA (liste JSON trouvée par la sonde)
    ("mecanique.yaml", "lundi"),              # 0.10.464 : mécanique de bascule en ombre, hebdomadaire
    ("collecte_veille.yaml", None),           # 0.10.480 : veille de la carte (flux RSS des fiches et compartiments)
    ("lecture_cartes.yaml", "premier_lundi"), # 0.10.470 : cartes publiées (standard de lecture), mensuel
    ("collecte_fred.yaml", None), ("collecte_meteo.yaml", None), ("collecte_eia.yaml", None), ("collecte_ouvertes.yaml", None), ("collecte_webamon.yaml", None), ("collecte_openmeasures.yaml", None), ("collecte_seismes.yaml", None), ("collecte_gfs.yaml", None), ("collecte_series_publiques.yaml", None), ("collecte_cadrage.yaml", None), ("collecte_matieres.yaml", None),   # 0.10.318 : traces du bas de l'échelle (écosystèmes)
)


def de_nuit(t: datetime) -> bool:
    m = t.hour * 60 + t.minute
    return m >= NUIT[0] or m < NUIT[1]


def permise(contrainte: str | None, t: datetime) -> bool:
    if contrainte == "apres_minuit":
        return 10 <= t.hour * 60 + t.minute < NUIT[1]
    if contrainte == "jours_ouvres":
        return t.weekday() < 5
    if contrainte == "lundi":
        return t.weekday() == 0 and t.hour * 60 + t.minute < NUIT[1]
    if contrainte == "premier_lundi":
        return t.weekday() == 0 and t.day <= 7 and t.hour * 60 + t.minute < NUIT[1]
    return True


def dues(passages: dict[str, list[dict]], t: datetime, bancs_actifs: bool) -> list[str]:
    """Collectes dues, la plus en retard d'abord. passages[fichier] = [{"cree": datetime, "conclusion": str|None}]."""
    out = []
    for f, contrainte in COLLECTES:
        if not permise(contrainte, t) or (contrainte == "groupe_bancs" and bancs_actifs):
            continue
        ps = passages.get(f, [])
        if any(p["conclusion"] is None for p in ps):                     # déjà en file ou en cours
            continue
        reussis = [p["cree"] for p in ps if p["conclusion"] == "success"]
        if reussis and t - max(reussis) < DELAI_REUSSITE:
            continue
        if ps and t - max(p["cree"] for p in ps) < DELAI_TENTATIVE:
            continue
        out.append((max(reussis) if reussis else datetime.min.replace(tzinfo=timezone.utc), f))
    return [f for _, f in sorted(out, key=lambda x: (x[1] not in PRIORITAIRES, x[0]))]


class Github:
    def __init__(self, jeton: str):
        self.c = httpx.Client(headers={"Authorization": f"Bearer {jeton}", "Accept": "application/vnd.github+json",
                                       "X-GitHub-Api-Version": "2022-11-28"}, timeout=60)

    def passages(self, fichier: str) -> list[dict]:
        r = self.c.get(f"{API}/actions/workflows/{fichier}/runs", params={"per_page": 10})
        r.raise_for_status()
        out = []
        for x in r.json().get("workflow_runs", []):
            out.append({"cree": datetime.fromisoformat(x["created_at"].replace("Z", "+00:00")),
                        "conclusion": x["conclusion"] if x["status"] == "completed" else None, "id": x["id"]})
        return out

    def en_cours(self) -> list[dict]:
        out = []
        for s in ("in_progress", "queued", "waiting", "pending"):
            r = self.c.get(f"{API}/actions/runs", params={"status": s, "per_page": 100})
            r.raise_for_status()
            out += r.json().get("workflow_runs", [])
        return out

    def lancer(self, fichier: str, entrees: dict | None = None) -> None:
        corps = {"ref": "main", **({"inputs": entrees} if entrees else {})}
        r = self.c.post(f"{API}/actions/workflows/{fichier}/dispatches", json=corps)
        r.raise_for_status()


def fichiers_du_groupe() -> set[str]:
    import glob
    out = set()
    for f in glob.glob(".github/workflows/*.yaml"):
        if f"group: {GROUPE_BANCS}" in open(f, encoding="utf-8").read():
            out.add(os.path.basename(f))
    return out


def principal(essai: bool) -> int:
    jeton = os.environ.get("GITHUB_TOKEN")
    if not jeton:
        print("GITHUB_TOKEN absent.")
        return 1
    gh = Github(jeton)
    moi = os.environ.get("GITHUB_RUN_ID")
    debut = time.monotonic()
    groupe = fichiers_du_groupe()
    noms_collectes = {f for f, _ in COLLECTES}
    autres = [x for x in gh.en_cours() if x.get("path", "").endswith(MOI) and str(x["id"]) != str(moi)]
    if autres and not essai:
        print("Un autre planificateur tourne déjà : arrêt.")
        return 0
    lances = []
    while True:
        t = datetime.now(timezone.utc)
        if not de_nuit(t):
            print(f"{t:%H:%M} UTC : il fait jour, arrêt (pas de relance).")
            break
        if time.monotonic() - debut > DUREE_PASSAGE:
            if not essai:
                gh.lancer(MOI)
            print(f"{t:%H:%M} UTC : fin de ce passage, planificateur relancé.")
            break
        actifs = gh.en_cours()
        fichiers_actifs = [x.get("path", "").split("/")[-1] for x in actifs]
        bancs_actifs = any(f in groupe for f in fichiers_actifs)
        n_collectes = sum(1 for f in fichiers_actifs if f in noms_collectes)
        passages = {f: gh.passages(f) for f, _ in COLLECTES}
        a_faire = dues(passages, t, bancs_actifs)
        if essai:
            print(f"{t:%H:%M} UTC : dues {a_faire} ; collectes en cours {n_collectes} ; bancs actifs {bancs_actifs}")
            break
        if a_faire and n_collectes < MAX_EN_COURS:
            gh.lancer(a_faire[0])
            lances.append(f"{t:%H:%M} {a_faire[0]}")
            print(f"{t:%H:%M} UTC : lancé {a_faire[0]} (encore dues : {a_faire[1:]})", flush=True)
        time.sleep(PAS)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as fo:
            fo.write("## Planificateur de nuit\n\n" + ("\n".join(f"- {x}" for x in lances) or "rien lancé") + "\n")
    return 0


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("--essai", action="store_true")
    sys.exit(principal(a.parse_args().essai))
