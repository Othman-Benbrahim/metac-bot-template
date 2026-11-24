"""Chantier C (décision de l'auteur, 2026-11-24, 12 h 57 et 14 h 11) : lecture mécanique des interconnexions de la carte
pour une question. Sans modèle de langue ; rien n'entre dans le bot tant que ce n'est pas testé en temps réel.

Pour une question (titre, horizon en jours) :
1. rattachement aux compartiments : termes validés (lecteur-local, listes/valides.txt), liste de rattachement validée
   (listes/proposes-rattachement.txt, termes et pays) ;
2. lecture autour des compartiments : relations entrantes (effet, délai, force, coupure), ponts d'influence entrants,
   cycles et tensions qui les touchent, repères mesurés (intensité) ;
3. confrontation à l'horizon : un chemin est « rapide » si son délai tient dans l'horizon de la question.

Sortie : la lecture (chemins rapides, chemins lents, freins, cycles, tensions, repères) et deux grandeurs simples :
- part_rapide : part des chemins entrants (pondérés par la force) dont le délai tient dans l'horizon ;
- freins_rapides : chemins rapides qui freinent (effet négatif) ou portent une condition de blocage écrite.

    python mise_au_point/lecture_mecanique.py "Will Israel strike Iran before June 2026?" 90
    python mise_au_point/lecture_mecanique.py --corpus      # observation descriptive sur les questions résolues
"""
from __future__ import annotations

import csv
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ICI = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ICI))
import ecosystemes  # noqa: E402

LISTES = ICI.parent / "lecteur-local" / "listes"
DELAI_JOURS = {"seconde": 0, "secondes": 0, "minutes": 0, "heures": 0.1, "soirée": 0.5, "jours": 3, "semaines": 14,
               "mois": 60, "trimestre": 90, "trimestres": 90, "saison": 120, "saisons": 120, "année": 365,
               "années": 365, "décennie": 3650, "décennies": 3650, "générations": 9000, "permanent": float("inf")}
FORCE = {"forte": 3, "moyenne": 2, "faible": 1}


def _motif(t: str):
    return re.compile(r"(?<![\w-])" + re.escape(t) + r"(?![\w-])", 0 if (t.isupper() and len(t) <= 4) else re.I)


def routage() -> tuple[list, list, dict]:
    termes = defaultdict(set)
    for l in (LISTES / "valides.txt").read_text(encoding="utf-8").splitlines():
        p = [x.strip() for x in l.split("|")]
        if len(p) >= 4 and p[0] == "+" and len(p[1]) >= 4:
            for r in p[3].split(";"):
                r = r.strip()
                if r.count(":") == 1 and not r.startswith("espace:"):
                    termes[p[1]].add(r)
    pays = {}
    for l in (LISTES / "proposes-rattachement.txt").read_text(encoding="utf-8").splitlines():
        p = [x.strip() for x in l.split("|")]
        if len(p) < 3 or p[0] != "+":
            continue
        if p[2].startswith("pays:"):
            pays[p[1]] = p[2][5:]
        else:
            for t in p[1].split("/"):
                termes[t.strip()] |= set(p[2].split(";"))
    for r in csv.DictReader(l for l in (ICI / "ecosystemes/codes-pays-fips.csv").read_text(encoding="utf-8").splitlines()
                            if l and not l.startswith("#")):
        if r.get("nom"):
            pays.setdefault(r["nom"], r["iso3"])
    mt = [(_motif(t), r) for t, r in termes.items()]
    mp = [(re.compile(r"(?<![\w-])" + re.escape(n) + r"(?![\w-])"), i) for n, i in pays.items() if len(n) >= 2]
    return mt, mp, pays


