"""La mécanique de bascule en temps réel, en OMBRE — bot 0.10.464 (étape 1 : étincelles, journal, calcul).

Décision de l'auteur, 2026-11-22, 20 h 51 - 20 h 57 : mettre en place, sur la carte et dans le bot, toute la mécanique
issue de la réflexion du jour (grammaire de bascule, seuil / tension / étincelle, cycles, rapport des forces, émetteur
et acte de langage, temps du texte, propagation, niveau de mesure, H2 signal × terrain, boucle), pour PRODUIRE des
prédictions. Rien n'entre dans les prévisions Metaculus avant qu'un score réel le justifie.

Étape 1 (ce fichier) :
- lit les manifestations GDELT par pays et par semaine (registre/gdelt-manifestations-recentes.csv, mode court de
  gdelt_bq.py ; sinon le relevé complet) ;
- repère les ÉTINCELLES de la dernière semaine complète (définitions validées par l'auteur le 22 novembre à 20 h 07) :
  part des manifestations ≥ 2 × niveau habituel (médiane des 52 semaines précédentes), après 4 semaines sous ce seuil ;
- prédit pour chacune la probabilité qu'elle PRENNE dans les 8 semaines (part ≥ 1,5 × niveau habituel au moins
  4 semaines sur 8) ;
- inscrit chaque prédiction dans un journal à AJOUT SEUL, constate les issues 8 semaines plus tard, calcule le score.

Calcul : log-cote de départ = taux observé sur 2015-2021 (31,5 % des 2 539 étincelles prennent, cas intermédiaires
compris) ; chaque MODULE de la mécanique ajoute un déplacement dans le sens fixé par l'auteur, de force w apprise sur les
issues réelles (la boucle). À l'étape 1, aucun module n'est encore branché : la prédiction est le taux de départ.
Étapes suivantes : signaux (lecteur-local, rang, acte, temps du fait), terrain (fiches, Banque mondiale), échéances.

Étape 2 (0.10.465, sens validés par l'auteur le 22 novembre à 21 h 15) : six modules, lus pour le pays de l'étincelle
dans les articles du collecteur lecteur-local (comptes/situations.jsonl) de la semaine de l'étincelle, et dans le
calendrier des élections (registre/elections.csv). Chaque entrée est orientée : + pousse vers « prend ».
- corroboration (+) : au moins 3 articles de 2 émetteurs sur le pays ;
- signal_faible (+) : moins de 3 articles, dont un d'une source officielle, et rien sur le pays dans les 30 jours avant ;
- rang_emetteur (+) : part des articles venant de sources officielles (rubrique « officiel » du collecteur) ;
- acte_haut_rang (+) : un terme d'acte d'État (état d'urgence, couvre-feu…) dans un article sur le pays ;
- fait_passe (−) : part des articles sur le pays qui portent sur un fait passé dans un calendrier attendu (procès,
  anniversaire, commémoration) ; l'entrée vaut −part, pour que tous les poids soient positifs au départ ;
- echeance (+) : une élection nationale prévue dans le pays dans les 8 semaines qui suivent.
L'annonce seule n'a aucun effet (position de l'auteur : elle ne prédit rien). Absence d'articles = 0, pas un signe
contraire. Poids de départ égaux et faibles (POIDS_DEPART) ; la boucle les ajuste sur chaque issue constatée
(descente de gradient de la perte logistique, pas APPRENTISSAGE), une seule fois par issue.
"""
from __future__ import annotations

import csv
import json
import math
import os
import statistics as st
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

