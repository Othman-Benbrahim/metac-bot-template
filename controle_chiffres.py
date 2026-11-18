"""Contrôle des chiffres : tout nombre écrit à la main doit se retrouver dans le résultat brut (bot 0.10.295).

Décision d'auteur du 2026-11-18, 21 h 48 (« oui, et il faudrait l'automatiser »). Origine : erreurs de recopie de
Claude (309 lignes présentées comme 309 questions ; lecture erronée des refus d'Azure). Idée reprise du journal de
contrôle qualité de Za1d7/sp500-financial-market-analysis.

Trois usages :
1. `bloc_chiffres(resume)` : la partie chiffrée d'une fiche, écrite par le code à partir du résumé JSON d'un banc.
2. `verifier(texte, sources)` : chaque nombre du texte est cherché parmi les valeurs des sources (arrondi selon les
   décimales écrites, pourcentages, valeur absolue) ; les introuvables sont rendus. Un nombre CALCULÉ à la main
   s'écrit avec sa formule entre crochets, recalculée ici : [calc: 0,6572 - 0,6588 = -0,0016]. Un chiffre lu dans
   le journal d'un run (hors JSON) se déclare ainsi : [journal: coût 0,41 $] ; il n'est pas vérifié, mais il est visible.
3. Automatisé : les fiches de résultats sont gardées dans fiches/ (en-tête « sources: ») et les verdicts d'essais
   portent leur fichier de résultat (« resume ») ; tests/test_controle_chiffres.py les vérifie à chaque envoi.

    python controle_chiffres.py fiches/x.md            # sources lues dans l'en-tête de la fiche
    python controle_chiffres.py --bloc registre/banc-x.json
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

NOMBRE = re.compile(r"(?<![\w.,])([−\-+]?)(\d{1,3}(?:[   ]\d{3})+|\d+)(?:[.,](\d+))?(?![\w])")
CALC = re.compile(r"\[calc:\s*([^=\]]+)=\s*([^\]]+)\]")
JOURNAL = re.compile(r"\[(?:journal|estimation):[^\]]*\]")       # chiffre lu dans le journal d'un run, hors JSON : déclaré, non vérifié


def _flottant(signe: str, entier: str, dec: str | None) -> tuple[float, int]:
    s = re.sub(r"[   ]", "", entier) + (("." + dec) if dec else "")
    v = float(s)
    return (-v if signe in ("−", "-") else v), len(dec or "")


def ignorable(texte: str, debut: int, fin: int, v: float, d: int) -> bool:
    """Ce qui n'est pas un résultat : années, dates, heures, versions, numéros de run, renvois de section."""
    avant, apres = texte[max(0, debut - 12):debut], texte[fin:fin + 4]
    if d == 0 and 1900 <= abs(v) <= 2100:
        return True                                   # année
    if re.match(r"[-/:h]\d| ?h ?\d", apres) or re.search(r"\d[-/:]$|\d h ?$", avant):
        return True                                   # date ou heure
    if re.search(r"(0\.10\.|v|bot |version |§ ?|run |ch\. ?|p\. ?|chapitre |Q|Haiku |Sonnet |Opus |Fable |Mythos )$", avant):
        return True                                   # version, section, run, page
    if re.search(r"[A-Za-z]-$", avant) or re.match(r"-[A-Za-z]", apres):
        return True                                   # nom de modèle ou de produit (gpt-5-mini, Qwen3-4B…)
    if d == 0 and abs(v) >= 10_000_000:
        return True                                   # identifiant (run GitHub…)
    return False


def nombres(texte: str) -> list[tuple[str, float, int]]:
    """(écrit, valeur, décimales) de chaque nombre du texte, calculs entre crochets exclus."""
    propre = re.sub(r"^(sources|constantes):.*$", " ", JOURNAL.sub(" ", CALC.sub(" ", texte)), flags=re.M)
    out = []
    for m in NOMBRE.finditer(propre):
        v, d = _flottant(m.group(1), m.group(2), m.group(3))
        if not ignorable(propre, m.start(), m.end(), v, d):
            out.append((m.group(0).strip(), v, d))
    return out


def valeurs(obj) -> list[float]:
    """Toutes les valeurs numériques d'un résumé JSON, y compris celles écrites dans ses textes."""
    out: list[float] = []
    if isinstance(obj, bool):
        return out
    if isinstance(obj, (int, float)):
        return [float(obj)]
    if isinstance(obj, str):
        return [v for _, v, _ in nombres(obj)]
    if isinstance(obj, dict):
        for k, v in obj.items():
            out += valeurs(v)
        return out
    if isinstance(obj, list):
        out.append(float(len(obj)))
        for v in obj:
            out += valeurs(v)
    return out


def correspond(x: float, d: int, vals: list[float]) -> bool:
    for v in vals:
        for w in (v, v * 100):
            for s in (w, abs(w), -w):
                if abs(s - x) <= 10 ** (-d) / 2 + 1e-6:          # arrondi au plus proche, demi vers le haut compris
                    return True
    return False


