# Couche écosystème (structure de la carte × état des séries) — procédure écrite avant le calcul

Décisions de l'auteur, 2026-11-24 : forme validée à 20 h 41 (« Oui ») avec deux avertissements : (1) chaque écosystème
joue à des niveaux différents — temps, vitesse, espace, taille — à travers différentes échelles : il faut en tenir
compte ; (2) la carte est probablement incomplète : la compléter petit à petit selon ce qu'on trouve. Une passe ; sans
retour. Lus avant : trois lectures d'essai (Brent, Fed, Israël–Iran), sans issues.

## Règle (ecosysteme_couche.py)
1. Rattachement : liste validée du chantier A (lecture_mecanique.Carte.rattacher).
2. Relations entrantes des cibles, effet « + » ou « − », retenues selon les échelles des fiches :
   temps (délai ≤ horizon), vitesse (amont « années » ou plus lent écarté si horizon < 180 j), espace (amont limité à
   des pays, écarté si la question nomme d'autres pays), taille (règle d'intensité : seuil et masse critique |z| ≥ 2 ;
   hystérésis |z| ≥ 1,5 ; saturation tanh ; sinon z borné à ±3).
3. État de l'amont : première série collectée ; z de la variation sur W (délai, 7 à 90 jours) contre les variations sur
   W des deux années précédentes ; données antérieures à la date de la question ; série trop ancienne = pas d'état.
4. d = Σ force·signe·g(z) / Σ force. 5. Sens du oui : lexique écrit (haut / bas), abstention si ambigu.
6. p = σ(logit p0 + k·d·sens) ; k seul paramètre.

## Évaluation (mise_au_point/couche_ecosysteme.py, une passe)
p0 = part de oui du corpus hors groupe. k estimé sur les questions lues d'avant 2026 (grille −3…3) ; confirmation sur
celles de 2026. Branchement si k > 0, perte(couche) < perte(p0) sur la confirmation, et, s'il y a au moins 5 questions
de 2026 où |d| ≥ 0,3, perte(couche) < perte(p0) sur celles-ci (idée de Snover : juger là où la carte pousse fort).
Lacunes de la carte (pas de compartiment, pas de relation, amont sans série, série sans état, sens illisible, rien aux
échelles) comptées dans registre/carte-lacunes.json pour compléter la carte.
Limites déclarées : 212 compartiments sur 837 ont une série ; ponts entre fiches non signés, non utilisés ; lexique du
sens du oui grossier ; p0 est un taux de base, pas la prévision du bot (non disponible sur le corpus).
