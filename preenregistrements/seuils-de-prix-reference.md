# Seuils de prix : référence avant tout mécanisme (2026-11-20)

Décision de l'auteur (19 h 21) : maîtriser le sujet avant de le traiter ; l'auteur déclare ne pas avoir les compétences
techniques sur ce point, Claude sert de filet. Origine : `registre/questions-bot-cadre.md` (18 questions sur 38 du
journal du bot portent sur un prix ou un chiffre à une date).

## 1. Ce qui est établi (et ce qui ne l'est pas)
- **Marche au hasard à court terme.** Sur quelques jours, les rendements d'un actif coté très liquide sont presque
  imprévisibles (efficience informationnelle : E. Fama, « Efficient Capital Markets: A Review of Theory and Empirical
  Work », *Journal of Finance*, 1970). La meilleure prévision du prix est le prix du jour ; l'incertitude croît comme la
  racine carrée de la durée.
- **Modèle log-normal.** Le logarithme du prix suit une marche au hasard de volatilité σ (F. Black et M. Scholes, « The
  Pricing of Options and Corporate Liabilities », *Journal of Political Economy*, 1973). Sans dérive :
  - **au-dessus du seuil K À la date T** : P = Φ( ln(S₀/K) / (σ·√t) ), t en années, S₀ le dernier prix connu ;
    sous le seuil : 1 − P.
  - **atteindre K AVANT la date T** (n'importe quel moment) : par le principe de réflexion, P ≈ 2·Φ( −|ln(K/S₀)| / (σ·√t) )
    pour un seuil pas encore atteint. Pour un seuil éloigné, c'est environ deux fois la probabilité « à la date ».
  - Ces deux formes de question ne doivent jamais être confondues.
- **Volatilité.** σ estimée sur les rendements logarithmiques quotidiens récents (30 et 90 jours de bourse), annualisée
  (× √252 pour les actions et indices, × √365 pour les cryptomonnaies qui cotent tous les jours).
- **Ce qui n'est pas établi et que le modèle ignore** : les queues épaisses (grands mouvements plus fréquents que la
  loi normale, surtout en cryptomonnaies), les grappes de volatilité, les annonces datées dans la fenêtre (résultats
  d'entreprise, réunion de banque centrale, sommet de l'OPEP+). Le calibrage sur des questions passées dira de combien
  il faut élargir.
- **Entrées interdites** : aucune cote de marché de prédiction, aucune prévision de foule, aucune volatilité implicite
  d'options (prix de marché) ; seulement l'historique des prix.

## 2. Données
- FRED (gratuit, déjà collecté par `collecte_fred.py`) : bitcoin (CBBTCUSD) et éther (CBETHUSD) quotidiens depuis 2015,
  Brent (DCOILBRENTEU) ; ajoutés en 0.10.398 : Nasdaq Composite (NASDAQCOM), S&P 500 (SP500), Dow Jones (DJIA).
- Actions individuelles (Nvidia, Tesla, Strategy…) : source gratuite à vérifier depuis GitHub (fichier robots),
  pas encore branchée.

## 3. Vérification prévue (avant le bot)
Questions de seuil de prix déjà résolues au registre : environ 120 (Polymarket 89, Manifold 23, Metaculus 11), dont une
soixantaine à moins de trois semaines ; quelques-unes dans l'échantillon de mise au point. On vérifiera le calibrage du
modèle sur celles dont l'actif a une série (bitcoin, éther, Brent, indices), avec les seuls prix connus avant la date
de la question. Plan du test écrit et annoncé à l'auteur avant tout calcul.

## 4. Deuxième famille : chiffres publiés (inflation, cas, sondages)
Même logique, autre modèle : dernier chiffre publié + distribution des variations passées entre deux publications +
calendrier de publication. À traiter après les prix.