REG = Path(os.environ.get("ALPHABET_REGISTRE", "registre"))
RECENTES = REG / "gdelt-manifestations-recentes.csv"
COMPLET = REG / "gdelt-manifestations-semaines.csv"
JOURNAL = REG / "mecanique-journal.csv"
ISSUES = REG / "mecanique-issues.csv"
POIDS = REG / "mecanique-poids.json"
SCORE = REG / "mecanique-score.json"
CODES = Path("ecosystemes/codes-pays-fips.csv")
VERSION = "0.10.468"
# 0.10.468 (accord de l'auteur, 2026-11-23, 7 h 06 ; veille Munshi, ch. 36-37 : un modèle faux devient plus sûr de lui
# à mesure que les données s'accumulent) : trois contrôles du modèle, affichés avec le score — calibration par tranches
# de probabilité, sous-ensembles (régions, périodes : mécanisme reproductible ou cadre à déplacer), résidus (surprises).
# 0.10.466 (accord de l'auteur, 2026-11-23, 5 h 42) : e-valeur, comparaison de la mécanique au taux de départ que l'on
# peut regarder chaque semaine sans gonfler l'erreur (test par pari, Waudby-Smith et Ramdas, arXiv 2010.09686).
# Préenregistré : seuil E_SEUIL = 20 (erreur 5 %) ; le franchir autorise à PROPOSER à l'auteur l'entrée de la mécanique
# dans les prévisions Metaculus (la décision reste la sienne) ; ne pas le franchir n'est pas une preuve contraire.
E_SEUIL, E_MISE_MAX = 20.0, 0.5
LECTEUR = Path(os.environ.get("LECTEUR_LOCAL", "lecteur"))      # dépôt lecteur-local (copie en lecture seule)
TERMES = Path("ecosystemes/mecanique-termes.yaml")
ELECTIONS = REG / "elections.csv"
POIDS_DEPART, APPRENTISSAGE = 0.2, 0.1
MODULES = ("corroboration", "signal_faible", "rang_emetteur", "acte_haut_rang", "fait_passe", "echeance")

MIN_EVENEMENTS = 200          # semaines plus petites ignorées (bruit)
FENETRE, MIN_VALIDES = 52, 40
SEUIL_ETINCELLE, SEUIL_ELEVE, CALME = 2.0, 1.5, 4
HORIZON, PREND_MIN = 8, 4
TAUX_DEPART = 0.315           # observation 2015-2021 (claude/observation-h2-terrain-… dans le projet)

COLS_JOURNAL = ["id", "inscrit_le", "pays", "iso3", "semaine", "part", "niveau_habituel", "rapport", "p_prend",
                "version", "modules"]
COLS_ISSUES = ["id", "constate_le", "prend", "semaines_elevees"]


def logit(p: float) -> float:
    return math.log(p / (1 - p))


def sigmo(x: float) -> float:
    return 1 / (1 + math.exp(-x))


def lire_series(chemin: Path) -> dict[str, list[tuple[str, float | None]]]:
    """{pays FIPS: [(semaine, part ou None)]}, triées, avec les semaines manquantes comblées (part None)."""
    brut: dict[str, dict[str, tuple[int, int]]] = {}
    for r in csv.DictReader(chemin.open(encoding="utf-8")):
        brut.setdefault(r["pays"], {})[r["semaine"]] = (int(r["evenements"]), int(r["manifs"]))
    out = {}
    for p, d in brut.items():
        s0, s1 = date.fromisoformat(min(d)), date.fromisoformat(max(d))
        l, s = [], s0
        while s <= s1:
            e, m = d.get(s.isoformat(), (0, 0))
            l.append((s.isoformat(), m / e if e >= MIN_EVENEMENTS else None))
            s += timedelta(weeks=1)
        out[p] = l
    return out


def niveau(l: list, i: int) -> float | None:
    base = [w for _, w in l[max(0, i - FENETRE):i] if w is not None]
    if len(base) < MIN_VALIDES:
        return None
    b = st.median(base)
    return b if b > 0 else None


def etincelle(l: list, i: int) -> tuple[float, float] | None:
    """(part, niveau habituel) si la semaine i est une étincelle, sinon None."""
    s, v = l[i]
    if v is None or i < FENETRE:
        return None
    b = niveau(l, i)
    if b is None or v < SEUIL_ETINCELLE * b:
        return None
    if any(w is None or w >= SEUIL_ETINCELLE * b for _, w in l[i - CALME:i]):
        return None
    return v, b


