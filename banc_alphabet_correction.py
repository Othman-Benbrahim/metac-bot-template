"""Banc de l'alphabet en correction finale à porte, au lieu de dans le jugement (0.10.305).

Décision d'auteur du 2026-11-19, 1 h 22. Idée : GraFT (Pham et al., Spatial-as-Refinement). Préenregistrement :
preenregistrements/alphabet-correction-finale.md. Aucun nouvel appel : notes, p_A, p_M et p_B déjà enregistrés.

    python banc_alphabet_correction.py
"""
from __future__ import annotations

import json
from pathlib import Path

import alphabet_pipeline as ap
import banc_porte as bp

RESUME = Path("registre/banc-alphabet-correction.json")
CLES = ("tendance", "engagements", "decideurs", "declencheur", "freins", "duree", "proportion")
INVERSEES = {"freins"}
GRILLE_ALPHA = [round(-2 + 0.1 * i, 1) for i in range(41)]


def score(notes: dict) -> float | None:
    """Moyenne des 7 notes centrées, dans [−1 ; 1], positif = pousse vers OUI ; None si une note manque."""
    vals = []
    for k in CLES:
        n = notes.get(k)
        n = n.get("note") if isinstance(n, dict) else n
        if n not in (1, 2, 3, 4):
            return None
        vals.append(((5 - n) if k in INVERSEES else n) - 2.5)
    return sum(vals) / len(vals) / 1.5


def preparer(lignes: list[dict], notes_de) -> list[dict]:
    out = []
    for x in lignes:
        s = score(notes_de(x) or {})
        if s is None or x.get("issue") not in (0, 1, "0", "1") or x.get("p_A") is None:
            continue
        out.append({"question_id": x["question_id"], "issue": int(x["issue"]), "p_A": float(x["p_A"]),
                    "p_M": float(x["p_M"]) if x.get("p_M") is not None else None,
                    "p_B": float(x["p_B"]) if x.get("p_B") is not None else None, "score": s})
    return out


def analyser(ls: list[dict], essai: str | None) -> dict:
    import profil_erreurs as pe
    import score_registre as sr
    p, alpha, _ = bp.loo_porte(ls, "p_A", "score", GRILLE_ALPHA)
    out = {"lignes": len(ls), "perte_A": bp.perte(ls, "p_A"), "perte_corrigee": bp.perte(ls, ps=p), "alpha_sur_tout": alpha}
    lignes = [dict(x, p_B=x["p_A"], o={"p": pp}) for x, pp in zip(ls, p)]
    out["critere"] = sr.critere_ombre_b(lignes, "o", essai or "alphabet_correction_finale", exclure_vus=False,
                                        bloc_par="question", tout_juger=True)
    m = [(x, pp) for x, pp in zip(ls, p) if x["p_M"] is not None]
    if m:
        out["secondaire_contre_M"] = {"n": len(m), "perte_M": bp.perte([x for x, _ in m], "p_M"),
                                      "perte_corrigee": bp.perte([x for x, _ in m], ps=[pp for _, pp in m])}
    b = [x for x in ls if x["p_B"] is not None]
    if len(b) >= 30:
        pb, ab, _ = bp.loo_porte(b, "p_B", "score", GRILLE_ALPHA)
        out["secondaire_base_B"] = {"n": len(b), "perte_B": bp.perte(b, "p_B"), "perte_corrigee": bp.perte(b, ps=pb),
                                    "alpha_sur_tout": ab}
    out["unites"] = pe.unites(ls)
    return out


def sans_fuite_stricte(ls: list[dict], p_cle: str = "p_A") -> dict | None:
    """Descriptif : questions sans fuite stricte au banc de la fuite (0.10.300)."""
    import banc_fuite_recherche as bf
    f = bf.lignes()
    if not f:
        return None
    touchees = {bp.q(x["question_id"]) for x in f if bf.stricte(x)}
    reste = [x for x in ls if bp.q(x["question_id"]) not in touchees]
    if len(reste) < 30:
        return None
    p, alpha, _ = bp.loo_porte(reste, "p_A", "score", GRILLE_ALPHA)
    return {"lignes": len(reste), "perte_A": bp.perte(reste, "p_A"), "perte_corrigee": bp.perte(reste, ps=p),
            "alpha_sur_tout": alpha}


def principal() -> int:
    import banc_jugement_alphabet as bja
    import banc_jugement_variantes as bv
    gpt = preparer([x for x in bja.lignes() if not x.get("exclue")], lambda x: x.get("notes"))
    haiku = preparer([dict(x, p_A=(x.get("haiku") or {}).get("p_A"), p_M=(x.get("haiku") or {}).get("p_M"))
                      for x in bv.lignes() if (x.get("haiku") or {}).get("notes")
                      and not (x.get("haiku") or {}).get("exclue") and not (x.get("haiku") or {}).get("connait_issue")],
                     lambda x: (x.get("haiku") or {}).get("notes"))
    r = {"version_bot": ap.VERSION_BOT,
         "note": ("base A (jugement sans alphabet) ; score = moyenne des 7 notes centrées, freins inversé ; "
                  "α appris sans la question jugée ; principal : notes de gpt-5-mini")}
    if len(gpt) < 30:
        r["verdict"] = "trop peu de lignes"
    else:
        r["principal"] = analyser(gpt, "alphabet_correction_finale")
        r["critere_principal"] = r["principal"]["critere"]
        r["descriptif_sans_fuite_stricte"] = sans_fuite_stricte(gpt)
    if len(haiku) >= 30:
        h = analyser(haiku, None)
        h.pop("critere", None)
        r["replique_haiku"] = h
    RESUME.write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(r, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(principal())
