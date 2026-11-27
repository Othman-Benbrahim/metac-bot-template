"""Diagnostic des pages de sondages introuvables (2026-11-27, accord de l'auteur 13 h 02). Lecture seule, aucun score,
aucune issue : pour chaque élection sans page archivée, imprime ce que renvoient (1) la recherche de l'API Wikimedia,
avec et sans « the », et (2) quelques titres construits directement. Sert à corriger la recherche du banc scrutin."""
from __future__ import annotations

import json
import re
import time
from collections import Counter
from pathlib import Path
from urllib.parse import quote

import httpx

import politesse

CORE = "https://api.wikimedia.org/core/v1/wikipedia/en"


def main() -> int:
    A = [json.loads(l) for l in open(Path("registre/scrutins/archives.jsonl"), encoding="utf-8")]
    manq = Counter(a["election"] for a in A if not a.get("revision"))
    with httpx.Client(headers={"User-Agent": politesse.UA}, timeout=60, follow_redirects=True) as c:
        if not politesse.autorise(c, CORE + "/search/page"):
            print("refusé par robots.txt"); return 0
        def get(url, **kw):
            for e in range(3):
                r = c.get(url, **kw)
                if r.status_code == 429:
                    time.sleep(10 * (e + 1)); continue
                time.sleep(0.3)
                return r.status_code, (r.json() if r.status_code == 200 else {})
            return 429, {}
        for e, n in manq.most_common(40):
            nu = re.sub(r"^(the|next)\s+", "", e.strip(), flags=re.I)
            print(f"\n=== {e}  ({n} questions)")
            for q in (f"Opinion polling for the {e}", e, f"Opinion polling for the {nu}", nu):
                st, d = get(CORE + "/search/page", params={"q": q, "limit": 5})
                print(f"  recherche « {q} » : HTTP {st} → {[p['title'] for p in (d.get('pages') or [])]}")
            for t in (f"Opinion polling for the {nu}", nu):
                st, d = get(CORE + f"/page/{quote(t.replace(' ', '_'), safe='')}/bare")
                print(f"  titre direct « {t} » : HTTP {st} {d.get('title', '')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
