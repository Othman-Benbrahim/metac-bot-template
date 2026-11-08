"""Surveillance des modèles (0.6.0) : sonde chaque modèle de chaque suite (ALPHABET_LLM, ALPHABET_PETIT_LLM,
ALPHABET_CONTRADICTEUR), et la liste des modèles de la passerelle si OPENAI_API_BASE est renseignée. Écrit une ligne
dans registre/sante-modeles.jsonl seulement si l'état change, et sort en erreur si un rôle obligatoire n'a plus aucun
modèle disponible : le workflow passe en rouge et GitHub prévient par e-mail."""
from __future__ import annotations

import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import alphabet_modeles as am

REGISTRE = Path(os.environ.get("ALPHABET_REGISTRE", "registre"))


def catalogue() -> list[str] | None:
    base, cle = os.environ.get("OPENAI_API_BASE"), os.environ.get("OPENAI_API_KEY")
    if not base or not cle:
        return None
    import httpx
    try:
        r = httpx.get(base.rstrip("/") + "/models", headers={"Authorization": f"Bearer {cle}"}, timeout=30)
        r.raise_for_status()
        return sorted(str(m.get("id")) for m in r.json().get("data", []))
    except Exception as e:
        print(f"⚠️  liste des modèles indisponible : {type(e).__name__}")
        return None


async def principal() -> int:
    essais = []
    for role, var in am.ROLES.items():
        for m in am.suite(os.environ.get(var)):
            r = await am.sonder(m)
            r["role"] = role
            essais.append(r)
            print(f"{'✅' if r['json_ok'] else '❌'}  {role} : {m} ({r['secondes']} s)" + (f" — {r['erreur']}" if r['erreur'] else ""))
    cat = catalogue()
    if cat is not None:                      # 0.7.3 : le catalogue de la passerelle, pour choisir les suites
        print(f"📚  {len(cat)} modèles à la passerelle : " + ", ".join(cat))
    absents = sorted({m.removeprefix("openai/") for m in (e["modele"] for e in essais)
                      if m.startswith("openai/") and cat is not None and m.removeprefix("openai/") not in cat})
    etat = {r: sorted(e["modele"] for e in essais if e["role"] == r and e["json_ok"]) for r in am.ROLES}
    resume = {"disponibles": etat, "absents_du_catalogue": absents}
    import alphabet_pipeline as ap
    f = ap.registre_ecrivable(REGISTRE) / "sante-modeles.jsonl"
    derniere = None
    if f.is_file():
        lignes = [x for x in f.read_text(encoding="utf-8").splitlines() if x.strip()]
        derniere = json.loads(lignes[-1]).get("resume") if lignes else None
    if resume != derniere:
        with open(f, "a", encoding="utf-8", newline="\n") as h:
            h.write(json.dumps({"horodatage": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                                "resume": resume, "essais": essais}, ensure_ascii=False, sort_keys=True) + "\n")
        print("📝  état changé : ligne ajoutée à registre/sante-modeles.jsonl")
    manquants = [r for r in ("principal",) if am.suite(os.environ.get(am.ROLES[r])) and not etat[r]]
    if manquants:
        print(f"❌  aucun modèle disponible pour : {', '.join(manquants)}")
        return 1
    if am.suite(os.environ.get("ALPHABET_CONTRADICTEUR")) and not etat["contradicteur"]:
        print("⚠️  aucun contradicteur disponible : le bot tournera sans contradicteur")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(principal()))
