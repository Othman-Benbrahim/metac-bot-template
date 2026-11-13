"""Sonde directe de l'API NVIDIA (build.nvidia.com), sans litellm (0.10.60).

Pour chaque modèle : la présence dans /v1/models, puis un appel « OK » en flux (délai jusqu'au premier octet, puis
jusqu'à la fin) et le code HTTP. Distingue un refus (401/403/404, immédiat), une file d'attente (aucun octet) et un
modèle qui répond. La clé vient du secret NVIDIA_API_KEY ; elle n'est jamais affichée.

    python sonde_nvidia.py [modele1,modele2,...]
"""
from __future__ import annotations

import json
import os
import sys
import time

import httpx

FOURNISSEURS = {   # 0.10.63 : la même sonde pour plusieurs fournisseurs compatibles OpenAI
    "nvidia": ("https://integrate.api.nvidia.com/v1", ("NVIDIA_API_KEY", "NVIDIA_NIM_API_KEY")),
    "mistral": ("https://api.mistral.ai/v1", ("MISTRAL_API_KEY",)),
    "sambanova": ("https://api.sambanova.ai/v1", ("SAMBANOVA_API_KEY",)),
    "cerebras": ("https://api.cerebras.ai/v1", ("CEREBRAS_API_KEY",)),
}
FOURNISSEUR = os.environ.get("SONDE_FOURNISSEUR") or "nvidia"
BASE, CLES = FOURNISSEURS[FOURNISSEUR]
DEFAUT_MISTRAL = "mistral-large-latest,mistral-medium-latest,mistral-small-latest,magistral-medium-latest"
DEFAUT = ("deepseek-ai/deepseek-v4.1-flash,nvidia/nemotron-3-ultra-550b-a55b,z-ai/glm-5.3-flash,"
          "minimaxai/minimax-m3.1-flash,google/gemma-4-31b-it,openai/gpt-oss-20b")
DELAI = float(os.environ.get("SONDE_DELAI") or "120")


def sonder(client: httpx.Client, modele: str) -> dict:
    corps = {"model": modele, "max_tokens": 64, "temperature": 0, "stream": True,
             "messages": [{"role": "user", "content": 'Réponds uniquement par cet objet JSON : {"ok": true}'}]}
    t0 = time.monotonic()
    premier, texte, code = None, "", None
    try:
        with client.stream("POST", f"{BASE}/chat/completions", json=corps, timeout=httpx.Timeout(DELAI, connect=20)) as r:
            code = r.status_code
            if code != 200:
                return {"modele": modele, "code": code, "secondes": round(time.monotonic() - t0, 1),
                        "erreur": r.read().decode("utf-8", "replace")[:300]}
            for ligne in r.iter_lines():
                if premier is None:
                    premier = round(time.monotonic() - t0, 1)
                if not ligne.startswith("data:") or ligne.strip() == "data: [DONE]":
                    continue
                try:
                    d = json.loads(ligne[5:])
                    delta = (d.get("choices") or [{}])[0].get("delta") or {}
                    texte += (delta.get("content") or "")
                except Exception:
                    pass
                if time.monotonic() - t0 > DELAI:
                    break
        return {"modele": modele, "code": code, "premier_octet_s": premier, "total_s": round(time.monotonic() - t0, 1),
                "reponse": texte.strip()[:200]}
    except Exception as e:
        return {"modele": modele, "code": code, "premier_octet_s": premier, "secondes": round(time.monotonic() - t0, 1),
                "erreur": f"{type(e).__name__}: {e}"[:300]}


def principal(modeles: list[str]) -> int:
    cle = next((os.environ.get(k) for k in CLES if os.environ.get(k)), None)
    if not cle:
        print(f"Pas de clé {CLES[0]} (fournisseur {FOURNISSEUR}).")
        return 1
    print(f"Fournisseur : {FOURNISSEUR} ({BASE})")
    with httpx.Client(headers={"Authorization": f"Bearer {cle}", "Accept": "text/event-stream"}) as c:
        try:
            r = c.get(f"{BASE}/models", timeout=30)
            ids = {m.get("id") for m in r.json().get("data", [])}
            print(f"/v1/models : HTTP {r.status_code}, {len(ids)} modèles listés")
            print("  dont : " + ", ".join(sorted(i for i in ids if any(k in i for k in
                                                                           ("deepseek", "nemotron-3", "glm", "minimax", "qwen", "kimi", "gpt-oss", "llama", "Llama", "DeepSeek")))))
        except Exception as e:
            ids = set()
            print(f"/v1/models : {type(e).__name__}: {e}")
        if modeles == ["*"]:
            modeles = sorted(i for i in ids if i)[:15]
        for m in modeles:
            res = sonder(c, m)
            res["liste"] = m in ids
            print(json.dumps(res, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    arg = sys.argv[1].strip() if len(sys.argv) > 1 else ""       # entrée vide du workflow : la liste par défaut
    defaut = {"mistral": DEFAUT_MISTRAL, "sambanova": "", "cerebras": ""}.get(FOURNISSEUR, DEFAUT)
    if not (arg or defaut):        # sambanova : les modèles listés par l'API elle-même
        defaut = "*"
    sys.exit(principal([m.strip() for m in (arg or defaut).split(",") if m.strip()]))
