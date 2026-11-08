"""Sonde des puits de données (0.7.0) : un appel réel par source, borné à une date passée, sans rien écrire.

    uv run python sonde_puits.py

Affiche pour chaque source : OK (nombre de points, premier et dernier), SANS CLÉ, VIDE ou ÉCHEC (motif). Sert à vérifier,
depuis GitHub Actions, que les connecteurs lisent bien les réponses réelles (le nom des champs de certaines API n'est
pas documenté). Sortie en erreur seulement si AUCUNE source ne répond.
"""
from __future__ import annotations

import asyncio
import sys
from datetime import date

import alphabet_puits as apz

EXEMPLES = {
    "fred": {"serie": "UNRATE"},
    "banque_mondiale": {"pays": "FRA", "indicateur": "NY.GDP.MKTP.KD.ZG"},
    "bce": {"cle": "EXR/M.USD.EUR.SP00.A"},
    "eurostat": {"jeu": "une_rt_m", "filtres": {"geo": "FR", "s_adj": "SA", "age": "TOTAL", "sex": "T", "unit": "PC_ACT"}},
    "tresor": {"jeu": "v2/accounting/od/avg_interest_rates", "champ": "avg_interest_rate_amt",
               "filtre": "security_desc:eq:Total Marketable"},
    "bls": {"serie": "LNS14000000"},
    "unhcr": {"pays_origine": "SYR"},
    "fts": {"pays": "SDN", "annees": [2023, 2024]},
    "ucdp": {"pays": "Sudan", "debut": "2024-01-01"},
    "usgs_seismes": {"magnitude_min": 7, "debut": "2015-01-01"},
    "gdacs": {"types": "EQ;TC", "debut": "2026-01-01"},
    "eonet": {"categorie": "wildfires", "jours": 30},
    "federal_register": {"terme": "tariff", "type_doc": "PRESDOCU"},
    "firms": {"pays": "GRC", "jours": 3},
    "wikidata_poste": {"poste": "President of France"},
    "wikipedia": {"titre": "Sudanese civil war (2023–present)"},
    "wayback": {"url": "https://www.state.gov/"},
    "hdx": {"terme": "Sudan food security"},
}


async def principal(avant: date) -> int:
    ok = 0
    for nom in apz.CATALOGUE:
        try:
            r = await apz.appeler(nom, EXEMPLES.get(nom, {}), avant)
        except apz.SansCle as e:
            print(f"⏭️  {nom} : SANS CLÉ ({e})")
            continue
        except Exception as e:
            print(f"❌  {nom} : ÉCHEC {type(e).__name__} : {str(e)[:200]}")
            continue
        pts = r["points"]
        if not pts:
            print(f"⚠️  {nom} : VIDE ({r['url']})")
            continue
        ok += 1
        exemple = apz.texte_releve(r, 2).splitlines()[1:3]
        print(f"✅  {nom} : {len(pts)} points, du {pts[0]['date']} au {pts[-1]['date']} · {' | '.join(exemple)[:160]}")
    print(f"\n{ok}/{len(apz.CATALOGUE)} sources répondent (bornées au {avant}).")
    return 0 if ok else 1


if __name__ == "__main__":
    borne = date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else date(2026, 6, 1)
    sys.exit(asyncio.run(principal(borne)))
