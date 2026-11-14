"""Les règles d'ancrage par les séries se déclenchent-elles sur du bruit ? (contrôle du 2026-11-14, sans coût)

Al Mamun, « From Data to Decision », ch. 10, 12 et 50 : un seuil, une rupture ou un régime CHERCHÉ dans une série paraît
presque toujours exister, et une série simplement persistante ressemble à une série à seuil ou à rupture. Les règles
de `ombres_auto.py` (CROISSANCE, PÉRIODICITÉ, INCERTITUDE) sont des règles courtes, sans test. Ce contrôle mesure leur
taux de déclenchement sur des séries de substitution SANS la structure visée, puis le compare au taux observé sur les
séries réelles du registre (ombre « ancrage par les séries »). Une règle qui se déclenche aussi souvent sur du bruit que
sur les séries réelles ne mesure rien.

Substituts (graine fixe, 2 000 séries par cas, longueurs 30, 60 et 250 points) : bruit blanc ; marche aléatoire ;
marche aléatoire avec dérive (la plupart des séries économiques montent) ; AR(1) persistant (φ = 0,9). SEUIL n'est pas
contrôlé : il dépend du seuil déclaré par la question, pas d'une recherche.

    python controle_regles_series.py [--json]
"""
from __future__ import annotations

import argparse
import json
import random
import sys

import ombres_auto as oa

CAS = ("bruit_blanc", "marche_aleatoire", "marche_avec_derive", "ar1_persistant")
LONGUEURS = (30, 60, 250)
N_SERIES = 2000


def substitut(cas: str, n: int, rnd: random.Random) -> list[float]:
    v, x = [], 100.0
    for _ in range(n):
        e = rnd.gauss(0, 1)
        if cas == "bruit_blanc":
            x = 100.0 + e
        elif cas == "marche_aleatoire":
            x += e
        elif cas == "marche_avec_derive":
            x += 0.3 + e
        else:
            x = 100.0 + 0.9 * (x - 100.0) + e
        v.append(x)
    return v


def taux_substituts(graine: int = 0, n_series: int = N_SERIES) -> dict:
    rnd = random.Random(graine)
    out = {}
    for cas in CAS:
        for n in LONGUEURS:
            c = {k: 0 for k in oa.REGLES}
            for _ in range(n_series):
                v = substitut(cas, n, rnd)
                for k, f in oa.REGLES.items():
                    c[k] += bool(f(v))
            out[f"{cas}:{n}"] = {k: round(c[k] / n_series, 3) for k in c}
    return out


def taux_reels(lignes: list[dict]) -> dict:
    n, c = 0, {k: 0 for k in oa.REGLES}
    for x in lignes:
        o = x.get("ombre_series") or {}
        code = o.get("code") if isinstance(o, dict) else None
        if not isinstance(code, dict):
            continue
        n += 1
        for k in c:
            c[k] += bool(code.get(k))
    return {"n": n, **({k: round(c[k] / n, 3) for k in c} if n else {})}


def principal(en_json: bool) -> int:
    import alphabet_pipeline as ap
    import alphabet_retro as ar
    f = ap.REGISTRE / ar.RETRO
    L = [json.loads(l) for l in f.read_text(encoding="utf-8").splitlines() if l.strip()] if f.is_file() else []
    rap = {"substituts": taux_substituts(), "series_reelles_du_registre": taux_reels(L)}
    if en_json:
        print(json.dumps(rap, ensure_ascii=False, indent=1))
        return 0
    print(f"{'cas':28} " + " ".join(f"{k:>6}" for k in oa.REGLES))
    for k, v in rap["substituts"].items():
        print(f"{k:28} " + " ".join(f"{v[r]:6.3f}" for r in oa.REGLES))
    r = rap["series_reelles_du_registre"]
    print(f"{'séries réelles (n=' + str(r['n']) + ')':28} " + " ".join(f"{r.get(k, 0):6.3f}" for k in oa.REGLES))
    return 0


if __name__ == "__main__":
    a = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    a.add_argument("--json", action="store_true")
    sys.exit(principal(a.parse_args().json))
