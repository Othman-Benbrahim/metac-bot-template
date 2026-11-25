# Contagion simple ou complexe des manifestations entre pays voisins (préenregistrement, 2026-11-25, 20 h 10)

Décision de l'auteur : formaliser la psychologie de l'influence (19 h 47) ; « on peut y aller ; j'aimerais que tu utilises
les instruments de mesure à ta disposition » (19 h 57). Théorie : Centola et Macy (2007), Centola (2010, 2018). Une
information se propage par un seul contact (contagion simple) ; un comportement coûteux et risqué, comme manifester,
demande plusieurs sources distinctes (contagion complexe). Prédiction écrite AVANT tout calcul sur ces données : aucun
taux n'a été regardé. Calcul fait une fois par `mise_au_point/contagion_complexe.py`, écrit à la suite de ce texte et
qui le suit sans le changer.

## Données (fixées)
- `registre/gdelt-manifestations.csv`, colonne « manifestations » (événements de protestation par pays et par jour,
  GDELT, codes CAMEO 14), jours couverts `registre/gdelt-jours.txt` (2024-07-01 → 2026-11-23) ; jour non couvert = absent.
- Voisins terrestres : `registre/voisins.json`.
- Défaut connu AVANT le calcul : la Serbie (code FIPS « RI ») et quelques autres pays des Balkans manquent, la table de
  conversion FIPS → ISO ne les contenant pas. Non corrigé pour ce test (la correction ne vaut que pour l'avenir).

## Mesure (fixée)
- **Pic** : un jour où le compte d'un pays est ≥ max(5, 3 × médiane de ses comptes des 90 jours couverts précédents).
  Premier jour jugé : le 91e jour couvert.
- **Unité** : pays-semaine (semaines ISO, lundi à dimanche). Y = 1 si le pays a au moins un pic dans la semaine.
- **Début seulement** : on ne garde que les pays-semaines où le pays n'avait AUCUN pic la semaine précédente (sinon on
  mesure la persistance d'un mouvement, pas sa transmission).
- **Exposition** k = nombre de voisins DISTINCTS ayant eu au moins un pic la semaine précédente ; classes 0, 1, 2, 3 et plus.
- Pays retenus : présents dans les données et ayant au moins un voisin présent.

## Témoin des chocs communs (fixé)
Des pics simultanés peuvent venir d'un même choc mondial (une guerre, une décision américaine) et non d'une transmission.
Témoin : pour chaque pays, des **pseudo-voisins** tirés au hasard parmi les pays NON voisins présents, en même nombre
que ses vrais voisins ; 200 tirages (graine 20261125). r'_k = taux moyen sur les tirages. **Excès** e_k = r_k − r'_k.

## Test (fixé)
- Contagion (tout court) : e_1 > 0.
- **Statistique de forme** D = (e_2 − e_1) − (e_1 − e_0). Contagion complexe : le deuxième voisin ajoute plus que le premier
  (D > 0, effet convexe, seuil). Contagion simple : le premier voisin ajoute le plus (D < 0, effet concave).
- Intervalle à 90 % par rééchantillonnage des PAYS (1 000 tirages, graine 20261125 ; le témoin est recalculé avec 50
  tirages de pseudo-voisins par rééchantillon).
- Verdict : complexe si l'intervalle de D est au-dessus de 0 ; simple s'il est au-dessous ; sinon non tranché. Même règle
  pour e_1 (contagion établie ou non).
- Rapporté aussi : effectifs par classe, r_k, r'_k, e_k, et e_3+ (pour voir si l'effet continue de croître).

## Limites connues avant le calcul
- GDELT compte des événements rapportés par la presse : une vague couverte chez un voisin peut gonfler la couverture du
  pays (effet média, pas contagion). Le témoin ne le corrige qu'en partie.
- Le voisinage terrestre ignore la proximité linguistique et numérique (diasporas, réseaux), canaux de la contagion moderne.
- Deux ans et demi de données ; un résultat non tranché est un résultat.
