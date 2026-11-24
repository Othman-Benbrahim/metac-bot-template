# Brique « accords » — procédure écrite avant le calcul

Décision de l'auteur, 2026-11-24, 16 h 16 : « Je valide les trois points » (accords avec PA-X, puis annonces, puis
produits) ; pas de seuil de taille : « plus on découpe les mécanismes plus on affine, moins il y a de statistiques et
c'est voulu, c'est le principe même de la matriochka ». Les hypothèses seront testées sur le terrain.
Procédure versée AVANT la collecte PA-X et avant tout calcul ; passée une fois, après la collecte ; sans retour.

## Sous-familles (titre seul, dans cet ordre)
Hors famille : banques centrales, Powell ; polarité inversée (« not meet ») : abstention.
1. tenue — « ceasefire … broken by » (oui = rompu), « ceasefire … continues through » (oui = tient) ;
2. rencontre — meet, meeting, attend ;
3. cessez_le_feu — ceasefire, cease-fire, truce (le conclure) ;
4. accord_paix — peace deal, nuclear deal, peace agreement, agreement restricting Iran…, sign a … deal ; quitter un
   accord (leave, withdraw, exit) n'en est pas un ;
5. autre — le reste (accords commerciaux, traités, adhésions, signatures).

## Mesures
- Source : PA-X v10 (Université d'Édimbourg, PeaceRep, CC BY-NC-SA 4.0), métadonnées seules (processus, stade, date).
- cessez_le_feu : λ = accords de stade Cea signés dans un processus déjà actif (un accord dans les 365 jours
  précédents), par jour de processus actif ; P = 1 − exp(−λ·h).
- accord_paix : même calcul, stades SubComp ou SubPar.
- tenue : un nouveau cessez-le-feu dans le même processus vaut rupture du précédent (indicateur indirect) ; λr par jour
  d'exposition (jusqu'au suivant, 365 jours au plus) ; P(rupture) = 1 − exp(−λr·h), « continues » = 1 − P(rupture).
- rencontre, autre : aucune mesure extérieure ; part de oui de la sous-famille, tirée vers la famille (poids 5).
- Sans regard vers l'avant : accords signés avant la date de la question ; exposition arrêtée à la dernière date
  couverte par PA-X. Limite déclarée : PA-X peut avoir ajouté des accords anciens après coup.
- h = jours entre la date de la question et l'échéance lue dans le titre ; échéance illisible = abstention.
- Limites déclarées : un cessez-le-feu PA-X peut être partiel ou local (le titre Metaculus vise souvent un
  cessez-le-feu général) ; les accords entre États hors guerre (accord nucléaire) y sont peu présents.

## Évaluation (une passe)
Corpus résolu, structure « procédure ». Groupe = mots à majuscule du titre. Référence = part de oui de la famille hors
groupe. Mélange = un quart (log-odds) avec la référence, plafonné à 15 points.
Branchement PAR SOUS-FAMILLE si : (1) règle < référence ; (2) mélange < référence ; (3) règle < référence sur les
questions de 2026 de la sous-famille, quand il y en a. Les sous-familles branchées et les taux de rencontre / autre
sont écrits dans ecosystemes/accords-taux-classes.json, que le bot lit (même mélange avec sa prévision, même plafond,
journal scellé).
