#!/usr/bin/env python3
"""Alphabet situationnel 0.7.56 — calcul expérimental, validation et traçabilité.
Bibliothèque standard Python 3.8+. `autotest` exécute les contrôles de régression.
Les analogies structurales sont des hypothèses, jamais une calibration acquise.
Auteur : Othman Ben Brahim · Licence MIT (voir LICENSE).
"""
import argparse, calendar, contextlib, datetime, hashlib, io, json, math, os, re, sys, unicodedata
from collections import defaultdict
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
P = json.loads((RACINE / "assets/parametres.json").read_text(encoding="utf-8"))
NOMS = P["cartes"]
NS = P["nombre_strates"]  # nombre de strates (O3) ; toute borne 1..NS en dépend
QUALIFS = {"rétroaction amplifiante", "rétroaction stabilisante", "multi-échelle", "délai", "multi-strate"}
DEGRADE = {"F": "M", "M": "f", "f": None}
UNITES = {"jour": 1., "jours": 1., "semaine": 7., "semaines": 7., "mois": 30.4375, "an": 365.25, "ans": 365.25}
MOT_RE = re.compile(r"^(?P<c>[^@\[\]{}]+)@(?P<s>\d{1,2})\[(?P<i>[Ff])\](?P<q>(?: \{[^}]+\}){0,2})$")
ETAT_RE = re.compile(r"^\[(?P<d>\d{4}-\d{2}(?:-\d{2})?) \| (?P<f>\d+ (?:jours?|semaines?|mois|ans?))\] (?P<corps>.+)$")

def _plat(s):
    s = unicodedata.normalize("NFD", s)
    return "".join(ch for ch in s if unicodedata.category(ch) != "Mn").upper().replace(" ", "").replace("·", "")


_INDEX = {}
for _ab, _nom in NOMS.items():
    _INDEX[_plat(_ab)] = _ab
    _INDEX[_plat(_nom)] = _ab
_INDEX["TRACE"] = "TRC"


def carte_id(s):
    k = _plat(s.strip())
    if k not in _INDEX:
        raise ValueError(f"carte inconnue : {s!r}")
    return _INDEX[k]



def cle(m):
    return f'{m["c"]}@{m["s"]}'



def forces_changees(a, b):
    """Mots présents dans deux états successifs avec une force différente (F ↔ f)."""
    fa = {cle(m): m["i"] for m in a["mots"]}
    return {cle(m) for m in b["mots"] if cle(m) in fa and fa[cle(m)] != m["i"]}



def lire_cle(t):
    c, s = t.strip().split("@")
    return f"{carte_id(c)}@{int(s)}"



def erreurs_g6(etat):
    err = []
    vus = set()
    for m in etat["mots"]:
        if not 1 <= m["s"] <= NS:
            err.append(f"{cle(m)} : strate hors de 1–{NS}")
        if cle(m) in vus:
            err.append(f"{cle(m)} : carte répétée dans la même strate (G6)")
        vus.add(cle(m))
        if len(m["q"]) != len(set(m["q"])) or len(m["q"]) > 2:
            err.append(f"{cle(m)} : qualificatifs répétés ou plus de deux (G1)")
        for q in m["q"]:
            if q not in QUALIFS:
                err.append(f"{cle(m)} : qualificatif inconnu {{{q}}} (G1)")
    return err



_STATUTS_CACHE = {}


def statuts():
    """Statut de chaque équivalent (carte, strate), relu si un fichier de strate a changé."""
    d = os.path.join(RACINE, "references", "equivalences")
    fichiers = [os.path.join(d, f"strate-{s:02d}.md") for s in range(1, NS + 1)]
    cle_ = tuple(os.path.getmtime(f) if os.path.exists(f) else None for f in fichiers)
    if _STATUTS_CACHE.get('cle') == cle_:
        return dict(_STATUTS_CACHE['st'])
    st = {}
    for s, f in enumerate(fichiers, 1):
        if not os.path.exists(f):
            continue
        for l in open(f, encoding="utf-8"):
            m = re.match(r"^\| (\S+) \|.*\| (Attesté|Documenté|Proposé|Vide|Hors domaine) \| [^|]* \|\s*$", l)
            if m:
                try:
                    st[(carte_id(m.group(1)), s)] = m.group(2)
                except ValueError:
                    pass
    _STATUTS_CACHE.update(cle=cle_, st=st)
    return dict(st)


def recherches_vide():
    """0.6.5. Critère de clôture des cases Vides (décision 1b) : la colonne Référence d'une case Vide
    déclare « recherches : N — … » (sources, période, marqueur testé). À N ≥ vide_recherches_cloture
    (§H), la case est close « non concluant » : elle reste Vide, mais compte comme traitée. Sans ce
    critère, rien ne distingue « pas encore cherché » de « cherché trois fois, rien trouvé »."""
    d = os.path.join(RACINE, "references", "equivalences"); r = {}
    for s in range(1, NS + 1):
        f = os.path.join(d, f"strate-{s:02d}.md")
        if not os.path.exists(f): continue
        for l in open(f, encoding="utf-8"):
            m = re.match(r"^\| (\S+) \|.*\| Vide \| ([^|]*) \|\s*$", l)
            if m:
                n = re.match(r"\s*recherches\s*:\s*(\d+)\s*—", m.group(2))
                try: r[(carte_id(m.group(1)), s)] = int(n.group(1)) if n else 0
                except ValueError: pass
    return r


def hors_domaine(k):
    c, s = k.split('@')
    return statuts().get((c, int(s))) == 'Hors domaine'


def voisines():
    """Voisines de chaque carte, lues dans `cartes.md` (listes « À ne pas confondre avec »)."""
    out, cur, dans = {}, None, False
    for l in (RACINE/'references'/'cartes.md').read_text(encoding='utf-8').splitlines():
        if l.startswith('## '):
            try:
                cur = carte_id(l[3:]); out[cur] = set()
            except ValueError:
                cur = None
            dans = False
        elif l.startswith('**À ne pas confondre avec**'):
            dans = True
        elif dans and cur:
            m = re.match(r'^- \*([^*]+)\*', l)
            if m:
                out[cur].add(carte_id(m.group(1)))
            elif l.startswith('**'):
                dans = False
    return out


def hors_parentheses(texte_, sep):
    """Découpe sur `sep` au niveau zéro des parenthèses seulement (0.7.42)."""
    out, cur, prof = [], [], 0
    for ch in texte_:
        if ch == '(': prof += 1
        elif ch == ')': prof = max(0, prof - 1)
        if ch == sep and prof == 0:
            out.append(''.join(cur)); cur = []
        else:
            cur.append(ch)
    out.append(''.join(cur))
    return out


def verdicts_a6(ligne, raisons=False):
    """{carte: verdict} (ou {carte: (verdict, raison)}) d'une ligne A6 « CARTE@s : VOISINE → (raison) ; … »."""
    corps = ligne.split(':', 1)[1] if ':' in ligne else ligne
    out = {}
    # 0.7.42 (test T7) : un « ; » dans une raison entre parenthèses coupait le segment ; on coupe hors parenthèses.
    for seg in hors_parentheses(corps, ';'):
        m = re.match(r'^\s*(.+?)\s*(→|\+|←|\?)\s*\((.*)\)\s*$', seg.strip(), re.S)
        if m:
            try:
                out[carte_id(m.group(1))] = (m.group(2), m.group(3).strip()) if raisons else m.group(2)
            except ValueError:
                pass
    return out


def controle_a6(k, ligne):
    """Erreurs A6 d'un mot Fort : chaque voisine de `cartes.md` passée, tranchée pour la carte, justifiée.
    `→` (la question tranche pour cette carte) et `+` (voisine aussi présente, par d'autres faits) sont
    seuls compatibles avec F : `?` laisse la question ouverte, `←` attribue l'unique fait du mot à la
    voisine, qui ne compte alors plus pour cette carte."""
    v = verdicts_a6(ligne, raisons=True); attendues = voisines().get(k.split('@')[0], set())
    err = []
    if attendues - set(v):
        err.append(f'{k} : voisines non passées dans la ligne A6 {sorted(NOMS[x] for x in attendues - set(v))}')
    if any(r == '?' for r, _ in v.values()):
        err.append(f'{k} : voisine non tranchée (?) → au plus f')
    cedees = sorted(NOMS[x] for x, (r, _) in v.items() if r == '←')
    if cedees:
        err.append(f'{k} : fait attribué à la voisine (←) {cedees} → il ne compte pas pour cette carte, F impossible')
    vides = sorted(NOMS[x] for x, (_, j) in v.items() if not j)
    if vides:
        err.append(f'{k} : justification vide pour {vides} (A6 : obligatoire)')
    return err


PORTEES = ('marginale', 'substantielle', 'dominante', 'aucune')


INDETERMINE = 'indetermine'
STATUTS_QUESTION = ('ouverte', 'partielle', 'resolue', 'presuppose_invalide')


def controle_questions(qs, fm, requis, reel=False):
    """0.6.0. Abduction : une lecture produit les questions que la situation rend posables, chacune
    départageant deux cartes. Forme : [{question, si_oui, si_non}], si_oui ≠ si_non (CARTE@strate),
    l'une au moins présente dans l'état. Une question dont les deux réponses mènent à la même carte est
    décorative et refusée. Exigée pour le premier état non nul d'un cas réel.

    0.7.2 (sémantique inquisitive : Ciardelli, Groenendijk et Roelofsen 2019, ch. 2 et 5). Une question
    se définit par ses **conditions de résolution** : ce qui y répondrait, et ce que chaque réponse
    établit. « Non A » ne vaut pas « B » : une branche peut mener à `"indetermine"` (le codage reste
    ouvert ; c'est un état de l'information, pas une issue du monde). Pour un cas réel, chaque question
    de discrimination porte `resolution` (l'observation et la source qui répondraient) et
    `justification` {oui, non} (pourquoi cette réponse établit cette carte). Une question de
    `type: "documentation"` cherche la preuve qui manque à un ancrage (`carte`, `manque`) : utile, elle
    ne remplace pas la question qui départage. `statut` (ouverte, partielle, resolue,
    presuppose_invalide) trace ce qui a été levé, par quelle `preuve`. Le moteur vérifie la forme et
    la cohérence des déclarations, pas la justesse d'une justification."""
    if qs is None:
        return ['questions requises au premier état d’un cas réel : au moins une question qui départage deux cartes'] if requis else []
    if not isinstance(qs, list) or (requis and not qs):
        return ['questions = liste non vide de {question, si_oui, si_non}']
    err = []; discrimination = 0
    for q in qs:
        if not isinstance(q, dict) or not isinstance(q.get('question'), str) or not q['question'].strip():
            err.append('question sans texte'); continue
        t = q['question'][:40]
        typ = q.get('type', 'discrimination')
        if typ not in ('discrimination', 'documentation'):
            err.append(f'« {t}… » : type = discrimination ou documentation'); continue
        if reel and not (isinstance(q.get('resolution'), str) and q['resolution'].strip()):
            err.append(f'« {t}… » : resolution requise pour un cas réel (quelle observation, dans quelle source, répondrait)')
        st = q.get('statut')
        if st is not None:
            if st not in STATUTS_QUESTION:
                err.append(f'« {t}… » : statut = {", ".join(STATUTS_QUESTION)}')
            elif st != 'ouverte' and not (isinstance(q.get('preuve'), str) and q['preuve'].strip()):
                err.append(f'« {t}… » : statut {st} sans preuve (ce qui a levé ou invalidé la question)')
            elif st == 'resolue' and typ == 'discrimination' and q.get('reponse') not in ('oui', 'non'):
                err.append(f'« {t}… » : question résolue sans reponse (oui ou non)')
        if typ == 'documentation':
            try:
                k = cle_valide(str(q.get('carte', '')))
            except (ValueError, IndexError):
                err.append(f'« {t}… » : une question de documentation nomme la carte (CARTE@strate) dont elle documente l’ancrage'); continue
            if k not in fm:
                err.append(f'« {t}… » : {k} n’est pas dans l’état')
            if not (isinstance(q.get('manque'), str) and q['manque'].strip()):
                err.append(f'« {t}… » : manque requis (la preuve qui fait défaut à l’ancrage)')
            continue
        discrimination += 1
        branches = {}
        for b in ('si_oui', 'si_non'):
            v = str(q.get(b, ''))
            if v == INDETERMINE:
                branches[b] = None; continue
            try:
                branches[b] = cle_valide(v)
            except (ValueError, IndexError):
                branches[b] = False
        if False in branches.values():
            err.append(f'« {t}… » : si_oui et si_non doivent être des CARTE@strate (ou « {INDETERMINE} »)'); continue
        a, b = branches['si_oui'], branches['si_non']
        if a is None and b is None:
            err.append(f'« {t}… » : les deux réponses laissent le codage indéterminé, la question ne départage rien'); continue
        if a == b:
            err.append(f'« {t}… » : les deux réponses mènent à {a}, question décorative'); continue
        if a not in fm and b not in fm:
            err.append(f'« {t}… » : aucune des deux cartes n’est dans l’état'); continue
        if reel:
            j = q.get('justification')
            if not isinstance(j, dict):
                err.append(f'« {t}… » : justification {{oui, non}} requise pour un cas réel (pourquoi cette réponse établit cette carte)'); continue
            for rep, cible in (('oui', a), ('non', b)):
                if cible is not None and not (isinstance(j.get(rep), str) and j[rep].strip()):
                    err.append(f'« {t}… » : justification.{rep} requise (pourquoi « {rep} » établit {cible} ; « non A » ne vaut pas « B »)')
            if all(isinstance(j.get(r), str) for r in ('oui', 'non')) and ' '.join(j['oui'].lower().split()) == ' '.join(j['non'].lower().split()):
                err.append(f'« {t}… » : justifications identiques pour oui et non')
    if requis and qs and not discrimination and not err:
        err.append('au moins une question de discrimination (si_oui, si_non) au premier état : une question de documentation ne départage pas deux cartes')
    return err


def controle_garantie(k, item, requis):
    """0.6.0. Garantie : le troisième terme de l'ancrage (interprétant de Peirce et test de clôture) —
    par quel *mécanisme* le fait est une instance de la carte, ce que la carte rend *attendu*, ce qui la
    *contredirait*. Option : le filtre de pertinence — un *acteur* (« le système » admis) et l'option
    qu'il avait *avant* et n'a plus *après*, ou l'inverse. Requis pour un mot F de cas réel ; s'il est
    fourni pour un mot f, il est contrôlé de la même façon. Le moteur vérifie la forme, pas la justesse."""
    err = []
    for champ, cles in (('garantie', ('mecanisme', 'attendu', 'contredirait')), ('option', ('acteur', 'avant', 'apres'))):
        v = item.get(champ)
        if v is None:
            if requis: err.append(f'{k} : champ {champ} requis pour F ({", ".join(cles)})')
            continue
        if not isinstance(v, dict) or any(not isinstance(v.get(x), str) or not v[x].strip() for x in cles):
            err.append(f'{k} : {champ} = objet avec {", ".join(cles)} renseignés')
    g = item.get('garantie')
    if isinstance(g, dict) and isinstance(g.get('contredirait'), str) and isinstance(item.get('contre_observation'), str):
        if ' '.join(g['contredirait'].lower().split()) == ' '.join(item['contre_observation'].lower().split()):
            err.append(f'{k} : la contre-observation est exactement ce qui contredirait la carte → la carte n\u2019est pas ancrée (A6, A7)')
    # 0.7.10 (Toulmin, lu par Plantin : une réfutation qui n'annule rien n'est pas une réfutation). Un
    # « contredirait » identique à l'« attendu » ne peut pas défaire la carte : forme refusée.
    if isinstance(g, dict) and all(isinstance(g.get(x), str) and g[x].strip() for x in ('attendu', 'contredirait')):
        if ' '.join(g['attendu'].lower().split()) == ' '.join(g['contredirait'].lower().split()):
            err.append(f'{k} : garantie.contredirait identique à garantie.attendu → ce qui réfuterait la carte doit pouvoir l\u2019annuler (Toulmin)')
    o = item.get('option')
    if isinstance(o, dict) and isinstance(o.get('avant'), str) and isinstance(o.get('apres'), str):
        if ' '.join(o['avant'].lower().split()) == ' '.join(o['apres'].lower().split()):
            err.append(f'{k} : option identique avant et après → le fait ne change l\u2019espace d\u2019action de personne (pertinence, O1)')
    return err


SUPPORTS = ('texte', 'loi', 'donnee', 'cas')


def controle_support(k, item, requis, asof=None):
    """0.7.10. Support du mécanisme (*backing* de Toulmin 1958, ch. III ; Plantin 2021). Le mécanisme est
    une loi de passage ; sa justesse reste un jugement, mais il doit dire **sur quoi il repose**, et la
    régression du support s'arrête dans un texte, une loi, une donnée publiée ou un cas codé — jamais dans
    un autre argument (`type: argument` est refusé : régression ouverte, le mécanisme est un *rabbit*).
    Disponible au plus tard à la date d'information (B1). Requis pour un mot F de cas réel codé sous 0.7.10
    ou après, et pour tout dossier ; contrôlé de la même façon s'il est fourni ailleurs. Le moteur vérifie
    la présence, le type et la date, pas la pertinence."""
    g = item.get('garantie')
    if not isinstance(g, dict): return []
    s = g.get('support')
    if s is None:
        return [f'{k} : garantie.support requis depuis 0.7.10 ({{type: {"|".join(SUPPORTS)}, reference, disponible_le}}) : sur quoi repose le mécanisme'] if requis else []
    if not isinstance(s, dict): return [f'{k} : garantie.support = objet {{type, reference, disponible_le}}']
    err = []
    if s.get('type') == 'argument':
        err.append(f'{k} : garantie.support de type « argument » refusé : la régression du support s\u2019arrête dans un texte, une loi, une donnée ou un cas, jamais dans un autre argument')
    elif s.get('type') not in SUPPORTS:
        err.append(f'{k} : garantie.support.type parmi {", ".join(SUPPORTS)}')
    if not (isinstance(s.get('reference'), str) and s['reference'].strip()):
        err.append(f'{k} : garantie.support.reference requise (titre, article, série ou id de cas)')
    try:
        d = date_iso(s.get('disponible_le'))
        if asof is not None and d > date_iso(asof):
            err.append(f'{k} : garantie.support disponible le {s["disponible_le"]}, après la date d\u2019information {asof} (B1)')
    except ValueError:
        err.append(f'{k} : garantie.support.disponible_le = date AAAA-MM-JJ')
    if isinstance(g.get('mecanisme'), str) and isinstance(s.get('reference'), str) and \
            ' '.join(g['mecanisme'].lower().split()) == ' '.join(s['reference'].lower().split()):
        err.append(f'{k} : garantie.support reformule le mécanisme : un support n\u2019est pas la loi qu\u2019il soutient')
    return err


TESTS_PREUVE = {'paille': 'straw-in-the-wind', 'cerceau': 'hoop', 'pistolet': 'smoking gun', 'double': 'doubly decisive'}
TESTS_SUFFISANTS = ('pistolet', 'double')


def controle_test(k, item, force, requis):
    """0.7.0. Tests de process tracing (Van Evera 1997 ; Collier 2011, PS 44(4), p. 825-827). Hypothèse
    testée : « la carte est active dans la strate ». Le fait d'ancrage déclare son test :
    paille (ni nécessaire ni suffisant), cerceau (nécessaire : son absence élimine la carte, sa présence
    ne la confirme pas — remplir le marqueur en est un), pistolet (suffisant : on ne l'observerait
    presque pas si la carte était fausse), double (nécessaire et suffisant). **F exige un test
    suffisant** : un fait qui remplit seulement le marqueur est un cerceau passé, il donne f. Le moteur
    vérifie la cohérence de la déclaration, pas sa justesse."""
    t = item.get('test')
    if t is None:
        return [f'{k} : champ test requis pour F de cas réel (pistolet ou double : un fait suffisant)'] if requis else []
    if not isinstance(t, str) or t not in TESTS_PREUVE:
        return [f'{k} : test = paille, cerceau, pistolet ou double']
    if force == 'F' and t not in TESTS_SUFFISANTS:
        return [f'{k} : F exige un test suffisant (pistolet ou double) ; un {t} ({TESTS_PREUVE[t]}) ne confirme pas la carte → f']
    return []


def controle_source(k, item):
    """0.7.1 (audit hacker.ai) : traçabilité facultative d'un fait. `source_url` (http ou https, sans
    espace) et `date_consultation` (AAAA-MM-JJ) ; contrôlés s'ils sont présents."""
    err=[]
    u=item.get('source_url')
    if u is not None and not (isinstance(u,str) and re.fullmatch(r'https?://\S+',u)):
        err.append(f'{k} : source_url = adresse http(s) sans espace')
    d=item.get('date_consultation')
    if d is not None:
        try:date_iso(d)
        except ValueError:err.append(f'{k} : date_consultation au format AAAA-MM-JJ')
    return err


CLASSES_SOURCE = ('contemporain', 'historiographie', 'memoire')


def controle_classe_source(k, item, requis):
    """0.7.5. Une base codée après coup peut encoder l'historiographie plutôt que les situations : un récit
    rétrospectif reconstruit selon des schémas (Bartlett 1932) et la couverture des sources varie avec ce
    qu'elles rapportent (biais de signalement, Weidmann 2016). `classe_source` dit d'où vient le fait :
    `contemporain` (produit au moment des faits), `historiographie` (analyse postérieure), `memoire`
    (témoignage ou récit rétrospectif). Requis pour tout mot documenté d'un cas réel actif ; il permettra
    de comparer les taux de transition par classe. Aucun effet sur le calcul."""
    v=item.get('classe_source')
    if v is None:
        return [f'{k} : classe_source requise pour un cas réel actif ({", ".join(CLASSES_SOURCE)})'] if requis else []
    return [] if v in CLASSES_SOURCE else [f'{k} : classe_source = {", ".join(CLASSES_SOURCE)}']


FIABILITES = ('A','B','C','D','E','F')


def controle_grille(k, item):
    """0.7.32 (audit DeepSeek, P0.2). Grille à deux axes du renseignement (code de l'Amirauté, repris par
    l'OTAN, STANAG 2511) : fiabilité de la source, A (sûre) à E (peu sûre), F (non évaluable) ; crédibilité de
    l'information, 1 (confirmée par d'autres sources) à 5 (improbable), 6 (non évaluable). Facultative ; si elle
    est remplie, un ancrage F exige une source A à C **et** une information 1 à 3 : une source douteuse ou une
    information non recoupée n'ancre pas fort. Aucun effet sur le calcul."""
    fs,cr=item.get('fiabilite_source'),item.get('credibilite')
    err=[]
    if fs is not None and fs not in FIABILITES:err.append(f'{k} : fiabilite_source = A à F')
    if cr is not None and (type(cr) is not int or not 1<=cr<=6):err.append(f'{k} : credibilite = entier de 1 à 6')
    if not err and item.get('intensite')=='F' and ((fs is not None and fs not in 'ABC') or (cr is not None and cr>3)):
        err.append(f'{k} : ancrage F refusé, source {fs or "?"}{cr or "?"} (F exige une source A à C et une information 1 à 3)')
    return err


CRITERES_INDEPENDANCE = ('origine', 'producteur', 'transmission')


def controle_corroboration(k, item, independance_requise=False):
    """0.6.6. Contrôle de la qualité de l'information (CIA, *Tradecraft Primer* ; Mulligan 2026 sur les
    sources fabriquées par IA générative). Un mot F de cas réel **actif** déclare si son fait repose sur
    des sources indépendantes ou sur une source unique : `corroboration` = "independantes" (le champ
    `source` en nomme au moins deux, séparées par « ; ») ou "unique" (admis, signalé à l'utilisateur).
    Aucun poids, aucun effet sur le calcul : la déclaration seule, qui peut échouer."""
    v = item.get('corroboration')
    if v is None:
        return [f'{k} : champ corroboration requis pour F de cas actif ("independantes" ou "unique")']
    if v not in ('independantes', 'unique'):
        return [f'{k} : corroboration = "independantes" ou "unique"']
    if v == 'independantes' and len([x for x in str(item.get('source', '')).split(';') if x.strip()]) < 2:
        return [f'{k} : corroboration "independantes" mais une seule source nommée (séparer les sources par « ; »)']
    # 0.7.11 (open-ontologies : deux moteurs qui s'accordent sans être indépendants). Deux identifiants
    # distincts peuvent partager une origine (deux dépêches du même fil, deux articles citant le même
    # rapport) : leur accord ne protège que des erreurs de transcription. `independance` nomme ce qui rend
    # les deux pièces indépendantes : origine, producteur ou chaîne de transmission distincts, et pourquoi.
    ind = item.get('independance')
    if v == 'independantes' and ind is None:
        return [f'{k} : corroboration "independantes" sans independance {{critere: {"|".join(CRITERES_INDEPENDANCE)}, motif}} (requis depuis 0.7.11) : ce qui rend les deux pièces indépendantes'] if independance_requise else []
    if ind is not None:
        if v != 'independantes':
            return [f'{k} : independance déclarée pour une source unique']
        if not isinstance(ind, dict) or ind.get('critere') not in CRITERES_INDEPENDANCE or not (isinstance(ind.get('motif'), str) and ind['motif'].strip()):
            return [f'{k} : independance = {{critere: {"|".join(CRITERES_INDEPENDANCE)}, motif}} (motif non vide)']
    return []


RELATIONS_PASSAGE = ('soutient', 'partiel', 'contredit', 'absent_de_la_piece', 'non_soutenu', 'insuffisant')
# 0.7.16 (Copley 2009, « fate-in-hindsight », et sa transposition au français) : forme de la pièce.
# prospective : antérieure à l'issue, ou datée et sans récit de l'issue ; retrospective : décrit le fait à
# travers son issue (« il devait devenir roi ») ; attribuee : rapporte sans assumer (conditionnel de
# reprise, « selon », discours rapporté) ; inclassable : non datable. Facultatif ; contrôlé s'il est fourni.
FORMES_PIECE = ('prospective', 'retrospective', 'attribuee', 'inclassable')


def controle_passage(k, item, force, requis):
    """0.7.2 (OpenScholar : Asai et al. 2024, contrôle affirmation–passage ; Shao). Une source réelle et
    pertinente ne prouve pas pour autant le fait tel qu'il est écrit : « peut être activé » ne soutient
    pas « a été activé ». `passage` (objet ou liste) relie le fait au passage lu : `localisation`
    (page, section, paragraphe, horodatage), `extrait` facultatif (court), `relation` : soutient,
    partiel, contredit ou insuffisant. Une pièce qui contredit va en contre-observation (A7) ; une pièce
    qui ne permet pas de conclure n'ancre rien. **F exige au moins un passage qui soutient** ; une
    corroboration « independantes » en exige deux. Requis pour F de cas réel actif ; contrôlé s'il est
    fourni ailleurs. Le moteur vérifie la cohérence de la déclaration, pas la lecture."""
    v = item.get('passage')
    if v is None:
        return [f'{k} : champ passage requis pour F de cas actif ({{localisation, relation}} : le passage lu qui soutient le fait)'] if requis else []
    ps = v if isinstance(v, list) else [v]
    if not ps:
        return [f'{k} : passage = objet ou liste non vide']
    err = []
    for x in ps:
        if not isinstance(x, dict) or not (isinstance(x.get('localisation'), str) and x['localisation'].strip()):
            err.append(f'{k} : passage = {{localisation, relation}} (où, dans la source, le fait se lit)'); continue
        r = x.get('relation')
        if r not in RELATIONS_PASSAGE:
            err.append(f'{k} : passage.relation = {", ".join(RELATIONS_PASSAGE)}'); continue
        fo = x.get('forme')
        if fo is not None and fo not in FORMES_PIECE:
            err.append(f'{k} : passage.forme = {", ".join(FORMES_PIECE)} (ou champ absent)'); continue
        e = x.get('extrait')
        if e is not None and not (isinstance(e, str) and e.strip() and len(e) <= 300):
            err.append(f'{k} : passage.extrait = court extrait (300 caractères au plus) ; sinon la seule localisation')
        if r == 'contredit':
            err.append(f'{k} : un passage qui contredit le fait est une contre-observation (A7), pas un ancrage')
        # 0.7.11 (open-ontologies, décision 0007) : « ne permet pas de conclure » confondait deux diagnostics
        # aux remèdes opposés. absent_de_la_piece : la pièce lue ne contient pas le fait, une autre pièce le
        # contiendrait peut-être (fenêtre trop étroite) → élargir la lecture ; le fait n'est pas réfuté.
        # non_soutenu : la source ne soutient pas le fait (rien ne le contient) → retirer l'ancrage ;
        # le fait a pu être composé. Aucun des deux n'ancre ; « insuffisant » demande de choisir.
        elif r == 'absent_de_la_piece':
            err.append(f'{k} : passage absent de la pièce lue : la fenêtre était trop étroite ; élargir la lecture (autre pièce, autre section) avant d’ancrer — l’absence ici ne réfute pas le fait')
        elif r == 'non_soutenu':
            err.append(f'{k} : la source ne soutient pas le fait : retirer l’ancrage ou réécrire le fait ; signaler au journal des lacunes si le fait venait d’un résumé')
        elif r == 'insuffisant':
            err.append(f'{k} : un passage qui ne permet pas de conclure n’ancre rien : corriger le fait, chercher une autre pièce, ou ne pas ancrer ; « insuffisant » confond deux cas aux remèdes opposés (0.7.11) : absent_de_la_piece (élargir la lecture) ou non_soutenu (retirer l’ancrage)')
    if err:
        return err
    soutiens = sum(1 for x in ps if x['relation'] == 'soutient' and x.get('forme') in (None, 'prospective'))
    exclus = [x.get('forme') for x in ps if x['relation'] == 'soutient' and x.get('forme') not in (None, 'prospective')]
    if force == 'F' and not soutiens and exclus:
        motif = {'retrospective': 'la pièce contient le fait mais le raconte à travers son issue : chercher une source antérieure',
                 'attribuee': 'la pièce attribue le fait sans l’établir : remonter à la source primaire',
                 'inclassable': 'source non datable : le motif est la date, pas le fait'}
        err.append(f'{k} : F exige un passage qui soutient le fait dans une pièce prospective (0.7.16) ; '
                   + ' ; '.join(sorted({motif[f] for f in exclus})) + ' ; à défaut, f')
    elif force == 'F' and not soutiens:
        err.append(f'{k} : F exige un passage qui soutient le fait tel qu’il est écrit ; un soutien partiel donne f')
    if force == 'F' and item.get('corroboration') == 'independantes' and soutiens < 2:
        err.append(f'{k} : corroboration « independantes » : deux passages qui soutiennent, un par source')
    return err


def controle_a7(k, item, precedent=None):
    """A7 : la portée de la contre-observation fixe la force. Substantielle : F → f (f → rejet) ;
    dominante : rejet. La force notée est la force après A7 ; `force_initiale` dit d'où elle vient.
    `precedent` = (force à l'état précédent, force_initiale de son dernier enregistrement) si le mot
    était déjà présent, None s'il est nouveau : `force_initiale: "F"` sur un mot qui persiste n'est
    admissible que s'il était F, ou déjà rétrogradé depuis F, à l'état précédent."""
    po = item.get('portee'); fi = item.get('force_initiale'); err = []
    if po not in PORTEES:
        return [f'{k} : portee requise parmi {", ".join(PORTEES)} (A7)']
    if fi is not None and (fi != 'F' or po != 'substantielle'):
        err.append(f'{k} : force_initiale "F" seulement avec une portée substantielle (A7)')
    if po == 'dominante':
        err.append(f'{k} : contre-observation dominante → mot rejeté, ne pas le coder (A7)')
    if po == 'substantielle':
        if item.get('intensite') != 'f':
            err.append(f'{k} : contre-observation substantielle → noter f et force_initiale "F" (A7)')
        elif fi != 'F':
            err.append(f'{k} : substantielle sur un mot lu f → rejet ; si la lecture était F avant A7, déclarer force_initiale "F" (A7)')
        elif precedent is not None and precedent[0] != 'F' and precedent[1] != 'F':
            err.append(f'{k} : force_initiale "F" contredite par l’état précédent (f sans origine F) → rejet (A7)')
    return err


def incompatibles():
    """Paires incompatibles lues dans `antagonismes.md` §3 (relation symétrique)."""
    texte_ = (RACINE/'references'/'antagonismes.md').read_text(encoding='utf-8')
    sec = texte_.split('## 3.', 1)[1].split('\n## ', 1)[0]
    out = set()
    for a_, b_ in re.findall(r'^\| ([^|↮]+?) ↮ ([^|]+?) \|', sec, re.M):
        out.add(frozenset((carte_id(a_), carte_id(b_))))
    exiger(out, 'antagonismes.md §3 : aucune paire incompatible lue')
    return out


def norm_objet(x):
    return ' '.join(unicodedata.normalize('NFC', x).lower().split())


def erreurs_objets(objets, liaisons, incomp):
    """G6 : paire incompatible sur le même objet → rejet ; indépendance exige des objets distincts."""
    err = []; cles = sorted(objets)
    for i, a_ in enumerate(cles):
        for b_ in cles[i+1:]:
            if frozenset((a_.split('@')[0], b_.split('@')[0])) in incomp and norm_objet(objets[a_]) == norm_objet(objets[b_]):
                err.append(f'{a_} et {b_} : paire incompatible sur le même objet « {objets[a_]} » ; rejeter un des ancrages (G6)')
    for a_, t, b_ in liaisons:
        if t == 'indépendance' and a_ in objets and b_ in objets and norm_objet(objets[a_]) == norm_objet(objets[b_]):
            err.append(f'{a_} —indépendance→ {b_} : objets identiques ; indépendance exige des objets distincts (G6)')
    return err


def marqueur_local(ab, strate):
    f = os.path.join(RACINE, "references", "equivalences", f"strate-{int(strate):02d}.md")
    if not os.path.exists(f):
        return None
    for l in open(f, encoding="utf-8"):
        cells = [x.strip() for x in l.strip().strip("|").split("|")]
        if len(cells) == 5 and cells[0] not in ("Carte", "---"):
            try:
                if carte_id(cells[0]) == ab:
                    return cells[1], cells[2], cells[3]
            except ValueError:
                pass
    return None



def _betacf(a, b, x):
    qab, qap, qam = a + b, a + 1, a - 1
    c, d = 1.0, 1 - qab * x / qap
    d = 1 / (d if abs(d) > 1e-30 else 1e-30)
    h = d
    for m in range(1, 300):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1 + aa * d; d = 1 / (d if abs(d) > 1e-30 else 1e-30)
        c = 1 + aa / c; c = c if abs(c) > 1e-30 else 1e-30
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1 + aa * d; d = 1 / (d if abs(d) > 1e-30 else 1e-30)
        c = 1 + aa / c; c = c if abs(c) > 1e-30 else 1e-30
        dl = d * c
        h *= dl
        if abs(dl - 1) < 1e-12:
            break
    return h



def ibeta(a, b, x):
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    lb = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log(1 - x)
    if x < (a + 1) / (a + b + 2):
        return math.exp(lb) * _betacf(a, b, x) / a
    return 1 - math.exp(lb) * _betacf(b, a, 1 - x) / b



def beta_quantile(a, b, q):
    lo, hi = 0.0, 1.0
    for _ in range(80):
        mid = (lo + hi) / 2
        if ibeta(a, b, mid) < q:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2



def forces(etat):
    return {cle(m): m["i"] for m in etat["mots"]}



def issue_evenement(typ, cible, a, b):
    """(transition éligible, événement réalisé) pour une transition a → b."""
    fa, fb = forces(a), forces(b)
    if typ == "apparait":
        return cible not in fa, cible in fb
    if typ == "persiste":
        return cible in fa, cible in fb
    if typ == "disparait":
        return cible in fa, cible not in fb
    if typ == "renforce":
        return fa.get(cible) == "f", fb.get(cible) == "F"
    if typ == "affaiblit":
        return fa.get(cible) == "F", fb.get(cible) == "f"
    raise ValueError(typ)



ATTENUATION = None   # {CARTE@strate: w}, posé seulement le temps d'une sonde (sensibilite)
# 0.7.56 (§33, ombre) : règle des médiateurs, posée seulement le temps d'une sonde. Si A et M sont deux sources de la
# cible et que la matrice porte A → M (sans M → A), l'arête A → cible est lue comme un effet TOTAL qui inclut le
# chemin par M : M est écarté. Une paire mutuelle (A ↔ M) est ambiguë : rien n'est écarté.
MEDIATION = False
MEDIATION_RETIRES = []


def sources_de(etat, cible, liaisons, bouge, manque):
    c, s = cible.split("@")
    s = int(s)
    transferts = {(a.split("@")[1], b.split("@")[1]) for a, t, b in liaisons if t == "transfert"}
    src = []
    for m in etat["mots"]:
        I = P["matrice"].get(m["c"], {}).get(c)
        note = "même strate"
        if m["s"] != s:
            spec = P["autre_strate"].get(m["c"], {}).get(c)
            if spec:
                I, note = spec, "autre strate, propagation documentée"
            elif (str(m["s"]), str(s)) in transferts:
                note = "autre strate, transfert ancré"
            elif I:
                I, note = DEGRADE[I], "autre strate, abaissée d'un cran"
        if I:
            lam = P["lambda"][I] * (P["multiplicateur_bouge"] if cle(m) in bouge else 1)
            if ATTENUATION is not None:
                # 0.7.6 : sonde d'atténuation (décision 5, réservée) : λ_eff = 1 + (λ − 1)·w, hors du p publié.
                lam = 1 + (lam - 1) * ATTENUATION.get(cle(m), 1.0)
            src.append({"mot": cle(m), "intensite": I, "lambda": lam, "note": note})
    if MEDIATION:
        cartes_src = {x["mot"].split("@")[0] for x in src}
        def mediateur(x):
            mc = x["mot"].split("@")[0]
            return any(a != mc and P["matrice"].get(a, {}).get(mc) and not P["matrice"].get(mc, {}).get(a)
                       for a in cartes_src)
        retires = [x for x in src if mediateur(x)]
        MEDIATION_RETIRES.extend(x["mot"] for x in retires)
        src = [x for x in src if x not in retires]
    if cible in manque:
        src.append({"mot": "position manque", "intensite": "M", "lambda": P["lambda"]["M"], "note": "G4"})
    # redondance : sources liées par inclusion, renforcement ou transfert → on garde la plus forte
    groupes = {x["mot"]: x["mot"] for x in src}

    def racine(x):
        while groupes[x] != x:
            x = groupes[x]
        return x
    for a, t, b in liaisons:
        if t in ("inclusion", "renforcement", "transfert") and a in groupes and b in groupes:
            groupes[racine(a)] = racine(b)
    garde = {}
    for x in src:
        r = racine(x["mot"])
        if r not in garde or x["lambda"] > garde[r]["lambda"]:
            garde[r] = x
    ecartees = [x for x in src if x not in garde.values()]
    return list(garde.values()), ecartees



def jaccard(a, b):
    return len(a & b) / len(a | b) if a | b else 1.0



def appliquer(etat, typ, k):
    mots = [m for m in etat["mots"] if cle(m) != k]
    if typ == "apparait":
        c, s = k.split("@")
        mots.append({"c": c, "s": int(s), "i": "f", "q": []})
    return {"date": etat["date"], "fenetre": etat["fenetre"], "mots": mots}



def texte(etat):
    if not etat["mots"]:
        return "∅"
    return " + ".join(f"{NOMS[m['c']]}@{m['s']}[{m['i']}]" for m in sorted(etat["mots"], key=cle))


# ───────────────────────── données et calendrier ─────────────────────────

def exiger(condition, message):
    if not condition:
        raise ValueError(message)


def texte_requis(x, champ):
    exiger(isinstance(x, str) and bool(x.strip()) and x.strip() not in ('…', '...', 'À FOURNIR', 'à fournir'),
           f'{champ} : texte renseigné requis')
    return x


def proba(x, champ='probabilité'):
    exiger(type(x) in (int, float) and math.isfinite(x) and 0 <= x <= 1,
           f'{champ} : nombre fini entre 0 et 1 requis')
    return float(x)


def version_lue(s, champ='version_regles'):
    """0.6.13 (audit 0.6.12, m1) : « 0.6 » ou « 0.6.12 », sinon refus. Une valeur illisible (« abc »)
    rendait une liste vide, et les exigences versionnées étaient sautées sans message."""
    m = re.fullmatch(r'(\d+)\.(\d+)(?:\.(\d+))?', s if isinstance(s, str) else '')
    exiger(m is not None, f'{champ} illisible : {s!r} (forme 0.6 ou 0.6.12)')
    return tuple(int(v) if v is not None else 0 for v in m.groups())


def date_iso(s):
    exiger(isinstance(s, str) and re.fullmatch(r'\d{4}-\d{2}(?:-\d{2})?', s), f'date invalide : {s!r}')
    try:
        return datetime.date.fromisoformat(s + '-01' if len(s) == 7 else s)
    except ValueError:
        raise ValueError(f'date calendaire invalide : {s!r}') from None


def jour(s):
    return date_iso(s).toordinal()


def duree_jours(fenetre):
    exiger(isinstance(fenetre, str) and re.fullmatch(r'[1-9]\d* (jours?|semaines?|mois|ans?)', fenetre),
           f'fenêtre strictement positive requise : {fenetre!r}')
    n, u = fenetre.split()
    return int(n) * UNITES[u]


def fin_fenetre(date, fenetre, pas=1):
    d = date_iso(date); duree_jours(fenetre)
    exiger(type(pas) is int and 1 <= pas <= P['pas_max'], f'pas : entier de 1 à {P["pas_max"]}')
    n, u = fenetre.split(); n = int(n) * pas
    if u in ('mois', 'an', 'ans'):
        n *= 12 if u != 'mois' else 1
        total = d.year * 12 + d.month - 1 + n
        y, month = divmod(total, 12); month += 1
        return datetime.date(y, month, min(d.day, calendar.monthrange(y, month)[1]))
    return d + datetime.timedelta(days=n * (7 if u.startswith('semaine') else 1))


def meme_fenetre(a, b):
    return abs(duree_jours(a) - duree_jours(b)) < 0.01


def lire_etat(texte):
    exiger(isinstance(texte, str), 'état : texte requis')
    m = ETAT_RE.fullmatch(texte.strip())
    exiger(m is not None, f'état mal formé : {texte!r}')
    date_iso(m['d']); duree_jours(m['f'])
    mots = []
    if m['corps'] != '∅':
        for brut in m['corps'].split(' + '):
            mm = MOT_RE.fullmatch(brut.strip())
            exiger(mm is not None, f'mot mal formé : {brut!r}')
            mots.append({'c': carte_id(mm['c']), 's': int(mm['s']), 'i': mm['i'], 'q': re.findall(r'\{([^}]+)\}', mm['q'])})
    e = {'date': m['d'], 'fenetre': m['f'], 'mots': mots}
    errors = erreurs_g6(e)
    exiger(not errors, '; '.join(errors))
    return e


def cle_valide(s):
    k = lire_cle(s); st = int(k.split('@')[1])
    exiger(1 <= st <= NS, f'strate hors de 1–{NS} : {s}')
    return k


def lire_texte(chemin, quoi):
    """Lit un fichier texte UTF-8 avec un message en français pour chaque échec prévisible."""
    texte_=str(chemin)
    exiger(not texte_.lstrip().startswith(('{','[')), f'{quoi} : chemin de fichier attendu, pas du JSON en ligne (écrire le JSON dans un fichier)')
    try:
        return Path(chemin).read_text(encoding='utf-8')
    except FileNotFoundError:
        raise ValueError(f'{quoi} : fichier introuvable — {texte_}') from None
    except IsADirectoryError:
        raise ValueError(f'{quoi} : un dossier a été donné, un fichier est attendu — {texte_}') from None
    except UnicodeDecodeError:
        raise ValueError(f'{quoi} : fichier non textuel ou non UTF-8 — {texte_}') from None
    except PermissionError:
        raise ValueError(f'{quoi} : lecture refusée — {texte_}') from None


def lire_json(chemin, quoi):
    try:
        return json.loads(lire_texte(chemin, quoi), parse_constant=lambda v: (_ for _ in ()).throw(ValueError(v)))
    except json.JSONDecodeError as e:
        raise ValueError(f'{quoi} : JSON invalide ligne {e.lineno}, colonne {e.colno} — {chemin}') from None


def charger(chemin):
    if not chemin:
        return []
    out = []
    for n, line in enumerate(lire_texte(chemin, 'fichier JSONL').splitlines(), 1):
        if line.strip():
            try:
                x = json.loads(line, parse_constant=lambda v: (_ for _ in ()).throw(ValueError(v)))
                exiger(isinstance(x, dict), 'objet JSON requis')
                out.append(x)
            except (ValueError, TypeError) as e:
                raise ValueError(f'{chemin}:{n} : {e}') from None
    return out


def ids_codeurs(c):
    """Identifiants des codeurs, qu'ils soient écrits en chaîne (fiches fictives, archives) ou en
    {id, role} (cas réel actif, 0.6.14)."""
    return [x['id'] if isinstance(x,dict) else x for x in (c.get('codage') or {}).get('codeurs') or []]


def usage_attendu(cid):
    return 'test' if hashlib.sha256(cid.encode()).hexdigest()[0] in P['partage_test'] else 'apprentissage'


def lire_registre(chemin):
    """0.7.4 (décision 2). Registre du partage apprentissage/test : une ligne {id, usage, date} par
    identifiant, écrite par `partager` au moment où le partage est consulté, jamais réécrite. Il rend
    datée la décision « fixé avant codage » (B5) ; comme un scellé, il ne prouve l'antériorité que s'il
    est publié (dépôt daté)."""
    reg={}
    path=Path(chemin)
    if not path.is_file():return reg
    for n,l in enumerate(path.read_text(encoding='utf-8').splitlines(),1):
        if not l.strip():continue
        try:r=json.loads(l)
        except json.JSONDecodeError:raise ValueError(f'{chemin}:{n} : JSON invalide') from None
        exiger(isinstance(r,dict) and isinstance(r.get('id'),str) and r.get('usage') in ('apprentissage','test'),f'{chemin}:{n} : {{id, usage, date}} attendu')
        date_iso(r.get('date'))
        exiger(r['id'] not in reg,f'{chemin}:{n} : {r["id"]} déjà enregistré ; un partage ne se réécrit pas')
        exiger(r['usage']==usage_attendu(r['id']),f'{chemin}:{n} : usage différent du partage par empreinte')
        reg[r['id']]=r
    return reg


def empreinte(x):
    return hashlib.sha256(json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def valide_date(d):
    try:date_iso(d);return True
    except ValueError:return False


TYPES_EVENEMENT={'apparaît':'apparait','apparait':'apparait','persiste':'persiste','disparaît':'disparait','disparait':'disparait',
    'se renforce':'renforce','renforce':'renforce',"s'affaiblit":'affaiblit','affaiblit':'affaiblit',
    'se transforme':'transforme','transforme':'transforme',"s'intensifie":'intensifie','intensifie':'intensifie'}


def libelles_evenement(raw):
    """0.7.40 (test T6, défaut 1). Les libellés qui désignent le même événement : « SEUIL@7 apparait », « SEU@7 apparait »,
    « SEUIL@7 apparaît »… `sceller-jugement` hache le libellé tel qu'écrit, `squelette` recopie la forme canonique du
    calcul : le sceau était déclaré « différent » alors que rien n'avait changé. Le hachage ne change pas (les sceaux
    déjà publiés restent valides) ; la vérification accepte toute forme équivalente."""
    out={raw}
    try:cible,typ=evenement_lire(raw)
    except ValueError:return out
    ab,st_=cible.split('@')
    for carte in (ab,NOMS.get(ab,ab)):
        for mot,t_ in TYPES_EVENEMENT.items():
            if t_==typ:out.add(f'{carte}@{st_} {mot}');out.add(f'{carte}@{st_} {mot}'.replace("'",'’'))
    return out


def empreinte_jugement(question, evenement, probabilite, date):
    """0.6.0. Scellé du jugement humain, calculé AVANT d'exécuter le moteur (`sceller-jugement`) : il lie
    la probabilité du codeur à la question et à la date, pour mesurer ensuite ce que le moteur ajoute."""
    return empreinte({'question':question,'evenement':evenement,'probabilite_jugement':probabilite,'date':date})


VUS_ADMIS = ('question', 'resolution', 'echeance', 'date', 'domaine')
VUS_INTERDITS = ('etat_present', 'etat', 'cartes', 'evenement', 'marqueur', 'strate', 'p', 'probabilite', 'p_sans_cartes',
                 'p_placebo', 'jugement_scelle', 'dossier', 'calcul')
CONTEXTES_COMPARATEUR = ('separe', 'meme_session')


def empreinte_comparateur(question, evenement, probabilite, date, source, methode):
    """0.7.8. Scellé du comparateur externe : lie la question, l'événement, la probabilité, la date, la
    source **et la méthode** (changer de méthode après coup change l'empreinte)."""
    return empreinte({'question':question,'evenement':evenement,'probabilite_comparateur':probabilite,'date':date,
                      'source':source,'methode':methode})


def mots_de_cartes(texte_):
    """Noms et abréviations de cartes présents dans un texte, comme mots entiers (accents et casse ignorés)."""
    mots=set(re.findall(r'[A-Z0-9]+',_plat_mots(str(texte_))));out=[]
    for ab,nom in NOMS.items():
        if ab in mots or set(re.findall(r'[A-Z0-9]+',_plat_mots(nom)))<=mots:out.append(nom)
    return out


def erreurs_comparateur(c, question, evenement, date_prevision=None):
    """0.7.8. Comparateur externe aveugle : un second bras qui produit une probabilité sans avoir vu l'état,
    les cartes, ni p. Contrôles : forme ; scellé au plus tard à la date de la prévision et jamais futur ;
    publication https ; empreinte ; liste blanche de ce qui a été vu (l'événement codé « SEU@7 apparait » et
    le marqueur local sont du vocabulaire de l'alphabet : ils sont interdits, la question et la résolution
    en clair suffisent) ; méthode et question sans nom de carte (tautologie). `aveugle` et `contexte` sont
    déclarés : un bras non aveugle, ou produit dans la même session que la lecture, est accepté mais
    publié « contaminé » et exclu du rapport."""
    err=[]
    if not isinstance(c,dict):return ['comparateur_externe = {methode, probabilite, scelle_le, source, aveugle, elements_vus, contexte, empreinte}']
    for k in ('methode','scelle_le','source','empreinte'):
        if not (isinstance(c.get(k),str) and c[k].strip()):err.append(f'comparateur_externe.{k} requis')
    if err:return err
    try:proba(c.get('probabilite'),'comparateur_externe.probabilite')
    except ValueError as e:return [str(e)]
    try:date_iso(c['scelle_le'])
    except ValueError:return ['comparateur_externe.scelle_le au format AAAA-MM-JJ']
    if date_prevision is not None and jour(c['scelle_le'])>jour(date_prevision):err.append('comparateur scellé après la prévision')
    if jour(c['scelle_le'])>datetime.date.today().toordinal():err.append('comparateur scellé à une date future : on scelle un comparateur déjà formé')
    if type(c.get('aveugle')) is not bool:err.append('comparateur_externe.aveugle = true ou false')
    if c.get('contexte') not in CONTEXTES_COMPARATEUR:err.append('comparateur_externe.contexte = separe ou meme_session')
    vus=c.get('elements_vus')
    if not isinstance(vus,list) or not all(isinstance(v,str) for v in vus):err.append('comparateur_externe.elements_vus = liste')
    else:
        for v in vus:
            if v not in VUS_ADMIS:err.append(f'comparateur_externe.elements_vus : « {v} » '+('interdit' if v in VUS_INTERDITS else 'inconnu')+f' (admis : {", ".join(VUS_ADMIS)})')
    if not re.match(r'https://\S+$',c['source']):err.append('comparateur sans publication https : la date n’est pas prouvée')
    for champ,txt in (('methode',c['methode']),('question',question)):
        cs=mots_de_cartes(txt)
        if cs:err.append(f'{champ} du comparateur tautologique : cite {", ".join(cs)}')
    if not err and c['empreinte']!=empreinte_comparateur(question,evenement,c['probabilite'],c['scelle_le'],c['source'],c['methode']):
        err.append('comparateur_externe.empreinte absente ou différente (question, événement, probabilité, date, source et méthode)')
    return err


def comparateur_contamine(c):
    return isinstance(c,dict) and (c.get('aveugle') is not True or c.get('contexte')!='separe')


def empreinte_prevision(prediction):
    # A publication receipt can be added later without changing the frozen substantive forecast.
    return empreinte({k:v for k,v in prediction.items() if k != 'preuve_prepublication'})


def fichier_sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def transitions(cas):
    seq = cas['sequence'] + [cas['issue']]
    return [(cas['id'], lire_etat(a['etat']), lire_etat(b['etat'])) for a, b in zip(seq, seq[1:])]


def disponible(cas, a, b, asof):
    # A transition cannot be used before both the outcome and its evidence were available.
    states = cas['sequence'] + [cas['issue']]
    sa = next(x for x in states if x['date'] == a['date'])
    sb = next(x for x in states if x['date'] == b['date'])
    return max(jour(a['date']), jour(b['date']), jour(sa['disponible_le']), jour(sb['disponible_le'])) <= jour(asof)


def base_active(base, asof, demo=False):
    return [c for c in base if c.get('statut_donnees') == 'actif' and c.get('usage') == 'apprentissage'
            and (demo or not c.get('fictif')) and any(disponible(c, a, b, asof) for _, a, b in transitions(c))]


def mode_solo(base, strate=None):
    lot = [c for c in base if strate is None or strate in c.get('strates', [])]
    doubles = [c for c in lot if len(set(ids_codeurs(c))) >= 2 and c['codage'].get('independants') is True
               and c['codage'].get('au_moins_un_humain') is True]
    return not lot or len(doubles) < P['double_codage_min_cas'] or len(doubles)/len(lot) < P['double_codage_part']


def lire_liaisons(liste, etat=None):
    types = {'echo':'écho', 'écho':'écho', 'independance':'indépendance', 'indépendance':'indépendance',
             **{x:x for x in ['transfert','conflit','renforcement','inclusion','appui','reproduction','tension']}}
    out = []
    for raw in liste or []:
        exiger(isinstance(raw, str), 'liaison : texte requis')
        p = raw.split(); exiger(len(p) == 3, f'liaison mal formée : {raw}')
        a, t, b = p; t = t.strip('—-→>')
        exiger(t in types, f'liaison inconnue : {t}')
        a, b, t = cle_valide(a), cle_valide(b), types[t]
        exiger(a != b, 'liaison réflexive interdite')
        same = a.split('@')[1] == b.split('@')[1]
        exiger((same and t not in ('transfert','écho')) or (not same and t in ('transfert','écho','conflit')),
               f'liaison incompatible avec ses strates : {raw}')
        if etat is not None:
            exiger(a in forces(etat) and b in forces(etat), f'liaison vers un mot absent : {raw}')
        out.append((a,t,b))
    exiger(len(out) == len(set(out)), 'liaisons dupliquées')
    return out


def valider_base(base, registre=None):
    ids = set(); stat = statuts(); archive = 0; propositions = 0; incomp = incompatibles()
    for c in base:
        cid = texte_requis(c.get('id'), 'id')
        exiger(cid not in ids, f'identifiant en double : {cid}'); ids.add(cid)
        exiger(re.fullmatch(r'C-\d{4}-S(?:0[1-9]|[1-9]\d)', cid) is not None or c.get('id_legacy') is True,
               f'{cid} : identifiant C-NNNN-SNN requis ; ancien id seulement avec id_legacy=true')
        for field in ('version_regles','titre','fenetre'):
            texte_requis(c.get(field), f'{cid}.{field}')
        duree_jours(c['fenetre'])
        exiger(type(c.get('sans_evenement')) is bool and type(c.get('fictif')) is bool, f'{cid} : booléens requis')
        exiger(c.get('usage') == usage_attendu(cid), f'{cid} : partage apprentissage/test incorrect')
        if c.get('statut_donnees') != 'archive_a_revoir':
            # 0.7.4 (décision 2) : le partage est daté. La décision demandait usage_fige_le ≤ date du premier
            # état : impossible pour tout cas historique (un partage fixé en 2026, un état de 1995). Ce que B5
            # exige est « fixé avant codage » : usage_fige_le ≤ codage.debut, requis pour un cas réel.
            exiger('usage_fige_le' in c, f'{cid} : usage_fige_le requis (date à laquelle le partage a été fixé, `partager`) ; un partage non daté rend la fiche non valide')
            date_iso(c['usage_fige_le'])
            deb=c['codage'].get('debut') if isinstance(c.get('codage'),dict) else None
            if not c.get('fictif'):
                exiger(deb is not None, f'{cid} : codage.debut requis (date du début du codage) : le partage doit le précéder (B5)')
            if deb is not None:
                date_iso(deb)
                exiger(jour(c['usage_fige_le'])<=jour(deb), f'{cid} : partage fixé le {c["usage_fige_le"]}, après le début du codage ({deb}) : B5 exige un partage fixé avant codage')
            if registre is not None and not c.get('fictif'):
                r_=registre.get(cid)
                exiger(r_ is not None, f'{cid} : absent du registre du partage ; lancer `partager` avant de coder')
                exiger(r_['date']==c['usage_fige_le'], f'{cid} : usage_fige_le ({c["usage_fige_le"]}) différent du registre ({r_["date"]}) ; le registre fait foi')
        strata = c.get('strates')
        exiger(isinstance(strata,list) and bool(strata) and all(type(s) is int and 1<=s<=NS for s in strata)
               and len(set(strata)) == len(strata), f'{cid} : strates invalides')
        exiger(c.get('statut_donnees') in ('actif','proposition','archive_a_revoir'), f'{cid} : statut_donnees requis (actif, proposition ou archive_a_revoir)')
        exiger(isinstance(c.get('sequence'),list) and c['sequence'] and isinstance(c.get('issue'),dict), f'{cid} : séquence et issue requises')
        states = c['sequence']+[c['issue']]
        exiger(all(isinstance(x,dict) for x in states), f'{cid} : chaque état de la séquence et l’issue doivent être des objets JSON')
        if c['statut_donnees'] == 'archive_a_revoir':
            texte_requis(c.get('motif_archive'), f'{cid}.motif_archive')
            for x in states:
                lire_etat(x['etat']); date_iso(x['date'])
            archive += 1
            continue # Conserved evidence, never an eligible training or validation observation.
        # Même version mineure : un correctif (0.4.x) ne force pas à recoder, puisque le validateur applique
        # de toute façon les règles courantes à chaque fiche ; un changement mineur (0.5) l'exige.
        exiger(version_lue(c['version_regles'],cid+'.version_regles')[:2]==version_lue(P['version'],'version')[:2], f'{cid} : recodage requis pour cette version')
        coding = c.get('codage')
        exiger(isinstance(coding,dict) and coding.get('mode') in ('manuel','declenche'), f'{cid} : mode de codage requis')
        coders = coding.get('codeurs')
        exiger(isinstance(coders,list) and bool(coders), f'{cid} : codeurs distincts requis')
        for x in coders:
            exiger((isinstance(x,str) and x.strip()) or (isinstance(x,dict) and isinstance(x.get('id'),str) and x['id'].strip()
                   and x.get('role') in ('humain','modele')), f'{cid} : codeur = identifiant, ou {{id, role: humain|modele}}')
        for x in coders:
            # 0.7.6 : déclaration préalable de ce qui fait un signe suffisant (étape 5). Facultative,
            # auto-déclarée, datée avant le début du codage ; une déclaration rétrospective ne prouve rien.
            if isinstance(x,dict) and x.get('signe_suffisant') is not None:
                exiger(x['signe_suffisant'] in ('declaration','execution','trace'),f'{cid} : signe_suffisant = declaration, execution ou trace')
                date_iso(x.get('declare_le'))
                deb_=coding.get('debut')
                exiger(deb_ is None or jour(x['declare_le'])<=jour(deb_),f'{cid} : signe_suffisant déclaré après le début du codage : une déclaration rétrospective ne prouve rien')
        ids_=ids_codeurs(c)
        exiger(len(set(ids_))==len(ids_), f'{cid} : codeurs distincts requis')
        for flag in ('independants','au_moins_un_humain'):
            exiger(coding.get(flag) is None or type(coding[flag]) is bool, f'{cid} : codage.{flag} doit être true ou false')
        if len(coders) >= 2:
            exiger(coding.get('independants') is True and coding.get('au_moins_un_humain') is True,
                   f'{cid} : double codage indépendant avec au moins un humain requis')
        if coding['mode']=='declenche':
            texte_requis(coding.get('regle_declenchement'), f'{cid}.regle_declenchement')
        if not c['fictif']:
            if c['statut_donnees']=='proposition':
                # Recodage complet, contrôlé comme un cas actif, en attente de la vérification humaine des
                # sources ; exclu des calculs (base_active ne retient que « actif »).
                texte_requis(c.get('motif_proposition'), f'{cid}.motif_proposition')
                exiger(c.get('sources_verifiees') is False, f'{cid} : une proposition porte sources_verifiees=false ; une fois les sources lues, passer en actif')
                propositions += 1
            else:
                exiger(c.get('sources_verifiees') is True, f'{cid} : sources non vérifiées ; passer en proposition ou archiver en attendant')
                # 0.6.7 : une sortie de modèle ne devient pas un fait sans relecture (« unchecked output »).
                # Un cas dont le codage a été proposé par un modèle (codage.recodage renseigné) n'entre dans
                # les calculs qu'avec la confirmation datée d'un codeur humain nommé.
                # 0.6.14 (audit Manus, haute 2) : l'identité des codeurs est structurée. Une liste de noms
                # libres et une liste noire (« claude ») laissaient passer GPT-4o seul, ou une confirmation
                # par un autre modèle. Un cas réel actif nomme au moins un codeur {role: humain} ; une
                # confirmation de recodage renvoie à l'identifiant de ce codeur humain.
                exiger(all(isinstance(x,dict) for x in coders),
                       f'{cid} : cas réel actif : chaque codeur est {{id, role: humain|modele}}')
                humains={x['id'] for x in coders if x['role']=='humain'}
                exiger(bool(humains), f'{cid} : cas réel actif : au moins un codeur de rôle « humain »')
                if coding.get('recodage'):
                    rc=coding.get('recodage_confirme')
                    exiger(isinstance(rc,dict) and rc.get('par') in humains and isinstance(rc.get('date'),str),
                           f'{cid} : codage proposé par un modèle ({coding["recodage"][:40]}…) : codage.recodage_confirme '
                           '{par: identifiant d’un codeur humain de la fiche, date} requis avant activation')
                    date_iso(rc['date'])
        observed = set(); prev=None; objets = {}; origine_f = {}
        for ix,x in enumerate(states):
            e = lire_etat(x.get('etat')); date_iso(x.get('date'))
            exiger(e['date']==x['date'], f'{cid} : date de fiche différente de celle de l’état')
            exiger(meme_fenetre(e['fenetre'],c['fenetre']), f'{cid} : fenêtres différentes')
            date_iso(x.get('disponible_le'))
            exiger(jour(x['disponible_le'])>=jour(x['date']), f'{cid} : disponibilité antérieure à l’observation')
            if prev:
                exiger(date_iso(e['date']) == fin_fenetre(prev['date'],c['fenetre']), f'{cid} : écart des dates différent de la fenêtre')
            fm=forces(e); observed.update(m['s'] for m in e['mots'])
            expected=set(fm) if prev is None else (set(fm)-set(forces(prev))) | forces_changees(prev,e)
            docs=x.get('mots','ABSENT')
            if not expected:
                exiger(docs is None or (isinstance(docs,list) and bool(docs)), f'{cid} : mots=null si aucun changement, [] interdit')
            else:
                exiger(isinstance(docs,list) and bool(docs), f'{cid} : documentation des mots requise')
            documented=set()
            for item in docs or []:
                exiger(isinstance(item,dict), f'{cid} : mot documenté invalide')
                k=cle_valide(f"{item.get('carte')}@{item.get('strate')}")
                exiger(k not in documented and k in fm, f'{cid} : mot documenté absent ou dupliqué : {k}'); documented.add(k)
                exiger(stat.get((k.split('@')[0],int(k.split('@')[1])))!='Hors domaine', f'{cid} : {k} est Hors domaine : aucun ancrage possible dans cette strate (A3)')
                exiger(item.get('intensite')==fm[k], f'{cid} : force contradictoire pour {k}')
                for field in ('fait','source','contre_observation','objet'):
                    texte_requis(item.get(field), f'{cid}.{k}.{field}')
                pr=None if prev is None or k not in forces(prev) else (forces(prev)[k], origine_f.get(k))
                errs=controle_a7(k,item,pr)+controle_source(k,item)+controle_classe_source(k,item,not c['fictif'] and c.get('statut_donnees')=='actif')+controle_grille(k,item)
                exiger(not errs, f'{cid} : '+' ; '.join(errs))
                if fm[k]=='F':
                    # A6 : F qualifie la lecture (fait précis, voisines tranchées), pas la bibliographie (A3).
                    texte_requis(item.get('a6'), f'{cid}.{k}.a6')
                    # 0.6.6 : ce refus était placé dans la branche f (indentation) ; une fiche pouvait ancrer F
                    # sur une case Vide et passer valider, le calcul seul la refusant.
                    ab,s=k.split('@')
                    exiger(stat.get((ab,int(s)))!='Vide', f'{cid} : F impossible sur un équivalent Vide {k} (A3)')
                    if not c['fictif']:
                        errs=controle_a6(k,item['a6'])+controle_garantie(k,item,True)+controle_test(k,item,'F',True)
                        errs+=controle_support(k,item,version_lue(c['version_regles'],cid+'.version_regles')>=(0,7,10),x['disponible_le'])
                        if c.get('statut_donnees')=='actif':errs+=controle_corroboration(k,item,version_lue(c['version_regles'],cid+'.version_regles')>=(0,7,11))
                        errs+=controle_passage(k,item,'F',c.get('statut_donnees')=='actif')
                        exiger(not errs, f'{cid} : '+' ; '.join(errs))
                    else:
                        errs=(controle_corroboration(k,item) if 'corroboration' in item else [])+controle_test(k,item,'F',False)+controle_passage(k,item,'F',False)
                        exiger(not errs, f'{cid} : '+' ; '.join(errs))
                elif 'garantie' in item or 'option' in item or 'corroboration' in item or 'test' in item or 'passage' in item:
                    errs=controle_garantie(k,item,False)+controle_support(k,item,False,x['disponible_le'])+(controle_corroboration(k,item) if 'corroboration' in item else [])+controle_test(k,item,'f',False)+controle_passage(k,item,'f',False)
                    exiger(not errs, f'{cid} : '+' ; '.join(errs))
            exiger(expected <= documented, f'{cid} : mots nouveaux ou modifiés non documentés {sorted(expected-documented)}')
            removed=set(forces(prev))-set(fm) if prev else set()
            retrait=x.get('retraits',[])
            exiger(isinstance(retrait,list), f'{cid} : retraits doit être une liste')
            rd=set()
            for item in retrait:
                exiger(isinstance(item,dict) and isinstance(item.get('mot'),str), f'{cid} : retrait = objet avec "mot" (texte), "fait", "source"')
                k=cle_valide(item['mot']); exiger(k not in rd, f'{cid} : retrait dupliqué');rd.add(k)
                texte_requis(item.get('fait'),'fait de retrait');texte_requis(item.get('source'),'source de retrait')
            exiger(rd==removed, f'{cid} : retraits incohérents')
            # Objets courants : documentés à l'apparition, conservés tant que le mot persiste.
            objets={k:v for k,v in objets.items() if k in fm}
            origine_f={k:v for k,v in origine_f.items() if k in fm}
            for item in docs or []:
                origine_f[cle_valide(f"{item.get('carte')}@{item.get('strate')}")]=item.get('force_initiale')
            for item in docs or []:
                objets[cle_valide(f"{item.get('carte')}@{item.get('strate')}")]=item['objet']
            exiger(isinstance(x.get('liaisons',[]),list), f'{cid} : liaisons doit être une liste (vide si aucune)')
            links=lire_liaisons(x.get('liaisons',[]),e)
            errs=erreurs_objets(objets,links,incomp); exiger(not errs, f'{cid} : '+' ; '.join(errs))
            if links:
                facts=x.get('preuves_liaisons')
                exiger(isinstance(facts,list) and len(facts)==len(links), f'{cid} : preuves de liaisons requises')
                for fact in facts: texte_requis(fact,'preuve de liaison')
            qkeys={cle(m) for m in e['mots'] if m['q']}
            for k in qkeys:
                texte_requis(x.get('preuves_qualificatifs',{}).get(k), f'{cid}.{k} : ligne Q')
            pos=x.get('positions')
            if pos is not None:
                exiger(isinstance(pos,dict) and len(fm)>=3, f'{cid} : positions avec au moins trois mots')
                for label,k in pos.items():
                    exiger(label in ('tient','bouge','manque'), f'{cid} : position inconnue')
                    kk=cle_valide(k)
                    exiger((kk not in fm) if label=='manque' else (kk in fm), f'{cid} : position incompatible')
                    if label=='tient': exiger(fm[kk]=='F', f'{cid} : tient exige F')
                texte_requis(x.get('preuve_positions'), f'{cid} : preuve des positions')
            if ix==0 and not c['fictif'] and e['mots']:
                errs=controle_questions(x.get('questions'),fm,True,True); exiger(not errs, f'{cid} : '+' ; '.join(errs))
            elif x.get('questions') is not None:
                errs=controle_questions(x['questions'],fm,False,not c['fictif']); exiger(not errs, f'{cid} : '+' ; '.join(errs))
            prev=e
        exiger(observed<=set(strata), f'{cid} : strate d’état absente de la fiche')
        if c['sans_evenement']:
            # B4 : « rien ne s'est produit » — aucune apparition, disparition ni changement de force.
            etats_=[lire_etat(x['etat']) for x in states]
            exiger(all(forces(a)==forces(b) for a,b in zip(etats_,etats_[1:])), f'{cid} : sans_evenement=true alors que la structure change (B4)')
    return {'cas':len(base),'actifs':len(base)-archive-propositions,'propositions':propositions,'archives_exclues':archive}


FAMILLES_RECHERCHE=('observation','discrimination','contradiction')


def extrait(t, n=50):
    """0.7.45 : coupe au mot, avec une ellipse (le drapeau coupait au milieu d'une parenthèse)."""
    t=' '.join(str(t).split())
    if len(t)<=n:return t
    c=t[:n].rsplit(' ',1)[0] or t[:n]
    if c.count('(')>c.count(')'):c=c[:c.rfind('(')]   # ne jamais laisser une parenthèse ouverte
    return c.rstrip(' ,;:(')+'…'


def controle_recherches(rs, mots_etat, candidats):
    """0.7.4 (décision 4). Plancher de couverture A7 : chaque carte de l'état est cherchée dans les
    trois familles (observation, discrimination, contradiction), et chaque paire de candidates d'une même
    strate a sa requête de discrimination. Le plancher porte sur les **familles couvertes**, pas sur un
    nombre de requêtes : dix requêtes d'observation ne remplacent pas une requête de contradiction.
    Une requête qui contient le nom de sa carte est signalée (A7 : chercher le phénomène, pas le mot ;
    coïncidence lexicale, A5). Rend (erreurs de forme, manques) : une forme fausse refuse le dossier, un
    manque le rend incomplet (statut de lecture Spéculatif, « À vérifier »)."""
    err=[];manques=[]
    if rs is None:
        return [],['aucune requête consignée (dossier.recherches) : couverture A7 non constatable']
    if not isinstance(rs,list):
        return ['dossier.recherches = liste de {famille, cartes, requete}'],[]
    couvert=defaultdict(set);paires=set();vues=set()
    for i,r in enumerate(rs):
        if not isinstance(r,dict) or r.get('famille') not in FAMILLES_RECHERCHE:
            err.append(f'dossier.recherches[{i}] : famille = {", ".join(FAMILLES_RECHERCHE)}');continue
        q=r.get('requete')
        if not (isinstance(q,str) and q.strip()):
            err.append(f'dossier.recherches[{i}] : requete = le texte exact de la requête');continue
        try:ks=[cle_valide(str(x)) for x in (r.get('cartes') or [])]
        except (ValueError,IndexError):err.append(f'dossier.recherches[{i}] : cartes = liste de CARTE@strate');continue
        if not 1<=len(ks)<=2 or not set(ks)<=set(candidats):
            err.append(f'dossier.recherches[{i}] : une ou deux cartes, prises parmi les candidates');continue
        # 0.7.45 (test FR-RU) : des requêtes marquées « non exécutée » dans leur texte passaient pour faites. Chaque requête
        # dit si elle a été lancée, et quand ; une requête non lancée est consignée, mais ne couvre rien (dossier Spéculatif).
        ex_=r.get('executee')
        if type(ex_) is not bool:
            err.append(f'dossier.recherches[{i}] : executee = true ou false (la requête a-t-elle été lancée ?)');continue
        if not ex_:
            manques.append(f'requête déclarée, non exécutée : « {extrait(q)} »');continue
        try:date_iso(r.get('date_execution'))
        except (ValueError,TypeError):err.append(f'dossier.recherches[{i}] : date_execution AAAA-MM-JJ requise pour une requête exécutée');continue
        cle_q=(r['famille'],' '.join(q.lower().split()))
        if cle_q in vues:manques.append(f'requête répétée, comptée une fois : « {extrait(q)} »')
        vues.add(cle_q)
        mots_q=set(re.findall(r'[A-Z0-9]+',_plat_mots(q)))
        for k in ks:
            ab=k.split('@')[0];noms=set(re.findall(r'[A-Z0-9]+',_plat_mots(NOMS[ab])))
            if noms & mots_q or re.search(r'\b'+ab+r'\b',q):
                manques.append(f'requête formée sur le nom de la carte {NOMS[ab]} (A7) : « {extrait(q)} »')
            couvert[k].add(r['famille'])
        if r['famille']=='discrimination' and len(set(ks))==2:paires.add(frozenset(ks))
    if err:return err,[]
    for k in sorted(mots_etat):
        for fam in FAMILLES_RECHERCHE:
            if fam not in couvert[k]:manques.append(f'{k} : aucune requête de {fam}')
    par_strate=defaultdict(list)
    for k in candidats:par_strate[int(k.split('@')[1])].append(k)
    for st_,ks in sorted(par_strate.items()):
        for i,a in enumerate(ks):
            for b in ks[i+1:]:
                if frozenset((a,b)) not in paires:manques.append(f'paire {a} / {b} : aucune requête de discrimination')
    return [],manques


def _plat_mots(s):
    """Majuscules sans accents, mots séparés (« TRACE·MÉMOIRE » → « TRACE MEMOIRE »)."""
    s=unicodedata.normalize('NFD',s)
    return ''.join(ch for ch in s if unicodedata.category(ch)!='Mn').upper().replace('·',' ')


def controle_concessions(cs,fm,candidats,n_mots):
    """0.7.9. Journal des concessions : une rétrogradation ou un retrait consécutif à une contestation se
    note de 1 à 5 (5 : pièce nouvelle ou raisonnement qui défait l'ancrage ; 4 : affaiblit
    substantiellement ; 3 et moins : la lecture tient). Rétrogradation : score ≥ 4 ; retrait : 5 ; après
    une concession, la suivante exige 5. La concession doit se lire dans le dossier (rétrogradée → f,
    retirée → absente). Au-delà de la moitié des mots, signalement : relire si c'est le dossier qui a changé
    ou le codeur qui a cédé. Le score est une déclaration ; la règle lie la cohérence, pas la vérité. Ne
    s'y inscrivent ni une portée dominante (A7), ni une correction matérielle, ni un rejet motivé par A6."""
    if cs is None:return [],[]
    if not isinstance(cs,list):return ['dossier.concessions = liste'],[]
    err=[];prec=False;n=0
    for i,c in enumerate(cs):
        if not isinstance(c,dict):err.append(f'concessions[{i}] : objet requis');continue
        try:k=cle_valide(str(c.get('carte')))
        except (ValueError,IndexError):err.append(f'concessions[{i}] : carte = CARTE@strate');continue
        sc=c.get('score');ac=c.get('action')
        if type(sc) is not int or not 1<=sc<=5:err.append(f'{k} : score de 1 à 5');continue
        if ac not in ('maintien','retrogradation','retrait'):err.append(f'{k} : action = maintien, retrogradation ou retrait');continue
        for ch in ('contestation','motif'):
            if not (isinstance(c.get(ch),str) and c[ch].strip()):err.append(f'{k} : {ch} requis')
        try:date_iso(c.get('date'))
        except ValueError:err.append(f'{k} : date au format AAAA-MM-JJ')
        if k not in candidats:err.append(f'{k} : concession sur une carte qui n’est pas candidate')
        if ac!='maintien':
            mini=5 if prec or ac=='retrait' else 4
            if sc<mini:err.append(f'{k} : {ac} avec un score {sc} < {mini}'+(' (concession précédente : la suivante exige 5)' if prec else '')+' ; l’insistance n’est pas une preuve')
            if ac=='retrogradation' and fm.get(k)!='f':err.append(f'{k} : rétrogradation déclarée, mais le mot n’est pas f dans l’état')
            if ac=='retrait' and k in fm:err.append(f'{k} : retrait déclaré, mais le mot est encore dans l’état')
            n+=1
        if type(c.get('concession_precedente')) is bool and c['concession_precedente']!=prec:err.append(f'{k} : concession_precedente incohérente avec le journal')
        prec=ac!='maintien'
    sig=[f'concessions : {n} pour {n_mots} mot(s), plus de la moitié ; relecture humaine : le dossier a-t-il changé, ou le codeur a-t-il cédé ?'] if n_mots and n>n_mots/2 else []
    return err,sig


def signalements_circularite(mots):
    """0.7.6. Une garantie circulaire reformule la carte au lieu de nommer un mécanisme (« c'est un seuil
    parce qu'il y a hystérésis »). Signalée — jamais refusée : nommer la carte n'est pas forcément
    circulaire, et le taux de faux signalements n'est pas connu (à éprouver sur cas réels)."""
    out=[]
    for item in mots or []:
        if not isinstance(item,dict) or not isinstance(item.get('garantie'),dict):continue
        mec=str(item['garantie'].get('mecanisme',''));ab=str(item.get('carte',''))
        if ab not in NOMS:continue
        noms=set(re.findall(r'[A-Z0-9]+',_plat_mots(NOMS[ab])));mots_m=set(re.findall(r'[A-Z0-9]+',_plat_mots(mec)))
        if noms & mots_m:
            out.append(f"{NOMS[ab]}@{item.get('strate')} : la garantie nomme la carte qu’elle fonde (« {mec[:50]} ») ; nommer le mécanisme dans la langue de la strate")
        # 0.7.10 : un « contredirait » qui nomme la carte (« si ce n'était pas une polarité ») est une
        # définition, pas une réfutation : il ne dit pas ce qu'on observerait. Signalé, jamais refusé.
        ctr=str(item['garantie'].get('contredirait',''))
        if noms & set(re.findall(r'[A-Z0-9]+',_plat_mots(ctr))):
            out.append(f"{NOMS[ab]}@{item.get('strate')} : garantie.contredirait nomme la carte (« {ctr[:50]} ») ; dire ce qu’on observerait, pas « si la carte était fausse »")
    return out


DOSSIER_ID='C-0001-S07'
TEMPORALITES=('generique','programmee','duree_de_vie')


SOURCES_VAGUES=('presse','la presse','médias','medias','les médias','sources ouvertes','internet','actualité','actualités','divers','web','réseaux sociaux')


def dossier_valider(d):
    """0.7.3. Dossier de lecture d'un calcul (mode PRÉVOIR) : les règles A1, A3, A5, A6, A7, la garantie,
    l'option, le test de preuve, la corroboration, le passage et les questions, contrôlés **avant** que le
    chiffre n'existe. En 0.7.2, toute cette théorie de la preuve n'était vérifiée que pour une fiche
    (CODER) : en PRÉVOIR, elle restait une obligation narrative, sans contrôle et sans trace. Le dossier
    passe par `valider_base` — une fiche d'un état, sans issue observée — donc par exactement les mêmes
    contrôles, et il porte un sceau qui fige la lecture et les événements avant le calcul."""
    exiger(isinstance(d,dict),'dossier : objet JSON requis')
    etat=texte_requis(d.get('etat'),'dossier.etat');e=lire_etat(etat)
    mots=d.get('mots')
    exiger(isinstance(mots,list) and bool(mots),'dossier.mots : documentation de chaque mot de l’état requise')
    fm=forces(e)
    # 0.7.3 (relecture de l'audit) : SKILL étape 2 teste 2 à 4 candidates **par strate**, dont une
    # contre-candidate. Le correctif reçu exigeait que toute candidate soit ancrée dans l'état : une
    # rivale écartée ne pouvait donc pas être déclarée, et la « contre-candidate » était forcément une
    # carte retenue. Une candidate absente de l'état porte désormais le motif de son rejet (`rejets`).
    cand=d.get('candidats')
    exiger(isinstance(cand,list) and cand,'dossier.candidats : liste des cartes testées (2 à 4 par strate)')
    keys=[cle_valide(str(x)) for x in cand]
    exiger(len(set(keys))==len(keys),'dossier.candidats : doublon')
    strates_etat=sorted({m['s'] for m in e['mots']})
    for st_ in strates_etat:
        n_=sum(1 for k in keys if int(k.split('@')[1])==st_)
        exiger(2<=n_<=4,f'dossier.candidats : 2 à 4 candidates dans la strate {st_} ({n_} déclarée(s))')
    exiger(set(fm)<=set(keys),f'dossier.candidats : un mot de l’état n’a pas été testé comme candidate ({sorted(set(fm)-set(keys))})')
    rej=d.get('rejets') or {}
    exiger(isinstance(rej,dict),'dossier.rejets : objet {CARTE@strate: motif}')
    rejk={cle_valide(str(k)):v for k,v in rej.items()}
    for k in keys:
        if k not in fm:
            texte_requis(rejk.get(k),f'dossier.rejets.{k} (motif du rejet d’une candidate non retenue : A6, A7 ou absence de fait)')
    exiger(set(rejk)<=set(keys)-set(fm),'dossier.rejets : seulement pour des candidates absentes de l’état')
    cc=d.get('contre_candidate')
    cc=cc if isinstance(cc,list) else [cc]
    contre=[cle_valide(str(x)) for x in cc]
    exiger(contre and set(contre)<=set(keys),'dossier.contre_candidate : la carte rivale la plus plausible, prise parmi les candidates (une ou une liste)')
    for st_ in strates_etat:
        exiger(any(int(k.split('@')[1])==st_ for k in contre),f'dossier.contre_candidate : une contre-candidate pour la strate {st_}')
    evs=d.get('evenements')
    if evs is not None:
        exiger(isinstance(evs,list) and evs,'dossier.evenements : liste non vide, ou champ absent')
        for x in evs:
            exiger(isinstance(x,dict),'dossier.evenements : objets requis')
            _,typ_d=evenement_lire(str(x.get('evenement','')))
            # 0.7.42 (test T7) : le dossier acceptait « presence » pour une intensification, que le journal refuse
            # (« compose ») ; le contrôle du dossier dit désormais la même chose que le journal.
            if typ_d in ('intensifie','transforme'):
                exiger(x.get('semantique')=='compose',f'dossier.evenements.semantique : « compose » pour un événement composé ({typ_d}), comme au journal')
            else:
                exiger(x.get('semantique') in ('presence','au-moins-une-fois','continue'),
                       'dossier.evenements.semantique : presence, au-moins-une-fois ou continue (« compose » pour s’intensifie et se transforme)')
            exiger(x.get('temporalite') in TEMPORALITES,
                   'dossier.evenements.temporalite : '+', '.join(TEMPORALITES)+' (mêmes valeurs que calculer --temporalite)')
            # 0.7.16 (Copley 2009, ch. 2 : un futur « programmé » présuppose un directeur capable de fixer
            # l'événement et affirme son engagement). Sans eux, l'événement n'est pas programmé.
            if x['temporalite']=='programmee':
                pg=x.get('programmation')
                exiger(isinstance(pg,dict) and all(isinstance(pg.get(c),str) and pg[c].strip() for c in ('qui','engagement')),
                       'dossier.evenements.programmation {qui, engagement} requis pour « programmee » : qui a la capacité de fixer '
                       'l’événement, et à quoi voit-on qu’il s’y est engagé (texte, calendrier publié) ; sans réponse, l’événement n’est pas programmé')
            texte_requis(x.get('resolution'),'dossier.evenements.resolution')
            # 0.7.39 (décision d'auteur, série 2 de tests régressifs, défaut 8) : un critère en langage naturel ne tranchait
            # pas T2 (une doctrine inchangée, minée en paroles). La source qui tranchera est nommée avant le calcul : qui
            # l'émet, quel document, et quelle règle s'applique si elle est ambiguë (ce qui compte, ce qui ne compte pas).
            sr=x.get('source_resolution')
            exiger(isinstance(sr,dict) and all(isinstance(sr.get(c),str) and sr[c].strip() for c in ('emetteur','document','regle_ambiguite')),
                   'dossier.evenements.source_resolution {emetteur, document, regle_ambiguite} requise : la source qui tranchera, '
                   'nommée avant le calcul, et ce qui compte si elle est ambiguë (ex. « un texte officiel ; une déclaration orale ne compte pas »)')
            exiger(' '.join(sr['emetteur'].lower().split()) not in SOURCES_VAGUES,
                   f'dossier.evenements.source_resolution.emetteur « {sr["emetteur"]} » : trop vague ; nommer l’émetteur (un ministère, une agence, une base)')
            # 0.7.35 (vue extérieure d'abord, Tetlock et Gardner 2015) : le taux de base de la classe de référence,
            # écrit par l'analyste avant tout calcul, avec sa classe et sa source. Requis.
            ve=x.get('vue_exterieure')
            exiger(isinstance(ve,dict) and type(ve.get('frequence')) in (int,float) and 0<ve['frequence']<1
                   and all(isinstance(ve.get(c),str) and ve[c].strip() for c in ('classe_de_reference','source')),
                   'dossier.evenements.vue_exterieure {frequence dans ]0 ; 1[, classe_de_reference, source} requise : le taux de base, '
                   'écrit avant le calcul (« vue extérieure d’abord »)')
            # 0.7.43 (décision d'auteur, option a) : une seconde classe plausible, scellée avec la première. La référence de V4
            # reste la classe retenue ; l'alternative est scorée à côté, pour que le choix de la classe se voie (T7 : 0,87
            # contre 0,50). Champ obligatoire : un objet, ou null avec un motif (aucune alternative honnête).
            exiger('classe_alternative' in ve,'dossier.evenements.vue_exterieure.classe_alternative requise (0.7.43) : '
                   '{frequence, classe_de_reference, source, pourquoi_ecartee}, ou null avec motif_sans_alternative')
            alt=ve['classe_alternative']
            if alt is None:
                texte_requis(ve.get('motif_sans_alternative'),'dossier.evenements.vue_exterieure.motif_sans_alternative (pourquoi aucune seconde classe plausible)')
            else:
                exiger(isinstance(alt,dict) and type(alt.get('frequence')) in (int,float) and 0<alt['frequence']<1
                       and all(isinstance(alt.get(c),str) and alt[c].strip() for c in ('classe_de_reference','source','pourquoi_ecartee')),
                       'dossier.evenements.vue_exterieure.classe_alternative {frequence dans ]0 ; 1[, classe_de_reference, source, pourquoi_ecartee}')
                exiger(' '.join(alt['classe_de_reference'].split())!=' '.join(ve['classe_de_reference'].split()),
                       'dossier.evenements.vue_exterieure.classe_alternative : une autre classe que la classe retenue')
            # 0.7.44 (test P-0001) : la question incluait l'artillerie lourde et les raids, la classe ne comptait que trois
            # grands épisodes ; appliqué au passé, le critère de résolution aurait dit « oui » bien plus souvent. Le taux de
            # base décrivait un autre événement. Obligatoire : en quoi ce que compte la classe diffère du critère de
            # résolution (« identique » s'il n'en diffère pas, avec la raison), sur le modèle d'ecart_marqueur.
            texte_requis(ve.get('ecart_critere'),'dossier.evenements.vue_exterieure.ecart_critere (0.7.44) : en quoi ce que compte la classe '
                         'diffère du critère de résolution de la question ; « identique : … » s’il n’en diffère pas')
            # 0.7.5 : la fenêtre est le levier le plus fort du calcul (inertie^(durée/91,3 j)) ; rien ne la
            # reliait à la durée du phénomène. Facultatif : une durée en jours, vérifiable contre une source.
            dc=x.get('duree_caracteristique_jours')
            if dc is not None:
                exiger(type(dc) in (int,float) and math.isfinite(dc) and dc>0,'dossier.evenements.duree_caracteristique_jours : nombre de jours > 0')
                texte_requis(x.get('source_duree'),'dossier.evenements.source_duree (d’où vient cette durée)')
                if x['temporalite']=='generique' and dc<P['ratio_duree_fenetre']*duree_jours(e['fenetre']):
                    texte_requis(x.get('justification_temporalite'),
                        f'dossier.evenements : durée caractéristique {dc:g} j, moins de {P["ratio_duree_fenetre"]:g} × la fenêtre '
                        f'({duree_jours(e["fenetre"]):g} j) avec temporalite « generique » : déclarer duree_de_vie, ou justifier '
                        '(justification_temporalite) ; l’inertie générique suppose un phénomène qui dure au moins la fenêtre')
    d1=fin_fenetre(e['date'],e['fenetre']).isoformat()
    etat_issue=etat.replace(f"[{e['date']} |",f"[{d1} |",1)
    fiche={'id':DOSSIER_ID,'version_regles':P['version'],'titre':'Dossier de lecture (PRÉVOIR)',
           'strates':sorted({m['s'] for m in e['mots']}),'fenetre':e['fenetre'],
           'sans_evenement':True,'fictif':False,'statut_donnees':'proposition',
           'motif_proposition':'dossier de lecture d’un calcul, sans issue observée',
           'sources_verifiees':False,'usage':usage_attendu(DOSSIER_ID),
           'usage_fige_le':d.get('disponible_le') or e['date'],   # sans objet pour un dossier : fiche technique
           'codage':{'mode':'manuel','codeurs':[{'id':'codeur-dossier','role':'humain'}],'debut':d.get('disponible_le') or e['date']},
           'sequence':[{'date':e['date'],'disponible_le':d.get('disponible_le') or e['date'],'etat':etat,'mots':mots,
                        'retraits':[],'liaisons':d.get('liaisons',[]),'positions':d.get('positions'),
                        'questions':d.get('questions'),'preuves_positions':d.get('preuves_positions'),
                        'preuves_liaisons':d.get('preuves_liaisons'),
                        'preuves_qualificatifs':d.get('preuves_qualificatifs')}],
           'issue':{'date':d1,'disponible_le':d1,'etat':etat_issue,'mots':None}}
    try:
        valider_base([fiche])
    except ValueError as err:
        # 0.7.45 : l'identifiant technique de la fiche interne (C-0001-S07) ne parle pas au codeur d'un dossier.
        raise ValueError(f'dossier refusé — '+str(err).replace(DOSSIER_ID+' : ','').replace(DOSSIER_ID,'dossier')) from None
    # 0.7.3 : la fiche technique est une « proposition » (sources non vérifiées par un tiers) ; valider_base
    # n'y exige donc ni corroboration ni passage. Une lecture réelle les doit pourtant (SKILL étape 3,
    # 0.7.1 et 0.7.2) : on les contrôle ici, pour chaque mot F, comme pour un cas actif.
    errs=[]
    for item in mots:
        if isinstance(item,dict) and item.get('intensite')=='F':
            k=cle_valide(f"{item.get('carte')}@{item.get('strate')}")
            errs+=controle_corroboration(k,item,True)+controle_passage(k,item,'F',True)
        if isinstance(item,dict):
            errs+=controle_classe_source(cle_valide(f"{item.get('carte')}@{item.get('strate')}"),item,True)
            errs+=controle_grille(cle_valide(f"{item.get('carte')}@{item.get('strate')}"),item)
    exiger(not errs,'dossier refusé — '+' ; '.join(errs))
    errs,manques=controle_recherches(d.get('recherches'),set(fm),keys)
    exiger(not errs,'dossier refusé — '+' ; '.join(errs))
    manques+=signalements_circularite(mots)
    errs,sig=controle_concessions(d.get('concessions'),fm,keys,len(mots));exiger(not errs,'dossier refusé — '+' ; '.join(errs));manques+=sig
    return {'conforme':True,'complet':not manques,'manques':manques,'etat':etat,'mots':len(mots),'candidats':keys,'contre_candidate':contre,
            'disponible_le':d.get('disponible_le') or e['date'],
            'evenements':evs or [],'sceau':empreinte(d),
            'instruction':'Publier ce sceau avant de lancer le calcul, puis lancer « calculer --dossier ». '
                          'Il fige la lecture et les événements, pas le jugement (voir sceller-jugement).'}


def cloture(base):
    """0.7.11 (open-ontologies : extension conservatrice). « Aucune probabilité ne change » se vérifiait sur
    des calculs témoins ; une conséquence hors témoin pouvait changer sans être vue. Le vocabulaire est fini :
    on calcule donc, pour **chaque** état daté de la base (séquences et issues) et **chaque** événement
    à un pas sur ses strates (16 cartes : apparition si absente, persistance et disparition si présente,
    cartes Hors domaine exclues), p, l'intervalle, ρ et p sans cartes. Le placebo d'homologie (200
    tirages par calcul) est hors clôture, et le dit. Un calcul refusé est compté « désarmé » : au-delà de
    la moitié, la clôture n'établit rien. Empreinte SHA-256 de l'ensemble, comparable d'une version à l'autre."""
    etats={}
    for c in base:
        for x in c['sequence']+[c['issue']]:
            if isinstance(x,dict) and x.get('etat'):etats.setdefault(x['etat'],None)
    res={};desarmes=0
    for st in sorted(etats):
        e=lire_etat(st);fm=forces(e)
        for s_ in sorted({m['s'] for m in e['mots']}):
            for ab in NOMS:
                k=f'{ab}@{s_}'
                if hors_domaine(k):continue
                for typ in (('persiste','disparait') if k in fm else ('apparait',)):
                    cle_=f'{st} :: {k} {typ}'
                    try:
                        r=calculer(e,typ,k,base);r0=calculer(e,typ,k,base,sans_cartes=True)
                        res[cle_]={'p':r['p'],'intervalle':r['intervalle'],'rho':r['rho'],'p_sans_cartes':r0['p']}
                    except ValueError as x_:
                        desarmes+=1;res[cle_]={'desarme':str(x_)[:120]}
    n=len(res)
    return {'version':P['version'],'etats':len(etats),'consequences':n,'desarmes':desarmes,
            'probant':n>0 and desarmes<=n/2,'hors_cloture':['p_placebo (200 tirages par calcul)','horizons de plus d’un pas','composés'],
            'empreinte':empreinte(res),'empreinte_portable':empreinte(arrondir(res)),'resultats':res}


def arrondir(x,chiffres=10):
    """0.7.18. Flottants arrondis à `chiffres` décimales, récursivement. L'empreinte stricte hache les flottants
    au bit près : elle peut différer d'une plateforme à l'autre (bibliothèque mathématique) sans qu'une
    conséquence change d'une manière lisible. L'empreinte portable sert à comparer deux plateformes ;
    l'empreinte stricte reste celle du journal."""
    if isinstance(x,float):return round(x,chiffres)
    if isinstance(x,dict):return {k:arrondir(v,chiffres) for k,v in x.items()}
    if isinstance(x,(list,tuple)):return [arrondir(v,chiffres) for v in x]
    return x


def comparer_clotures(a,b):
    """Conséquences changées entre deux clôtures de la même base (clés communes), et clés propres à l'une."""
    ra,rb=a['resultats'],b['resultats']
    changees=sorted(k for k in set(ra)&set(rb) if ra[k]!=rb[k])
    hors_arrondi=[k for k in changees if arrondir(ra[k])!=arrondir(rb[k])]
    return {'communes':len(set(ra)&set(rb)),'changees':len(changees),'changees_hors_arrondi':len(hors_arrondi),'exemples':changees[:10],
            'seulement_avant':len(set(ra)-set(rb)),'seulement_apres':len(set(rb)-set(ra)),
            'conservative':not changees and set(ra)==set(rb)}


def accord(a,b,c,d,repetabilite=False,ecart_jours=None,llm=False):
    """0.7.9. Accord de deux codeurs sur une carte, à partir de la table 2×2 de leurs décisions (a : les deux
    ancrent ; b : le premier seul ; c : le second seul ; d : aucun). κ (Cohen 1960) dépend de la prévalence :
    indéfini si pₑ = 1, effondré quand le code est rare (Feinstein et Cicchetti 1990). PABAK = 2·pₒ − 1
    (Byrt, Bishop et Carlin 1993) ne s'effondre pas, mais ne voit pas un codeur qui n'ancre jamais. On
    publie donc aussi les accords spécifiques positif et négatif (Cicchetti et Feinstein 1990) et les
    **deux** taux de manque, b/(a+b) et c/(a+c) : aucun codeur n'est la référence de l'autre (A4), un
    seul taux supposerait le contraire ; c/(c+d) (taux de faux positifs) est publié mais, sous faible
    prévalence, il est presque toujours voisin de zéro et n'informe pas. Verdict : sans objet si personne
    n'ancre ; non estimable si aucun codeur n'atteint `accord_min_ancrages` ancrages ; sinon PABAK ≥ kappa_min (et
    ≥ kappa_rapportable pour « rapportable ») **et** les deux taux de manque ≤ fnr_max."""
    # 0.7.10 : même table pour la **répétabilité** (le même codeur, deux passes à l'aveugle sur les mêmes
    # cas ; « bruit d'occasion »). C'est l'analyse d'accord par attributs de la métrologie (répétabilité
    # intra-évaluateur contre reproductibilité inter-évaluateurs), pas Gage R&R, réservé aux grandeurs
    # continues. a : ancré aux deux passes ; b : première seule ; c : seconde seule ; d : aucune. Deux passes
    # trop rapprochées mesurent la mémoire du premier codage : verdict « non recevable » sous
    # repetabilite_ecart_min_jours.
    for v in (a,b,c,d):exiger(type(v) is int and v>=0,'accord : a, b, c, d entiers ≥ 0')
    exiger(not(llm and repetabilite),'accord : --llm et --repetabilite s’excluent (exécutions d’un modèle contre passes d’un humain)')
    if repetabilite:exiger(type(ecart_jours) is int and ecart_jours>=0,'accord --repetabilite : --ecart-jours (entier ≥ 0, jours entre les deux passes) requis')
    n=a+b+c+d;exiger(n>0,'accord : table vide')
    po=(a+d)/n;p1=(a+b)/n;p2=(a+c)/n;pe=p1*p2+(1-p1)*(1-p2)
    k=None if abs(1-pe)<1e-12 else (po-pe)/(1-pe)
    se=None if k is None else math.sqrt(po*(1-po)/n)/(1-pe)
    m1=None if a+b==0 else b/(a+b);m2=None if a+c==0 else c/(a+c)
    r={'table':{'a':a,'b':b,'c':c,'d':d},'n':n,'prevalence':(2*a+b+c)/(2*n),'po':po,'pe':pe,'kappa':k,
       'kappa_intervalle_95_approche':None if se is None else [k-1.96*se,k+1.96*se],'pabak':2*po-1,
       'accord_positif':None if 2*a+b+c==0 else 2*a/(2*a+b+c),'accord_negatif':None if 2*d+b+c==0 else 2*d/(2*d+b+c),
       'manque_second':m1,'manque_premier':m2,'faux_positifs_second':None if c+d==0 else c/(c+d)}
    # 0.7.23 : intervalle de PABAK (approximation normale, SE = 2·√(pₒ(1−pₒ)/n)), publié avec n, le nombre de
    # décisions ; les décisions d'un même cas ne sont pas indépendantes : l'intervalle est optimiste.
    sp=2*math.sqrt(po*(1-po)/n);r['pabak_intervalle_95_approche']=[2*po-1-1.96*sp,2*po-1+1.96*sp]
    # 0.7.18 (Artstein et Poesio 2008 ; Krippendorff 2011). π de Scott (marges regroupées) : κ et π peuvent tomber de
    # part et d'autre de kappa_min, on publie les deux. α de Krippendorff, nominal, deux codeurs, sans valeur
    # manquante : α = 1 − (2n − 1)(b + c) / (n₀ n₁), n₀ et n₁ comptant les valeurs (et non les unités). Publiés,
    # hors du verdict.
    pi_=r['prevalence'];pep=pi_*pi_+(1-pi_)*(1-pi_);n1_=2*a+b+c;n0_=2*d+b+c
    r['pe_regroupe']=pep
    r['pi_scott']=None if abs(1-pep)<1e-12 else (po-pep)/(1-pep)
    r['alpha_krippendorff']=None if n0_*n1_==0 else 1-(2*n-1)*(b+c)/(n0_*n1_)
    # Taux de manque de la valeur **absence** : sous forte prévalence, c'est elle la valeur rare (a=90, b=5, c=5,
    # d=0 : pₒ 0,90, κ −0,05, PABAK 0,80, taux de manque des ancrages 0,05 ; aucune absence partagée).
    r['manque_absence_second']=None if c+d==0 else c/(c+d);r['manque_absence_premier']=None if b+d==0 else b/(b+d)
    if a+b+c==0:v='sans objet : aucun des deux codeurs n’ancre la carte'
    elif max(a+b,a+c)<P['accord_min_ancrages']:v=f'non estimable : moins de {P["accord_min_ancrages"]} ancrages pour chaque codeur'
    else:
        # Le taux de manque se lit depuis le codeur qui ancre assez : un codeur qui n'ancre jamais manque tout.
        ok=max(x for x,base_ in ((m1,a+b),(m2,a+c)) if x is not None and base_>=P['accord_min_ancrages'])<=P['fnr_max']
        v=('rapportable' if r['pabak']>=P['kappa_rapportable'] else 'provisoire' if r['pabak']>=P['kappa_min'] else 'insuffisant') if ok \
          else f'insuffisant : un codeur manque plus de {round(100*P["fnr_max"])} % des ancrages de l’autre'
        # 0.7.18 : la règle des deux taux de manque vaut pour la valeur rare. Si la carte est ancrée dans plus de la
        # moitié des décisions, la valeur rare est l'absence : même contrôle sur les absences de chaque codeur.
        if ok and r['prevalence']>.5:
            xs=[x for x,base_ in ((r['manque_absence_second'],c+d),(r['manque_absence_premier'],b+d)) if x is not None and base_>=P['accord_min_ancrages']]
            if not xs:v='non estimable : forte prévalence et moins de '+str(P['accord_min_ancrages'])+' absences pour chaque codeur'
            elif max(xs)>P['fnr_max']:v=f'insuffisant : forte prévalence, un codeur manque plus de {round(100*P["fnr_max"])} % des absences de l’autre'
    if repetabilite:
        r.update(type='repetabilite',ecart_jours=ecart_jours,
                 lecture='a : ancré aux deux passes ; b : première passe seule ; c : seconde seule ; manque_second et manque_premier se lisent « manque de la seconde / de la première passe »')
        if ecart_jours<P['repetabilite_ecart_min_jours']:
            v=f'non recevable : passes séparées de {ecart_jours} j, moins de {P["repetabilite_ecart_min_jours"]} j (la seconde passe mesure la mémoire du premier codage)'
    elif llm:
        r.update(type='repetabilite_llm',
                 lecture='a : ancré aux deux exécutions ; b : première seule ; c : seconde seule. Deux exécutions du même modèle, contextes séparés '
                         '(ou une exécution et une paraphrase du dossier, à publier à part) ; une stabilité élevée mesure la fiabilité, pas la validité')
    else:r['type']='reproductibilite'
    r['verdict']=v
    return r


def wilson(k,n):
    """Intervalle de Wilson à 95 % d'une proportion k/n (Wilson 1927), sans valeurs hors [0, 1]."""
    if not n:return None
    z=1.959964;p_=k/n;c=(p_+z*z/(2*n))/(1+z*z/n);h=z*math.sqrt(p_*(1-p_)/n+z*z/(4*n*n))/(1+z*z/n)
    return [max(0.,c-h),min(1.,c+h)]


def feuille_rejets(dossier):
    """0.7.9. Feuille de relecture aveugle des rejets d'un dossier : les candidates écartées et les faits
    de l'état, **sans** le motif du rejet ni la lecture retenue. Tirage de `rejets_tirage` rejets au plus,
    ordonné par SHA-256 du sceau du dossier : on ne peut pas choisir le tirage."""
    dv=dossier_valider(dossier)
    rej=sorted(cle_valide(str(k)) for k in (dossier.get('rejets') or {}))
    tir=sorted(rej,key=lambda k:hashlib.sha256(f"{dv['sceau']}:{k}".encode()).hexdigest())[:P['rejets_tirage']]
    faits=sorted({str(m.get(x)).strip() for m in dossier.get('mots') or [] for x in ('fait','contre_observation') if m.get(x)},
                 key=lambda f:hashlib.sha256(f"{dv['sceau']}|{f}".encode()).hexdigest())
    return {'sceau_dossier':dv['sceau'],'etat_date':lire_etat(dossier['etat'])['date'],'tirage':tir,'rejets_au_dossier':len(rej),
            'faits':faits,'consigne':'Pour chaque carte du tirage : « maintenu » ou « annule », avec une ligne de justification, '
                                    'sans consulter le motif du rejet ni la lecture retenue.'}


def erreurs_audit_rejets(audit,dossier):
    """0.7.9. Contrôle d'un audit de rejets : même tirage que la feuille, relecture déclarée aveugle,
    verdict pour chaque carte tirée, motif d'origine recopié exact, taux d'annulation cohérent."""
    err=[];f=feuille_rejets(dossier);rej={cle_valide(str(k)):v for k,v in (dossier.get('rejets') or {}).items()}
    if not isinstance(audit,dict):return ['audit_rejets : objet JSON requis']
    if audit.get('sceau_dossier')!=f['sceau_dossier']:err.append('audit_rejets : sceau d’un autre dossier')
    if [cle_valide(str(k)) for k in audit.get('tirage') or []]!=f['tirage']:err.append('audit_rejets : tirage différent de celui de la feuille (graine non choisie)')
    if audit.get('aveugle') is not True:err.append('audit_rejets : relecture non aveugle')
    if not (isinstance(audit.get('relecteur'),str) and audit['relecteur'].strip()):err.append('audit_rejets : relecteur requis')
    vs=audit.get('verdicts')
    if not isinstance(vs,list):return err+['audit_rejets : verdicts = liste']
    vus=set();ann=0
    for v in vs:
        if not isinstance(v,dict):err.append('audit_rejets : verdict = objet');continue
        k=cle_valide(str(v.get('carte')));vus.add(k)
        if v.get('verdict') not in ('maintenu','annule'):err.append(f'{k} : verdict = maintenu ou annule')
        if not (isinstance(v.get('justification'),str) and v['justification'].strip()):err.append(f'{k} : justification requise')
        if v.get('motif_original')!=rej.get(k):err.append(f'{k} : motif_original différent du motif du dossier')
        ann+=v.get('verdict')=='annule'
    if vus!=set(f['tirage']):err.append('audit_rejets : un verdict par carte tirée, ni plus ni moins')
    if vs and abs(audit.get('taux_annulation',-1)-ann/len(vs))>1e-9:err.append('audit_rejets : taux_annulation ≠ annulés / verdicts')
    return err


CLES_CODAGE=('mots','cartes','intensite','questions','recherches','liaisons','positions','retraits','preuves_liaisons',
             'preuves_qualificatifs','preuve_positions','strates','sans_evenement','etat','codage')


def export_codeur(cas):
    """0.7.8. Vue d'un cas pour un second codeur : les faits, leurs sources et les dates de disponibilité,
    sans le premier codage. Les faits sont regroupés par état, dédoublonnés et **mélangés** (ordre par
    SHA-256) : l'ordre et le regroupement par mot trahiraient la structure du premier codage. Exclus aussi
    les strates (le rattachement O1 est une décision de codage) et `sans_evenement` (un jugement B4).
    Limite : ces faits sont ceux que le premier codeur a retenus ; un codage indépendant part au mieux du
    dossier de sources complet. Un fait qui nomme une carte est signalé."""
    def faits(x):
        out={}
        for m in x.get('mots') or []:
            for k in ('fait','contre_observation'):
                if isinstance(m.get(k),str) and m[k].strip():out[m[k].strip()]={'fait':m[k].strip(),'source':m.get('source')}
        for r_ in x.get('retraits') or []:
            if isinstance(r_.get('fait'),str):out[r_['fait'].strip()]={'fait':r_['fait'].strip(),'source':r_.get('source')}
        return sorted(out.values(),key=lambda f:hashlib.sha256(f"{cas.get('id')}|{f['fait']}".encode()).hexdigest())
    seq=[{'date':x.get('date'),'disponible_le':x.get('disponible_le'),'faits':faits(x)} for x in cas.get('sequence') or []]
    iss=cas.get('issue') or {};issue={'date':iss.get('date'),'disponible_le':iss.get('disponible_le'),'faits':faits(iss)}
    sig=[f"{e['date']} : « {f['fait'][:50]} » nomme {', '.join(mots_de_cartes(f['fait']))}" for e in seq+[issue] for f in e['faits'] if mots_de_cartes(f['fait'])]
    return {'id':cas.get('id'),'fenetre':cas.get('fenetre'),'sequence':seq,'issue':issue,
            'avertissements':['Faits retenus par le premier codeur, sans leur rattachement : la sélection elle-même reste une trace du premier codage.']
                             +[f'fait qui nomme une carte (à reformuler avant envoi) : {x}' for x in sig]}


def voisins(base):
    """0.7.18 (stumpy, matrice de profil ; López de Prado 2018, ch. 4). Deux diagnostics de la base, sans effet
    sur p. (1) Pour chaque transition, son meilleur voisin par la similarité du moteur (H1 : égalité de l'état
    avec forces et qualificatifs ; H1.5 : Jaccard pondéré F = 1, f = 0,5), correspondances triviales exclues
    — même cas, ou fenêtres qui se recoupent. Une base où presque tout a un jumeau exact ne laisse aucune place
    à la sélection : le placebo ne peut pas s'en distinguer. (2) L'unicité moyenne ū de López de Prado
    (inverse de la moyenne harmonique de la concurrence mensuelle) : la part d'information propre de chaque
    transition, non utilisée par le calcul."""
    T=[t for c in base for t in transitions(c)]
    if not T:return None
    mois=lambda d:int(d[:4])*12+int(d[5:7])-1
    iv=[(mois(a['date']),mois(b['date'])) for _,a,b in T]
    q_=lambda e:{(cle(m),m['i'],tuple(sorted(m['q']))) for m in e['mots']}
    def sim(e1,e2):
        f1,f2=forces(e1),forces(e2)
        w1={k:(1. if v=='F' else .5) for k,v in f1.items()};w2={k:(1. if v=='F' else .5) for k,v in f2.items()};u=set(w1)|set(w2)
        return sum(min(w1.get(k,0),w2.get(k,0)) for k in u)/sum(max(w1.get(k,0),w2.get(k,0)) for k in u) if u else 0.
    best=[];jum=0;seuls=0
    for i,(ci,a,_) in enumerate(T):
        bs=None;ex=False
        for j,(cj,a2,_) in enumerate(T):
            if j==i or cj==ci or (iv[i][0]<iv[j][1] and iv[j][0]<iv[i][1]):continue
            s_=sim(a,a2);bs=s_ if bs is None else max(bs,s_)
            if a['mots'] and q_(a)==q_(a2):ex=True
        if bs is None:seuls+=1
        best.append(0. if bs is None else bs);jum+=ex
    n=len(best);bt=sorted(best);qq=lambda u:bt[min(n-1,int(u*n))]
    conc=defaultdict(int)
    for s_,e_ in iv:
        for m in range(s_,e_):conc[m]+=1
    un=[sum(1/conc[m] for m in range(s_,e_))/(e_-s_) for s_,e_ in iv if e_>s_]
    # 0.7.18 (confondant entre cartes : Académie des sciences 2017, Gao et al. 2022). Deux cartes toujours présentes
    # ensemble dans les états de la base ne se départagent pas : leurs effets sont confondus.
    etats_={}
    for c in base:
        for x in c['sequence']+[c['issue']]:
            if isinstance(x,dict) and x.get('etat'):etats_[x['etat']]=set(forces(lire_etat(x['etat'])))
    occ=defaultdict(int);paire=defaultdict(int)
    for ks in etats_.values():
        for k in ks:occ[k]+=1
        for k1 in ks:
            for k2 in ks:
                if k1<k2:paire[(k1,k2)]+=1
    cooc=sorted(({'cartes':[k1,k2],'ensemble':v,'jaccard':v/(occ[k1]+occ[k2]-v)} for (k1,k2),v in paire.items()),
                key=lambda x:(-x['jaccard'],-x['ensemble'],x['cartes']))
    # 0.7.18 (Boudon 1963, effet de groupement) : combien de cas et de transitions par strate ; une strate pauvre
    # rend l'emprunt H3 presque inévitable.
    ps_=defaultdict(lambda:[0,0])
    for c in base:
        for st_ in c['strates']:ps_[st_][0]+=1;ps_[st_][1]+=len(transitions(c))
    return {'transitions':n,'jumeau_H1_non_trivial':jum,'part_jumeau_H1':jum/n,'sans_voisin_non_trivial':seuls,
            'meilleur_voisin':{'moyenne':sum(best)/n,'mediane':qq(.5),'q95':qq(.95),'minimum':bt[0]},
            'au_dessus_jaccard_H15':sum(x>=P['jaccard_H15'] for x in best),'seuil':P['jaccard_H15'],
            'unicite':{'moyenne':sum(un)/len(un),'mediane':sorted(un)[len(un)//2],'minimum':min(un),
                       'part_inferieure_a_1':sum(x<1-1e-12 for x in un)/len(un),'concurrence_max':max(conc.values())} if un else None,
            'par_strate':{str(k):{'cas':v[0],'transitions':v[1]} for k,v in sorted(ps_.items())},
            'etats_distincts':len(etats_),'co_occurrence':{'paires':cooc[:10],'toujours_ensemble':sum(x['jaccard']>=1-1e-12 for x in cooc)},
            'lecture':'diagnostic de la base, sans effet sur p : une médiane du meilleur voisin à 1 signale un vocabulaire saturé '
                      '(la sélection des homologues n’a rien à discriminer) ; une médiane basse, des cas singuliers.'}


def confronter(base):
    """0.7.5. Confrontation de la matrice aux observations (P8 : la couverture n'est pas présumée). Pour
    chaque transition codée, chaque **apparition** observée est classée selon la règle même du moteur
    (`sources_de`, avec les liaisons et la position *manque* de l'état de départ) : atteignable dans la
    strate, par une propagation documentée, par un transfert ancré, seulement par une arête inter-strates
    abaissée d'un cran, ou **non atteignable**. Un départ depuis l'état nul est compté à part : le moteur
    n'en dit rien par construction. Deuxième mesure : maintien d'un mot au pas suivant selon le nombre de
    pas où il était déjà présent (âge), pour éprouver l'hypothèse de taux constant (graphe.md §2.4).
    Lit la base, ne calcule aucune probabilité. Les transitions d'un même cas ne sont pas indépendantes,
    et une base fictive ne renseigne que sur sa propre fabrication."""
    classes=('meme_strate','propagation_documentee','transfert_ancre','position_manque','inter_strates_abaissee','non_atteignable','etat_nul')
    compte={k:0 for k in classes};divergences=[];age=defaultdict(lambda:[0,0]);occ=defaultdict(lambda:[0,0])
    for c in base:
        if not isinstance(c,dict) or not isinstance(c.get('sequence'),list) or not isinstance(c.get('issue'),dict):continue
        seq=c['sequence']+[c['issue']]
        presence=defaultdict(int)
        for xa,xb in zip(seq,seq[1:]):
            a,b=lire_etat(xa['etat']),lire_etat(xb['etat'])
            fa,fb=forces(a),forces(b)
            try:links=lire_liaisons(xa.get('liaisons') or [],a)
            except ValueError:links=[]
            pos=xa.get('positions') or {}
            manque={cle_valide(pos['manque'])} if isinstance(pos,dict) and pos.get('manque') else set()
            for k in fa:
                age[min(presence[k],2)][0]+=1;age[min(presence[k],2)][1]+=k in fb
            # 0.7.6 : occasions d'éprouver chaque arête de la même strate (source présente, cible absente).
            for k in fa:
                ab,st_=k.split('@')
                for cb in P['matrice'].get(ab,{}):
                    t_=f'{cb}@{st_}'
                    if t_ not in fa:occ[(ab,cb)][0]+=1;occ[(ab,cb)][1]+=t_ in fb
            presence=defaultdict(int,{k:presence[k]+1 for k in fa})
            for x in sorted(set(fb)-set(fa)):
                if not fa:
                    cl='etat_nul';src=[]
                else:
                    src,_=sources_de(a,x,links,(),manque)
                    notes={y['note'] for y in src}
                    cl=('meme_strate' if 'même strate' in notes else 'propagation_documentee' if 'autre strate, propagation documentée' in notes
                        else 'transfert_ancre' if 'autre strate, transfert ancré' in notes else 'position_manque' if 'G4' in notes
                        else 'inter_strates_abaissee' if "autre strate, abaissée d'un cran" in notes else 'non_atteignable')
                compte[cl]+=1
                if cl in ('non_atteignable','etat_nul','inter_strates_abaissee'):
                    divergences.append({'cas':c.get('id'),'statut':c.get('statut_donnees'),'fictif':c.get('fictif'),'date':b['date'],
                                        'apparition':x,'depuis':sorted(fa),'classe':cl})
    motifs=defaultdict(int)
    for d in divergences:
        if d['classe']=='non_atteignable':motifs[(' + '.join(k.split('@')[0] for k in d['depuis']),d['apparition'].split('@')[0])]+=1
    n0,m0=age[0];n1=age[1][0]+age[2][0];m1=age[1][1]+age[2][1]
    test=None
    if n0 and n1:
        p0_,p1_=m0/n0,m1/n1;se=math.sqrt(p0_*(1-p0_)/n0+p1_*(1-p1_)/n1)
        reelle=bool(base) and all(isinstance(c,dict) and not c.get('fictif') and c.get('statut_donnees')=='actif' for c in base)
        zz=None if se==0 else (p1_-p0_)/se
        # 0.7.7 (règle figée avant les données) : la loi à taux variable s'ouvre si l'écart âge ≥ 1 − âge 0
        # dépasse deux écarts-types, sur au moins weibull_occasions_min occasions de chaque côté, en cas réels actifs.
        crit={'regle':f"|z| ≥ 2, ≥ {P['weibull_occasions_min']} occasions à l’âge 0 et à l’âge ≥ 1, cas réels actifs seulement",
              'applicable':reelle and n0>=P['weibull_occasions_min'] and n1>=P['weibull_occasions_min'],
              'atteint':reelle and n0>=P['weibull_occasions_min'] and n1>=P['weibull_occasions_min'] and zz is not None and abs(zz)>=2}
        test={'maintien_age_0':p0_,'maintien_age_1_et_plus':p1_,'ecart':p1_-p0_,'ecart_type':se,'critere_weibull':crit,
              'z':zz,'ecart_detectable_80':2.80*se,
              'lecture':'écart à comparer à l’écart détectable : un écart non significatif sur un petit effectif ne confirme pas le taux constant'}
    tot=sum(compte.values())
    na=sum(len(v) for v in P['matrice'].values())
    couverture={'aretes':na,'avec_une_occasion':sum(1 for v in occ.values() if v[0]>=1),
                'avec_dix_occasions':sum(1 for v in occ.values() if v[0]>=10),
                'lecture':'une arête sans occasion observée n’est ni confirmée ni réfutée : elle n’est pas estimable'}
    return {'apparitions':tot,'couverture_aretes':couverture,'classes':compte,'part_non_atteignable':compte['non_atteignable']/tot if tot else None,
            'motifs_non_atteignables':[{'depuis':k[0],'apparition':NOMS[k[1]],'occurrences':v} for k,v in sorted(motifs.items(),key=lambda t:-t[1])],
            'divergences':divergences,
            'age':{str(k) if k<2 else '2+':{'occasions':v[0],'maintiens':v[1],'taux':v[1]/v[0] if v[0] else None,'intervalle_95':wilson(v[1],v[0])} for k,v in sorted(age.items())},
            'test_age':test,
            'limites':['Les transitions d’un même cas ne sont pas indépendantes : effectifs et écarts-types sont optimistes.',
                       'Une base fictive ne renseigne que sur sa fabrication ; seuls des cas réels actifs confrontent la matrice au monde.',
                       'Une apparition non atteignable est une divergence à examiner (journal des lacunes, A2), pas une réfutation à elle seule.']}


def valider(chemin, registre=None):
    result=valider_base(charger(chemin), None if registre is None else lire_registre(registre))
    print(f"{result['cas']} cas · {result['actifs']} actifs recevables · {result['propositions']} propositions conformes, sources à vérifier"
          f" · {result['archives_exclues']} archives à revoir ; propositions et archives exclues des calculs")
    print('Contrôle structurel seulement : ne certifie ni la vérité des sources ni le jugement du codeur.'
          +('' if registre else ' Partage non recoupé avec un registre (--registre) : dates déclarées seulement.'))
    return True

# ───────────────────────── prévisions conditionnelles ─────────────────────────

def a_l_echelle(p, fenetre):
    return -math.expm1(math.log1p(-proba(p)) * duree_jours(fenetre)/P['fenetre_reference_jours']) if p<1 else 1.


def odds_module(f, lr):
    proba(f);exiger(math.isfinite(lr) and lr>0,'multiplicateur strictement positif requis')
    if f in (0.,1.): return f
    return f*lr/(1-f+f*lr)


def refs_valider(refs, fenetre, asof):
    exiger(isinstance(refs,dict),'références : objet indexé par événement requis')
    for event,r in refs.items():
        exiger(isinstance(r,dict),f'{event} : référence invalide')
        proba(r.get('frequence'),event)
        for k in ('source','definition','periode','fenetre','disponible_le'):
            texte_requis(r.get(k),f'{event}.{k}')
        exiger(meme_fenetre(r['fenetre'],fenetre), f'{event} : référence d’une autre fenêtre')
        exiger(jour(r['disponible_le'])<=jour(asof),f'{event} : référence indisponible à la date de prévision')
        # 0.6.14 : une clé mal formée nomme la clé fautive et le format attendu.
        exiger(isinstance(event,str) and len(event.split(' ',1))==2,f'référence « {event} » : clé « CARTE@strate type » requise (ex. « SEU@7 apparait »)')
        key,typ=event.split(' ',1)
        try:cle_valide(key)
        except (ValueError,IndexError):raise ValueError(f'référence « {event} » : « {key} » n’est pas une clé CARTE@strate') from None
        exiger(typ in ('apparait','persiste','disparait','hausse|persiste','transformation|persiste'),f'{event} : type de référence inconnu')
    errs=erreurs_references(refs);exiger(not errs,' ; '.join(errs))
    return refs


GABARIT_SOURCE='SOURCE À REMPLACER PAR UNE RÉFÉRENCE VÉRIFIÉE'


def erreurs_references(refs):
    """0.7.8 (`frequences-externes.md`). Deux erreurs que la forme ne voyait pas : une source recopiée du
    gabarit de `graphe.md` §2.2, et une classe de référence définie avec le vocabulaire des cartes
    (« épisodes de POLARITÉ ») — compter ce que l'alphabet a déjà codé, ce n'est pas une référence externe."""
    err=[]
    for event,r in (refs or {}).items():
        if not isinstance(r,dict):continue
        if GABARIT_SOURCE.lower() in str(r.get('source','')).lower():err.append(f'{event} : source du gabarit, à remplacer par une référence lue')
        cs=mots_de_cartes(r.get('definition',''))
        if cs:err.append(f'{event} : classe tautologique, la définition cite {", ".join(cs)} ; définir la classe dans le vocabulaire de la source')
        # 0.7.10 (Flyvbjerg 2008, représentation stratégique) : une fréquence fournie par le promoteur de
        # l'issue est un fait fabriqué, pas une donnée. Et deux taux mesurés depuis des référentiels
        # différents (décision contre contrat, Love et Ahiaga-Dagbui 2018) ne se comparent pas : le
        # référentiel se déclare s'il existe. Champs facultatifs, contrôlés s'ils sont présents.
        it=r.get('interet')
        if it is not None and it not in ('aucun','declare','promoteur'):err.append(f'{event} : interet parmi aucun, declare, promoteur')
        if it=='promoteur':err.append(f'{event} : source partie prenante de l’issue (interet « promoteur ») : représentation stratégique, référence refusée')
        if it=='declare':
            if not (isinstance(r.get('fourni_par'),str) and r['fourni_par'].strip()):err.append(f'{event} : interet « declare » sans fourni_par (qui fournit le taux, et son intérêt)')
        if 'referentiel' in r and not (isinstance(r['referentiel'],str) and r['referentiel'].strip()):err.append(f'{event} : referentiel vide (point de mesure du taux : décision, contrat…)')
    return err


def reference(refs, cible, typ):
    r=refs.get(cible+' '+typ)
    return r['frequence'] if r else None


def echantillon(base, typ, cible, fenetre, asof):
    s=int(cible.split('@')[1]);out=[]
    for c in base:
        if s not in c['strates'] or not meme_fenetre(c['fenetre'],fenetre): continue
        for cid,a,b in transitions(c):
            if not disponible(c,a,b,asof): continue
            ok,hit=issue_evenement(typ,cible,a,b)
            if ok: out.append((cid,a,b,bool(hit),c['sans_evenement']))
    return out


def ponderer(trans, asof, emprunt=False):
    counts=defaultdict(int)
    for t in trans: counts[t[0]]+=1
    out=[]
    for cid,a,b,hit,sans in trans:
        age=max(0,(jour(asof)-jour(b['date']))/365.25)
        # A case contributes at most one effective observation, even if it has many transitions.
        # 0.7.18 : López de Prado (2018, ch. 4) pondère par l'attribution de rendement |Σ r/c_t| ; sans amplitude de
        # transition et à fenêtre fixe, elle se réduit à l'unicité moyenne ū. Le recouvrement entre cas distincts
        # (ū = 0,705 sur la démonstration, `voisins`) n'est pas corrigé ici : le corriger change p, version séparée.
        # La décroissance reste chronologique, contre l'avis de la source (graphe.md §3.4, complément 0.7.18).
        w=(.5**(age/P['demi_vie_ans'])) / counts[cid]
        if emprunt: w*=P['w_emprunt']
        out.append({'id':cid,'debut':a['date'],'fin':b['date'],'poids':w,'issue':int(hit),'sans_evenement':sans})
    return out


def frequence_de_base(base, typ, cible, fenetre, asof, ref):
    samples=ponderer(echantillon(base,typ,cible,fenetre,asof),asof)
    n=sum(x['poids'] for x in samples); hit=sum(x['poids']*x['issue'] for x in samples)
    c=len({x['id'] for x in samples})
    value=(hit+P['k0_frequence']*ref)/(n+P['k0_frequence'])
    return value,c,n


def apriori(etat,typ,cible,base,liaisons=(),bouge=(),manque=(),refs=None,ctr_materielle=(),asof=None,sans_cartes=False):
    refs=refs or {}; asof=asof or etat['date'];c,s=cible.split('@');fen=etat['fenetre']
    inert=P['inertie_contrainte_materielle'] if c=='CTR' and s in ctr_materielle else P['inertie'][c]
    inert=inert**(duree_jours(fen)/P['fenetre_reference_jours'])
    if cible in bouge and not sans_cartes: inert=inert**P['multiplicateur_bouge']
    external=reference(refs,cible,typ);rref=refs.get(cible+' '+typ)
    if external is None and typ in ('persiste','disparait'):
        cle_c=cible+' '+('disparait' if typ=='persiste' else 'persiste');comp=reference(refs,cible,cle_c.split(' ',1)[1])
        external=None if comp is None else 1-comp;rref=refs.get(cle_c) if comp is not None else None
    # 0.6.13 (audit 0.6.12, m2) : la ligne S5 nomme la source externe en clair (constitution.md §3).
    source_ext=None if not rref else (str(rref.get('source','')).strip()+(f", {rref['periode']}" if rref.get('periode') else '')) or None
    default=a_l_echelle(P['f_defaut'],fen) if typ=='apparait' else (inert if typ=='persiste' else 1-inert)
    ref=default if external is None else external
    f,cnt,neff=frequence_de_base(base,typ,cible,fen,asof,ref)
    # 0.7.7 (décision 1) : deux seuils, deux sens. f est publié comme comparateur dès n_min_publication
    # observation pondérée (avec son intervalle et la part de l'a priori) ; il n'est dit « ancré » — accès à
    # ρ3 — que si les données pèsent au moins autant que l'a priori : neff ≥ n_min_ancrage (= k₀). Aucun p ne change.
    publie=external is not None or neff>=P['n_min_publication']
    anchored=external is not None or neff>=P['n_min_ancrage']
    src,removed=sources_de(etat,cible,liaisons,bouge,manque) if typ=='apparait' and not sans_cartes else ([],[])
    lr=math.prod(x['lambda'] for x in src)
    capped=lr>P['plafond_LR'];lr=min(lr,P['plafond_LR'])
    p=odds_module(f,lr)
    # Exact externally supplied boundaries are supported; never manufacture a beta law with zero parameters.
    # 0.6.9 : le plafond borne l'effet des cartes, pas la fréquence. Appliqué à toute p, il ramenait une
    # persistance d'inertie (99,5 % sur 7 jours) à 95 % sans toucher son complément (somme 96,2 %), et
    # 7 pas quotidiens plafonnés donnaient 0,95⁷ ≈ 70 % au lieu de la persistance sur 7 jours.
    if 0<p<1 and p>f: p=min(p,max(f,P['plafond_p0']))
    # 0.7.5 : f est la moyenne a posteriori d'une loi Beta(k₀·réf, k₀·(1−réf)) révisée par neff observations
    # pondérées (k₀ = pseudo-observations de l'a priori) ; on publie son poids et l'intervalle de cette loi.
    tot=neff+P['k0_frequence']
    itv_f=quantiles_beta(f*tot,(1-f)*tot) if 0<f<1 else None
    return {'p0':proba(p),'f_base':f if publie else None,'reference_interne':f,'ancrage':anchored,'publie':publie,
            'reference_a_priori':ref,'poids_a_priori_f':P['k0_frequence']/tot,'intervalle_f':itv_f,
            'reference_externe':external,'source_externe':source_ext,'cas_reference':cnt,'effectif_reference':neff,'LR':lr,'LR_plafonne':capped,
            'sources':src,'ecartees':removed,'inertie':inert}


def intervalle_beta(nE,nA,p0):
    # Quantiles de la loi Beta(nE + k·p₀, nA − nE + k·(1−p₀)) : la loi a posteriori dont p est la moyenne.
    a=nE+P['k']*p0;b=nA-nE+P['k']*(1-p0)
    if nA<=0 or a<=0 or b<=0: return None
    q=(1-P['intervalle'])/2
    return [proba(beta_quantile(a,b,q)),proba(beta_quantile(a,b,1-q))]


def quantiles_beta(a,b):
    if a<=0 or b<=0:return None
    q=(1-P['intervalle'])/2
    return [proba(beta_quantile(a,b,q)),proba(beta_quantile(a,b,1-q))]


BARREAUX = {'A': 'association', 'I': 'intervention documentée', 'C': 'contrefactuel documenté'}


def barreau_de(sources, cible):
    """Barreau de Pearl d'un calcul : le plus bas des transitions utilisées (A < I < C). Sans transition
    (persistance, disparition), l'inertie est une fréquence observée : association."""
    b = P['barreau']; ordre = 'AIC'
    rangs = [b['exceptions'].get(f"{x['mot'].split('@')[0]}>{cible.split('@')[0]}", b['defaut'])
             for x in sources if '@' in x['mot']]
    return min(rangs, key=ordre.index) if rangs else b['defaut']


def graine_placebo(etat,typ,cible,asof):
    """0.7.4 (décision 3). Graine dérivée de la question (état, événement, date d'information), non
    choisie : on ne peut pas essayer des graines jusqu'à obtenir le placebo qui arrange."""
    return int(hashlib.sha256(f'{texte(etat)}|{cible} {typ}|{asof}'.encode()).hexdigest()[:12],16)


A_REMPLIR='À REMPLIR'


def squelette_prevision(calc,ident):
    """0.7.38 (test régressif du 2026-11-03 : sept itérations pour découvrir les champs du journal). Une ligne de
    prévision complète, tirée du JSON de `calculer` : ce que le moteur sait est recopié ; ce que seul l'analyste peut
    dire porte « À REMPLIR », que `valider_journal` refuse. Rien n'est mis à null pour passer : un champ non rempli
    reste visible."""
    ctx=calc.get('contexte') or {};R=A_REMPLIR
    res=calc.get('resolution') if isinstance(calc.get('resolution'),dict) else {k:R for k in ('source','critere','seuil','marqueur','objet')}
    return {'type':'prevision','id':ident,'date':ctx.get('date_information',R),'echeance':calc.get('echeance',R),
            'version_regles':P['version'],'question':R,'evenement':calc.get('evenement',R),'episode_id':R,'pas':calc.get('pas',1),
            'indicateur_bascule':R,'refutation':R,'semantique':calc.get('semantique') or R,'etat_present':calc.get('etat',R),
            'probabilite':calc.get('p'),'intervalle':calc.get('intervalle'),'rho':'ρ'+str(calc.get('rho')) if calc.get('rho') is not None else R,
            'resolution':res,'resolution_verifiee':R+' (true ou false)','frequence_de_base':calc.get('comparateur'),'p_sans_cartes':calc.get('p_sans_cartes'),
            'vue_exterieure':(calc.get('vue_exterieure') or {}).get('declaree'),
            'vue_exterieure_alternative':(calc.get('vue_exterieure') or {}).get('alternative'),
            'mode_test':R+' (prospectif ou regressif)','date_limite_connaissance':R+' (AAAA-MM-JJ si regressif, sinon null)',
            'probabilite_jugement':None,'temporalite':calc.get('temporalite',R),'rejeu':R+' (true si une issue a pu être vue)',
            'fictif':bool(ctx.get('demo')),'partition':None,'p_placebo':calc.get('p_placebo'),'graine_placebo':calc.get('graine_placebo'),
            'apport_homologie':calc.get('apport_homologie'),'comparateur_externe':None,'calcul':calc,
            'empreintes':ctx.get('empreintes'),'preuve_prepublication':None}


def fiche_test(prev,score_=None):
    """0.7.34. Fiche Markdown d'une prévision journalisée (mode TEST) : lisible par un humain, et portant la ligne
    JSON exacte du journal dans un bloc `alphabet-test`, avec son empreinte. Coller la fiche dans le registre ;
    `ingerer` relira le bloc et vérifiera l'empreinte : une fiche retouchée à la main se détecte."""
    e=empreinte_prevision(prev);p=prev.get('probabilite');res=prev.get('resolution') or {}
    l=[f"## Test {prev['id']} · {prev.get('question','')}",'',
       f"- Date de la prévision : {prev['date']} · échéance : {prev.get('echeance','?')} · règles {prev.get('version_regles','?')}",
       f"- Événement : {prev.get('evenement','')} · état : {prev.get('etat_present','')}",
       f"- Probabilité : {'non estimée (abstention)' if p is None else pct(p)+' — bande : '+bande_verbale(p)}"
       +('' if prev.get('p_sans_cartes') is None else f" · sans cartes : {pct(prev['p_sans_cartes'])}"),
       f"- Résolution : {res.get('critere','') if isinstance(res,dict) else res} · source : {res.get('source','') if isinstance(res,dict) else ''}",
       '- Non calibré : paramètres posés à la main ; ce test sert à mesurer, non à conclure.']
    ve_=(prev.get('calcul') or {}).get('vue_exterieure')
    if ve_:l.append(f"- Vue extérieure (déclarée avant le calcul) : {pct(ve_['declaree'])} · {ve_['classe_de_reference']} · source : {ve_['source']}")
    if ve_ and ve_.get('ecart_critere'):l.append(f"- Classe et critère de résolution : {ve_['ecart_critere']}")
    if ve_ and ve_.get('alternative') is not None:l.append(f"- Classe alternative (scellée avec elle) : {pct(ve_['alternative'])} · {ve_['classe_alternative']}")
    l+=['',
       f"Empreinte de la prévision : `{e}`",'','```json alphabet-test',json.dumps(prev,ensure_ascii=False,sort_keys=True),'```','']
    return '\n'.join(l)


MODES_RESOLUTION=('positif','absence')
MODES_TEST=('prospectif','regressif')


def controle_resolution_score(ident,x):
    """0.7.44 (test P-0001). Une issue se tranche par une source ; la déclarée au dossier n'est pas toujours celle qui a
    servi (P-0001 : communiqués annoncés, Polymarket et ACLED utilisés ; issue établie par absence de preuve). Champs
    facultatifs pour les lignes antérieures, obligatoires pour `fiche-resultat` depuis 0.7.44 ; contrôlés s'ils sont là."""
    if 'mode_resolution' in x or 'source_utilisee' in x or 'source_conforme' in x:
        exiger(x.get('mode_resolution') in MODES_RESOLUTION,f'{ident} : mode_resolution « positif » (un document établit l’issue) ou « absence » (aucune trace trouvée)')
        texte_requis(x.get('source_utilisee'),f'{ident}.source_utilisee')
        exiger(type(x.get('source_conforme')) is bool,f'{ident} : source_conforme true ou false (la source utilisée est-elle celle du dossier ?)')
        if not x['source_conforme']:texte_requis(x.get('ecart_source'),f'{ident}.ecart_source (pourquoi une autre source que celle du dossier)')


def fiche_resultat(prev,issue,preuve,date_constat,note=None,source_utilisee=None,source_conforme=None,mode=None,ecart_source=None):
    """0.7.34. Fiche Markdown du résultat (mode RÉSULTAT) : l'issue constatée, sa preuve et sa date, liées à
    l'empreinte de la prévision ; bloc `alphabet-resultat` (ligne `score` du journal)."""
    exiger(issue is None or issue in (0,1),'issue : 0, 1, ou rien si non résolue');texte_requis(preuve,'preuve');date_iso(date_constat)
    exiger(jour(date_constat)>=jour(prev.get('echeance',prev['date'])),'résultat constaté avant l’échéance de la prévision')
    sc={'type':'score','id':prev['id'],'date':date_constat,'issue':issue,'preuve':preuve.strip(),'empreinte_prevision':empreinte_prevision(prev)}
    if note:sc['note']=note
    if source_utilisee is not None or mode is not None or source_conforme is not None:
        sc.update(source_utilisee=source_utilisee,source_conforme=source_conforme,mode_resolution=mode)
        if ecart_source:sc['ecart_source']=ecart_source
        controle_resolution_score(prev['id'],sc)
    sr_=(prev.get('resolution') or {}).get('source') if isinstance(prev.get('resolution'),dict) else None
    p=prev.get('probabilite')
    b=None if p is None or issue is None else (p-issue)**2
    l=[f"## Résultat {prev['id']}",'',f"- Constaté le {date_constat} · issue : {'non résolue' if issue is None else 'réalisée' if issue==1 else 'non réalisée'}",
       f"- Preuve : {preuve.strip()}",
       *([f"- Source utilisée : {sc['source_utilisee']} · {'conforme au dossier' if sc['source_conforme'] else 'AUTRE QUE CELLE DU DOSSIER ('+str(sr_)+') : '+sc.get('ecart_source','')}"
          f" · résolution {'positive (un document établit l’issue)' if sc['mode_resolution']=='positif' else 'PAR ABSENCE (aucune trace trouvée)'}"]
         if 'mode_resolution' in sc else []),
       f"- Brier de cette question : {'—' if b is None else f'{b:.3f}'}"+('' if prev.get('p_sans_cartes') is None or issue is None else
         f" · sans cartes : {(prev['p_sans_cartes']-issue)**2:.3f}")
         +('' if vue_exterieure_de(prev) is None or issue is None else f" · vue extérieure : {(vue_exterieure_de(prev)-issue)**2:.3f}")
         +('' if vue_alternative_de(prev) is None or issue is None else f" · classe alternative : {(vue_alternative_de(prev)-issue)**2:.3f}"),
       '- Un Brier isolé ne dit rien : seul le registre entier, scoré par `ingerer`, se lit.','',
       '```json alphabet-resultat',json.dumps(sc,ensure_ascii=False,sort_keys=True),'```','']
    return '\n'.join(l)


def ingerer(texte_):
    """0.7.34. Relit un registre Markdown : chaque bloc `alphabet-test` (une prévision) et `alphabet-resultat` (son
    issue). Vérifie que l'empreinte déclarée dans chaque résultat est celle de la prévision relue, que les lignes
    forment un journal valide, puis le score. Le Markdown est le support ; les blocs JSON sont la donnée."""
    blocs=re.findall(r'```json alphabet-(test|resultat)\n(.*?)\n```',texte_,re.S)
    tests=[json.loads(b) for k,b in blocs if k=='test'];res=[json.loads(b) for k,b in blocs if k=='resultat']
    exiger(tests,'registre : aucun bloc alphabet-test')
    emp={t['id']:empreinte_prevision(t) for t in tests}
    for r_ in res:
        exiger(r_.get('id') in emp,f"résultat {r_.get('id')} sans prévision dans le registre")
        exiger(r_.get('empreinte_prevision')==emp[r_['id']],f"résultat {r_['id']} : empreinte différente, la prévision a été modifiée après coup")
    journal=tests+[{k:v for k,v in r_.items() if k!='empreinte_prevision'} for r_ in res]
    valider_journal(journal)
    return {'previsions':len(tests),'resultats':len(res),'en_attente':sorted(set(emp)-{r_['id'] for r_ in res}),
            'score':score_result(journal),'journal':journal}


def depouiller(premier,second):
    """0.7.32 (audit DeepSeek, P1.4 ; A4 : « le calcul depuis deux fiches d'un même cas reste différé »). Deux
    codages indépendants des mêmes cas (fichiers JSONL, mêmes id, mêmes dates d'états) donnent, pour chaque carte,
    la table 2×2 de leurs décisions sur chaque état et chaque strate déclarée par l'un ou l'autre ; `accord` la
    lit. Rend aussi la table **groupée** (toutes cartes), celle de l'accord prospectif (validation.md §11.10).
    Les décisions d'un même état ne sont pas indépendantes : intervalles optimistes."""
    A={c['id']:c for c in premier};B={c['id']:c for c in second}
    exiger(A and set(A)==set(B),'depouiller : les deux fichiers doivent porter les mêmes cas (mêmes id)')
    tab={c:[0,0,0,0] for c in NOMS};etats=0
    for i in sorted(A):
        ea={x['date']:x for x in A[i]['sequence']+[A[i]['issue']]};eb={x['date']:x for x in B[i]['sequence']+[B[i]['issue']]}
        exiger(set(ea)==set(eb),f'depouiller : {i}, dates d’états différentes entre les deux codages')
        strates=sorted(set(A[i].get('strates') or [])|set(B[i].get('strates') or []))
        exiger(strates,f'depouiller : {i}, aucune strate déclarée')
        for d in sorted(ea):
            ka={cle(m) for m in lire_etat(ea[d]['etat'])['mots']};kb={cle(m) for m in lire_etat(eb[d]['etat'])['mots']};etats+=1
            for c in NOMS:
                for s in strates:
                    k=f'{c}@{s}';x,y=k in ka,k in kb
                    tab[c][0 if x and y else 1 if x else 2 if y else 3]+=1
    par={c:accord(*v) for c,v in tab.items() if v[0]+v[1]+v[2]>0}
    g=[sum(v[j] for v in tab.values()) for j in range(4)]
    return {'cas':len(A),'etats':etats,'par_carte':par,'groupe':accord(*g),
            'cartes_sans_ancrage':sorted(c for c,v in tab.items() if v[0]+v[1]+v[2]==0),
            'lecture':'table par carte : a les deux ancrent, b le premier seul, c le second seul, d aucun ; '
                      'décisions d’un même état non indépendantes, intervalles optimistes (§11.10 : bootstrap par états)'}


def cas_attestation(reference):
    """0.7.46 (décision d'auteur ; `protocole.md` A3). Un équivalent Attesté cite au moins deux cas réels d'événements
    distincts. Rend les numéros d'événement distincts lus dans la colonne Référence (`C-0001-S05` et `C-0001-S07` sont
    un seul événement). Contrôle de forme : ni l'indépendance des sources ni celle des événements n'est vérifiée."""
    return sorted(set(re.findall(r'\bC-(\d{4})(?:-S\d{2})?\b',reference or '')))


ARCHIVE_WAYBACK = re.compile(r'^https?://web\.archive\.org/web/(\d{4})(\d{2})(\d{2})\d{0,6}[a-z_]*/\S+$')


def date_archive(url):
    """0.7.48 (validation.md §26 ; El Lahib et al. 2026). Date d'un instantané de la Wayback Machine, lue dans son
    adresse (`web.archive.org/web/AAAAMMJJ…/`). Rend None pour une adresse qui n'en est pas une."""
    m=ARCHIVE_WAYBACK.match(url or '')
    return f'{m[1]}-{m[2]}-{m[3]}' if m else None


def recolter_ligne(fait,source,source_url,date_fait,disponible_le,date_consultation,classe_source,fiabilite=None,credibilite=None,
                   critere=None,motif=None,archive=None):
    """0.7.32 (audit DeepSeek, P0.1). Une ligne de carnet : un fait observé, daté, sourcé, avant tout codage. Le
    carnet ne code rien (ni carte, ni strate, ni force) : il garde le matériau brut et la date à laquelle il était
    disponible, pour qu'un dossier ne puisse citer que ce qui était connu à sa date d'information."""
    texte_requis(fait,'fait');texte_requis(source,'source')
    exiger(re.match(r'https?://\S+',source_url or '') is not None,'source_url : adresse http(s) requise')
    for v,n in ((date_fait,'date'),(disponible_le,'disponible_le'),(date_consultation,'date_consultation')):date_iso(v)
    exiger(jour(date_fait)<=jour(disponible_le)<=jour(date_consultation),'dates : fait ≤ disponible_le ≤ date_consultation')
    exiger(classe_source in CLASSES_SOURCE,f'classe_source = {", ".join(CLASSES_SOURCE)}')
    x={'fait':fait.strip(),'source':source.strip(),'source_url':source_url,'date':date_fait,'disponible_le':disponible_le,
       'date_consultation':date_consultation,'classe_source':classe_source}
    if fiabilite is not None:x['fiabilite_source']=fiabilite
    if credibilite is not None:x['credibilite']=credibilite
    err=controle_grille('carnet',x);exiger(not err,'; '.join(err))
    if critere or motif:
        exiger(critere in ('origine','producteur','transmission') and isinstance(motif,str) and motif.strip(),
               'independance : critere = origine, producteur ou transmission, avec un motif')
        x['independance']={'critere':critere,'motif':motif.strip()}
    if archive is not None:
        # 0.7.48 (validation.md §26). Une page lue en direct peut avoir été mise à jour, porter des encadrés récents ou un
        # horodatage faux : sa date affichée ne prouve pas ce qu'elle contenait. Un instantané figé le prouve, à sa date.
        # Le contenu lu dans l'instantané n'est établi qu'à la date de l'instantané : disponible_le ne peut pas la précéder.
        da=date_archive(archive)
        exiger(da is not None,'archive : adresse d’instantané Wayback requise (https://web.archive.org/web/AAAAMMJJ…/adresse)')
        date_iso(da)
        exiger(jour(da)<=jour(disponible_le),f'archive : instantané du {da}, postérieur à disponible_le ({disponible_le}) ; '
               'l’instantané ne prouve que ce qui existait à sa date : déclarer disponible_le au plus tôt à cette date, ou citer un instantané antérieur')
        exiger(jour(da)<=jour(date_consultation),f'archive : instantané du {da}, postérieur à la consultation ({date_consultation})')
        x['archive']=archive;x['archive_le']=da
    x['id']='F-'+hashlib.sha256(f"{x['fait']}|{x['source_url']}|{x['date']}".encode()).hexdigest()[:12]
    return x


def attribuer(etat,typ,cible,base,refs=None,asof=None,n_max=8):
    """0.7.31 (validation.md §12 ; Mogia, *Agent-Causality*). Attribution **dans le moteur** : le moteur est un
    évaluateur déterministe ; on recalcule p sur tous les sous-ensembles des mots de l'état (la cible reste pour
    persiste et disparait), puis on rend la valeur de Shapley exacte de chaque mot (en points de probabilité) et
    l'indice d'interaction de chaque paire (Grabisch 1997), en logit : l'a priori est additif en logit, un indice
    non nul y signale une interaction introduite par le choix des homologues. Ces nombres expliquent le **calcul**,
    jamais l'événement. Sans liaisons ni positions (refusées) ; au plus n_max mots, soit 2^n calculs."""
    from itertools import combinations
    asof=asof or etat['date'];cible=cle_valide(cible)
    joueurs=sorted(cle(x) for x in etat['mots'] if not (typ!='apparait' and cle(x)==cible))
    n=len(joueurs);exiger(1<=n<=n_max,f'attribuer : 1 à {n_max} mots attribuables (hors cible), reçu {n}')
    garde=[x for x in etat['mots'] if typ!='apparait' and cle(x)==cible]
    lg=lambda q:math.log(min(max(q,1e-12),1-1e-12)/(1-min(max(q,1e-12),1-1e-12)))
    v={}
    for k in range(n+1):
        for S in combinations(joueurs,k):
            e=dict(etat,mots=garde+[x for x in etat['mots'] if cle(x) in S])
            if not e['mots']:v[S]=calculer(etat,typ,cible,base,refs=refs,asof=asof,sans_cartes=True)['p']
            else:v[S]=calculer(e,typ,cible,base,refs=refs,asof=asof)['p']
    f_=math.factorial
    def val(S):return v[tuple(sorted(S))]
    shap={}
    for i in joueurs:
        autres=[j for j in joueurs if j!=i];s=0.
        for k in range(n):
            for S in combinations(autres,k):s+=f_(k)*f_(n-k-1)/f_(n)*(val(S+(i,))-val(S))
        shap[i]=s
    inter=[]
    for i,j in combinations(joueurs,2):
        autres=[x for x in joueurs if x not in (i,j)];s=0.
        for k in range(n-1):
            for S in combinations(autres,k):
                s+=f_(k)*f_(n-k-2)/f_(n-1)*(lg(val(S+(i,j)))-lg(val(S+(i,)))-lg(val(S+(j,)))+lg(val(S)))
        forme=('additive' if abs(s)<1e-9 else 'conjointe (renforcement)' if s>0 else 'concurrente (redondance)')
        inter.append({'paire':[i,j],'interaction_logit':s,'forme':forme})
    inter.sort(key=lambda x:-abs(x['interaction_logit']))
    return {'evenement':cible+' '+typ,'joueurs':joueurs,'calculs':len(v),'p_complet':val(tuple(joueurs)),'p_vide':val(()),
            'shapley_points':shap,'somme_shapley':sum(shap.values()),'interactions':inter,
            'non_additif':any(abs(x['interaction_logit'])>=1e-9 for x in inter),
            'lecture':'explique le calcul, pas l’événement : ce que chaque mot pèse dans p sous ce moteur et cette base ; '
                      'une interaction non nulle vient du choix des homologues, l’a priori étant additif en logit'}


def placebo_homologie(base,typ,cible,etat,asof,c_A,p0,graine,p_reel=None):
    """0.7.4 (décision 3). Placebo d'homologie : autant de cas distincts que la classe retenue, tirés au
    hasard dans la même strate et la même fenêtre (sans regarder les cartes), sous le même a priori p0 et
    la même révision. `p − p_placebo` sépare « l'analogie structurale apporte » de « le taux de base de la
    strate apporte ». Un tirage seul est bruité : on en moyenne `placebo_tirages`, chacun reproductible
    (rang de chaque cas par SHA-256 de graine:tirage:id, indépendant de la version de Python)."""
    pool=echantillon(base,typ,cible,etat['fenetre'],asof)
    ids=sorted({t[0] for t in pool})
    if not ids:return None
    n=min(c_A,len(ids));ps=[]
    for r in range(P['placebo_tirages']):
        choix=set(sorted(ids,key=lambda i:hashlib.sha256(f'{graine}:{r}:{i}'.encode()).hexdigest())[:n])
        sm=ponderer([t for t in pool if t[0] in choix],asof)
        a_=sum(x['poids'] for x in sm);e_=sum(x['poids']*x['issue'] for x in sm)
        ps.append((e_+P['k']*p0)/(a_+P['k']))
    ps.sort();q=lambda u:ps[min(len(ps)-1,int(u*len(ps)))]
    out={'p':proba(sum(ps)/len(ps)),'graine':graine,'tirages':len(ps),'cas_tires':n,'cas_disponibles':len(ids),
            'plage_90':[proba(q(.05)),proba(q(.95))]}
    if p_reel is not None:
        # 0.7.18 : même statistique que sonde_matrice (centile de permutation, ex æquo comptés pour moitié ;
        # une p-value prédictive au sens de Gelman et al., BDA3 §6.3). Nullité d'intérêt : « la sélection des
        # homologues ne fait pas mieux que des cas tirés au hasard » ; un centile proche de 0,5 dit que
        # l'instrument ne trouve rien, non que tout va bien. Résolution : 1/tirages.
        sous=sum(x<p_reel-1e-12 for x in ps);egaux=sum(abs(x-p_reel)<=1e-12 for x in ps)
        out.update({'centile_reel':(sous+egaux/2)/len(ps),'resolution':1/len(ps),
                    'nullite':'la sélection des homologues ne fait pas mieux que des cas tirés au hasard dans la strate'})
    return out


def calculer(etat,typ,cible,base,liaisons=(),bouge=(),manque=(),refs=None,ctr_materielle=(),asof=None,sans_cartes=False,placebo=False,**unused):
    exiger(typ in ('apparait','persiste','disparait'),'type non prévisionnel : F/f mesure la confiance, pas une intensité physique')
    asof=asof or etat['date']; date_iso(asof);cible=cle_valide(cible)
    fm=forces(etat)
    exiger((cible not in fm) if typ=='apparait' else (cible in fm),
           f'{cible} déjà présent dans l’état : « apparaît » est impossible. Un mot par carte et par strate (G6) : '
           'si le mot présent ne remplit pas vraiment le marqueur local, le retirer de l’état ; sinon la '
           'question porte sur sa persistance ou sa disparition. Une **nouvelle occurrence** d’une structure déjà présente '
           '(un autre paquet, une autre frappe, une autre expulsion) se pose avec « s’intensifie » sur une grandeur cumulée '
           '(nombre d’actes), avec --resolution et la référence conditionnelle « CARTE@strate hausse|persiste » '
           '(simulation.md §4, « Nouvelle occurrence »)' if typ=='apparait' else
           f'{cible} absent de l’état : seul « apparaît » est possible')
    exiger(not hors_domaine(cible), f'{cible} : carte Hors domaine dans cette strate, aucun événement à prévoir (A3)')
    ap=apriori(etat,typ,cible,base,liaisons,bouge,manque,refs,ctr_materielle,asof,sans_cartes)
    allkeys=set(fm);strong={k for k,v in fm.items() if v=='F'}
    sourcekeys={x['mot'] for x in ap['sources'] if '@' in x['mot']}
    if typ!='apparait': sourcekeys={cible}
    levels={'H1':[],'H1.5':[],'H2':[]}
    for t in echantillon(base,typ,cible,etat['fenetre'],asof):
        fa=forces(t[1]);ka=set(fa);sa={k for k,v in fa.items() if v=='F'}
        # H1 is equality of the full, nonempty structural state including qualifiers.
        qa={(cle(m),m['i'],tuple(sorted(m['q']))) for m in t[1]['mots']}
        qe={(cle(m),m['i'],tuple(sorted(m['q']))) for m in etat['mots']}
        if allkeys and qa==qe: levels['H1'].append(t)
        wa={k:(1. if fa[k]=='F' else .5) for k in ka};we={k:(1. if fm[k]=='F' else .5) for k in allkeys}
        union=ka|allkeys
        score=sum(min(wa.get(k,0),we.get(k,0)) for k in union)/sum(max(wa.get(k,0),we.get(k,0)) for k in union) if union else 0
        if ka & allkeys and score>=P['jaccard_H15']: levels['H1.5'].append(t)
        if sourcekeys and sourcekeys<=ka: levels['H2'].append(t)
    counts={h:len({x[0] for x in ts}) for h,ts in levels.items()}
    # Niveau le plus strict qui atteint c_min_rho1 cas distincts ; sinon le plus strict non vide.
    # Raison : H1 ⊆ H1.5, donc « le niveau qui offre le plus de cas » ne retenait jamais H1 sous 30 cas
    # et échangeait la comparabilité contre l'effectif sans le dire.
    # 0.7.7 : choix du niveau séparé de sa sanction ρ (c_min_rho1). c_min_niveau vaut 3, le statu quo :
    # le porter à 2 (décision 4) change un p de démonstration, donc une version dédiée.
    h=next((h for h in levels if counts[h]>=P['c_min_niveau']),None)
    if h is None: h=next((h for h in levels if counts[h]>0),'H1')
    hom=[] if sans_cartes else levels[h]; borrowed=False
    if not hom and not sans_cartes and sourcekeys:
        statuses=statuts();target,st=cible.split('@');st=int(st)
        original=sourcekeys|{cible}
        if all(statuses.get((k.split('@')[0],int(k.split('@')[1]))) in ('Attesté','Documenté') for k in original):
            cards={k.split('@')[0] for k in sourcekeys}
            for case in base:
                if not meme_fenetre(case['fenetre'],etat['fenetre']):continue
                for cid,a,b in transitions(case):
                    if not disponible(case,a,b,asof):continue
                    for s in sorted(set(case['strates'])-{st}):
                        if not all(statuses.get((ab,s)) in ('Attesté','Documenté') for ab in cards|{target}):continue
                        if not {f'{ab}@{s}' for ab in cards}<=set(forces(a)):continue
                        ok,hit=issue_evenement(typ,f'{target}@{s}',a,b)
                        if ok:hom.append((cid,a,b,hit,case['sans_evenement']));break
            if hom:h='H3';borrowed=True
    samples=ponderer(hom,asof,borrowed)
    nA=sum(x['poids'] for x in samples);nE=sum(x['poids']*x['issue'] for x in samples);cA=len({x['id'] for x in samples})
    prob=(nE+P['k']*ap['p0'])/(nA+P['k'])
    # 0.7.6 : concentration des poids par cas (taille effective de Kish, (Σw)²/Σw²) : dit si c_A cas pèsent
    # comme c_A cas ou si quelques-uns font le calcul.
    wc=defaultdict(float)
    for x in samples:wc[x['id']]+=x['poids']
    kish=None if not wc else sum(wc.values())**2/sum(v*v for v in wc.values())
    part_max=None if not wc else max(wc.values())/sum(wc.values())
    # 0.7.3 — le choix du niveau d'homologie (H1 → H1.5 → H2) est discret et se décide sur un compte
    # (c_min_rho1). Deux lectures également conformes peuvent donc différer d'un cran sans que rien ne
    # le signale. On rend p pour chaque niveau non vide : la fragilité de niveau devient visible.
    niveaux={}
    for hx,ts in levels.items():
        sm=ponderer(ts,asof,False);a_=sum(x['poids'] for x in sm);e_=sum(x['poids']*x['issue'] for x in sm)
        if a_>0:
            niveaux[hx]={'c_A':len({x['id'] for x in sm}),'p':proba((e_+P['k']*ap['p0'])/(a_+P['k']))}
    fragilite=None if len(niveaux)<2 else max(v['p'] for v in niveaux.values())-min(v['p'] for v in niveaux.values())
    if sans_cartes:niveaux={};fragilite=None
    rho=2 if borrowed and cA>=P['c_min_rho1'] else 0 if cA>=P['seuil_rho0_cas_distincts'] else 1 if cA>=P['c_min_rho1'] else 3 if ap['ancrage'] else 4
    flags=['Modèle expérimental : multiplicateurs hypothétiques, performance prospective non établie.']
    if rho==0 and (mode_solo(base,int(cible.split('@')[1])) or not any(x['sans_evenement'] for x in samples)):
        rho=1;flags.append('ρ0 inaccessible : double codage insuffisant ou aucun cas sans événement.')
    if rho<=1 and samples:
        ordered=sorted(samples,key=lambda x:jour(x['fin']));mid=len(ordered)//2;halves=(ordered[:mid],ordered[mid:])
        if all(len({x['id'] for x in half})>=P['min_transitions_par_moitie'] for half in halves):
            rates=[(sum(x['poids']*x['issue'] for x in half)+.5)/(sum(x['poids'] for x in half)+1) for half in halves]
            if max(rates)/min(rates)>P['ratio_non_stationnarite']:rho=max(1,rho);flags.append('Non-stationnarité : plafond ρ1.')
    if not ap['ancrage']: flags.append('A priori non ancré : aucune référence externe vérifiée fournie et effectif de base insuffisant.')
    if ap['LR_plafonne']:flags.append('Produit des multiplicateurs plafonné.')
    if fragilite is not None and fragilite>P['ecart_niveaux_max']:
        detail=', '.join(f'{k} {v["p"]*100:.1f} % sur {v["c_A"]} cas' for k,v in niveaux.items())
        flags.append(f'Fragilité de niveau : p varie de {fragilite*100:.1f} points selon le niveau d’homologie retenu '
                     f'({detail}) ; le seuil c_min_rho1 décide seul du niveau.')
    return {'evenement':cible+' '+typ,'p':proba(prob),'intervalle':intervalle_beta(nE,nA,ap['p0']),
            'rho':rho,'homologie':h if hom else None,'nb_cas_par_niveau':counts,'c_A':cA,'n_A':nA,'n_E':nE,
            'niveaux':niveaux,'fragilite_niveau':fragilite,'poids_a_priori_p':P['k']/(nA+P['k']),
            'n_eff_kish':kish,'part_cas_le_plus_lourd':part_max,
            'placebo':placebo_homologie(base,typ,cible,etat,asof,cA,ap['p0'],graine_placebo(etat,typ,cible,asof),prob) if placebo and not sans_cartes and not borrowed else None,
            # 0.7.28 (validation.md §11.12) : inertie de strate, les mêmes tirages de cas que le placebo (même graine,
            # même nombre) sous p₀ = f, sans λ. placebo − inertie de strate isole l'a priori des cartes ; alphabet −
            # inertie de strate, l'effet des cartes à base de cas égale.
            'inertie_strate':placebo_homologie(base,typ,cible,etat,asof,cA,ap['reference_interne'],graine_placebo(etat,typ,cible,asof)) if placebo and not sans_cartes and not borrowed else None,
            'a_priori':ap,'comparateur':ap['f_base'],'transitions':samples,'drapeaux':flags,
            'incertitude':'intervalle de crédibilité à 80 % de la loi Beta a posteriori dont p est la moyenne (Beta-binomial) : '
                           'quantiles calculés exactement, mais sur une vraisemblance pondérée (décroissance, un cas pèse au plus une observation) '
                           'et conditionnellement à k (pseudo-observations de p₀), à p₀ et au choix des cas ; incertitude de codage et de modèle '
                           'non intégrée (bandes de sensibilité)',
            'barreau':barreau_de(ap['sources'],cible)}


def sensibilite(etat,typ,cible,base,opts,h,semantique,pieces=None):
    """0.6.0. Sous-spécification : une centaine de paramètres pour quelques cas, donc une infinité de
    jeux compatibles. On relance le même calcul sous des variantes plausibles des hypothèses non
    calibrées et l'on rend la bande obtenue. Elle mesure l'incertitude de modèle, que l'intervalle bêta
    (bruit d'échantillonnage seul) ne couvre pas. Aucun paramètre nouveau n'est estimé.

    0.7.3. La version 0.6.0 ne faisait varier que le PRIOR (multiplicateurs, inerties, fréquence par
    défaut). Or l'estimateur dépend aussi du choix de la CLASSE DE RÉFÉRENCE — seuil de Jaccard, force
    du lissage k et k₀, demi-vie de la pondération — et c'est cette classe qui décide quels cas entrent.
    Une bande qui ne bouge pas quand la classe change donne une fausse assurance : elle mesure le
    désaccord sur le prior, pas sur les données retenues. On sépare donc deux bandes, `modele` et
    `classe`, et l'on rend aussi l'effet de la force d'ancrage (canal homologie seulement)."""
    import copy
    sauve={k:copy.deepcopy(P[k]) for k in ('lambda','inertie','f_defaut','inertie_contrainte_materielle',
                                           'jaccard_H15','k','k0_frequence','demi_vie_ans')}
    lam=sauve['lambda'];jac=sauve['jaccard_H15']
    modele=[
        ('multiplicateurs un cran plus bas', {'lambda':{'F':lam['M'],'M':lam['f'],'f':1.0}}),
        ('multiplicateurs un cran plus haut', {'lambda':{'F':lam['F'],'M':lam['F'],'f':lam['M']}}),
        ('inerties − 0,05', {'inertie':{k:min(.99,max(.01,v-.05)) for k,v in sauve['inertie'].items()},
                             'inertie_contrainte_materielle':max(.01,sauve['inertie_contrainte_materielle']-.05)}),
        ('inerties + 0,05', {'inertie':{k:min(.99,max(.01,v+.05)) for k,v in sauve['inertie'].items()},
                             'inertie_contrainte_materielle':min(.99,sauve['inertie_contrainte_materielle']+.05)}),
        ('fréquence par défaut × ½', {'f_defaut':sauve['f_defaut']/2}),
        ('fréquence par défaut × 2', {'f_defaut':min(.99,sauve['f_defaut']*2)}),
    ]
    classe=[
        ('classe : Jaccard − 0,1', {'jaccard_H15':max(.05,round(jac-.1,10))}),
        ('classe : Jaccard + 0,1', {'jaccard_H15':min(.95,round(jac+.1,10))}),
        ('classe : lissage k ÷ 2', {'k':sauve['k']/2}),
        ('classe : lissage k × 2', {'k':sauve['k']*2}),
        ('classe : lissage k₀ ÷ 2', {'k0_frequence':sauve['k0_frequence']/2}),
        ('classe : lissage k₀ × 2', {'k0_frequence':sauve['k0_frequence']*2}),
        ('classe : demi-vie ÷ 2', {'demi_vie_ans':sauve['demi_vie_ans']/2}),
        ('classe : demi-vie × 2', {'demi_vie_ans':sauve['demi_vie_ans']*2}),
    ]
    sortie=[]
    try:
        P.update(copy.deepcopy(sauve))
        reference=horizon_result(etat,typ,cible,base,opts,h,semantique)['p']
        for groupe,variantes in (('modele',modele),('classe',classe)):
            for nom,modif in variantes:
                P.update(copy.deepcopy(sauve));P.update(modif)
                r=horizon_result(etat,typ,cible,base,opts,h,semantique)
                sortie.append({'variante':nom,'groupe':groupe,'p':r['p'],'c_A':r.get('c_A'),
                               'homologie':r.get('homologie'),'frappee':False,
                               'cas':sorted({t['id'] for t in r.get('transitions') or []})})
        # Force d'ancrage : seule la sélection des homologues y réagit (les λ viennent de la matrice).
        faible={'date':etat['date'],'fenetre':etat['fenetre'],
                'mots':[{'c':m['c'],'s':m['s'],'i':'f','q':m['q']} for m in etat['mots']]}
        P.update(copy.deepcopy(sauve))
        rf=horizon_result(faible,typ,cible,base,opts,h,semantique)
        # 0.7.6 : décision 5 en variante, hors bande. Atténuation par la force (w = 1 F, 0,5 f) et, si un
        # dossier fournit les pièces, par la fiabilité du signal (corroboration et passage), orthogonale à F/f.
        global ATTENUATION
        attenuations={}
        try:
            ATTENUATION={cle(m):(1.0 if m['i']=='F' else P['attenuation_w_f']) for m in etat['mots']}
            attenuations['force']=horizon_result(etat,typ,cible,base,opts,h,semantique)['p']-reference
            if pieces:
                ATTENUATION={k:(1.0 if v['corroboration']=='independantes' and v['passage']=='soutient' else P['attenuation_w_f'])
                             for k,v in pieces.items()}
                attenuations['corroboration_passage']=horizon_result(etat,typ,cible,base,opts,h,semantique)['p']-reference
        finally:ATTENUATION=None
        # 0.7.56 (§33) : deux sondes causales, hors bande et hors p publié. Règle des médiateurs (effet total),
        # puis ablation carte par carte : chaque mot retiré seul, toutes choses égales (contraste dans le modèle,
        # pas contrefactuel dans le monde).
        global MEDIATION
        mediation=None
        try:
            MEDIATION=True;MEDIATION_RETIRES.clear()
            rm_=horizon_result(etat,typ,cible,base,opts,h,semantique)
            mediation={'p':rm_['p'],'effet':rm_['p']-reference,'mediateurs_retires':sorted(set(MEDIATION_RETIRES))}
        except ValueError:pass
        finally:MEDIATION=False;MEDIATION_RETIRES.clear()
        ablation=[]
        for m_ in etat['mots']:
            k_=cle(m_)
            if k_==cible:continue
            try:
                pa_=horizon_result(appliquer(etat,'disparait',k_),typ,cible,base,opts,h,semantique)['p']
                ablation.append({'retire':k_,'p':pa_,'apport':reference-pa_})
            except ValueError:pass
        sortie.append({'variante':'forces d’ancrage abaissées d’un cran (F → f)','groupe':'lecture',
                       'p':rf['p'],'c_A':rf.get('c_A'),'homologie':rf.get('homologie'),'frappee':True})
    finally:
        P.update(sauve)
    # 0.7.3 : la sonde F → f est une autre lecture, pas une hypothèse de modèle : elle reste hors de la bande.
    ps=[x['p'] for x in sortie if x['groupe']!='lecture']
    pm=[x['p'] for x in sortie if x['groupe']=='modele']
    pc=[x['p'] for x in sortie if x['groupe']=='classe']
    s=P['seuil_decision']
    # La classe est dite instable si le niveau retenu ou l'effectif change : c'est un saut discret, que
    # la bande continue ne montre pas nécessairement.
    # 0.7.3 : instabilité = l'ensemble des cas retenus change. Un changement d'étiquette (H1.5 → H2) sur
    # les mêmes cas ne change pas la classe ; le correctif reçu le signalait comme une instabilité.
    signatures={tuple(x['cas']) for x in sortie if x['groupe']=='classe'}
    retour={'reference':reference,'min':min(ps),'max':max(ps),'variantes':sortie,'seuil_decision':s,
            'traverse_seuil':min(ps)<s<=max(ps),
            'modele':{'min':min(pm),'max':max(pm),'traverse_seuil':min(pm)<s<=max(pm)},
            'classe':{'min':min(pc),'max':max(pc),'traverse_seuil':min(pc)<s<=max(pc),
                      'instable':len(signatures)>1,
                      'niveaux':sorted({str(x['homologie']) for x in sortie if x['groupe']=='classe'}),
                      'effectifs':sorted({x['c_A'] for x in sortie if x['groupe']=='classe' if x['c_A'] is not None})},
            'effet_force':rf['p']-reference,'effet_attenuation':attenuations,
            'mediation':mediation,'ablation':ablation,
            'bande_large':max(ps)-min(ps)>P['largeur_max_affichage'],
            'saturee':any(abs(p-P['plafond_p0'])<1e-12 for p in ps)}
    # Deux bandes qui traversent le seuil ne se lisent pas de la même façon : on nomme celle qui décide.
    retour['origine_seuil']=('classe de référence' if retour['classe']['traverse_seuil'] else
                             'hypothèses de modèle' if retour['modele']['traverse_seuil'] else None)
    return retour



def sonde_matrice(etat,typ,cible,base,opts,h,semantique,tirage,n=None):
    """0.7.6. Variable sonde (Dreyfus et al. 2008, ch. 1) appliquée aux paramètres : le même calcul avec
    une matrice altérée au hasard. `aretes` : 66 paires (source, cible) tirées parmi les 240 possibles,
    intensités conservées ; `intensites` : étiquettes F/M/f permutées sur les arêtes réelles ; `inerties` :
    inerties permutées entre cartes. Le calcul de référence **sans multiplicateurs, homologues gardés**
    (`p_sans_multiplicateurs`) sépare ce qui vient de la matrice de ce qui vient de la révision par les cas :
    sans lui, l'apport d'une matrice aléatoire paraît grand alors qu'il vient des cas. Graine dérivée de
    la question ; tirages ordonnés par SHA-256. Lit, ne modifie rien."""
    import copy
    exiger(tirage in ('aretes','intensites','inerties'),'sonde : --tirage aretes, intensites ou inerties')
    n=n or P['placebo_tirages'];graine=graine_placebo(etat,typ,cible,opts.get('asof') or etat['date'])
    sauve={k:copy.deepcopy(P[k]) for k in ('matrice','inertie','lambda')}
    h_=lambda *x:hashlib.sha256(':'.join(map(str,(graine,)+x)).encode()).hexdigest()
    aretes=[(a,b,i) for a,row in sauve['matrice'].items() for b,i in row.items()]
    paires=[(a,b) for a in NOMS for b in NOMS if a!=b];ps=[]
    try:
        reel=horizon_result(etat,typ,cible,base,opts,h,semantique)['p']
        P['lambda']={k:1.0 for k in sauve['lambda']}
        sans_mult=horizon_result(etat,typ,cible,base,opts,h,semantique)['p']
        P.update(copy.deepcopy(sauve))
        sans_cartes=horizon_result(etat,typ,cible,base,dict(opts,sans_cartes=True),h,semantique)['p']
        for r in range(n):
            P.update(copy.deepcopy(sauve))
            if tirage=='aretes':
                choix=sorted(paires,key=lambda q:h_('a',r,*q))[:len(aretes)]
                its=sorted((x[2] for x in aretes),key=lambda i_,c=iter(range(10**6)):h_('i',r,next(c)))
                m_={a:{} for a in NOMS}
                for (a,b),i in zip(choix,its):m_[a][b]=i
                P['matrice']=m_
            elif tirage=='intensites':
                its=[x[2] for x in sorted(aretes,key=lambda x:h_('p',r,x[0],x[1]))]
                m_={a:{} for a in NOMS}
                for (a,b,_),i in zip(aretes,its):m_[a][b]=i
                P['matrice']=m_
            else:
                ks=sorted(NOMS);vs=[sauve['inertie'][k] for k in sorted(ks,key=lambda k:h_('n',r,k))]
                P['inertie']=dict(zip(ks,vs))
            ps.append(horizon_result(etat,typ,cible,base,opts,h,semantique)['p'])
    finally:
        P.update(sauve)
    ps.sort();q=lambda u:ps[min(len(ps)-1,int(u*len(ps)))]
    sous=sum(x<reel-1e-12 for x in ps);egaux=sum(abs(x-reel)<=1e-12 for x in ps)
    med=q(.5);apm=reel-sans_mult
    return {'tirage':tirage,'tirages':n,'graine':graine,'p_reel':reel,'p_sans_multiplicateurs':sans_mult,'p_sans_cartes':sans_cartes,
            'p_sonde_mediane':med,'p_sonde_90':[q(.05),q(.95)],'centile_reel':(sous+egaux/2)/n,
            'part_sans_effet':sum(abs(x-sans_mult)<=1e-12 for x in ps)/n,
            'apport_matrice_reel':apm,'apport_matrice_sonde_median':med-sans_mult,
            'apport_cas':sans_mult-sans_cartes,
            'lecture':('les inerties n’entrent pas dans ce calcul (apparition à un pas : la persistance de la cible n’est pas utilisée)'
                       if tirage=='inerties' and all(abs(x-reel)<=1e-12 for x in ps) else
                       f"matrice réelle au {round(100*(sous+egaux/2)/n)}ᵉ centile des sondes ; la matrice ajoute {apm*100:+.1f} points aux cas, "
                       f"une sonde médiane {(med-sans_mult)*100:+.1f}").replace('.',',')}


def cumul(a,r,h,q0=0):
    q=q0
    for _ in range(h):q=q*r+(1-q)*a
    return proba(q)


def horizon_result(etat,typ,cible,base,opts,h,semantique):
    r=calculer(etat,typ,cible,base,**opts)
    exiger(type(h) is int and 1 <= h <= P['pas_max'], 'nombre de pas invalide')
    allowed = ('presence','continue') if typ == 'persiste' else ('presence','au-moins-une-fois')
    # 0.7.39 (série 2, défaut 7) : le refus nomme les sémantiques admises.
    exiger(semantique in allowed, f'sémantique « {semantique} » incompatible avec « {typ} » ; admises ici : '+', '.join(allowed)
           +(' ; une nouvelle occurrence d’une carte présente s’écrit « CARTE@s s’intensifie » (simulation.md §4)' if typ in ('persiste','apparait') else ''))
    if h==1:return dict(r,semantique=semantique,pas=1)
    present=cible in forces(etat)
    ea=appliquer(etat,'disparait',cible);ep=appliquer(ea,'apparait',cible)
    ea['date']=ep['date']=etat['date']
    ra=calculer(ea,'apparait',cible,base,**opts);rp=calculer(ep,'persiste',cible,base,**opts)
    def f(a,p):
        if typ=='apparait':
            exiger(semantique in ('presence','au-moins-une-fois'),'apparition : presence ou au-moins-une-fois')
            return cumul(a,p,h) if semantique=='presence' else 1-(1-a)**h
        if typ=='persiste':
            exiger(semantique in ('presence','continue'),'persistance : presence ou continue')
            return cumul(a,p,h,1) if semantique=='presence' else p**h
        exiger(semantique in ('presence','au-moins-une-fois'),'disparition : absence finale (presence) ou au-moins-une-fois')
        return 1-cumul(a,p,h,1) if semantique=='presence' else 1-p**h
    used=[ra,rp] if semantique=='presence' else [ra] if typ=='apparait' else [rp]
    baseline=f(ra['comparateur'],rp['comparateur']) if ra['comparateur'] is not None and rp['comparateur'] is not None else None
    if semantique!='presence':
        b=used[0]['comparateur'];baseline=None if b is None else (1-(1-b)**h if typ=='apparait' else b**h if typ=='persiste' else 1-b**h)
    pl=None
    if all(x.get('placebo') for x in used):
        # 0.7.4 : placebo multi-pas = même combinaison que p, appliquée aux moyennes des tirages (approximation déclarée).
        pa=ra['placebo']['p'] if ra.get('placebo') else ra['p'];pp=rp['placebo']['p'] if rp.get('placebo') else rp['p']
        pl=dict(used[0]['placebo'],p=proba(f(pa,pp)),plage_90=None,multi_pas='combinaison des moyennes par pas')
    r.update(p=proba(f(ra['p'],rp['p'])),comparateur=baseline,rho=max(x['rho'] for x in used),intervalle=None,placebo=pl,
             pas=h,semantique=semantique,composantes={'apparition':ra,'persistance':rp})
    r['drapeaux']+=['Sources et probabilités supposées fixes sur l’horizon. Intervalle multi-pas non estimé : aucune propagation partielle de bornes.']
    return r


def compose(etat,typ,cible,base,opts,resolution):
    exiger(cible in forces(etat),'événement composé : mot absent')
    exiger(isinstance(resolution,dict),'événement composé : --resolution JSON obligatoire')
    for k in ('source','critere','seuil','marqueur','objet'):
        texte_requis(resolution.get(k),'resolution.'+k)
    if typ=='intensifie':
        for k in ('grandeur','unite','comparaison'):texte_requis(resolution.get(k),'resolution.'+k)
        values=resolution.get('observations')
        exiger(isinstance(values,list) and len(values)>=2,'intensification : deux observations datées au minimum')
        dates=[]
        for v in values:
            exiger(isinstance(v,dict) and type(v.get('valeur')) in (int,float) and math.isfinite(v['valeur']),'mesure numérique finie requise')
            d=jour(v.get('date'));exiger(d<=jour(opts['asof']),'observation de résolution postérieure à la date de prévision');dates.append(d)
        exiger(dates==sorted(set(dates)),'observations dans l’ordre, dates distinctes')
        key='hausse|persiste'
    else:
        exiger(not cible.startswith('TRA@') and 'TRA@'+cible.split('@')[1] not in forces(etat),'transformation déjà présente ou objet TRANSFORMATION')
        key='transformation|persiste'
    rp=calculer(etat,'persiste',cible,base,**opts)
    cond=reference(opts.get('refs',{}),cible,key)
    if cond is None:
        return {'evenement':cible+' '+typ,'p':None,'intervalle':None,'rho':4,'comparateur':None,
                'drapeaux':['Probabilité non estimée : fournir une référence conditionnelle propre à cet objet et à cette fenêtre. Aucun produit de marginales ni 1/3 par défaut.'],
                'composantes':{'persistance':rp},'resolution':resolution}
    return {'evenement':cible+' '+typ,'p':proba(rp['p']*cond),'intervalle':None,'rho':max(3,rp['rho']),
            'comparateur':None if rp['comparateur'] is None else rp['comparateur']*cond,
            'composantes':{'persistance':rp,'conditionnelle':cond},'resolution':resolution,
            'drapeaux':['P(composé)=P(persiste) × P(changement | persiste). Intervalle conjoint non estimé.']}


# ───────────────────────── trajectoires ─────────────────────────

LIAISONS_INFERENTIELLES=('transfert','inclusion','renforcement')


def modele_declare(result,typ,sem,liaisons):
    """0.7.14 (note « unifier représentation, inférence et dynamique », §5). Ce que p est, et ce que le
    calcul ne lit pas. p₀ a la forme exacte d'une conditionnelle log-linéaire à paires,
    logit p₀ = logit f + Σ ln λ ; mais la matrice n'est pas symétrique (12 entrées réciproques à intensité
    égale sur 66), donc ces conditionnelles ne dérivent d'aucune loi jointe garantie : une
    **pseudo-vraisemblance** (Besag 1975), pas un rapport de vraisemblance. Le quotient nomme ce que l'état
    calculé ne distingue pas : deux situations qui ne diffèrent que par là sont le même état pour le moteur."""
    ap=result.get('a_priori') or {}
    non_lues=sorted({t for _,t,_ in liaisons or [] if t not in LIAISONS_INFERENTIELLES})
    return {'estimande':{'apparait':'P(carte@strate présente à l’horizon | état, même fenêtre)','persiste':'P(carte@strate encore présente | état)',
                         'disparait':'P(carte@strate absente | état)'}.get(typ)+f' · sémantique {sem}',
            'lecture':'conditionnelle de pseudo-vraisemblance (logit p₀ = logit f + Σ ln λ) ; aucune loi jointe garantie, matrice non symétrique',
            'quotient':['objets','rôles','positions tient','liaisons '+'|'.join(x for x in ('conflit','tension','appui','reproduction','indépendance','écho'))],
            'champ':{'produit_lambda':ap.get('LR'),'plafonne':ap.get('LR_plafonne')},
            'liaisons_non_inferentielles':non_lues}


def noyau_joint(evenements,marginales,exclusions=()):
    """0.7.14 (même note, §6). Loi jointe d'un pas sur une **frontière** de 2 à 10 événements, de
    marginales imposées égales aux p de `calculer` : la loi d'entropie maximale sous ces contraintes,
    restreinte au support déclaré (paires mutuellement exclusives retirées). Sans exclusion, c'est le
    produit (horloges indépendantes) ; avec exclusions, ajustement proportionnel itératif depuis
    l'uniforme sur le support. Ne change aucun p : il dit comment la masse se répartit entre les
    configurations, simultanéités comprises, ce que le noyau concurrent de `trajectoires` ne représente pas."""
    k=len(evenements);exiger(2<=k<=10,'noyau : 2 à 10 événements (2^k configurations énumérées)')
    ex=[(evenements.index(a),evenements.index(b)) for a,b in exclusions]
    cells=[c for c in range(1<<k) if not any((c>>i)&1 and (c>>j)&1 for i,j in ex)]
    w={c:1./len(cells) for c in cells};conv=False;err=None
    for it in range(20000):
        for j,pj in enumerate(marginales):
            m1=sum(v for c,v in w.items() if (c>>j)&1)
            if (m1==0 and pj>0) or (m1==1 and pj<1):break
            for c in w:w[c]*=(pj/m1 if (c>>j)&1 else (1-pj)/(1-m1)) if 0<m1<1 else 1
        err=max(abs(sum(v for c,v in w.items() if (c>>j)&1)-pj) for j,pj in enumerate(marginales))
        if err<1e-12:conv=True;break
    n_=lambda c:bin(c).count('1')
    pn=lambda n:sum(v for c,v in w.items() if n_(c)==n)
    H=sum(-math.log1p(-min(x,1-1e-12)) for x in marginales)
    premier=[(1-math.exp(-H))*(-math.log1p(-min(x,1-1e-12)))/H if H else 0. for x in marginales]
    conf=sorted(([' + '.join(evenements[j] for j in range(k) if (c>>j)&1) or 'aucun',v] for c,v in w.items()),key=lambda x:-x[1])
    shown=[x for x in conf if x[1]>=P['seuil_affichage']]
    return {'evenements':evenements,'marginales':marginales,'exclusions':[[a,b] for a,b in exclusions],
            'convergence':conv,'ecart_marginal_max':err,
            'faisable':conv,'configurations':shown,'reste':sum(x[1] for x in conf if x[1]<P['seuil_affichage']),
            'p_aucun':pn(0),'p_exactement_un':pn(1),'p_deux_ou_plus':max(0.,1-pn(0)-pn(1)),
            'p_premier':dict(zip(evenements,premier)),'p_horizon':dict(zip(evenements,marginales)),
            'hypothese':'entropie maximale sous les marginales : indépendance hors exclusions déclarées ; aucune dépendance n’est estimée',
            'lecture':'p_horizon : l’événement est réalisé à l’échéance (marginale, égale à calculer) ; p_premier : il est le premier changement (noyau de trajectoires) ; deux estimandes, une loi'}


def trajectoires(etat,h,base,opts,strates_sup=()):
    exiger(all(type(s) is int and 1<=s<=NS for s in strates_sup),f'strates supplémentaires hors 1–{NS}')
    branches=[(1.,etat,[],0)];elague=0.;rho_el=0;ecarts=[];masse_simul=0.
    for step in range(h):
        new=[]
        for weight,e,path,rho in branches:
            candidates=[];present=set(forces(e))
            # Fixed original evidence cutoff; remove links and positions invalidated by simulated changes.
            op=dict(opts);op['liaisons']=[x for x in opts.get('liaisons',[]) if x[0] in present and x[2] in present]
            op['bouge']=[x for x in opts.get('bouge',[]) if x in present];op['manque']=[x for x in opts.get('manque',[]) if x not in present]
            for k in sorted(present):candidates.append(('disparait',k,calculer(e,'disparait',k,base,**op)))
            for s in sorted({m['s'] for m in e['mots']}|set(strates_sup)):
                for ab in NOMS:
                    k=f'{ab}@{s}'
                    if k not in present and not hors_domaine(k) and sources_de(e,k,op['liaisons'],op['bouge'],op['manque'])[0]:
                        candidates.append(('apparait',k,calculer(e,'apparait',k,base,**op)))
            # This competing-risk kernel is exploratory. Normalization depends on ALL candidates.
            hazards=[-math.log1p(-min(x[2]['p'],1-1e-12)) for x in candidates];H=sum(hazards)
            if step==0:masse_simul=1-math.exp(-H)*(1+H)
            sq=math.exp(-H);rr=max([rho]+[x[2]['rho'] for x in candidates])
            new.append((weight*sq,e,path+['statu quo'],rr,sq))
            for (t,k,r),haz in zip(candidates,hazards):
                q=(1-sq)*haz/H if H else 0
                new.append((weight*q,appliquer(e,t,k),path+[k+' '+t],rr,q))
                # 0.7.13 (audit comparatif, point 4) : au premier pas, la probabilité qu'un événement reçoit
                # dans le noyau concurrent n'est pas sa probabilité isolée (deux événements à 50 % y reçoivent
                # 37,5 % chacun, le statu quo 25 %). L'écart se publie : ce sont deux modèles, pas un.
                if step==0:ecarts.append({'evenement':f'{k} {t}','p_isole':r['p'],'p_trajectoire':q,'ecart':q-r['p']})
        keep=[]
        for x in new:
            if x[4]<P['seuil_affichage']:elague+=x[0];rho_el=max(rho_el,x[3])
            else:keep.append(x)
        keep.sort(key=lambda x:-x[0])
        for x in keep[P['faisceau_max']:]:elague+=x[0];rho_el=max(rho_el,x[3])
        branches=[x[:4] for x in keep[:P['faisceau_max']]]
    merged={}
    for w,e,path,rho in branches:
        sig=json.dumps(sorted((cle(m),m['i'],sorted(m['q'])) for m in e['mots']),ensure_ascii=False)
        if sig not in merged:merged[sig]={'p':0.,'etat':texte(e),'qualificatifs':{cle(m):m['q'] for m in e['mots'] if m['q']},'rho':0,'chemins':[]}
        x=merged[sig];x['p']+=w;x['rho']=max(x['rho'],rho);x['chemins'].append(path)
    shown=sorted([v for v in merged.values() if v['p']>=P['seuil_affichage']],key=lambda x:-x['p'])
    rare=sum(v['p'] for v in merged.values() if v['p']<P['seuil_affichage'])
    total=sum(x['p'] for x in shown)+rare+elague
    exiger(abs(total-1)<1e-8,'perte de masse dans les trajectoires')
    ecarts.sort(key=lambda x:-abs(x['ecart']))
    em=max((abs(x['ecart']) for x in ecarts),default=0.)
    return {'trajectoires':shown,'R1':rare,'R2':elague,'rho_R2':rho_el,'somme':total,
            # 0.7.14 : l'estimande du noyau, nommé ; et la masse que des horloges indépendantes de mêmes
            # marginales donneraient à deux changements ou plus au premier pas, que le noyau ne représente pas.
            'estimande':'premier changement parmi les candidats, un au plus par pas (horloges indépendantes tronquées)',
            'masse_simultanee_pas1':masse_simul,
            'ecart_marginales_pas1':{'max_absolu':em,'evenements':ecarts[:10],
                'lecture':'probabilité au premier pas dans le noyau concurrent − probabilité isolée (calculer) : un seul changement par pas, '
                          'aucune réalisation simultanée ; les deux ne dérivent pas d’une même distribution jointe'},
            'drapeaux':['Noyau exploratoire : un seul changement par pas ; calculer fait foi pour un événement isolé.']+
            ([f'Écart aux marginales : jusqu’à {em*100:.1f} points entre le premier pas et le calcul isolé ; ne pas lire une trajectoire comme la probabilité d’un événement.'] if em>=P['delta_discriminant'] else [])+
            (['Masse abandonnée > 30 % : distribution non représentative.'] if elague>P['alerte_R2'] else [])}

# ───────────────────────── journal et score ─────────────────────────

PROCEDURES_JUGEMENT=('seul','compromis','simulation','analogies','autre')


def valider_journal(data):
    prev={};scores={};partitions=defaultdict(list)
    for x in data:
        exiger(isinstance(x,dict),'ligne de journal : objet JSON requis')
        typ=x.get('type');exiger(typ in ('prevision','score'),'type de ligne : prevision ou score')
        # 0.7.38 : un squelette non rempli ne passe pas ; on liste tous les champs à remplir d'un coup.
        vides=sorted(k for k,v in x.items() if (isinstance(v,str) and A_REMPLIR in v) or (isinstance(v,dict) and any(isinstance(w,str) and A_REMPLIR in w for w in v.values())))
        exiger(not vides,f"{x.get('id')} : champs à remplir — "+', '.join(vides))
        ident=texte_requis(x.get('id'),'id');date_iso(x.get('date'))
        dest=prev if typ=='prevision' else scores
        exiger(ident not in dest,f'doublon {typ} : {ident}');dest[ident]=x
        if typ=='score':
            exiger('issue' in x,f'{ident} : champ issue requis (0, 1, ou null si non résolue)')
            exiger(x.get('issue') is None or (type(x['issue']) is int and x['issue'] in (0,1)),f'{ident} : issue 0, 1 ou null')
            texte_requis(x.get('preuve'),f'{ident}.preuve');controle_resolution_score(ident,x);continue
        origine=x.get('origine','moteur')
        exiger(origine in ('moteur','jugement'),f'{ident} : origine « moteur » ou « jugement »')
        if origine=='jugement':
            exiger(x.get('comparateur_externe') is None,f'{ident} : pas de comparateur externe sur une ligne « jugement » (calibration du codeur)')
            # Question nominative ou hors alphabet (« qui sera élu ? ») : probabilité humaine, journalisée
            # et scorée à part, jamais mêlée au score du moteur ni à V4.
            version_lue(x.get('version_regles'),ident+'.version_regles')
            for field in ('version_regles','question','evenement','episode_id','refutation'):
                texte_requis(x.get(field),f'{ident}.{field}')
            # 0.7.10 : « jugement » sous-spécifiait. Le jugement nu est la condition la moins bien mesurée
            # (Green et Armstrong 2007 ; Green 2005) ; il existe des procédures de référence (modèle de
            # compromis, Achen 2006 ; simulation à plusieurs passes ; analogies listées avant notation).
            # Prospectif : requis à compter de jugement_procedure_depuis.
            pr_=x.get('procedure')
            if pr_ is not None or jour(x['date'])>=jour(P['jugement_procedure_depuis']):
                exiger(pr_ in PROCEDURES_JUGEMENT,f'{ident} : procedure parmi {", ".join(PROCEDURES_JUGEMENT)} (requise depuis {P["jugement_procedure_depuis"]})')
            date_iso(x.get('echeance'));exiger(jour(x['date'])<jour(x['echeance']),f'{ident} : prévision datée à échéance ou après')
            proba(x.get('probabilite'),ident+'.probabilite')
            exiger(type(x.get('rejeu')) is bool and type(x.get('fictif')) is bool,f'{ident} : rejeu et fictif explicites requis')
            res=x.get('resolution');exiger(isinstance(res,dict),f'{ident} : résolution externe requise')
            for field in ('source','critere','seuil'):texte_requis(res.get(field),f'{ident}.resolution.{field}')
            part=x.get('partition');exiger(part is None or (isinstance(part,str) and part.strip()),f'{ident} : partition invalide')
            if part:partitions[part].append(x)
            continue
        for field in ('version_regles','question','evenement','episode_id','indicateur_bascule','refutation','semantique'):
            texte_requis(x.get(field),f'{ident}.{field}')
        date_iso(x.get('echeance')); state = lire_etat(x.get('etat_present'))
        exiger(jour(state['date']) <= jour(x['date']), f'{ident} : état postérieur à la prévision')
        exiger(type(x.get('pas')) is int and 1 <= x['pas'] <= P['pas_max'], f'{ident} : nombre de pas requis')
        exiger(fin_fenetre(state['date'], state['fenetre'], x['pas']) == date_iso(x['echeance']), f'{ident} : échéance incompatible avec état, fenêtre et pas')
        exiger(jour(x['date']) < jour(x['echeance']), f'{ident} : prévision datée à échéance ou après')
        exiger(jour(x['date'])<=jour(x['echeance']),f'{ident} : date après échéance')
        calc=x.get('calcul')
        # 0.6.14 (audit Manus, haute 1) : une prévision réelle d'origine moteur porte le calcul qui l'a
        # produite. Sans lui, une probabilité saisie à la main pouvait compter comme sortie du moteur.
        # Un chiffre humain relève d'origine « jugement ».
        if not x.get('fictif'):
            exiger(isinstance(calc,dict) and 'p' in calc and isinstance(calc.get('contexte'),dict),
                   f'{ident} : prévision réelle d’origine moteur sans calcul figé (JSON complet de calculer, contexte compris) ; '
                   'une probabilité saisie à la main se journalise avec origine « jugement »')
        # 0.6.11 : un calcul « non estimé » (p null) ne devient pas une prévision chiffrée. La ligne est
        # une **abstention** : probabilite null, calcul joint, hors partition ; scorer la compte à part.
        abst=isinstance(calc,dict) and 'p' in calc and calc['p'] is None
        if abst:
            exiger(x.get('probabilite') is None,f'{ident} : le calcul figé n’a pas estimé p ; une probabilité journalisée ne vient pas du moteur (journaliser une abstention, probabilite null, ou un jugement, origine jugement)')
            exiger(not x.get('partition'),f'{ident} : une abstention ne fait pas partie d’une partition')
        else:
            exiger(x.get('probabilite') is not None or calc is not None,f'{ident} : probabilite null seulement pour une abstention, avec le calcul figé « non estimé » joint')
            proba(x.get('probabilite'),ident+'.probabilite')
        if calc is not None:
            # Le calcul figé est la preuve de la probabilité journalisée : ils doivent coïncider.
            exiger(isinstance(calc,dict),f'{ident} : calcul doit être le résultat JSON du moteur')
            if calc.get('p') is not None:
                exiger(type(calc['p']) in (int,float) and abs(calc['p']-x['probabilite'])<1e-12,f'{ident} : probabilite différente du calcul figé')
            if calc.get('rho') is not None:
                exiger(str(x.get('rho'))==f"ρ{calc['rho']}",f'{ident} : rho différent du calcul figé')
            # 0.6.9 : le calcul figé prouve la question entière, pas seulement p et ρ. Un calcul étiqueté
            # pour un autre événement, ou un comparateur sans cartes recopié faux, passaient.
            if calc.get('evenement') is not None:
                exiger(isinstance(calc['evenement'],str),f'{ident} : calcul.evenement invalide')
                exiger(evenement_lire(calc['evenement'])==evenement_lire(x['evenement']),f'{ident} : événement différent du calcul figé')
            for champ in ('pas','semantique','echeance'):
                if calc.get(champ) is not None:
                    exiger(calc[champ]==x.get(champ),f'{ident} : {champ} différent du calcul figé')
            if 'p_sans_cartes' in calc:
                a_,b_=calc['p_sans_cartes'],x.get('p_sans_cartes')
                num=lambda v:type(v) in (int,float) and math.isfinite(v)
                exiger((a_ is None and b_ is None) or (num(a_) and num(b_) and abs(a_-b_)<1e-12),
                       f'{ident} : p_sans_cartes différent du calcul figé')
            if calc.get('etat') is not None:
                exiger(isinstance(calc['etat'],str),f'{ident} : calcul.etat invalide')
                e1,e2=lire_etat(calc['etat']),lire_etat(x.get('etat_present'))
                exiger((e1['date'],e1['fenetre'],forces(e1))==(e2['date'],e2['fenetre'],forces(e2)),f'{ident} : état différent du calcul figé')
            # 0.6.10 : fréquence de référence, intervalle « non estimé » et marqueur de résolution.
            if 'comparateur' in calc:
                a_,b_=calc['comparateur'],x.get('frequence_de_base')
                exiger((a_ is None and b_ is None) or (type(a_) in (int,float) and type(b_) in (int,float) and abs(a_-b_)<1e-12),
                       f'{ident} : frequence_de_base différente du comparateur du calcul figé')
            if 'intervalle' in calc and calc['intervalle'] is None:
                exiger(x.get('intervalle') is None,f'{ident} : intervalle journalisé alors que le calcul figé ne l’a pas estimé')
            ml=calc.get('marqueur_local')
            if isinstance(ml,dict) and isinstance(ml.get('marqueur'),str) and isinstance(x.get('resolution'),dict):
                r_=x['resolution']
                exiger(' '.join(str(r_.get('marqueur','')).split())==' '.join(ml['marqueur'].split())
                       or (isinstance(r_.get('ecart_marqueur'),str) and r_['ecart_marqueur'].strip()),
                       f'{ident} : resolution.marqueur différent du marqueur local du calcul (S1) ; le recopier, ou justifier l’écart dans '
                       'resolution.ecart_marqueur (champ de l’objet « resolution », 0.7.42)')
            if 'intervalle' in calc and calc['intervalle'] is not None:
                ci,xi=calc['intervalle'],x.get('intervalle')
                ok=lambda v:isinstance(v,list) and len(v)==2 and all(type(u) in (int,float) and math.isfinite(u) for u in v)
                exiger(ok(ci) and ok(xi) and all(abs(u-v)<1e-12 for u,v in zip(ci,xi)),
                       f'{ident} : intervalle différent du calcul figé')
        exiger('frequence_de_base' in x,f'{ident} : fréquence de base requise (null si non évaluable)')
        vr=version_lue(x['version_regles'],ident+'.version_regles')
        if vr>=(0,5,0):
            exiger('p_sans_cartes' in x,f'{ident} : p_sans_cartes requis depuis 0.5 (null pour un composé) : comparateur inertiel')
        if x.get('p_sans_cartes') is not None:proba(x['p_sans_cartes'],ident+'.p_sans_cartes')
        # 0.7.28 : inertie de strate, facultative (journaux antérieurs admis) ; contrôlée contre le calcul figé.
        if x.get('p_inertie_strate') is not None:
            proba(x['p_inertie_strate'],ident+'.p_inertie_strate')
            if isinstance(calc,dict) and calc.get('p_inertie_strate') is not None:
                exiger(abs(calc['p_inertie_strate']-x['p_inertie_strate'])<1e-12,f'{ident} : p_inertie_strate différent du calcul figé')
        # 0.7.4 (décision 3) : placebo d'homologie, au même titre que p_sans_cartes (null si non évaluable).
        if vr>=(0,7,4):
            for k_ in ('p_placebo','graine_placebo','apport_homologie'):
                exiger(k_ in x,f'{ident} : {k_} requis depuis 0.7.4 (null si non évaluable) : placebo d’homologie')
        if x.get('p_placebo') is not None:
            proba(x['p_placebo'],ident+'.p_placebo')
            exiger(type(x.get('graine_placebo')) is int,f'{ident} : graine_placebo entière requise avec p_placebo')
            exiger(x.get('probabilite') is None or (type(x.get('apport_homologie')) in (int,float) and abs(x['apport_homologie']-(x['probabilite']-x['p_placebo']))<1e-12),
                   f'{ident} : apport_homologie = probabilite − p_placebo')
        if isinstance(calc,dict):
            for k_ in ('p_placebo','graine_placebo'):
                if k_ in calc:
                    a_,b_=calc[k_],x.get(k_)
                    exiger(a_==b_ if not isinstance(a_,float) else (isinstance(b_,(int,float)) and abs(a_-b_)<1e-12),f'{ident} : {k_} différent du calcul figé')
        # 0.7.8 : comparateur externe aveugle, requis (null si non joué) depuis 0.7.8.
        if vr>=(0,7,8):
            exiger('comparateur_externe' in x,f'{ident} : comparateur_externe requis depuis 0.7.8 (null si le bras n’a pas été joué)')
        if x.get('comparateur_externe') is not None:
            exiger(not x.get('partition'),f'{ident} : un comparateur externe ne s’applique pas à une partition')
            errs=erreurs_comparateur(x['comparateur_externe'],x['question'],x['evenement'],x['date'])
            exiger(not errs,f'{ident} : '+' ; '.join(errs))
        # 0.7.4 (décision 1) : sceau du dossier de lecture et sa publication.
        pdos=x.get('preuve_dossier')
        if pdos is not None:
            exiger(isinstance(pdos,dict),f'{ident} : preuve_dossier = {{source, date, sceau}}')
            for k_ in ('source','date','sceau'):texte_requis(pdos.get(k_),f'{ident}.preuve_dossier.{k_}')
            date_iso(pdos['date'])
            exiger(re.fullmatch(r'[0-9a-f]{64}',pdos['sceau']) is not None,f'{ident} : preuve_dossier.sceau = SHA-256')
            sd=((calc or {}).get('dossier') or {}).get('sceau') if isinstance(calc,dict) else None
            exiger(sd is None or sd==pdos['sceau'],f'{ident} : sceau publié différent de celui du calcul figé')
        if vr>=(0,6,0):
            exiger('probabilite_jugement' in x,f'{ident} : probabilite_jugement requis depuis 0.6 (null si aucun jugement scellé)')
        if x.get('probabilite_jugement') is not None:
            proba(x['probabilite_jugement'],ident+'.probabilite_jugement')
            exiger(x.get('jugement_scelle') in {empreinte_jugement(x['question'],ev_,x['probabilite_jugement'],x['date']) for ev_ in libelles_evenement(x['evenement'])},
                   f'{ident} : jugement_scelle absent ou différent : question, probabilité et date doivent être recopiées à l’identique '
                   'de sceller-jugement (l’événement peut être écrit en forme courte ou longue, 0.7.40 ; --date est la date d’information '
                   'de la prévision, pas le jour du scellement, 0.7.42) ; un jugement se scelle avant le moteur')
        # 0.6.10 : temporalité déclarée. Une échéance programmée ou une durée de vie propre ne se chiffre
        # pas sur le taux générique : ρ4 refusé. Exigée à partir de version_regles 0.6.10.
        if vr>=(0,6,10):
            exiger(x.get('temporalite') in ('generique','programmee','duree_de_vie'),
                   f'{ident} : temporalite requise depuis 0.6.10 (generique, programmee ou duree_de_vie)')
        if x.get('temporalite') not in (None,'generique') and x.get('probabilite') is not None:
            # 0.6.13 : une référence de domaine, pas seulement « pas ρ4 » ; le calcul figé le prouve.
            exiger(isinstance(calc,dict) and calc.get('reference_de_domaine') is True,
                   f'{ident} : temporalité {x["temporalite"]} : une prévision chiffrée joint son calcul, fondé sur une référence de domaine (--fref ou --references) ; des cas seuls ne suffisent pas')
        if isinstance(calc,dict) and calc.get('temporalite') is not None:
            exiger(calc['temporalite']==x.get('temporalite','generique'),f'{ident} : temporalite différente du calcul figé')
        bs=x.get('bande_sensibilite')
        if bs is not None:
            exiger(isinstance(bs,list) and len(bs)==2,f'{ident} : bande_sensibilite [min, max]')
            proba(bs[0]);proba(bs[1]);exiger(bs[0]<=bs[1],f'{ident} : bande_sensibilite inversée')
        if x['frequence_de_base'] is not None:proba(x['frequence_de_base'],ident+'.frequence_de_base')
        # 0.7.40 (test T6, défaut 2) : la vue extérieure du dossier devient un bras scoré. Elle vivait dans le dossier et dans
        # le calcul figé, mais `frequence_de_base` doit égaler le comparateur du moteur : sur T6, le bras qui gagnait (0,02)
        # n'était mesuré par aucun score. Champ requis à partir de 0.7.40 (null sans dossier), égal à celui du calcul figé.
        ve_c=((x.get('calcul') or {}).get('vue_exterieure') or {}).get('declaree') if isinstance(x.get('calcul'),dict) else None
        if vr>=(0,7,40):
            exiger('vue_exterieure' in x,f'{ident} : vue_exterieure requise depuis 0.7.40 (taux de base du dossier, null sans dossier)')
        if x.get('vue_exterieure') is not None:
            proba(x['vue_exterieure'],ident+'.vue_exterieure')
            exiger(ve_c is None or abs(ve_c-x['vue_exterieure'])<1e-12,f'{ident} : vue_exterieure différente de celle du calcul figé')
        elif vr>=(0,7,40):
            exiger(ve_c is None,f'{ident} : vue_exterieure à recopier du calcul figé ({ve_c})')
        # 0.7.45 (test FR-RU) : le test régressif à l'aveugle (date d'information = limite de connaissance du codeur, issue
        # postérieure) est le seul immédiatement disponible avec un modèle de langage. Il se déclare : mode_test, et la limite
        # de connaissance, qui ne peut pas dépasser la date d'information. Hors V4 par construction, scoré dans son propre
        # bilan, au lieu de se confondre avec une prévision simplement non publiée.
        if vr>=(0,7,45):
            exiger(x.get('mode_test') in MODES_TEST,f'{ident} : mode_test « prospectif » ou « regressif » requis depuis 0.7.45')
        if x.get('mode_test') is not None:
            exiger(x['mode_test'] in MODES_TEST,f'{ident} : mode_test « prospectif » ou « regressif »')
            if x['mode_test']=='regressif':
                dl_=x.get('date_limite_connaissance');date_iso(dl_)
                exiger(jour(dl_)<=jour(x['date']),f'{ident} : date_limite_connaissance ({dl_}) après la date d’information ({x["date"]}) : '
                       'le codeur pouvait connaître l’issue ; ce n’est pas un test à l’aveugle (rejeu)')
            else:
                exiger(x.get('date_limite_connaissance') is None,f'{ident} : date_limite_connaissance réservée au mode « regressif »')
        # 0.7.43 : la classe alternative suit les mêmes règles que la vue extérieure (requise, null si absente, égale au calcul).
        va_c=((x.get('calcul') or {}).get('vue_exterieure') or {}).get('alternative') if isinstance(x.get('calcul'),dict) else None
        if vr>=(0,7,43):
            exiger('vue_exterieure_alternative' in x,f'{ident} : vue_exterieure_alternative requise depuis 0.7.43 (null sans classe alternative)')
        if x.get('vue_exterieure_alternative') is not None:
            proba(x['vue_exterieure_alternative'],ident+'.vue_exterieure_alternative')
            exiger(va_c is None or abs(va_c-x['vue_exterieure_alternative'])<1e-12,f'{ident} : vue_exterieure_alternative différente de celle du calcul figé')
        elif vr>=(0,7,43):
            exiger(va_c is None,f'{ident} : vue_exterieure_alternative à recopier du calcul figé ({va_c})')
        # 0.7.40 (test T6, défaut 3) : un état daté au mois (« [2026-06 | 3 mois] ») se lit au 1er : échéance au 2026-09-01
        # pour une question qui courait jusqu'au 2026-09-30. Une date de la question ou de la résolution postérieure à
        # l'échéance est refusée : la prévision ne couvrirait pas toute la question.
        if vr>=(0,7,40) and x.get('echeance'):
            tx_=' '.join([str(x.get('question',''))]+[str(v) for v in ((x.get('resolution') or {}).values() if isinstance(x.get('resolution'),dict) else [])])
            tard=sorted({d_ for d_ in re.findall(r'\b(\d{4}-\d{2}-\d{2})\b',tx_) if valide_date(d_) and jour(d_)>jour(x['echeance'])})
            exiger(not tard,f'{ident} : la question ou la résolution court jusqu’au {tard[-1] if tard else ""}, après l’échéance {x["echeance"]} ; '
                   'dater l’état au jour (ex. « [2026-06-30 | 3 mois] » finit le 2026-09-30), ou resserrer la question')
        exiger(type(x.get('rejeu')) is bool and type(x.get('fictif')) is bool,f'{ident} : rejeu et fictif explicites requis')
        exiger(re.fullmatch(r'ρ[0-4]',str(x.get('rho',''))) is not None,f'{ident} : rho invalide')
        itv=x.get('intervalle')
        if itv is not None:
            exiger(isinstance(itv,list) and len(itv)==2,f'{ident} : intervalle invalide')
            proba(itv[0]);proba(itv[1]);exiger(itv[0]<=itv[1],f'{ident} : intervalle inversé')
        res=x.get('resolution');exiger(isinstance(res,dict),f'{ident} : résolution externe requise')
        for field in ('source','critere','seuil','marqueur','objet'):texte_requis(res.get(field),f'{ident}.resolution.{field}')
        exiger(type(x.get('resolution_verifiee')) is bool,f'{ident} : contrôle S1 explicite requis')
        part=x.get('partition');exiger(part is None or (isinstance(part,str) and part.strip()),f'{ident} : partition invalide')
        if part:partitions[part].append(x)
        else:
            key,event_type=evenement_lire(x['evenement'])
            exiger(event_type not in ('renforce','affaiblit'),f'{ident} : ancien changement de confiance non prévisionnel')
            present = key in forces(state)
            exiger((not present) if event_type=='apparait' else present, f'{ident} : événement incompatible avec état')
            if event_type in ('transforme','intensifie'):
                exiger(x['pas']==1 and x['semantique']=='compose', f'{ident} : composé à un pas seulement')
            else:
                allowed=('presence','continue') if event_type=='persiste' else ('presence','au-moins-une-fois')
                exiger(x['semantique'] in allowed, f'{ident} : sémantique « {x["semantique"]} » incompatible ; admises ici : '+', '.join(allowed))
        for k in ('preuve_prepublication','empreintes'):
            exiger(k in x,f'{ident} : champ {k} requis (null si indisponible)')
        if x['empreintes'] is not None:
            exiger(isinstance(x['empreintes'],dict),f'{ident} : empreintes invalides')
            for key in ('moteur','parametres','base'):
                value=x['empreintes'].get(key)
                exiger(isinstance(value,str) and re.fullmatch(r'[0-9a-f]{64}',value),f'{ident} : SHA-256 {key} requis')
            # 0.6.14 : les empreintes sont celles du calcul figé, et non des chaînes déclarées. Si la
            # prévision porte la version courante, moteur et paramètres sont recalculés sur les fichiers.
            ce=(calc.get('contexte') or {}).get('empreintes') if isinstance(calc,dict) else None
            if ce is not None:
                exiger(ce==x['empreintes'],f'{ident} : empreintes différentes de celles du calcul figé')
            if not x.get('fictif') and x['version_regles']==P['version']:
                exiger(x['empreintes']['moteur']==fichier_sha(__file__) and x['empreintes']['parametres']==fichier_sha(RACINE/'assets/parametres.json'),
                       f'{ident} : empreintes moteur/paramètres différentes des fichiers de la version {P["version"]} : le calcul ne vient pas de ce moteur')
        proof=x['preuve_prepublication']
        if proof is not None:
            exiger(isinstance(proof,dict),f'{ident} : preuve de prépublication invalide')
            for k in ('source','date','empreinte_prevision'):texte_requis(proof.get(k),f'{ident}.preuve_prepublication.{k}')
            exiger(proof['empreinte_prevision']==empreinte_prevision(x), f'{ident} : preuve rattachée à une autre version de la prévision')
            exiger(jour(x['date'])<=jour(proof['date'])<jour(x['echeance']),f'{ident} : prépublication hors délai')
    # 0.7.5 (de Finetti 1937 : une probabilité porte sur une « épreuve bien déterminée »). Deux lignes qui
    # posent la même question — même épisode, même événement, même échéance : une révision — portent la
    # même épreuve : même source, critère, seuil et objet. Sinon la révision change la question et le
    # Brier moyenne deux épreuves sous une étiquette. Le document reçu proposait d'imposer le même critère
    # à toutes les lignes d'un même événement : ce serait refuser SEUIL@7 sur deux objets différents.
    epreuves={}
    for ident,x in prev.items():
        if not isinstance(x.get('resolution'),dict):continue
        k_=(x.get('episode_id'),' '.join(str(x.get('evenement','')).split()),x.get('echeance'))
        e_=tuple(' '.join(str(x['resolution'].get(c,'')).split()) for c in ('source','critere','seuil','objet'))
        if k_ in epreuves:
            exiger(epreuves[k_][1]==e_,f'{ident} : même question que {epreuves[k_][0]} (épisode, événement, échéance) avec une autre épreuve '
                   '(source, critère, seuil ou objet) ; une révision garde l’épreuve, sinon c’est une autre question : changer l’échéance ou l’épisode')
        else:epreuves[k_]=(ident,e_)
    for ident,s in scores.items():
        exiger(ident in prev,f'score orphelin : {ident}')
        exiger(jour(s['date'])>=jour(prev[ident]['echeance']),f'{ident} : score avant échéance')
    for key,items in partitions.items():
        exiger(len(items)>=2,f'partition {key} : au moins deux issues')
        exiger(len({x['question'] for x in items})==1 and len({x['echeance'] for x in items})==1 and len({x['date'] for x in items})==1
               and len({x['episode_id'] for x in items})==1,f'partition {key} : question, dates et épisode communs requis')
        exiger(len({x['evenement'] for x in items})==len(items),f'partition {key} : issues dupliquées')
        exiger(abs(sum(x['probabilite'] for x in items)-1)<1e-8,f'partition {key} : probabilités ne somment pas à 1')
        exiger(len({x.get('origine','moteur') for x in items})==1,f'partition {key} : origines mêlées (moteur et jugement)')
        fb=[x.get('frequence_de_base') for x in items]
        exiger(all(x is None for x in fb) or (all(x is not None for x in fb) and abs(sum(fb)-1)<1e-8),f'partition {key} : comparateur incomplet ou non normalisé')
        outcomes=[scores.get(x['id'],{}).get('issue') for x in items]
        if all(x is not None for x in outcomes):exiger(sum(outcomes)==1,f'partition {key} : exactement une issue réalisée')
    return prev,scores,partitions


def perte_log(items,champ,scores):
    """0.7.5. Score logarithmique (perte −ln de la probabilité donnée à l'issue réalisée), en regard du
    Brier : strictement propre lui aussi, plus sévère sur les erreurs confiantes, non borné (une
    probabilité 0 ou 1 démentie vaut l'infini, rendu null avec le drapeau `log_infini`)."""
    if any(x.get(champ) is None for x in items):return None
    t=0.
    for x in items:
        o=scores[x['id']]['issue'];q=x[champ] if o==1 else 1-x[champ]
        if len(items)>1 and o==0:continue           # partition : seule l'issue réalisée compte
        if q<=0:return float('inf')
        t-=math.log(q)
    return t


def brier_comparateur(items,scores,ech,origine):
    """0.7.8. Brier du comparateur externe (questions binaires du moteur seulement), et indicateurs : bras
    contaminé (publié, exclu du rapport), question discriminante contre le bras (|p − p_ext| ≥ δ, avant l'issue)."""
    c=items[0].get('comparateur_externe') if len(items)==1 and origine=='moteur' else None
    if c is None:return {'brier_comparateur':None,'comparateur_contamine':None,'discriminant_comparateur':None}
    cont=comparateur_contamine(c);o=scores[items[0]['id']]['issue']
    return {'brier_comparateur':None if cont else (c['probabilite']-o)**2,'comparateur_contamine':cont,
            'discriminant_comparateur':abs(items[0]['probabilite']-c['probabilite'])>=P['delta_discriminant']-1e-12}


def comparateur_externe(units):
    """0.7.8. Ce que vaut le dispositif entier contre un bras indépendant : Brier du bras, du moteur,
    améliorations et dégradations comptées, différentiel par épisode et tests exacts. Les bras contaminés
    sont comptés à part."""
    cont=sum(1 for x in units if x.get('comparateur_contamine'))
    v=[x for x in units if x.get('brier_comparateur') is not None]
    if not v and not cont:return None
    if not v:return {'questions':0,'contamines_exclus':cont,'lecture':'aucun bras aveugle et séparé : rien à comparer'}
    n=len(v);bc=sum(x['brier_comparateur'] for x in v)/n;bm=sum(x['brier'] for x in v)/n
    dm=differentiel(v,'brier_comparateur')
    return {'questions':n,'contamines_exclus':cont,'brier_comparateur':bc,'brier_moteur':bm,
            'ameliorations':sum(x['brier']<x['brier_comparateur'] for x in v),
            'degradations':sum(x['brier']>x['brier_comparateur'] for x in v),'par_episode':dm,
            'lecture':lecture_test(dm,'moteur contre comparateur externe') if bm!=bc else 'aucun écart : un apport nul se publie comme tel'}


def discriminant(items):
    """0.7.7 (décision 6). Une question est discriminante si, **avant l'issue**, p s'écarte d'au moins δ
    (points de probabilité) de p_sans_cartes ou de p_placebo : sinon elle ne peut rien départager entre
    l'alphabet et ses comparateurs. Calculé depuis le journal, non déclaré ; ne dépend pas de l'issue."""
    d=P['delta_discriminant']
    if any(x.get('probabilite') is None for x in items):return None
    refs=[(x['probabilite'],x.get(k)) for x in items for k in ('p_sans_cartes','p_placebo') if x.get(k) is not None]
    if not refs:return None
    return any(abs(a-b)>=d-1e-12 for a,b in refs)


def pertes_log(items,scores):
    l1,l2=perte_log(items,'probabilite',scores),perte_log(items,'p_sans_cartes',scores)
    inf=lambda v:v is not None and not math.isfinite(v)
    return {'log':None if inf(l1) else l1,'log_sans_cartes':None if inf(l2) else l2,'log_infini':inf(l1) or inf(l2)}


def test_signe(d):
    """Test exact du signe (Diebold et Mariano 1995, test de complément à petit effectif) sur des
    différentiels de perte d = perte(A) − perte(B), nuls exclus. H0 : médiane nulle. `p_amelioration` :
    P(au moins autant de d < 0 sous H0), unilatéral en faveur de A."""
    v=[x for x in d if abs(x)>1e-12];n=len(v);neg=sum(x<0 for x in v)
    if not n:return None
    up=lambda k:sum(math.comb(n,i) for i in range(k,n+1))/2**n
    return {'n':n,'ameliorations':neg,'degradations':n-neg,'nuls':len(d)-n,'p_amelioration':up(neg),
            'p_bilateral':min(1.,2*min(up(neg),up(n-neg)))}


def test_wilcoxon(d):
    """Test exact des rangs signés de Wilcoxon (même source), loi exacte conditionnelle aux rangs moyens
    en cas d'égalité, par programmation dynamique sur les rangs doublés (entiers). `p_amelioration` :
    P(W⁺ ≤ observé sous H0), W⁺ = somme des rangs des d > 0 (dégradations)."""
    v=[x for x in d if abs(x)>1e-12];n=len(v)
    if not n:return None
    o=sorted(range(n),key=lambda i:abs(v[i]));rang=[0]*n;i=0
    while i<n:
        j=i
        while j+1<n and abs(abs(v[o[j+1]])-abs(v[o[i]]))<1e-12:j+=1
        for t in range(i,j+1):rang[o[t]]=i+j+2          # rang moyen × 2
        i=j+1
    tot=sum(rang);dist=defaultdict(int);dist[0]=1
    for r in rang:
        nd=defaultdict(int)
        for k_,c_ in dist.items():nd[k_]+=c_;nd[k_+r]+=c_
        dist=nd
    w=sum(rang[i] for i in range(n) if v[i]>0);N=2**n
    return {'n':n,'W_plus':w/2,'p_amelioration':sum(c_ for k_,c_ in dist.items() if k_<=w)/N,
            'p_bilateral':min(1.,2*min(sum(c_ for k_,c_ in dist.items() if k_<=w),sum(c_ for k_,c_ in dist.items() if k_>=w))/N)}


def e_processus(d,decalage=0.):
    """0.7.12 (audit V34, D4). Les tests exacts du signe et de Wilcoxon sont à effectif fixe ; lus sur un
    journal croissant, à des moments choisis, ils gonflent l'erreur de type I. Un e-processus reste valide à
    tout instant (inégalité de Ville) : on peut le relire après chaque épisode et s'arrêter dès qu'il franchit
    1/α. Hypothèse nulle : E[d] ≥ −decalage (aucune amélioration au-delà de decalage). Paris fixes λⱼ sur
    x = −d − decalage, mélange uniforme sur une grille (Waudby-Smith et Ramdas 2024, paris à capital ;
    Ramdas et al. 2023, *Statistical Science*) : chaque produit Π(1 + λⱼxᵢ) est une surmartingale positive
    sous l'hypothèse nulle, leur moyenne aussi. Épisodes supposés indépendants, comme pour les tests exacts."""
    if not d:return None
    borne=2.+abs(decalage)                       # |d| ≤ 2 (partitions) ; 1 + λx > 0 pour λ < 1/borne
    lams=[j/(10*borne) for j in range(1,10)]
    caps=[1.]*len(lams);e_max=1.;franchi=None
    for i,x_ in enumerate(d,1):
        x=-x_-decalage
        caps=[c*(1+l*x) for c,l in zip(caps,lams)]
        e=sum(caps)/len(caps)
        if e>e_max:e_max=e
        if franchi is None and e>=1/P['v4_alpha']:franchi=i
    return {'e_valeur':e,'e_max':e_max,'seuil':1/P['v4_alpha'],'franchi_a_l_episode':franchi,'decalage':decalage}


def sequence_confiance(d,alpha=None):
    """0.7.51 (validation.md §28, levée du gel pour cet outil seul). Séquence de confiance sur la moyenne des d
    d'épisodes (Brier − référence), valide à tout moment de relecture : μ est gardé tant qu'aucun des deux
    e-processus unilatéraux, « E[d] ≥ μ » et « E[d] ≤ μ », ne franchit 2/α (inversion des tests par pari de
    `e_processus`, Waudby-Smith et Ramdas 2024). Même inférence que le bot Metaculus (`score_registre.py`), pour que
    les deux outils ne concluent pas différemment sur le §27. Verdict à trois valeurs ; « indéterminé » en est une."""
    if not d:return None
    a=alpha or P['v4_alpha'];s=2/a
    e_haut=lambda mu:e_processus(d,-mu)['e_valeur']                 # contre « E[d] ≥ μ » : croît avec μ
    e_bas=lambda mu:e_processus([-x for x in d],mu)['e_valeur']     # contre « E[d] ≤ μ » : décroît avec μ
    lo,hi=-2.,2.
    for _ in range(40):
        m_=(lo+hi)/2
        lo,hi=(lo,m_) if e_haut(m_)>=s else (m_,hi)
    haut=hi
    lo,hi=-2.,2.
    for _ in range(40):
        m_=(lo+hi)/2
        lo,hi=(m_,hi) if e_bas(m_)>=s else (lo,m_)
    bas=lo
    verdict=('meilleur que la référence (établi)' if haut<0 else 'moins bon que la référence (établi)' if bas>0
             else 'indéterminé')
    return {'intervalle':[bas,haut],'niveau':1-a,'verdict':verdict,
            'lecture':'d = Brier − Brier de référence, par épisode ; négatif = mieux que la référence ; valide quel que '
                      'soit le moment de relecture, sous indépendance des épisodes ; « indéterminé » tant que 0 est dedans'}


def differentiel(units,champ):
    """0.7.5. Différentiel de perte par épisode (d̄ de Diebold-Mariano : le numérateur ; on publie aussi sa
    dispersion et les tests exacts). Les questions liées d'un épisode sont moyennées : un épisode, une
    observation. L'autocorrélation d'ordre 1 des d d'épisodes rangés par date est descriptive : elle dit
    si des périodes se trompent ensemble, ce que le regroupement par épisode ne voit pas."""
    ep=defaultdict(list)
    for x in units:
        if x[champ] is not None:ep[x['episode_id']].append(x)
    if not ep:return None
    serie=sorted(((min(u['date'] for u in v),k,sum(u['brier']-u[champ] for u in v)/len(v)) for k,v in ep.items()))
    d=[t[2] for t in serie];n=len(d);m_=sum(d)/n
    sd=math.sqrt(sum((x-m_)**2 for x in d)/(n-1)) if n>1 else None
    den=sum((x-m_)**2 for x in d)
    r1=sum((d[i]-m_)*(d[i+1]-m_) for i in range(n-1))/den if n>2 and den>0 else None
    return {'episodes':n,'d_moyen':m_,'sigma_d':sd,'erreur_type':None if sd is None else sd/math.sqrt(n),
            'autocorrelation_1':r1,'test_signe':test_signe(d),'test_wilcoxon':test_wilcoxon(d),
            # 0.7.12 : lecture séquentielle, valide à tout instant (e_processus) ; s'ajoute aux tests exacts.
            'e_amelioration':e_processus(d),'e_gain_v4':e_processus(d,P['v4_gain_abs']),
            'sequence_confiance':sequence_confiance(d)}


def lecture_test(dm,nom):
    if dm is None or dm['test_signe'] is None:return f'{nom} : aucun épisode où les deux pertes diffèrent'
    p_=dm['test_wilcoxon']['p_amelioration'];q_=1-dm['test_signe']['p_amelioration'] if dm['test_signe'] else None
    sens='amélioration' if dm['d_moyen']<0 else 'dégradation' if dm['d_moyen']>0 else 'aucun écart moyen'
    return (f"{nom} : {sens} moyenne de {abs(dm['d_moyen']):.4f} sur {dm['episodes']} épisode(s) ; test du signe p = "
            f"{dm['test_signe']['p_bilateral']:.3f}, Wilcoxon p = {dm['test_wilcoxon']['p_bilateral']:.3f} (bilatéraux, exacts) — "
            +('non distinguable de zéro à cet effectif' if dm['test_wilcoxon']['p_bilateral']>=.05 else 'distinct de zéro au seuil de 5 %, sous réserve d’indépendance des épisodes'))


def apport_cartes(units):
    """Brier avec cartes moins Brier sans cartes, sur les questions qui portent p_sans_cartes.
    0.7.5 : la moyenne seule annonçait « les cartes améliorent le score ». Une moyenne n'est pas un test :
    différentiel par épisode, dispersion et tests exacts du signe et de Wilcoxon (`differentiel`)."""
    v=[x for x in units if x['brier_sans_cartes'] is not None]
    if not v:return None
    d=sum(x['brier']-x['brier_sans_cartes'] for x in v)/len(v)
    lg=[x for x in v if x.get('log') is not None and x.get('log_sans_cartes') is not None]
    dm=differentiel(v,'brier_sans_cartes')
    return {'questions':len(v),'brier_avec':sum(x['brier'] for x in v)/len(v),'brier_sans':sum(x['brier_sans_cartes'] for x in v)/len(v),
            'difference':d,'par_episode':dm,
            'log_avec':sum(x['log'] for x in lg)/len(lg) if lg else None,'log_sans':sum(x['log_sans_cartes'] for x in lg)/len(lg) if lg else None,
            'log_infini':sum(1 for x in v if x.get('log_infini')),
            'lecture':lecture_test(dm,'cartes contre inertie') if abs(d)>1e-12 else 'score dû à l’inertie seule : les cartes ne déplacent pas p'}


def jugements(units):
    """Score des probabilités humaines (origine « jugement »), séparé du moteur : c'est la calibration
    du codeur, que le moteur ne mesure pas. Référence : Brier d'une réponse à 50 %."""
    v=[x for x in units if x['origine']=='jugement']
    if not v:return None
    ref=sum(0.25 if not x['partition'] else (1-1/len(x['ids'])) for x in v)/len(v)
    pp=defaultdict(list)
    for x in v:pp[x.get('procedure') or 'non declaree'].append(x['brier'])
    return {'questions':len(v),'dont_rejeux':sum(x['rejeu'] for x in v),'brier':sum(x['brier'] for x in v)/len(v),
            'brier_reponse_indifferente':ref,'incertitude_annoncee':sum(x['incertitude_annoncee'] for x in v)/len(v),
            # 0.7.10 : par procédure déclarée, descriptif (aucun test : les effectifs seront petits).
            'par_procedure':{k:{'questions':len(b_),'brier':sum(b_)/len(b_)} for k,b_ in sorted(pp.items())}}


def moteur_contre_jugement(units):
    """0.6.0. Ce que le moteur ajoute au jugement scellé du codeur (Pearl : enregistrer l'écart entre
    l'intention et la délibération). Une amélioration moyenne peut cacher des dégradations : on les compte."""
    v=[x for x in units if x['brier_jugement'] is not None]
    if not v:return None
    n=len(v);bj=sum(x['brier_jugement'] for x in v)/n;bm=sum(x['brier'] for x in v)/n
    dm=differentiel(v,'brier_jugement')
    return {'questions':n,'brier_jugement':bj,'brier_moteur':bm,
            'degradations':sum(x['brier']>x['brier_jugement'] for x in v),
            'ameliorations':sum(x['brier']<x['brier_jugement'] for x in v),'par_episode':dm,
            'lecture':lecture_test(dm,'moteur contre jugement') if bm!=bj else 'aucun apport mesuré'}


def difficulte(units):
    """0.6.0. Un Brier s'améliore aussi en posant des questions faciles : une fréquence de référence
    extrême (< 0,1 ou > 0,9) rend « non » ou « oui » presque gratuit. Difficulté = 0,5 − |f − 0,5| (0.6.5 :
    croît avec la difficulté ; 0 pour une référence à 0 ou 1, 0,5 pour une référence à 50 %), f étant la
    fréquence de base au même horizon, à défaut la probabilité sans cartes. Score stratifié, rien d'interdit."""
    v=[x for x in units if x['difficulte'] is not None and x['origine']=='moteur']
    if not v:return None
    ext=[x for x in v if x['reference_difficulte']<.1 or x['reference_difficulte']>.9];mod=[x for x in v if x not in ext]
    tranche=lambda w:None if not w else {'questions':len(w),'brier':sum(x['brier'] for x in w)/len(w)}
    return {'questions':len(v),'difficulte_moyenne':sum(x['difficulte'] for x in v)/len(v),
            'part_extremes':len(ext)/len(v),'extremes':tranche(ext),'moderees':tranche(mod),
            'lecture':'gain non interprétable : plus de 70 % de questions à référence extrême' if len(ext)/len(v)>.7 else 'composition interprétable'}


def murphy(paires):
    """0.7.0. Décomposition du score de Brier (Murphy 1973, *J. Appl. Meteor.* 12, 595-600) sur des
    prévisions binaires : BS = fiabilité − résolution + incertitude (+ variance intra-classe, due au
    regroupement en déciles). La **fiabilité** mesure l'écart entre p annoncé et fréquence observée
    (calibration ; 0 = parfait) ; la **résolution**, la capacité à séparer les issues de la moyenne
    (plus haut = mieux) ; l'**incertitude**, ō(1 − ō), ne dépend que des questions posées. Un bon Brier
    obtenu par des questions faciles se voit dans une incertitude basse et une résolution nulle."""
    if not paires:return None
    n=len(paires);ob=sum(o for _,o in paires)/n;classes=defaultdict(list)
    for p,o in paires:classes[min(9,int(p*10))].append((p,o))
    rel=sum(len(v)*(sum(p for p,_ in v)/len(v)-sum(o for _,o in v)/len(v))**2 for v in classes.values())/n
    res=sum(len(v)*(sum(o for _,o in v)/len(v)-ob)**2 for v in classes.values())/n
    unc=ob*(1-ob);bs=sum((p-o)**2 for p,o in paires)/n
    return {'questions':n,'brier':bs,'fiabilite':rel,'resolution':res,'incertitude':unc,'variance_intra_classe':bs-(rel-res+unc),
            'lecture':('indicatif : moins de 50 questions, chaque classe compte trop peu de cas' if n<50 else
                       'fiabilité 0 = calibré ; résolution haute = discrimine ; incertitude = difficulté de l’ensemble posé')}


def v4_bras(eligible,champ,filtre):
    """0.7.8. V4 lu contre un bras donné (ici le comparateur externe), sur toutes les questions éligibles
    ou sur les seules discriminantes contre ce bras ; second rapport, jamais filtre du premier."""
    v=[x for x in eligible if x.get(champ) is not None and (filtre is None or x.get(filtre))]
    if not v:return None
    r={k:w for k,w in v4_statut(differentiel(v,champ)).items() if k!='regle'};r['questions']=len(v);return r


def v4_statut(dm):
    """0.7.7 (décisions 2 et 3). V4 se juge sur le différentiel **absolu** par épisode d̄ = Brier − Brier
    de référence : atteint si d̄ ≤ −v4_gain_abs, si le test exact (v4_test) rejette « aucune amélioration »
    au seuil v4_alpha, et si l'effectif atteint **à la fois** le plancher v4_n et l'effectif requis par la
    dispersion observée, n = ⌈((z₁₋α/₂ + z_puissance) · σ̂(d) / v4_gain_abs)²⌉. Le plancher empêche qu'un σ̂
    sous-estimé sur trois épisodes déclare le jalon atteint ; la cible se révise à chaque `scorer`."""
    from statistics import NormalDist
    z=NormalDist().inv_cdf(1-P['v4_alpha']/2)+NormalDist().inv_cdf(P['v4_puissance'])
    regle=(f"d̄ ≤ −{P['v4_gain_abs']} ; test {P['v4_test']} p < {P['v4_alpha']} ; épisodes ≥ max({P['v4_n']}, "
           f"⌈({z:.2f}·σ̂/{P['v4_gain_abs']})²⌉)")
    if dm is None:return {'statut':'non encore évalué','episodes':0,'effectif_requis':None,'regle':regle}
    sd=dm.get('sigma_d');req=None if sd is None else math.ceil((z*sd/P['v4_gain_abs'])**2)
    t=dm['test_signe' if P['v4_test']=='signe' else 'test_wilcoxon']
    p_=None if t is None else t['p_amelioration']
    cible=None if req is None else max(P['v4_n'],req)
    ic=None if dm.get('erreur_type') is None else [dm['d_moyen']-1.96*dm['erreur_type'],dm['d_moyen']+1.96*dm['erreur_type']]
    if cible is None or dm['episodes']<cible:st='non encore évalué'
    elif dm['d_moyen']<=-P['v4_gain_abs'] and p_ is not None and p_<P['v4_alpha']:st='jalon interne atteint — validation externe non établie'
    else:st='jalon interne non atteint'
    # 0.7.12 (audit V34, D4) : seconde lecture, séquentielle — l'e-processus de H0 « gain < v4_gain_abs » a-t-il
    # franchi 1/v4_alpha à un épisode quelconque ? Valide malgré les relectures du journal. Elle ne remplace
    # pas le statut (règle de 0.7.7, décision d'auteur) : elle se publie à côté.
    eg=dm.get('e_gain_v4')
    seq=None if eg is None else {'e_valeur':eg['e_valeur'],'e_max':eg['e_max'],'seuil':eg['seuil'],'franchi_a_l_episode':eg['franchi_a_l_episode'],
        'lecture':('franchi : gain ≥ v4_gain_abs établi à tout instant, sous indépendance des épisodes' if eg['franchi_a_l_episode']
                   else 'non franchi : le journal peut être relu à chaque épisode sans gonfler α')}
    # 0.7.23 (décision d'auteur, validation.md §11) : deux conclusions, deux tests primaires. « Gain » : l'e-processus
    # e_gain_v4 franchit v4_e_seuil_primaire. « Aucun apport » : équivalence (TOST, deux tests unilatéraux à
    # v4_alpha, soit l'intervalle à 1 − 2α de d̄ dans ±v4_equivalence_delta), lue une seule fois, à l'effectif
    # d'équivalence déclaré. Barrière : si l'autocorrélation d'ordre 1 des épisodes dépasse v4_autocorrelation_max,
    # aucune des deux conclusions n'est émise. Le test du signe et le statut ci-dessus restent publiés, descriptifs.
    # 0.7.29 (§11.13) : l'énoncé négatif est une **non-supériorité** unilatérale (« pas d'apport supérieur à δ »),
    # non une équivalence bilatérale : un alphabet nuisible n'y devient plus « non établi ». z = z₁₋α + z_puissance.
    zt=NormalDist().inv_cdf(1-P['v4_alpha'])+NormalDist().inv_cdf(P['v4_puissance'])
    # 0.7.24 : l'effectif d'équivalence se fixe une fois (après 20 épisodes, sur σ̂), puis se déclare dans
    # v4_effectif_equivalence ; tant qu'il vaut 0, il est provisoire et aucune équivalence ne se conclut.
    de=P['v4_equivalence_delta'];fixe=P['v4_effectif_equivalence']>0
    n_eq=P['v4_effectif_equivalence'] if fixe else None if sd is None else max(P['v4_n'],math.ceil((zt*sd/de)**2))
    r1=dm.get('autocorrelation_1');barr=r1 is not None and r1>P['v4_autocorrelation_max']
    se_=dm.get('erreur_type');z1=NormalDist().inv_cdf(1-P['v4_alpha'])
    ic_eq=None if se_ is None else [dm['d_moyen']-z1*se_,dm['d_moyen']+z1*se_]
    # 0.7.24 : aucune conclusion avant v4_n épisodes (la barrière d'indépendance a besoin d'épisodes) ; gain et
    # équivalence à la fois : contradiction publiée, aucune conclusion ; l'équivalence exige un effectif fixé.
    mur=dm['episodes']>=P['v4_n']
    gain_ok=mur and eg is not None and eg['e_max']>=P['v4_e_seuil_primaire']
    # Non-supériorité : borne basse unilatérale de d̄ (Brier − référence) au-dessus de −δ, soit un gain < δ établi.
    # Nuisance, énoncé séparé : la même borne au-dessus de +δ, soit une dégradation de plus de δ établie.
    eq_ok=mur and fixe and ic_eq is not None and dm['episodes']>=n_eq and ic_eq[0]>-de
    nuis=mur and fixe and ic_eq is not None and dm['episodes']>=n_eq and ic_eq[0]>de
    if not mur:concl='non encore évalué : moins de '+str(P['v4_n'])+' épisodes'
    elif barr:concl='aucune conclusion : épisodes autocorrélés (ρ̂₁ > '+str(P['v4_autocorrelation_max'])+'), espacer les épisodes'
    # 0.7.25 : libellés qui nomment l'hypothèse testée et le seuil (e_gain_v4 teste H0 « gain < v4_gain_abs »).
    elif gain_ok and eq_ok:concl='aucune conclusion : gain ≥ '+str(P['v4_gain_abs'])+' et équivalence à ±'+str(de)+' à la fois (contradiction publiée)'
    elif gain_ok:concl='gain d’au moins '+str(P['v4_gain_abs'])+' établi (H0 « gain < '+str(P['v4_gain_abs'])+' » rejetée, e ≥ '+str(P['v4_e_seuil_primaire'])+')'
    elif nuis:concl='dégradation de plus de '+str(de)+' établie (nuisance) ; énoncé séparé, publié comme tel'
    elif eq_ok:concl='pas d’apport supérieur à '+str(de)+' (non-supériorité) ; un apport plus petit n’est pas exclu'
    elif fixe and dm['episodes']>=n_eq:concl='non établi : ni gain, ni équivalence à l’effectif d’équivalence (arrêt)'
    elif not fixe:concl='non encore évalué : effectif d’équivalence non fixé (provisoire '+str(n_eq)+')'
    else:concl='non encore évalué'
    decision={'conclusion':concl,'nuisance':nuis,'gain_e_max':None if eg is None else eg['e_max'],'equivalence_intervalle':ic_eq,
              'effectif_equivalence':n_eq,'effectif_equivalence_fixe':fixe,'autocorrelation_1':r1,'barriere':barr,
              'regle':(f"gain : e_gain_v4 ≥ {P['v4_e_seuil_primaire']} ; pas d'apport > {de} : borne basse unilatérale à {1-P['v4_alpha']:.0%} de d̄ > −{de} (nuisance : > +{de}), "
                       f"lu à épisodes ≥ max({P['v4_n']}, ⌈({zt:.2f}·σ̂/{de})²⌉) ; barrière ρ̂₁ > {P['v4_autocorrelation_max']} ; test du signe descriptif")}
    return {'statut':st,'episodes':dm['episodes'],'effectif_requis':req,'effectif_cible':cible,'d_moyen':dm['d_moyen'],
            'intervalle_95_approche':ic,'p_test':p_,'sigma_d':sd,'regle':regle,'sequentiel':seq,'decision':decision,
            'sequence_confiance':dm.get('sequence_confiance')}


def dossier_publie(x):
    """0.7.4 (décision 1) : le dossier de lecture d'une prévision est scellé dans le calcul figé et
    publié (adresse https d'un dépôt daté) au plus tard à la date d'information."""
    c=x.get('calcul');pd=x.get('preuve_dossier')
    if not isinstance(c,dict) or not isinstance(pd,dict):return False
    sd=(c.get('dossier') or {}).get('sceau');di=(c.get('contexte') or {}).get('date_information')
    return (sd is not None and sd==pd.get('sceau') and di is not None and jour(pd['date'])<=jour(di)
            and re.match(r'https://\S+',str(pd.get('source',''))) is not None)


def vue_exterieure_de(x):
    """0.7.40. Taux de base du dossier pour une prévision : le champ du journal, sinon celui du calcul figé (lignes 0.7.39 et
    antérieures, où il n'était pas recopié ; le calcul figé fait partie de l'empreinte de la prévision)."""
    v=x.get('vue_exterieure')
    if v is None and isinstance(x.get('calcul'),dict):v=((x['calcul'].get('vue_exterieure') or {}).get('declaree'))
    return v if type(v) in (int,float) else None


def robustesse_classe(v4,v4_alt):
    """0.7.43 (option a). V4 décide contre la classe retenue ; on publie à côté le même calcul contre la classe
    alternative. Deux statuts différents : le verdict dépend du choix de la classe, et cela s'écrit."""
    if v4 is None or v4_alt is None or P['v4_reference']!='vue_exterieure':return None
    return {'statut_classe_retenue':v4.get('statut'),'statut_classe_alternative':v4_alt.get('statut'),
            'concordant':v4.get('statut')==v4_alt.get('statut'),'questions_alternative':v4_alt.get('questions'),
            'lecture':'V4 décide sur la classe retenue (scellée) ; si les deux statuts divergent, le verdict dépend du choix de la classe : à publier tel quel'}


def vue_alternative_de(x):
    """0.7.43. Taux de la classe alternative : champ du journal, sinon calcul figé."""
    v=x.get('vue_exterieure_alternative')
    if v is None and isinstance(x.get('calcul'),dict):v=((x['calcul'].get('vue_exterieure') or {}).get('alternative'))
    return v if type(v) in (int,float) else None


def bras_vue_exterieure(units):
    """0.7.40 (test T6). Bras « vue extérieure » sur toutes les questions du moteur résolues, hors V4 compris (descriptif) :
    Brier moyen du taux de base déclaré contre celui du moteur et du moteur sans cartes, sur les mêmes questions. Ce
    bras n'entre pas dans la décision V4, dont la référence est fixée d'avance (§11) ; il est publié à côté."""
    u=[x for x in units if x['origine']=='moteur' and x.get('brier_vue_exterieure') is not None]
    if not u:return None
    m=lambda k:sum(x[k] for x in u)/len(u) if all(x.get(k) is not None for x in u) else None
    ua=[x for x in u if x.get('brier_vue_alternative') is not None]
    return {'questions':len(u),'brier_vue_exterieure':m('brier_vue_exterieure'),'brier_moteur':m('brier'),'brier_sans_cartes':m('brier_sans_cartes'),
            'questions_avec_alternative':len(ua),
            'brier_vue_alternative':sum(x['brier_vue_alternative'] for x in ua)/len(ua) if ua else None,
            'brier_moteur_sur_alternative':sum(x['brier'] for x in ua)/len(ua) if ua else None,
            'lecture':'descriptif, hors décision V4 : le taux de base déclaré avant le calcul, scoré comme un bras'}


def bilan_regressif(units):
    """0.7.45. Bilan des tests régressifs à l'aveugle, séparé de V4 : Brier moyen par bras, sur les lignes non rejouées.
    Il ne valide rien (pas de prépublication) ; il mesure le fonctionnement et donne une première idée des écarts."""
    u=[x for x in units if x.get('mode_test')=='regressif' and x['origine']=='moteur']
    if not u:return None
    a=[x for x in u if not x['rejeu']]
    m=lambda k:(lambda v:None if not v else sum(v)/len(v))([x[k] for x in a if x.get(k) is not None])
    return {'questions':len(u),'rejeux':len(u)-len(a),'aveugles':len(a),
            'brier':{'moteur':m('brier'),'sans_cartes':m('brier_sans_cartes'),'jugement':m('brier_jugement'),
                     'vue_exterieure':m('brier_vue_exterieure'),'classe_alternative':m('brier_vue_alternative')},
            'lecture':'tests régressifs à l’aveugle, hors V4 : fonctionnement et ordres de grandeur, jamais une validation'}


def qualite_resolutions(scores):
    """0.7.44. Comment les issues ont été tranchées : par un document (positif) ou par absence de trace, avec la source
    du dossier ou une autre. Une résolution par absence ou hors source n'est pas fausse ; elle est plus fragile, et se compte."""
    r=[x for x in scores.values() if x.get('issue') is not None]
    ren=[x for x in r if 'mode_resolution' in x]
    return {'resolues':len(r),'renseignees':len(ren),'non_renseignees':len(r)-len(ren),
            'positives':sum(1 for x in ren if x['mode_resolution']=='positif'),
            'par_absence':sum(1 for x in ren if x['mode_resolution']=='absence'),
            'hors_source_du_dossier':sum(1 for x in ren if not x['source_conforme']),
            'ids_fragiles':sorted(x['id'] for x in ren if x['mode_resolution']=='absence' or not x['source_conforme']),
            'lecture':'une issue établie par absence de trace, ou par une autre source que celle du dossier, est plus fragile ; '
                      'non renseignées : lignes antérieures à 0.7.44'}


def episodes_suspects(prev):
    """0.7.44 (T6 et P-0001 : même question, même dyade, même fenêtre, deux identifiants d'épisode). Deux prévisions sur
    le même événement, à fenêtres qui se chevauchent, sous des épisodes différents, compteraient en V4 comme deux
    épisodes indépendants. Signalé, non corrigé : seul l'analyste sait si ce sont deux épisodes."""
    xs=[x for x in prev.values() if x.get('origine','moteur')=='moteur' and x.get('evenement') and x.get('echeance')]
    out=[]
    for i,a in enumerate(xs):
        for b in xs[i+1:]:
            try:same=evenement_lire(a['evenement'])==evenement_lire(b['evenement'])
            except ValueError:same=a['evenement']==b['evenement']
            if same and a.get('episode_id')!=b.get('episode_id') and jour(a['date'])<jour(b['echeance']) and jour(b['date'])<jour(a['echeance']):
                out.append({'ids':sorted([a['id'],b['id']]),'evenement':a['evenement'],'episodes':sorted([str(a.get('episode_id')),str(b.get('episode_id'))])})
    return out


def score_result(data):
    prev,scores,partitions=valider_journal(data);units=[];used=set();unresolved=0;missing=0
    # 0.6.11 : abstentions (calcul « non estimé ») comptées à part. Elles n'ont pas de Brier et ne valent
    # pas une prédiction parfaite ; mais un outil qui s'abstient sur les questions difficiles et répond
    # aux faciles améliorerait son score sans rien prévoir : leur nombre et leurs issues se publient.
    abst=[x for x in prev.values() if x.get('probabilite') is None]
    ab_res=[x for x in abst if x['id'] in scores and scores[x['id']]['issue'] is not None]
    prev={k:v for k,v in prev.items() if v.get('probabilite') is not None}
    groups=list(partitions.values())+[[x] for x in prev.values() if not x.get('partition')]
    for items in groups:
        if any(x['id'] not in scores for x in items):missing+=1;continue
        if any(scores[x['id']]['issue'] is None for x in items):unresolved+=1;continue
        # 0.6.13 (audit 0.6.12, M3) : le Brier d'une partition (somme sur les issues, de 0 à 2) était
        # moyenné avec des Brier binaires (de 0 à 1) : une partition 0,5/0,5 valait 0,50, la binaire
        # équivalente 0,25. Divisé par 2, il revient sur l'échelle binaire (identique pour deux issues).
        ech=.5 if len(items)>1 else 1.
        b=ech*sum((x['probabilite']-scores[x['id']]['issue'])**2 for x in items)
        origine=items[0].get('origine','moteur')
        bb=None if any(x.get('frequence_de_base') is None for x in items) else ech*sum((x['frequence_de_base']-scores[x['id']]['issue'])**2 for x in items)
        bsc=None if any(x.get('p_sans_cartes') is None for x in items) else ech*sum((x['p_sans_cartes']-scores[x['id']]['issue'])**2 for x in items)
        bis=None if any(x.get('p_inertie_strate') is None for x in items) else ech*sum((x['p_inertie_strate']-scores[x['id']]['issue'])**2 for x in items)
        bj=None if any(x.get('probabilite_jugement') is None for x in items) else ech*sum((x['probabilite_jugement']-scores[x['id']]['issue'])**2 for x in items)
        bve=None if any(vue_exterieure_de(x) is None for x in items) else ech*sum((vue_exterieure_de(x)-scores[x['id']]['issue'])**2 for x in items)
        bva=None if any(vue_alternative_de(x) is None for x in items) else ech*sum((vue_alternative_de(x)-scores[x['id']]['issue'])**2 for x in items)
        ref=None if len(items)>1 else items[0].get('frequence_de_base') if items[0].get('frequence_de_base') is not None else items[0].get('p_sans_cartes')
        # 0.6.14 : éligibilité V4 = calcul figé joint, empreintes, résolution vérifiée et prépublication
        # **publique** (adresse https d'un dépôt horodaté par un tiers : release, commit, archive web).
        # Une preuve qui ne pointe que vers elle-même ne prouve ni l'origine ni la date.
        verified=all(x.get('preuve_prepublication') is not None and x.get('empreintes') is not None and x.get('resolution_verifiee')
                     and isinstance(x.get('calcul'),dict)
                     and re.match(r'https://\S+',str(x['preuve_prepublication'].get('source',''))) is not None for x in items)
        # 0.7.4 (décision 1) : à compter de v4_dossier_depuis, une prévision du moteur n'est éligible que si
        # son dossier de lecture porte un sceau publié (https) au plus tard à la date d'information, et que
        # ce sceau est celui du calcul figé. Prospectif : les prévisions antérieures ne sont pas invalidées.
        verified=verified and all(dossier_publie(x) for x in items if origine=='moteur' and jour(x['date'])>=jour(P['v4_dossier_depuis']))
        regressif=any(x.get('mode_test')=='regressif' for x in items)
        excluded=origine=='jugement' or any(x['rejeu'] or x['fictif'] for x in items) or not verified or regressif
        units.append({'ids':[x['id'] for x in items],'episode_id':items[0]['episode_id'],'origine':origine,'rejeu':any(x['rejeu'] for x in items),
                      'date':min(x['date'] for x in items),
                      'brier':b,'brier_base':bb,'brier_sans_cartes':bsc,'brier_inertie_strate':bis,'brier_jugement':bj,'brier_vue_exterieure':bve,'brier_vue_alternative':bva,
                      **pertes_log(items,scores),
                      'discriminant':None if origine=='jugement' else discriminant(items),
                      **brier_comparateur(items,scores,ech,origine),
                      'difficulte':None if ref is None else .5-abs(ref-.5),'reference_difficulte':ref,
                      'hors_V4':excluded,'partition':bool(items[0].get('partition')),'mode_test':items[0].get('mode_test'),
                      'rho':'jugement' if origine=='jugement' else max(x['rho'] for x in items),
                      'procedure':items[0].get('procedure') if origine=='jugement' else None,
                      'cartes':[] if origine=='jugement' else sorted({x['evenement'].split('@')[0] for x in items}),
                      'strate':'jugement' if origine=='jugement' else items[0]['evenement'].split('@')[1].split()[0] if '@' in items[0]['evenement'] and not items[0].get('partition') else 'partition',
                      'incertitude_annoncee':sum(x['probabilite']*(1-x['probabilite']) for x in items)})
    eligible=[x for x in units if not x['hors_V4']];episodes=defaultdict(list)
    for x in eligible:
        if x['brier_base'] is not None:episodes[x['episode_id']].append(x)
    # Equal weight per episode. Ten related forecasts cannot manufacture ten independent cases.
    b=sum(sum(x['brier'] for x in v)/len(v) for v in episodes.values())/len(episodes) if episodes else None
    bb=sum(sum(x['brier_base'] for x in v)/len(v) for v in episodes.values())/len(episodes) if episodes else None
    gain=1-b/bb if bb is not None and bb>0 else None
    # 0.7.5 : le gain est un « skill score » (Gneiting et Raftery 2007, §2.3) ; il s'accompagne du
    # différentiel par épisode contre la référence et de ses tests exacts.
    # 0.7.8 : `v4_reference` choisit le bras contre lequel le jalon se lit (inertie par défaut : inchangé).
    # 0.7.41 (décision d'auteur, prise avant le premier épisode prospectif) : référence par défaut = la vue extérieure du
    # dossier, taux de base déclaré avant le calcul. Plus exigeant que l'inertie du moteur (T6 : 0,0004 contre 0,0025).
    champ_ref={'inertie':'brier_base','jugement':'brier_jugement','comparateur_externe':'brier_comparateur',
               'vue_exterieure':'brier_vue_exterieure'}[P['v4_reference']]
    if champ_ref!='brier_base':
        episodes=defaultdict(list)
        for x in eligible:
            if x[champ_ref] is not None:episodes[x['episode_id']].append(x)
    dv4=differentiel([x for x in eligible if x[champ_ref] is not None],champ_ref)
    v4=v4_statut(dv4);v4['reference']=P['v4_reference']
    status=v4['statut']
    # 0.7.7 (décision 6) : second rapport sur les seules questions discriminantes, jamais un filtre du premier.
    disc=[x for x in eligible if x.get('discriminant')]
    dv4d=differentiel([x for x in disc if x[champ_ref] is not None],champ_ref)
    v4_discriminant={'questions':len(disc),'part_des_eligibles':len(disc)/len(eligible) if eligible else None,
                     'differentiel':dv4d,**{k:v for k,v in v4_statut(dv4d).items() if k!='regle'}}
    by={}
    for field in ('rho','strate'):
        groups=defaultdict(list)
        for x in eligible:groups[x[field]].append(x)
        by[field]={k:{'questions':len(v),'episodes':len({x['episode_id'] for x in v}),'brier':sum(x['brier'] for x in v)/len(v)} for k,v in groups.items()}
    bins=defaultdict(list)
    ok_ids={i for u in eligible if not u['partition'] for i in u['ids']}
    for i in ok_ids:
        x=prev[i];bins[min(9,int(x['probabilite']*10))].append((x['probabilite'],scores[i]['issue']))
    calibration={f'{k*10}–{k*10+10}':{'n':len(v),'p_moyenne':sum(x[0] for x in v)/len(v),'frequence':sum(x[1] for x in v)/len(v)} for k,v in sorted(bins.items())}
    # 0.7.0 : décomposition de Murphy, sur les binaires éligibles (V4) et, à titre descriptif, sur toutes
    # les binaires résolues du moteur (rejeux et fictifs compris, jamais une preuve).
    tous={i for u in units if not u['partition'] and u['origine']=='moteur' for i in u['ids']}
    decomposition={'eligibles':murphy([(prev[i]['probabilite'],scores[i]['issue']) for i in sorted(ok_ids)]),
                   'toutes_moteur':murphy([(prev[i]['probabilite'],scores[i]['issue']) for i in sorted(tous)])}
    abstentions={'questions':len(abst),'resolues':len(ab_res),'issues_realisees':sum(scores[x['id']]['issue'] for x in ab_res),
                 'part_des_questions':len(abst)/(len(abst)+len(prev)) if abst or prev else None,
                 'motifs':sorted({x['calcul'].get('non_estime_motif') or 'référence manquante' for x in abst}),
                 'lecture':'une abstention n’a pas de score ; un Brier calculé sur les seules questions chiffrées ne dit rien de celles que l’outil a refusées'} if abst else None
    # 0.7.23 (validation.md §11) : couverture. Le bras alphabet est scoré sur toutes les questions binaires soumises et
    # résolues ; une abstention reçoit la fréquence de base déclarée (règle fixée d'avance : sans cartes, p₀ = f).
    # Une abstention sans fréquence de base reste « sans repli » et rend la couverture incomplète.
    bin_=[(x['probabilite'],scores[x['id']]['issue']) for x in prev.values() if not x.get('partition') and x['id'] in scores and scores[x['id']]['issue'] is not None]
    rep=[(x.get('frequence_de_base'),scores[x['id']]['issue']) for x in ab_res if not x.get('partition')]
    rep_ok=[(q,o) for q,o in rep if q is not None];tout=bin_+rep_ok
    couverture={'binaires_resolues_chiffrees':len(bin_),'abstentions_resolues':len(rep),'repli_applique':len(rep_ok),
                'sans_repli':len(rep)-len(rep_ok),'taux_de_repli':len(rep_ok)/len(tout) if tout else None,
                'brier_chiffrees':sum((q-o)**2 for q,o in bin_)/len(bin_) if bin_ else None,
                'brier_avec_repli':sum((q-o)**2 for q,o in tout)/len(tout) if tout else None,
                'complete':len(rep)==len(rep_ok),
                'regle':'abstention → frequence_de_base ; score sur toutes les binaires soumises et résolues'}
    # 0.7.25 (validation.md §11.9) : d̄ primaire **avec repli**. Une abstention résolue, non rejouée, non fictive et
    # prépubliée (https) entre dans le différentiel : le bras alphabet y reçoit la fréquence de base ; l'inertie aussi
    # (sans cartes, p₀ = f), d'où d = 0 contre l'inertie ; contre le comparateur externe, son propre Brier.
    pseudo=[]
    for x in ab_res:
        f_=x.get('frequence_de_base');o=scores[x['id']]['issue'];pp=x.get('preuve_prepublication') or {}
        if f_ is None or x.get('partition') or x.get('rejeu') or x.get('fictif') or not re.match(r'https://\S+',str(pp.get('source',''))):continue
        ce=x.get('comparateur_externe');bce=None
        if isinstance(ce,dict) and ce.get('probabilite') is not None and not comparateur_contamine(ce):bce=(ce['probabilite']-o)**2
        ve_=vue_exterieure_de(x)
        pseudo.append({'episode_id':x['episode_id'],'date':x['date'],'brier':(f_-o)**2,'brier_base':(f_-o)**2,
                       'brier_comparateur':bce,'brier_jugement':None,'brier_vue_exterieure':None if ve_ is None else (ve_-o)**2,
                       'brier_vue_alternative':None if vue_alternative_de(x) is None else (vue_alternative_de(x)-o)**2})
    bin_el=[x for x in eligible if not x['partition']]
    dv4r=differentiel([x for x in bin_el+pseudo if x.get(champ_ref) is not None],champ_ref)
    couverture['v4_avec_repli']={'abstentions_admises':len(pseudo),**v4_statut(dv4r),
                                 'lecture':'d̄ primaire (§11.9) : binaires éligibles et abstentions avec repli ; v4 reste publié sur les seules chiffrées'}
    return {'questions_resolues':len(units),'questions_eligibles':len(eligible),'abstentions':abstentions,
            'resolutions':qualite_resolutions(scores),'registre_regressif':bilan_regressif(units),'episodes_suspects':episodes_suspects({**prev,**{x['id']:x for x in abst}}),
            'couverture':couverture,
            'incertitude_annoncee_moyenne':sum(x['incertitude_annoncee'] for x in units)/len(units) if units else None,
            'apport_des_cartes':apport_cartes([x for x in units if x['origine']=='moteur']),
            'jugements':jugements(units),
            'moteur_contre_jugement':moteur_contre_jugement([x for x in units if x['origine']=='moteur']),
            'difficulte':difficulte(units),'questions_hors_V4':len(units)-len(eligible),
            'sans_score':missing,'non_resolues':unresolved,'episodes_comparables':len(episodes),'brier_par_episode':b,
            'brier_base_par_episode':bb,'gain':gain,'gain_par_episode':dv4,'v4':v4,'v4_discriminant':v4_discriminant,
            'comparateur_externe':comparateur_externe([x for x in units if x['origine']=='moteur']),
            'v4_comparateur':v4_bras(eligible,'brier_comparateur',None),
            'v4_inertie_strate':v4_bras(eligible,'brier_inertie_strate',None),
            'v4_vue_exterieure':v4_bras(eligible,'brier_vue_exterieure',None),
            'v4_vue_alternative':v4_bras(eligible,'brier_vue_alternative',None),
            'v4_robustesse_classe':robustesse_classe(v4,v4_bras(eligible,'brier_vue_alternative',None)),
            'vue_exterieure':bras_vue_exterieure(units),
            'v4_comparateur_discriminant':v4_bras(eligible,'brier_comparateur','discriminant_comparateur'),'statut':status,'par_groupe':by,'calibration':calibration,
            'decomposition_murphy':decomposition,'details':units,
            'limites':['Prépublication déclarée : authenticité à vérifier humainement.',
                       '50 épisodes et 10 % de gain constituent un jalon interne, pas une preuve statistique : lire avec gain_par_episode (tests exacts, sigma_d).',
                       'Un skill score (gain) n’est pas une règle propre en général : le Brier l’est, le rapport de deux Brier non (Gneiting et Raftery 2007).',
                       'p(1-p) décrit la confiance annoncée ; une valeur faible ne démontre pas que le test est inutile.']}


COLONNES_CSV=('ids','episode_id','origine','rho','strate','partition','hors_V4','brier','brier_base','brier_sans_cartes',
              'brier_jugement','brier_comparateur','brier_vue_exterieure','brier_vue_alternative','comparateur_contamine','log','log_sans_cartes','difficulte','reference_difficulte','incertitude_annoncee')


def scorer(path, csv_=False):
    r=score_result(charger(path))
    if csv_:
        # 0.7.1 : une ligne par question résolue, pour suivre la calibration dans un tableur ; séparateur « ; »,
        # décimale « . », abstentions et décomposition de Murphy dans le JSON.
        import csv
        out=io.StringIO();w=csv.writer(out,delimiter=';',lineterminator='\n');w.writerow(COLONNES_CSV)
        for u in r['details']:
            w.writerow(['+'.join(u['ids']) if k=='ids' else ('' if u.get(k) is None else u.get(k)) for k in COLONNES_CSV])
        return out.getvalue().rstrip('\n')
    return json.dumps(r,ensure_ascii=False,indent=2,allow_nan=False)


# ───────────────────────── intégrité et paramètres ─────────────────────────

def parametres_markdown():
    rows=['| Paramètre | Valeur |','|---|---|']
    def visit(prefix,x):
        if isinstance(x,dict):
            for k,v in x.items():visit(prefix+'.'+k if prefix else k,v)
        else:rows.append('| `'+prefix+'` | `'+json.dumps(x,ensure_ascii=False,separators=(',',':'))+'` |')
    visit('',P)
    return '\n'.join(rows)


# Renvois « fichier.md §N » attendus → mot qui doit figurer dans le titre de la section visée.
# L'audit vérifie l'existence ET la pertinence ; un renvoi absent de cette table est signalé.
RENVOIS = {
    ('base-de-cas.md','4'):'sans événement', ('apports-theoriques.md','27'):'Grossetti lu', ('apports-theoriques.md','28'):'Simmel', ('apports-theoriques.md','16.3'):'attend', ('validation.md','11'):'Règles de décision', ('apports-theoriques.md','29'):'Deux relectures', ('validation.md','12'):'Attribution', ('apports-theoriques.md','30'):'Agent-Causality', ('validation.md','13'):'Audit pratique', ('validation.md','11.10'):'Cinquième relecture', ('apports-theoriques.md','31'):'DeepSeek', ('apports-theoriques.md','32'):'Druckman', ('graphe.md','3.1'):'Unité de comptage', ('validation.md','14'):'Registre des tests', ('validation.md','15'):'Vue extérieure', ('validation.md','16'):'Premier test', ('validation.md','17'):'Deuxième série', ('validation.md','18'):'Test T6', ('validation.md','19'):'référence de V4', ('validation.md','20'):'Test T7', ('validation.md','21'):'Classe alternative', ('validation.md','22'):'Sources', ('validation.md','23'):'Test FR-RU', ('validation.md','24'):'deux sources', ('validation.md','25'):'Tests du codeur', ('validation.md','26'):'Fuites temporelles', ('validation.md','27'):'levée de L7', ('validation.md','28'):'Alignement avec le bot', ('validation.md','29'):'Bras exploratoire', ('validation.md','30'):'intensité', ('validation.md','31'):'Fait de série', ('validation.md','32'):'Équivalents de données', ('validation.md','33'):'Lecture causale', ('dynamiques.md','0'):'Lecture des fiches', ('apports-theoriques.md','34'):'Vue extérieure', ('apports-theoriques.md','33'):'Open Science', ('validation.md','11.9'):'Quatrième relecture',
    ('antagonismes.md','3'):'incompatibilités', ('apports-theoriques.md','4'):'attend', ('apports-theoriques.md','7'):'Deux apports', ('apports-theoriques.md','8'):'Intuition Machine', ('antagonismes.md','4'):'Tensions',
    ('antagonismes.md','4bis'):'Inclusions', ('antagonismes.md','6'):'même objet',
    ('base-de-cas.md','2'):'Fiche', ('base-de-cas.md','3'):'Coder', ('base-de-cas.md','5'):'Partage',
    ('constitution.md','2'):'principes', ('constitution.md','3'):'risque', ('constitution.md','4'):'couches',
    ('constitution.md','5'):"n'est pas", ('constitution.md','6'):'Données personnelles', ('equivalences.md','2'):'Statuts', ('feuille-de-route.md','5.1'):'Strate 7', ('feuille-de-route.md','4'):'Premiers cas', ('feuille-de-route.md','7'):'Code différé', ('grammaire.md','2'):'Syntaxe', ('equivalences.md','3'):'Bilan',
    ('grammaire.md','4'):'liaisons', ('grammaire.md','5'):'Positions', ('grammaire.md','7'):'bonne formation',
    ('graphe.md','2'):'priori', ('graphe.md','2.1'):'Sources', ('graphe.md','2.2'):'Fréquence',
    ('graphe.md','2.3'):'Combinaison', ('graphe.md','3'):'homologues',
    ('protocole.md','H'):'Paramètres', ('simulation.md','1'):'Modèle de sortie', ('simulation.md','4'):'Rédiger', ('simulation.md','6'):'autres cas', ('simulation.md','2'):'remplissage',
    ('strates.md','2'):'Fiches', ('strates.md','3'):'taxonomie', ('strates.md','4'):'rattachement',
    ('validation.md','1'):'Journal des prévisions', ('validation.md','4'):'Diagnostic',
    ('validation.md','5'):'calibration', ('validation.md','6'):'lacunes', ('validation.md','7'):'santé', ('validation.md','8'):'aveugle',
    ('validation.md','9'):'Banc', ('simulation.md','7'):'État de travail', ('apports-theoriques.md','1'):'Règle',
    ('apports-theoriques.md','10'):'Cinq apports', ('apports-theoriques.md','11'):'manque', ('apports-theoriques.md','12'):'Capacité', ('apports-theoriques.md','13'):'Accord', ('apports-theoriques.md','14'):'rivaux', ('apports-theoriques.md','15'):'open-ontologies', ('apports-theoriques.md','16'):'V34', ('apports-theoriques.md','17'):'comparatif', ('simulation.md','3'):'Trajectoires', ('apports-theoriques.md','18'):'Unifier', ('apports-theoriques.md','19'):'Copley', ('apports-theoriques.md','20'):'Digital Consciousness Model', ('apports-theoriques.md','21'):'mathématiques expérimentales', ('apports-theoriques.md','22'):'Dix notes', ('apports-theoriques.md','23'):'Causalité', ('apports-theoriques.md','24'):'Causes des effets', ('apports-theoriques.md','25'):'Horizon', ('apports-theoriques.md','26'):'Contingence', ('graphe.md','5'):'Emprunt', ('validation.md','10'):'ne mesure pas', ('constitution.md','1'):'Ce qu', ('simulation.md','4'):'Rédiger', ('graphe.md','2.1'):'Sources', ('equivalences.md','4'):'Érosion', ('validation.md','8'):'aveugle', ('frequences-externes.md','2'):'six champs', ('graphe.md','3.4'):'Capacité', ('graphe.md','3.2'):'similarité', ('feuille-de-route.md','4'):'Premiers cas', ('feuille-de-route.md','7'):'Code différé', ('graphe.md','4'):'Révision', ('graphe.md','2.4'):'plusieurs pas', ('graphe.md','3.3'):'postule', ('feuille-de-route.md','1'):'Vue', ('base-de-cas.md','6'):'qualité', ('sources-france.md','5'):'Séries', ('sources-france.md','1'):'Règles',
}
RENVOI_RE = re.compile(r'`?([a-z\-]+\.md)`?\s*§\s*([0-9]+(?:\.[0-9]+)?(?:bis)?|[A-Z]\b)')


def titre_section(fichier, sec):
    path = RACINE/'SKILL.md' if fichier == 'SKILL.md' else RACINE/'references'/fichier
    if not path.is_file():
        return None
    texte_ = path.read_text(encoding='utf-8')
    niveau = '###' if '.' in sec else '##'
    m = re.search(r'^' + niveau + r' (?:§)?' + re.escape(sec) + r'(?:\.|\s·|\s|$)(.*)$', texte_, re.M)
    return m.group(1).strip() if m else None


def erreurs_renvois(chemins):
    err = []
    for path in chemins:
        for fic, sec in RENVOI_RE.findall(path.read_text(encoding='utf-8')):
            t = titre_section(fic, sec)
            if t is None:
                err.append(f'{path.name} : renvoi {fic} §{sec} vers une section absente')
            elif (fic, sec) not in RENVOIS:
                err.append(f'{path.name} : renvoi {fic} §{sec} non répertorié dans RENVOIS (vérifier, puis l’ajouter)')
            elif RENVOIS[(fic, sec)].lower() not in t.lower():
                err.append(f'{path.name} : renvoi {fic} §{sec} pointe vers « {t} », attendu « {RENVOIS[(fic, sec)]} »')
    return err


def erreurs_statuts(texte_skill=None):
    """M1 : la répartition des statuts publiée (Bilans, equivalences.md, protocole.md, SKILL.md) est
    recalculée à partir des 16 × NS cellules, jamais crue sur parole."""
    st=statuts();err=[];ordre=('Attesté','Documenté','Proposé','Vide','Hors domaine')
    tot={s:sum(v==s for v in st.values()) for s in ordre}
    for s in range(1,NS+1):
        f=RACINE/'references/equivalences'/f'strate-{s:02}.md';t=f.read_text(encoding='utf-8')
        m=re.search(r'Bilan : (\d+) Documenté, (\d+) Proposé, (\d+) Vide, (\d+) Hors domaine, (\d+) Attesté',t)
        vrai=[sum(v==x for (c,ss),v in st.items() if ss==s) for x in ('Documenté','Proposé','Vide','Hors domaine','Attesté')]
        if not m or [int(x) for x in m.groups()]!=vrai:err.append(f'{f.name} : Bilan ≠ cellules {vrai}')
    eq=(RACINE/'references/equivalences.md').read_text(encoding='utf-8')
    sec3=eq.split('## 3.',1)[1].split('\n## ',1)[0]
    lignes=re.findall(r'^\| (\d+) [^|]+\| (\d+) \| (\d+) \| (\d+) \| (\d+) \|$',sec3,re.M)
    if len(lignes)!=NS:err.append(f'equivalences.md §3 : tableau par strate incomplet ({NS} lignes, 4 statuts)')
    for s,d,pr,v,hd in lignes:
        vrai=[sum(x==y for (c,ss),x in st.items() if ss==int(s)) for y in ('Documenté','Proposé','Vide','Hors domaine')]
        if [int(d),int(pr),int(v),int(hd)]!=vrai:err.append(f'equivalences.md §3, strate {s} : {[d,pr,v,hd]} ≠ {vrai}')
    vides=sorted(f'{c}@{s}' for (c,s),x in st.items() if x=='Vide')
    m=re.search(r'Les (\d+) cases Vides \(carte : strates\) : (.+?)\. ',sec3,re.S)
    if m:
        lus=sorted(f'{carte_id(n)}@{int(x)}' for n,xs in re.findall(r'([A-ZÉÈ·][A-ZÉÈ· ]+?) \(([\d, ]+)\)',m.group(2)) for x in xs.split(','))
        if int(m.group(1))!=len(vides) or lus!=vides:err.append(f'equivalences.md §3 : liste des cases Vides ≠ cellules {vides}')
    else:err.append('equivalences.md §3 : liste des cases Vides absente')
    for f in ('references/equivalences.md','references/protocole.md'):
        for a,d,pr,v,hd in re.findall(r'(\d+) Attesté, (\d+) Documenté, (\d+) Proposé, (\d+) Vide, (\d+) Hors domaine',(RACINE/f).read_text(encoding='utf-8')):
            if [int(a),int(d),int(pr),int(v),int(hd)]!=[tot[x] for x in ordre]:err.append(f'{f} : bilan {a}/{d}/{pr}/{v}/{hd} ≠ {[tot[x] for x in ordre]}')
    # 0.6.13 (audit 0.6.12, M1) : le texte est coupé par un retour à la ligne, la regex ne trouvait rien
    # et le contrôle ne s'exécutait jamais. Blancs normalisés, trois nombres comparés, absence = erreur.
    sk=' '.join((texte_skill if texte_skill is not None else (RACINE/'SKILL.md').read_text(encoding='utf-8')).split())
    # 0.6.15 : les cinq statuts, comme protocole.md (audit Scira, anomalie 3).
    trouves=re.findall(r'(\d+) Attesté, (\d+) Documenté, (\d+) Proposé, (\d+) Vide, (\d+) Hors domaine',sk)
    if not trouves:err.append('SKILL.md : répartition « N Attesté, N Documenté, N Proposé, N Vide, N Hors domaine » introuvable')
    ordre=('Attesté','Documenté','Proposé','Vide','Hors domaine')
    for g in trouves:
        if [int(x) for x in g]!=[tot[k] for k in ordre]:
            err.append(f'SKILL.md : {"/".join(g)} ≠ cellules ({"/".join(str(tot[k]) for k in ordre)}, ordre {", ".join(ordre)})')
    return err


def erreurs_index():
    """M2 : `cartes-index.md` (chargé en premier) recoupe `cartes.md` : définition (première phrase),
    début de la structure mathématique, voisines A6."""
    def norm(x):return ' '.join(x.replace('**','').split()).strip().rstrip('.').strip()
    fiches={}
    for sec in re.split(r'^## ',(RACINE/'references/cartes.md').read_text(encoding='utf-8'),flags=re.M)[1:]:
        try:ab=carte_id(sec.split('\n',1)[0])
        except ValueError:continue
        d=re.search(r'\*\*Définition\*\*\s*:\s*(.+?)(?:\n\n|$)',sec,re.S);s_=re.search(r'\*\*Structure mathématique\*\*\s*:\s*(.+?)(?:\n\n|$)',sec,re.S)
        if d and s_:fiches[ab]=(norm(d.group(1)),norm(s_.group(1)))
    err=[];vus=set();V=voisines()
    for l in (RACINE/'references/cartes-index.md').read_text(encoding='utf-8').splitlines():
        c=[x.strip() for x in l.strip().strip('|').split('|')]
        if len(c)!=5 or c[0] in ('Carte','---'):continue
        ab=carte_id(c[0]);vus.add(ab)
        if ab not in fiches:err.append(f'cartes-index.md : {c[0]} sans fiche lisible');continue
        d,s_=fiches[ab]
        if not d.startswith(norm(c[2])):err.append(f'cartes-index.md : définition de {c[0]} ≠ cartes.md')
        if not s_.startswith(norm(c[3]).split('(')[0].strip()):err.append(f'cartes-index.md : structure de {c[0]} ≠ cartes.md')
        if {carte_id(x) for x in c[4].split(',')}!=V.get(ab):err.append(f'cartes-index.md : voisines de {c[0]} ≠ cartes.md')
    if vus!=set(NOMS):err.append(f'cartes-index.md : cartes manquantes {sorted(set(NOMS)-vus)}')
    return err


def erreurs_repetitions(chemins):
    """Texte recopié par erreur : paragraphe identique au précédent, ou segment « ; X ; X » répété
    dans une même ligne (défaut revenu deux fois dans le glossaire)."""
    err=[]
    for path in chemins:
        t=path.read_text(encoding='utf-8')
        pars=[' '.join(x.split()) for x in re.split(r'\n\s*\n',t) if x.strip()]
        for a,b in zip(pars,pars[1:]):
            if a==b and len(a)>40 and not a.startswith(('|','---','```')):err.append(f'{path.name} : paragraphe répété « {a[:50]}… »')
        for l in t.splitlines():
            seg=[x.strip(' |*') for x in re.split(r' ; |\|',l)]
            for a,b in zip(seg,seg[1:]):
                if a==b and len(a)>15:err.append(f'{path.name} : segment répété « {a[:50]} »')
    return err


def bilan(base_chemin=None, refs_chemin=None, journal_chemin=None):
    """Position mesurée sur la feuille de route (`feuille-de-route.md`) : seules les étapes
    mesurables sont calculées ; les décisions d'auteur restent déclarées dans le document."""
    out=[f'Bilan de la feuille de route · version {P["version"]}']
    st=statuts();par={s:sum(st.get((ab,s)) in ('Attesté','Documenté') for ab in NOMS) for s in range(1,NS+1)}
    rv=recherches_vide();clos={k for k,n in rv.items() if n>=P['vide_recherches_cloture']}
    traite={s:par[s]+sum(1 for ab in NOMS if (ab,s) in clos or st.get((ab,s))=='Hors domaine') for s in range(1,NS+1)}
    best=max(par,key=par.get)
    base=charger(base_chemin or RACINE/'assets/cas-reels.jsonl');valider_base(base)
    reels=[c for c in base if not c.get('fictif')]
    n={k:sum(c.get('statut_donnees')==k for c in reels) for k in ('actif','proposition','archive_a_revoir')}
    out.append(f"Étape 2 · cas réels : {n['actif']} actifs · {n['proposition']} propositions (sources à lire) · {n['archive_a_revoir']} archives"
               +(' → terminée' if n['actif'] else ' → en cours' if n['proposition'] else ' → à commencer : premier cas sous les règles courantes, de préférence avant son issue'))
    out.append(f"Étape 3 · strate pilote : {par[best]}/16 équivalents Documentés ou Attestés ({'meilleure : strate '+str(best) if par[best] else 'aucune strate entamée'}) ; "
               f"{sum(v==16 for v in traite.values())} strate(s) complète(s) (Vide clos et Hors domaine comptés) ; "
               f"{len(clos)}/{len(rv)} cases Vides closes ({P['vide_recherches_cloture']} recherches documentées) ; "
               f"emprunt T4 {'possible' if sum(v>0 for v in par.values())>=2 else 'fermé'}")
    if refs_chemin:
        r=lire_json(refs_chemin,'--references');exiger(isinstance(r,dict),'--references : objet attendu')
        out.append(f'Étape 4 · références externes : {len(r)} événements référencés')
    else:
        out.append('Étape 4 · références externes : aucun fichier fourni (--references)')
    act=[c for c in reels if c.get('statut_donnees')=='actif']
    for s in sorted({s for c in act for s in c['strates']}):
        lot=[c for c in act if s in c['strates']]
        dbl=sum(len(set(ids_codeurs(c)))>=2 and c['codage'].get('independants') is True for c in lot)
        sans=sum(bool(c['sans_evenement']) for c in lot)
        out.append(f"Étape 5 · strate {s} : {len(lot)} cas actifs (ρ1 dès {P['c_min_rho1']} homologues, ρ0 dès {P['seuil_rho0_cas_distincts']}) · "
                   f"{dbl} double-codés (sortie du mode solo : {P['double_codage_min_cas']} et {P['double_codage_part']:.0%}) · {sans} sans événement")
    if not act:out.append('Étape 5 · base réelle : aucun cas actif')
    if journal_chemin:
        r=score_result(charger(journal_chemin))
        v_=r['v4'];cib=v_.get('effectif_cible')
        out.append(f"Test à l'aveugle · {r['questions_eligibles']} questions éligibles V4 · {r['episodes_comparables']} épisodes comparables, cible "
                   +(f"{cib} (plancher {P['v4_n']}, requis par σ̂ {v_['effectif_requis']})" if cib else f"≥ {P['v4_n']}, σ̂(d) encore inconnu")
                   +f" · {r['statut']} · règle : {v_['regle']}"
                   +(f" · discriminantes : {r['v4_discriminant']['questions']}" if r.get('v4_discriminant') else ''))
        mj=r['moteur_contre_jugement'];df=r['difficulte']
        if mj:out.append(f"Mesure · moteur contre jugement scellé : {mj['questions']} questions · {mj['ameliorations']} améliorations · {mj['degradations']} dégradations · {mj['lecture']}")
        if df:out.append(f"Mesure · questions à référence extrême : {df['part_extremes']:.0%} · {df['lecture']}")
        dm=(r.get('decomposition_murphy') or {}).get('eligibles')
        if dm:out.append(f"Mesure · Murphy (éligibles) : fiabilité {dm['fiabilite']:.3f} · résolution {dm['resolution']:.3f} · incertitude {dm['incertitude']:.3f} · {dm['lecture']}")
        ab=r.get('abstentions')
        if ab:out.append(f"Mesure · abstentions (non estimé) : {ab['questions']} · {ab['part_des_questions']:.0%} des questions · {ab['resolues']} résolues, {ab['issues_realisees']} réalisées")
    else:
        out.append("Test à l'aveugle : aucun journal fourni (--journal)")
    out.append('Étapes 0, 1 et 6 (installation, décisions d’auteur, code différé) : état déclaré dans references/feuille-de-route.md')
    return '\n'.join(out)


def schema_documente():
    """Premier bloc JSON de `base-de-cas.md` §2 : le schéma qu'un lecteur recopiera."""
    sec=(RACINE/'references'/'base-de-cas.md').read_text(encoding='utf-8').split('## 2.',1)[1].split('\n## ',1)[0]
    m=re.search(r'```json\n(.*?)\n```',sec,re.S)
    exiger(m is not None,'base-de-cas.md §2 : schéma JSON absent')
    return json.loads(m.group(1))


# Paramètres déclarés mais lus par aucun calcul, à dessein (protocole.md A4 pour kappa_min).
PARAMETRES_RESERVES = set()   # 0.7.9 : kappa_min et kappa_rapportable sont lus par `accord`


def erreurs_parametres(params=None):
    """0.6.13 (audit 0.6.12, m7) : « paramètres exhaustifs » ne disait pas « chaque paramètre est lu ».
    Un paramètre publié dans §H mais jamais appliqué (largeur_max_affichage jusqu'en 0.4.5) passait.
    Tout paramètre est lu littéralement par le moteur (P['clé']), ou déclaré réservé."""
    src=Path(__file__).read_text(encoding='utf-8');err=[]
    for k in (params if params is not None else P):
        lu=re.search(r"P\[['\"]"+re.escape(k)+r"['\"]\]",src) is not None
        if not lu and k not in PARAMETRES_RESERVES:err.append(f'parametres.json : « {k} » n’est lu par aucun calcul ; l’appliquer ou le déclarer réservé')
        if lu and k in PARAMETRES_RESERVES:err.append(f'parametres.json : « {k} » déclaré réservé mais lu par le moteur')
    return err


EXCLUS_MANIFESTE = {'SHA256SUMS'}


def fichiers_livres():
    """Fichiers du skill, chemins relatifs POSIX triés (hors manifeste, __pycache__, *.pyc).
    0.7.15 : hors fichiers et dossiers cachés (`.gitattributes`, `.gitignore`, `.github/`, `.git/`).
    Ce sont des fichiers du dépôt, pas du skill ; plusieurs canaux d'installation ne les transmettent
    pas, et un manifeste qui les listait faisait échouer `audit` sur un paquet par ailleurs intact.
    Présents ou absents, ils ne comptent plus."""
    out=[]
    for p in sorted(RACINE.rglob('*')):
        r=p.relative_to(RACINE).as_posix()
        if p.is_dir() or r in EXCLUS_MANIFESTE or any(x.startswith('.') for x in r.split('/')) or '__pycache__' in r or r.endswith('.pyc'):continue
        out.append(r)
    return out


def manifeste_texte():
    return ''.join(f'{fichier_sha(RACINE/r)}  {r}\n' for r in fichiers_livres())


def erreurs_manifeste(texte=None):
    """0.6.14 (audit Manus, haute 4) : SHA256SUMS relie le contenu décompressé à la version livrée,
    fichier par fichier (`sha256sum -c SHA256SUMS`). L'audit refuse un fichier modifié, ajouté ou absent."""
    f=RACINE/'SHA256SUMS'
    if texte is None:
        if not f.is_file():return ['SHA256SUMS absent : le générer avec « moteur.py manifeste » avant livraison']
        texte=f.read_text(encoding='utf-8')
    attendu={};err=[]
    for l in texte.splitlines():
        if l.strip():
            h,_,r=l.partition('  ');attendu[r]=h
    reels=set(fichiers_livres())
    for r in sorted(set(attendu)-reels):err.append(f'SHA256SUMS : {r} absent du paquet')
    for r in sorted(reels-set(attendu)):err.append(f'SHA256SUMS : {r} non répertorié')
    for r in sorted(set(attendu)&reels):
        if fichier_sha(RACINE/r)!=attendu[r]:err.append(f'SHA256SUMS : {r} modifié depuis la livraison')
    return err


def audit():
    exiger(P['version']=='0.7.56','version du moteur et des paramètres différente')
    # 0.7.34 (audit Open Science) : la docstring du moteur annonçait 0.7.9 sans que l'audit la lise.
    exiger(f"Alphabet situationnel {P['version']} " in (__doc__ or ''),'docstring du moteur : version différente de parametres.json')
    errs=erreurs_parametres();exiger(not errs,' ; '.join(errs))
    for k in ('f_defaut','plafond_p0','w_emprunt','jaccard_H15','seuil_affichage','intervalle','double_codage_part','kappa_min','v4_gain_abs','v4_alpha','v4_puissance','delta_discriminant','fnr_max','alerte_R2','ecart_niveaux_max','kappa_rapportable','ratio_duree_fenetre','attenuation_w_f'):
        proba(P[k],k)
    for k in ('k','k0_frequence','demi_vie_ans','fenetre_reference_jours','multiplicateur_bouge','plafond_LR'):
        exiger(type(P[k]) in (int,float) and math.isfinite(P[k]) and P[k]>0,f'paramètre positif : {k}')
    date_iso(P['v4_dossier_depuis']);date_iso(P['jugement_procedure_depuis'])
    exiger(P['v4_test'] in ('signe','wilcoxon'),'v4_test : signe ou wilcoxon')
    exiger(P['v4_reference'] in ('inertie','jugement','comparateur_externe','vue_exterieure'),'v4_reference : inertie, jugement, comparateur_externe ou vue_exterieure')
    for k in ('seuil_rho0_cas_distincts','double_codage_min_cas','v4_n','faisceau_max','pas_max','n_min_publication','n_min_ancrage','c_min_rho1','c_min_niveau','placebo_tirages','weibull_occasions_min','accord_min_ancrages','rejets_tirage','repetabilite_ecart_min_jours'):
        exiger(type(P[k]) is int and P[k]>0,f'paramètre entier positif : {k}')
    for ab,p in P['inertie'].items():exiger(ab in NOMS and 0<proba(p)<1,'inertie invalide')
    exiger(set(P['inertie'])==set(NOMS),'inerties incomplètes')
    for key in ('matrice','autre_strate'):
        for a,row in P[key].items():
            exiger(a in NOMS and isinstance(row,dict),'matrice invalide')
            for b,intensity in row.items():exiger(b in NOMS and intensity in P['lambda'],'transition invalide')
    for v in P['lambda'].values():exiger(math.isfinite(v) and v>0,'multiplicateur positif requis')
    exiger(P['barreau']['defaut'] in BARREAUX and all(re.fullmatch(r'[A-Z]{3}>[A-Z]{3}',k) and v in BARREAUX for k,v in P['barreau']['exceptions'].items()),
           'barreau : A, I ou C ; exceptions « SRC>CIB »')
    files=['constitution','protocole','glossaire','strates','cartes-index','cartes','equivalences','antagonismes','grammaire','dynamiques','base-de-cas','graphe','simulation','validation','exemples','feuille-de-route','sources-france','angles-morts','apports-theoriques','frequences-externes']
    paths=[RACINE/'references'/f'{x}.md' for x in files]+[RACINE/'references/equivalences'/f'strate-{s:02}.md' for s in range(1,NS+1)]
    for path in paths:
        exiger(path.is_file(),f'fichier absent : {path.relative_to(RACINE)}')
        exiger('> Version : '+P['version'] in path.read_text(encoding='utf-8'),f'version absente/différente : {path.name}')
    sk=(RACINE/'SKILL.md').read_text(encoding='utf-8')
    exiger("version: '"+P['version']+"'" in sk,'version SKILL.md différente')
    protocol=(RACINE/'references/protocole.md').read_text(encoding='utf-8')
    begin='<!-- PARAMETRES:BEGIN -->';end='<!-- PARAMETRES:END -->'
    exiger(begin in protocol and end in protocol,'table exhaustive des paramètres absente')
    mirror=protocol.split(begin,1)[1].split(end,1)[0].strip()
    exiger(mirror==parametres_markdown(),'parametres.json et protocole §H diffèrent ; générer avec parametres')
    dyn=(RACINE/'references/dynamiques.md').read_text(encoding='utf-8')
    for ab,name in NOMS.items():
        lines=[x for x in re.findall(r'^\| '+re.escape(name)+r' \|(.*)\|$',dyn,re.M) if x.count('|')==15]
        exiger(bool(lines),f'matrice documentaire absente : {name}')
        cells=[x.strip() for x in lines[0].split('|')]
        exiger({list(NOMS)[j]:cells[j] for j in range(16) if cells[j]}==P['matrice'][ab],f'matrice documentaire différente : {name}')
        mi=re.search(r'^\| '+re.escape(name)+r' \| (0,\d+)',dyn,re.M)
        exiger(mi is not None and abs(float(mi[1].replace(',','.'))-P['inertie'][ab])<1e-9,f'inertie documentaire différente : {name}')
    exiger(type(P['nombre_strates']) is int and P['nombre_strates']>0,'nombre_strates : entier positif')
    exiger(len(statuts())==16*NS,f'{16*NS} équivalents attendus (16 cartes × {NS} strates)')
    for s in range(1,NS+1):
        for line in (RACINE/'references/equivalences'/f'strate-{s:02}.md').read_text(encoding='utf-8').splitlines():
            cells=[x.strip() for x in line.strip('|').split('|')]
            if len(cells)==5 and cells[3] in ('Documenté','Attesté'):
                exiger(cells[4].lower() not in ('à fournir','—',''),f'équivalent non sourcé : {cells[0]}@{s}')
                exiger(cells[3]=='Attesté' or re.search(r'«[^»]+»',cells[4]) is not None,
                       f'équivalent Documenté sans nom local « … » : {cells[0]}@{s} (objet-frontière, equivalences.md §2)')
                exiger(cells[3]!='Attesté' or len(cas_attestation(cells[4]))>=2,
                       f'équivalent Attesté sur moins de deux événements distincts : {cells[0]}@{s} (protocole.md A3, 0.7.46)')
            if len(cells)==5 and cells[3]=='Hors domaine':
                exiger(cells[4].lower() not in ('à fournir','—',''),f'Hors domaine sans motif : {cells[0]}@{s} (A3 : décision d’auteur motivée)')
    # Check actual local Markdown paths; numbered sections are checked where explicit.
    for path in [RACINE/'SKILL.md']+paths:
        text=path.read_text(encoding='utf-8')
        for target in re.findall(r'\]\(([^)]+\.md)\)',text):
            if '://' not in target:exiger((path.parent/target).is_file(),f'lien absent : {path.name} → {target}')
    # 0.6.5 : angles morts. Règle de forme du registre : chaque entrée est réfutable, sauf exclusion délibérée.
    for l in (RACINE/'references/angles-morts.md').read_text(encoding='utf-8').splitlines():
        if not l.startswith('| ') or l.startswith('| Angle mort') or l.startswith('|---'):continue
        c=[x.strip() for x in l.strip().strip('|').split('|')]
        exiger(len(c)==4 and c[0] and c[1] and c[3],f'angles-morts.md : entrée à 4 colonnes renseignées attendue — {l[:60]}')
        exiger(c[2] not in ('','—','-') or c[3].startswith('délibéré'),
               f'angles-morts.md : entrée sans condition de réfutation, non déclarée « délibéré » — {c[0][:50]}')
    for n_,l in enumerate((RACINE/'assets/rabbits.jsonl').read_text(encoding='utf-8').splitlines(),1):
        if not l.strip():continue
        r=json.loads(l)
        exiger(all(isinstance(r.get(k),str) and r[k].strip() for k in ('cas','probleme','construction','necessite','date'))
               and r.get('type') in ('carte','strate','qualificatif','statut','regle'),f'rabbits.jsonl:{n_} : champs cas, probleme, construction, type, necessite, date')
        # 0.6.5 : cycle de vie. Un registre sans statut est un historique, pas une dette.
        exiger(r.get('statut') in ('ouvert','resorbe'),f'rabbits.jsonl:{n_} : statut ouvert ou resorbe')
        exiger(r['statut']=='ouvert' or (isinstance(r.get('resolution'),str) and r['resolution'].strip()),
               f'rabbits.jsonl:{n_} : une entrée résorbée dit comment (resolution)')
        date_iso(r['date'])
    schema=schema_documente()
    try:valider_base([schema])
    except ValueError as e:raise ValueError(f'base-de-cas.md §2 : le schéma documenté ne passe pas valider — {e}') from None
    # 0.6.14 (audit Manus, haute 3) : les JSONL livrés sont validés, pas seulement la documentation.
    for nom in ('base-de-cas.exemple.jsonl','cas-reels.jsonl','cas-reels-originaux.jsonl'):
        try:valider_base(charger(RACINE/'assets'/nom))
        except ValueError as e:raise ValueError(f'assets/{nom} : {e}') from None
    try:score_result(charger(RACINE/'assets/journal.exemple.jsonl'))
    except ValueError as e:raise ValueError(f'assets/journal.exemple.jsonl : {e}') from None
    # 0.7.3 : le dossier de lecture d'exemple est le format que l'on recopiera ; il doit passer `dossier`.
    try:dossier_valider(lire_json(RACINE/'assets/dossier.exemple.json','dossier d’exemple'))
    except ValueError as e:raise ValueError(f'assets/dossier.exemple.json : {e}') from None
    errs=erreurs_manifeste();exiger(not errs,' ; '.join(errs[:8])+(f' (+{len(errs)-8})' if len(errs)>8 else ''))
    errs=erreurs_statuts()+erreurs_index()+erreurs_repetitions([RACINE/'SKILL.md',RACINE/'README.md']+paths)
    for f in ('constitution.md','simulation.md'):
        if OUVERTURE not in (RACINE/'references'/f).read_text(encoding='utf-8'):errs.append(f'{f} : ligne d’ouverture normative absente (« {OUVERTURE} »)')
    if not re.search(r'^Version '+re.escape(P['version'])+r'\b',(RACINE/'README.md').read_text(encoding='utf-8'),re.M):
        errs.append('README.md : « Version '+P['version']+' » absente')
    exiger(not errs,'cohérence documentaire : '+' ; '.join(errs))
    errs=erreurs_renvois([RACINE/'SKILL.md',RACINE/'README.md']+paths)
    exiger(not errs,'renvois : '+' ; '.join(errs))
    exiger(voisines() and all(voisines().get(ab) for ab in NOMS),'cartes.md : listes de voisines illisibles (A6)')
    incompatibles()
    print(f'audit : conforme — fichiers, versions, {16*NS} statuts, paramètres exhaustifs (chacun référencé par le code), '
          f'JSONL et dossier d’exemple validés, manifeste SHA256SUMS ({len(fichiers_livres())} fichiers), matrice et inerties, '
          f'{sum(len(RENVOI_RE.findall(p.read_text(encoding="utf-8"))) for p in [RACINE/"SKILL.md",RACINE/"README.md"]+paths)} renvois §, '
          'voisines A6, incompatibilités G6, schéma de fiche validé, répartition des statuts, index des cartes, répétitions ; '
          'contrôle de forme et de recoupement interne, pas de la justesse du contenu ni certification empirique')
    return True


# ───────────────────────── interface ─────────────────────────

def evenement_lire(raw):
    # 0.7.42 : l'apostrophe typographique (« s’intensifie », « s’affaiblit ») vaut l'apostrophe droite.
    raw=raw.replace('’',"'")
    parts=raw.split(' ',1);exiger(len(parts)==2,'événement : CARTE@strate type')
    types={'apparaît':'apparait','apparait':'apparait','persiste':'persiste','disparaît':'disparait','disparait':'disparait',
           'se renforce':'renforce','renforce':'renforce',"s'affaiblit":'affaiblit','affaiblit':'affaiblit',
           'se transforme':'transforme','transforme':'transforme',"s'intensifie":'intensifie','intensifie':'intensifie'}
    exiger(parts[1] in types,'type d’événement inconnu')
    return cle_valide(parts[0]),types[parts[1]]


def metadata(base,asof,demo=False):
    return {'version':P['version'],'date_information':asof,'demo':demo,'evaluation':'non encore évalué prospectivement',
            'empreintes':{'moteur':fichier_sha(__file__),'parametres':fichier_sha(RACINE/'assets/parametres.json'),'base':empreinte(base)}}


def pct(x,unite=True):
    """Pourcentage affiché sans fausse précision : entier entre 1 et 99 %, une décimale aux extrêmes.
    Le JSON et le journal gardent la valeur non arrondie."""
    v=x*100;s=f'{v:.0f}' if 1<=v<=99 else f'{v:.1f}'.replace('.',',')
    return s+(' %' if unite else '')


OUVERTURE='⚠ Prévision · cet outil prend un risque déclaré.'  # constitution.md §3, ligne normative unique


def texte_probabilite(p,itv):
    """S5 : « p [a–b] », ou « ~p (large : a–b) » si l'intervalle dépasse largeur_max_affichage (§H)."""
    if p is None:return 'non estimée'
    if not itv:return pct(p)+' [intervalle non estimé]'
    a,b=pct(itv[0],False),pct(itv[1],False)
    return f'~{pct(p)} (large : {a}–{b})' if itv[1]-itv[0]>P['largeur_max_affichage'] else f'{pct(p)} [{a}–{b}]'


def vider_chiffres(result):
    """0.7.39 (test régressif, série 2, défaut 5). Une abstention est une abstention : en 0.7.38, « non estimé »
    laissait dans la sortie JSON une bande d'horizon chiffrée (0,22 / 0,52 / 0,76), les variantes de codage, la paire
    « résultat principal » et la bande verbale. Tout chiffre dérivé de p est mis à null ; le motif et les drapeaux restent."""
    for k_ in CHAMPS_ABSTENTION:
        if k_ in result:result[k_]=None
    return result


CHAMPS_ABSTENTION=('p','intervalle','p_sans_cartes','apport_cartes','sensibilite','p_placebo','apport_homologie','p_inertie_strate',
                   'bande_horizon','variantes_codage','resultat_principal','bande_verbale','centile_placebo','homologie_discernable')


def controle_vue_exterieure(result, vue):
    """0.7.35. Deux contrôles, avant que les cartes ne parlent.
    (1) Vue extérieure d'abord (Tetlock et Gardner 2015) : le taux de base déclaré dans le dossier est rendu à côté de
    f (la fréquence du moteur sans cartes), avec leur rapport de cotes.
    (2) Contrôle prédictif a priori (McElreath, *Statistical Rethinking*) : p₀, ce que les paramètres posés à la main
    (λ, inerties, f) impliquent avant toute révision par des cas, est comparé au taux de base. Si leurs cotes diffèrent de
    plus de `vue_exterieure_rapport_max` (10, le plafond de LR : plus que des cartes ne pourraient justifier), l'a priori est
    absurde pour ce domaine : non estimé."""
    if not vue or result.get('p') is None:return result
    cote=lambda q:min(max(q,1e-9),1-1e-9)/(1-min(max(q,1e-9),1-1e-9))
    v=vue['frequence'];ap=result.get('a_priori') or {};p0=ap.get('p0');f_=result.get('p_sans_cartes')
    # 0.7.42 : un composé n'a pas d'a priori propre ; son p (persistance × référence conditionnelle) tient lieu de p₀,
    # et son comparateur de f. Le contrôle attrape alors une référence absurde pour le domaine.
    if p0 is None and 'composantes' in result:p0=result.get('p')
    if f_ is None:f_=result.get('comparateur')
    rf=None if f_ is None else cote(f_)/cote(v);r0=None if p0 is None else cote(p0)/cote(v)
    R=P['vue_exterieure_rapport_max']
    absurde=r0 is not None and (r0>R or r0<1/R)
    alt=vue.get('classe_alternative') if isinstance(vue.get('classe_alternative'),dict) else None
    result['vue_exterieure']={'declaree':v,'classe_de_reference':vue['classe_de_reference'],'source':vue['source'],
        'alternative':None if alt is None else alt['frequence'],'classe_alternative':None if alt is None else alt['classe_de_reference'],
        'motif_sans_alternative':vue.get('motif_sans_alternative') if alt is None else None,
        'ecart_critere':vue.get('ecart_critere'),
        'ecart_classes':None if alt is None else abs(alt['frequence']-v),
        'f_moteur':f_,'rapport_cotes_f':rf,'p0':p0,'rapport_cotes_p0':r0,'a_priori_absurde':absurde,
        'lecture':'vue extérieure d’abord : le taux de base déclaré avant le calcul ; p₀ hors d’un facteur '+str(R)+' en cotes = paramètres incompatibles avec le domaine. '
                  'Elle ne modifie pas p : c’est le bras de référence de V4 (§19), qui doit rester indépendant du moteur ; pour qu’une fréquence '
                  'sourcée entre dans le calcul, la passer en référence (--fref avec --definition-ref, ou --references)'}
    if absurde:
        result.update(p=None,intervalle=None,p_sans_cartes=None,apport_cartes=None,sensibilite=None,
                      p_placebo=None,apport_homologie=None,p_inertie_strate=None,
                      non_estime_motif=f'a priori incompatible avec la vue extérieure (p₀ {p0:.3f} contre {v:.3f}, rapport de cotes {r0:.1f})')
        vider_chiffres(result)
        result.setdefault('drapeaux',[]).append('Non estimé : les paramètres posés à la main donnent un a priori hors d’un facteur '
            f'{R:g} en cotes du taux de base déclaré ; corriger la référence (--fref, --references) ou la vue extérieure, sans retoucher le dossier scellé.')
    return result


def appliquer_temporalite(result, temporalite):
    """0.6.10. Le moteur ne sait pas reconnaître qu'une question porte sur une échéance programmée
    (scrutin, proclamation : test brésilien) ou sur un phénomène à durée de vie propre (cyclone : test
    Polo, ÉMERGENCE@11 persistant à 96,75 % sur 7 jours par l'inertie trimestrielle générique). Déclarée
    par le codeur, cette temporalité interdit de chiffrer avec le seul taux générique. 0.6.13 (audit
    0.6.12, M2) : la règle ne mordait que sur une base vide (ρ4) ; avec des cas homologues, une
    proclamation ou un cyclone recevaient un chiffre, alors que ces cas, appariés par cartes et non par
    calendrier, partagent le même angle mort. Désormais, hors « generique », **seule une référence externe**
    (`--fref`, `--references`, ou la référence conditionnelle d'un composé) permet de chiffrer ; des cas
    seuls ne suffisent pas. La déclaration reste humaine."""
    result['temporalite']=temporalite
    ap=result.get('a_priori') or {}
    externe=ap.get('reference_externe') is not None or 'conditionnelle' in (result.get('composantes') or {})
    result['reference_de_domaine']=externe
    if temporalite!='generique' and not externe and result.get('p') is not None:
        motif={'programmee':'échéance programmée','duree_de_vie':'durée de vie propre au phénomène'}[temporalite]
        result.update(p=None,intervalle=None,p_sans_cartes=None,apport_cartes=None,sensibilite=None,
                      p_placebo=None,apport_homologie=None,p_inertie_strate=None,
                      non_estime_motif=f'{motif} : référence de domaine requise (--fref ou --references) ; ni le taux générique ni des cas appariés par cartes ne représentent ce calendrier')
        vider_chiffres(result)
        result.setdefault('drapeaux',[]).append(f'Non estimé : {motif} ; l’inertie et la fréquence par défaut ne représentent pas ce calendrier ou cette durée de vie (simulation.md §4).')
    # 0.7.39 (série 2, défaut 5) : un événement programmé est unique (un sommet, un scrutin) ; le composer sur 3 ou 6
    # fenêtres n'a pas de sens. Pas de bande d'horizon, même avec une référence.
    if temporalite=='programmee' and result.get('bande_horizon') is not None:
        result['bande_horizon']=None
        result.setdefault('drapeaux',[]).append('Événement programmé : unique, pas de bande d’horizon (la composer sur 3 ou 6 fenêtres n’aurait pas de sens).')
    return result


def appliquer_inertie_objet(result, typ, cible, demo):
    """0.7.39 (décision d'auteur, série 2 de tests régressifs, défaut 2). L'inertie du moteur est celle d'une carte
    (INCERTITUDE : 0,40 par trimestre), pas celle de l'objet : une doctrine en place depuis 1979, une trêve d'une semaine
    et un embargo y ont la même persistance. Test T2 (ambiguïté stratégique américaine sur Taïwan) : 0,40 contre une issue
    réalisée, Brier 0,36. Les paramètres ne changent pas (version séparée, données réelles). Hors démonstration, une
    persistance ou une disparition en strate de prévision se chiffre **seulement** avec une référence de l'objet
    (`--fref` avec `--definition-ref`, ou `--references`) ; sinon non estimé. En démonstration, un drapeau le dit."""
    if typ not in ('persiste','disparait') or result.get('p') is None:return result
    ap=result.get('a_priori') or {}
    if ap.get('reference_externe') is not None:return result
    s_=int(cible.split('@')[1])
    msg=(f'Inertie générique de la carte ({cible.split("@")[0]} : {P["inertie"][cible.split("@")[0]]:g} par trimestre), pas celle de l’objet '
         '(une doctrine, une trêve, un embargo) ; fournir une référence de l’objet (--fref avec --definition-ref, ou --references).')
    if demo or s_ not in P['strates_prevision']:
        result.setdefault('drapeaux',[]).insert(0,msg);result['inertie_generique']=True;return result
    result.update(non_estime_motif=f'{typ} sans référence de l’objet : l’inertie générique de la carte ne représente pas cet objet (0.7.39)',
                  inertie_generique=True)
    vider_chiffres(result)
    result.setdefault('drapeaux',[]).append('Non estimé : '+msg)
    return result


def ligne_signalement(result):
    """Ligne S5 (protocole.md, constitution.md §3) :
    ⚠ ρ[n] · [barreau] · [source en clair] · p₀ [x] % · p [y] % [intervalle] · échéance [date] · journal [id]"""
    h=result.get('homologie');c=result.get('c_A') or 0;ap=result.get('a_priori')
    if result.get('non_estime_motif'):src=result['non_estime_motif']
    elif c and h=='H3':src=f'{c} cas empruntés (H3)'
    elif c:src=f'{c} cas distincts ({h})'
    elif 'conditionnelle' in result.get('composantes',{}):src='composé : persistance × référence conditionnelle'
    elif result.get('non_estime_motif'):src=result['non_estime_motif']
    elif result.get('p') is None:src='référence conditionnelle manquante'
    else:src='a priori '+('ancré' if ap and ap.get('ancrage') else 'non ancré')+', aucun cas'
    if ap and ap.get('source_externe') and not result.get('non_estime_motif'):src+=f" · réf. {ap['source_externe']}"
    p0=f" · p₀ {pct(ap['p0'])}" if ap and not result.get('non_estime_motif') else ''
    sb=result.get('sensibilite')
    if sb and sb['traverse_seuil'] and result.get('p') is not None:
        ptxt=f"{pct(result['p'])} non identifié (variantes {pct(sb['min'],False)}–{pct(sb['max'])} de part et d'autre de {pct(sb['seuil_decision'])})"
        return (f"⚠ ρ{result['rho']} · {BARREAUX[result.get('barreau') or P['barreau']['defaut']]} · {src}{p0} · p {ptxt}"
                f" · échéance {result.get('echeance') or '[date]'} · journal {result.get('journal') or '[à attribuer]'}")
    bar=BARREAUX[result.get('barreau') or P['barreau']['defaut']]
    return (f"⚠ ρ{result['rho']} · {bar} · {src}{p0} · p {texte_probabilite(result.get('p'),result.get('intervalle'))}"
            f" · échéance {result.get('echeance') or '[date]'} · journal {result.get('journal') or '[à attribuer]'}")


BANDES_VERBALES=((.05,'probabilité très éloignée'),(.20,'très improbable'),(.45,'improbable'),(.55,'chance approximativement égale'),
                 (.80,'probable'),(.95,'très probable'),(1.01,'presque certain'))


def bande_verbale(p):
    """0.7.18 (directive ODNI 203, 2015, citée par Van Puyvelde 2015). Sept bandes de probabilité, colonne
    « probabilité » et non « certitude » : p est une fréquence conditionnelle, pas un état de confiance du lecteur.
    Une bande ne remplace pas p ni son intervalle ; elle dit combien de chiffres le lecteur peut utiliser."""
    if p is None:return None
    return next(n for b,n in BANDES_VERBALES if p<b)


def afficher(result,as_json=False):
    if as_json or 'p' not in result:
        print(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False));return
    print(OUVERTURE)
    print(ligne_signalement(result))
    # 0.7.34 (audit Open Science) : un p affiché ressemble à une mesure. Tant qu'aucune calibration n'existe, la
    # sortie dit d'abord que les paramètres sont posés à la main, et donne la bande avant le chiffre.
    if result.get('p') is not None:
        print(f"Non calibré : multiplicateurs, inerties, k₀ et demi-vie sont posés à la main, non dérivés de données ; "
              f"lire d’abord la bande ({bande_verbale(result['p'])}) et le taux sans cartes, le chiffre ensuite")
    ve_=result.get('vue_exterieure')
    if ve_:
        print(f"Vue extérieure d’abord : taux de base déclaré {pct(ve_['declaree'])} ({ve_['classe_de_reference']}) · "
              f"f du moteur {pct(ve_['f_moteur'])} · p₀ {pct(ve_['p0'])}"+(' · A PRIORI ABSURDE : non estimé' if ve_['a_priori_absurde'] else '')
              +" · elle ne modifie pas p (bras de référence de V4, indépendant du moteur)")
        if ve_.get('ecart_critere'):print(f"Classe et critère de résolution : {ve_['ecart_critere']}")
        if ve_.get('alternative') is not None:
            print(f"Classe alternative {pct(ve_['alternative'])} ({ve_['classe_alternative']}) · écart entre classes "
                  f"{round(100*ve_['ecart_classes'])} points : plus l’écart est grand, plus le chiffre dépend du choix de la classe")
    rp_=result.get('resultat_principal')
    if rp_:print(f"À lire d’abord : sans cartes {pct(rp_['p_sans_cartes'])} → avec cartes {pct(rp_['p_avec_cartes'])} "
                 "(aucun cas réel actif : arêtes non éprouvées, P8 ; p seul n’est qu’un dérivé de cette paire"
                 +(" ; a priori non ancré : l’écart lui-même n’est pas interprétable)" if not (result.get('a_priori') or {}).get('ancrage') else ")"))
    bh_=result.get('bande_horizon')
    if bh_:print('Bande d’horizon ('+bh_['semantique']+') : '+' · '.join(f"{h} × {bh_['fenetre']} : {pct(v['p'])} (sans cartes {pct(v['p_sans_cartes'],False)})"
                                       for h,v in bh_['pas'].items() if v)+" — l’horizon est la question, pas une incertitude")
    vc_=result.get('variantes_codage')
    if vc_ and vc_['plage']:print(f"Variantes de codage (mots f retirés, un par un puis tous) : p de {pct(vc_['plage'][0],False)} à {pct(vc_['plage'][1])} — "
                                 "un ancrage f pèse ici autant qu’un F ; c’est cette plage qui dit ce qu’il coûte")
    # 0.6.13 (audit 0.6.12, m4) : en sortie, le nom canonique (grammaire.md) ; l'abréviation reste dans le JSON.
    ev=result['evenement'];k_,t_=ev.split(' ',1) if ' ' in ev else (ev,'')
    try:c_,s_=k_.split('@');ev=f"{NOMS[c_]}@{s_} {t_}".strip()
    except (ValueError,KeyError):pass
    print(f"Événement : {ev} · ρ = provenance du chiffre, pas sa fiabilité")
    bv_=result.get('bande_verbale')
    if bv_:print(f"Bande : {bv_['p']}"+(f" (intervalle de {bv_['intervalle'][0]} à {bv_['intervalle'][1]})" if bv_['intervalle'][0] else ' (intervalle non estimé)')+" — échelle en sept bandes ; "
                 "une fréquence conditionnelle, pas une certitude")
    if (result.get('barreau') or P['barreau']['defaut'])=='A':
        print("Lecture : association — si le motif observé dans les cas et les inerties se répète, alors cette fréquence ;"
              " aucun modèle causal, donc ni effet d'une intervention ni « ce qui se serait passé »")
    # 0.7.39 : en abstention, le comparateur reste (bras de scoring, frequence_de_base du journal) mais se dit tel.
    print('Comparateur au même horizon'+(' (bras de scoring, pas une estimation : le moteur s’abstient)' if result.get('non_estime_motif') else '')+' : '
          +('non évaluable' if result.get('comparateur') is None else pct(result['comparateur'])))
    ap=result.get('a_priori')
    if result.get('p_sans_cartes') is not None and result.get('p') is not None:
        d=(result['p']-result['p_sans_cartes'])*100
        if ap is not None and not ap.get('ancrage'):
            # 0.7.3. Sans ancrage, f est surtout le défaut (5 % à trois mois) lissé : l'écart mesure la
            # distance au défaut, pas l'apport des cartes. L'annoncer comme un apport était un contresens.
            print(f"Sans cartes (inertie et fréquences seules) : {pct(result['p_sans_cartes'])} — écart de {d:+.1f} points "
                  "non interprétable : l’a priori n’est pas ancré (effectif pondéré sous n_min_ancrage), "
                  "l’écart mesure la distance au défaut, pas ce que les cartes ajoutent")
        else:
            print(f"Sans cartes (inertie et fréquences seules) : {pct(result['p_sans_cartes'])} — "
                  +('les cartes ne changent rien à ce calcul : un bon score ne validerait pas la lecture' if abs(d)<0.05
                    else f"les cartes déplacent la probabilité de {d:+.1f} points".replace('.',',')))
    pl=result.get('placebo')
    if result.get('p') is not None and 'p_placebo' in result:
        if pl and result.get('p_placebo') is not None:
            d=result['apport_homologie']*100
            plage=f" ; 90 % des tirages entre {pct(pl['plage_90'][0],False)} et {pct(pl['plage_90'][1])}" if pl.get('plage_90') else ''
            print(f"Placebo d’homologie : {pct(result['p_placebo'])} ({pl['tirages']} tirages de {pl['cas_tires']} cas parmi "
                  f"{pl['cas_disponibles']} de la strate et de la fenêtre, graine {pl['graine']}{plage}) — apport de l’homologie "
                  +f"{d:+.1f} points".replace('.',',')
                  +(' : le choix des homologues ne fait pas mieux que des cas tirés au hasard' if abs(d)<0.05 else ''))
        else:
            print('Placebo d’homologie : non évaluable (aucun cas de la strate et de la fenêtre, emprunt H3, ou composé)')
    if ap and ap.get('sources'):
        print('Sources du calcul (carte · intensité de matrice · multiplicateur · motif) :')
        for x in ap['sources']:
            print(f"  {NOMS.get(x['mot'].split('@')[0],x['mot'].split('@')[0])}"
                  f"{'@'+x['mot'].split('@')[1] if '@' in x['mot'] else ''} · {x['intensite']} · λ {x['lambda']:.2f} · {x['note']}")
        if any(x['note']=="autre strate, abaissée d'un cran" for x in ap['sources']):
            # 0.7.3 : l'alerte visait aussi les propagations documentées (autre_strate) et les transferts ancrés.
            print('! Influence inter-strates par défaut : arête de la matrice abaissée d’un cran, sans propagation documentée '
                  '(autre_strate) ni transfert ancré (P1 ne présume pas que les dynamiques se transportent) : à déclarer dans « À vérifier ».')
    if result.get('fragilite_niveau') is not None and result['fragilite_niveau']>P['ecart_niveaux_max']:
        lv=', '.join(f"{k} {v['p']*100:.1f} % ({v['c_A']} cas)" for k,v in (result.get('niveaux') or {}).items())
        print(f"Fragilité de niveau : p varie de {result['fragilite_niveau']*100:.1f} points selon le niveau d’homologie "
              f"({lv}) ; le seuil c_min_rho1 décide seul. Comparabilité et effectif s’échangent sans que le lecteur le voie.")
    sb=result.get('sensibilite')
    if sb:
        print(f"Sensibilité du modèle : {pct(sb['modele']['min'],False)}–{pct(sb['modele']['max'])} sur "
              f"{len([x for x in sb['variantes'] if x['groupe']=='modele'])} variantes "
              "(multiplicateurs d'un cran, inerties ± 0,05, fréquence par défaut × ½ et × 2)")
        print(f"Sensibilité de la classe de référence : {pct(sb['classe']['min'],False)}–{pct(sb['classe']['max'])} "
              f"sur {len([x for x in sb['variantes'] if x['groupe']=='classe'])} variantes "
              "(Jaccard ± 0,1, k et k₀ × ½ et × 2, demi-vie × ½ et × 2)"
              +(' — classe instable : les cas retenus ou le niveau changent selon le seuil' if sb['classe'].get('instable') else ' — classe stable'))
        print(f"Bande retenue : {pct(sb['min'],False)}–{pct(sb['max'])}"
              +(f" — non identifié : elle traverse {pct(sb['seuil_decision'])}" if sb['traverse_seuil'] else '')
              +(f" (origine : {sb['origine_seuil']})" if sb.get('origine_seuil') else '')
              +(f" — bande large (plus de {pct(P['largeur_max_affichage'])}) : le résultat dépend des hypothèses non calibrées" if sb.get('bande_large') else '')
              +(f" — saturée : une variante touche le plafond des cartes ({pct(P['plafond_p0'])}), la bande ne mesure plus rien" if sb.get('saturee') else ''))
        if sb.get('effet_force') is not None and abs(sb['effet_force'])<1e-12:
            print("Force d’ancrage : aucun effet numérique ici (les multiplicateurs viennent de la matrice, pas du degré de preuve ; "
                  "F/f ne pèse que sur la sélection des homologues"
                  +(", nulle sans base)." if not result.get('c_A') else ", sans effet sur les cas retenus ici)."))
        at_=sb.get('effet_attenuation') or {}
        if at_:
            print('Atténuation de λ (décision 5, variante non appliquée à p) : '+' · '.join(
                f"{'par la force F/f' if k=='force' else 'par corroboration et passage'} {v*100:+.1f} points".replace('.',',') for k,v in at_.items()))
        if sb.get('effet_force') is not None and abs(sb['effet_force'])>=1e-12:
            print(f"Force d’ancrage : toutes les forces abaissées à f, p varie de {sb['effet_force']*100:+.1f} points "
                  "(par la seule sélection des homologues)".replace('.',','))
    if 'a_priori' in result:
        ap=result['a_priori']
        part=P['k0_frequence']/(ap['effectif_reference']+P['k0_frequence'])
        print(f"Trace : multiplicateur {ap['LR']:.2f} · homologie {result['homologie'] or '—'} · c_A {result['c_A']} · "
              f"n_A {result['n_A']:.1f} · n_E {result['n_E']:.1f} · part de l’a priori dans f {round(part*100)} %"
              +(f" · part de p₀ dans p {round(result['poids_a_priori_p']*100)} %" if result.get('poids_a_priori_p') is not None else '')
              +(f" · taille effective (Kish) {result['n_eff_kish']:.1f} pour {result['c_A']} cas, cas le plus lourd {round(result['part_cas_le_plus_lourd']*100)} %"
                if result.get('n_eff_kish') else ''))
        itf=ap.get('intervalle_f')
        if 'reference_a_priori' in ap:
            print(f"A priori : f {pct(ap['reference_interne'])}"+(f" [{pct(itf[0],False)}–{pct(itf[1])}]" if itf else '')
                  +f" sur {ap['effectif_reference']:.1f} observations pondérées + {P['k0_frequence']} pseudo-observations de la référence "
                  +f"{pct(ap['reference_a_priori'])} ; p₀ révisé par {result['n_A']:.1f} observations + {P['k']:g} pseudo-observations"
                  +(" — « ancré » signifie données au moins aussi lourdes que l’a priori (n_min_ancrage), pas fréquence précise" if ap.get('ancrage') and ap.get('reference_externe') is None else ''))
    ml=result.get('marqueur_local')
    if ml:print(f"Résolution (S1) : la source doit mesurer le marqueur local « {ml['marqueur']} » ({ml['equivalent']}, {ml['statut']}) ; sinon reformuler l'événement")
    ds=result.get('dossier')
    if ds:print(f"Dossier de lecture : sceau {ds['sceau'][:16]}… · contre-candidate(s) "
                f"{', '.join(NOMS.get(k.split('@')[0],k)+'@'+k.split('@')[1] for k in ds['contre_candidate'])} · {ds['controle']}")
    for flag in result.get('drapeaux',[]):print('! '+flag)
    print('Valeurs non arrondies, détails et empreintes : ajouter --json. Aucun score de validation acquis.')


def main():
    parser=argparse.ArgumentParser(description=__doc__);subs=parser.add_subparsers(dest='cmd',required=True)
    for name in ('audit','autotest','parametres'):subs.add_parser(name)
    sj=subs.add_parser('sceller-jugement');sj.add_argument('--question',required=True);sj.add_argument('--evenement',required=True)
    sj.add_argument('--p',type=float,required=True)
    sj.add_argument('--date','--date-information',dest='date',required=True,
                    help='date d’information de la prévision (champ « date » du journal), pas le jour du scellement (0.7.42)')
    sj.add_argument('--origine',choices=('moteur','jugement'),default='moteur')
    for name in ('valider','scorer','sceller'):
        s=subs.add_parser(name);s.add_argument('fichier')
        if name=='scorer':s.add_argument('--csv',action='store_true')
        if name=='valider':s.add_argument('--registre')
    p=subs.add_parser('partager');p.add_argument('ids',nargs='+')
    p.add_argument('--registre',default='partage.jsonl');p.add_argument('--date')
    subs.add_parser('manifeste')
    sc=subs.add_parser('sceller-comparateur')
    for k in ('--question','--evenement','--date','--methode','--source'):sc.add_argument(k,required=True)
    sc.add_argument('--p',type=float,required=True);sc.add_argument('--aveugle',action='store_true')
    sc.add_argument('--vu',action='append',default=[]);sc.add_argument('--contexte',choices=CONTEXTES_COMPARATEUR,required=True)
    ex=subs.add_parser('export-codeur');ex.add_argument('--base',required=True);ex.add_argument('--cas',required=True)
    sq=subs.add_parser('squelette');sq.add_argument('--calcul',required=True);sq.add_argument('--id',required=True)
    ft=subs.add_parser('fiche-test');ft.add_argument('--journal',required=True);ft.add_argument('--id',required=True)
    fr=subs.add_parser('fiche-resultat');fr.add_argument('--journal',required=True);fr.add_argument('--id',required=True)
    fr.add_argument('--issue',type=int,choices=(0,1));fr.add_argument('--preuve',required=True);fr.add_argument('--date',required=True);fr.add_argument('--note')
    fr.add_argument('--source-utilisee',required=True,help='la source qui a effectivement tranché l’issue (0.7.44)')
    fr.add_argument('--source-conforme',choices=('oui','non'),required=True,help='est-ce la source de résolution déclarée au dossier ?')
    fr.add_argument('--ecart-source',help='requis si --source-conforme non : pourquoi une autre source')
    fr.add_argument('--mode',choices=MODES_RESOLUTION,required=True,help='positif : un document établit l’issue ; absence : aucune trace trouvée')
    ig=subs.add_parser('ingerer');ig.add_argument('registre');ig.add_argument('--journal-sortie');ig.add_argument('--json',action='store_true')
    dp=subs.add_parser('depouiller');dp.add_argument('--premier',required=True);dp.add_argument('--second',required=True);dp.add_argument('--json',action='store_true')
    rc=subs.add_parser('recolter');rc.add_argument('--carnet',required=True);rc.add_argument('--fait');rc.add_argument('--source');rc.add_argument('--source-url')
    rc.add_argument('--date');rc.add_argument('--disponible-le');rc.add_argument('--date-consultation');rc.add_argument('--classe-source')
    rc.add_argument('--fiabilite',choices=FIABILITES);rc.add_argument('--credibilite',type=int);rc.add_argument('--independance-critere');rc.add_argument('--independance-motif')
    rc.add_argument('--jusqu-au',help='lister les faits disponibles à cette date (brouillon de dossier)')
    rc.add_argument('--archive',help='instantané Wayback de la pièce (0.7.48) : prouve son contenu à la date de l’instantané')
    ac=subs.add_parser('accord');[ac.add_argument(k,type=int,required=True) for k in ('--a','--b','--c','--d')];ac.add_argument('--json',action='store_true')
    ac.add_argument('--repetabilite',action='store_true');ac.add_argument('--ecart-jours',type=int);ac.add_argument('--llm',action='store_true')
    cv=subs.add_parser('conservativite');cv.add_argument('--base',required=True);cv.add_argument('--sortie');cv.add_argument('--contre');cv.add_argument('--empreinte')
    rj=subs.add_parser('rejets');rj.add_argument('--dossier',required=True);rj.add_argument('--audit')
    vr_=subs.add_parser('valider-references');vr_.add_argument('fichier')
    cf=subs.add_parser('confronter');cf.add_argument('fichier');cf.add_argument('--json',action='store_true')
    vo=subs.add_parser('voisins');vo.add_argument('fichier');vo.add_argument('--json',action='store_true')
    ds=subs.add_parser('dossier');ds.add_argument('--fichier',required=True);ds.add_argument('--json',action='store_true')
    q=subs.add_parser('equivalences');q.add_argument('--carte',required=True);q.add_argument('--json',action='store_true')
    b=subs.add_parser('bilan');b.add_argument('--base');b.add_argument('--references');b.add_argument('--journal')
    for name in ('calculer','trajectoires','sonde','noyau','attribuer'):
        c=subs.add_parser(name);c.add_argument('--base');c.add_argument('--etat',required=True)
        c.add_argument('--date-information');c.add_argument('--liaison',action='append',default=[])
        c.add_argument('--bouge',action='append',default=[]);c.add_argument('--manque',action='append',default=[])
        c.add_argument('--ctr-materielle',action='append',default=[]);c.add_argument('--references')
        c.add_argument('--fref',type=float);c.add_argument('--source-ref');c.add_argument('--periode-ref');c.add_argument('--disponible-ref')
        c.add_argument('--definition-ref',help='classe de la référence, dans le vocabulaire de la source (requis avec --fref, 0.7.39)')
        c.add_argument('--pas',type=int,default=1);c.add_argument('--semantique');c.add_argument('--resolution')
        c.add_argument('--echeance');c.add_argument('--journal');c.add_argument('--strates',default='')
        c.add_argument('--json',action='store_true');c.add_argument('--demo',action='store_true')
        c.add_argument('--sans-cartes',action='store_true')
        c.add_argument('--exploratoire',action='store_true',
                       help='0.7.52 (validation.md §29) : lève L7 pour CE calcul seul ; résultat marqué, jamais publié, compté à part')
        c.add_argument('--temporalite',choices=TEMPORALITES,default=None)
        if name in ('calculer','sonde','attribuer'):c.add_argument('--evenement',required=True)
        if name=='noyau':c.add_argument('--evenement',action='append',required=True);c.add_argument('--exclusion',action='append',default=[])
        if name=='calculer':c.add_argument('--dossier')
        if name=='sonde':c.add_argument('--tirage',choices=('aretes','intensites','inerties'),default='aretes');c.add_argument('--tirages',type=int)
    a=parser.parse_args()
    if a.cmd=='audit':audit();return
    if a.cmd=='autotest':autotest();return
    if a.cmd=='parametres':print(parametres_markdown());return
    if a.cmd=='valider':valider(a.fichier,a.registre);return
    if a.cmd=='dossier':
        dr=dossier_valider(lire_json(a.fichier,'--fichier'))
        if a.json:print(json.dumps(dr,ensure_ascii=False,indent=2));return
        print(f"dossier conforme — {dr['mots']} mots · candidates {', '.join(NOMS[k.split('@')[0]]+'@'+k.split('@')[1] for k in dr['candidats'])} · "
              f"contre-candidate(s) {', '.join(NOMS[k.split('@')[0]]+'@'+k.split('@')[1] for k in dr['contre_candidate'])} · {len(dr['evenements'])} événement(s) déclaré(s)")
        print('recherches A7 : '+('plancher atteint (familles et paires couvertes)' if dr['complet'] else
              'dossier INCOMPLET — statut de lecture Spéculatif ; à reporter dans « À vérifier » :\n  - '+'\n  - '.join(dr['manques'])))
        print(f"sceau : {dr['sceau']}")
        print(dr['instruction'])
        return
    if a.cmd=='voisins':
        r=voisins(charger(a.fichier));exiger(r is not None,'voisins : aucune transition dans la base')
        if a.json:print(json.dumps(r,ensure_ascii=False,indent=2));return
        mv,un=r['meilleur_voisin'],r['unicite']
        print(f"{r['transitions']} transitions · jumeau H1 non trivial : {r['jumeau_H1_non_trivial']} ({r['part_jumeau_H1']*100:.0f} %) · "
              f"meilleur voisin : moyenne {mv['moyenne']:.3f}, médiane {mv['mediane']:.3f}, minimum {mv['minimum']:.3f} · "
              f"au-dessus de {r['seuil']} : {r['au_dessus_jaccard_H15']}/{r['transitions']}")
        if un:print(f"unicité moyenne {un['moyenne']:.3f} (médiane {un['mediane']:.3f}, minimum {un['minimum']:.3f}) · "
                    f"{un['part_inferieure_a_1']*100:.0f} % des transitions partagent des mois · concurrence maximale {un['concurrence_max']}")
        co_=r['co_occurrence']
        print(f"co-occurrence dans {r['etats_distincts']} états distincts : {co_['toujours_ensemble']} paire(s) de cartes toujours ensemble"
              +(' ; la plus liée : '+' + '.join(co_['paires'][0]['cartes'])+f" (Jaccard {co_['paires'][0]['jaccard']:.2f}, {co_['paires'][0]['ensemble']} états)" if co_['paires'] else ''))
        print('par strate (cas / transitions) : '+' · '.join(f"{k}: {v['cas']}/{v['transitions']}" for k,v in r['par_strate'].items()))
        print(r['lecture']);return
    if a.cmd=='confronter':
        r=confronter(charger(a.fichier))
        if a.json:print(json.dumps(r,ensure_ascii=False,indent=2));return
        c_=r['classes'];print(f"{r['apparitions']} apparition(s) observée(s) : {c_['meme_strate']} atteignable(s) dans la strate, "
              f"{c_['propagation_documentee']} par propagation documentée, {c_['transfert_ancre']} par transfert ancré, {c_['position_manque']} par position manque, "
              f"{c_['inter_strates_abaissee']} seulement par une arête inter-strates abaissée, {c_['non_atteignable']} NON ATTEIGNABLE(S), {c_['etat_nul']} depuis l’état nul")
        for d_ in r['divergences']:
            print(f"  {d_['cas']} {d_['date']} : {d_['apparition']} depuis {' + '.join(d_['depuis']) or '∅'} — {d_['classe']}"+(' (fictif)' if d_['fictif'] else '')+(f" ({d_['statut']})" if d_['statut']!='actif' else ''))
        cv=r['couverture_aretes'];print(f"Arêtes de la matrice éprouvées : {cv['avec_une_occasion']}/{cv['aretes']} au moins une fois, {cv['avec_dix_occasions']}/{cv['aretes']} au moins dix fois")
        print('Maintien selon l’âge (pas déjà présents) : '+' · '.join(f"{k} : {v['maintiens']}/{v['occasions']}"
              +(f" [{v['intervalle_95'][0]*100:.0f}–{v['intervalle_95'][1]*100:.0f} %]" if v['intervalle_95'] else '') for k,v in r['age'].items()))
        t_=r['test_age']
        if t_:
            print(f"Écart âge ≥ 1 − âge 0 : {t_['ecart']*100:+.1f} points (écart-type {t_['ecart_type']*100:.1f} ; détectable à 80 % : {t_['ecart_detectable_80']*100:.0f} points)")
            cw=t_['critere_weibull'];print('Critère d’ouverture d’une loi à taux variable ('+cw['regle']+') : '
                  +('atteint' if cw['atteint'] else 'non atteint' if cw['applicable'] else 'non applicable (base fictive, archivée ou trop petite)'))
        for l_ in r['limites']:print('! '+l_)
        return
    if a.cmd=='bilan':print(bilan(a.base,a.references,a.journal));return
    if a.cmd=='manifeste':
        (RACINE/'SHA256SUMS').write_text(manifeste_texte(),encoding='utf-8')
        print(f'SHA256SUMS : {len(fichiers_livres())} fichiers ; vérifier avec « sha256sum -c SHA256SUMS » ou « moteur.py audit »');return
    if a.cmd=='partager':
        # 0.6.13 : même format que valider_base, refusé en amont.
        # 0.7.4 (décision 2) : chaque consultation s'inscrit au registre, datée, sans réécriture : un
        # identifiant essayé puis abandonné y reste visible. Le registre est un fichier de l'utilisateur
        # (dossier courant), pas du skill : `assets/` est remplacé à chaque installation.
        d_=a.date or datetime.date.today().isoformat();date_iso(d_)
        exiger(jour(d_)<=jour(datetime.date.today().isoformat()),'partager : --date ne peut pas être future')
        reg=lire_registre(a.registre);nouv=[]
        for ident in a.ids:
            exiger(re.fullmatch(r'C-\d{4}-S(?:0[1-9]|[1-9]\d)',ident) is not None,f'partager : identifiant C-NNNN-SNN attendu, reçu « {ident} »')
            if ident in reg:
                print(f"{ident} → {reg[ident]['usage']} · fixé le {reg[ident]['date']} (déjà au registre, inchangé)")
            else:
                r_={'id':ident,'usage':usage_attendu(ident),'date':d_};reg[ident]=r_;nouv.append(r_)
                print(f"{ident} → {r_['usage']} · fixé le {d_} · usage_fige_le à recopier dans la fiche")
        if nouv:
            with open(a.registre,'a',encoding='utf-8') as f:
                for r_ in nouv:f.write(json.dumps(r_,ensure_ascii=False)+'\n')
            print(f'registre : {a.registre} ({len(nouv)} ligne(s) ajoutée(s)) ; le publier (dépôt daté) pour prouver la date')
        return
    if a.cmd=='equivalences':
        # 0.6.13 : table lisible, ou JSON (--json), au lieu de tuples Python.
        ab=carte_id(a.carte);rows=[]
        for s in range(1,NS+1):
            m=marqueur_local(ab,s);rows.append({'strate':s,'equivalent':m[0] if m else None,'marqueur':m[1] if m else None,'statut':m[2] if m else None})
        if a.json:print(json.dumps({'carte':NOMS[ab],'equivalents':rows},ensure_ascii=False,indent=2));return
        print(f'{NOMS[ab]} — équivalents locaux (statut, marqueur)')
        for r in rows:print(f"  {r['strate']:>2} · {r['statut'] or '—'} · {r['equivalent'] or '—'} — {r['marqueur'] or '—'}")
        return
    if a.cmd=='scorer':print(scorer(a.fichier,a.csv));return
    if a.cmd=='sceller-jugement':
        proba(a.p,'--p');date_iso(a.date)
        # 0.6.13 : l'outil qui fabrique la preuve refuse en amont ce que le journal refuserait.
        if a.origine=='moteur':evenement_lire(a.evenement)
        else:texte_requis(a.evenement,'--evenement')
        exiger(jour(a.date)<=datetime.date.today().toordinal(),f'--date {a.date} postérieure à aujourd’hui : on scelle un jugement déjà formé')
        print(json.dumps({'probabilite_jugement':a.p,'jugement_scelle':empreinte_jugement(a.question,a.evenement,a.p,a.date),
                          'question':a.question,'evenement':a.evenement,
                          'date_information':a.date,'scelle_le_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
                          'instruction':'Recopier ces champs dans la ligne de prévision (question et événement mot pour mot : le sceau en dépend, 0.7.45), puis seulement lancer le moteur. '
                                        '--date est la date d’information (champ « date » du journal), pas le jour du scellement ; '
                                        'scelle_le_utc dit quand le sceau a été produit.'},ensure_ascii=False));return
    if a.cmd=='sceller-comparateur':
        evenement_lire(a.evenement)
        c={'methode':a.methode,'probabilite':a.p,'scelle_le':a.date,'source':a.source,'aveugle':a.aveugle,
           'elements_vus':a.vu,'contexte':a.contexte}
        c['empreinte']=empreinte_comparateur(a.question,a.evenement,a.p,a.date,a.source,a.methode)
        errs=erreurs_comparateur(c,a.question,a.evenement);exiger(not errs,' ; '.join(errs))
        print(json.dumps({'comparateur_externe':c,'contamine':comparateur_contamine(c),
                          'instruction':'Recopier ce champ dans la ligne de prévision, puis seulement lancer le moteur. '
                                        'Un bras non aveugle ou produit dans la même session que la lecture est publié, mais exclu du rapport.'},ensure_ascii=False));return
    if a.cmd=='export-codeur':
        cas=next((c for c in charger(a.base) if c.get('id')==a.cas),None);exiger(cas is not None,f'export-codeur : {a.cas} absent de {a.base}')
        print(json.dumps(export_codeur(cas),ensure_ascii=False,indent=2));return
    if a.cmd=='conservativite':
        base_=charger(a.base);valider_base(base_);r=cloture(base_)
        if a.sortie:Path(a.sortie).write_text(json.dumps(r,ensure_ascii=False,indent=1)+'\n',encoding='utf-8')
        print(f"clôture {r['version']} : {r['consequences']} conséquences sur {r['etats']} états, {r['desarmes']} désarmées"
              f"{'' if r['probant'] else ' — plus de la moitié : la clôture n’établit rien'} · empreinte {r['empreinte']}")
        print('hors clôture : '+' ; '.join(r['hors_cloture']))
        print(f"empreinte portable (flottants à 10 décimales, pour comparer deux plateformes) : {r['empreinte_portable']}")
        if a.contre:
            cmp_=comparer_clotures(lire_json(a.contre,'--contre'),r)
            print(f"contre {a.contre} : {cmp_['changees']} conséquence(s) changée(s) sur {cmp_['communes']} communes ; "
                  f"{cmp_['seulement_avant']} seulement avant, {cmp_['seulement_apres']} seulement après · "
                  +('extension conservatrice' if cmp_['conservative'] else 'NON conservatrice')
                  +('' if cmp_['conservative'] else f" ; {cmp_['changees_hors_arrondi']} au-delà de 10 décimales"))
            for k_ in cmp_['exemples']:print('  changée : '+k_)
            if not cmp_['conservative']:raise SystemExit(1)
        if a.empreinte:
            ok_=a.empreinte.strip().lower()==r['empreinte']
            print('empreinte attendue : '+('identique' if ok_ else 'DIFFÉRENTE'))
            if not ok_:raise SystemExit(1)
        return
    if a.cmd=='squelette':
        print(json.dumps(squelette_prevision(lire_json(a.calcul,'--calcul'),a.id),ensure_ascii=False));return
    if a.cmd in ('fiche-test','fiche-resultat'):
        data=charger(a.journal);valider_journal(data)
        pr_=[x for x in data if x.get('type')=='prevision' and x.get('id')==a.id];exiger(pr_,f'prévision {a.id} absente du journal')
        print(fiche_test(pr_[0]) if a.cmd=='fiche-test' else fiche_resultat(pr_[0],a.issue,a.preuve,a.date,a.note,a.source_utilisee,a.source_conforme=='oui',a.mode,a.ecart_source));return
    if a.cmd=='ingerer':
        r=ingerer(lire_texte(a.registre,'registre'))
        if a.journal_sortie:
            with open(a.journal_sortie,'w',encoding='utf-8',newline='\n') as f_:
                for x in r['journal']:f_.write(json.dumps(x,ensure_ascii=False,sort_keys=True)+'\n')
        s=r['score']
        if a.json:print(json.dumps({k:v for k,v in r.items() if k!='journal'},ensure_ascii=False,indent=2));return
        print(f"Registre : {r['previsions']} prévision(s), {r['resultats']} résultat(s), {len(r['en_attente'])} en attente · empreintes vérifiées")
        print(f"Questions résolues {s['questions_resolues']} · éligibles V4 {s['questions_eligibles']} · statut : {s['statut']}")
        cv=s.get('couverture') or {}
        if cv.get('brier_avec_repli') is not None:print(f"Brier avec repli {cv['brier_avec_repli']:.3f} · taux de repli {cv['taux_de_repli']:.0%}")
        ve_=s.get('vue_exterieure')
        if ve_:print(f"Vue extérieure ({ve_['questions']} question(s), descriptif) : Brier {ve_['brier_vue_exterieure']:.4f} · moteur {ve_['brier_moteur']:.4f}"
                     +('' if ve_['brier_sans_cartes'] is None else f" · sans cartes {ve_['brier_sans_cartes']:.4f}"))
        if ve_ and ve_.get('brier_vue_alternative') is not None:
            print(f"Classe alternative ({ve_['questions_avec_alternative']} question(s)) : Brier {ve_['brier_vue_alternative']:.4f} · moteur sur ces questions {ve_['brier_moteur_sur_alternative']:.4f}")
        rr_=s.get('registre_regressif')
        if rr_:print(f"Tests régressifs : {rr_['questions']} ({rr_['aveugles']} à l’aveugle, {rr_['rejeux']} rejoué(s)) · Brier moyen : "
                     +' · '.join(f"{k.replace('_',' ')} {v:.4f}" for k,v in rr_['brier'].items() if v is not None))
        mj_=s.get('moteur_contre_jugement')
        if mj_:print(f"Moteur contre jugement scellé ({mj_['questions']} question(s), toutes lignes) : Brier moteur {mj_['brier_moteur']:.4f} · jugement {mj_['brier_jugement']:.4f}")
        rq_=s.get('resolutions') or {}
        if rq_.get('resolues'):print(f"Résolutions : {rq_['positives']} positive(s), {rq_['par_absence']} par absence, {rq_['hors_source_du_dossier']} hors source du dossier, "
                                    f"{rq_['non_renseignees']} non renseignée(s)"+(f" · fragiles : {', '.join(rq_['ids_fragiles'])}" if rq_['ids_fragiles'] else ''))
        for d_ in s.get('episodes_suspects') or []:
            print(f"! Même événement ({d_['evenement']}), fenêtres qui se chevauchent, épisodes différents ({' / '.join(d_['episodes'])}) : "
                  f"{' et '.join(d_['ids'])} compteraient en V4 comme deux épisodes indépendants ; unifier episode_id s’il s’agit du même")
        print('! Un registre d’auteur sans prépublication publique reste hors V4 ; il documente, il ne valide pas.');return
    if a.cmd=='depouiller':
        r=depouiller(charger(a.premier),charger(a.second))
        if a.json:print(json.dumps(r,ensure_ascii=False,indent=2));return
        g=r['groupe'];print(f"Dépouillement · {r['cas']} cas · {r['etats']} états · groupé : PABAK {g['pabak']:.3f} "
              f"[{g['pabak_intervalle_95_approche'][0]:.3f} ; {g['pabak_intervalle_95_approche'][1]:.3f}] · verdict {g['verdict']}")
        for c,v in sorted(r['par_carte'].items()):print(f"  {NOMS[c]} : a={v['table']['a']} b={v['table']['b']} c={v['table']['c']} · PABAK {v['pabak']:.3f} · {v['verdict']}")
        if r['cartes_sans_ancrage']:print('  sans ancrage chez aucun codeur : '+', '.join(r['cartes_sans_ancrage']))
        print('! '+r['lecture']);return
    if a.cmd=='recolter':
        chemin=Path(a.carnet)
        if a.jusqu_au:
            date_iso(a.jusqu_au);faits=[x for x in (charger(chemin) if chemin.exists() else []) if jour(x['disponible_le'])<=jour(a.jusqu_au)]
            print(json.dumps({'date_information':a.jusqu_au,'faits':faits,
                'sans_archive':sorted(x['id'] for x in faits if not x.get('archive')),
                'lecture':'brouillon : faits disponibles à la date ; carte, strate, force, objet et passage restent à coder dans le dossier ; '
                          'en test régressif, un fait sans archive repose sur une page lue en direct, exposée aux fuites (validation.md §26)'},
                ensure_ascii=False,indent=2));return
        x=recolter_ligne(a.fait,a.source,a.source_url,a.date,a.disponible_le,a.date_consultation,a.classe_source,a.fiabilite,a.credibilite,
                         a.independance_critere,a.independance_motif,a.archive)
        anciens=charger(chemin) if chemin.exists() else []
        exiger(all(y.get('id')!=x['id'] for y in anciens),f"recolter : fait déjà au carnet ({x['id']})")
        with open(chemin,'a',encoding='utf-8',newline='\n') as f_:f_.write(json.dumps(x,ensure_ascii=False,sort_keys=True)+'\n')
        print(f"carnet {chemin.name} : {x['id']} ajouté · {len(anciens)+1} fait(s)");return
    if a.cmd=='accord':
        r=accord(a.a,a.b,a.c,a.d,a.repetabilite,a.ecart_jours,a.llm)
        if a.llm and not a.json:print('répétabilité d’un modèle : deux exécutions en contextes séparés (fiabilité, pas validité)')
        if a.json:print(json.dumps(r,ensure_ascii=False,indent=2));return
        if a.repetabilite:print(f"répétabilité : même codeur, deux passes séparées de {a.ecart_jours} j (manque du second = manque de la seconde passe)")
        f_=lambda v:'indéfini' if v is None else f'{v:.3f}'
        print(f"table a={a.a} b={a.b} c={a.c} d={a.d} · prévalence {r['prevalence']*100:.1f} % · pₒ {r['po']:.3f} · κ {f_(r['kappa'])} · PABAK {r['pabak']:.3f} · "
              f"accord positif {f_(r['accord_positif'])} · manque du second {f_(r['manque_second'])} · manque du premier {f_(r['manque_premier'])}")
        pi_=r['pabak_intervalle_95_approche'];print(f"PABAK, intervalle à 95 % (approché, décisions non indépendantes) : [{pi_[0]:.3f} ; {pi_[1]:.3f}] sur {r['n']} décisions")
        print(f"π de Scott {f_(r['pi_scott'])} · α de Krippendorff {f_(r['alpha_krippendorff'])} · pₑ {r['pe']:.3f}"
              +(f" · manque des absences {f_(r['manque_absence_second'])} / {f_(r['manque_absence_premier'])}" if r['prevalence']>.5 else ''))
        print('verdict : '+r['verdict']);return
    if a.cmd=='rejets':
        d_=lire_json(a.dossier,'--dossier')
        if a.audit:
            errs=erreurs_audit_rejets(lire_json(a.audit,'--audit'),d_);exiger(not errs,' ; '.join(errs))
            au=lire_json(a.audit,'--audit');print(f"audit conforme · {len(au['verdicts'])} rejet(s) relu(s) · taux d’annulation {au['taux_annulation']*100:.0f} %");return
        print(json.dumps(feuille_rejets(d_),ensure_ascii=False,indent=2));return
    if a.cmd=='valider-references':
        refs=lire_json(a.fichier,'fichier de références')
        exiger(isinstance(refs,dict),'références : objet indexé par événement requis')
        errs=erreurs_references(refs)
        for event,r in refs.items():
            try:
                exiger(isinstance(r,dict),f'{event} : référence invalide');proba(r.get('frequence'),event)
                for k in ('source','definition','periode','fenetre','disponible_le'):texte_requis(r.get(k),f'{event}.{k}')
                duree_jours(r['fenetre']);date_iso(r['disponible_le'])
                key,typ=event.split(' ',1);cle_valide(key)
                exiger(typ in ('apparait','persiste','disparait','hausse|persiste','transformation|persiste'),f'{event} : type de référence inconnu')
            except (ValueError,IndexError) as e:errs.append(str(e))
        exiger(not errs,' ; '.join(errs))
        print(f'{len(refs)} référence(s) conformes en forme : six champs, fréquence dans ]0 ; 1[, fenêtre, date, clé, ni gabarit ni classe tautologique ; '
              'la vérité de la source reste à vérifier par un humain');return
    if a.cmd=='sceller':
        data=charger(a.fichier);valider_journal(data)
        predictions=[x for x in data if x['type']=='prevision']
        now=datetime.date.today()
        exiger(predictions,'aucune prévision à sceller')
        exiger(all(date_iso(x['echeance'])>now for x in predictions),'scellement prospectif impossible : échéance atteinte')
        print(json.dumps({'sha256':fichier_sha(a.fichier),'previsions_sha256':empreinte([empreinte_prevision(p) for p in predictions]),'empreintes_previsions':{p['id']:empreinte_prevision(p) for p in predictions},'date_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
                          'instruction':'Publier cette empreinte avant échéance ; conserver le fichier exact. La date locale seule ne prouve pas la prépublication.'},ensure_ascii=False));return
    base=charger(a.base);summary=valider_base(base)
    exiger(a.demo or not any(c.get('fictif') and c.get('statut_donnees')=='actif' for c in base),'base fictive : --demo obligatoire ; chiffres interdits en prévision réelle')
    etat=lire_etat(a.etat);asof=a.date_information or etat['date'];date_iso(asof)
    exiger(jour(asof)>=jour(etat['date']),'date d’information antérieure à l’état')
    exiger(type(a.pas) is int and 1<=a.pas<=P['pas_max'],f'pas entre 1 et {P["pas_max"]}')
    end=fin_fenetre(etat['date'],etat['fenetre'],a.pas).isoformat()
    if a.echeance:exiger(date_iso(a.echeance).isoformat()==end,'échéance différente de date état + pas × fenêtre')
    exiger(jour(asof)<jour(end),'date d’information à l’échéance ou après : le calcul serait rétrospectif. '
           'Donner une date d’information antérieure à l’échéance ; un cas déjà survenu se code (mode CODER), il ne se prévoit pas')
    st=statuts()
    for m in etat['mots']:
        exiger(m['i']!='F' or st.get((m['c'],m['s']))!='Vide',f'{cle(m)} : F impossible sur un équivalent Vide (A3)')
        exiger(st.get((m['c'],m['s']))!='Hors domaine',f'{cle(m)} : carte Hors domaine dans cette strate, aucun ancrage possible (A3)')
    active=base_active(base,asof,a.demo)
    # 0.7.34 (décision d'auteur, L7) : hors démonstration, la prévision chiffrée est limitée aux strates de
    # strates_prevision (la strate 7 : 13 équivalents sur 16 sourcés) tant qu'aucune autre n'a d'accord mesuré.
    # 0.7.52 (décision d'auteur, §29) : --exploratoire lève L7 pour ce calcul seul. Le chiffre est marqué, n'est pas
    # écrit au journal prospectif et ne compte jamais dans la condition 1 du §27.
    explo=bool(getattr(a,'exploratoire',False))
    exiger(not (explo and getattr(a,'journal',None)),'--exploratoire : pas de --journal (le chiffre exploratoire ne va pas au journal prospectif, §29)')
    exiger(not (explo and a.demo),'--exploratoire et --demo sont exclusifs (§29)')
    if not a.demo and not explo:
        evs_cli=[a.evenement] if isinstance(getattr(a,'evenement',None),str) else list(getattr(a,'evenement',None) or [])
        sts_=[int(k.split('@')[1].split()[0]) for k in evs_cli if '@' in k and k.split('@')[1].split()[0].isdigit()]
        if a.cmd=='trajectoires':sts_+=[int(x) for x in a.strates.split(',') if x.strip().isdigit()]
        exiger(all(s_ in P['strates_prevision'] for s_ in sts_),
               f"prévision chiffrée limitée aux strates {P['strates_prevision']} (décision L7, 0.7.34) ; les autres strates se lisent (mode LIRE) sans chiffre")
    refs=lire_json(a.references,'--references') if a.references else {}
    if a.fref is not None:
        proba(a.fref,'fref');exiger(a.cmd=='calculer','--fref scalaire interdit pour plusieurs événements ; utiliser --references')
        cible,typ=evenement_lire(a.evenement)
        exiger(typ in ('apparait','persiste','disparait'),'événement composé : fournir des références séparées dans --references')
        for name in ('source_ref','periode_ref','disponible_ref','definition_ref'):texte_requis(getattr(a,name),'--'+name.replace('_','-'))
        exiger(cible+' '+typ not in refs,'référence fournie deux fois')
        # 0.7.39 (test régressif, série 2, défaut 3) : la définition était le nom de l'événement (« SEUIL@7 apparait »),
        # que le contrôle de classe tautologique (0.7.8) refusait toujours : --fref était un chemin mort, et le refus
        # d'une échéance programmée conseillait pourtant --fref. La classe se déclare désormais, dans les mots de la source.
        refs[cible+' '+typ]={'frequence':a.fref,'source':a.source_ref,'definition':a.definition_ref,'periode':a.periode_ref,'fenetre':etat['fenetre'],'disponible_le':a.disponible_ref}
    refs_valider(refs,etat['fenetre'],asof)
    for key in list(refs):
        # Keys are canonical abbreviations; reject aliases instead of silently missing a supplied reference.
        k,t=key.split(' ',1);exiger(k==cle_valide(k),f'référence : employer la clé canonique {cle_valide(k)} {t}')
    links=lire_liaisons(a.liaison,etat);bouge=[cle_valide(x) for x in a.bouge];manque=[cle_valide(x) for x in a.manque]
    if bouge or manque:
        exiger(len(etat['mots'])>=3,'positions : au moins trois mots ancrés requis')
        exiger(all(x in forces(etat) for x in bouge) and all(x not in forces(etat) for x in manque),'positions incompatibles avec l’état')
    exiger(all(x.isdigit() and 1<=int(x)<=NS for x in a.ctr_materielle),'strate de contrainte matérielle invalide')
    opts=dict(liaisons=links,bouge=bouge,manque=manque,refs=refs,ctr_materielle=a.ctr_materielle,asof=asof,sans_cartes=a.sans_cartes)
    if a.cmd=='sonde':
        cible,typ=evenement_lire(a.evenement)
        exiger(typ in ('apparait','persiste','disparait'),'sonde : événement simple seulement')
        sem=a.semantique or ('continue' if typ=='persiste' else 'au-moins-une-fois' if typ=='disparait' else 'presence')
        r=sonde_matrice(etat,typ,cible,active,dict(opts,sans_cartes=False),a.pas,sem,a.tirage,a.tirages)
        r['contexte']=metadata(base,asof,a.demo)
        if a.json:print(json.dumps(r,ensure_ascii=False,indent=2));return
        print(f"Sonde « {a.tirage} » · {r['tirages']} tirages · graine {r['graine']} · {cible} {typ}")
        print(f"p réel {pct(r['p_reel'])} · sans multiplicateurs (cas gardés) {pct(r['p_sans_multiplicateurs'])} · sans cartes {pct(r['p_sans_cartes'])}")
        print(f"p sonde : médiane {pct(r['p_sonde_mediane'])}, 90 % des tirages {pct(r['p_sonde_90'][0],False)}–{pct(r['p_sonde_90'][1])} ; "
              f"{round(100*r['part_sans_effet'])} % des tirages sans aucun multiplicateur")
        print(r['lecture']+f" ; révision par les cas : {r['apport_cas']*100:+.1f} points".replace('.',','))
        print('! Base fictive : la sonde décrit la mécanique du calcul, pas la valeur de la matrice. Un seul événement, un seul état.' if a.demo else
              '! Un seul événement, un seul état : répéter sur plusieurs cibles avant toute conclusion sur la matrice.')
        return
    if a.cmd=='attribuer':
        exiger(a.pas==1 and not (links or bouge or manque) and not a.sans_cartes,'attribuer : un pas, sans liaisons, positions ni --sans-cartes')
        exiger(a.temporalite=='generique','attribuer : --temporalite generique')
        cible,typ=evenement_lire(a.evenement)
        exiger(typ in ('apparait','persiste','disparait'),'attribuer : événement simple seulement')
        r=attribuer(etat,typ,cible,active,refs,asof);r['contexte']=metadata(base,asof,a.demo)
        if a.json:print(json.dumps(r,ensure_ascii=False,indent=2));return
        print(f"Attribution dans le moteur · {r['evenement']} · {r['calculs']} calculs · p complet {pct(r['p_complet'])} · sans ces mots {pct(r['p_vide'])}")
        for k_,s_ in sorted(r['shapley_points'].items(),key=lambda x:-abs(x[1])):print(f"  {k_} : {s_*100:+.2f} points (Shapley)".replace('.',','))
        for x in r['interactions'][:10]:print(f"  {x['paire'][0]} × {x['paire'][1]} : interaction {x['interaction_logit']:+.3f} en logit · {x['forme']}".replace('.',','))
        print('! '+r['lecture'])
        return
    if a.cmd=='noyau':
        exiger(a.pas==1,'noyau : un pas (frontière jointe d’un pas ; plusieurs pas : version ultérieure)')
        exiger(a.temporalite=='generique','noyau : --temporalite generique (les événements programmés ou à durée de vie propre se calculent un par un)')
        evs_=[];ps_=[]
        for ev_ in a.evenement:
            cible_,typ_=evenement_lire(ev_);exiger(typ_ in ('apparait','persiste','disparait'),'noyau : événements simples seulement')
            exiger(cible_ not in [x.split()[0] for x in evs_],f'noyau : {cible_} figure deux fois (un événement par mot)')
            sem_='continue' if typ_=='persiste' else 'au-moins-une-fois' if typ_=='disparait' else 'presence'
            ps_.append(horizon_result(etat,typ_,cible_,active,opts,1,sem_)['p']);evs_.append(f'{cible_} {typ_}')
        exs_=[]
        for x_ in a.exclusion:
            pa_=[y.strip() for y in x_.split(';')];exiger(len(pa_)==2,'--exclusion « E1 ; E2 »')
            pa_=[' '.join(evenement_lire(y)) for y in pa_];exiger(all(y in evs_ for y in pa_),'--exclusion : événements de la frontière seulement')
            exs_.append(tuple(pa_))
        r=noyau_joint(evs_,ps_,exs_);r['contexte']=metadata(base,asof,a.demo)
        if a.json:print(json.dumps(r,ensure_ascii=False,indent=2));return
        print('Noyau joint d’un pas · '+str(len(evs_))+' événements · marginales = calculer'+('' if r['faisable'] else ' · NON FAISABLE : exclusions incompatibles avec les marginales'))
        for ev_,pp in zip(evs_,ps_):print(f"  {ev_} : à l’échéance {pct(pp)} · premier changement {pct(r['p_premier'][ev_])}")
        print(f"Aucun {pct(r['p_aucun'])} · exactement un {pct(r['p_exactement_un'])} · deux ou plus {pct(r['p_deux_ou_plus'])}")
        for c_,v_ in r['configurations'][:12]:print(f"  {pct(v_)} · {c_}")
        print('! '+r['hypothese'])
        return
    if a.cmd=='trajectoires':
        # 0.6.11 : l'option était acceptée et sans effet. Les trajectoires reposent sur les taux génériques
        # de toutes les cartes à la fois ; une échéance programmée ou une durée de vie propre ne s'y déclare pas.
        exiger(getattr(a,'temporalite',None) in (None,'generique'),
               'trajectoires : --temporalite programmee ou duree_de_vie refusée ; les trajectoires reposent sur les taux génériques de toutes les cartes. Utiliser calculer, événement par événement, avec une référence de domaine')
        exiger(not a.sans_cartes,'trajectoires : comparaison sans cartes disponible via calculer')
        brut=[x.strip() for x in a.strates.split(',') if x.strip()]
        exiger(all(x.isdigit() for x in brut),f'--strates : numéros de strate séparés par des virgules (ex. 8,11), reçu « {a.strates} »')
        sup=[int(x) for x in brut];result=trajectoires(etat,a.pas,active,opts,sup)
    else:
        # 0.6.12 : la temporalité n'a plus de défaut. Un oubli faisait retomber sur l'inertie générique
        # (Polo : 96,75 %) ; la question se pose donc avant tout calcul.
        exiger(a.temporalite is not None,
               '--temporalite requis. Avant de calculer, répondre à cette question : l’événement est-il fixé par '
               'un calendrier (scrutin, proclamation, échéance légale) → programmee ; ou le phénomène a-t-il '
               'une durée de vie propre, sans rapport avec trois mois (cyclone, grève, session) → duree_de_vie ; '
               'sinon → generique')
        # 0.7.39 (décision d'auteur, série 2 de tests régressifs, défaut 6) : sans dossier, un état codé de mémoire, faux
        # (T1 : une frappe déjà survenue en juin), passait avec des mots en F et un simple avertissement. Hors
        # démonstration, le calcul exige désormais le dossier de lecture : vue extérieure, pièces datées, source de résolution.
        exiger(a.demo or a.dossier,'calculer hors --demo : --dossier D.json requis (dossier de lecture scellé avant le calcul : '
               'faits datés et sourcés, vue extérieure, source de résolution ; modèle assets/dossier.exemple.json, '
               'contrôle par « moteur.py dossier --fichier D.json »)')
        cible,typ=evenement_lire(a.evenement)
        dossier=None;sem=None
        if a.dossier:
            # 0.7.3 : le dossier fige la lecture et la définition de l'événement avant le chiffre,
            # comme `sceller-jugement` fige le jugement. Un dossier ne vaut que pour son état.
            dd=lire_json(a.dossier,'--dossier');dossier=dossier_valider(dd)
            exiger(' '.join(str(dd.get('etat','')).split())==' '.join(a.etat.split()),
                   '--dossier : l’état du dossier diffère de --etat ; un dossier ne vaut que pour l’état qu’il documente')
            # 0.7.3 : sans événements déclarés, tout événement passait et la sortie annonçait pourtant la
            # définition contrôlée ; et des preuves postérieures à la date d'information étaient admises.
            exiger(bool(dossier['evenements']),'--dossier : dossier.evenements requis pour un calcul (la définition de l’événement précède le chiffre)')
            exiger(jour(dossier['disponible_le'])<=jour(asof),
                   f'--dossier : pièces disponibles le {dossier["disponible_le"]}, après la date d’information {asof} (B1)')
            if dossier['evenements']:
                exiger(any(evenement_lire(x['evenement'])==(cible,typ) for x in dossier['evenements']),
                       f'--dossier : « {cible} {typ} » n’est pas déclaré dans dossier.evenements ; '
                       'la définition de l’événement précède le chiffre, sinon elle peut suivre le résultat')
        exiger(typ not in ('renforce','affaiblit'),'f ↔ F est une révision de confiance, pas un événement physique ; utiliser s’intensifie avec une mesure ou reformuler le critère observable')
        if typ in ('intensifie','transforme'):
            exiger(a.pas==1,'événements composés : --pas > 1 non pris en charge')
            res=lire_json(a.resolution,'--resolution') if a.resolution else None
            result=compose(etat,typ,cible,active,opts,res)
            if dossier and dossier['evenements']:
                decl=next(x for x in dossier['evenements'] if evenement_lire(x['evenement'])==(cible,typ))
                exiger(decl['temporalite']==a.temporalite,f'--dossier : temporalité « {a.temporalite} » différente du dossier (« {decl["temporalite"]} »)')
        else:
            sem=a.semantique or ('continue' if typ=='persiste' else 'au-moins-une-fois' if typ=='disparait' else 'presence')
            if dossier and dossier['evenements']:
                decl=next(x for x in dossier['evenements'] if evenement_lire(x['evenement'])==(cible,typ))
                exiger(decl['semantique']==sem,f'--dossier : sémantique « {sem} » différente du dossier (« {decl["semantique"]} »)')
                exiger(decl['temporalite']==a.temporalite,f'--dossier : temporalité « {a.temporalite} » différente du dossier (« {decl["temporalite"]} »)')
            result=horizon_result(etat,typ,cible,active,dict(opts,placebo=True),a.pas,sem)
            pl_=result.get('placebo')
            result['p_placebo']=pl_['p'] if pl_ else None
            is_=result.get('inertie_strate');result['p_inertie_strate']=is_['p'] if is_ else None
            result['graine_placebo']=pl_['graine'] if pl_ else None
            result['apport_homologie']=None if pl_ is None or result.get('p') is None else result['p']-pl_['p']
            # 0.7.12 (audit V34, D5) : un p dans la plage à 90 % du placebo est indiscernable d'une sélection de cas
            # au hasard. Constat publié et drapeau ; ρ, qui dit la provenance et non la fiabilité, est inchangé.
            pg_=(pl_ or {}).get('plage_90')
            result['homologie_discernable']=None if not pg_ or result.get('p') is None else not (pg_[0]<=result['p']<=pg_[1])
            # 0.7.18 : le drapeau est un tricolore ; le centile dit où p se situe parmi les tirages (comparable et agrégeable).
            result['centile_placebo']=(pl_ or {}).get('centile_reel')
            if result['homologie_discernable'] is False:
                result.setdefault('drapeaux',[]).append(f"Homologie indiscernable du hasard : p ({pct(result['p'])}) dans la plage à 90 % du placebo "
                    f"({pct(pg_[0],False)}–{pct(pg_[1])}) ; la sélection des homologues ne fait pas mieux que des cas tirés au hasard dans la strate.")
            if not a.sans_cartes:
                # Comparateur inertiel : même calcul sans cartes (inertie, fréquences, références seules).
                # Sans lui, un bon Brier peut ne venir que du statu quo (exemple 11).
                nu=horizon_result(etat,typ,cible,active,dict(opts,sans_cartes=True),a.pas,sem)
                result['p_sans_cartes']=nu['p'];result['apport_cartes']=result['p']-nu['p']
                # 0.7.12 (audit V34, D7) : sans cas réel actif, aucune arête n'est éprouvée (P8) ; la paire
                # (sans cartes, avec cartes) est le résultat à lire, p seul en est dérivé. Aucun calcul ne change.
                if not any(not c.get('fictif') for c in active) and result.get('p') is not None and nu.get('p') is not None:
                    result['resultat_principal']={'p_sans_cartes':nu['p'],'p_avec_cartes':result['p'],
                        'motif':'aucun cas réel actif : arêtes non éprouvées (P8) ; lire l’écart, pas p seul'}
                # 0.7.12 (audit V34, D6) : l'horizon est le levier le plus fort ; p à 1, 3 et 6 pas, même sémantique,
                # sans placebo. Ce n'est pas une incertitude (l'horizon est la question), c'est ce qu'il faut voir.
                bh={}
                for h_ in (1,3,6):
                    if h_>P['pas_max']:continue
                    try:
                        bh[str(h_)]={'p':horizon_result(etat,typ,cible,active,opts,h_,sem)['p'],
                                     'p_sans_cartes':horizon_result(etat,typ,cible,active,dict(opts,sans_cartes=True),h_,sem)['p']}
                    except ValueError:bh[str(h_)]=None
                # 0.7.13 (audit comparatif, point 2) : un mot f a le même effet numérique qu'un mot F (λ vient de la
                # matrice). Plutôt qu'un poids arbitraire, on explore les codages plausibles : chaque mot f retiré,
                # puis tous ; même question, même horizon. Aucun p publié ne change.
                fs=[cle(m_) for m_ in etat['mots'] if m_['i']=='f' and cle(m_)!=cible]
                vc=[]
                for k_ in fs:
                    try:vc.append({'retire':[k_],'p':horizon_result(appliquer(etat,'disparait',k_),typ,cible,active,opts,a.pas,sem)['p']})
                    except ValueError:pass
                if len(fs)>1:
                    e_=etat
                    for k_ in fs:e_=appliquer(e_,'disparait',k_)
                    try:vc.append({'retire':fs,'p':horizon_result(e_,typ,cible,active,opts,a.pas,sem)['p']})
                    except ValueError:pass
                ps_=[x['p'] for x in vc if x['p'] is not None]
                result['variantes_codage']=None if not fs else {'mots_f':fs,'variantes':vc,
                    'plage':None if not ps_ else [min(ps_+[result['p']]),max(ps_+[result['p']])],
                    'lecture':'un mot f est un ancrage incertain : p si chaque mot f, puis tous, étaient absents'}
                result['modele']=modele_declare(result,typ,sem,links)
                if result['modele']['liaisons_non_inferentielles']:
                    result.setdefault('drapeaux',[]).append('Liaisons sans effet sur p : '+', '.join(result['modele']['liaisons_non_inferentielles'])
                        +' (seules transfert, inclusion et renforcement entrent dans le calcul) ; elles restent une lecture.')
                result['bande_horizon']={'pas':bh,'fenetre':etat['fenetre'],'semantique':sem,
                                         'lecture':'même question à 1, 3 et 6 fenêtres : l’horizon choisi change p plus que les variantes de modèle'}
                pieces=None
                if dossier:
                    pieces={}
                    for it_ in dd.get('mots') or []:
                        ps_=it_.get('passage');ps_=ps_ if isinstance(ps_,list) else [ps_] if ps_ else []
                        pieces[cle_valide(f"{it_.get('carte')}@{it_.get('strate')}")]={'corroboration':it_.get('corroboration'),
                            'passage':'soutient' if any(isinstance(x,dict) and x.get('relation')=='soutient' for x in ps_) else 'partiel'}
                result['sensibilite']=sensibilite(etat,typ,cible,active,opts,a.pas,sem,pieces)
        result['echeance']=end;result['journal']=a.journal;result['etat']=a.etat
        if result.get('p') is not None:
            iv_=result.get('intervalle') or [None,None]
            result['bande_verbale']={'p':bande_verbale(result['p']),'intervalle':[bande_verbale(iv_[0]),bande_verbale(iv_[1])],
                'lecture':'échelle de probabilité en sept bandes (ODNI 203) ; une fréquence conditionnelle, pas une certitude'}
        if dossier and not dossier['complet']:
            result.setdefault('drapeaux',[]).append('Dossier incomplet (plancher A7) : '+' ; '.join(dossier['manques'][:4])
                +(f' (+{len(dossier["manques"])-4})' if len(dossier['manques'])>4 else '')+' → statut de lecture Spéculatif, à reporter dans « À vérifier ».')
        if dossier:result['dossier']={'sceau':dossier['sceau'],'candidats':dossier['candidats'],'complet':dossier['complet'],'manques':dossier['manques'],
                                      'contre_candidate':dossier['contre_candidate'],'controle':'forme de A1–A7, passages et questions contrôlée avant calcul (pas leur justesse)'}
        if a.semantique is None and sem is not None:
            result.setdefault('drapeaux',[]).append(f'Sémantique non déclarée : « {sem} » appliqué par défaut. '
                                                   'À déclarer par --semantique (présence finale, au moins une fois, persistance continue).')
        if a.date_information is None:
            result.setdefault('drapeaux',[]).append(f'Date d’information non déclarée : date de l’état ({asof}) appliquée. '
                                                   'Les cas disponibles après cette date sont exclus du calcul.')
        for k_ in ('p_placebo','graine_placebo','apport_homologie','p_inertie_strate'):result.setdefault(k_,None)   # composés : null
        result=appliquer_temporalite(result,a.temporalite)
        if typ in ('persiste','disparait'):result=appliquer_inertie_objet(result,typ,cible,a.demo)
        # 0.7.42 (test T7) : la vue extérieure d'un composé (« s'intensifie », « se transforme ») n'était ni contrôlée ni
        # recopiée dans le calcul, donc ni dans `squelette` ni dans le score. Elle l'est pour tout événement déclaré.
        if dossier and dossier['evenements']:
            dcl_=next((x for x in dossier['evenements'] if evenement_lire(x['evenement'])==(cible,typ)),None)
            if dcl_:result=controle_vue_exterieure(result,dcl_.get('vue_exterieure'))
    if a.cmd=='calculer':
        ml=marqueur_local(*cible.split('@'))
        st_=statuts().get((cible.split('@')[0],int(cible.split('@')[1])))
        result['marqueur_local']=None if ml is None else {'equivalent':ml[0],'marqueur':ml[1],'statut':st_}
    if a.cmd=='calculer' and re.fullmatch(r'\d{4}-\d{2}',str(etat['date'])):
        # 0.7.40 (test T6, défaut 3) : une date d'état au mois se lit au 1er ; l'échéance le dit.
        result.setdefault('drapeaux',[]).insert(0,f"État daté au mois ({etat['date']}) : lu au 1er, échéance {end}. Pour une question qui court "
            f"jusqu’à une autre date, dater l’état au jour (ex. « [{asof} | {etat['fenetre']}] », à la date d’information).")
    if a.cmd=='calculer' and not a.dossier:
        result.setdefault('drapeaux',[]).append('Aucun dossier de lecture (--dossier) : A1, A3, A6, A7, questions et définition de '
                                               'l’événement ne sont pas contrôlés par le moteur pour ce calcul.')
    result['contexte']=metadata(base,asof,a.demo);result['base']=summary
    result['base']['cas_apprentissage_disponibles']=len(active)
    nv=[cle(m) for m in etat['mots'] if m['i']=='F' and st.get((m['c'],m['s'])) not in ('Attesté','Documenté')]
    if nv:result.setdefault('drapeaux',[]).append('Ancrage F sur équivalent non vérifié (Proposé) : '+', '.join(nv)+' — la lecture est tranchée, la correspondance reste à documenter (A3).')
    if a.demo:result.setdefault('drapeaux',[]).insert(0,'DÉMONSTRATION FICTIVE — ne constitue ni une prévision réelle ni une preuve de calibration.')
    if explo:
        result['exploratoire']=True;result['contexte']['exploratoire']=True
        result.setdefault('drapeaux',[]).insert(0,f"EXPLORATOIRE (§29) : L7 levée pour ce calcul seul, hors des strates {P['strates_prevision']} — "
                                                  'chiffre scellé pour mesure, à ne pas publier, compté à part du §27.')
    afficher(result,a.json)

# ───────────────────────── tests de régression intégrés ─────────────────────────

def autotest():
    import copy, unittest
    def fake_case(year=2020, count=1):
        cid=next(f'C-{i:04d}-S07' for i in range(9000,9999) if usage_attendu(f'C-{i:04d}-S07')=='apprentissage')
        states=[]
        for j in range(count+1):
            dt=fin_fenetre(f'{year}-01-01','3 mois',j).isoformat() if j else f'{year}-01-01'
            states.append({'date':dt,'disponible_le':dt,'etat':f'[{dt} | 3 mois] POLARITÉ@7[f]',
                           'mots':[{'carte':'POL','strate':7,'intensite':'f','fait':'deux camps observés',
                                    'source':'source de test fictive','contre_observation':'médiation observée, marginale','portee':'marginale','objet':'conflit-test','classe_source':'contemporain'}] if not j else None,
                           'retraits':[],'liaisons':[],'positions':None})
        states[0]['questions']=[{'question':'Une médiation impose-t-elle une règle commune ?','si_oui':'CTR@7','si_non':'POL@7',
                                 'resolution':'texte de la médiation publié au registre (fictif)',
                                 'justification':{'oui':'une règle commune retire des options aux deux camps','non':'sans règle, les deux camps restent seuls à se définir l’un par l’autre'}}]
        return {'id':cid,'version_regles':P['version'],'titre':'Cas technique fictif','strates':[7],'fenetre':'3 mois',
                'sequence':states[:-1],'issue':states[-1],'sans_evenement':True,'fictif':True,'statut_donnees':'actif',
                'codage':{'mode':'manuel','codeurs':[{'id':'codeur-1','role':'humain'}],'debut':'2026-01-01'},'usage':'apprentissage','usage_fige_le':'2026-01-01'}
    def forecast(ident='P-1',**kw):
        x={'type':'prevision','id':ident,'date':'2026-01-01','echeance':'2026-04-01','version_regles':P['version'],
           'question':'Une rupture survient-elle ?','evenement':'SEU@7 apparait','episode_id':'episode-A','pas':1,
           'indicateur_bascule':'rappel d’un ambassadeur','refutation':'aucune rupture','semantique':'presence',
           'etat_present':'[2026-01-01 | 3 mois] POLARITÉ@7[f]','probabilite':.2,'intervalle':None,'rho':'ρ4',
           'resolution':{'source':'registre public','critere':'rupture publiée','seuil':'une publication','marqueur':'rupture diplomatique','objet':'relation A-B'},
           'resolution_verifiee':True,'frequence_de_base':.3,'p_sans_cartes':None,'probabilite_jugement':None,'temporalite':'generique','rejeu':False,'fictif':True,'partition':None,
           'p_placebo':None,'graine_placebo':None,'apport_homologie':None,'comparateur_externe':None,
           'empreintes':None,'preuve_prepublication':None,'vue_exterieure':None,'vue_exterieure_alternative':None,
           'mode_test':'prospectif','date_limite_connaissance':None}
        x.update(kw);return x
    def calc_reel(**kw):
        # Calcul figé minimal d'une prévision réelle de la version courante (0.6.14).
        e={'moteur':fichier_sha(__file__),'parametres':fichier_sha(RACINE/'assets/parametres.json'),'base':'a'*64}
        c={'evenement':'SEU@7 apparait','p':.2,'rho':4,'contexte':{'empreintes':e}};c.update(kw);return c
    def reel(ident='P-1',**kw):
        c=calc_reel();x=forecast(ident,fictif=False,calcul=c,empreintes=dict(c['contexte']['empreintes']),
            preuve_prepublication={'source':'https://github.com/exemple/depot/releases/tag/v0','date':'2026-01-02'});x.update(kw)
        x['preuve_prepublication']['empreinte_prevision']=empreinte_prevision(x);return x
    def score(i='P-1',issue=0):return {'type':'score','id':i,'date':'2026-04-02','issue':issue,'preuve':'registre consulté'}
    class Tests(unittest.TestCase):
        def test_calendar_invalid(self):
            for d in ('2026-99-99','2026-02-29','2026-04-31'):
                with self.assertRaises(ValueError):date_iso(d)
        def test_attestation_deux_evenements(self):
            # 0.7.46 : deux cas d'événements distincts ; deux strates d'un même événement comptent pour un.
            self.assertEqual(cas_attestation('C-0001-S05 ; C-0001-S07'),['0001'])
            self.assertEqual(cas_attestation('C-0001-S05, C-0004-S05'),['0001','0004'])
            self.assertEqual(cas_attestation('à fournir'),[])
        def test_leap(self):self.assertEqual(date_iso('2024-02-29').day,29)
        def test_calendar_month_end(self):self.assertEqual(fin_fenetre('2026-01-31','1 mois').isoformat(),'2026-02-28')
        def test_window_invalid(self):
            for f in ('0 jours','-1 mois','1 minute'):
                with self.assertRaises(ValueError):duree_jours(f)
        def test_probability_limits(self):
            for x in (-.1,1.1,float('nan'),float('inf'),True):
                with self.assertRaises(ValueError):proba(x)
        def test_odds_boundaries(self):
            self.assertEqual(odds_module(0,3),0);self.assertEqual(odds_module(1,3),1)
        def test_negative_regression(self):
            e=lire_etat('[2026-01-01 | 1 an] INCERTITUDE@7[f] + RÉSEAU@7[f] + POLARITÉ@7[f]')
            r=calculer(e,'persiste','INC@7',[],bouge=['INC@7']);self.assertGreaterEqual(r['p'],0);self.assertLessEqual(r['p'],1)
        def test_invalid_state(self):
            for s in ('[2026-01 | 3 mois] SEUIL@99[f]','[2026-01 | 3 mois] SEUIL@7[f] + SEUIL@7[F]'):
                with self.assertRaises(ValueError):lire_etat(s)
        def test_valid_case(self):self.assertEqual(valider_base([fake_case()])['actifs'],1)
        def test_case_strata(self):
            c=fake_case();c['strates']=[12]
            with self.assertRaises(ValueError):valider_base([c])
        def test_case_force(self):
            c=fake_case();c['sequence'][0]['mots'][0]['intensite']='F'
            with self.assertRaises(ValueError):valider_base([c])
        def test_missing_coders(self):
            c=fake_case();c['codage']={}
            with self.assertRaises(ValueError):valider_base([c])
        def test_ten_year_transition(self):
            c=fake_case();c['issue']['date']=c['issue']['disponible_le']='2030-01-01';c['issue']['etat']='[2030-01-01 | 3 mois] POLARITÉ@7[f]'
            with self.assertRaises(ValueError):valider_base([c])
        def test_future_exclusion(self):self.assertEqual(base_active([fake_case(2090)],'2026-01-01',True),[])
        def test_delayed_source(self):
            c=fake_case();c['issue']['disponible_le']='2090-01-01';self.assertEqual(base_active([c],'2026-01-01',True),[])
        def test_fiction_exclusion(self):self.assertEqual(base_active([fake_case()],'2026-01-01'),[])
        def test_archive_exclusion(self):
            c=fake_case();c['statut_donnees']='archive_a_revoir';self.assertEqual(base_active([c],'2026-01-01',True),[])
        def test_homology_empty_strong(self):
            e=lire_etat('[2026-01-01 | 3 mois] RÉSEAU@7[f]');r=calculer(e,'apparait','SEU@7',[fake_case()]);self.assertEqual(r['nb_cas_par_niveau']['H1'],0)
        def test_case_weight_cap(self):
            e=lire_etat('[2026-01-01 | 3 mois] POLARITÉ@7[f]');r=calculer(e,'persiste','POL@7',[fake_case(count=10)]);self.assertLessEqual(r['n_A'],1)
        def test_reference_future(self):
            r={'POL@7 persiste':{'frequence':.2,'source':'x','definition':'x','periode':'x','fenetre':'3 mois','disponible_le':'2090-01-01'}}
            with self.assertRaises(ValueError):refs_valider(r,'3 mois','2026-01-01')
        def test_reference_scope(self):
            e=lire_etat('[2026-01-01 | 3 mois] POLARITÉ@7[f]');r=calculer(e,'persiste','POL@7',[],refs={'POL@7 hausse|persiste':{'frequence':.2}});self.assertAlmostEqual(r['p'],.85)
        def test_reference_disappearance(self):
            e=lire_etat('[2026-01-01 | 3 mois] POLARITÉ@7[f]');r=calculer(e,'disparait','POL@7',[],refs={'POL@7 disparait':{'frequence':.2}});self.assertAlmostEqual(r['p'],.2)
        def test_beta_uniform(self):self.assertAlmostEqual(beta_quantile(1,1,.1),.1,places=9)
        def test_beta_degenerate(self):self.assertIsNone(intervalle_beta(0,0,0))
        def test_single_step_invalid_semantics(self):
            e=lire_etat('[2026-01-01 | 3 mois] POLARITÉ@7[f]')
            for sem in ('invalide','continue'):
                with self.assertRaises(ValueError):horizon_result(e,'apparait','SEU@7',[],{},1,sem)
        def test_journal_future_state(self):
            p=forecast(etat_present='[2028-01-01 | 3 mois] POLARITÉ@7[f]')
            with self.assertRaises(ValueError):valider_journal([p])
        def test_journal_horizon_mismatch(self):
            p=forecast(echeance='2026-05-01')
            with self.assertRaises(ValueError):valider_journal([p])
        def test_prepublication_binds_probability(self):
            p=forecast(fictif=False,preuve_prepublication={'source':'registre','date':'2026-01-02'})
            p['preuve_prepublication']['empreinte_prevision']=empreinte_prevision(p)
            p['probabilite']=.9
            with self.assertRaises(ValueError):valider_journal([p])
        def test_horizon_baseline(self):
            e=lire_etat('[2026-01-01 | 3 mois] POLARITÉ@7[f]');opts={'refs':{'SEU@7 apparait':{'frequence':.2},'SEU@7 persiste':{'frequence':.8}}}
            r=horizon_result(e,'apparait','SEU@7',[],opts,4,'presence');self.assertAlmostEqual(r['comparateur'],cumul(.2,.8,4));self.assertIsNone(r['intervalle'])
        def test_ever_vs_final(self):self.assertGreater(1-(1-.2)**4,cumul(.2,.8,4))
        def test_compound_conditional(self):
            e=lire_etat('[2026-01-01 | 3 mois] POLARITÉ@7[f]');op={'asof':'2026-01-01','refs':{'POL@7 hausse|persiste':{'frequence':.2}}}
            res={'source':'x','critere':'x','seuil':'x','marqueur':'x','objet':'x','grandeur':'x','unite':'x','comparaison':'x','observations':[{'date':'2025-11-01','valeur':1},{'date':'2025-12-01','valeur':2}]}
            self.assertAlmostEqual(compose(e,'intensifie','POL@7',[],op,res)['p'],.17)
        def test_compound_missing_reference(self):
            e=lire_etat('[2026-01-01 | 3 mois] RÉSEAU@7[f]');res={k:'x' for k in ('source','critere','seuil','marqueur','objet')}
            self.assertIsNone(compose(e,'transforme','RES@7',[],{'asof':'2026-01-01'},res)['p'])
        def test_journal_duplicate(self):
            with self.assertRaises(ValueError):valider_journal([forecast(),forecast()])
        def test_journal_missing_rejeu(self):
            p=forecast();p.pop('rejeu')
            with self.assertRaises(ValueError):valider_journal([p])
        def test_journal_early_score(self):
            s=score();s['date']='2026-02-01'
            with self.assertRaises(ValueError):valider_journal([forecast(),s])
        def test_journal_orphan(self):
            with self.assertRaises(ValueError):valider_journal([score()])
        def test_partition_sum(self):
            p=forecast(partition='A');q=forecast('P-2',partition='A',evenement='SEU@7 absent')
            with self.assertRaises(ValueError):valider_journal([p,q])
        def test_partition_issues(self):
            p=forecast(partition='A',probabilite=.5,frequence_de_base=.5);q=forecast('P-2',partition='A',probabilite=.5,frequence_de_base=.5,evenement='SEU@7 absent')
            with self.assertRaises(ValueError):valider_journal([p,q,score(issue=1),score('P-2',1)])
        def test_partition_brier(self):
            p=forecast(partition='A',probabilite=.5,frequence_de_base=.5);q=forecast('P-2',partition='A',probabilite=.5,frequence_de_base=.5,evenement='SEU@7 absent')
            r=score_result([p,q,score(issue=1),score('P-2',0)]);self.assertEqual(r['questions_resolues'],1);self.assertAlmostEqual(r['details'][0]['brier'],.25)   # échelle binaire (0.6.13)
        def test_missing_score_counted(self):self.assertEqual(score_result([forecast()])['sans_score'],1)
        def test_fiction_never_validated(self):self.assertEqual(score_result([forecast(),score()])['questions_eligibles'],0)
        def test_unverified_never_validated(self):
            p=reel();p['preuve_prepublication']=None
            self.assertEqual(score_result([p,score()])['questions_eligibles'],0)
        def test_moteur_sans_calcul(self):
            # 0.6.14 (audit Manus, haute 1) : reproduction de l'auditeur, puis les voies fermées une à une.
            with self.assertRaises(ValueError):valider_journal([forecast(fictif=False)])                 # sans calcul
            self.assertEqual(score_result([reel(),score()])['questions_eligibles'],1)                    # chemin légitime
            p=reel();p['empreintes']={k:'0'*64 for k in ('moteur','parametres','base')}
            p['preuve_prepublication']['empreinte_prevision']=empreinte_prevision(p)
            with self.assertRaises(ValueError):valider_journal([p])                                      # empreintes factices
            p=reel();p['preuve_prepublication']['source']='moi';p['preuve_prepublication']['empreinte_prevision']=empreinte_prevision(p)
            self.assertEqual(score_result([p,score()])['questions_eligibles'],0)                         # preuve non publique
        def test_episode_count(self):
            data=[]
            for i in range(50):
                data.extend([reel(f'P-{i}',vue_exterieure=.3),score(f'P-{i}')])   # 0.7.41 : la référence V4 est la vue extérieure
            r=score_result(data);self.assertEqual(r['episodes_comparables'],1);self.assertEqual(r['statut'],'non encore évalué')
        def test_trajectory_mass(self):
            e=lire_etat('[2026-01-01 | 3 mois] POLARITÉ@7[f]');r=trajectoires(e,2,[],{'liaisons':[],'bouge':[],'manque':[]});self.assertAlmostEqual(r['somme'],1)
        def test_audit_parameter_mismatch(self):
            old=P['k'];P['k']=999
            try:
                with self.assertRaises(ValueError):audit()
            finally:P['k']=old
        def test_f_proposed_allowed_vide_refused(self):
            c=fake_case();m=c['sequence'][0]['mots'][0];c['fictif']=False;c['sources_verifiees']=True
            m['intensite']='F';m['a6']='POLARITÉ@7 : CONTRAINTE → (deux camps, pas une règle) ; SEUIL → (aucun passage irréversible)'
            for s_ in c['sequence']+[c['issue']]:s_['etat']=s_['etat'].replace('[f]','[F]')
            with self.assertRaises(ValueError):valider_base([c])            # garantie et option manquantes (0.6.0)
            m.update(garantie={'mecanisme':'deux camps se définissent l\'un par l\'autre','support':{'type':'texte','reference':'ouvrage de référence (test)','disponible_le':'2000-01-01'},'attendu':'alignements exclusifs','contredirait':'troisième position stable'},option={'acteur':'les électeurs','avant':'choisir entre plusieurs offres','apres':'choisir un camp'},test='pistolet')
            with self.assertRaises(ValueError):valider_base([c])            # corroboration manquante (0.6.6)
            m['corroboration']='independantes'
            with self.assertRaises(ValueError):valider_base([c])            # une seule source nommée
            m['source']='source A ; source B'
            with self.assertRaises(ValueError):valider_base([c])            # passage manquant (0.7.2)
            m['passage']={'localisation':'source A, p. 3','relation':'soutient'}
            with self.assertRaises(ValueError):valider_base([c])            # « independantes » : un seul passage qui soutient
            m['passage']=[{'localisation':'source A, p. 3','relation':'soutient'},{'localisation':'source B, § 4','relation':'soutient'}]
            with self.assertRaises(ValueError):valider_base([c])            # indépendance non nommée (0.7.11)
            m['independance']={'critere':'producteur','motif':'deux rédactions distinctes, aucune ne cite l’autre'}
            self.assertEqual(valider_base([c])['actifs'],1)
            m['corroboration']='unique'
            with self.assertRaises(ValueError):valider_base([c])            # indépendance déclarée pour une source unique
            m.pop('independance');self.assertEqual(valider_base([c])['actifs'],1)
            c2=self._f_case('POLARITÉ@7 : CONTRAINTE → (deux camps) ; SEUIL → (aucune rupture)')
            st=statuts();cle_=_STATUTS_CACHE['cle'];st[('POL',7)]='Vide';_STATUTS_CACHE.update(st=st)
            try:
                with self.assertRaises(ValueError):valider_base([c2])         # F sur case Vide refusé à la validation (0.6.6)
            finally:_STATUTS_CACHE.clear()
            self.assertEqual(statuts().get(('COM',1)),'Vide')
        def test_a6_neighbours_required(self):
            c=fake_case();m=c['sequence'][0]['mots'][0];c['fictif']=False;c['sources_verifiees']=True
            m['intensite']='F';m['a6']='POLARITÉ@7 : CONTRAINTE → (deux camps, pas une règle)'
            for s_ in c['sequence']+[c['issue']]:s_['etat']=s_['etat'].replace('[f]','[F]')
            with self.assertRaises(ValueError):valider_base([c])
            m['a6']='POLARITÉ@7 : CONTRAINTE → (x) ; SEUIL ? (non tranché)'
            with self.assertRaises(ValueError):valider_base([c])
        def _g6_case(self,o1,o2,link):
            c=fake_case();st0=c['sequence'][0];st0['etat']=st0['etat'].replace('POLARITÉ@7[f]','INCERTITUDE@7[f] + CONTRAINTE@7[f]')
            c['issue']['etat']=c['issue']['etat'].replace('POLARITÉ@7[f]','INCERTITUDE@7[f] + CONTRAINTE@7[f]')
            base_m=st0['mots'][0];st0['mots']=[dict(base_m,carte='INC',objet=o1),dict(base_m,carte='CTR',objet=o2)]
            st0['liaisons']=[link];st0['preuves_liaisons']=['preuve fictive'];return c
        def test_g6_same_object_refused(self):
            with self.assertRaises(ValueError):valider_base([self._g6_case('le plafond','le plafond','INCERTITUDE@7 renforcement CONTRAINTE@7')])
        def test_g6_distinct_objects_accepted(self):
            self.assertEqual(valider_base([self._g6_case('le plafond','le périmètre','INCERTITUDE@7 renforcement CONTRAINTE@7')])['actifs'],1)
        def test_g6_independence_same_object(self):
            c=self._g6_case('x','y','INCERTITUDE@7 indépendance CONTRAINTE@7');self.assertEqual(valider_base([c])['actifs'],1)
            self.assertTrue(erreurs_objets({'POL@7':'a','RES@7':'A '},[('POL@7','indépendance','RES@7')],incompatibles()))
        def test_renvoi_detection(self):
            import tempfile
            with tempfile.TemporaryDirectory() as d:
                f=Path(d)/'x.md';f.write_text('voir `strates.md` §9 et `validation.md` §3',encoding='utf-8')
                self.assertEqual(len(erreurs_renvois([f])),2)
                f.write_text('voir `validation.md` §6',encoding='utf-8');self.assertEqual(erreurs_renvois([f]),[])
        def test_homology_strictest(self):
            # 3 cas identiques (H1) + 2 cas avec un mot de plus (H1.5 seulement) : 0.4.0 prenait H1.5.
            mots4='POLARITÉ@7[f] + CONTRAINTE@7[f] + RÉSEAU@7[f] + HIÉRARCHIE@7[f]'
            ids=[f'C-{i:04d}-S07' for i in range(9000,9999) if usage_attendu(f'C-{i:04d}-S07')=='apprentissage'][:5]
            base=[]
            for n,cid in enumerate(ids):
                c=fake_case();c['id']=cid;ms=mots4+(' + PROPORTION@7[f]' if n>=3 else '')
                for s_ in c['sequence']+[c['issue']]:s_['etat']=s_['etat'].replace('POLARITÉ@7[f]',ms)
                d=c['sequence'][0]['mots'][0]
                c['sequence'][0]['mots']=[dict(d,carte=k,objet='objet-'+k) for k in ('POL','CTR','RES','HIE')+(('PRO',) if n>=3 else ())]
                base.append(c)
            e=lire_etat('[2026-01-01 | 3 mois] '+mots4);r=calculer(e,'persiste','POL@7',base)
            self.assertEqual(r['nb_cas_par_niveau']['H1'],3);self.assertEqual(r['nb_cas_par_niveau']['H1.5'],5)
            self.assertEqual(r['homologie'],'H1')
        def _f_case(self,a6,**mot):
            c=fake_case();m=c['sequence'][0]['mots'][0];c['fictif']=False;c['sources_verifiees']=True
            m.update(intensite='F',a6=a6,garantie={'mecanisme':'deux camps se définissent l\'un par l\'autre','support':{'type':'texte','reference':'ouvrage de référence (test)','disponible_le':'2000-01-01'},'attendu':'alignements exclusifs','contredirait':'troisième position stable'},option={'acteur':'les électeurs','avant':'choisir entre plusieurs offres','apres':'choisir un camp'},corroboration='unique',test='pistolet',passage={'localisation':'p. 3, § 2','relation':'soutient'});m.update(mot)
            for s_ in c['sequence']+[c['issue']]:s_['etat']=s_['etat'].replace('[f]','[F]')
            return c
        def test_a6_verdicts(self):
            ok='POLARITÉ@7 : CONTRAINTE → (deux camps) ; SEUIL + (rupture datée, autre fait)'
            self.assertEqual(valider_base([self._f_case(ok)])['actifs'],1)
            for bad in ('POLARITÉ@7 : CONTRAINTE → () ; SEUIL → ()','POLARITÉ@7 : CONTRAINTE ← (r) ; SEUIL ← (r)',
                        'POLARITÉ@7 : CONTRAINTE → (r) ; SEUIL ← (r)'):
                with self.assertRaises(ValueError):valider_base([self._f_case(bad)])
        def test_a7_portee(self):
            ok='POLARITÉ@7 : CONTRAINTE → (deux camps) ; SEUIL → (aucune rupture)'
            for kw in ({'portee':'substantielle'},{'portee':'dominante'},{'portee':'inconnue'}):
                with self.assertRaises(ValueError):valider_base([self._f_case(ok,**kw)])
            c=fake_case();c['sequence'][0]['mots'][0].update(portee='substantielle')
            with self.assertRaises(ValueError):valider_base([c])
            c['sequence'][0]['mots'][0]['force_initiale']='F';self.assertEqual(valider_base([c])['actifs'],1)
        def test_a7_force_initiale_cross_state(self):
            c=fake_case(count=2)
            c['sequence'][1]['mots']=[dict(fake_case()['sequence'][0]['mots'][0],portee='substantielle',force_initiale='F')]
            with self.assertRaises(ValueError):valider_base([c])   # f à l'état précédent, sans origine F → rejet
            c['sequence'][0]['mots'][0].update(portee='substantielle',force_initiale='F')
            self.assertEqual(valider_base([c])['actifs'],1)          # déjà rétrogradé depuis F : cohérent
        def test_a7_messages(self):
            errs=controle_a7('POL@7',{'portee':'substantielle','intensite':'F','force_initiale':'F'})
            self.assertEqual(len(errs),1);self.assertIn('noter f',errs[0])
            self.assertTrue(controle_a7('POL@7',{'portee':'marginale','intensite':'f','force_initiale':'F'}))
        def test_schema_documente(self):self.assertEqual(valider_base([schema_documente()])['actifs'],1)
        def _mutations(self,base,n,graine):
            import random
            def chemins(x,p=()):
                if isinstance(x,dict):
                    for k,v in x.items():yield p+(k,);yield from chemins(v,p+(k,))
                elif isinstance(x,list):
                    for i,v in enumerate(x):yield p+(i,);yield from chemins(v,p+(i,))
            P_=list(chemins(base));rng=random.Random(graine)
            valeurs=[None,[],{},'',0,-1,1.5,True,'x','2005-13','[2005-04 | 0 mois] ∅',float('nan')]
            for _ in range(n):
                c=copy.deepcopy(base);ch=rng.choice(P_);parent=c
                for k in ch[:-1]:parent=parent[k]
                if rng.random()<.3 and isinstance(parent,dict):del parent[ch[-1]]
                else:parent[ch[-1]]=rng.choice(valeurs)
                yield ch,c
        def test_fuzz_valider(self):
            # Toute fiche altérée est acceptée ou refusée par un message (ValueError), jamais par une trace.
            for ch,c in self._mutations(schema_documente(),1500,42):
                try:valider_base([c])
                except ValueError:pass
                except Exception as e:self.fail(f'{ch} : {type(e).__name__} {e}')
        def test_fuzz_journal(self):
            base=charger(RACINE/'assets/journal.exemple.jsonl')
            for ch,c in self._mutations(base,1500,7):
                try:score_result(c)
                except ValueError:pass
                except Exception as e:self.fail(f'{ch} : {type(e).__name__} {e}')
        def test_journal_calcul_coherent(self):
            base=charger(RACINE/'assets/journal.exemple.jsonl');x=next(l for l in base if l.get('calcul'))
            x['probabilite']=min(1,x['probabilite']+.1)
            with self.assertRaises(ValueError):valider_journal(base)
        def test_sans_evenement_coherent(self):
            c=fake_case();c['sans_evenement']=True;self.assertEqual(valider_base([c])['actifs'],1)
            c['issue']['etat']=c['issue']['etat'].replace('POLARITÉ@7[f]','∅');c['issue']['retraits']=[{'mot':'POLARITÉ@7','fait':'x','source':'y'}]
            with self.assertRaises(ValueError):valider_base([c])
        def test_affichage_pourcentage(self):
            self.assertEqual(pct(.220379),'22 %');self.assertEqual(pct(.00724),'0,7 %');self.assertEqual(pct(.9931),'99,3 %')
        def test_erreur_json(self):
            import subprocess
            r=subprocess.run([sys.executable,__file__,'calculer','--etat','[2026-09 | 3 mois] POLARITÉ@7[F]','--evenement','SEUIL@99 apparait','--json'],capture_output=True,text=True,stdin=subprocess.DEVNULL,encoding='utf-8')
            self.assertEqual(r.returncode,2);self.assertIn('erreur',json.loads(r.stdout))
            # 0.6.12 : sans --temporalite, la question est posée et le calcul refusé.
            r=subprocess.run([sys.executable,__file__,'calculer','--etat','[2026-09-26 | 7 jours] ÉMERGENCE@7[f]','--evenement','ÉMERGENCE@7 persiste','--json'],capture_output=True,text=True,stdin=subprocess.DEVNULL,encoding='utf-8')
            self.assertEqual(r.returncode,2);self.assertIn('durée de vie propre',json.loads(r.stdout)['erreur'])
            # 0.7.34 (L7) : hors démonstration, une prévision chiffrée hors de la strate 7 est refusée.
            r=subprocess.run([sys.executable,__file__,'calculer','--etat','[2026-09-26 | 7 jours] ÉMERGENCE@11[f]','--evenement','ÉMERGENCE@11 persiste','--temporalite','generique','--json'],capture_output=True,text=True,stdin=subprocess.DEVNULL,encoding='utf-8')
            self.assertEqual(r.returncode,2);self.assertIn('strates [7]',json.loads(r.stdout)['erreur'])
            # 0.7.52 (§29) : --exploratoire lève L7 pour ce calcul seul (le refus suivant est celui du dossier manquant),
            # et refuse --journal.
            r=subprocess.run([sys.executable,__file__,'calculer','--etat','[2026-09-26 | 7 jours] ÉMERGENCE@11[f]','--evenement','ÉMERGENCE@11 persiste','--temporalite','generique','--exploratoire','--json'],capture_output=True,text=True,stdin=subprocess.DEVNULL,encoding='utf-8')
            self.assertNotIn('strates [7]',json.loads(r.stdout).get('erreur',''))
            r=subprocess.run([sys.executable,__file__,'calculer','--etat','[2026-09-26 | 7 jours] ÉMERGENCE@11[f]','--evenement','ÉMERGENCE@11 persiste','--temporalite','generique','--exploratoire','--journal','j.jsonl','--json'],capture_output=True,text=True,stdin=subprocess.DEVNULL,encoding='utf-8')
            self.assertEqual(r.returncode,2);self.assertIn('§29',json.loads(r.stdout)['erreur'])
        def test_console_cp1252(self):
            # 0.7.1 (audit hacker.ai) : sortie Windows en cp1252, redirigée. Erreur JSON et sortie humaine.
            import subprocess
            env=dict(os.environ,PYTHONIOENCODING='cp1252');env.pop('PYTHONUTF8',None)
            r=subprocess.run([sys.executable,__file__,'calculer','--etat','[2026-09 | 3 mois] POLARITÉ@7[F]','--evenement','SEUIL@99 apparait','--json'],
                             capture_output=True,stdin=subprocess.DEVNULL,env=env)
            self.assertEqual(r.returncode,2);self.assertEqual(json.loads(r.stdout.decode('ascii'))['code'],2)
            r=subprocess.run([sys.executable,__file__,'calculer','--demo','--etat','[2026-09 | 3 mois] POLARITÉ@7[F]','--evenement','SEUIL@7 apparait','--temporalite','generique'],
                             capture_output=True,stdin=subprocess.DEVNULL,env=env)   # 0.7.39 : --demo (hors démonstration, --dossier requis)
            self.assertEqual(r.returncode,0);self.assertIn('⚠ ρ4',r.stdout.decode('utf-8'))
            # 0.7.32 (audit DeepSeek, P2.9) : les glyphes de `accord` (κ, π, α, ₒ, ·) passent aussi.
            r=subprocess.run([sys.executable,__file__,'accord','--a','90','--b','5','--c','5','--d','20'],capture_output=True,stdin=subprocess.DEVNULL,env=env)
            self.assertEqual(r.returncode,0);self.assertIn('κ',r.stdout.decode('utf-8'))
        def test_sortie_doree(self):
            # Sortie humaine de l'exemple 1 : ouverture constitutionnelle, ligne S5, marquage « large ».
            e=lire_etat('[2026-09 | 3 mois] POLARITÉ@7[F] + CONTRAINTE@6[F]')
            base=base_active(charger(RACINE/'assets/base-de-cas.exemple.jsonl'),'2026-09-01',True)
            r=horizon_result(e,'apparait','SEU@7',base,{'liaisons':lire_liaisons(['CONTRAINTE@6 echo POLARITÉ@7'],e),'asof':'2026-09-01'},1,'presence')
            r.update(echeance='2026-12-01',journal='P-0101')
            out=io.StringIO()
            with contextlib.redirect_stdout(out):afficher(r)
            lignes=out.getvalue().splitlines()
            self.assertEqual(lignes[0],'⚠ Prévision · cet outil prend un risque déclaré.')
            self.assertEqual(lignes[1],'⚠ ρ1 · association · 10 cas distincts (H1) · p₀ 23 % · p ~22 % (large : 5–43) · échéance 2026-12-01 · journal P-0101')
        def test_intervalle_large(self):
            self.assertEqual(texte_probabilite(.22,[.05,.43]),'~22 % (large : 5–43)')
            self.assertEqual(texte_probabilite(.22,[.15,.30]),'22 % [15–30]')
            self.assertEqual(texte_probabilite(None,None),'non estimée')
        def test_fichiers_messages(self):
            for arg in ('{"a":1}','/introuvable.json',str(RACINE/'scripts')):
                with self.assertRaises(ValueError):lire_json(arg,'--references')
        def test_repetitions(self):
            import tempfile
            with tempfile.TemporaryDirectory() as d:
                f=Path(d)/'x.md'
                f.write_text('| X | provenance ; ne mesure pas sa calibration ; ne mesure pas sa calibration |',encoding='utf-8')
                self.assertEqual(len(erreurs_repetitions([f])),1)
                para='Un paragraphe suffisamment long pour être contrôlé par le détecteur.'
                f.write_text(para+'\n\n'+para,encoding='utf-8');self.assertEqual(len(erreurs_repetitions([f])),1)
                f.write_text(para,encoding='utf-8');self.assertEqual(erreurs_repetitions([f]),[])
        def test_bilan(self):
            t=bilan(journal_chemin=RACINE/'assets/journal.exemple.jsonl')
            self.assertIn('Étape 2',t);self.assertIn('Étape 3',t);self.assertIn("Test à l'aveugle",t)
        def test_recodage_confirme(self):
            c=self._f_case('POLARITÉ@7 : CONTRAINTE → (deux camps) ; SEUIL → (aucune rupture)')
            c['codage']['recodage']='Claude — proposition 0.6.0'
            with self.assertRaises(ValueError):valider_base([c])
            c['codage']['recodage_confirme']={'par':'Claude','date':'2026-10-27'}
            with self.assertRaises(ValueError):valider_base([c])            # un modèle ne se confirme pas lui-même
            c['codage']['recodage_confirme']={'par':'codeur-1','date':'2026-10-27'}
            self.assertEqual(valider_base([c])['actifs'],1)
            # 0.6.14 (audit Manus, haute 2) : identité structurée, pas de liste noire de noms.
            c['codage']['codeurs']=[{'id':'GPT-4o','role':'modele'}]
            c['codage']['recodage_confirme']={'par':'GPT-4o','date':'2026-10-27'}
            with self.assertRaises(ValueError):valider_base([c])            # codeur modèle seul
            c['codage']['codeurs']=[{'id':'codeur-1','role':'humain'},{'id':'Gemini','role':'modele'}]
            c['codage'].update(independants=True,au_moins_un_humain=True)
            c['codage']['recodage_confirme']={'par':'Gemini','date':'2026-10-27'}
            with self.assertRaises(ValueError):valider_base([c])            # confirmation par un modèle
            c['codage']['recodage_confirme']={'par':'quelqu-un','date':'2026-10-27'}
            with self.assertRaises(ValueError):valider_base([c])            # confirmation non reliée
            c['codage']['codeurs']=['codeur-1']
            with self.assertRaises(ValueError):valider_base([c])            # chaîne libre sur cas réel actif
        def test_proposition(self):
            c=fake_case();c['fictif']=False;c['statut_donnees']='proposition';c['sources_verifiees']=False;c['motif_proposition']='recodage à vérifier'
            r=valider_base([c]);self.assertEqual((r['actifs'],r['propositions']),(0,1))
            self.assertEqual(base_active([c],'2026-01-01'),[])
            c['sources_verifiees']=True
            with self.assertRaises(ValueError):valider_base([c])
        def test_hors_domaine(self):
            # Simule une case Hors domaine : aucun ancrage, aucun événement, aucune trajectoire vers elle.
            st=statuts();cle_=_STATUTS_CACHE['cle'];st[('SEU',7)]='Hors domaine';_STATUTS_CACHE.update(st=st)
            try:
                e=lire_etat('[2026-01-01 | 3 mois] POLARITÉ@7[f]')
                with self.assertRaises(ValueError):calculer(e,'apparait','SEU@7',[])
                r=trajectoires(e,1,[],{'liaisons':[],'bouge':[],'manque':[]})
                self.assertFalse(any('SEU@7' in str(t['chemins']) for t in r['trajectoires']))
            finally:_STATUTS_CACHE.clear()
        def test_strate_13(self):
            self.assertEqual(NS,13);lire_etat('[2026-10-19 | 1 semaine] ÉMERGENCE@13[f]')
            with self.assertRaises(ValueError):lire_etat('[2026-10-19 | 1 semaine] ÉMERGENCE@14[f]')
            self.assertEqual(len(statuts()),16*NS)
        def test_comparateur_inertiel(self):
            p=forecast(version_regles='0.5.0');p.pop('p_sans_cartes')
            with self.assertRaises(ValueError):valider_journal([p])          # p_sans_cartes absent
            p=forecast(version_regles='0.4.8');p.pop('p_sans_cartes');valider_journal([p])  # journaux antérieurs admis
            p=forecast(version_regles='0.5.0',p_sans_cartes=.2,probabilite=.2)
            r=score_result([p,score()]);self.assertEqual(r['apport_des_cartes']['difference'],0)
            p=forecast(version_regles='0.5.0',p_sans_cartes=.5,probabilite=.2)
            self.assertLess(score_result([p,score()])['apport_des_cartes']['difference'],0)
        def test_jugement(self):
            j=lambda i,p:{'type':'prevision','id':i,'date':'2026-09-28','echeance':'2026-10-26','version_regles':'0.5.1',
                          'origine':'jugement','question':'q','evenement':'Larcher élu','episode_id':'E','refutation':'non',
                          'probabilite':p,'rejeu':False,'fictif':False,'resolution':{'source':'s','critere':'c','seuil':'t'}}
            s=lambda i,o:{'type':'score','id':i,'date':'2026-10-26','issue':o,'preuve':'p'}
            r=score_result([j('J1',.8),s('J1',1),j('J2',.45),s('J2',1),j('J3',.6),s('J3',0)])
            self.assertAlmostEqual(r['jugements']['brier'],0.2341666667,places=6);self.assertEqual(r['questions_eligibles'],0)
            self.assertIsNone(r['apport_des_cartes'])
            m=forecast('P-9',partition='A',probabilite=.5,frequence_de_base=None);jj=dict(j('J9',.5),partition='A')
            with self.assertRaises(ValueError):valider_journal([m,jj])          # origines mêlées dans une partition
        def test_apparait_message(self):
            e=lire_etat('[2026-01-01 | 3 mois] SEUIL@13[f]')
            with self.assertRaises(ValueError) as c:calculer(e,'apparait','SEU@13',[])
            self.assertIn('déjà présent',str(c.exception))
        def test_garantie_option(self):
            ok={'mecanisme':'m','attendu':'a','contredirait':'c'};op={'acteur':'x','avant':'pouvait','apres':'ne peut plus'}
            self.assertEqual(controle_garantie('POL@7',{'garantie':ok,'option':op,'contre_observation':'z'},True),[])
            self.assertTrue(controle_garantie('POL@7',{'garantie':dict(ok,attendu=''),'option':op},True))
            self.assertTrue(controle_garantie('POL@7',{'garantie':ok,'option':dict(op,apres='pouvait')},True))
            self.assertTrue(controle_garantie('POL@7',{'garantie':ok,'option':op,'contre_observation':'C'},True))
            self.assertEqual(controle_garantie('POL@7',{},False),[])
        def test_jugement_scelle(self):
            p=forecast(version_regles='0.6.0');p.pop('probabilite_jugement')
            with self.assertRaises(ValueError):valider_journal([p])
            p=forecast(version_regles='0.6.0',probabilite_jugement=.6,probabilite=.2)
            with self.assertRaises(ValueError):valider_journal([p])          # scellé absent
            p['jugement_scelle']=empreinte_jugement(p['question'],p['evenement'],.6,p['date'])
            r=score_result([p,score()]);mj=r['moteur_contre_jugement']
            self.assertEqual((mj['ameliorations'],mj['degradations']),(1,0))
            self.assertAlmostEqual(r['difficulte']['difficulte_moyenne'],.3)   # f=0,3 → 0,5−0,2 (0.6.5)
        def test_sensibilite(self):
            e=lire_etat('[2026-01-01 | 3 mois] POLARITÉ@7[f]');avant=json.dumps(P,sort_keys=True)
            s=sensibilite(e,'apparait','SEU@7',[],{},1,'presence')
            # 0.7.3 : deux familles (modèle, classe de référence) et une sonde de force d'ancrage.
            self.assertEqual(len([x for x in s['variantes'] if x['groupe']=='modele']),6)
            self.assertEqual(len([x for x in s['variantes'] if x['groupe']=='classe']),8)
            self.assertEqual(len([x for x in s['variantes'] if x['groupe']=='lecture']),1)
            self.assertLessEqual(s['min'],s['max']);self.assertLessEqual(s['modele']['min'],s['modele']['max'])
            self.assertLessEqual(s['classe']['min'],s['classe']['max'])
            self.assertTrue(s['modele']['min']<=s['reference']<=s['modele']['max'])
            self.assertEqual(s['min'],min(s['modele']['min'],s['classe']['min']))   # 0.7.3 : sonde F → f hors bande
            self.assertEqual(json.dumps(P,sort_keys=True),avant)               # paramètres restaurés
            self.assertEqual(s['bande_large'],s['max']-s['min']>P['largeur_max_affichage'])
        def test_sensibilite_classe_vide(self):
            # Base vide : la classe ne peut pas bouger, seule la sonde de force mesure un canal nul.
            e=lire_etat('[2026-01-01 | 3 mois] POLARITÉ@7[F] + CONTRAINTE@7[F]')
            s=sensibilite(e,'apparait','SEU@7',[],{},1,'presence')
            self.assertEqual(len(s['classe']['effectifs']),1)
            self.assertAlmostEqual(s['effet_force'],0.0)      # les λ viennent de la matrice, pas de la force
        def test_fragilite_niveau(self):
            # 2 cas stricts (H1) qui touchent, 3 cas à force de lecture différente (H1.5) qui ne touchent
            # pas : c_min_rho1 écarte H1 et retient H1.5. Le calcul doit rendre les deux p, pas les seuls effectifs.
            def mini(y,ctr,hit):
                d0=f'{y}-01-01';d1=fin_fenetre(d0,'3 mois').isoformat()
                e0=f'POLARITÉ@7[F] + CONTRAINTE@7[{ctr}]'
                return {'id':f'C-{y-2000:04d}-S07','strates':[7],'fenetre':'3 mois','sans_evenement':False,
                        'sequence':[{'date':d0,'disponible_le':d0,'etat':f'[{d0} | 3 mois] '+e0}],
                        'issue':{'date':d1,'disponible_le':d1,
                                 'etat':f'[{d1} | 3 mois] '+e0+(' + SEUIL@7[f]' if hit else '')}}
            base=[mini(2010,'F',True),mini(2011,'F',True)]+[mini(2012,'f',False),mini(2013,'f',False),mini(2014,'f',False)]
            e=lire_etat('[2026-01-01 | 3 mois] POLARITÉ@7[F] + CONTRAINTE@7[F]')
            r=calculer(e,'apparait','SEU@7',base)
            self.assertEqual(r['nb_cas_par_niveau']['H1'],2)
            self.assertEqual(r['homologie'],'H1.5')
            self.assertEqual(r['niveaux']['H1']['c_A'],2);self.assertEqual(r['niveaux']['H1.5']['c_A'],5)
            self.assertGreater(r['fragilite_niveau'],0.1)
            self.assertNotEqual(r['niveaux']['H1']['p'],r['niveaux']['H1.5']['p'])
            # 0.7.3 : l'écart de 20 points n'était signalé par rien (seuil de 30 points) ; seuil dédié de 10.
            self.assertTrue(any(f.startswith('Fragilité de niveau') for f in r['drapeaux']))
            sb=sensibilite(e,'apparait','SEU@7',base,{},1,'presence')
            ids={tuple(x['cas']) for x in sb['variantes'] if x['groupe']=='classe'}
            self.assertEqual(sb['classe']['instable'],len(ids)>1)          # instabilité = cas retenus, pas étiquette
        def test_dossier_refuse_sans_a6(self):
            d={'etat':'[2026-01-01 | 3 mois] POLARITÉ@7[F] + CONTRAINTE@7[F]','candidats':['POL@7','CTR@7'],
               'contre_candidate':'CTR@7',
               'mots':[{'carte':'POL','strate':7,'intensite':'F','fait':'deux camps se définissent l’un par l’autre',
                        'source':'source A ; source B','objet':'relation A-B','contre_observation':'médiation acceptée, marginale',
                        'portee':'marginale','test':'pistolet','corroboration':'independantes','classe_source':'contemporain',
                        'passage':[{'localisation':'p. 3','relation':'soutient'},{'localisation':'p. 4','relation':'soutient'}],
                        'garantie':{'mecanisme':'x','support':{'type':'cas','reference':'C-0001','disponible_le':'2000-01-01'},'attendu':'y','contredirait':'z'},'option':{'acteur':'A','avant':'a','apres':'b'}}]}
            with self.assertRaises(ValueError) as cm:dossier_valider(d)
            self.assertIn('a6',str(cm.exception))
        def test_dossier_rejette_contre_candidate_hors_liste(self):
            d={'etat':'[2026-01-01 | 3 mois] POLARITÉ@7[f] + CONTRAINTE@7[f]','candidats':['POL@7','CTR@7'],
               'contre_candidate':'SEU@7','mots':[{'carte':'POL','strate':7,'intensite':'f','fait':'f','source':'s',
                                                   'objet':'o','contre_observation':'c','portee':'marginale','classe_source':'contemporain'}]}
            with self.assertRaises(ValueError):dossier_valider(d)
        def test_dossier_sceau_stable(self):
            d={'etat':'[2026-01-01 | 3 mois] POLARITÉ@7[f] + CONTRAINTE@7[f]','candidats':['POL@7','CTR@7'],
               'contre_candidate':'CTR@7',
               'questions':[{'question':'Une règle commune est-elle imposée ?','si_oui':'CTR@7','si_non':'POL@7',
                             'resolution':'texte publié au registre',
                             'justification':{'oui':'une règle commune retire une option aux deux camps',
                                              'non':'sans règle, chaque camp reste seul à se définir'}}],
               'mots':[{'carte':'POL','strate':7,'intensite':'f','fait':'f','source':'s','objet':'o',
                        'contre_observation':'c','portee':'marginale','classe_source':'contemporain'},
                       {'carte':'CTR','strate':7,'intensite':'f','fait':'f','source':'s','objet':'o',
                        'contre_observation':'c','portee':'marginale','classe_source':'contemporain'}]}
            a=dossier_valider(d);b=dossier_valider(copy.deepcopy(d))
            self.assertEqual(a['sceau'],b['sceau']);self.assertEqual(len(a['sceau']),64)
            d['contre_candidate']='POL@7'
            self.assertNotEqual(dossier_valider(d)['sceau'],a['sceau'])
        def _dossier(self,**kw):
            d=json.loads((RACINE/'assets/dossier.exemple.json').read_text(encoding='utf-8'));d.update(kw);return d
        def test_dossier_corrections(self):
            # 0.7.3 : relecture du correctif reçu avec l'audit d'ingénierie.
            self.assertTrue(dossier_valider(self._dossier())['conforme'])
            d=self._dossier();d['evenements'][0]['temporalite']='duree_de_vie'
            self.assertTrue(dossier_valider(d)['conforme'])                  # même valeur que calculer --temporalite
            d['evenements'][0]['temporalite']='duree_vie'
            with self.assertRaises(ValueError):dossier_valider(d)
            for champ in ('passage','corroboration'):                         # exigés pour F d'une lecture réelle
                d=self._dossier();d['mots'][0].pop(champ)
                with self.assertRaises(ValueError):dossier_valider(d)
            d=self._dossier();d['rejets'].pop('SEU@7')                         # rivale écartée sans motif
            with self.assertRaises(ValueError):dossier_valider(d)
            d=self._dossier(candidats=['POL@7','CTR@6','HIE@6'],contre_candidate=['HIE@6'])
            d['rejets'].pop('SEU@7')
            with self.assertRaises(ValueError):dossier_valider(d)            # strate 7 : une seule candidate
            d=self._dossier(contre_candidate='HIE@6')
            with self.assertRaises(ValueError):dossier_valider(d)            # strate 7 sans contre-candidate
            d=self._dossier();d['rejets']['POL@7']='x'
            with self.assertRaises(ValueError):dossier_valider(d)            # rejet d'une carte retenue
        def test_dossier_calculer(self):
            import subprocess,tempfile
            et='[2026-09 | 3 mois] POLARITÉ@7[F] + CONTRAINTE@6[F]'
            base=[sys.executable,__file__,'calculer','--etat',et,'--temporalite','generique','--json']
            def run(d,*extra):
                with tempfile.TemporaryDirectory() as t:
                    f=Path(t)/'d.json';f.write_text(json.dumps(d,ensure_ascii=False),encoding='utf-8')
                    r=subprocess.run(base+['--dossier',str(f)]+list(extra),capture_output=True,text=True,stdin=subprocess.DEVNULL,encoding='utf-8')
                return r.returncode,json.loads(r.stdout)
            ok=['--evenement','SEUIL@7 apparait','--semantique','presence','--date-information','2026-09-20']
            c,o=run(self._dossier(),*ok);self.assertEqual(c,0);self.assertIn('dossier',o)
            d=self._dossier();d.pop('evenements')
            c,o=run(d,*ok);self.assertEqual(c,2)                               # événement non déclaré : refus
            c,o=run(self._dossier(disponible_le='2026-10-20'),*ok);self.assertEqual(c,2)   # pièces postérieures (B1)
            c,o=run(self._dossier(),'--evenement','SEUIL@7 apparait','--semantique','au-moins-une-fois','--date-information','2026-09-20')
            self.assertEqual(c,2)
        def test_compose_sans_semantique(self):
            # 0.7.3 : le correctif reçu levait UnboundLocalError (« sem ») sur tout événement composé.
            import subprocess,tempfile
            with tempfile.TemporaryDirectory() as t:
                f=Path(t)/'r.json';f.write_text(json.dumps({'source':'x','critere':'x','seuil':'x','marqueur':'x','objet':'x'}),encoding='utf-8')
                r=subprocess.run([sys.executable,__file__,'calculer','--demo','--etat','[2026-09 | 3 mois] POLARITÉ@7[F]','--evenement','POL@7 se transforme',
                                  '--temporalite','generique','--resolution',str(f),'--json'],capture_output=True,text=True,stdin=subprocess.DEVNULL,encoding='utf-8')
            self.assertNotIn('UnboundLocalError',r.stdout);self.assertEqual(r.returncode,0)
        def test_partage_date(self):
            # 0.7.4 (décision 2) : partage daté, registre qui fait foi, partage avant codage.
            import tempfile,subprocess
            c=self._f_case('POLARITÉ@7 : CONTRAINTE → (deux camps) ; SEUIL → (aucune rupture)')
            self.assertEqual(valider_base([c])['actifs'],1)
            c2=copy.deepcopy(c);c2.pop('usage_fige_le')
            with self.assertRaises(ValueError):valider_base([c2])            # partage non daté
            c2=copy.deepcopy(c);c2['codage'].pop('debut')
            with self.assertRaises(ValueError):valider_base([c2])            # cas réel sans début de codage
            c2=copy.deepcopy(c);c2['usage_fige_le']='2026-02-01'
            with self.assertRaises(ValueError):valider_base([c2])            # partage fixé après le début du codage
            c2=copy.deepcopy(c);c2['sequence'][0]['date']  # un état ancien n'empêche rien : historique admis
            self.assertTrue(jour(c2['sequence'][0]['date'])<=jour(c2['usage_fige_le']))
            with tempfile.TemporaryDirectory() as t:
                reg=Path(t)/'partage.jsonl'
                with self.assertRaises(ValueError):valider_base([c],registre=lire_registre(reg))   # absent du registre
                r=subprocess.run([sys.executable,__file__,'partager',c['id'],'--registre',str(reg),'--date','2026-01-01'],
                                 capture_output=True,text=True,stdin=subprocess.DEVNULL,encoding='utf-8')
                self.assertEqual(r.returncode,0)
                self.assertEqual(valider_base([c],registre=lire_registre(reg))['actifs'],1)
                r=subprocess.run([sys.executable,__file__,'partager',c['id'],'--registre',str(reg),'--date','2026-01-05'],
                                 capture_output=True,text=True,stdin=subprocess.DEVNULL,encoding='utf-8')
                self.assertIn('inchangé',r.stdout);self.assertEqual(lire_registre(reg)[c['id']]['date'],'2026-01-01')   # jamais réécrit
                c2=copy.deepcopy(c);c2['usage_fige_le']='2025-12-31';c2['codage']['debut']='2026-01-01'
                with self.assertRaises(ValueError):valider_base([c2],registre=lire_registre(reg))   # date différente du registre
                reg.write_text(reg.read_text(encoding='utf-8')*2,encoding='utf-8')
                with self.assertRaises(ValueError):lire_registre(reg)          # doublon : un partage ne se réécrit pas
        def test_placebo(self):
            # 0.7.4 (décision 3) : placebo d'homologie reproductible, absent sans base.
            base=charger(RACINE/'assets/base-de-cas.exemple.jsonl')
            e=lire_etat('[2026-09 | 3 mois] POLARITÉ@7[F] + CONTRAINTE@6[F]')
            r1=calculer(e,'apparait','SEU@7',base,asof='2026-09-20',placebo=True)
            r2=calculer(e,'apparait','SEU@7',base,asof='2026-09-20',placebo=True)
            self.assertEqual(r1['placebo'],r2['placebo']);self.assertEqual(r1['placebo']['tirages'],P['placebo_tirages'])
            self.assertEqual(r1['placebo']['cas_tires'],r1['c_A'])
            self.assertLessEqual(r1['placebo']['plage_90'][0],r1['placebo']['plage_90'][1])
            self.assertEqual(r1['p'],calculer(e,'apparait','SEU@7',base,asof='2026-09-20')['p'])   # p inchangé par le placebo
            self.assertIsNone(calculer(e,'apparait','SEU@7',[],placebo=True)['placebo'])
            self.assertNotEqual(graine_placebo(e,'apparait','SEU@7','2026-09-20'),graine_placebo(e,'apparait','SEU@7','2026-09-21'))
            p=forecast(version_regles='0.7.4',probabilite=.3,p_placebo=.25,graine_placebo=7,apport_homologie=.05)
            self.assertTrue(valider_journal([p]))
            with self.assertRaises(ValueError):valider_journal([dict(p,apport_homologie=.1)])
            q=dict(p);q.pop('p_placebo')
            with self.assertRaises(ValueError):valider_journal([q])        # requis depuis 0.7.4
        def test_v4_sceau_dossier(self):
            # 0.7.4 (décision 1) : à compter de v4_dossier_depuis, sceau de dossier publié requis pour V4.
            sc='b'*64
            def apres(**kw):
                c=calc_reel(dossier={'sceau':sc});c['contexte']['date_information']='2026-11-01'
                x=reel(date='2026-11-01',echeance='2027-02-01',etat_present='[2026-11-01 | 3 mois] POLARITÉ@7[f]',calcul=c,
                       preuve_prepublication={'source':'https://github.com/exemple/depot/releases/tag/v1','date':'2026-11-02'})
                x.update(kw);x['preuve_prepublication']['empreinte_prevision']=empreinte_prevision(x);return x
            sco=lambda i:{'type':'score','id':i,'date':'2027-02-02','issue':0,'preuve':'registre'}
            self.assertEqual(score_result([apres(),sco('P-1')])['questions_eligibles'],0)          # pas de sceau publié
            ok=apres(preuve_dossier={'source':'https://github.com/exemple/depot/commit/abc','date':'2026-11-01','sceau':sc})
            self.assertEqual(score_result([ok,sco('P-1')])['questions_eligibles'],1)
            tard=apres(preuve_dossier={'source':'https://github.com/exemple/depot/commit/abc','date':'2026-11-02','sceau':sc})
            self.assertEqual(score_result([tard,sco('P-1')])['questions_eligibles'],0)           # publié après la date d'information
            with self.assertRaises(ValueError):
                valider_journal([apres(preuve_dossier={'source':'https://x.org','date':'2026-11-01','sceau':'c'*64})])   # autre sceau
            self.assertEqual(score_result([reel(),score()])['questions_eligibles'],1)             # avant la date : non rétroactif
        def test_recherches_a7(self):
            # 0.7.4 (décision 4) : plancher sur les familles couvertes, pas sur un nombre.
            d=self._dossier();self.assertTrue(dossier_valider(d)['complet'])
            d=self._dossier();d['recherches']=[r for r in d['recherches'] if r['famille']!='contradiction' or r['cartes']!=['POL@7']]
            r=dossier_valider(d);self.assertFalse(r['complet']);self.assertTrue(any('POL@7 : aucune requête de contradiction' in m for m in r['manques']))
            d=self._dossier();d['recherches']=[r for r in d['recherches'] if r['cartes']!=['CTR@6','HIE@6']]
            self.assertTrue(any('paire' in m for m in dossier_valider(d)['manques']))
            d=self._dossier();d['recherches'][0]['requete']='signes de polarité entre A et B'
            self.assertTrue(any('nom de la carte' in m for m in dossier_valider(d)['manques']))
            d=self._dossier();d['recherches']+= [dict(d['recherches'][0])]*10       # dix fois la même : comptée une fois
            self.assertTrue(any('répétée' in m for m in dossier_valider(d)['manques']))
            for bad in ({'famille':'autre','cartes':['POL@7'],'requete':'x'},{'famille':'observation','cartes':['RES@7'],'requete':'x'},
                        {'famille':'observation','cartes':['POL@7'],'requete':''}):
                d=self._dossier();d['recherches'].append(bad)
                with self.assertRaises(ValueError):dossier_valider(d)
            d=self._dossier();d.pop('recherches');self.assertFalse(dossier_valider(d)['complet'])
        def test_confronter(self):
            # 0.7.5 : matrice confrontée aux observations, classée par la règle du moteur.
            r=confronter(charger(RACINE/'assets/cas-reels.jsonl'))
            self.assertEqual((r['apparitions'],r['classes']['non_atteignable'],r['classes']['meme_strate']),(3,2,1))
            self.assertEqual({d['apparition'] for d in r['divergences']},{'CTR@8','TRC@5'})
            r=confronter(charger(RACINE/'assets/base-de-cas.exemple.jsonl'))
            self.assertEqual((r['apparitions'],r['classes']['etat_nul'],r['classes']['inter_strates_abaissee'],r['classes']['non_atteignable']),(22,1,1,0))
            self.assertEqual((r['age']['0']['occasions'],r['age']['0']['maintiens']),(80,68))
            c=fake_case(count=1);c['issue']['etat']=c['issue']['etat'].replace('POLARITÉ@7[f]','POLARITÉ@7[f] + PÉRIODICITÉ@7[f]')
            self.assertGreaterEqual(confronter([c])['apparitions'],1)
        def test_tests_exacts(self):
            self.assertAlmostEqual(test_signe([-1]*32+[1]*18)['p_amelioration'],0.0325,places=4)
            self.assertEqual(test_signe([0,0])['n'] if test_signe([0,0]) else 0,0)            # nuls exclus
            w=test_wilcoxon([-.1,-.2,-.3,-.4,.05]);self.assertEqual(w['W_plus'],1);self.assertAlmostEqual(w['p_amelioration'],2/32)
            self.assertAlmostEqual(test_wilcoxon([-1,-1,1,-2])['p_amelioration'],.25)        # rangs moyens
            # apport des cartes : la lecture vient du test, pas de la moyenne seule
            ps=[forecast(f'P-{i}',episode_id=f'e{i}',version_regles='0.5.0',p_sans_cartes=.5,probabilite=.4 if i%2 else .6) for i in range(6)]
            r=score_result(ps+[score(f'P-{i}',0) for i in range(6)])
            a_=r['apport_des_cartes'];self.assertEqual(a_['par_episode']['episodes'],6)
            self.assertIn('non distinguable',a_['lecture'])
            self.assertIsNotNone(a_['log_avec'])
        def test_meme_epreuve(self):
            # 0.7.5 : une révision (même épisode, événement, échéance) garde l'épreuve.
            a_=forecast('P-1');b_=forecast('P-2',probabilite=.3)
            self.assertTrue(valider_journal([a_,b_]))
            b_['resolution']=dict(b_['resolution'],critere='rupture exécutée')
            with self.assertRaises(ValueError):valider_journal([a_,b_])
            b_['episode_id']='episode-B';self.assertTrue(valider_journal([a_,b_]))       # autre objet : autre épreuve admise
        def test_priors_publies(self):
            e=lire_etat('[2026-09 | 3 mois] POLARITÉ@7[F] + CONTRAINTE@6[F]')
            r=calculer(e,'apparait','SEU@7',charger(RACINE/'assets/base-de-cas.exemple.jsonl'),asof='2026-09-20')
            ap=r['a_priori'];self.assertAlmostEqual(ap['poids_a_priori_f'],P['k0_frequence']/(ap['effectif_reference']+P['k0_frequence']))
            self.assertAlmostEqual(r['poids_a_priori_p'],P['k']/(r['n_A']+P['k']))
            lo,hi=ap['intervalle_f'];self.assertTrue(lo<ap['reference_interne']<hi)
            self.assertEqual(calculer(e,'apparait','SEU@7',[],sans_cartes=True)['p'],calculer(e,'apparait','SEU@7',[])['a_priori']['reference_interne'])  # p_sans_cartes = f
        def test_classe_source_duree(self):
            c=self._f_case('POLARITÉ@7 : CONTRAINTE → (deux camps) ; SEUIL → (aucune rupture)');c['sequence'][0]['mots'][0].pop('classe_source')
            with self.assertRaises(ValueError):valider_base([c])
            c['sequence'][0]['mots'][0]['classe_source']='rumeur'
            with self.assertRaises(ValueError):valider_base([c])
            d=self._dossier();d['evenements'][0].update(duree_caracteristique_jours=5,source_duree='OMM')
            with self.assertRaises(ValueError):dossier_valider(d)            # 5 j contre une fenêtre de 3 mois, générique
            d['evenements'][0]['justification_temporalite']='question sur la récurrence, pas sur un épisode';self.assertTrue(dossier_valider(d)['conforme'])
            d=self._dossier();d['evenements'][0].update(duree_caracteristique_jours=200,source_duree='série publiée');self.assertTrue(dossier_valider(d)['conforme'])
        def test_sonde(self):
            # 0.7.6 : variable sonde sur les paramètres ; référence sans multiplicateurs, cas gardés.
            base=base_active(charger(RACINE/'assets/base-de-cas.exemple.jsonl'),'2026-09-20',True)
            e=lire_etat('[2026-09 | 3 mois] POLARITÉ@7[F] + CONTRAINTE@6[F]');avant=json.dumps(P,sort_keys=True)
            r=sonde_matrice(e,'apparait','SEU@7',base,{'asof':'2026-09-20'},1,'presence','aretes',40)
            self.assertEqual(json.dumps(P,sort_keys=True),avant)                  # paramètres restaurés
            self.assertEqual(r,sonde_matrice(e,'apparait','SEU@7',base,{'asof':'2026-09-20'},1,'presence','aretes',40))   # reproductible
            self.assertAlmostEqual(r['p_reel'],calculer(e,'apparait','SEU@7',base,asof='2026-09-20')['p'])
            self.assertAlmostEqual(r['apport_cas']+r['apport_matrice_reel'],r['p_reel']-r['p_sans_cartes'])
            self.assertTrue(0<=r['centile_reel']<=1)
            ri=sonde_matrice(e,'apparait','SEU@7',base,{'asof':'2026-09-20'},1,'presence','inerties',10)
            self.assertEqual(ri['p_sonde_90'][0],ri['p_sonde_90'][1])           # inerties hors d'une apparition à un pas
            rp=sonde_matrice(e,'apparait','SEU@7',base,{'asof':'2026-09-20'},3,'presence','inerties',10)
            self.assertLess(rp['p_sonde_90'][0],rp['p_sonde_90'][1])            # mais dans la chaîne à plusieurs pas
        def test_kish_attenuation(self):
            base=base_active(charger(RACINE/'assets/base-de-cas.exemple.jsonl'),'2026-09-20',True)
            e=lire_etat('[2026-09 | 3 mois] POLARITÉ@7[F] + CONTRAINTE@6[f]')
            r=calculer(e,'apparait','SEU@7',base,asof='2026-09-20')
            self.assertTrue(0<r['n_eff_kish']<=r['c_A']+1e-9);self.assertTrue(0<r['part_cas_le_plus_lourd']<=1)
            sb=sensibilite(e,'apparait','SEU@7',base,{'asof':'2026-09-20'},1,'presence',
                           {'POL@7':{'corroboration':'unique','passage':'soutient'}})
            self.assertLess(sb['effet_attenuation']['force'],0)                  # f atténue l'arête de CTR@6
            self.assertIn('corroboration_passage',sb['effet_attenuation'])
            self.assertIsNone(globals().get('ATTENUATION'))                     # crochet retiré après la sonde
            self.assertEqual(r['p'],calculer(e,'apparait','SEU@7',base,asof='2026-09-20')['p'])
        def test_ombre_causale(self):
            # 0.7.56 (§33) : règle des médiateurs et ablation, hors du p publié.
            base=base_active(charger(RACINE/'assets/base-de-cas.exemple.jsonl'),'2026-09-20',True)
            e=lire_etat('[2026-09 | 3 mois] CROISSANCE@7[f] + CONTRAINTE@7[f]')
            r=calculer(e,'apparait','SEU@7',base,asof='2026-09-20')
            sb=sensibilite(e,'apparait','SEU@7',base,{'asof':'2026-09-20'},1,'presence')
            self.assertEqual(sb['mediation']['mediateurs_retires'],['CTR@7'])     # CRO → CTR → SEU et CRO → SEU
            self.assertEqual(sorted(x['retire'] for x in sb['ablation']),['CRO@7','CTR@7'])
            self.assertFalse(globals().get('MEDIATION'))                         # crochet retiré après la sonde
            self.assertEqual(r['p'],calculer(e,'apparait','SEU@7',base,asof='2026-09-20')['p'])
            e2=lire_etat('[2026-09 | 3 mois] CROISSANCE@7[f] + ÉMERGENCE@7[f]')  # paire mutuelle : rien d'écarté
            sb2=sensibilite(e2,'apparait','CTR@7',base,{'asof':'2026-09-20'},1,'presence')
            self.assertEqual(sb2['mediation']['mediateurs_retires'],[])
        def test_circularite_ideologie(self):
            d=self._dossier();d['mots'][0]['garantie']['mecanisme']='c’est une polarité parce que deux camps'
            r=dossier_valider(d);self.assertTrue(any('nomme la carte' in m for m in r['manques']));self.assertFalse(r['complet'])
            self.assertFalse(any('nomme la carte' in m for m in dossier_valider(self._dossier())['manques']))
            c=self._f_case('POLARITÉ@7 : CONTRAINTE → (deux camps) ; SEUIL → (aucune rupture)')
            c['codage']['codeurs'][0].update(signe_suffisant='execution',declare_le='2025-12-31');self.assertEqual(valider_base([c])['actifs'],1)
            c['codage']['codeurs'][0]['declare_le']='2026-02-01'
            with self.assertRaises(ValueError):valider_base([c])            # déclaration rétrospective
            c['codage']['codeurs'][0].update(signe_suffisant='intuition',declare_le='2025-12-31')
            with self.assertRaises(ValueError):valider_base([c])
            cv=confronter(charger(RACINE/'assets/base-de-cas.exemple.jsonl'))['couverture_aretes']
            self.assertEqual(cv['aretes'],66);self.assertLessEqual(cv['avec_dix_occasions'],cv['avec_une_occasion'])
        def test_ancrage_dedouble(self):
            # 0.7.7 (décision 1) : publication et ancrage séparés ; p inchangé.
            base=base_active(charger(RACINE/'assets/base-de-cas.exemple.jsonl'),'2026-09-20',True)
            e=lire_etat('[2026-09 | 3 mois] POLARITÉ@7[F] + CONTRAINTE@6[F]')
            r=calculer(e,'apparait','SEU@7',base,asof='2026-09-20');ap=r['a_priori']
            self.assertTrue(P['n_min_publication']<=ap['effectif_reference']<P['n_min_ancrage'])
            self.assertTrue(ap['publie']);self.assertFalse(ap['ancrage']);self.assertIsNotNone(r['comparateur'])
            old=P['n_min_ancrage'];P['n_min_ancrage']=1
            try:self.assertEqual(calculer(e,'apparait','SEU@7',base,asof='2026-09-20')['p'],r['p'])
            finally:P['n_min_ancrage']=old
            self.assertIsNone(calculer(e,'apparait','SEU@7',[])['comparateur'])               # base vide : rien à publier
        def test_v4_statut(self):
            # 0.7.7 (décisions 2 et 3) : gain absolu, test exact, effectif = max(plancher, requis par σ̂).
            dm=lambda n,dbar,sd,neg:{'episodes':n,'d_moyen':dbar,'sigma_d':sd,'erreur_type':sd/math.sqrt(n),
                                      'test_signe':test_signe([-1]*neg+[1]*(n-neg)),'test_wilcoxon':test_wilcoxon([-1]*neg+[1]*(n-neg))}
            self.assertEqual(v4_statut(dm(3,-.05,.001,3))['statut'],'non encore évalué')         # σ̂ minuscule : le plancher tient
            self.assertTrue(v4_statut(dm(60,-.03,.05,45))['statut'].startswith('jalon interne atteint'))
            self.assertEqual(v4_statut(dm(60,-.01,.05,45))['statut'],'jalon interne non atteint')   # gain trop petit
            self.assertEqual(v4_statut(dm(60,-.03,.05,31))['statut'],'jalon interne non atteint')   # test non significatif
            r=v4_statut(dm(60,-.03,.10,45));self.assertEqual(r['effectif_requis'],126);self.assertEqual(r['statut'],'non encore évalué')
            self.assertEqual(v4_statut(None)['statut'],'non encore évalué')
        def test_discriminant_weibull(self):
            self.assertTrue(discriminant([{'probabilite':.30,'p_sans_cartes':.27,'p_placebo':.295}]))
            self.assertFalse(discriminant([{'probabilite':.30,'p_sans_cartes':.29,'p_placebo':.305}]))
            self.assertIsNone(discriminant([{'probabilite':.30}]))
            ps=[forecast(f'P-{i}',episode_id=f'e{i}',version_regles='0.5.0',p_sans_cartes=.5,probabilite=.4 if i%2 else .49) for i in range(4)]
            r=score_result(ps+[score(f'P-{i}',0) for i in range(4)]);self.assertIn('v4_discriminant',r);self.assertIn('v4',r)
            lo,hi=wilson(68,80);self.assertTrue(lo<.85<hi);self.assertIsNone(wilson(0,0))
            cw=confronter(charger(RACINE/'assets/base-de-cas.exemple.jsonl'))['test_age']['critere_weibull']
            self.assertFalse(cw['applicable'])                                                  # base fictive : jamais applicable
        def _comparateur(self,x,**kw):
            c={'methode':'décomposition de Fermi et taux de base externe','probabilite':.34,'scelle_le':x['date'],
               'source':'https://github.com/exemple/depot/commit/abc123','aveugle':True,'elements_vus':['question','resolution','echeance'],'contexte':'separe'}
            c.update(kw);c['empreinte']=empreinte_comparateur(x['question'],x['evenement'],c['probabilite'],c['scelle_le'],c['source'],c['methode'])
            return c
        def test_comparateur_controles(self):
            # 0.7.8 : comparateur externe aveugle, scellé, publié, non tautologique.
            x=forecast(version_regles='0.7.8');x['comparateur_externe']=self._comparateur(x);self.assertTrue(valider_journal([x]))
            for kw in ({'scelle_le':'2026-01-02'},{'source':'http://exemple.org/p'},{'methode':'lecture des SEUIL ancrés'},
                       {'methode':'analogie POL'},{'elements_vus':['question','etat_present']},{'elements_vus':['evenement']},
                       {'elements_vus':['strate']},{'contexte':'ailleurs'},{'aveugle':'oui'}):
                y=forecast(version_regles='0.7.8');y['comparateur_externe']=self._comparateur(y,**kw)
                with self.assertRaises(ValueError,msg=str(kw)):valider_journal([y])
            y=forecast(version_regles='0.7.8');y['comparateur_externe']=self._comparateur(y);y['comparateur_externe']['probabilite']=.4
            with self.assertRaises(ValueError):valider_journal([y])                              # modifié après scellé
            y=forecast(version_regles='0.7.8',question='Un SEUIL est-il franchi ?');y['comparateur_externe']=self._comparateur(y)
            with self.assertRaises(ValueError):valider_journal([y])                              # question tautologique
            y=forecast(version_regles='0.7.8');y.pop('comparateur_externe')
            with self.assertRaises(ValueError):valider_journal([y])                              # requis depuis 0.7.8
            z=forecast(version_regles='0.4.0');z.pop('comparateur_externe');self.assertTrue(valider_journal([z]))   # journaux antérieurs
            p_=forecast('P-A',partition='part',probabilite=.5,version_regles='0.7.8');p_['comparateur_externe']=self._comparateur(p_)
            q_=forecast('P-B',partition='part',probabilite=.5,version_regles='0.7.8',evenement='HIE@7 apparait')
            with self.assertRaises(ValueError):valider_journal([p_,q_])                          # pas sur une partition
        def test_comparateur_rapport(self):
            ps=[]
            for i in range(6):
                x=forecast(f'P-{i}',episode_id=f'e{i}',version_regles='0.7.8',probabilite=.2 if i%3 else .6)
                x['comparateur_externe']=self._comparateur(x,probabilite=.3);ps.append(x)
            c_=forecast('P-9',episode_id='e9',version_regles='0.7.8');c_['comparateur_externe']=self._comparateur(c_,contexte='meme_session');ps.append(c_)
            r=score_result(ps+[score(f'P-{i}',0) for i in list(range(6))+[9]])
            ce=r['comparateur_externe'];self.assertEqual(ce['questions'],6);self.assertEqual(ce['contamines_exclus'],1)
            self.assertEqual(ce['ameliorations']+ce['degradations'],6);self.assertEqual(ce['par_episode']['episodes'],6)
            self.assertIn('v4_comparateur',r);self.assertIn('v4_comparateur_discriminant',r)
            self.assertEqual(r['v4']['reference'],'vue_exterieure')                          # 0.7.41 (était « inertie »)
        def test_v4_reference_defaut(self):
            # 0.7.41 : référence par défaut = vue extérieure ; chaque épisode qui la porte entre dans v4.
            ps=[forecast(f'P-{i}',episode_id=f'e{i}',version_regles='0.7.8',probabilite=.2,vue_exterieure=.05) for i in range(4)]
            r=score_result(ps+[score(f'P-{i}',0) for i in range(4)])
            self.assertEqual(P['v4_reference'],'vue_exterieure')
            self.assertEqual(r['v4']['reference'],'vue_exterieure');self.assertEqual(r['statut'],'non encore évalué')
            self.assertEqual(r['v4']['episodes'],r['episodes_comparables'])
        def test_references_gabarit_tautologie(self):
            ok={'SEU@7 apparait':{'frequence':.05,'source':'UCDP, onset dataset','definition':'nouveau conflit armé interétatique','periode':'1990-2020','fenetre':'3 mois','disponible_le':'2026-01-01'}}
            self.assertEqual(erreurs_references(ok),[])
            self.assertTrue(erreurs_references({'SEU@7 apparait':dict(ok['SEU@7 apparait'],source=GABARIT_SOURCE)}))
            self.assertTrue(erreurs_references({'SEU@7 apparait':dict(ok['SEU@7 apparait'],definition='épisodes de POLARITÉ')}))
            with self.assertRaises(ValueError):refs_valider({'SEU@7 apparait':dict(ok['SEU@7 apparait'],definition='cas où un SEUIL est franchi')},'3 mois','2026-02-01')
        def test_export_codeur(self):
            cas=schema_documente();r=export_codeur(cas)
            dump=json.dumps(r,ensure_ascii=False)
            for k in CLES_CODAGE:self.assertNotIn(f'"{k}"',dump)
            self.assertNotIn('POLARITÉ@7',dump);self.assertTrue(r['sequence'][0]['faits'])
            self.assertEqual(export_codeur(cas),r)                                               # ordre stable
        def test_accord(self):
            # 0.7.9 : κ, PABAK, accords spécifiques, deux taux de manque ; κ indéfini déclaré indéfini.
            r=accord(0,0,0,118);self.assertIsNone(r['kappa']);self.assertEqual(r['pabak'],1);self.assertTrue(r['verdict'].startswith('sans objet'))
            r=accord(0,1,1,116);self.assertAlmostEqual(r['kappa'],-0.0086,places=3);self.assertAlmostEqual(r['pabak'],0.966,places=3)
            self.assertAlmostEqual(accord(0,1,0,117)['kappa'],0.0,places=9)                 # un seul désaccord : κ = 0, pas 0,496
            r=accord(0,87,0,1801);self.assertAlmostEqual(r['kappa'],0);self.assertAlmostEqual(r['pabak'],0.908,places=3)
            self.assertEqual(r['accord_positif'],0);self.assertTrue(r['verdict'].startswith('insuffisant'))   # PABAK seul se tromperait
            r=accord(35,52,5,1796);self.assertAlmostEqual(r['manque_second'],0.598,places=3);self.assertTrue(r['verdict'].startswith('insuffisant'))
            self.assertEqual(accord(35,5,5,1843)['verdict'],'rapportable')
            self.assertTrue(accord(1,1,1,115)['verdict'].startswith('non estimable'))
            with self.assertRaises(ValueError):accord(-1,0,0,1)
            # 0.7.18 : forte prévalence (Di Eugenio et Glass 2004) : PABAK 0,80 mais κ < 0 ; refusé par le contrôle des absences.
            r=accord(90,5,5,0);self.assertAlmostEqual(r['kappa'],-0.0526,places=3);self.assertAlmostEqual(r['pabak'],.8)
            self.assertTrue(r['verdict'].startswith('insuffisant : forte prévalence'))
            self.assertAlmostEqual(accord(1,1,3,5)['alpha_krippendorff'],1-19*4/(14*6))                 # Meg et Owen : α = 0,095
            self.assertEqual(accord(35,5,5,1843)['verdict'],'rapportable')                              # faible prévalence inchangée
        def test_support_garantie(self):
            # 0.7.10 : support du mécanisme (Toulmin) ; régression bornée, date ≤ information.
            g={'mecanisme':'m','attendu':'a','contredirait':'c'}
            self.assertEqual(controle_support('POL@7',{'garantie':g},False),[])
            self.assertTrue(controle_support('POL@7',{'garantie':g},True))                       # absent, requis
            ok=dict(g,support={'type':'loi','reference':'loi n° 1','disponible_le':'2020-01-01'})
            self.assertEqual(controle_support('POL@7',{'garantie':ok},True,'2026-01-01'),[])
            for bad in ({'type':'argument','reference':'r','disponible_le':'2020-01-01'},{'type':'avis','reference':'r','disponible_le':'2020-01-01'},
                        {'type':'texte','reference':'','disponible_le':'2020-01-01'},{'type':'texte','reference':'r','disponible_le':'2027-01-01'},
                        {'type':'texte','reference':'m','disponible_le':'2020-01-01'}):
                self.assertTrue(controle_support('POL@7',{'garantie':dict(g,support=bad)},True,'2026-01-01'),bad)
            d=self._dossier();d['mots'][0]['garantie'].pop('support')
            with self.assertRaises(ValueError):dossier_valider(d)                                  # un dossier l'exige
            c=self._f_case('POLARITÉ@7 : CONTRAINTE → (deux camps, pas une règle) ; SEUIL → (aucun passage irréversible)');c['version_regles']='0.7.9'
            c['sequence'][0]['mots'][0]['garantie'].pop('support');self.assertEqual(valider_base([c])['actifs'],1)   # prospectif
        def test_refutation_qui_annule(self):
            ok={'mecanisme':'m','attendu':'positions durcies','contredirait':'concession acceptée'};op={'acteur':'x','avant':'a','apres':'b'}
            self.assertEqual(controle_garantie('POL@7',{'garantie':ok,'option':op},True),[])
            self.assertTrue(controle_garantie('POL@7',{'garantie':dict(ok,contredirait='Positions  durcies'),'option':op},True))
            d=self._dossier();d['mots'][0]['garantie']['contredirait']='si ce n’était pas une polarité'
            r=dossier_valider(d);self.assertFalse(r['complet']);self.assertTrue(any('contredirait nomme' in m_ for m_ in r['manques']))
        def test_repetabilite(self):
            r=accord(35,5,5,1843,True,90);self.assertEqual(r['type'],'repetabilite');self.assertEqual(r['verdict'],'rapportable')
            self.assertEqual(r['kappa'],accord(35,5,5,1843)['kappa'])                              # même statistique
            self.assertTrue(accord(35,5,5,1843,True,3)['verdict'].startswith('non recevable'))     # mémoire du codage
            with self.assertRaises(ValueError):accord(1,1,1,1,True)
            self.assertEqual(accord(35,5,5,1843)['type'],'reproductibilite')
        def test_references_interet(self):
            ok={'frequence':.05,'source':'UCDP, onset dataset','definition':'nouveau conflit armé interétatique','periode':'1990-2020','fenetre':'3 mois','disponible_le':'2026-01-01'}
            self.assertEqual(erreurs_references({'SEU@7 apparait':dict(ok,interet='aucun',referentiel='date de déclenchement')}),[])
            self.assertTrue(erreurs_references({'SEU@7 apparait':dict(ok,interet='promoteur')}))
            self.assertTrue(erreurs_references({'SEU@7 apparait':dict(ok,interet='declare')}))
            self.assertEqual(erreurs_references({'SEU@7 apparait':dict(ok,interet='declare',fourni_par='association professionnelle')}),[])
            self.assertTrue(erreurs_references({'SEU@7 apparait':dict(ok,interet='peut-être')}))
            self.assertTrue(erreurs_references({'SEU@7 apparait':dict(ok,referentiel=' ')}))
        def test_procedure_jugement(self):
            j=lambda d,**kw:dict({'type':'prevision','id':'J'+d,'date':d,'echeance':'2027-01-01','version_regles':'0.7.10','origine':'jugement',
                                  'question':'q','evenement':'X élu','episode_id':'E','refutation':'non','probabilite':.6,'rejeu':False,'fictif':False,
                                  'resolution':{'source':'s','critere':'c','seuil':'t'}},**kw)
            valider_journal([j('2026-10-30')])                                                      # avant la date : facultatif
            with self.assertRaises(ValueError):valider_journal([j('2026-11-02')])                  # après : requis
            valider_journal([j('2026-11-02',procedure='compromis')])
            with self.assertRaises(ValueError):valider_journal([j('2026-10-30',procedure='intuition')])
            r=score_result([j('2026-11-02',procedure='simulation'),{'type':'score','id':'J2026-11-02','date':'2027-01-02','issue':1,'preuve':'p'}])
            self.assertEqual(r['jugements']['par_procedure']['simulation']['questions'],1)
        def test_passage_deux_diagnostics(self):
            # 0.7.11 : « ne permet pas de conclure » scindé ; remèdes opposés, aucun n'ancre.
            for r_,mot_ in (('absent_de_la_piece','élargir'),('non_soutenu','retirer'),('insuffisant','absent_de_la_piece')):
                e_=controle_passage('POL@7',{'passage':{'localisation':'p. 2','relation':r_}},'f',False)
                self.assertTrue(e_ and mot_ in e_[0],(r_,e_))
        def test_independance(self):
            it={'corroboration':'independantes','source':'A ; B'}
            self.assertEqual(controle_corroboration('POL@7',it),[])                                  # fiche antérieure : facultatif
            self.assertTrue(controle_corroboration('POL@7',it,True))
            self.assertEqual(controle_corroboration('POL@7',dict(it,independance={'critere':'origine','motif':'m'}),True),[])
            for bad in ({'critere':'nom','motif':'m'},{'critere':'origine','motif':' '},'origine'):
                self.assertTrue(controle_corroboration('POL@7',dict(it,independance=bad),True),bad)
            d=self._dossier();d['mots'][0].pop('independance')
            with self.assertRaises(ValueError):dossier_valider(d)
        def test_cloture(self):
            # 0.7.11 : clôture complète, empreinte stable, comparaison qui voit un changement hors témoin.
            base=[fake_case()];a=cloture(base);b=cloture(copy.deepcopy(base))
            self.assertEqual(a['empreinte'],b['empreinte']);self.assertTrue(a['consequences']>0 and a['probant'])
            self.assertTrue(comparer_clotures(a,b)['conservative'])
            k_=sorted(a['resultats'])[0];b['resultats'][k_]=dict(b['resultats'][k_],p=0.5)
            c_=comparer_clotures(a,b);self.assertEqual(c_['changees'],1);self.assertFalse(c_['conservative'])
            old=P['k'];P['k']=7.0
            try:self.assertFalse(comparer_clotures(a,cloture(base))['conservative'])                    # un paramètre changé se voit
            finally:P['k']=old
        def test_empreinte_portable(self):
            # 0.7.18 : un écart au-delà du bit, sous 10 décimales, change l'empreinte stricte, pas la portable.
            base=[fake_case()];a=cloture(base);b=copy.deepcopy(a)
            k_=sorted(b['resultats'])[0];b['resultats'][k_]['p']+=1e-15
            self.assertNotEqual(empreinte(a['resultats']),empreinte(b['resultats']))
            self.assertEqual(empreinte(arrondir(a['resultats'])),empreinte(arrondir(b['resultats'])))
            c_=comparer_clotures(a,b);self.assertEqual((c_['changees'],c_['changees_hors_arrondi']),(1,0))
            self.assertEqual(a['empreinte_portable'],empreinte(arrondir(a['resultats'])))

        def test_voisins(self):
            # 0.7.18 : diagnostic de la base ; sur la démonstration, 69/78 jumeaux H1 non triviaux, ū = 0,705.
            r=voisins(charger(RACINE/'assets/base-de-cas.exemple.jsonl'))
            self.assertEqual((r['transitions'],r['jumeau_H1_non_trivial'],r['au_dessus_jaccard_H15']),(78,69,73))
            self.assertAlmostEqual(r['unicite']['moyenne'],55/78,places=9);self.assertEqual(r['unicite']['concurrence_max'],4)
            un=voisins([fake_case()]);self.assertEqual(un['sans_voisin_non_trivial'],un['transitions'])   # un cas seul : aucun voisin
            self.assertEqual(r['par_strate'],{'6':{'cas':40,'transitions':78},'7':{'cas':40,'transitions':78}})
            self.assertEqual((r['etats_distincts'],r['co_occurrence']['toujours_ensemble']),(111,0))
            self.assertEqual([bande_verbale(x) for x in (.02,.05,.22,.5,.6,.9,.97)],
                             ['probabilité très éloignée','très improbable','improbable','chance approximativement égale','probable','très probable','presque certain'])
            self.assertIsNone(voisins([]))

        def test_e_processus(self):
            # 0.7.12 (audit V34, D4) : valide à tout instant ; franchit vite sur un gain net, jamais sans gain.
            self.assertIsNone(e_processus([]))
            r=e_processus([-.3]*40);self.assertTrue(r['franchi_a_l_episode'] is not None and r['e_valeur']>=r['seuil'])
            r=e_processus([0.]*500);self.assertIsNone(r['franchi_a_l_episode']);self.assertAlmostEqual(r['e_max'],1.)
            r=e_processus([-.02]*500,P['v4_gain_abs']);self.assertIsNone(r['franchi_a_l_episode'])   # gain sous le seuil V4
            import random as rd_;g=rd_.Random(5);fr=0
            for _ in range(200):                                                               # H0 vraie : E[d] = 0
                if e_processus([g.choice((-.2,.2)) for _ in range(100)])['franchi_a_l_episode']:fr+=1
            self.assertLessEqual(fr/200,P['v4_alpha']+.03)                                     # Ville : ≤ α à tout instant
            dm=differentiel([{'episode_id':f'E{i}','date':f'2026-01-{i+1:02d}','brier':.1,'ref':.3} for i in range(25)],'ref')
            self.assertIsNotNone(v4_statut(dm)['sequentiel'])
        def test_sorties_audit_v34(self):
            # 0.7.12 : paire (sans cartes, avec cartes), bande d'horizon, homologie indiscernable — aucun p changé.
            import subprocess
            cmd=[sys.executable,__file__,'calculer','--demo','--base',str(RACINE/'assets/base-de-cas.exemple.jsonl'),'--etat',
                 '[2026-09 | 3 mois] POLARITÉ@7[F] + CONTRAINTE@6[F]','--liaison','CONTRAINTE@6 echo POLARITÉ@7',
                 '--evenement','SEUIL@7 apparait','--temporalite','generique','--json']
            r=json.loads(subprocess.run(cmd,capture_output=True,text=True,encoding='utf-8').stdout)
            self.assertEqual(r['resultat_principal']['p_avec_cartes'],r['p']);self.assertEqual(r['resultat_principal']['p_sans_cartes'],r['p_sans_cartes'])
            self.assertEqual(sorted(r['bande_horizon']['pas']),['1','3','6']);self.assertAlmostEqual(r['bande_horizon']['pas']['1']['p'],r['p'])
            self.assertIs(r['homologie_discernable'],False);self.assertTrue(any('indiscernable' in x for x in r['drapeaux']))
            # 0.7.18 : le placebo publie aussi un centile, cohérent avec le drapeau.
            self.assertTrue(0<=r['centile_placebo']<=1);self.assertAlmostEqual(r['placebo']['resolution'],1/P['placebo_tirages'])
            self.assertTrue(.05<=r['centile_placebo']<=.95)
        def test_ecart_marginales(self):
            # 0.7.13 : le noyau concurrent ne reproduit pas les marginales ; l'écart est publié.
            e=lire_etat('[2026-01-01 | 3 mois] POLARITÉ@7[F] + CONTRAINTE@6[f]')
            r=trajectoires(e,1,[],{})
            em=r['ecart_marginales_pas1'];self.assertTrue(em['evenements'])
            x=em['evenements'][0];self.assertAlmostEqual(x['ecart'],x['p_trajectoire']-x['p_isole'])
            self.assertTrue(all(x_['p_trajectoire']<=x_['p_isole']+1e-12 for x_ in em['evenements']))   # concurrence : jamais au-dessus
        def test_variantes_codage(self):
            import subprocess
            cmd=[sys.executable,__file__,'calculer','--demo','--base',str(RACINE/'assets/base-de-cas.exemple.jsonl'),'--etat',
                 '[2026-09 | 3 mois] POLARITÉ@7[F] + CONTRAINTE@6[f]','--evenement','SEUIL@7 apparait','--temporalite','generique','--json']
            r=json.loads(subprocess.run(cmd,capture_output=True,text=True,encoding='utf-8').stdout)
            v=r['variantes_codage'];self.assertEqual(v['mots_f'],['CTR@6']);self.assertEqual(len(v['variantes']),1)
            self.assertTrue(v['plage'][0]<=r['p']<=v['plage'][1])
        def test_noyau_joint(self):
            # 0.7.14 : marginales = p à 1e-12 ; sans exclusion, produit ; exclusions respectées ; masses publiées.
            r=noyau_joint(['A','B'],[.5,.5])
            self.assertAlmostEqual(r['p_aucun'],.25);self.assertAlmostEqual(r['p_deux_ou_plus'],.25);self.assertAlmostEqual(r['p_premier']['A'],.375)
            r=noyau_joint(['A','B','C'],[.1,.15,.3],[('A','B')])
            self.assertTrue(r['faisable']);self.assertLess(r['ecart_marginal_max'],1e-12)
            self.assertFalse(any('A + B' in c for c,_ in r['configurations']))
            self.assertFalse(noyau_joint(['A','B'],[.7,.6],[('A','B')])['faisable'])                 # 0,7 + 0,6 > 1 : impossible
            with self.assertRaises(ValueError):noyau_joint(['A'],[.5])
            t=trajectoires(lire_etat('[2026-01-01 | 3 mois] POLARITÉ@7[F] + CONTRAINTE@6[F]'),1,[],{})
            self.assertTrue(0<t['masse_simultanee_pas1']<1);self.assertIn('premier changement',t['estimande'])
        def test_modele_declare(self):
            import subprocess
            cmd=[sys.executable,__file__,'calculer','--demo','--etat','[2026-09 | 3 mois] POLARITÉ@7[F] + CONTRAINTE@6[F]',
                 '--liaison','CONTRAINTE@6 echo POLARITÉ@7','--evenement','SEUIL@7 apparait','--temporalite','generique','--json']
            r=json.loads(subprocess.run(cmd,capture_output=True,text=True,encoding='utf-8').stdout)
            self.assertAlmostEqual(r['modele']['champ']['produit_lambda'],2.16);self.assertEqual(r['modele']['liaisons_non_inferentielles'],['écho'])
            self.assertTrue(any('sans effet sur p' in x for x in r['drapeaux']))
        def test_manifeste_sans_fichiers_caches(self):
            # 0.7.15 : un paquet installé sans .gitattributes, .gitignore ni .github/ passe audit.
            fl=fichiers_livres()
            self.assertFalse(any(x.startswith('.') for r in fl for x in r.split('/')))
            self.assertIn('SKILL.md',fl);self.assertIn('scripts/moteur.py',fl)
            self.assertFalse(any('.github' in l or '.gitignore' in l for l in manifeste_texte().splitlines()))
        def test_forme_piece(self):
            # 0.7.16 : une pièce rétrospective, attribuée ou non datable ne soutient pas F ; f reste possible.
            ok={'localisation':'p. 2','relation':'soutient'}
            self.assertEqual(controle_passage('POL@7',{'passage':dict(ok,forme='prospective')},'F',True),[])
            for fo,mot in (('retrospective','antérieure'),('attribuee','source primaire'),('inclassable','non datable')):
                e=controle_passage('POL@7',{'passage':dict(ok,forme=fo)},'F',True);self.assertTrue(e and mot in e[0],(fo,e))
                self.assertEqual(controle_passage('POL@7',{'passage':dict(ok,forme=fo)},'f',False),[])
            self.assertTrue(controle_passage('POL@7',{'passage':dict(ok,forme='futur')},'f',False))
            two=[dict(ok,forme='retrospective'),dict(ok,localisation='p. 5')]
            self.assertEqual(controle_passage('POL@7',{'passage':two},'F',True),[])                   # une pièce prospective suffit
            self.assertTrue(controle_passage('POL@7',{'passage':two,'corroboration':'independantes'},'F',True))
        def test_programmation(self):
            d=self._dossier();d['evenements'][0]['temporalite']='programmee'
            with self.assertRaises(ValueError):dossier_valider(d)
            d['evenements'][0]['programmation']={'qui':'la commission électorale','engagement':'calendrier publié au Journal officiel'}
            self.assertTrue(dossier_valider(d)['conforme'])
        def test_rejets_audit(self):
            d=self._dossier();f=feuille_rejets(d)
            self.assertEqual(sorted(f['tirage']),['HIE@6','SEU@7']);self.assertNotIn('motif',json.dumps(f,ensure_ascii=False).lower().replace('motif du rejet',''))
            self.assertEqual(feuille_rejets(copy.deepcopy(d))['tirage'],f['tirage'])
            rej={cle_valide(k):v for k,v in d['rejets'].items()}
            au={'sceau_dossier':f['sceau_dossier'],'tirage':f['tirage'],'aveugle':True,'relecteur':'relecteur-B',
                'verdicts':[{'carte':k,'verdict':'annule' if i==0 else 'maintenu','justification':'x','motif_original':rej[k]} for i,k in enumerate(f['tirage'])],
                'taux_annulation':0.5}
            self.assertEqual(erreurs_audit_rejets(au,d),[])
            for mod in ({'aveugle':False},{'taux_annulation':1.0},{'tirage':list(reversed(f['tirage']))}):
                self.assertTrue(erreurs_audit_rejets(dict(au,**mod),d),msg=str(mod))
            b=copy.deepcopy(au);b['verdicts'][0]['motif_original']='autre';self.assertTrue(erreurs_audit_rejets(b,d))
            b=copy.deepcopy(au);b['verdicts']=b['verdicts'][:1];self.assertTrue(erreurs_audit_rejets(b,d))
        def test_concessions(self):
            d=self._dossier();d['etat']=d['etat'].replace('CONTRAINTE@6[F]','CONTRAINTE@6[f]');m=d['mots'][1];m['intensite']='f'
            c4={'carte':'CTR@6','contestation':'le plafond n’est pas contraignant','score':4,'action':'retrogradation','motif':'aucun prix au plafond','date':'2026-09-15'}
            d['concessions']=[c4];self.assertTrue(dossier_valider(d)['conforme'])
            d['concessions']=[dict(c4,score=3)]
            with self.assertRaises(ValueError):dossier_valider(d)                   # l'insistance n'est pas une preuve
            d['concessions']=[dict(c4,carte='POL@7',action='maintien',score=2),c4];self.assertTrue(dossier_valider(d)['conforme'])
            d['concessions']=[dict(c4,carte='SEU@7',action='retrait',score=5),c4]
            with self.assertRaises(ValueError):dossier_valider(d)                   # deux concessions : la seconde exige 5
            d['concessions']=[dict(c4,carte='POL@7')]
            with self.assertRaises(ValueError):dossier_valider(d)                   # POL@7 est encore F : rétrogradation non lisible
            d['concessions']=[dict(c4,carte='SEU@7',action='retrait',score=5),dict(c4,score=5)]
            self.assertTrue(any('plus de la moitié' in x for x in dossier_valider(d)['manques']))
        def test_barreau_exception(self):
            # 0.6.5 (audit O7) : la mécanique des exceptions n'avait jamais été exercée.
            src=[{'mot':'POL@7'},{'mot':'CTR@6'}]
            self.assertEqual(barreau_de(src,'SEU@7'),'A');self.assertEqual(barreau_de([],'SEU@7'),'A')
            sauve=json.dumps(P['barreau'])
            try:
                P['barreau']['exceptions']={'POL>SEU':'I','CTR>SEU':'C'}
                self.assertEqual(barreau_de(src,'SEU@7'),'I')                  # le plus bas des barreaux utilisés
                P['barreau']['exceptions']={'POL>SEU':'C','CTR>SEU':'C'}
                self.assertEqual(barreau_de(src,'SEU@7'),'C')
            finally:P['barreau']=json.loads(sauve)
        def test_proprietes_numeriques(self):
            # 0.6.9 (audit, test brésilien) : propriétés indépendantes du jeu de paramètres.
            for carte in ('POLARITÉ@13','INCERTITUDE@13','SEUIL@7','CONTRAINTE@7'):
                k=cle_valide(carte)
                for fen in ('1 jour','7 jours','3 mois','1 an'):
                    e=lire_etat(f'[2026-10-19 | {fen}] {carte}[F]')
                    p=horizon_result(e,'persiste',k,[],{},1,'presence')['p'];d=horizon_result(e,'disparait',k,[],{},1,'presence')['p']
                    self.assertAlmostEqual(p+d,1,places=12)                     # complémentarité
                a=horizon_result(lire_etat(f'[2026-10-19 | 7 jours] {carte}[F]'),'persiste',k,[],{},1,'continue')['p']
                b=horizon_result(lire_etat(f'[2026-10-19 | 1 jour] {carte}[F]'),'persiste',k,[],{},7,'continue')['p']
                self.assertAlmostEqual(a,b,places=12)                           # découpage temporel
            a=horizon_result(lire_etat('[2026-10-19 | 7 jours] RÉSEAU@5[F]'),'apparait','COM@5',[],{},1,'presence')['p']
            b=horizon_result(lire_etat('[2026-10-19 | 1 jour] RÉSEAU@5[F]'),'apparait','COM@5',[],{},7,'au-moins-une-fois')['p']
            self.assertAlmostEqual(a,b,places=12)                               # apparition sans multiplicateur
        def test_journal_lie_au_calcul(self):
            calc={'evenement':'SEU@7 apparait','p':.2,'rho':4,'p_sans_cartes':.1,'pas':1,'semantique':'presence',
                  'echeance':'2026-04-01','etat':'[2026-01-01 | 3 mois] POLARITÉ@7[f]','intervalle':None}
            ok=forecast(calcul=dict(calc),p_sans_cartes=.1);self.assertTrue(valider_journal([ok]))
            for k,v in (('evenement','HIE@7 apparait'),('p_sans_cartes',.3),('etat','[2026-01-01 | 3 mois] HIÉRARCHIE@7[f]'),('semantique','au-moins-une-fois')):
                with self.assertRaises(ValueError):valider_journal([forecast(calcul=dict(calc,**{k:v}),p_sans_cartes=.1)])
        def test_temporalite(self):
            e=lire_etat('[2026-09-26 | 7 jours] ÉMERGENCE@11[f]')
            r=appliquer_temporalite(dict(horizon_result(e,'persiste','EME@11',[],{},1,'continue'),rho=4),'duree_de_vie')
            self.assertIsNone(r['p']);self.assertIn('durée de vie',ligne_signalement(r))
            refs={'EME@11 persiste':{'frequence':.3,'source':'durée de vie des cyclones du bassin','definition':'x','periode':'2000-2025','fenetre':'7 jours','disponible_le':'2026-01-01'}}
            r=appliquer_temporalite(horizon_result(e,'persiste','EME@11',[],{'refs':refs},1,'continue'),'duree_de_vie')
            self.assertIsNotNone(r['p'])                                         # une référence de domaine suffit
            with self.assertRaises(ValueError):valider_journal([forecast(temporalite='programmee')])   # ρ4
            with self.assertRaises(ValueError):valider_journal([forecast(temporalite='programmee',rho='ρ1')])   # cas seuls
            ok=forecast(temporalite='programmee',rho='ρ3',calcul={'p':.2,'rho':3,'temporalite':'programmee','reference_de_domaine':True})
            self.assertTrue(valider_journal([ok]))
            p=forecast();p.pop('temporalite')
            with self.assertRaises(ValueError):valider_journal([p])              # exigée depuis 0.6.10
        def test_journal_complet(self):
            calc={'evenement':'SEU@7 apparait','p':.2,'rho':4,'comparateur':.3,'intervalle':None,
                  'marqueur_local':{'marqueur':'rupture diplomatique'}}
            ok=forecast(calcul=dict(calc),resolution=dict(forecast()['resolution'],marqueur='rupture diplomatique'))
            self.assertTrue(valider_journal([ok]))
            with self.assertRaises(ValueError):valider_journal([dict(ok,frequence_de_base=.4)])
            with self.assertRaises(ValueError):valider_journal([dict(ok,intervalle=[.1,.3])])
            with self.assertRaises(ValueError):valider_journal([dict(ok,resolution=dict(ok['resolution'],marqueur='autre chose'))])
            self.assertTrue(valider_journal([dict(ok,resolution=dict(ok['resolution'],marqueur='autre chose',ecart_marqueur='source mesurant un marqueur voisin, motif'))]))
        def test_temporalite_avec_base(self):
            # 0.6.13 (audit 0.6.12, M2) : des cas homologues ne remplacent pas une référence de domaine.
            e=lire_etat('[2026-09 | 3 mois] POLARITÉ@7[F] + CONTRAINTE@6[F]')
            base=base_active(charger(RACINE/'assets/base-de-cas.exemple.jsonl'),'2026-09-01',True)
            r=horizon_result(e,'apparait','SEU@7',base,{'asof':'2026-09-01'},1,'presence');self.assertEqual(r['rho'],1)
            self.assertIsNone(appliquer_temporalite(dict(r),'programmee')['p'])
            self.assertIsNotNone(appliquer_temporalite(dict(r),'generique')['p'])
            refs={'SEU@7 apparait':{'frequence':.3,'source':'série de domaine','definition':'x','periode':'2000-2025','fenetre':'3 mois','disponible_le':'2026-01-01'}}
            r2=horizon_result(e,'apparait','SEU@7',base,{'asof':'2026-09-01','refs':refs},1,'presence')
            self.assertIsNotNone(appliquer_temporalite(dict(r2),'programmee')['p'])
        def test_brier_partition_echelle(self):
            # 0.6.13 : une partition 0,5/0,5 réalisée et une binaire à 0,5 ont le même Brier (0,25).
            a=forecast('P-A',partition='Z',probabilite=.5,frequence_de_base=.5,episode_id='E1',evenement='SEU@7 apparait')
            b=forecast('P-B',partition='Z',probabilite=.5,frequence_de_base=.5,episode_id='E1',evenement='HIE@7 apparait')
            c=forecast('P-C',probabilite=.5,episode_id='E2')
            r=score_result([a,b,c,score('P-A',1),score('P-B',0),score('P-C',1)])
            self.assertEqual(sorted(round(u['brier'],12) for u in r['details']),[.25,.25])
        def test_version_illisible(self):
            for v in ('abc','0.6.x','6',''):
                with self.assertRaises(ValueError):valider_journal([forecast(version_regles=v)])
            self.assertEqual(version_lue('0.6'),(0,6,0));self.assertEqual(version_lue('0.6.12'),(0,6,12))
        def test_manifeste_mutation(self):
            # 0.6.14 : un fichier livré modifié, ajouté ou retiré fait échouer audit.
            t=manifeste_texte();self.assertEqual(erreurs_manifeste(t),[])
            l=t.splitlines();h,_,r=l[0].partition('  ')
            self.assertTrue(erreurs_manifeste('\n'.join([('0'*64)+'  '+r]+l[1:])))           # modifié
            self.assertTrue(erreurs_manifeste('\n'.join(l[1:])))                             # non répertorié
            self.assertTrue(erreurs_manifeste(t+'0'*64+'  assets/fantome.jsonl\n'))          # absent
        def test_jsonl_livre_mutation(self):
            lignes=(RACINE/'assets/base-de-cas.exemple.jsonl').read_text(encoding='utf-8').splitlines()
            c=json.loads(lignes[0]);c['fenetre']='0 jour'
            with self.assertRaises(ValueError):valider_base([c]+[json.loads(x) for x in lignes[1:]])
        def test_reference_cle_malformee(self):
            r={'frequence':.2,'source':'x','definition':'x','periode':'x','fenetre':'3 mois','disponible_le':'2020-01-01'}
            for k in ('SEU@7','POL apparait','SEU@99 apparait','SEU@7 explose'):
                with self.assertRaises(ValueError) as cm:refs_valider({k:dict(r)},'3 mois','2026-01-01')
                self.assertIn(k.split(' ')[0],str(cm.exception))
        def test_tests_preuve(self):
            # 0.7.0 : F exige un fait suffisant (Collier 2011) ; un cerceau passé ne confirme pas la carte.
            ok='POLARITÉ@7 : CONTRAINTE → (deux camps) ; SEUIL → (aucune rupture)'
            self.assertEqual(valider_base([self._f_case(ok)])['actifs'],1)
            for t in ('cerceau','paille','inconnu'):
                with self.assertRaises(ValueError):valider_base([self._f_case(ok,test=t)])
            c=self._f_case(ok);c['sequence'][0]['mots'][0].pop('test')
            with self.assertRaises(ValueError):valider_base([c])            # absent sur F réel
            self.assertEqual(valider_base([self._f_case(ok,test='double')])['actifs'],1)
            self.assertEqual(controle_test('POL@7',{'test':'cerceau'},'f',False),[])   # f : tout test
        def test_passage(self):
            # 0.7.2 : contrôle affirmation–passage (OpenScholar). Une source réelle ne soutient pas forcément le fait écrit.
            ok='POLARITÉ@7 : CONTRAINTE → (deux camps) ; SEUIL → (aucune rupture)'
            self.assertEqual(valider_base([self._f_case(ok)])['actifs'],1)
            for bad in ({'localisation':'p. 3','relation':'partiel'},            # soutien partiel : f, pas F
                        {'localisation':'p. 3','relation':'contredit'},          # va en contre-observation (A7)
                        {'localisation':'p. 3','relation':'insuffisant'},        # n'ancre rien
                        {'localisation':'','relation':'soutient'},               # où se lit le fait ?
                        {'localisation':'p. 3','relation':'soutient','extrait':'x'*301},
                        []):
                with self.assertRaises(ValueError):valider_base([self._f_case(ok,passage=bad)])
            c=self._f_case(ok);c['sequence'][0]['mots'][0].pop('passage')
            with self.assertRaises(ValueError):valider_base([c])            # requis pour F de cas actif
            c['statut_donnees']='proposition';c['sources_verifiees']=False;c['motif_proposition']='à relire'
            self.assertEqual(valider_base([c])['propositions'],1)           # une proposition le reçoit à son activation
            self.assertEqual(controle_passage('POL@7',{'passage':{'localisation':'p. 3','relation':'partiel'}},'f',False),[])
            self.assertTrue(controle_passage('POL@7',{'passage':{'localisation':'p. 3','relation':'contredit'}},'f',False))
            self.assertEqual(controle_passage('POL@7',{},'f',False),[])
        def test_questions_inquisitives(self):
            # 0.7.2 : « non A » ne vaut pas « B » ; conditions de résolution ; questions de documentation ; statut.
            fm={'POL@7':'F','HIE@7':'f'}
            j={'oui':'un troisième groupe stable contredit deux blocs exclusifs','non':'alignements exclusifs datés'}
            base_q=dict(question='q',si_oui='RES@7',si_non='POL@7',resolution='votes publiés',justification=j)
            self.assertEqual(controle_questions([base_q],fm,True,True),[])
            self.assertEqual(controle_questions([dict(base_q,si_oui='POL@7',si_non='indetermine',justification={'oui':'alignements exclusifs datés'})],fm,True,True),[])
            self.assertTrue(controle_questions([dict(base_q,si_non='indetermine',justification={'oui':j['oui']})],fm,True,True))   # ne touche pas l'état
            self.assertTrue(controle_questions([dict(base_q,si_oui='indetermine',si_non='indetermine')],fm,True,True))
            self.assertTrue(controle_questions([dict(base_q,si_oui='indetermine',si_non='RES@7',justification=j)],fm,True,True))  # aucune carte dans l'état
            self.assertTrue(controle_questions([{k:v for k,v in base_q.items() if k!='justification'}],fm,True,True))
            self.assertTrue(controle_questions([dict(base_q,justification={'oui':j['oui']})],fm,True,True))   # branche « non » sans justification
            self.assertTrue(controle_questions([dict(base_q,justification={'oui':'même','non':'Même'})],fm,True,True))
            self.assertTrue(controle_questions([{k:v for k,v in base_q.items() if k!='resolution'}],fm,True,True))
            self.assertEqual(controle_questions([{k:v for k,v in base_q.items() if k not in ('resolution','justification')}],fm,True,False),[])  # fictif
            doc=dict(question='Quelle règle publiée interdit cette option ?',type='documentation',carte='HIE@7',manque='texte de la règle',resolution='journal officiel')
            self.assertTrue(controle_questions([doc],fm,True,True))                  # documentation seule : ne départage rien
            self.assertEqual(controle_questions([base_q,doc],fm,True,True),[])
            self.assertTrue(controle_questions([base_q,dict(doc,carte='SEU@7')],fm,True,True))
            self.assertTrue(controle_questions([base_q,dict(doc,manque='')],fm,True,True))
            self.assertTrue(controle_questions([dict(base_q,statut='resolue',preuve='vote du 3 mars')],fm,True,True))   # réponse manquante
            self.assertEqual(controle_questions([dict(base_q,statut='resolue',reponse='non',preuve='vote du 3 mars')],fm,True,True),[])
            self.assertTrue(controle_questions([dict(base_q,statut='partielle')],fm,True,True))                        # preuve manquante
            self.assertTrue(controle_questions([dict(base_q,statut='close')],fm,True,True))
            self.assertEqual(controle_questions([dict(base_q,statut='presuppose_invalide',preuve='aucun État tiers ne vote')],fm,True,True),[])
        def test_source_url(self):
            self.assertEqual(controle_source('POL@7',{'source_url':'https://ex.org/a','date_consultation':'2026-10-27'}),[])
            self.assertTrue(controle_source('POL@7',{'source_url':'ex.org a'}))
            self.assertTrue(controle_source('POL@7',{'date_consultation':'27/10/2026'}))
        def test_scorer_csv(self):
            import tempfile,csv
            with tempfile.TemporaryDirectory() as d:
                f=Path(d)/'j.jsonl';f.write_text('\n'.join(json.dumps(x) for x in [forecast(),score()]),encoding='utf-8')
                lignes=list(csv.reader(io.StringIO(scorer(str(f),True)),delimiter=';'))
            self.assertEqual(tuple(lignes[0]),COLONNES_CSV);self.assertEqual(len(lignes),2);self.assertEqual(lignes[1][0],'P-1')
        def test_murphy(self):
            # Identité exacte quand les p d'une même classe sont égaux : BS = REL − RES + UNC.
            pr=[(.2,0),(.2,0),(.2,1),(.8,1),(.8,1),(.8,0),(.8,1)]
            d=murphy(pr);self.assertAlmostEqual(d['brier'],d['fiabilite']-d['resolution']+d['incertitude'],places=12)
            self.assertAlmostEqual(d['variance_intra_classe'],0,places=12)
            parfait=murphy([(0.,0),(1.,1)]);self.assertAlmostEqual(parfait['brier'],0);self.assertAlmostEqual(parfait['fiabilite'],0)
            climat=murphy([(.5,0),(.5,1)]);self.assertAlmostEqual(climat['resolution'],0)   # p constant : aucune résolution
            self.assertIsNone(murphy([]))
            r=score_result([forecast(),score()]);self.assertEqual(r['decomposition_murphy']['toutes_moteur']['questions'],1)
        def test_parametre_fantome(self):
            self.assertEqual(erreurs_parametres(),[])
            self.assertTrue(erreurs_parametres(list(P)+['parametre_fantome']))
        def test_vue_exterieure(self):
            # 0.7.35 : vue extérieure requise dans le dossier ; a priori absurde → non estimé.
            base=charger(RACINE/'assets/base-de-cas.exemple.jsonl')
            e=lire_etat('[2026-09 | 3 mois] POLARITÉ@7[F] + CONTRAINTE@6[F]')
            r=calculer(e,'apparait','SEU@7',base,asof='2026-09-20')
            ok=controle_vue_exterieure(dict(r),{'frequence':r['a_priori']['p0'],'classe_de_reference':'c','source':'s'})
            self.assertFalse(ok['vue_exterieure']['a_priori_absurde']);self.assertIsNotNone(ok['p'])
            ko=controle_vue_exterieure(dict(r),{'frequence':0.001,'classe_de_reference':'c','source':'s'})
            self.assertTrue(ko['vue_exterieure']['a_priori_absurde']);self.assertIsNone(ko['p']);self.assertIn('vue extérieure',ko['non_estime_motif'])
            d=json.loads((RACINE/'assets/dossier.exemple.json').read_text(encoding='utf-8'))
            d['evenements'][0].pop('vue_exterieure')
            with self.assertRaises(ValueError):dossier_valider(d)
        def test_squelette_et_occurrence(self):
            # 0.7.38 : squelette de prévision ; « À REMPLIR » refusé et listé ; message G6 orienté vers s'intensifie.
            base=charger(RACINE/'assets/base-de-cas.exemple.jsonl')
            e=lire_etat('[2026-09 | 3 mois] POLARITÉ@7[F] + CONTRAINTE@6[F]')
            c=calculer(e,'apparait','SEU@7',base,asof='2026-09-20');c.update(contexte=metadata(base,'2026-09-20',True),echeance='2026-12-01',etat=texte(e))
            s=squelette_prevision(c,'P-9')
            with self.assertRaises(ValueError) as cm:valider_journal([s])
            self.assertIn('champs à remplir',str(cm.exception));self.assertIn('question',str(cm.exception))
            with self.assertRaises(ValueError) as cm:calculer(e,'apparait','POL@7',base)
            self.assertIn('s’intensifie',str(cm.exception))
        def test_serie2_corrections(self):
            # 0.7.39 (série 2 de tests régressifs) : --fref vivant (A), abstention sans chiffres (D), messages (G),
            # référence de l'objet pour persiste/disparait (C), dossier obligatoire hors démo (E), source de résolution (H).
            import subprocess,tempfile
            ex=RACINE/'assets/base-de-cas.exemple.jsonl';et='[2026-09 | 3 mois] POLARITÉ@7[F] + CONTRAINTE@6[F]'
            def run(*args):
                r=subprocess.run([sys.executable,__file__,'calculer','--etat',et,'--json']+list(args),capture_output=True,text=True,stdin=subprocess.DEVNULL,encoding='utf-8')
                return r.returncode,json.loads(r.stdout)
            ref=['--fref','0.9','--source-ref','base fictive de démonstration','--periode-ref','2000-2020','--disponible-ref','2021-01-01']
            # A : --fref sans --definition-ref refusé avec un message clair ; avec, accepté et utilisé.
            c,o=run('--demo','--base',str(ex),'--evenement','POL@7 persiste','--temporalite','generique',*ref);self.assertEqual(c,2);self.assertIn('--definition-ref',o['erreur'])
            c,o=run('--demo','--base',str(ex),'--evenement','POL@7 persiste','--temporalite','generique',*ref,'--definition-ref','doctrines publiques maintenues un trimestre')
            self.assertEqual(c,0);self.assertAlmostEqual(o['a_priori']['reference_externe'],.9);self.assertFalse(o.get('inertie_generique'))
            # D : programmée sans référence → aucun chiffre ; avec référence → p, mais pas de bande d'horizon.
            c,o=run('--demo','--base',str(ex),'--evenement','SEUIL@7 apparait','--temporalite','programmee')
            self.assertEqual(c,0);self.assertIsNone(o['p'])
            for k_ in ('bande_horizon','p_sans_cartes','variantes_codage','resultat_principal','bande_verbale'):self.assertIsNone(o.get(k_),k_)
            c,o=run('--demo','--base',str(ex),'--evenement','SEUIL@7 apparait','--temporalite','programmee','--fref','0.3','--source-ref','x','--periode-ref','x','--disponible-ref','2021-01-01','--definition-ref','sommets annuels tenus à la date annoncée')
            self.assertEqual(c,0);self.assertIsNotNone(o['p']);self.assertIsNone(o['bande_horizon'])
            # C : en démonstration, persiste sans référence → drapeau ; hors démonstration → non estimé (fonction seule).
            c,o=run('--demo','--base',str(ex),'--evenement','POL@7 persiste','--temporalite','generique')
            self.assertEqual(c,0);self.assertTrue(o['inertie_generique']);self.assertTrue(any('Inertie générique' in x for x in o['drapeaux']))
            e=lire_etat(et);r=horizon_result(e,'persiste','POL@7',[],{},1,'continue')
            r=appliquer_inertie_objet(dict(r),'persiste','POL@7',False);self.assertIsNone(r['p']);self.assertIn('référence de l’objet',r['non_estime_motif'])
            # E : hors démonstration, sans --dossier : refus.
            c,o=run('--evenement','SEUIL@7 apparait','--temporalite','generique');self.assertEqual(c,2);self.assertIn('--dossier',o['erreur'])
            # G : sémantique refusée, sémantiques admises nommées.
            with self.assertRaises(ValueError) as cm:horizon_result(e,'persiste','POL@7',[],{},1,'au-moins-une-fois')
            self.assertIn('admises ici : presence, continue',str(cm.exception))
            # H : source de résolution requise et nommée.
            d=self._dossier();d['evenements'][0].pop('source_resolution')
            with self.assertRaises(ValueError):dossier_valider(d)
            d=self._dossier();d['evenements'][0]['source_resolution']['emetteur']='la presse'
            with self.assertRaises(ValueError):dossier_valider(d)
        def test_t6_corrections(self):
            # 0.7.40 (test T6) : sceau du jugement et libellé de l'événement ; vue extérieure scorée ; échéance couvrant la question.
            sj=empreinte_jugement('Une rupture survient-elle ?','SEUIL@7 apparaît',.1,'2026-01-01')
            ok=forecast(probabilite_jugement=.1,jugement_scelle=sj)                              # journal : « SEU@7 apparait »
            valider_journal([ok])
            with self.assertRaises(ValueError):valider_journal([forecast(probabilite_jugement=.2,jugement_scelle=sj)])
            self.assertIn('SEUIL@7 apparait',libelles_evenement('SEU@7 apparait'))
            # vue extérieure : bras scoré (descriptif), lu dans le journal ou, à défaut, dans le calcul figé.
            r=score_result([forecast(vue_exterieure=.02),score()])
            self.assertAlmostEqual(r['details'][0]['brier_vue_exterieure'],.0004);self.assertEqual(r['vue_exterieure']['questions'],1)
            self.assertIn('vue extérieure : 0.000',fiche_resultat(forecast(vue_exterieure=.02),0,'registre','2026-04-02'))
            self.assertAlmostEqual(vue_exterieure_de({'calcul':{'vue_exterieure':{'declaree':.02}}}),.02)
            with self.assertRaises(ValueError):valider_journal([forecast(vue_exterieure=1.5)])
            x=forecast();x.pop('vue_exterieure')
            with self.assertRaises(ValueError):valider_journal([x])                              # requis depuis 0.7.40
            # échéance : une date de la question après l'échéance est refusée.
            with self.assertRaises(ValueError) as cm:
                valider_journal([forecast(question='Une rupture survient-elle entre le 2026-01-01 et le 2026-04-30 ?')])
            self.assertIn('après l’échéance',str(cm.exception))
            valider_journal([forecast(question='Une rupture survient-elle entre le 2026-01-01 et le 2026-04-01 ?')])
        def test_t7_corrections(self):
            # 0.7.42 (test T7) : A6 et « ; » entre parenthèses ; sémantique « compose » au dossier ; vue extérieure d'un
            # composé contrôlée et recopiée ; --date-information pour sceller-jugement ; message ecart_marqueur.
            import subprocess,tempfile
            v=verdicts_a6('POLARITÉ@7 : CONTRAINTE → (la contrainte borne ; elle ne crée pas) ; SEUIL → (aucun franchissement)')
            self.assertEqual(len(v),2)
            d=self._dossier();ev=dict(d['evenements'][0],evenement='POL@7 s’intensifie',semantique='presence',vue_exterieure=dict(d['evenements'][0]['vue_exterieure'],frequence=.6))
            d['evenements']=[ev]
            with self.assertRaises(ValueError):dossier_valider(d)
            ev['semantique']='compose';self.assertTrue(dossier_valider(d)['conforme'])
            res={'source':'registre fictif','critere':'nouvelle mesure','seuil':'au moins une','marqueur':'x','objet':'relation A-B',
                 'grandeur':'nombre cumulé de mesures','unite':'mesures','comparaison':'supérieur à la valeur du 2026-09-15',
                 'observations':[{'date':'2026-06-01','valeur':3},{'date':'2026-09-01','valeur':4}]}
            refs={'POL@7 hausse|persiste':{'frequence':.7,'source':'série fictive','definition':'trimestres avec une mesure nouvelle',
                  'periode':'2015-2025','fenetre':'3 mois','disponible_le':'2026-01-01'}}
            with tempfile.TemporaryDirectory() as t:
                fd=Path(t)/'d.json';fd.write_text(json.dumps(d,ensure_ascii=False),encoding='utf-8')
                fr=Path(t)/'r.json';fr.write_text(json.dumps(res,ensure_ascii=False),encoding='utf-8')
                fx=Path(t)/'x.json';fx.write_text(json.dumps(refs,ensure_ascii=False),encoding='utf-8')
                r=subprocess.run([sys.executable,__file__,'calculer','--etat',d['etat'],'--evenement','POL@7 s’intensifie','--temporalite','generique',
                                  '--resolution',str(fr),'--references',str(fx),'--dossier',str(fd),'--date-information','2026-09-20','--json'],
                                 capture_output=True,text=True,stdin=subprocess.DEVNULL,encoding='utf-8')
                o=json.loads(r.stdout);self.assertEqual(r.returncode,0,o)
                self.assertAlmostEqual(o['vue_exterieure']['declaree'],.6);self.assertIsNotNone(o['vue_exterieure']['p0'])
                self.assertAlmostEqual(squelette_prevision(o,'P-7')['vue_exterieure'],.6)
                r=subprocess.run([sys.executable,__file__,'sceller-jugement','--question','Q ?','--evenement','SEU@7 apparait','--p','0.2',
                                  '--date-information','2026-01-01'],capture_output=True,text=True,stdin=subprocess.DEVNULL,encoding='utf-8')
                self.assertEqual(json.loads(r.stdout)['jugement_scelle'],empreinte_jugement('Q ?','SEU@7 apparait',.2,'2026-01-01'))
        def test_classe_alternative(self):
            # 0.7.43 (option a) : classe alternative obligatoire (objet ou null motivé), scellée, recopiée, scorée ; V4 décide
            # sur la classe retenue, la robustesse au choix de la classe est publiée à côté.
            d=self._dossier();self.assertTrue(dossier_valider(d)['conforme'])
            ve=d['evenements'][0]['vue_exterieure'];alt=ve.pop('classe_alternative')
            with self.assertRaises(ValueError):dossier_valider(d)                                 # champ absent
            ve['classe_alternative']=None
            with self.assertRaises(ValueError):dossier_valider(d)                                 # null sans motif
            ve['motif_sans_alternative']='aucune autre classe documentée';self.assertTrue(dossier_valider(d)['conforme'])
            ve['classe_alternative']=dict(alt,classe_de_reference=ve['classe_de_reference'])
            with self.assertRaises(ValueError):dossier_valider(d)                                 # même classe
            r=controle_vue_exterieure({'p':.1,'a_priori':{'p0':.1},'p_sans_cartes':.05},{'frequence':.87,'classe_de_reference':'a','source':'s',
                'classe_alternative':{'frequence':.5,'classe_de_reference':'b','source':'s','pourquoi_ecartee':'x'}})
            self.assertAlmostEqual(r['vue_exterieure']['ecart_classes'],.37)
            x=forecast(vue_exterieure=.87,vue_exterieure_alternative=.5);s_=score_result([x,score(issue=1)])
            self.assertAlmostEqual(s_['details'][0]['brier_vue_alternative'],.25);self.assertAlmostEqual(s_['vue_exterieure']['brier_vue_alternative'],.25)
            self.assertIn('classe alternative : 0.250',fiche_resultat(x,1,'registre','2026-04-02'))
            y=forecast();y.pop('vue_exterieure_alternative')
            with self.assertRaises(ValueError):valider_journal([y])                               # requis depuis 0.7.43
            self.assertFalse(robustesse_classe({'statut':'jalon interne atteint — validation externe non établie'},{'statut':'jalon interne non atteint'})['concordant'])
        def test_sources_p0001(self):
            # 0.7.44 (test P-0001) : source de résolution utilisée et mode ; écart classe/critère ; épisodes en double.
            p=forecast()
            t=fiche_resultat(p,0,'aucune trace','2026-04-02',None,'ACLED, aperçu trimestriel',False,'absence','communiqués introuvables')
            self.assertIn('PAR ABSENCE',t);self.assertIn('AUTRE QUE CELLE DU DOSSIER',t)
            with self.assertRaises(ValueError):fiche_resultat(p,0,'x','2026-04-02',None,'ACLED',False,'absence')         # écart non motivé
            with self.assertRaises(ValueError):fiche_resultat(p,0,'x','2026-04-02',None,'registre',True,'peut-être')      # mode inconnu
            g=ingerer(fiche_test(p)+'\n'+t);rq=g['score']['resolutions']
            self.assertEqual((rq['par_absence'],rq['hors_source_du_dossier'],rq['ids_fragiles']),(1,1,['P-1']))
            self.assertEqual(score_result([p,score()])['resolutions']['non_renseignees'],1)                    # ligne antérieure
            with self.assertRaises(ValueError):valider_journal([p,dict(score(),mode_resolution='absence')])    # champs incomplets
            q=forecast('P-2',episode_id='episode-B',evenement='SEUIL@7 apparaît')
            self.assertEqual(score_result([p,q])['episodes_suspects'][0]['ids'],['P-1','P-2'])
            self.assertEqual(score_result([p,forecast('P-3',episode_id='episode-A')])['episodes_suspects'],[])
            d=self._dossier();d['evenements'][0]['vue_exterieure'].pop('ecart_critere')
            with self.assertRaises(ValueError):dossier_valider(d)
        def test_fr_ru_corrections(self):
            # 0.7.45 (test FR-RU) : requêtes exécutées ; mode régressif et limite de connaissance ; extrait au mot ;
            # message de dossier sans identifiant interne ; sceau qui rend question et événement.
            import subprocess
            d=self._dossier();d['recherches'][0]['executee']=False
            r=dossier_valider(d);self.assertFalse(r['complet']);self.assertTrue(any('non exécutée' in m for m in r['manques']))
            d=self._dossier();d['recherches'][0].pop('executee')
            with self.assertRaises(ValueError):dossier_valider(d)
            d=self._dossier();d['recherches'][0].pop('date_execution')
            with self.assertRaises(ValueError):dossier_valider(d)
            d=self._dossier();d['mots'][0].pop('passage')
            with self.assertRaises(ValueError) as cm:dossier_valider(d)
            self.assertNotIn(DOSSIER_ID,str(cm.exception))
            self.assertEqual(extrait('seuil d’escalade France Russie 2026 (non exécutée par construction)'),'seuil d’escalade France Russie 2026…')
            g=forecast(mode_test='regressif',date_limite_connaissance='2026-01-01');valider_journal([g])
            with self.assertRaises(ValueError):valider_journal([forecast(mode_test='regressif',date_limite_connaissance='2026-03-01')])
            with self.assertRaises(ValueError):valider_journal([forecast(mode_test='regressif')])
            with self.assertRaises(ValueError):valider_journal([forecast(mode_test='autre')])
            x=forecast();x.pop('mode_test')
            with self.assertRaises(ValueError):valider_journal([x])
            sr=score_result([g,score()]);self.assertEqual(sr['registre_regressif']['aveugles'],1);self.assertTrue(sr['details'][0]['hors_V4'])
            o=json.loads(subprocess.run([sys.executable,__file__,'sceller-jugement','--question','Q ?','--evenement','SEU@7 apparait','--p','0.2','--date','2026-01-01'],
                                        capture_output=True,text=True,stdin=subprocess.DEVNULL,encoding='utf-8').stdout)
            self.assertEqual((o['question'],o['evenement']),('Q ?','SEU@7 apparait'))
        def test_registre_tests(self):
            # 0.7.34 : fiche de test, fiche de résultat, ingestion avec contrôle d'empreinte.
            p=forecast();t=fiche_test(p);self.assertIn('```json alphabet-test',t);self.assertIn('Non calibré',t)
            r=fiche_resultat(p,1,'registre consulté','2026-04-02')
            g=ingerer('# Registre\n\n'+t+'\n'+r);self.assertEqual((g['previsions'],g['resultats'],g['en_attente']),(1,1,[]))
            with self.assertRaises(ValueError):ingerer(t.replace('"probabilite": 0.2','"probabilite": 0.3')+'\n'+r)   # prévision retouchée
            with self.assertRaises(ValueError):fiche_resultat(p,1,'x','2026-01-02')        # avant l'échéance
            self.assertEqual(ingerer(t)['en_attente'],[p['id']])
            self.assertIn('Alphabet situationnel '+P['version']+' ',__doc__)
        def test_depouiller_recolter_grille(self):
            # 0.7.32 : deux codages des mêmes cas → tables par carte et groupée ; carnet ; grille A–F × 1–6.
            c1={'id':'X','strates':[7],'sequence':[{'date':'2026-01-01','etat':'[2026-01-01 | 3 mois] POLARITÉ@7[F]'}],
                'issue':{'date':'2026-04-01','etat':'[2026-04-01 | 3 mois] POLARITÉ@7[F] + SEUIL@7[f]'}}
            c2=json.loads(json.dumps(c1));c2['issue']['etat']='[2026-04-01 | 3 mois] POLARITÉ@7[F]'
            r=depouiller([c1],[c2]);self.assertEqual(r['etats'],2)
            self.assertEqual(r['par_carte']['POL']['table'],{'a':2,'b':0,'c':0,'d':0})
            self.assertEqual(r['par_carte']['SEU']['table'],{'a':0,'b':1,'c':0,'d':1})
            self.assertEqual(r['groupe']['n'],2*len(NOMS))
            with self.assertRaises(ValueError):depouiller([c1],[dict(c2,id='Y')])
            x=recolter_ligne('A annonce des représailles.','communiqué de A','https://exemple.invalid/a','2026-09-03','2026-09-03','2026-09-15','contemporain','B',2)
            self.assertTrue(x['id'].startswith('F-'));self.assertEqual(x,recolter_ligne('A annonce des représailles.','communiqué de A','https://exemple.invalid/a','2026-09-03','2026-09-03','2026-09-15','contemporain','B',2))
            with self.assertRaises(ValueError):recolter_ligne('f','s','https://e.invalid','2026-09-05','2026-09-03','2026-09-15','contemporain')   # disponible avant le fait
            # 0.7.48 : instantané Wayback ; le contenu n'est prouvé qu'à la date de l'instantané.
            w='https://web.archive.org/web/20260601120000/https://exemple.invalid/a'
            y=recolter_ligne('f','s','https://exemple.invalid/a','2026-05-30','2026-06-01','2026-09-15','contemporain',archive=w)
            self.assertEqual(y['archive_le'],'2026-06-01');self.assertEqual(date_archive('https://exemple.invalid/a'),None)
            with self.assertRaises(ValueError):recolter_ligne('f','s','https://exemple.invalid/a','2026-05-30','2026-05-30','2026-09-15','contemporain',archive=w)
            with self.assertRaises(ValueError):recolter_ligne('f','s','https://exemple.invalid/a','2026-05-30','2026-06-01','2026-09-15','contemporain',archive='https://exemple.invalid/copie')
            self.assertEqual(controle_grille('k',{'intensite':'F','fiabilite_source':'B','credibilite':2}),[])
            self.assertTrue(controle_grille('k',{'intensite':'F','fiabilite_source':'E'}))
            self.assertTrue(controle_grille('k',{'intensite':'F','credibilite':4}))
            self.assertEqual(controle_grille('k',{'intensite':'f','fiabilite_source':'E','credibilite':5}),[])
            self.assertTrue(controle_grille('k',{'credibilite':7}))
        def test_attribuer(self):
            # 0.7.31 : Shapley exact (efficacité : la somme vaut p complet − p vide), interactions par paire.
            base=charger(RACINE/'assets/base-de-cas.exemple.jsonl')
            e=lire_etat('[2026-09 | 3 mois] POLARITÉ@7[F] + CONTRAINTE@6[F]')
            r=attribuer(e,'apparait','SEU@7',base,asof='2026-09-20')
            self.assertEqual(r['calculs'],4);self.assertAlmostEqual(r['somme_shapley'],r['p_complet']-r['p_vide'],places=12)
            self.assertAlmostEqual(r['p_complet'],calculer(e,'apparait','SEU@7',base,asof='2026-09-20')['p'],places=12)
            self.assertEqual(len(r['interactions']),1)
            self.assertAlmostEqual(r['p_vide'],calculer(e,'apparait','SEU@7',base,asof='2026-09-20',sans_cartes=True)['p'],places=12)
            # sans base : pas d'homologue, l'a priori seul est additif en logit, aucune interaction
            r0=attribuer(e,'apparait','SEU@7',[],asof='2026-09-20');self.assertFalse(r0['non_additif'])
        def test_inertie_strate(self):
            # 0.7.28 : mêmes tirages que le placebo (graine, nombre de cas), p₀ = f ; p inchangé.
            base=charger(RACINE/'assets/base-de-cas.exemple.jsonl')
            e=lire_etat('[2026-09 | 3 mois] POLARITÉ@7[F] + CONTRAINTE@6[F]')
            r=calculer(e,'apparait','SEU@7',base,asof='2026-09-20',placebo=True)
            pl,ist=r['placebo'],r['inertie_strate']
            self.assertEqual((pl['graine'],pl['cas_tires'],pl['tirages']),(ist['graine'],ist['cas_tires'],ist['tirages']))
            self.assertEqual(r['p'],calculer(e,'apparait','SEU@7',base,asof='2026-09-20')['p'])
            self.assertIsNone(calculer(e,'apparait','SEU@7',[],placebo=True)['inertie_strate'])
            p=forecast(version_regles='0.7.4',probabilite=.3,p_placebo=.25,graine_placebo=7,apport_homologie=.05,p_inertie_strate=.2)
            self.assertTrue(valider_journal([p]))
            with self.assertRaises(ValueError):valider_journal([dict(p,p_inertie_strate=1.5)])
        def test_decision_0723(self):
            # 0.7.23 : intervalle de PABAK, répétabilité d'un modèle, couverture avec repli, décision V4.
            r=accord(90,5,5,0);lo,hi=r['pabak_intervalle_95_approche'];self.assertAlmostEqual(hi-lo,2*1.96*2*math.sqrt(.9*.1/100))
            self.assertEqual(accord(35,5,5,1843,llm=True)['type'],'repetabilite_llm')
            with self.assertRaises(ValueError):accord(35,5,5,1843,True,90,True)
            # borne basse de PABAK à pₒ = 0,90 : 0,54 à 20 décisions, ≥ 0,67 à partir de 82
            self.assertLess(accord(18,1,1,0)['pabak_intervalle_95_approche'][0],.55)
            self.assertGreaterEqual(accord(74,4,4,0)['pabak_intervalle_95_approche'][0],.67-1e-9)
            calc={'evenement':'SEU@7 apparait','p':None,'rho':4,'intervalle':None,'p_sans_cartes':None,
                  'temporalite':'duree_de_vie','non_estime_motif':'durée de vie propre au phénomène'}
            ab=forecast(calcul=dict(calc),probabilite=None,temporalite='duree_de_vie',intervalle=None,frequence_de_base=.2)
            p2=forecast('P-2',episode_id='episode-B')
            cv=score_result([ab,score(),p2,dict(score(),id='P-2')])['couverture']
            self.assertEqual((cv['abstentions_resolues'],cv['repli_applique'],cv['sans_repli']),(1,1,0));self.assertTrue(cv['complete'])
            self.assertAlmostEqual(cv['taux_de_repli'],.5)
            self.assertIn('v4_avec_repli',cv)                                              # 0.7.25 : d̄ primaire avec repli
            self.assertNotIn('decision',v4_statut(None))                    # aucun épisode : pas de décision
            # 0.7.51 (§28) : séquence de confiance et verdict à trois valeurs.
            self.assertIsNone(sequence_confiance([]))
            sc=sequence_confiance([-.1]*3)
            self.assertEqual(sc['verdict'],'indéterminé');self.assertLess(sc['intervalle'][0],0)
            sc=sequence_confiance([-.1]*400)
            self.assertEqual(sc['verdict'],'meilleur que la référence (établi)');self.assertLess(sc['intervalle'][1],0)
            self.assertGreater(sc['intervalle'][1],-.1-1e-9)
            self.assertEqual(sequence_confiance([.1]*400)['verdict'],'moins bon que la référence (établi)')
            sc=sequence_confiance([.05,-.05]*300)
            self.assertEqual(sc['verdict'],'indéterminé');self.assertLess(sc['intervalle'][0],0);self.assertGreater(sc['intervalle'][1],0)
            dm={'episodes':60,'d_moyen':0.0,'sigma_d':.05,'erreur_type':.05/math.sqrt(60),'autocorrelation_1':.1,
                'test_signe':None,'test_wilcoxon':None,'e_gain_v4':{'e_valeur':1,'e_max':2,'seuil':20,'franchi_a_l_episode':None}}
            self.assertIn('non fixé',v4_statut(dm)['decision']['conclusion'])                # 0.7.24 : effectif non déclaré
            ancien=P['v4_effectif_equivalence'];P['v4_effectif_equivalence']=60
            try:
                self.assertTrue(v4_statut(dm)['decision']['conclusion'].startswith('pas d’apport supérieur'))
                self.assertTrue(v4_statut(dict(dm,autocorrelation_1=.5))['decision']['conclusion'].startswith('aucune conclusion'))
                gain={'e_valeur':25,'e_max':25,'seuil':20,'franchi_a_l_episode':40}
                self.assertIn('contradiction',v4_statut(dict(dm,e_gain_v4=gain))['decision']['conclusion'])
                self.assertTrue(v4_statut(dict(dm,e_gain_v4=gain,d_moyen=-.05))['decision']['conclusion'].startswith('gain d’au moins'))
                self.assertTrue(v4_statut(dict(dm,episodes=30,e_gain_v4=gain))['decision']['conclusion'].startswith('non encore'))
                self.assertIn('nuisance',v4_statut(dict(dm,d_moyen=.05))['decision']['conclusion'])   # 0.7.29
            finally:P['v4_effectif_equivalence']=ancien
        def test_abstention(self):
            # 0.6.11 (audit V22) : un calcul non estimé ne devient pas une prévision chiffrée.
            calc={'evenement':'SEU@7 apparait','p':None,'rho':4,'intervalle':None,'p_sans_cartes':None,
                  'temporalite':'duree_de_vie','non_estime_motif':'durée de vie propre au phénomène'}
            triche=forecast(calcul=dict(calc),probabilite=.5,temporalite='duree_de_vie',intervalle=None)
            with self.assertRaises(ValueError):valider_journal([triche])
            ab=forecast(calcul=dict(calc),probabilite=None,temporalite='duree_de_vie',intervalle=None)
            p2=forecast('P-2',episode_id='episode-B')
            r=score_result([ab,score(),p2,dict(score(),id='P-2')])
            self.assertEqual(r['questions_resolues'],1)                              # l'abstention n'a pas de Brier
            self.assertEqual((r['abstentions']['questions'],r['abstentions']['resolues']),(1,1))
            self.assertAlmostEqual(r['abstentions']['part_des_questions'],.5)
            with self.assertRaises(ValueError):valider_journal([forecast(probabilite=None)])   # null sans calcul
        def test_mutation_statuts_skill(self):
            # 0.6.13 : un contrôle par regex sur texte libre a son test de mutation.
            sk=(RACINE/'SKILL.md').read_text(encoding='utf-8');self.assertEqual(erreurs_statuts(sk),[])
            m=re.search(r'(\d+) Attesté,\s+(\d+) Documenté,\s+(\d+) Proposé,\s+(\d+) Vide,\s+(\d+) Hors domaine',sk);self.assertIsNotNone(m)
            for g in (1,2,3,4,5):
                mut=sk[:m.start(g)]+str(int(m.group(g))+1)+sk[m.end(g):]
                self.assertTrue(erreurs_statuts(mut),f'mutation du nombre {g} non détectée')
            self.assertTrue(erreurs_statuts(sk.replace(m.group(0),'(répartition supprimée)')))
        def test_cloture_vide(self):
            rv=recherches_vide();self.assertEqual(rv[(carte_id('RÉSONANCE'),7)],3)          # close en 0.7.7
            self.assertEqual(rv[(carte_id('CROISSANCE'),7)],2)                                 # rétrogradée, deux lectures
            self.assertEqual(sum(1 for v in rv.values() if v>=P['vide_recherches_cloture']),1)
            self.assertEqual(len(rv),sum(1 for v in statuts().values() if v=='Vide'))
        def test_questions(self):
            fm={'POL@7':'F','CTR@7':'f'}
            self.assertEqual(controle_questions([{'question':'q','si_oui':'POLARITÉ@7','si_non':'HIÉRARCHIE@7'}],fm,True),[])
            self.assertTrue(controle_questions([{'question':'q','si_oui':'POL@7','si_non':'POL@7'}],fm,True))
            self.assertTrue(controle_questions([{'question':'q','si_oui':'SEU@7','si_non':'HIE@7'}],fm,True))
            self.assertTrue(controle_questions(None,fm,True));self.assertEqual(controle_questions(None,fm,False),[])
        def test_audit(self):
            with contextlib.redirect_stdout(io.StringIO()):self.assertTrue(audit())
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(Tests)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    exiger(result.wasSuccessful(),'tests de régression échoués')


def sorties_robustes():
    """0.7.1 (audit hacker.ai) : sous Windows, une sortie redirigée ou une console MSYS est en cp1252 ; le
    premier « ⚠ » ou « → » levait UnicodeEncodeError, et toute la sortie, erreurs comprises, échouait.
    Sortie redirigée : UTF-8 (ce qu'attend le programme qui la lit). Console : encodage conservé, les
    caractères absents remplacés par une séquence d'échappement plutôt qu'un plantage."""
    for flux in (sys.stdout, sys.stderr):
        enc=(getattr(flux,'encoding','') or '').lower().replace('-','')
        if enc=='utf8' or not hasattr(flux,'reconfigure'):continue
        try:
            if flux.isatty():flux.reconfigure(errors='backslashreplace')
            else:flux.reconfigure(encoding='utf-8',errors='backslashreplace')
        except (ValueError,OSError,io.UnsupportedOperation):pass


if __name__=='__main__':
    sorties_robustes()
    try:
        main()
    except Exception as e:
        # Une entrée invalide ne doit jamais produire une trace Python. Avec --json, l'erreur est du JSON.
        msg=str(e) if isinstance(e,ValueError) else f'{type(e).__name__} : {e} (entrée inattendue)'
        if '--json' in sys.argv[1:]:
            # JSON d'erreur en ASCII pur : lisible par tout programme, quel que soit l'encodage de la console.
            print(json.dumps({'erreur':msg,'code':2},ensure_ascii=True))
        else:
            print('Erreur : '+msg,file=sys.stderr)
        sys.exit(2)
