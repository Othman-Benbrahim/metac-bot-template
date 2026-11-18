"""Variantes de M sur les questions de jugement, et réplique sur un second modèle (bot 0.10.254).

Décisions d'auteur du 2026-11-18 : 5 h 55 (explorer les autres angles morts, en dépensant le moins possible, avant la
fin des crédits Bedrock le 23) ; 6 h 09 (garder gpt-5-mini pour les tests comparables, trouver un usage aux crédits
Bedrock) ; 6 h 13 (Claude Haiku 4.5 sur Bedrock, pas un modèle gourmand).
Préenregistrement : preenregistrements/jugement-variantes.md (écrit avant le premier passage).

Mêmes questions que le banc jugement_alphabet (les 309 valides, dans le même ordre fixé par empreinte), une recherche
bornée avant la date du jeu par question, partagée par tous les bras. Les notes des cartes de gpt-5-mini sont reprises
du banc (registre/banc-jugement-alphabet.jsonl) : on ne repaye pas ce qui est déjà acquis.
  gpt-5-mini (Azure) :
    M_refait : le jugement final de M refait sur la recherche de ce passage (référence appariée) ;
    M_avocat : un appel « avocat du OUI » (le chemin le plus plausible vers OUI, et sa solidité), puis le jugement
               final qui le voit ; vise les « oui » surprenants (22 des 50 « oui » mis à 23 % ou moins par M) ;
    M_neutre : le jugement final posé en deux issues symétriques (« critères remplis » / « non remplis »), dans un
               ordre tiré par empreinte, au lieu d'une question oui/non (biais d'acquiescement inversé).
  Claude Haiku 4.5 (Bedrock, crédits jusqu'au 23) : A, les sept notes, M, et M_avocat (réplique du banc sur un
    second lecteur ; examen des cartes sur ce lecteur).
La prévision de la communauté n'est jamais lue ni transmise.

    python banc_jugement_variantes.py --n 150 --budget 3 --budget-bedrock 15
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import alphabet_modeles as am
import alphabet_pipeline as ap
import alphabet_retro as ar
import trace_recherche as tr
import banc_forecastbench as fb
import banc_jugement_alphabet as bja
import garde_injection as gi

REGISTRE = Path("registre")
FICHIER = REGISTRE / "banc-jugement-variantes.jsonl"
RESUME = REGISTRE / "banc-jugement-variantes.json"
GPT = "azure_ai/gpt-5-mini"
HAIKU = "bedrock/global.anthropic.claude-haiku-4-5-20251001-v1:0"


def consigne_avocat(q: dict, p_b: float, notes: dict, recherche: str, jeu: str) -> str:
    lignes = "\n".join(f"- {carte} ({k}) : {notes[k]['note']}/4" for k, carte, _ in bja.CRITERES if k in notes)
    return f"""Nous sommes le {jeu}. Tu es l'AVOCAT DU OUI dans un comité de prévision. Les questions de ce genre se
