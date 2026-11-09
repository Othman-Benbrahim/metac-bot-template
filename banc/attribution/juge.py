"""JUGE VERROUILLÉ du banc d'attribution. Ne pas modifier pendant une boucle d'amélioration (ni le corpus).

    uv run python banc/attribution/juge.py            # partie de travail
    uv run python banc/attribution/juge.py --cache    # partie cachée : vérification finale SEULEMENT

Un chiffre, à faire baisser : le taux de faits NON attribuables acceptés (« faux acceptés »), tant que le taux de
faits attribuables refusés (« faux refus ») reste ≤ 10 %. Au-delà, le score vaut 1 + faux refus (contrôle inutilisable :
il rejetterait les vrais faits). Seul alphabet_attribution.py est modifiable.
"""
import argparse
import json
import sys
from pathlib import Path

ICI = Path(__file__).parent
sys.path.insert(0, str(ICI.parent.parent))
from alphabet_attribution import controle_attribution  # noqa: E402

FAUX_REFUS_MAX = 0.10


def juger(cas: list[dict]) -> dict:
    fa = fr = n_neg = n_pos = 0
    par_genre: dict[str, list[int]] = {}
    erreurs = []
    for c in cas:
        dossier = {"mots": [{"carte": "SEU", "strate": 7, "fait": c["fait"], "source_url": c["source_url"],
                             "passage": [{"extrait": e} for e in c["extraits"]]}]}
        r = controle_attribution(dossier, c["resultats"])
        accepte = bool(r and r["detail"]["SEU@7"]["attribue"] is True)
        juste = accepte == c["attribuable"]
        g = par_genre.setdefault(c["genre"], [0, 0])
        g[0] += juste
        g[1] += 1
        if c["attribuable"]:
            n_pos += 1
            fr += not accepte
        else:
            n_neg += 1
            fa += accepte
        if not juste:
            erreurs.append(c["id"])
    t_fa, t_fr = fa / max(1, n_neg), fr / max(1, n_pos)
    return {"score": t_fa if t_fr <= FAUX_REFUS_MAX else 1 + t_fr, "faux_acceptes": round(t_fa, 4),
            "faux_refus": round(t_fr, 4), "cas": len(cas),
            "justes_par_genre": {g: f"{v[0]}/{v[1]}" for g, v in sorted(par_genre.items())}, "erreurs": erreurs}


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("--cache", action="store_true")
    args = a.parse_args()
    nom = "corpus-cache.json" if args.cache else "corpus-travail.json"
    r = juger(json.loads((ICI / nom).read_text(encoding="utf-8")))
    if args.cache:
        r.pop("erreurs")          # la partie cachée ne livre que des agrégats
    print(json.dumps(r, ensure_ascii=False, indent=1))