class Carte:
    def __init__(self):
        self.s = ecosystemes.assembler(ecosystemes.charger())
        self.ids = {n["id"] for n in self.s["noeuds"]}
        self.par_pays = defaultdict(set)
        for n in self.s["noeuds"]:
            for p in (n.get("geopolitique") or {}).get("pays") or []:
                self.par_pays[p].add(n["id"])
        self.entrants = defaultdict(list)
        for r in self.s["relations"]:
            self.entrants[r["vers"]].append(r)
        self.ponts_entrants = defaultdict(list)
        for p in self.s["ponts"]:
            if p["resolu"] and p["type"] == "influence":
                self.ponts_entrants[p["vers"]].append(p)
        self.mt, self.mp, _ = routage()

    def rattacher(self, titre: str) -> tuple[set[str], list[str]]:
        """Compartiments de thème (termes) ; à défaut, compartiments des pays cités (tous les pays, sinon l'un d'eux).
        Un compartiment de thème rattaché à d'autres pays que ceux de la question est écarté."""
        theme = {r for m, rs in self.mt if m.search(titre) for r in rs if r in self.ids}
        pays = sorted({i for m, i in self.mp if m.search(titre)})
        lies = set()
        if pays:
            lies = set.intersection(*(self.par_pays[p] for p in pays)) or set().union(*(self.par_pays[p] for p in pays))
            geo = set().union(*self.par_pays.values())
            theme = {c for c in theme if c not in geo or c in lies}
        return (theme or lies), pays

    def lire(self, titre: str, horizon: float) -> dict:
        comps, pays = self.rattacher(titre)
        rapides, lents, freins = [], [], []
        poids_r = poids_t = 0
        for c in sorted(comps):
            for r in self.entrants.get(c, []):
                d = DELAI_JOURS.get(str(r.get("delai") or "").strip(), None)
                w = FORCE.get(r.get("force"), 1)
                e = {"de": r["de"], "vers": c, "effet": r.get("effet"), "delai": r.get("delai"), "force": r.get("force"),
                     "coupure": r.get("coupure"), "texte": r.get("texte")}
                if d is None:
                    continue
                poids_t += w
                if d <= horizon:
                    poids_r += w
                    rapides.append(e)
                    if r.get("effet") == "-" or (r.get("coupure") and r.get("coupure") != "inconnue"):
                        freins.append(e)
                else:
                    lents.append(e)
        cycles = [{"id": f"{x['theme']}:{x['id']}", "phase_vulnerable": x.get("phase_vulnerable"),
                   "mecanisme": x.get("mecanisme")} for x in self.s["cycles"]
                  if any(f"{x['theme']}:{k}" in comps for k in x.get("compartiments") or [])]
        tensions = [{"id": f"{x['theme']}:{x['id']}", "forme": x.get("forme"), "seuil": x.get("seuil")}
                    for x in self.s["tensions"] if any(f"{x['theme']}:{k}" in comps for k in x.get("entre") or [])]
        reperes = [r["intensite"]["mesure"] for c in comps for r in self.entrants.get(c, [])
                   if isinstance(r.get("intensite"), dict) and r["intensite"].get("mesure")]
        ponts = [{"de": p["de"], "vers": p["vers"], "nature": p["nature"]} for c in comps for p in self.ponts_entrants.get(c, [])]
        return {"titre": titre, "horizon_jours": horizon, "pays": pays, "compartiments": sorted(comps),
                "part_rapide": round(poids_r / poids_t, 3) if poids_t else None,
                "chemins_rapides": rapides, "chemins_lents": len(lents), "freins_rapides": freins,
                "cycles": cycles, "tensions": tensions, "reperes": reperes, "ponts_entrants": ponts}


def corpus(carte: Carte) -> int:
    vus, lignes = set(), []
    for l in (ICI / "registre/jugement-questions.jsonl").read_text(encoding="utf-8").splitlines():
        q = json.loads(l)
        if q["titre"] in vus or str(q.get("issue")) not in ("0", "1") or not str(q.get("horizon") or "").isdigit():
            continue
        vus.add(q["titre"])
        x = carte.lire(q["titre"], float(q["horizon"]))
        lignes.append({"source": q["source"], "issue": int(q["issue"]), "horizon": float(q["horizon"]),
                       "n_comp": len(x["compartiments"]), "part_rapide": x["part_rapide"],
                       "n_rapides": len(x["chemins_rapides"]), "n_freins": len(x["freins_rapides"]),
                       "n_cycles": len(x["cycles"]), "n_reperes": len(x["reperes"])})
    out = ICI / "registre/lecture-mecanique-corpus.json"
    def oui(L):
        return (round(sum(x["issue"] for x in L) / len(L), 3), len(L)) if L else (None, 0)
    res = {"questions": len(lignes), "avec_lecture": sum(1 for x in lignes if x["part_rapide"] is not None),
           "oui_toutes": oui(lignes)}
    lus = [x for x in lignes if x["part_rapide"] is not None]
    for nom, f in [("aucun chemin rapide", lambda x: x["part_rapide"] == 0),
                   ("part rapide < 1/3", lambda x: 0 < x["part_rapide"] < 1 / 3),
                   ("part rapide 1/3 à 2/3", lambda x: 1 / 3 <= x["part_rapide"] < 2 / 3),
                   ("part rapide >= 2/3", lambda x: x["part_rapide"] >= 2 / 3),
                   ("freins rapides présents", lambda x: x["n_freins"] > 0),
                   ("cycle touché", lambda x: x["n_cycles"] > 0),
                   ("repère mesuré", lambda x: x["n_reperes"] > 0)]:
        res[nom] = oui([x for x in lus if f(x)])
        res[nom + " (Metaculus)"] = oui([x for x in lus if f(x) and x["source"] == "metaculus"])
    out.write_text(json.dumps({"resume": res, "lignes": lignes}, ensure_ascii=False, indent=1), encoding="utf-8")
    for k, v in res.items():
        print(f"{k:40} {v}")
    return 0


if __name__ == "__main__":
    c = Carte()
    if len(sys.argv) > 1 and sys.argv[1] == "--corpus":
        sys.exit(corpus(c))
    print(json.dumps(c.lire(sys.argv[1], float(sys.argv[2]) if len(sys.argv) > 2 else 90), ensure_ascii=False, indent=1))
