"""Banc du contexte physique : prévision météo pour les températures Météo-France (0.10.135, décision d'auteur du
2026-11-15 : une série sans son contexte ne donne rien). AUCUN modèle de langue, aucun coût.

Questions DBnomics « la température moyenne du jour à la station … sera-t-elle plus haute à D+7 qu'à D ? ». B :
comptage des hausses sur 5 ans (code du banc). B météo : la prévision archivée d'Open-Meteo émise avant la date, avec
son échéance (Previous Runs API). Règle et critère : preenregistrements/contexte-meteo.md.
Registre : registre/banc-meteo.jsonl ; résumé : registre/banc-meteo.json.

    python banc_meteo.py [--max 400]
"""
from __future__ import annotations

import argparse
import asyncio
import json
import math
import re
import sys
from datetime import date, timedelta
from pathlib import Path

import httpx

import alphabet_pipeline as ap
import banc_a as ba
import banc_forecastbench as fb

REGISTRE = Path("registre")
FICHIER = REGISTRE / "banc-meteo.jsonl"
RESUME = REGISTRE / "banc-meteo.json"
SIGMA = 2.7
MOTIF = "daily average temperature at the French weather station at"
FRANCE = {"FR", "RE", "MQ", "GF", "GP", "YT", "BL", "MF", "PM", "NC", "PF", "WF", "TF"}
UA = {"User-Agent": "alphabet-situationnel-bot/1.0 (recherche ; GitHub Othman-Benbrahim)"}


def station(titre: str) -> str | None:
    m = re.search(r"weather station at (.+?) will be higher", titre)
    return m.group(1).strip() if m else None


def nom_a_geocoder(st: str) -> str:
    n = re.split(r"\s[–-]\s|–", st)[0]
    n = re.sub(r"\b(Airport|Aerodrome|Air Base|Aéroport|Base aérienne)\b", "", n, flags=re.I)
    return re.sub(r"\s+", " ", n).strip(" -–")


def phi(x: float) -> float:
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def p_meteo(t_d: float, t_d7: float, sigma: float = SIGMA) -> float:
    return min(0.99, max(0.01, phi((t_d7 - t_d) / sigma)))


def moyenne_jour(heures: list[str], valeurs: list, jour: date) -> float | None:
    vs = [v for h, v in zip(heures, valeurs) if h.startswith(jour.isoformat()) and v is not None]
    return sum(vs) / len(vs) if len(vs) >= 20 else None


async def coordonnees(c: httpx.AsyncClient, st: str, cache: dict) -> tuple | None:
    if st in cache:
        return cache[st]
    r = None
    try:
        g = await c.get("https://geocoding-api.open-meteo.com/v1/search",
                        params={"name": nom_a_geocoder(st), "count": 10, "language": "fr", "format": "json"})
        # 0.10.139 : la France d'outre-mer a ses propres codes pays (La Réunion, Martinique, Guyane…)
        res = [x for x in (g.json().get("results") or []) if x.get("country_code") in FRANCE]
        if res:
            r = (res[0]["latitude"], res[0]["longitude"])
    except Exception:
        r = None
    cache[st] = r
    return r


async def prevision(c: httpx.AsyncClient, lat: float, lon: float, d0: date) -> dict | None:
    d7 = d0 + timedelta(days=7)
    try:
        r = await c.get("https://previous-runs-api.open-meteo.com/v1/forecast",
                        params={"latitude": lat, "longitude": lon, "start_date": d0.isoformat(), "end_date": d7.isoformat(),
                                "hourly": "temperature_2m_previous_day1,temperature_2m_previous_day7", "timezone": "Europe/Paris"})
        j = r.json()
    except Exception as e:
        return {"erreur": f"{type(e).__name__}: {e}"[:200]}
    h = (j.get("hourly") or {})
    t = h.get("time") or []
    t_d = moyenne_jour(t, h.get("temperature_2m_previous_day1") or [], d0)
    t_d7 = moyenne_jour(t, h.get("temperature_2m_previous_day7") or [], d7)
    if t_d is None or t_d7 is None:
        return {"erreur": "prévision manquante", "raison_api": str(j.get("reason", ""))[:200]}
    return {"t_d_prevue": round(t_d, 2), "t_d7_prevue": round(t_d7, 2), "p": p_meteo(t_d, t_d7)}


