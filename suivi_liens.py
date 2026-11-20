"""Suivi en avant des liens d'acteurs sur les questions réelles (2026-11-20, 19 h 06, « on y va »).

Chaque lien de ecosystemes/liens-acteurs.yaml reçoit un motif de reconnaissance écrit sur le titre (MOTIFS, fixés le
2026-11-20 avant toute issue ; un lien sans motif n'est pas suivi). On relève :
- les questions du journal du bot (registre/journal-bot.jsonl, dernière ligne intacte par question) ;
- les questions du registre de jugement jouées à partir du 2026-11-20 (essais.CONFIRMATION_DEPUIS).
À chaque issue connue : part de OUI et perte du bot (journal) sur les questions qui touchent chaque lien, par type de
relation et selon que la fenêtre de la question franchit ou non l'échéance du cycle (temps.jusqua). Observation, pas un
test : un test se préenregistre quand assez de questions sont résolues. Rien n'entre dans le bot.

    python suivi_liens.py     # écrit registre/suivi-liens.json
"""
from __future__ import annotations

import json
import math
import re
import sys
from collections import defaultdict
from pathlib import Path

import liens_acteurs as la

REG = Path("registre")
SORTIE = REG / "suivi-liens.json"
DEPUIS = "2026-11-20"
R = lambda s: re.compile(s, re.I)
MOTIFS = {
    "us_loi_depend_du_congres": R(r"\b(congress|house of representatives|u\.?s\.? senate)\b.*\b(pass|bill|legislation|act)\b|\bbecome law\b"),
    "us_veto_bloque_le_congres": R(r"\bveto\b"),
    "us_decret_sans_le_congres": R(r"\bexecutive order\b"),
    "us_tribunaux_bloquent_les_decrets": R(r"\b(judge|court)\b.*\b(block|injunction|halt|strike down)\b"),
    "us_nominations_confirmees_par_le_senat": R(r"\bconfirm\w*\b.*\b(u\.?s\.? )?senate\b(?!.*\b(argentin|brazil|philippin|mexic|australi|canad|french|italian))"),
    "us_120e_congres": R(r"\b120th congress\b|\bspeaker of the house\b|\bmidterm"),
    "ua_loi_martiale_prolongee_par_la_rada": R(r"\bmartial law\b.*\bukrain|\bukrain\w*\b.*\bmartial law\b"),
    "ua_elections_suspendues_sous_loi_martiale": R(r"\bukrain\w*\b.*\belection|\bzelensk\w*\b.*\b(election|re-?elect)"),
    "ue_sanctions_renouvelees_tous_les_six_mois": R(r"\b(EU|European Union)\b.*\bsanction"),
    "us_tarifs_ieepa_annules": R(r"\btariff"),
    "cn_licences_exportation_mineraux": R(r"\b(rare earth|gallium|germanium|graphite|antimony)\b"),
    "treve_sino_americaine": R(r"\b(china|chinese)\b.*\b(tariff|trade (deal|truce|war))\b|\btrade truce\b"),
    "il_formation_du_gouvernement": R(r"\b(israel\w*|knesset|netanyahu|eisenkot)\b.*\b(government|prime minister|coalition|election)\b"),
    "gaza_force_de_stabilisation": R(r"\bgaza\b|\bhamas\b"),
    "ir_sanctions_onu_retablies": R(r"\biran\w*\b.*\b(sanction|snapback)"),
    "ir_verification_aiea_limitee": R(r"\biaea\b|\biran\w*\b.*\b(nuclear|enrich|inspect)"),
    "oms_urgences_en_vigueur": R(r"(?-i:\bWHO\b)|\bpheic\b|public health emergency|pandemic emergency"),
    "us_rougeole_decompte_cdc": R(r"\bmeasles\b"),
    "accord_pandemie_attend_annexe_pabs": R(r"\bpandemic (agreement|treaty|accord)\b|\bpabs\b"),
    "otan_article_4_invoque": R(r"\barticle 4\b"),
    "otan_objectif_cinq_pour_cent": R(r"\bnato\b.*\b(spend|gdp|percent|%)"),
    "otan_decisions_par_consensus": R(r"\bnato\b"),
    "ue_adhesion_ukraine_groupes_de_chapitres": R(r"\b(accession|cluster|join the (EU|European Union))\b"),
    "ue_reglement_ia_calendrier": R(r"\bAI Act\b"),
    "us_licences_puces_ia_chine": R(r"\b(nvidia|h20|h200|chip)\b.*\bchin"),
    "opep_plus_quotas_mensuels": R(r"\bopec"),
    "iran_detroit_d_ormuz": R(r"\bhormuz\b"),
    "houthis_bab_el_mandeb": R(r"\b(houthi\w*|red sea|bab el-?mandeb)\b"),
    "us_cour_supreme_session_annuelle": R(r"\bsupreme court\b"),
    "us_revocation_gouverneur_fed_bloquee": R(r"\b(lisa cook|fed(eral reserve)? governor)\b"),
    "us_president_fed_warsh": R(r"\b(warsh|fed chair|chair of the federal reserve)\b"),
    "houthis_cessez_le_feu_etats_unis": R(r"\bhouthi\w*\b.*\bceasefire|\bceasefire\b.*\bhouthi"),
    "soudan_treves_echouent": R(r"\bsudan\w*\b"),
    "ru_ua_negociation_reprise": R(r"\b(peace (deal|agreement|talks)|ceasefire)\b.*\b(russia|ukrain)|\b(russia|ukrain)\w*\b.*\b(peace|ceasefire)\b|\b(trump|putin)\b.*\bmeet"),
    "br_lula_reelu": R(r"\bbrazil\w*\b|\blula\b|\bbolsonaro\b"),
    "ve_transition_sans_date": R(r"\bvenezuel\w*\b|\bmaduro\b|\bdelcy\b"),
    "ht_elections_reportees": R(r"\bhaiti\w*\b"),
    "groenland_accord_securite": R(r"\bgreenland\b"),
    "us_inde_accord_commercial_cadre": R(r"\bindia\w*\b.*\btrade\b|\btrade\b.*\bindia"),
}


