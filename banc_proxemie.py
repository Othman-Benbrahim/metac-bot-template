"""La carte aide-t-elle à prévoir ? (bot 0.10.348, ombre). Préenregistrement : preenregistrements/proxemie-carte.md.

Chaque question résolue est rattachée aux fiches de la carte par des règles fixées d'avance ; on lit l'état de ces
fiches au jour du jeu (séries coupées à cette date, sans la calibration, qui fuirait) ; on compare le recalibrage des
questions semblables avec et sans ces traits.

    python banc_proxemie.py      # écrit registre/banc-proxemie.json
"""
from __future__ import annotations

import json
import math
import re
import sys
from pathlib import Path

import numpy as np

import adaptateurs as ad
import banc_jugement as bj
import banc_redacteur as br
import carte as ca

SORTIE = Path("registre") / "banc-proxemie.json"
COMBINEE = re.compile(r"We are presenting you with two probability questions", re.I)
REGLES = {
    "ormuz": r"\bhormuz\b|persian gulf",
    "iran-nucleaire": r"\biran|\biaea\b|enrich|tehran|khamenei",
    "russie-ukraine": r"ukrain|\brussia|putin|zelensk|\bkyiv|crimea|donbas|donetsk",
    "guerre-levant": r"\bisrael|\bgaza|hamas|hezbollah|lebanon|\bsyria|yemen|houthi|netanyahu",
    "liban-institutions": r"lebanon|hezbollah|beirut",
    "energie-mondiale": r"\boil\b|\bbrent\b|\bwti\b|\bopec|crude|gasoline|natural gas|\blng\b",
    "inflation-mondiale": r"inflation|\bcpi\b|consumer price|interest rate|federal reserve|\bfed\b|\becb\b|rate cut|rate hike",
    "crises-bancaires": r"\bbank|deposit|bailout|\bvix\b",
    "politique-americaine": r"\btrump|congress|senate|house of representatives|supreme court|executive order|governor|"
                            r"democrat|republican|white house|shutdown",
    "rivalite-sino-americaine": r"\bchina|chinese|taiwan|xi jinping|tariff|beijing",
    "economie-chinoise": r"\bchina|chinese|yuan|renminbi",
    "securite-europeenne": r"\bnato\b|european union|\beu\b|germany|\bfrance|poland",
    "climat-extremes": r"hurricane|temperature|heat ?wave|drought|wildfire|flood|el ni[nñ]o",
    "epidemies": r"virus|outbreak|pandemic|h5n1|measles|covid|ebola|mpox",
    "elections-amerique-latine": r"brazil|argentin|mexic|venezuela|colombia|\bchile|\bperu\b|bolivia|ecuador",
    "alimentation-mondiale": r"\bfood|wheat|grain|famine|\brice\b",
    "humain": r"protest|\briot|\bstrike\b|referendum|approval rating|\bpoll",
    "sciences-techniques": r"\bai\b|artificial intelligence|openai|anthropic|spacex|\bnasa\b|launch",
    "information-cyber": r"cyber|\bhack|internet shutdown|ransomware|censorship",
    "transport-maritime": r"shipping|\bsuez|red sea|container|panama canal",
    "dette-emergents": r"\bdebt\b|\bimf\b|sovereign|default",
    "non-proliferation": r"nuclear|warhead|missile test|north korea",
    "migrations-demographie": r"migra|refugee|asylum|border crossing",
}


def fiches_de(titre: str) -> list[str]:
    t = (titre or "").lower()
    return [f for f, rx in REGLES.items() if re.search(rx, t)]


class _Coupure:
    """Pendant le calcul d'un état historique, ad.lire ne rend que les valeurs datées ≤ la date de coupure."""
    def __init__(self):
        self.cache: dict[str, list] = {}
        self.date = "9999-12-31"
        self._lire = ad.lire

    def lire(self, nom, reg=ad.REG):
        if nom not in self.cache:
            try:
                self.cache[nom] = self._lire(nom, reg)
            except Exception:
                self.cache[nom] = []
        return [x for x in self.cache[nom] if x[0][:10] <= self.date]


def etats_par_jeu(jeux: list[str]) -> dict[str, dict]:
    """Pour chaque date de jeu : par fiche, (T, M, B) calculés sur la carte coupée à cette date."""
    coupe = _Coupure()
    ad.lire, ancien = coupe.lire, ad.lire
    try:
        c = ca.Carte(calibration=None)
        out = {}
        for j in jeux:
            coupe.date = j
            c._etat = None
            e = c.etat()
            marges = c.marges_de_bascule(10_000)
            par = {}
            for f in REGLES:
                zs = [min(abs(v.get("z") or 0.0), ca.INTENSITE_MAX) for k, v in e.items()
                      if k.startswith(f + ":") and "z" in v and not ca.est_compte_a_rebours(str(v.get("adaptateur", "")))]
                mg = [m["marge"] for m in marges if m["marge"] is not None and m["relation"].startswith(f + ":")]
                par[f] = (float(np.mean(zs)) if zs else 0.0, float(max(zs)) if zs else 0.0,
                          float(max(-3.0, min(3.0, min(mg)))) if mg else 3.0)
            out[j] = par
        return out
    finally:
        ad.lire = ancien