MODELES_V2 = ("gfs_global", "ecmwf_ifs025", "icon_global", "gem_global", "meteofrance_arpege_world")
JEU_V2 = "2026-09-27"          # seconde version jugée sur les jeux postérieurs seulement


def p_meteo2(deltas: list[float], sigma0: float = SIGMA) -> float | None:
    if len(deltas) < 3:
        return None
    d = sum(deltas) / len(deltas)
    s = (sum((x - d) ** 2 for x in deltas) / (len(deltas) - 1)) ** 0.5
    return min(0.99, max(0.01, phi(d / math.sqrt(sigma0 ** 2 + s ** 2))))


async def prevision2(c: httpx.AsyncClient, lat: float, lon: float, d0: date) -> dict:
    """Seconde version (preenregistrements/contexte-meteo.md) : cinq modèles, même échéance (7 jours), σ selon le désaccord."""
    d7 = d0 + timedelta(days=7)
    try:
        r = await c.get("https://previous-runs-api.open-meteo.com/v1/forecast",
                        params={"latitude": lat, "longitude": lon, "start_date": d0.isoformat(), "end_date": d7.isoformat(),
                                "hourly": "temperature_2m_previous_day7", "models": ",".join(MODELES_V2),
                                "timezone": "Europe/Paris"})
        h = (r.json().get("hourly") or {})
    except Exception as e:
        return {"erreur": f"{type(e).__name__}: {e}"[:200]}
    t = h.get("time") or []
    deltas = {}
    for m in MODELES_V2:
        v = h.get(f"temperature_2m_previous_day7_{m}") or []
        a, b = moyenne_jour(t, v, d0), moyenne_jour(t, v, d7)
        if a is not None and b is not None:
            deltas[m] = round(b - a, 2)
    p = p_meteo2(list(deltas.values()))
    if p is None:
        return {"erreur": f"{len(deltas)} modèle(s) disponible(s)", "deltas": deltas}
    return {"p": p, "deltas": deltas}


def lignes() -> list[dict]:
    if not FICHIER.exists():
        return []
    return [json.loads(l) for l in FICHIER.read_text(encoding="utf-8").splitlines() if l.strip()]


def resumer(ls: list[dict]) -> dict:
    import audit_b
    import score_registre as sr
    pl = sr.log_score
    vu: dict[str, dict] = {}
    for x in ls:                                  # dernière tentative de chaque question
        vu[x["question_id"]] = x
    ls = list(vu.values())
    ok = sorted((x for x in ls if x.get("issue") in (0, 1) and x.get("p_B") is not None
                 and isinstance(x.get("ombre_b_meteo"), dict) and x["ombre_b_meteo"].get("p") is not None),
                key=lambda x: x["ordre"])
    moy = lambda f: round(sum(pl(f(x), x["issue"]) for x in ok) / len(ok), 4) if ok else None
    return {"version_bot": ap.VERSION_BOT, "questions": len(ls), "appliquees": len(ok),
            "note": "perte log, plus bas = mieux ; pile ou face = 0,693 ; aucun modèle de langue",
            "B": moy(lambda x: x["p_B"]), "B_meteo": moy(lambda x: x["ombre_b_meteo"]["p"]),
            "bon_sens": round(sum((x["ombre_b_meteo"]["p"] > 0.5) == (x["issue"] == 1) for x in ok) / len(ok), 3) if ok else None,
            "critere": sr.critere_ombre_b(ok, "ombre_b_meteo", "contexte_meteo", exclure_vus=False),
            "v2": resumer_v2(ls),
            "audit_b": audit_b.pour_resume(ls)}


DEBUT_CONSTRUITES = date(2026, 10, 4)


def station_du_jour(d: date, codes: list[str]) -> str:
    import hashlib
    return sorted(codes)[int(hashlib.sha1(d.isoformat().encode()).hexdigest(), 16) % len(codes)]


async def horaires_v2(c: httpx.AsyncClient, lat: float, lon: float, debut: date, fin: date) -> dict:
    try:
        r = await c.get("https://previous-runs-api.open-meteo.com/v1/forecast",
                        params={"latitude": lat, "longitude": lon, "start_date": debut.isoformat(), "end_date": fin.isoformat(),
                                "hourly": "temperature_2m_previous_day7", "models": ",".join(MODELES_V2),
                                "timezone": "Europe/Paris"})
        return r.json().get("hourly") or {}
    except Exception:
        return {}


