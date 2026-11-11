# Alphabet situationnel — Les 13 strates (couche 0)

> Version : 0.7.70

> Source de vérité de la **liste des strates** et de leur contenu. Les règles de rattachement sont
> O1–O3 (`protocole.md`).

---

## 1. Vue d'ensemble

Les strates sont choisies aussi **éloignées** que possible les unes des autres, de la matière aux
artefacts. Raison (P1) : tester une carte dans des strates distantes éprouve sa portée descriptive ; cela ne démontre pas
le transfert de ses dynamiques prédictives.

| Rangée | Strates | Agents intentionnels | Registre Brown |
|---|---|---|---|
| Sans intention | 1 Matière · 2 Vivant · 11 Climat | non | ne s'applique pas ; noyau mathématique seul |
| Agents et groupes | 3 Psyché · 4 Relations · 5 Organisations | oui | s'applique |
| Institutions | 6 Économie · 7 Géopolitique · 8 Droit | oui | s'applique |
| Artefacts et durée | 9 Culture · 10 Technique · 12 Histoire longue | oui (indirectement pour 10) | s'applique |

La numérotation est historique (ordre de rédaction) ; elle ne dit rien de la proximité entre strates.
Les rangées regroupent les strates selon la présence d'agents intentionnels (ce qui décide si le
registre Brown s'applique) ; elles ne forment pas un axe unique.