def traits(x: dict, etats: dict) -> list[float]:
    fs = x["fiches"]
    if not fs:
        return [0.0, 0.0, 3.0, 0.0]
    v = [etats[x["jeu"]][f] for f in fs]
    return [float(np.mean([a[0] for a in v])), float(max(a[1] for a in v)), float(min(a[2] for a in v)), 1.0]


def logit(p: float) -> float:
    p = min(0.98, max(0.02, p))
    return math.log(p / (1 - p))


def predire(xs: list[dict], etats: dict) -> None:
    XP = np.array([[1.0, logit(x["p_S"])] for x in xs])
    XC = np.array([[1.0, logit(x["p_S"])] + traits(x, etats) for x in xs])
    y = np.array([x["issue"] for x in xs], dtype=float)
    fin = np.array([max(x["resolue_le"], x.get("cloture", "")) for x in xs])
    for jeu in sorted({x["jeu"] for x in xs}):
        ok = fin < jeu
        cibles = [i for i, x in enumerate(xs) if x["jeu"] == jeu]
        if ok.sum() < 50 or len(set(y[ok])) < 2:
            for i in cibles:
                xs[i]["p_P"] = xs[i]["p_C"] = xs[i]["p_S"]
            continue
        wp, wc = br.ajuster(XP[ok], y[ok]), br.ajuster(XC[ok], y[ok])
        for i in cibles:
            xs[i]["p_P"] = float(min(0.98, max(0.02, 1 / (1 + np.exp(-XP[i] @ wp)))))
            xs[i]["p_C"] = float(min(0.98, max(0.02, 1 / (1 + np.exp(-XC[i] @ wc)))))


def juger(xs: list[dict]) -> dict:
    import essais as es
    cb = bj.cb
    conf = [x for x in xs if x["jeu"] >= bj.COUPURE]
    pm = lambda s, k: round(sum(cb.pl(x[k], x["issue"]) for x in s) / len(s), 4) if s else None
    ec = [(f'{x["source"]}:{x["id"]}', cb.pl(x["p_C"], x["issue"]) - cb.pl(x["p_P"], x["issue"])) for x in conf]
    bas, haut = cb.bootstrap(ec, es.risque_corrige(1))
    tou = [x for x in conf if x["fiches"]]
    et = [(f'{x["source"]}:{x["id"]}', cb.pl(x["p_C"], x["issue"]) - cb.pl(x["p_P"], x["issue"])) for x in tou]
    bt, ht = cb.bootstrap(et, es.risque_corrige(1)) if len(et) >= 30 else (None, None)
    return {"n_confirmation": len(conf), "questions_distinctes": len({k for k, _ in ec}),
            "part_touchee": round(len(tou) / len(conf), 3) if conf else None,
            "perte": {k: pm(conf, k) for k in ("p_S", "p_P", "p_C")},
            "ecart_C_moins_P": round(sum(e for _, e in ec) / len(ec), 4), "intervalle_corrige": [round(bas, 4), round(haut, 4)],
            "verdict": "la carte aide" if haut < 0 else ("la carte nuit" if bas > 0 else "non tranché"),
            "touchees": {"n": len(tou), "perte_P": pm(tou, "p_P"), "perte_C": pm(tou, "p_C"),
                         "intervalle_corrige": [round(bt, 4), round(ht, 4)] if bt is not None else None},
            "risque_corrige": es.risque_corrige(1),
            "par_source": {s: {"n": len(v), "touchees": sum(1 for x in v if x["fiches"]),
                               **{k: pm(v, k) for k in ("p_P", "p_C")}}
                           for s in bj.SOURCES for v in [[x for x in conf if x["source"] == s]] if v},
            "par_fiche": {f: {"n": len(v), "perte_P": pm(v, "p_P"), "perte_C": pm(v, "p_C")}
                          for f in REGLES for v in [[x for x in conf if f in x["fiches"]]] if len(v) >= 20}}


def principal() -> int:
    xs = [json.loads(l) for l in bj.REGISTRE.read_text(encoding="utf-8").splitlines() if l.strip()]
    xs = [x for x in xs if not COMBINEE.search(x.get("titre") or "")]
    xs = bj.cohorte_complete(xs)
    bj.calculer(xs)
    for x in xs:
        x["fiches"] = fiches_de(x["titre"])
    etats = etats_par_jeu(sorted({x["jeu"] for x in xs}))
    predire(xs, etats)
    r = juger(xs)
    av = [x for x in xs if max(x["resolue_le"], x.get("cloture", "")) < bj.COUPURE]
    w = br.ajuster(np.array([[1.0, logit(x["p_S"])] + traits(x, etats) for x in av]), np.array([x["issue"] for x in av], dtype=float))
    r["coefficients_avant_coupure"] = dict(zip(["constante", "logit_S", "T_moyenne_z", "M_max_z", "B_marge", "touchee"],
                                               [round(float(v), 3) for v in w]))
    r["note"] = "perte log, plus bas = mieux ; carte coupée au jour du jeu, sans calibration ; ombre"
    SORTIE.write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(r, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(principal())