résolvent le plus souvent NON (le statu quo l'emporte) ; ton rôle est de chercher honnêtement comment elle pourrait
quand même se résoudre OUI avant l'échéance. Tu ne donnes pas de probabilité.

{bja._entete(q, p_b, jeu)}

NOTES DU COMITÉ (1 à 4) :
{lignes}

RÉSULTATS DE RECHERCHE (antérieurs au {jeu}) :
{gi.bloc(recherche, 5000)}

Décris le chemin le plus plausible vers OUI : qui agirait, par quel événement (vote, décision, annonce, échéance
prévue), et quels signes de ce chemin sont DÉJÀ visibles dans les recherches. Puis note sa solidité :
1 = invraisemblable, aucun signe ; 2 = possible mais spéculatif ; 3 = des signes concrets ; 4 = déjà en cours.
Rends UNIQUEMENT un objet JSON : {{"chemin": "deux phrases", "signes": "une phrase (ou « aucun »)", "solidite": 1-4}}"""


def consigne_finale_avocat(q: dict, p_b: float, notes: dict, avocat: dict, recherche: str, jeu: str) -> str:
    base = bja.consigne_finale(q, p_b, notes, recherche, jeu)
    ajout = (f"\n\nL'AVOCAT DU OUI a cherché le chemin le plus plausible vers OUI :\n- chemin : {avocat.get('chemin', '')}\n"
             f"- signes déjà visibles : {avocat.get('signes', '')}\n- solidité : {avocat.get('solidite', '?')}/4\n"
             "Tiens-en compte s'il s'appuie sur des signes concrets ; s'il est spéculatif, ne t'écarte pas pour lui.")
    i = base.rfind("Rends UNIQUEMENT")
    return base[:i] + ajout.strip() + "\n\n" + base[i:]


def ordre_neutre(qid: str) -> bool:
    """True : l'issue « critères remplis » est présentée en premier (moitié des questions, fixé par empreinte)."""
    return int(hashlib.sha1(f"neutre:{qid}".encode()).hexdigest(), 16) % 2 == 0


def consigne_neutre(q: dict, p_b: float, notes: dict, recherche: str, jeu: str, remplie_d_abord: bool) -> str:
    lignes = "\n".join(f"- {carte} ({k}) : {notes[k]['note']}/4 — {notes[k].get('pourquoi', '')}"
                       for k, carte, _ in bja.CRITERES if k in notes)
    r = "ISSUE R : à l'échéance, les critères de résolution sont REMPLIS."
    n = "ISSUE N : à l'échéance, les critères de résolution ne sont PAS remplis."
    i1, i2 = (r, n) if remplie_d_abord else (n, r)
    return f"""Tu es un prévisionniste. Nous sommes le {jeu}. Deux issues sont possibles, et une seule se produira :
{i1}
{i2}

{bja._entete(q, p_b, jeu)}

LE COMITÉ A NOTÉ SÉPARÉMENT CES SITUATIONS (1 à 4 ; pour « freins », 4 = obstacles forts) :
{lignes}

RÉSULTATS DE RECHERCHE (antérieurs au {jeu}) :
{gi.bloc(recherche, 4000)}

Pars du taux de base. Répartis la probabilité entre les deux issues ; les deux nombres somment à 1.
Rends UNIQUEMENT un objet JSON : {{"R": nombre entre 0,01 et 0,99, "N": nombre entre 0,01 et 0,99, "raison": "une phrase"}}"""


def lire_neutre(r: dict) -> float:
    pr, pn = float(r["R"]), float(r.get("N", 1 - float(r["R"])))
    s = pr + pn
    return min(0.99, max(0.01, pr / s if s > 0 else pr))


def borne(p) -> float:
    return min(0.99, max(0.01, float(p)))


def base_banc() -> dict[str, dict]:
    """Les lignes valides du banc jugement_alphabet (notes et M de gpt-5-mini), une par question."""
    out = {}
    for x in bja.lignes():
        if x.get("exclue") or x.get("p_A") is None or x.get("p_M") is None or x.get("issue") not in (0, 1):
            continue
        out.setdefault(x["question_id"], x)
    return out


def lignes() -> list[dict]:
    if not FICHIER.exists():
        return []
    return [json.loads(l) for l in FICHIER.read_text(encoding="utf-8").splitlines() if l.strip()]


def resumer(ls: list[dict]) -> dict:
    import psychometrie_alphabet as ps
    import score_registre as sr
    pl = sr.log_score
    out = {"version_bot": ap.VERSION_BOT, "n_lignes": len(ls), "note": "perte log, plus bas = mieux"}

    def comparer(xs, ref, var, essai):
        ok = [x for x in xs if x.get(ref) is not None and x.get(var) is not None]
        if not ok:
            return {"n": 0}
        n = len(ok)
        return {"n": n, ref: round(sum(pl(x[ref], x["issue"]) for x in ok) / n, 4),
                var: round(sum(pl(x[var], x["issue"]) for x in ok) / n, 4),
                "critere": sr.critere_ombre_b([dict(x, p_B=x[ref], o={"p": x[var]}) for x in ok], "o", essai,
                                              exclure_vus=False, bloc_par="question")}
    out["gpt_avocat_oui"] = comparer(ls, "p_M_refait", "p_M_avocat", "avocat_oui")
    out["gpt_formulation_neutre"] = comparer(ls, "p_M_refait", "p_M_neutre", "formulation_neutre")
    out["haiku_replique_M_contre_A"] = comparer([dict(x, **{"hA": x.get("haiku", {}).get("p_A"),
                                                             "hM": x.get("haiku", {}).get("p_M")}) for x in ls],
                                                "hA", "hM", "replique_haiku")
    h = [dict(x, hM=x.get("haiku", {}).get("p_M"), hMav=x.get("haiku", {}).get("p_M_avocat")) for x in ls]
    ok = [x for x in h if x["hM"] is not None and x["hMav"] is not None]
    if ok:
        out["haiku_avocat_descriptif"] = {"n": len(ok), "M": round(sum(pl(x["hM"], x["issue"]) for x in ok) / len(ok), 4),
                                          "M_avocat": round(sum(pl(x["hMav"], x["issue"]) for x in ok) / len(ok), 4)}
    import profil_erreurs as pe          # 0.10.265 : les deux côtés des erreurs, toujours affichés
    out["unites"] = pe.unites(ls)
    out["profils_gpt"] = pe.profils(ls, {"M_refait": "p_M_refait", "M_avocat": "p_M_avocat", "M_neutre": "p_M_neutre"})
    out["profils_haiku"] = pe.profils([dict(x, hA=x.get("haiku", {}).get("p_A"), hM=x.get("haiku", {}).get("p_M"),
                                            hMav=x.get("haiku", {}).get("p_M_avocat")) for x in ls
                                       if not (x.get("haiku") or {}).get("exclue")],
                                      {"A": "hA", "M": "hM", "M_avocat": "hMav"})
    # « oui » surprenants : combien de « oui » chaque bras met à 23 % ou moins (descriptif ; ne jamais juger sur ce
    # seul côté : voir profils, qui montrent aussi les fausses alertes)
    oui = [x for x in ls if x["issue"] == 1]
    out["oui_mis_bas"] = {k: sum(1 for x in oui if x.get(k) is not None and x[k] <= 0.23)
                          for k in ("p_M_refait", "p_M_avocat", "p_M_neutre")}
    out["oui_mis_bas"]["n_oui"] = len(oui)
    notes_h = [{"question_id": x["question_id"], "issue": x["issue"], "forme": x.get("forme", "autre"),
                "notes": x["haiku"]["notes"]}
               for x in ls if (x.get("haiku") or {}).get("notes") and not x["haiku"].get("exclue")]
    if len(notes_h) >= 30:
        out["cartes_haiku"] = ps.examiner(notes_h)
    return out


async def appeler(modele: str, consigne: str) -> dict:
    return ap.extraire_json(await am.llm(modele, temperature=0.2, timeout=300, allowed_tries=2).invoke(consigne))


async def principal(n: int, budget: float, budget_bedrock: float) -> int:
    from forecasting_tools import MonetaryCostManager
    if not ar.recherche_bornee_disponible():
        print("Il faut une recherche bornable dans le temps (EXA_API_KEY ou TINYFISH_API_KEY). Rien n'est lancé.")
        return 1
    base = base_banc()
    deja = {x["question_id"] for x in lignes()}
    cand = [x for x in bja.candidates() if f'{x["source"]}:{x["id"]}:{x["jeu"]}' in base]
    print(f"{len(cand)} questions du banc jugement_alphabet reprises ; {len(deja)} déjà faites ici.")
    textes: dict[str, dict] = {}
    faites, cumul_gpt, cumul_br, pire_gpt, pire_br = 0, 0.0, 0.0, 0.0, 0.0
    with FICHIER.open("a", encoding="utf-8") as f:
        for x in cand:
            qid = f'{x["source"]}:{x["id"]}:{x["jeu"]}'
            if faites >= n:
                break
            if qid in deja:
                continue
            if fb.depasse(cumul_gpt, pire_gpt, budget) or fb.depasse(cumul_br, pire_br, budget_bedrock):
                print(f"Plafond atteint : Azure {cumul_gpt:.2f} $, Bedrock {cumul_br:.2f} $. Arrêt.")
                break
            if x["jeu"] not in textes:
                try:
                    qs = await fb._json(f"{fb.DEPOT}/question_sets/{x['jeu']}-llm.json")
                    textes[x["jeu"]] = {str(q["id"]): q for q in qs.get("questions", [])}
                except Exception:
                    textes[x["jeu"]] = {}
            src = textes[x["jeu"]].get(x["id"])
            if not src:
                continue
            q = {"titre": x["titre"], "cloture": x["cloture"],
                 "criteres": str(src.get("market_info_resolution_criteria") or src.get("resolution_criteria") or ""),
                 "contexte": str(src.get("background") or "")}       # jamais freeze_datetime_value ni source_intro
            b = base[qid]
            p_b, notes = float(b["p_B"]), b.get("notes") or {}
            info = datetime.fromisoformat(x["jeu"]).replace(tzinfo=timezone.utc)
            # 0.10.258 : recherche gelée par question (cache) et tracée (trace_recherche.py)
            rech, du_cache = await tr.chercher_fige(qid, x["titre"], info, ar.chercher_avant)
            res: dict = {"recherche": {**tr.tracer(rech, x["jeu"]), "cache": du_cache}}
            with MonetaryCostManager() as cm:
                if len(notes) >= 4:
                    try:
                        res["p_M_refait"] = borne((await appeler(GPT, bja.consigne_finale(q, p_b, notes, rech, x["jeu"])))["p"])
                    except Exception as e:
                        res["erreur_refait"] = f"{type(e).__name__}: {e}"[:200]
                    try:
                        av = await appeler(GPT, consigne_avocat(q, p_b, notes, rech, x["jeu"]))
                        res["avocat"] = {k: (str(av.get(k, ""))[:400] if k != "solidite" else av.get(k)) for k in
                                         ("chemin", "signes", "solidite")}
                        res["p_M_avocat"] = borne((await appeler(GPT, consigne_finale_avocat(
                            q, p_b, notes, res["avocat"], rech, x["jeu"])))["p"])
                    except Exception as e:
                        res["erreur_avocat"] = f"{type(e).__name__}: {e}"[:200]
                    try:
                        res["neutre_remplie_d_abord"] = ordre_neutre(qid)
                        res["p_M_neutre"] = lire_neutre(await appeler(GPT, consigne_neutre(
                            q, p_b, notes, rech, x["jeu"], res["neutre_remplie_d_abord"])))
                    except Exception as e:
                        res["erreur_neutre"] = f"{type(e).__name__}: {e}"[:200]
                c_gpt = float(cm.current_usage or 0)
            h: dict = {}
            with MonetaryCostManager() as cm:
                try:
                    r = await appeler(HAIKU, bja.consigne_a(q, p_b, rech, x["jeu"]))
                    h["p_A"], h["connait_issue"] = borne(r["p"]), bool(r.get("connait_issue"))
                except Exception as e:
                    h["erreur_A"] = f"{type(e).__name__}: {e}"[:200]
                try:
                    r = await appeler(HAIKU, bja.consigne_notes(q, p_b, rech, x["jeu"]))
                    h["notes"] = bja.lire_notes(r)
                    h["connait_issue"] = h.get("connait_issue", False) or bool(r.get("connait_issue"))
                    if len(h["notes"]) >= 4:
                        h["p_M"] = borne((await appeler(HAIKU, bja.consigne_finale(q, p_b, h["notes"], rech, x["jeu"])))["p"])
                        av = await appeler(HAIKU, consigne_avocat(q, p_b, h["notes"], rech, x["jeu"]))
                        h["avocat_solidite"] = av.get("solidite")
                        h["p_M_avocat"] = borne((await appeler(HAIKU, consigne_finale_avocat(
                            q, p_b, h["notes"], av, rech, x["jeu"])))["p"])
                except Exception as e:
                    h["erreur_M"] = f"{type(e).__name__}: {e}"[:200]
                c_br = float(cm.current_usage or 0)
            if h.get("connait_issue"):      # même règle que le banc : une question dont l'issue est connue sort
                h = {"exclue": True, "notes": h.get("notes")}
            ligne = {"type": "banc_jugement_variantes", "jeu": x["jeu"], "question_id": qid, "forme": x["forme"],
                     "issue": x["issue"], "p_B": p_b, "p_M_banc": b["p_M"], **res, "haiku": h,
                     "version_bot": ap.VERSION_BOT, "modeles": {"gpt": GPT, "haiku": HAIKU},
                     "cout_azure_usd": round(c_gpt, 4), "cout_bedrock_usd": round(c_br, 4),
                     "licence": "ForecastBench, Forecasting Research Institute, CC BY-SA 4.0"}
            f.write(json.dumps(ligne, ensure_ascii=False) + "\n")
            f.flush()
            deja.add(qid)
            cumul_gpt, cumul_br = cumul_gpt + c_gpt, cumul_br + c_br
            pire_gpt, pire_br = max(pire_gpt, c_gpt), max(pire_br, c_br)
            faites += 1
            print(f"{qid[:46]} : M {res.get('p_M_refait')} · avocat {res.get('p_M_avocat')} · neutre "
                  f"{res.get('p_M_neutre')} · Haiku A {h.get('p_A')} M {h.get('p_M')} · issue {x['issue']} · "
                  f"{c_gpt:.4f} $ + {c_br:.4f} $")
    r = resumer(lignes())
    RESUME.write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{faites} question(s) ; Azure {cumul_gpt:.2f} $ (plafond {budget:.2f}), Bedrock {cumul_br:.2f} $ "
          f"(plafond {budget_bedrock:.2f}).")
    print(json.dumps({k: v for k, v in r.items() if k != "cartes_haiku"}, ensure_ascii=False, indent=1)[:3000])
    return 0


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("--n", type=int, default=150)
    a.add_argument("--budget", type=float, default=3.0)
    a.add_argument("--budget-bedrock", type=float, default=15.0)
    o = a.parse_args()
    sys.exit(asyncio.run(principal(o.n, o.budget, o.budget_bedrock)))