def v2_depuis_horaires(h: dict, d0: date) -> dict:
    t = h.get("time") or []
    deltas = {}
    for m in MODELES_V2:
        v = h.get(f"temperature_2m_previous_day7_{m}") or []
        a, b = moyenne_jour(t, v, d0), moyenne_jour(t, v, d0 + timedelta(days=7))
        if a is not None and b is not None:
            deltas[m] = round(b - a, 2)
    p = p_meteo2(list(deltas.values()))
    return {"p": p, "deltas": deltas} if p is not None else {"erreur": f"{len(deltas)} modèle(s)", "deltas": deltas}


async def questions_construites(c: httpx.AsyncClient, f) -> int:
    """Amendement du 2026-11-15 (17 h 50, preenregistrements/contexte-meteo.md) : une station par date, dates ≥ 2026-10-04."""
    import alphabet_puits as apz
    stations = {}
    for x in lignes():
        q = x.get("question_id", "")
        if x.get("coordonnees") and "meteofrance_TEMPERATURE_celsius." in q:
            code = q.split(":")[3]                          # ex. meteofrance_TEMPERATURE_celsius.07005.D
            stations[code] = {"station": x.get("station"), "coordonnees": x["coordonnees"],
                              "chemin": code.replace("meteofrance_TEMPERATURE_", "meteofrance/TEMPERATURE/")}
    if not stations:
        print("Questions construites : aucune station connue.")
        return 0
    deja = {x["question_id"] for x in lignes() if x.get("type") == "meteo_construite"}
    fin = date.today() - timedelta(days=8)
    jours = [DEBUT_CONSTRUITES + timedelta(days=i) for i in range((fin - DEBUT_CONSTRUITES).days + 1)]
    choix = {d: station_du_jour(d, list(stations)) for d in jours}
    series, horaires, faites = {}, {}, 0
    for d in jours:
        code = choix[d]
        qid = f"construite:{d.isoformat()}:{code}"
        if qid in deja:
            continue
        st = stations[code]
        if code not in series:
            try:
                r = await apz.dbnomics(st["chemin"])
                series[code] = {p_["date"][:10]: float(p_["valeur"]) for p_ in r.get("points") or []
                                if p_.get("valeur") is not None}, r.get("points") or []
            except Exception as e:
                series[code] = ({}, [])
        valeurs, points = series[code]
        v0, v7 = valeurs.get(d.isoformat()), valeurs.get((d + timedelta(days=7)).isoformat())
        if v0 is None or v7 is None:
            continue
        b = fb.b_hausse(points, 7, d)
        if not b:
            continue
        if code not in horaires:
            lat, lon = st["coordonnees"]
            horaires[code] = await horaires_v2(c, lat, lon, DEBUT_CONSTRUITES, fin + timedelta(days=7))
        semaine = d - timedelta(days=d.weekday())
        ligne = {"type": "meteo_construite", "jeu": semaine.isoformat(), "date_question": d.isoformat(),
                 "ordre": [10 ** 6 + d.toordinal(), d.isoformat()], "source_question": "dbnomics", "question_id": qid,
                 "version_bot": ap.VERSION_BOT, "station": st["station"], "coordonnees": st["coordonnees"],
                 "titre": f"Température moyenne à {st['station']} plus haute le {d + timedelta(days=7)} que le {d} ? (construite)",
                 "issue": int(v7 > v0), "p_B": b[0], "ombre_b_meteo2": v2_depuis_horaires(horaires[code], d),
                 "licence": "Météo-France via DBnomics ; prévisions Open-Meteo, CC BY 4.0"}
        f.write(json.dumps(ligne, ensure_ascii=False) + "\n")
        f.flush()
        faites += 1
        print(f"construite {d} {st['station'][:24]:24s} : B {b[0]:.3f} · v2 {ligne['ombre_b_meteo2'].get('p')} · issue {ligne['issue']}")
    return faites


def resumer_v2(ls: list[dict]) -> dict:
    import score_registre as sr
    pl = sr.log_score
    ok = sorted((x for x in ls if x.get("issue") in (0, 1) and x.get("p_B") is not None and x["jeu"] > JEU_V2
                 and isinstance(x.get("ombre_b_meteo2"), dict) and x["ombre_b_meteo2"].get("p") is not None),
                key=lambda x: x["ordre"])
    if not ok:
        return {"n": 0, "note": f"jugée sur les jeux postérieurs au {JEU_V2} seulement"}
    moy = lambda f: round(sum(pl(f(x), x["issue"]) for x in ok) / len(ok), 4)
    v1 = [x for x in ok if (x.get("ombre_b_meteo") or {}).get("p") is not None]
    return {"n": len(ok), "B": moy(lambda x: x["p_B"]), "B_meteo2": moy(lambda x: x["ombre_b_meteo2"]["p"]),
            "B_meteo1_memes_questions": round(sum(pl(x["ombre_b_meteo"]["p"], x["issue"]) for x in v1) / len(v1), 4) if v1 else None,
            "critere": sr.critere_ombre_b(ok, "ombre_b_meteo2", "contexte_meteo_v2", exclure_vus=False)}