**Hétérogénéité assumée (décision d'auteur, 0.4.8).** Les strates ne sont pas toutes du même type :
1 à 5 sont des niveaux d'organisation, 6 à 11 des domaines, et 12 (Histoire longue) une **échelle de
temps**. La strate 12 est conservée comme **registre de longue durée** : un fait y est rangé seulement
si sa signification dépend d'une période de plus d'un siècle (§2) ; sinon il va dans la strate de son
domaine. Les strates restent une liste plate de registres ; l'option de ramener les strates à 11 avec
un attribut de durée sur les faits est écartée. La strate 13 (Politique intérieure, 0.5.0) est un
domaine ; elle prend le numéro suivant pour ne renuméroter aucune strate existante (O3).

---

## 2. Fiches des strates

Pour chaque strate : ce qu'elle couvre, ce qui y compte comme fait (A5), des sources de faits
typiques, les disciplines de niveau 2 (indicatives, voir §3).

### 1 · Matière
- **Couvre** : états et transformations de la matière et de l'énergie, sans organisme.
- **Faits** : mesures physiques datées, résultats expérimentaux, relevés d'instruments.
- **Sources** : publications, bases de mesures, rapports d'incidents industriels.
- **Disciplines** : physique, chimie, science des matériaux, énergétique.

### 2 · Vivant
- **Couvre** : organismes, populations, écosystèmes ; le corps humain comme organisme.
- **Faits** : comptages de populations, observations d'écosystèmes, données cliniques agrégées.
- **Sources** : relevés écologiques, bases épidémiologiques, publications.
- **Disciplines** : biologie, écologie, épidémiologie, médecine (hors psyché).

### 3 · Psyché
- **Couvre** : fonctionnement d'un individu — perceptions, décisions, habitudes, développement.
- **Faits** : comportements décrits précisément, décisions datées, résultats de tests rapportés.
  Un ressenti n'est pas un fait (A5) ; une conduite l'est.
- **Sources** : récit précis de l'intéressé, observations, données d'études.
- **Disciplines** : psychologie, sciences cognitives, neurosciences.
- **Garde-fou** : pas de diagnostic (`constitution.md` §5).

### 4 · Relations
- **Couvre** : liens interpersonnels de petite taille — couple, famille, amitié, voisinage.
- **Faits** : échanges datés, ruptures, dons, conflits ouverts, décisions communes.
- **Sources** : récit précis d'un participant, correspondances.
- **Disciplines** : psychologie sociale, sociologie de la famille, anthropologie de la parenté.

### 5 · Organisations
- **Couvre** : collectifs dotés de règles d'appartenance — entreprises, associations, armées,
  administrations.
- **Faits** : décisions, organigrammes, effectifs, budgets internes, départs, réorganisations.
- **Sources** : documents internes ou publics, presse économique, rapports annuels.
- **Disciplines** : sociologie des organisations, management, gestion publique.

### 6 · Économie
- **Couvre** : production, échange, monnaie, finance, marchés, travail.
- **Faits** : prix, volumes, taux, indicateurs datés, faillites, flux commerciaux.
- **Sources** : instituts statistiques, banques centrales, données de marché.
- **Disciplines** : macroéconomie, finance, économie du travail, commerce international.

### 7 · Géopolitique
- **Couvre** : rapports entre États et acteurs armés ou transnationaux.
- **Faits** : déclarations officielles (faits sur le discours), accords, sanctions, mouvements de
  troupes, incidents datés, votes internationaux.
- **Sources** : flux d'événements codés (POLECAT, ACLED, GDELT), communiqués, presse.
- **Disciplines** : relations internationales, études stratégiques, science politique.

### 8 · Droit
- **Couvre** : normes, procédures, juridictions, institutions juridiques.
- **Faits** : textes adoptés, décisions de justice, procédures ouvertes, délais.
- **Sources** : journaux officiels, bases de jurisprudence, registres.
- **Disciplines** : droit public, droit privé, droit international, théorie du droit.

### 9 · Culture
- **Couvre** : récits, croyances, langues, arts, rites, religions.
- **Faits** : œuvres datées, pratiques observées, diffusion mesurée, rites décrits.
- **Sources** : corpus, enquêtes ethnographiques, données d'audience.
- **Disciplines** : anthropologie, histoire de l'art, linguistique, sciences des religions.

### 10 · Technique
- **Couvre** : artefacts techniques, infrastructures, systèmes d'information.
- **Faits** : versions, pannes datées, taux d'adoption, capacités mesurées, normes publiées.
- **Sources** : documentation technique, registres d'incidents, statistiques d'usage.
- **Disciplines** : ingénierie, informatique, réseaux, histoire des techniques.

### 11 · Climat
- **Couvre** : atmosphère, océans, cryosphère, cycles biogéochimiques.
- **Faits** : séries de mesures, anomalies datées, événements extrêmes enregistrés.
- **Sources** : agences météorologiques et océanographiques, rapports d'évaluation.
- **Disciplines** : climatologie, océanographie, géosciences.

### 12 · Histoire longue
- **Couvre** : dynamiques pluriséculaires — civilisations, démographie longue, empires.
- **Faits** : séries historiques, événements datés établis par l'historiographie.
- **Sources** : historiographie, bases de données historiques.
- **Disciplines** : histoire, démographie historique, archéologie.
- **Note** : cette strate porte sur des durées, pas sur un objet. Un fait n'y est classé que si sa
  signification dépend d'une période de plus d'un siècle.

### 13 · Politique intérieure
- **Couvre** : la compétition pour le pouvoir et son exercice à l'intérieur d'un État — exécutif,
  Parlement, partis, élections, opinion, mobilisations et mouvements sociaux.
- **Faits** : votes et scrutins nominatifs, résultats proclamés, motions, nominations, déclarations
  (faits sur le discours, A5), manifestations comptées par une source nommée, sondages publiés (fait
  sur la mesure publiée, pas sur l'opinion elle-même).
- **Sources** : open data de l'Assemblée nationale et du Sénat, résultats électoraux du ministère de
  l'Intérieur, Répertoire national des élus, Conseil constitutionnel, vie-publique.fr, presse ;
  inventaire détaillé dans `sources-france.md`.
- **Disciplines** : science politique, sociologie électorale, sociologie des mobilisations.
- **Ajoutée en 0.5.0** après un test sur la crise française d'octobre 2026 : le moteur de la
  situation, un mouvement auto-organisé, n'avait aucune strate où s'ancrer (`exemples.md`, exemple 11).

---

## 3. Niveau 2 : taxonomie empruntée (O2)

Les disciplines du §2 sont indicatives. La taxonomie de référence reste à choisir ; O2 est un objectif documentaire non encore réalisé. Candidat : la
classification thématique d'OpenAlex (de mémoire : 4 domaines, 26 champs, environ 250 sous-champs,
environ 4 500 thèmes — **chiffres à vérifier** avant adoption). Procédure d'adoption : rattacher
chaque sous-champ à une strate unique, publier la table de correspondance dans ce fichier, incrémenter
la version.

---

## 4. Cas de rattachement difficiles (O1)

Un fait peut sembler relever de deux strates. Règles de départage, dans l'ordre :

1. **Le mécanisme, pas le thème.** Une sanction économique est un fait de strate 7 (décision entre
   États) ; ses effets sur les prix sont des faits de strate 6. Ce sont deux faits.
2. **L'acteur qui produit le fait.** Une décision de justice est en 8, même si elle porte sur un
   contrat commercial.
3. **En cas de doute réel,** classer le fait dans les deux strates et l'indiquer : l'enchevêtrement
   (G3) dira si le lien est un transfert ou un écho.

**Frontières de la strate 13 (Politique intérieure)**, application des règles 1 et 2 :

| Fait | Strate | Raison |
|---|---|---|
| couvre-feu, interdiction préfectorale, état d'urgence décrété, loi adoptée | 8 | l'acte juridique lui-même |
| vote de censure, alliance parlementaire, consigne de vote, résultat électoral | 13 | compétition pour le pouvoir |
| congrès d'un parti, fonctionnement interne d'un syndicat | 5 | organisation à règles d'appartenance, vue de l'intérieur |
| mouvement sans règles d'appartenance, coordination entre organisations | 13 | action collective hors d'une organisation |
| élection d'un État vue par les autres États, ingérence étrangère | 7 | rapport entre États |
| répertoire ou symbole évoqué sans mobilisation (commémoration, récit) | 9 | récit, pas action |

**Régimes d'exception.** L'état d'urgence ou un couvre-feu décrété est une **CONTRAINTE@8** qui
apparaît ; son extension (communes, durée, mesures) se prévoit par `CONTRAINTE@8 s'intensifie` avec
une grandeur comptée. Ce n'est un **SEUIL@8** que si une décision devient définitive ou si des mesures
d'exception passent dans le droit commun (point de non-retour) ; la chute d'un gouvernement est un
**SEUIL@13**.

Un même fait ne peut ancrer qu'**un** mot par strate.
