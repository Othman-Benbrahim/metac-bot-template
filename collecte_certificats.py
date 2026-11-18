"""Collecte des certificats HTTPS des laboratoires d'IA (bot 0.10.299, en ombre).

Décision d'auteur du 2026-11-18, 22 h 35 (« recoupe tout ce qui est exploitable et branche-le ; carte blanche »).
Idée : avant de lancer un produit, une entreprise prépare ses adresses ; chaque certificat HTTPS est inscrit dans des
registres PUBLICS de transparence (Certificate Transparency), datés. Un nom de modèle peut y apparaître avant
l'annonce (« l'avenir déjà présent »). Carte : DÉCLENCHEUR. Préenregistrement : preenregistrements/sources-hors-cadre.md.

Source : API Cert Spotter (SSLMate), sans clé (limite basse) ou avec CERTSPOTTER_CLE (compte gratuit). Domaines suivis :
registre/certificats-domaines.txt (un par ligne, modifiable). Seuls les NOMS DNS et les dates sont gardés
(registre/certificats.jsonl) ; état de reprise dans registre/certificats-etat.json. Rien n'entre dans le bot.

    python collecte_certificats.py
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

import politesse

REG = Path(os.environ.get("ALPHABET_REGISTRE", "registre"))
DOMAINES = REG / "certificats-domaines.txt"
SORTIE = REG / "certificats.jsonl"
ETAT = REG / "certificats-etat.json"
API = "https://api.certspotter.com/v1/issuances"
PAGES_MAX = 8                 # par domaine et par passage : l'historique se rattrape de nuit en nuit
DEFAUT = ["openai.com", "chatgpt.com", "anthropic.com", "claude.ai", "x.ai", "grok.com", "mistral.ai",
          "deepseek.com", "deepmind.google", "meta.ai", "perplexity.ai", "kimi.com", "z.ai", "qwen.ai"]


def domaines() -> list[str]:
    if DOMAINES.exists():
        return [l.strip() for l in DOMAINES.read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("#")]
    return DEFAUT


def nouveaux_noms(issuances: list[dict], vus: set[str]) -> list[dict]:
    out = []
    for i in issuances:
        for n in i.get("dns_names") or []:
            n = n.lower().lstrip("*.")
            if n not in vus:
                vus.add(n)
                out.append({"nom": n, "vu_le": str(i.get("not_before") or "")[:10], "id": str(i.get("id"))})
    return out


def principal() -> int:
    etat = json.loads(ETAT.read_text(encoding="utf-8")) if ETAT.exists() else {}
    vus = {json.loads(l)["nom"] for l in SORTIE.read_text(encoding="utf-8").splitlines() if l.strip()} if SORTIE.exists() else set()
    entetes = {"User-Agent": politesse.UA}
    if os.environ.get("CERTSPOTTER_CLE"):
        entetes["Authorization"] = f"Bearer {os.environ['CERTSPOTTER_CLE']}"
    total, sante = 0, {}
    collecte = datetime.now(timezone.utc).date().isoformat()
    with httpx.Client(headers=entetes, timeout=40) as c, SORTIE.open("a", encoding="utf-8") as f:
        for d in domaines():
            n_d = 0
            try:
                for _ in range(PAGES_MAX):
                    params = {"domain": d, "include_subdomains": "true", "expand": "dns_names"}
                    if etat.get(d):
                        params["after"] = etat[d]
                    r = c.get(API, params=params)
                    if r.status_code == 429:
                        sante[d] = "limite atteinte (reprise au prochain passage)"
                        break
                    r.raise_for_status()
                    lot = r.json()
                    if not lot:
                        break
                    for x in nouveaux_noms(lot, vus):
                        f.write(json.dumps({"domaine": d, **x, "collecte_le": collecte}, ensure_ascii=False) + "\n")
                        n_d += 1
                    etat[d] = str(lot[-1]["id"])
                    time.sleep(1.5)
                sante.setdefault(d, "ok")
            except Exception as e:
                sante[d] = f"{type(e).__name__}: {str(e)[:120]}"
            total += n_d
            print(f"{d} : {n_d} nouveau(x) nom(s) ; {sante[d]}", flush=True)
    ETAT.write_text(json.dumps(etat, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Total : {total} nouveau(x) nom(s).")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