def verifier_calculs(texte: str) -> list[str]:
    erreurs = []
    for expr, res in CALC.findall(texte):
        e = expr.replace(",", ".").replace("−", "-").replace("×", "*")
        if not re.fullmatch(r"[\d.\s+\-*/()]+", e):
            erreurs.append(f"calcul illisible : {expr}")
            continue
        r = res.strip().replace(",", ".").replace("−", "-")
        try:
            attendu, ecrit = eval(e, {"__builtins__": {}}), float(r)   # noqa: S307 (chiffres et opérateurs seulement)
        except Exception:
            erreurs.append(f"calcul illisible : {expr} = {res}")
            continue
        d = len(r.split(".")[1]) if "." in r else 0
        if abs(round(attendu, d) - ecrit) > 10 ** (-d) / 2 + 1e-9:
            erreurs.append(f"calcul faux : {expr} = {res} (vaut {attendu:.{d + 2}f})")
    return erreurs


def verifier(texte: str, sources: list[Path]) -> dict:
    vals: list[float] = constantes_de(texte)
    for s in sources:
        vals += valeurs(json.loads(Path(s).read_text(encoding="utf-8")))
    vals += [v for _, v, _ in nombres(" ".join(r for _, r in CALC.findall(texte)))]   # résultats des calculs vérifiés
    introuvables = [ecrit for ecrit, v, d in nombres(texte) if not correspond(v, d, vals)]
    return {"nombres": len(nombres(texte)), "introuvables": introuvables, "calculs": verifier_calculs(texte)}


def sources_de(fiche: str) -> list[Path]:
    m = re.search(r"^sources:\s*(.+)$", fiche, re.M)
    return [Path(s.strip()) for s in m.group(1).split(",")] if m else []


def constantes_de(fiche: str) -> list[float]:
    """Nombres de CONCEPTION déclarés en tête (« constantes: 7, 90, 500 ») : nombre de cartes, niveaux, tirages."""
    m = re.search(r"^constantes:\s*(.+)$", fiche, re.M)
    return [float(x.strip().replace(",", ".")) for x in m.group(1).split(";")] if m else []


def _f(v, d: int = 4) -> str:
    return "—" if v is None else (f"{v:.{d}f}".replace(".", ",") if isinstance(v, float) else str(v))


def bloc_chiffres(r: dict) -> str:
    """La partie chiffrée d'une fiche, écrite par le code (jamais recopiée à la main)."""
    lignes = ["## Chiffres (écrits par controle_chiffres.bloc_chiffres, à ne pas retoucher)"]

    def critere(nom: str, c: dict):
        if isinstance(c, dict) and "ecart_moyen" in c:
            b, h = c.get("intervalle_90_par_blocs") or [None, None]
            bc, hc = c.get("intervalle_corrige") or [None, None]
            lignes.append(f"- {nom} : écart {_f(c['ecart_moyen'], 4)} ; intervalle 90 % [{_f(b)} ; {_f(h)}] ; corrigé "
                          f"[{_f(bc)} ; {_f(hc)}] ; {c.get('n_juge')} lignes, {c.get('blocs')} blocs ; {c.get('verdict')}")

    def parcourir(obj, chemin=""):
        if not isinstance(obj, dict):
            return
        for k, v in obj.items():
            ch = f"{chemin}.{k}" if chemin else k
            if k in ("critere", "critere_principal", "secondaire_toutes", "secondaire_contre_S"):
                critere(ch, v)
            elif k == "unites" and isinstance(v, dict) and "questions_distinctes" in v:
                lignes.append(f"- unités : {v['lignes']} lignes, {v['questions_distinctes']} questions distinctes, "
                              f"{v.get('questions_oui_distinctes')} oui")
            elif k.startswith("perte") and isinstance(v, (int, float)):
                lignes.append(f"- {ch} : {_f(float(v))}")
            elif k.startswith("perte") and isinstance(v, dict) and all(isinstance(x, (int, float)) for x in v.values()):
                lignes.append(f"- {ch} : " + " ; ".join(f"{a} {_f(float(b))}" for a, b in v.items()))
            elif isinstance(v, dict):
                parcourir(v, ch)
    parcourir(r)
    return "\n".join(lignes)


def principal(args: list[str]) -> int:
    if args and args[0] == "--bloc":
        print(bloc_chiffres(json.loads(Path(args[1]).read_text(encoding="utf-8"))))
        return 0
    code = 0
    for f in args:
        t = Path(f).read_text(encoding="utf-8")
        r = verifier(t, sources_de(t))
        etat = "OK" if not r["introuvables"] and not r["calculs"] else "À VÉRIFIER"
        print(f"{f} : {etat} ({r['nombres']} nombres) ; introuvables {r['introuvables']} ; calculs {r['calculs']}")
        code |= etat != "OK"
    return code


if __name__ == "__main__":
    sys.exit(principal(sys.argv[1:]))
