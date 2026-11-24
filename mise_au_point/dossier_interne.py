"""Dossier interne d'une question (prototype, décision de l'auteur du 2026-11-24, 21 h 52 : « D'accord ») : ce que nos
ressources internes disent d'une question, pour le « juge informé ». Faits mesurés et sourcés seulement, aucun avis.

1. briques mesurées qui reconnaissent la question (probabilité, mécanisme, mesure) ;
2. carte : compartiments rattachés, relations qui jouent dans le délai, freins, cycles ;
3. biais du questionneur : part de oui des questions résolues de même structure ;
4. sondes de l'écosystème : lecture et coefficient du moment.

    python mise_au_point/dossier_interne.py "<titre>" <échéance AAAA-MM-JJ>
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from collections import Counter
from functools import lru_cache
from pathlib import Path

ICI = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ICI))


def _briques(titre: str, jour: dt.date, fin: str) -> list[str]:
    out = []
    j = jour.isoformat()

    def essai(nom, f):
        try:
            e = f()
        except Exception:
            e = None
        if e:
            p = e.get("p_regle", e.get("p"))
            if isinstance(p, (int, float)):
                out.append(f"- {nom} : {p:.0%}" + (f" ({e['texte'].strip()[:220]})" if isinstance(e.get("texte"), str) else ""))
    import seuils_prix as spx
    nom = "seuils de prix (marche aléatoire calibrée sur la volatilité du sous-jacent)"
    avant = len(out)
    essai(nom, lambda: spx.estimer(titre, j, spx.echeance(titre, j) or fin))
    q = spx.lire(titre)
    if q and len(out) == avant:
        pts = [d for d, _ in spx.points(q["actif"]) if d < j]
        out.append(f"- {nom} : reconnaît la question ({q['actif']}, seuil {q['k']:g}) mais se tait : dernier prix connu "
                   f"{pts[-1] if pts else 'absent'}, trop ancien (plus de {spx.FRAICHEUR_JOURS} jours)")
    import evenements_regle as evr
    essai("événements comptés", lambda: evr.estimer(titre, j, fin, 0.5))
    import maintien_regle as mr
    essai("maintien au pouvoir (tables de mortalité et de départs, Archigos)", lambda: mr.estimer(titre, j, fin, 0.5, False))
    import escalade_regle as es
    essai("échelle de l'escalade", lambda: es.estimer(titre, 0.5))
    import competitions_regle as cp
    essai("un parmi N (compétitions)", lambda: cp.estimer(titre, 0.5))
    import banque_centrale_regle as bc
    essai("banque centrale (inertie de la Fed, FOMC depuis 1994)", lambda: bc.estimer(titre, jour))
    import accords_etats as ae, accords_mid as am, accords_guerre as ag, accords_regle as ar
    essai("cessez-le-feu (COW, ETH/PRIO)", lambda: ae.estimer(titre, jour))
    essai("tenue d'une trêve (MID, ETH/PRIO)", lambda: am.estimer(titre, jour))
    essai("accord de paix pendant une guerre (UCDP)", lambda: ag.estimer(titre, jour))
    import rencontres_regle as rr, sommets_regle as so, justice_regle as jr
    essai("rencontre au sommet (COLT)", lambda: rr.estimer(titre, jour))
    essai("sommet de l'OTAN (COLT)", lambda: so.estimer(titre, jour))
    essai("Cour suprême (SCDB)", lambda: jr.estimer(titre, jour))
    essai("autres accords (consentements requis)", lambda: ar.estimer_autres(titre))
    return out


@lru_cache(1)
def _taux_structure():
    import structures_questions as sq
    vus, n, o = set(), Counter(), Counter()
    for l in (ICI / "registre" / "jugement-questions.jsonl").read_text(encoding="utf-8").splitlines():
        q = json.loads(l)
        if q["titre"] in vus or str(q.get("issue")) not in ("0", "1"):
            continue
        vus.add(q["titre"])
        s = sq.structure(q["titre"])
        n[s] += 1
        o[s] += str(q["issue"]) == "1"
    return n, o, len(vus), sum(o.values())


@lru_cache(1)
def _lecteurs():
    from mise_au_point.lecture_mecanique import Carte
    import sondes
    return Carte(), sondes.Sondes()


def dossier(titre: str, fin: str, jour: dt.date | None = None) -> str:
    import sondes
    import structures_questions as sq
    jour = jour or dt.date.today()
    horizon = max(1, (dt.date.fromisoformat(fin) - jour).days)
    L = [f"DOSSIER INTERNE (faits mesurés ; {jour.isoformat()}, échéance {fin}, {horizon} jours)"]
    B = _briques(titre, jour, fin)
    L.append("1. Briques mesurées :" if B else "1. Briques mesurées : aucune ne reconnaît cette question (pas de mesure dédiée).")
    L += B
    carte, S = _lecteurs()
    lu = carte.lire(titre, horizon)
    if lu["compartiments"]:
        L.append(f"2. Carte : compartiments {', '.join(lu['compartiments'][:6])}"
                 + (f" ; pays {', '.join(lu['pays'])}" if lu["pays"] else ""))
        rap = sorted(lu["chemins_rapides"], key=lambda e: {"forte": 0, "moyenne": 1}.get(e.get("force"), 2))[:5]
        for e in rap:
            L.append(f"   - {e['de'].split(':')[-1]} → {e['vers'].split(':')[-1]} ({e['effet']}, {e['delai']}, {e['force']}) : {e.get('texte') or ''}"[:200])
        if lu["part_rapide"] is not None:
            L.append(f"   - part des relations entrantes qui jouent avant l'échéance : {lu['part_rapide']:.0%} ; freins rapides : {len(lu['freins_rapides'])}")
        for c in lu["cycles"][:2]:
            L.append(f"   - cycle {c['id']} : phase vulnérable « {c['phase_vulnerable']} »")
    else:
        L.append("2. Carte : aucun compartiment rattaché (lacune de la carte).")
    n, o, tot, oui = _taux_structure()
    s = sq.structure(titre)
    if n[s] >= 20:
        L.append(f"3. Biais du questionneur : questions de structure « {s} » : {o[s] / n[s]:.0%} de oui sur {n[s]} résolues "
                 f"(tout le corpus : {oui / tot:.0%}).")
    else:
        L.append(f"3. Biais du questionneur : tout le corpus : {oui / tot:.0%} de oui sur {tot} questions résolues.")
    E = sondes.etat().get("sondes") or {}
    lec = S.lire(titre, horizon, jour)
    if lec:
        for k, v in lec.items():
            e = E.get(k, {})
            L.append(f"4. Sonde « {k} » : direction {v['d']:+.2f}, sens du oui {v['sens']:+d}, coefficient du moment "
                     f"{e.get('k', 0)} ({'active' if e.get('actif') else 'inactive'}, étalon sur {e.get('etalon', {}).get('lues', 0)} questions)")
    else:
        L.append("4. Sondes : aucune ne lit cette question.")
    return "\n".join(L)


if __name__ == "__main__":
    print(dossier(sys.argv[1], sys.argv[2]))