def liens_de(titre: str) -> list[str]:
    return [k for k, r in MOTIFS.items() if r.search(titre or "")]


def questions() -> list[dict]:
    import alphabet_pipeline as ap
    par = {}
    f = REG / "journal-bot.jsonl"
    if f.exists():
        for l in filter(str.strip, f.read_text(encoding="utf-8").splitlines()):
            x = json.loads(l)
            s = x.pop("sceau", None)
            if s == ap.sceau(x):
                par[("bot", x["question_id"])] = {"origine": "journal du bot", "id": x["question_id"], "titre": x["titre"],
                                                  "jeu": x["date_information"], "fin": x.get("resolution_prevue"),
                                                  "p_bot": x.get("p_poste")}
    g = REG / "jugement-questions.jsonl"
    if g.exists():
        for l in filter(str.strip, g.read_text(encoding="utf-8").splitlines()):
            x = json.loads(l)
            if x["jeu"] >= DEPUIS:
                par[(x["source"], x["id"])] = {"origine": x["source"], "id": x["id"], "titre": x["titre"], "jeu": x["jeu"],
                                               "fin": x.get("resolue_le"), "issue": x.get("issue")}
    return list(par.values())


def perte(p: float, y: int) -> float:
    p = max(0.01, min(0.99, p))
    return -math.log(p if y else 1 - p)


def issues_bot() -> dict[str, int]:
    f = REG / "issues.jsonl"
    return {x["question_id"]: int(x["issue"]) for x in map(json.loads, filter(str.strip, f.read_text(encoding="utf-8").splitlines()))} \
        if f.exists() else {}


def principal() -> int:
    liens = {x["id"]: x for x in la.liens()}
    ib = issues_bot()
    par_lien = defaultdict(list)
    for q in questions():
        if q["origine"] == "journal du bot":
            q["issue"] = ib.get(q["id"])
        for k in liens_de(q["titre"]):
            t = liens.get(k, {}).get("temps") or {}
            franchit = bool(t.get("jusqua") and q.get("fin") and str(q["fin"])[:10] > str(t["jusqua"])[:10])
            par_lien[k].append({**q, "relation": liens.get(k, {}).get("relation"), "franchit_echeance": franchit})
    sortie = {}
    for k, qs in sorted(par_lien.items()):
        res = [q for q in qs if q.get("issue") is not None]
        pb = [q for q in res if isinstance(q.get("p_bot"), (int, float))]
        sortie[k] = {"relation": qs[0]["relation"], "questions": len(qs), "resolues": len(res),
                     "part_oui": round(sum(q["issue"] for q in res) / len(res), 3) if res else None,
                     "perte_log_bot": round(sum(perte(q["p_bot"], q["issue"]) for q in pb) / len(pb), 4) if pb else None,
                     "franchissent_echeance": sum(q["franchit_echeance"] for q in qs),
                     "exemples": [q["titre"][:100] for q in qs[:3]]}
    r = {"releve": DEPUIS + " →", "liens_suivis": len(MOTIFS), "liens_touches": len(sortie), "par_lien": sortie,
         "note": "observation en avant, pas un test ; rien n'entre dans le bot"}
    SORTIE.write_text(json.dumps(r, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: (v["questions"], v["resolues"]) for k, v in sortie.items()}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(principal())