async def principal(apres: str, max_q: int) -> int:
    async with httpx.AsyncClient(timeout=30, follow_redirects=True, headers=UA) as c:
        test = await prevision(c, 48.85, 2.35, date(2026, 7, 5))      # vérification au démarrage
        if not test or "p" not in test:
            print(f"Prévisions archivées indisponibles : {test}. Rien n'est lancé.")
            return 1
        print(f"Open-Meteo (prévisions archivées) joignable ; essai Paris 2026-07-05 : {test}")
        # 0.10.139 : une question dont la prévision a échoué (station non géocodée, délai) est retentée
        deja = {x["question_id"] for x in lignes() if (x.get("ombre_b_meteo") or {}).get("p") is not None}
        jeux = sorted(fb.jeux_candidats(date.today(), date.fromisoformat(apres), n_max=26))
        tous = []
        for j in jeux:
            try:
                qs = await fb._json(f"{fb.DEPOT}/question_sets/{j}-llm.json")
                rs = await fb._json(f"{fb.DEPOT}/resolution_sets/{j}_resolution_set.json")
            except Exception as e:
                print(f"Jeu {j} indisponible : {type(e).__name__}")
                continue
            items = [fb.construire(i, j) for i in fb.apparier(qs, rs, ("dbnomics",))]
            items = sorted((x for x in items if MOTIF in x["titre"]
                            and (date.fromisoformat(x["resolution"]) - date.fromisoformat(j)).days == 7),
                           key=lambda x: ba.rang(x["qid"]))
            tous += [(r, j, x) for r, x in enumerate(items)]
        tous.sort(key=lambda t: (t[0], t[1]))
        print(f"{len(tous)} questions de température à 7 jours, entrelacées.")
        REGISTRE.mkdir(exist_ok=True)
        cache, faites = {}, 0
        with FICHIER.open("a", encoding="utf-8") as f:
            for r_, j, x in tous:
                if faites >= max_q:
                    break
                if x["qid"] in deja:
                    continue
                try:
                    vue = await fb.vue_calculee(x, x["_q"], j)
                except Exception:
                    vue = None
                st = station(x["titre"])
                co = await coordonnees(c, st, cache) if st else None
                me = await prevision(c, co[0], co[1], date.fromisoformat(j)) if co else {"erreur": "station non géocodée"}
                me2 = await prevision2(c, co[0], co[1], date.fromisoformat(j)) if co else {"erreur": "station non géocodée"}
                ligne = {"type": "banc_meteo", "jeu": j, "ordre": [r_, j], "source_question": "dbnomics",
                         "question_id": x["qid"], "version_bot": ap.VERSION_BOT, "titre": x["titre"], "issue": x["issue"],
                         "station": st, "coordonnees": co, "p_B": (vue or {}).get("frequence"), "ombre_b_meteo": me, "ombre_b_meteo2": me2,
                         "licence": "ForecastBench, Forecasting Research Institute, CC BY-SA 4.0 ; prévisions Open-Meteo, CC BY 4.0"}
                f.write(json.dumps(ligne, ensure_ascii=False) + "\n")
                f.flush()
                deja.add(x["qid"])
                faites += 1
                print(f"{(st or '?')[:28]:28s} {j} : B {ligne['p_B']} · météo {(me or {}).get('p')} · issue {x['issue']}")
        with FICHIER.open("a", encoding="utf-8") as f:
            n_c = await questions_construites(c, f)
        print(f"{n_c} question(s) construite(s) ajoutée(s).")
    r = resumer(lignes())
    RESUME.write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{faites} question(s) ajoutée(s).")
    print(json.dumps(r, ensure_ascii=False, indent=1)[:2500])
    return 0


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("--apres", default="2026-07-01")
    a.add_argument("--max", type=int, default=400)
    o = a.parse_args()
    sys.exit(asyncio.run(principal(o.apres, o.max)))