def lire_csv(chemin: Path) -> list[dict]:
    return list(csv.DictReader(chemin.open(encoding="utf-8"))) if chemin.exists() else []


def ajouter(chemin: Path, cols: list[str], lignes: list[dict]) -> None:
    """Ajout seul : on n'écrit que de nouvelles lignes à la fin ; rien d'existant n'est réécrit."""
    neuf = not chemin.exists()
    chemin.parent.mkdir(parents=True, exist_ok=True)
    with chemin.open("a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        if neuf:
            w.writeheader()
        w.writerows(lignes)


def codes_iso3() -> dict[str, str]:
    if not CODES.exists():
        return {}
    lignes = [l for l in CODES.read_text(encoding="utf-8").splitlines() if l and not l.startswith("#")]
    return {r["fips"]: r["iso3"] for r in csv.DictReader(lignes)}


def codes_complets() -> list[dict]:
    if not CODES.exists():
        return []
    lignes = [l for l in CODES.read_text(encoding="utf-8").splitlines() if l and not l.startswith("#")]
    return list(csv.DictReader(lignes))


def charger_contexte() -> dict:
    """Ce que les modules lisent : articles du collecteur (par pays FIPS), élections (par pays FIPS), termes."""
    import yaml
    codes = codes_complets()
    fr2fips = {r["nom_fr"]: r["fips"] for r in codes if r.get("nom_fr")}
    iso2fips = {r["iso2"]: r["fips"] for r in codes if r.get("iso2")}
    articles: dict[str, list[dict]] = {}
    f = LECTEUR / "comptes/situations.jsonl"
    if f.exists():
        for l in f.open(encoding="utf-8"):
            try:
                a = json.loads(l)
            except ValueError:
                continue
            for e in a.get("espace", []):
                if e.startswith("pays:") and e[5:] in fr2fips:
                    articles.setdefault(fr2fips[e[5:]], []).append(
                        {"jour": a.get("jour", ""), "emetteur": (a.get("emetteur") or {}).get("domaine", ""),
                         "officiel": a.get("rubrique") == "officiel", "termes": [t.lower() for t in a.get("termes", [])]})
    elections: dict[str, list[str]] = {}
    if ELECTIONS.exists():
        for r in csv.DictReader(ELECTIONS.open(encoding="utf-8")):
            if r.get("pays") in iso2fips:
                elections.setdefault(iso2fips[r["pays"]], []).append(r["date"])
    termes = yaml.safe_load(TERMES.read_text(encoding="utf-8")) if TERMES.exists() else {}
    return {"articles": articles, "elections": elections,
            "acte": {t.lower() for t in (termes.get("acte_haut_rang") or [])},
            "fait_passe": {t.lower() for t in (termes.get("fait_passe") or [])}}


def modules(pays: str, semaine: str, contexte: dict) -> dict[str, float]:
    """Les entrées des mécanismes (x_k), chacune orientée dans le sens fixé par l'auteur (+ pousse vers « prend »)."""
    if not contexte:
        return {}
    w0 = date.fromisoformat(semaine)
    d0, d1, avant = w0.isoformat(), (w0 + timedelta(days=6)).isoformat(), (w0 - timedelta(days=30)).isoformat()
    tous = contexte.get("articles", {}).get(pays, [])
    sem = [a for a in tous if d0 <= a["jour"] <= d1]
    x = {k: 0.0 for k in MODULES}
    if sem:
        n, em = len(sem), {a["emetteur"] for a in sem}
        x["corroboration"] = 1.0 if n >= 3 and len(em) >= 2 else 0.0
        x["signal_faible"] = 1.0 if n < 3 and any(a["officiel"] for a in sem) and not any(
            avant <= a["jour"] < d0 for a in tous) else 0.0
        x["rang_emetteur"] = round(sum(a["officiel"] for a in sem) / n, 3)
        x["acte_haut_rang"] = 1.0 if any(set(a["termes"]) & contexte["acte"] for a in sem) else 0.0
        x["fait_passe"] = -round(sum(1 for a in sem if set(a["termes"]) & contexte["fait_passe"]) / n, 3)
    fin = (w0 + timedelta(weeks=HORIZON + 1)).isoformat()
    x["echeance"] = 1.0 if any(d1 < j <= fin for j in contexte.get("elections", {}).get(pays, [])) else 0.0
    return x


def lire_poids() -> dict:
    p = json.loads(POIDS.read_text(encoding="utf-8")) if POIDS.exists() else {}
    p.setdefault("poids", {k: POIDS_DEPART for k in MODULES})
    for k in MODULES:
        p["poids"].setdefault(k, POIDS_DEPART)
    p.setdefault("appris_sur", [])
    return p


def apprendre(etat: dict, journal: list[dict], issues: list[dict]) -> int:
    """La boucle : chaque issue constatée corrige les poids une fois (gradient de la perte logistique), dans l'ordre
    des constats. Les poids restent positifs : le SENS est fixé par l'auteur, seule la FORCE s'apprend."""
    par_id = {r["id"]: r for r in journal}
    faits, n = set(etat["appris_sur"]), 0
    for i in issues:
        r = par_id.get(i["id"])
        if not r or i["id"] in faits:
            continue
        x = json.loads(r.get("modules") or "{}")
        if not x:
            faits.add(i["id"])
            continue
        p = predire(x, etat["poids"])
        y = int(i["prend"])
        for k, v in x.items():
            if k in etat["poids"]:
                etat["poids"][k] = max(0.0, etat["poids"][k] + APPRENTISSAGE * (y - p) * v)
        faits.add(i["id"])
        n += 1
    etat["appris_sur"] = sorted(faits)
    return n


def predire(x: dict[str, float], poids: dict[str, float]) -> float:
    z = logit(TAUX_DEPART) + sum(poids.get(k, 0.0) * v for k, v in x.items())
    return sigmo(z)


def inscrire(series: dict, journal: list[dict], aujourd_hui: date, contexte: dict | None = None) -> list[dict]:
    """Étincelles de la DERNIÈRE semaine complète seulement (aucune semaine de la fenêtre de 8 semaines n'est connue au
    moment de la prédiction ; une semaine manquée n'est pas rattrapée, pour ne pas prédire ce qu'on voit déjà)."""
    deja = {(r["pays"], r["semaine"]) for r in journal}
    poids = lire_poids()["poids"]
    iso = codes_iso3()
    cible = (aujourd_hui - timedelta(days=aujourd_hui.weekday()) - timedelta(weeks=1)).isoformat()
    neuves = []
    for p, l in sorted(series.items()):
        for i, (s, _) in enumerate(l):
            if s != cible or (p, s) in deja:
                continue
            e = etincelle(l, i)
            if not e:
                continue
            x = modules(p, s, contexte or {})
            neuves.append({"id": f"{p}-{s}", "inscrit_le": aujourd_hui.isoformat(), "pays": p, "iso3": iso.get(p, ""),
                           "semaine": s, "part": "%.5f" % e[0], "niveau_habituel": "%.5f" % e[1],
                           "rapport": "%.2f" % (e[0] / e[1]), "p_prend": "%.4f" % predire(x, poids),
                           "version": VERSION, "modules": json.dumps(x, ensure_ascii=False)})
    return neuves


def constater(series: dict, journal: list[dict], issues: list[dict], aujourd_hui: date) -> list[dict]:
    """Issues des étincelles dont les 8 semaines suivantes sont complètes ; une issue n'est jamais réécrite."""
    fait = {r["id"] for r in issues}
    neuves = []
    for r in journal:
        if r["id"] in fait or r["pays"] not in series:
            continue
        l = series[r["pays"]]
        idx = {s: k for k, (s, _) in enumerate(l)}
        i = idx.get(r["semaine"])
        lundi = aujourd_hui - timedelta(days=aujourd_hui.weekday())
        if i is None or i + HORIZON >= len(l) or date.fromisoformat(l[i + HORIZON][0]) + timedelta(days=7) > lundi:
            continue                                        # les 8 semaines suivantes ne sont pas toutes complètes
        b = float(r["niveau_habituel"])
        nxt = [w for _, w in l[i + 1:i + 1 + HORIZON]]
        elev = sum(1 for w in nxt if w is not None and w >= SEUIL_ELEVE * b)
        neuves.append({"id": r["id"], "constate_le": aujourd_hui.isoformat(), "prend": int(elev >= PREND_MIN),
                       "semaines_elevees": elev})
    return neuves


def e_valeur(journal: list[dict], issues: list[dict]) -> dict:
    """Pour chaque issue constatée, dans l'ordre des constats : d = Brier(taux de départ) − Brier(mécanique), dans
    [−1, 1]. Hypothèse nulle : la mécanique ne fait pas mieux (moyenne conditionnelle de d ≤ 0). Richesse
    K = Π(1 + λ·d), avec une mise λ ∈ [0, 0,5] fixée d'après les seules issues précédentes (prévisible) ; sous
    l'hypothèse nulle, la probabilité que K atteigne un jour 1/α est au plus α (inégalité de Ville). Les étincelles
    sans mécanisme (p = taux de départ) donnent d = 0 et ne changent rien."""
    p = {r["id"]: float(r["p_prend"]) for r in journal}
    ordre = sorted((r for r in issues if r["id"] in p), key=lambda r: (r["constate_le"], r["id"]))
    k, kmax, franchi, vus = 1.0, 1.0, "", []
    for r in ordre:
        y = int(r["prend"])
        d = (TAUX_DEPART - y) ** 2 - (p[r["id"]] - y) ** 2
        if vus:
            m = sum(vus) / len(vus)
            v = sum((x - m) ** 2 for x in vus) / len(vus)
            lam = min(E_MISE_MAX, max(0.0, m / (v + m * m))) if (v + m * m) > 0 else 0.0
        else:
            lam = 0.0
        k *= 1 + lam * d
        vus.append(d)
        if k > kmax:
            kmax = k
        if not franchi and k >= E_SEUIL:
            franchi = r["constate_le"]
    return {"e_valeur": round(k, 3), "e_max": round(kmax, 3), "e_seuil": E_SEUIL, "e_franchi_le": franchi,
            "e_comparees": len(ordre)}


TRANCHES = ((0.0, 0.25), (0.25, 0.35), (0.35, 0.5), (0.5, 1.01))


def controles(journal: list[dict], issues: list[dict]) -> dict:
    """Trois contrôles du modèle (veille Munshi, ch. 36-37), calculés sur les issues constatées.
    - calibration : par tranche de probabilité annoncée, la part qui a réellement pris ;
    - sous-ensembles : par région (ONU) et par moitié de période, la part qui a pris, la part annoncée, le Brier de la
      mécanique et celui du taux de départ ; un écart qui change de signe d'un sous-ensemble à l'autre signale un cadre à
      déplacer plutôt qu'un mécanisme reproductible ;
    - résidus : les surprises (a pris alors qu'on annonçait moins de 25 %, s'est éteinte alors qu'on annonçait plus de
      60 %), comptées par région ; un regroupement désigne un mécanisme manquant.
    Aucun de ces contrôles ne décide de rien : ils s'affichent."""
    region = {r["fips"]: r.get("region") or "?" for r in codes_complets()}
    par_id = {r["id"]: r for r in journal}
    cas = []
    for i in sorted(issues, key=lambda r: (r["constate_le"], r["id"])):
        r = par_id.get(i["id"])
        if r:
            cas.append({"p": float(r["p_prend"]), "y": int(i["prend"]), "region": region.get(r["pays"], "?"),
                        "semaine": r["semaine"], "id": r["id"]})
    out = {"calibration": [], "sous_ensembles": {}, "surprises": {"nombre": 0, "par_region": {}, "liste": []}}
    if not cas:
        return out
    for a, b in TRANCHES:
        t = [c for c in cas if a <= c["p"] < b]
        if t:
            out["calibration"].append({"tranche": f"{round(a * 100)}-{min(100, round(b * 100))} %", "n": len(t),
                                       "annoncee": round(sum(c["p"] for c in t) / len(t), 3),
                                       "observee": round(sum(c["y"] for c in t) / len(t), 3)})

    def bloc(t):
        return {"n": len(t), "annoncee": round(sum(c["p"] for c in t) / len(t), 3),
                "observee": round(sum(c["y"] for c in t) / len(t), 3),
                "brier": round(sum((c["p"] - c["y"]) ** 2 for c in t) / len(t), 4),
                "brier_taux_depart": round(sum((TAUX_DEPART - c["y"]) ** 2 for c in t) / len(t), 4)}
    regs = {}
    for c in cas:
        regs.setdefault(c["region"], []).append(c)
    out["sous_ensembles"]["regions"] = {k: bloc(v) for k, v in sorted(regs.items())}
    sem = sorted({c["semaine"] for c in cas})
    if len(sem) >= 2:
        mi = sem[len(sem) // 2]
        out["sous_ensembles"]["periodes"] = {f"avant le {mi}": bloc([c for c in cas if c["semaine"] < mi]),
                                             f"à partir du {mi}": bloc([c for c in cas if c["semaine"] >= mi])}
    sur = [c for c in cas if (c["y"] == 1 and c["p"] < 0.25) or (c["y"] == 0 and c["p"] > 0.6)]
    out["surprises"]["nombre"] = len(sur)
    for c in sur:
        out["surprises"]["par_region"][c["region"]] = out["surprises"]["par_region"].get(c["region"], 0) + 1
    out["surprises"]["liste"] = [{"id": c["id"], "p": c["p"], "prend": c["y"]} for c in sur[-20:]]
    return out


def score(journal: list[dict], issues: list[dict]) -> dict:
    p = {r["id"]: float(r["p_prend"]) for r in journal}
    res = [(p[r["id"]], int(r["prend"])) for r in issues if r["id"] in p]
    out = {"calcule_le": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"), "inscrites": len(journal),
           "constatees": len(res), "ouvertes": len(journal) - len(res), "taux_depart": TAUX_DEPART}
    if res:
        out["brier"] = round(sum((q - y) ** 2 for q, y in res) / len(res), 4)
        out["brier_taux_depart"] = round(sum((TAUX_DEPART - y) ** 2 for _, y in res) / len(res), 4)
        out["part_prend"] = round(sum(y for _, y in res) / len(res), 3)
    out.update(e_valeur(journal, issues))
    out["controles"] = controles(journal, issues)
    return out


def principal() -> int:
    src = RECENTES if RECENTES.exists() else COMPLET
    if not src.exists():
        print("::warning::mécanique : aucun relevé GDELT des manifestations ; rien à faire.")
        return 0
    series = lire_series(src)
    auj = date.today()
    journal = lire_csv(JOURNAL)
    contexte = charger_contexte()
    print(f"contexte : {sum(len(v) for v in contexte['articles'].values())} rattachements article-pays ; "
          f"{len(contexte['elections'])} pays avec élections ; {len(contexte['acte'])} termes d'acte, "
          f"{len(contexte['fait_passe'])} termes de fait passé", flush=True)
    neuves = inscrire(series, journal, auj, contexte)
    ajouter(JOURNAL, COLS_JOURNAL, neuves)
    journal += neuves
    issues = lire_csv(ISSUES)
    constats = constater(series, journal, issues, auj)
    ajouter(ISSUES, COLS_ISSUES, constats)
    issues += constats
    etat = lire_poids()
    appris = apprendre(etat, journal, issues)
    POIDS.write_text(json.dumps(etat, ensure_ascii=False, indent=1), encoding="utf-8")
    sc = score(journal, issues)
    sc["poids"] = etat["poids"]
    sc["appris_ce_passage"] = appris
    SCORE.write_text(json.dumps(sc, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"mécanique : source {src.name} ; {len(neuves)} étincelle(s) inscrite(s), {len(constats)} issue(s) constatée(s) ; "
          f"{sc}")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
