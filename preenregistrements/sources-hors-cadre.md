# Préenregistrement : sources hors cadre, collectes en ombre
2026-11-18, bot 0.10.299.

Décisions d'auteur du 2026-11-18 : 22 h 30 (« plus de folie, sans ça nous ne pourrons pas nous dépasser ») et 22 h 35
(« recoupe tout ce qui est exploitable et branche-le directement sur GitHub ; carte blanche »). Liste complète et
cartes : document de projet claude/sources-hors-cadre.md.

## Principe
Des traces PUBLIQUES, INSTITUTIONNELLES et DATÉES laissées par ceux qui préparent l'avenir. Datées, elles ne fuient
pas. Aucune personne privée ; robots.txt respecté (politesse.py) ; aucun contournement ; une source qui refuse est
notée, jamais forcée. Toutes les collectes sont EN OMBRE : rien n'entre dans le bot ni dans ce qu'il poste (décision
du 2026-11-18, 19 h 40). Chaque source n'entrera qu'après un banc préenregistré à part, quand assez de questions
résolues la croiseront.

## Branché (0.10.298 et 0.10.299)
| Source | Fichier | Carte | Lancement |
|---|---|---|---|
| Pages vues et protections Wikipédia | banc_wikipedia.py | CROISSANCE, SEUIL | banc (manuel) |
| Certificats HTTPS des laboratoires d'IA (Cert Spotter) | collecte_certificats.py | DÉCLENCHEUR | chaque nuit |
| Rythme de publication des sites officiels (flux RSS) | collecte_routines.py | PÉRIODICITÉ, SEUIL | chaque nuit |
| Federal Register, inspection publique (textes avant publication) | collecte_federal_register.py | DÉCLENCHEUR | chaque nuit |
| Interdictions de survol FAA | sonde_tfr.py (sonde seulement) | RÉSEAU, RÉCIPROCITÉ | manuel |

## Bancs prévus (à préenregistrer quand les données suffiront)
- Certificats : sur les questions résolues de sortie de modèles d'IA, un nom de produit apparu dans les certificats
  avant la date de la question annonce-t-il plus souvent un OUI ? (historique des certificats rattrapé de nuit en nuit)
- Routines : un écart au rythme habituel d'une source officielle (moins de 50 % de sa médiane sur 7 jours) précède-t-il
  plus souvent un événement de la question liée ?
- Federal Register : un texte en inspection publique qui correspond à une question ouverte (agence et mots du titre).

## En attente d'une intervention de l'auteur (clés gratuites)
USPTO (marques), USAJOBS (offres d'emploi publiques), CourtListener (audiences), congress.gov (agenda du Congrès),
Cert Spotter (clé facultative : limite plus haute). Aucune n'est indispensable pour démarrer.
